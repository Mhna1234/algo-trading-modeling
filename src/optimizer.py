"""
Portfolio Optimization Module

This module implements modern portfolio theory optimization using convex optimization.
It provides implementations for:
- Mean-variance optimization
- Sharpe ratio maximization  
- Risk parity optimization
- Transaction cost-aware optimization
- Constraints handling (long-only, turnover limits, etc.)

Mathematical Formulations:
- Mean-Variance: max w^T μ - λ w^T Σ w, s.t. 1^T w = 1, w ≥ 0
- Sharpe Maximization: max (w^T μ - R_f) / sqrt(w^T Σ w), s.t. 1^T w = 1
- Risk Parity: min Σ(w_i * (Σw)_i / σ_p - 1/n)^2
- Transaction Costs: Penalty = κ * Σ|w_t - w_{t-1}|
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
import warnings
import logging
import cvxpy as cp
from scipy.optimize import minimize
from pypfopt import EfficientFrontier, risk_models, expected_returns
from pypfopt.objective_functions import L2_reg

logger = logging.getLogger(__name__)

class PortfolioOptimizer:
    """
    Comprehensive portfolio optimization using convex optimization.
    
    This class provides methods for various portfolio optimization objectives
    with support for constraints and transaction costs.
    """
    
    def __init__(self, 
                 returns: Optional[pd.DataFrame] = None,
                 risk_free_rate: float = 0.02,
                 max_weight: float = 0.3,
                 min_weight: float = 0.0,
                 transaction_cost: float = 0.001,
                 turnover_limit: Optional[float] = None):
        """
        Initialize PortfolioOptimizer with configuration parameters.
        
        Args:
            returns: Historical returns data (optional, can be provided in optimize())
            risk_free_rate: Annual risk-free rate
            max_weight: Maximum weight per asset
            min_weight: Minimum weight per asset (0 for long-only)
            transaction_cost: Transaction cost rate
            turnover_limit: Maximum portfolio turnover per period
        """
        self.returns = returns
        self.risk_free_rate = risk_free_rate
        self.max_weight = max_weight
        self.min_weight = min_weight
        self.transaction_cost = transaction_cost
        self.turnover_limit = turnover_limit
        
        # Store last optimization results
        self.last_weights = None
        self.last_returns = None
        self.last_volatility = None
        self.last_sharpe = None
    
    def optimize(self,
                initial_weights: Union[pd.Series, np.ndarray],
                objective: str = 'sharpe',
                alpha: float = 0.95,
                long_only: bool = True,
                max_weight: Optional[float] = None,
                risk_aversion: float = 1.0,
                lookback: Optional[int] = None,
                returns_data: Optional[pd.DataFrame] = None,
                **kwargs) -> np.ndarray:
        """
        Generic optimization wrapper method.
        
        This is a convenience method that routes to the appropriate
        optimization function based on the objective.
        
        Args:
            initial_weights: Starting weights or signals
            objective: Optimization objective ('sharpe', 'mvo', 'cvar', 'risk_parity')
            alpha: Confidence level for CVaR (if using cvar objective)
            long_only: Whether to enforce long-only constraints
            max_weight: Maximum weight per asset (overrides instance setting)
            risk_aversion: Risk aversion parameter (for MVO)
            lookback: Lookback period (for data windowing)
            returns_data: Historical returns (overrides instance returns)
            **kwargs: Additional strategy-specific parameters
            
        Returns:
            Optimal portfolio weights
        """
        # Use provided returns data or fall back to instance returns
        if returns_data is not None:
            returns = returns_data
        elif self.returns is not None:
            returns = self.returns
        else:
            # If no returns data available, return equal weights
            logger.warning("No returns data available, using equal weights")
            n = len(initial_weights)
            return np.ones(n) / n
        
        # Use lookback period if specified, otherwise use all available data
        if lookback is not None and lookback > 0:
            returns = returns.iloc[-lookback:]
            
        # Calculate expected returns and covariance from recent data
        expected_returns = returns.mean() * 252  # Annualized
        cov_matrix = returns.cov() * 252  # Annualized
        
        # Use max_weight parameter if provided, otherwise use instance setting
        if max_weight is not None:
            original_max_weight = self.max_weight
            self.max_weight = max_weight
        
        try:
            # Route to appropriate optimization method
            if objective == 'sharpe':
                weights = self.sharpe_maximization(expected_returns, cov_matrix)
            elif objective == 'mvo':
                weights = self.mean_variance_optimization(expected_returns, cov_matrix, 
                                                         risk_aversion=risk_aversion)
            elif objective == 'cvar':
                weights = self.cvar_optimization(returns, alpha=alpha)
            elif objective == 'risk_parity':
                weights = self.risk_parity_optimization(cov_matrix)
            elif objective == 'black_litterman':
                weights = self.black_litterman_optimization(expected_returns, cov_matrix, **kwargs)
            else:
                # Default to equal weights for unknown objectives
                logger.warning(f"Unknown objective '{objective}', using equal weights")
                n = len(initial_weights)
                weights = np.ones(n) / n
        finally:
            # Restore original max_weight if it was temporarily changed
            if max_weight is not None:
                self.max_weight = original_max_weight
        
        return weights
        
    def mean_variance_optimization(self, 
                                 expected_returns: Union[pd.Series, np.ndarray],
                                 cov_matrix: Union[pd.DataFrame, np.ndarray],
                                 risk_aversion: float = 1.0,
                                 previous_weights: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Solve mean-variance optimization problem.
        
        Mathematical formulation:
        maximize: w^T μ - λ w^T Σ w - κ |w - w_prev|
        subject to: Σw_i = 1, w_min ≤ w_i ≤ w_max
        
        Args:
            expected_returns: Expected returns for each asset
            cov_matrix: Covariance matrix of returns
            risk_aversion: Risk aversion parameter (λ)
            previous_weights: Previous period weights for transaction costs
            
        Returns:
            Optimal portfolio weights
        """
        n_assets = len(expected_returns)
        
        # Convert to numpy arrays
        mu = np.array(expected_returns)
        sigma = np.array(cov_matrix)
        
        # Define optimization variables
        w = cp.Variable(n_assets)
        
        # Objective function: utility - transaction costs
        utility = mu.T @ w - 0.5 * risk_aversion * cp.quad_form(w, sigma)
        
        # Add transaction costs if previous weights provided
        if previous_weights is not None:
            w_prev = np.array(previous_weights)
            transaction_penalty = self.transaction_cost * cp.norm(w - w_prev, 1)
            objective = utility - transaction_penalty
        else:
            objective = utility
        
        # Constraints
        constraints = [
            cp.sum(w) == 1,  # Budget constraint
            w >= self.min_weight,  # Minimum weight
            w <= self.max_weight   # Maximum weight
        ]
        
        # Add turnover constraint if specified
        if self.turnover_limit is not None and previous_weights is not None:
            constraints.append(cp.norm(w - w_prev, 1) <= self.turnover_limit)
        
        # Solve optimization problem
        problem = cp.Problem(cp.Maximize(objective), constraints)
        problem.solve(solver=cp.ECOS)
        
        if problem.status != cp.OPTIMAL:
            logger.warning(f"Optimization did not converge: {problem.status}")
            # Return equal-weighted portfolio as fallback
            return np.ones(n_assets) / n_assets
        
        optimal_weights = w.value
        
        # Store results
        self.last_weights = optimal_weights
        self.last_returns = np.dot(optimal_weights, mu)
        self.last_volatility = np.sqrt(np.dot(optimal_weights, np.dot(sigma, optimal_weights)))
        self.last_sharpe = (self.last_returns - self.risk_free_rate) / self.last_volatility
        
        logger.info(f"Mean-variance optimization completed. Sharpe: {self.last_sharpe:.3f}")
        return optimal_weights
    
    def sharpe_maximization(self, 
                          expected_returns: Union[pd.Series, np.ndarray],
                          cov_matrix: Union[pd.DataFrame, np.ndarray],
                          previous_weights: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Maximize Sharpe ratio using convex optimization.
        
        Mathematical formulation:
        maximize: (w^T μ - R_f) / sqrt(w^T Σ w)
        subject to: Σw_i = 1, w_min ≤ w_i ≤ w_max
        
        This is reformulated as a convex problem by optimization over κ and y = κw.
        
        Args:
            expected_returns: Expected returns for each asset
            cov_matrix: Covariance matrix of returns
            previous_weights: Previous period weights for transaction costs
            
        Returns:
            Optimal portfolio weights
        """
        n_assets = len(expected_returns)
        
        # Convert to numpy arrays
        mu = np.array(expected_returns)
        sigma = np.array(cov_matrix)
        
        # Reformulation variables: y = κw, κ > 0
        y = cp.Variable(n_assets)
        kappa = cp.Variable()
        
        # Objective: maximize excess return (denominator will be constrained to 1)
        excess_returns = mu - self.risk_free_rate
        objective = excess_returns.T @ y
        
        # Constraints
        constraints = [
            cp.quad_form(y, sigma) <= 1,  # Risk constraint (normalized)
            cp.sum(y) == kappa,  # Budget constraint
            kappa >= 0,  # Kappa must be positive
            y >= self.min_weight * kappa,  # Minimum weight
            y <= self.max_weight * kappa   # Maximum weight
        ]
        
        # Solve optimization problem
        problem = cp.Problem(cp.Maximize(objective), constraints)
        problem.solve(solver=cp.ECOS)
        
        if problem.status != cp.OPTIMAL:
            logger.warning(f"Sharpe optimization did not converge: {problem.status}")
            return self.mean_variance_optimization(expected_returns, cov_matrix, 
                                                 risk_aversion=1.0, previous_weights=previous_weights)
        
        # Recover original weights: w = y / κ
        optimal_weights = y.value / kappa.value
        
        # Handle edge cases
        if np.any(np.isnan(optimal_weights)) or np.any(np.isinf(optimal_weights)):
            logger.warning("Invalid weights from Sharpe optimization, using mean-variance")
            return self.mean_variance_optimization(expected_returns, cov_matrix,
                                                 risk_aversion=1.0, previous_weights=previous_weights)
        
        # Normalize weights to sum to 1 (numerical precision)
        optimal_weights = optimal_weights / np.sum(optimal_weights)
        
        # Store results
        self.last_weights = optimal_weights
        self.last_returns = np.dot(optimal_weights, mu)
        self.last_volatility = np.sqrt(np.dot(optimal_weights, np.dot(sigma, optimal_weights)))
        self.last_sharpe = (self.last_returns - self.risk_free_rate) / self.last_volatility
        
        logger.info(f"Sharpe maximization completed. Sharpe: {self.last_sharpe:.3f}")
        return optimal_weights
    
    def risk_parity_optimization(self, 
                               cov_matrix: Union[pd.DataFrame, np.ndarray],
                               target_risk: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Solve risk parity optimization problem.
        
        Mathematical formulation:
        minimize: Σ(w_i * (Σw)_i / σ_p - target_i)^2
        subject to: Σw_i = 1, w_i ≥ 0
        
        Where (Σw)_i is the i-th component of the portfolio risk contribution.
        
        Args:
            cov_matrix: Covariance matrix of returns
            target_risk: Target risk contribution (default: equal risk)
            
        Returns:
            Risk parity portfolio weights
        """
        n_assets = len(cov_matrix)
        sigma = np.array(cov_matrix)
        
        if target_risk is None:
            target_risk = np.ones(n_assets) / n_assets
        
        def risk_parity_objective(weights):
            """Objective function for risk parity optimization."""
            portfolio_vol = np.sqrt(np.dot(weights, np.dot(sigma, weights)))
            
            if portfolio_vol < 1e-10:
                return 1e10  # Large penalty for zero volatility
            
            # Risk contributions: w_i * (Σw)_i / σ_p
            risk_contributions = weights * np.dot(sigma, weights) / portfolio_vol
            risk_contributions = risk_contributions / np.sum(risk_contributions)  # Normalize
            
            # Sum of squared deviations from target
            objective = np.sum((risk_contributions - target_risk) ** 2)
            return objective
        
        def constraint_sum_to_one(weights):
            """Budget constraint."""
            return np.sum(weights) - 1.0
        
        # Initial guess: equal weights
        x0 = np.ones(n_assets) / n_assets
        
        # Bounds: non-negative weights with maximum limit
        bounds = [(self.min_weight, self.max_weight) for _ in range(n_assets)]
        
        # Constraints
        constraints = [{'type': 'eq', 'fun': constraint_sum_to_one}]
        
        # Solve optimization
        result = minimize(
            risk_parity_objective,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'ftol': 1e-9, 'disp': False}
        )
        
        if not result.success:
            logger.warning("Risk parity optimization failed, using equal weights")
            return np.ones(n_assets) / n_assets
        
        optimal_weights = result.x
        
        # Store results
        self.last_weights = optimal_weights
        portfolio_vol = np.sqrt(np.dot(optimal_weights, np.dot(sigma, optimal_weights)))
        self.last_volatility = portfolio_vol
        
        logger.info(f"Risk parity optimization completed. Portfolio vol: {portfolio_vol:.3f}")
        return optimal_weights
    
    def cvar_optimization(self,
                         returns_data: pd.DataFrame,
                         alpha: float = 0.95,
                         previous_weights: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Minimize Conditional Value at Risk (CVaR).
        
        CVaR (Expected Shortfall) is the expected loss given that the loss
        exceeds the VaR threshold. It's a coherent risk measure that captures
        tail risk better than VaR.
        
        Mathematical formulation:
        minimize: CVaR_α(w) = VaR_α + (1/(1-α)) E[(loss - VaR_α)^+]
        subject to: Σw_i = 1, w_min ≤ w_i ≤ w_max
        
        Args:
            returns_data: Historical returns data (DataFrame)
            alpha: Confidence level (0.95 = minimize worst 5%)
            previous_weights: Previous period weights for transaction costs
            
        Returns:
            Optimal portfolio weights
        """
        n_assets = returns_data.shape[1]
        n_scenarios = len(returns_data)
        
        # Convert to numpy array
        returns_matrix = returns_data.values
        
        # Decision variables
        w = cp.Variable(n_assets)  # Portfolio weights
        var = cp.Variable()  # Value at Risk
        z = cp.Variable(n_scenarios)  # Auxiliary variables for CVaR
        
        # Portfolio returns for each scenario
        portfolio_returns = returns_matrix @ w
        
        # CVaR objective
        cvar = var + (1 / (n_scenarios * (1 - alpha))) * cp.sum(z)
        
        # Constraints
        constraints = [
            cp.sum(w) == 1,  # Budget constraint
            w >= self.min_weight,  # Minimum weight
            w <= self.max_weight,  # Maximum weight
            z >= 0,  # Auxiliary variables non-negative
            z >= -portfolio_returns - var  # Definition of CVaR
        ]
        
        # Transaction costs if previous weights provided
        if previous_weights is not None and self.transaction_cost > 0:
            turnover = cp.norm1(w - previous_weights)
            objective = cvar + self.transaction_cost * turnover
        else:
            objective = cvar
        
        # Solve optimization problem
        problem = cp.Problem(cp.Minimize(objective), constraints)
        
        try:
            problem.solve(solver=cp.ECOS)
        except:
            # Try alternative solver if ECOS fails
            try:
                problem.solve(solver=cp.SCS)
            except:
                logger.warning("CVaR optimization failed, using equal weights")
                return np.ones(n_assets) / n_assets
        
        if problem.status not in [cp.OPTIMAL, cp.OPTIMAL_INACCURATE]:
            logger.warning(f"CVaR optimization did not converge: {problem.status}")
            return np.ones(n_assets) / n_assets
        
        optimal_weights = w.value
        
        # Handle edge cases
        if optimal_weights is None or np.any(np.isnan(optimal_weights)):
            logger.warning("Invalid weights from CVaR optimization, using equal weights")
            return np.ones(n_assets) / n_assets
        
        # Normalize weights
        optimal_weights = optimal_weights / np.sum(optimal_weights)
        
        # Store results
        self.last_weights = optimal_weights
        self.last_returns = np.mean(returns_matrix @ optimal_weights) * 252
        self.last_volatility = np.std(returns_matrix @ optimal_weights) * np.sqrt(252)
        
        logger.info(f"CVaR optimization completed. VaR: {var.value:.4f}, CVaR: {cvar.value:.4f}")
        return optimal_weights
    
    def black_litterman_optimization(self, 
                                   expected_returns: Union[pd.Series, np.ndarray],
                                   cov_matrix: Union[pd.DataFrame, np.ndarray],
                                   market_caps: Optional[Union[pd.Series, np.ndarray]] = None,
                                   tau: float = 0.025,
                                   views: Optional[Dict] = None) -> np.ndarray:
        """
        Black-Litterman portfolio optimization.
        
        Mathematical formulation:
        μ_BL = [(τΣ)^(-1) + P^T Ω^(-1) P]^(-1) [(τΣ)^(-1)Π + P^T Ω^(-1) Q]
        Σ_BL = [(τΣ)^(-1) + P^T Ω^(-1) P]^(-1)
        
        Args:
            expected_returns: Historical expected returns
            cov_matrix: Covariance matrix
            market_caps: Market capitalizations for equilibrium returns
            tau: Confidence parameter for prior
            views: Dictionary of investor views
            
        Returns:
            Black-Litterman optimal weights
        """
        n_assets = len(expected_returns)
        sigma = np.array(cov_matrix)
        
        # Market equilibrium returns (if market caps not provided, use equal weights)
        if market_caps is None:
            w_market = np.ones(n_assets) / n_assets
        else:
            w_market = np.array(market_caps) / np.sum(market_caps)
        
        # Implied equilibrium returns: Π = λ Σ w_market
        # Estimate lambda from historical returns
        lambda_market = (np.mean(expected_returns) - self.risk_free_rate) / np.var(expected_returns)
        pi = lambda_market * np.dot(sigma, w_market)
        
        # If no views provided, use original mean-variance optimization
        if views is None:
            return self.sharpe_maximization(pi, cov_matrix)
        
        # Process views (simplified implementation)
        # In practice, this would handle more complex view structures
        P = np.eye(n_assets)  # Simplified: absolute views on each asset
        Q = np.array(expected_returns)  # Views are the expected returns
        omega = np.eye(n_assets) * 0.01  # View uncertainty
        
        # Black-Litterman formula
        tau_sigma_inv = np.linalg.inv(tau * sigma)
        p_omega_inv_p = np.dot(P.T, np.dot(np.linalg.inv(omega), P))
        
        # Posterior mean
        bl_precision = tau_sigma_inv + p_omega_inv_p
        bl_mean = np.dot(np.linalg.inv(bl_precision),
                        np.dot(tau_sigma_inv, pi) + np.dot(P.T, np.dot(np.linalg.inv(omega), Q)))
        
        # Posterior covariance
        bl_cov = np.linalg.inv(bl_precision)
        
        # Optimize using Black-Litterman inputs
        return self.sharpe_maximization(bl_mean, bl_cov)
    
    def optimize_portfolio_forecasted(self,
                                    mean_forecast: Union[pd.Series, np.ndarray],
                                    cov_matrix: Union[pd.DataFrame, np.ndarray],
                                    method: str = 'sharpe',
                                    previous_weights: Optional[np.ndarray] = None,
                                    **kwargs) -> np.ndarray:
        """
        Main optimization method using forecasted returns.
        
        Args:
            mean_forecast: Forecasted expected returns
            cov_matrix: Covariance matrix of returns
            method: Optimization method ('sharpe', 'mean_variance', 'risk_parity')
            previous_weights: Previous period weights
            **kwargs: Additional parameters for specific methods
            
        Returns:
            Optimal portfolio weights
        """
        logger.info(f"Portfolio optimization using {method} method")
        
        if method == 'sharpe':
            return self.sharpe_maximization(mean_forecast, cov_matrix, previous_weights)
        
        elif method == 'mean_variance':
            risk_aversion = kwargs.get('risk_aversion', 1.0)
            return self.mean_variance_optimization(mean_forecast, cov_matrix, 
                                                 risk_aversion, previous_weights)
        
        elif method == 'risk_parity':
            return self.risk_parity_optimization(cov_matrix)
        
        elif method == 'black_litterman':
            return self.black_litterman_optimization(mean_forecast, cov_matrix, **kwargs)
        
        else:
            raise ValueError(f"Unknown optimization method: {method}")
    
    def efficient_frontier(self, 
                         expected_returns: Union[pd.Series, np.ndarray],
                         cov_matrix: Union[pd.DataFrame, np.ndarray],
                         num_points: int = 50) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Generate efficient frontier points.
        
        Args:
            expected_returns: Expected returns for each asset
            cov_matrix: Covariance matrix
            num_points: Number of points on the frontier
            
        Returns:
            Tuple of (returns, volatilities, sharpe_ratios)
        """
        mu = np.array(expected_returns)
        sigma = np.array(cov_matrix)
        n_assets = len(mu)
        
        # Target return range
        min_ret = np.min(mu)
        max_ret = np.max(mu)
        target_returns = np.linspace(min_ret, max_ret, num_points)
        
        frontier_vols = []
        frontier_weights = []
        
        for target_ret in target_returns:
            # Minimize variance for target return
            w = cp.Variable(n_assets)
            
            objective = cp.quad_form(w, sigma)
            constraints = [
                cp.sum(w) == 1,
                mu.T @ w == target_ret,
                w >= self.min_weight,
                w <= self.max_weight
            ]
            
            problem = cp.Problem(cp.Minimize(objective), constraints)
            problem.solve(solver=cp.ECOS, verbose=False)
            
            if problem.status == cp.OPTIMAL:
                vol = np.sqrt(problem.value)
                frontier_vols.append(vol)
                frontier_weights.append(w.value)
            else:
                frontier_vols.append(np.nan)
                frontier_weights.append(np.full(n_assets, np.nan))
        
        frontier_vols = np.array(frontier_vols)
        frontier_sharpes = (target_returns - self.risk_free_rate) / frontier_vols
        
        logger.info(f"Generated efficient frontier with {num_points} points")
        return target_returns, frontier_vols, frontier_sharpes


def optimize_portfolio_forecasted(mean_forecast: Union[pd.Series, np.ndarray],
                                cov_matrix: Union[pd.DataFrame, np.ndarray],
                                method: str = 'sharpe',
                                **kwargs) -> np.ndarray:
    """
    Convenience function for portfolio optimization.
    
    Args:
        mean_forecast: Forecasted expected returns
        cov_matrix: Covariance matrix
        method: Optimization method
        **kwargs: Additional parameters
        
    Returns:
        Optimal portfolio weights
    """
    optimizer = PortfolioOptimizer(**kwargs)
    return optimizer.optimize_portfolio_forecasted(mean_forecast, cov_matrix, method)


if __name__ == "__main__":
    # Example usage
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from src.data_loader import load_data
    from src.feature_engineering import make_features
    from src.forecasting import forecast_returns_volatility
    
    # Load sample data
    tickers = ['AAPL', 'MSFT', 'SPY', 'QQQ']
    start_date = '2020-01-01'
    end_date = '2024-01-01'
    
    try:
        _, price_data = load_data(tickers, start_date, end_date)
        features = make_features(price_data)
        
        # Generate forecasts
        mean_forecast, vol_forecast = forecast_returns_volatility(
            features['returns'], auto_order=False, steps=1)
        
        # Get the next-period forecast
        next_returns = mean_forecast.iloc[0]
        cov_matrix = features['cov']
        
        # Initialize optimizer
        optimizer = PortfolioOptimizer(
            risk_free_rate=0.02,
            max_weight=0.4,
            min_weight=0.0,
            transaction_cost=0.001
        )
        
        print("Portfolio Optimization Results:")
        print(f"Assets: {tickers}")
        print(f"Forecasted returns: {next_returns.values}")
        
        # Test different optimization methods
        methods = ['sharpe', 'mean_variance', 'risk_parity']
        
        for method in methods:
            try:
                if method == 'mean_variance':
                    weights = optimizer.optimize_portfolio_forecasted(
                        next_returns, cov_matrix, method, risk_aversion=2.0)
                else:
                    weights = optimizer.optimize_portfolio_forecasted(
                        next_returns, cov_matrix, method)
                
                print(f"\n{method.upper()} Optimization:")
                for i, asset in enumerate(tickers):
                    print(f"  {asset}: {weights[i]:.3f}")
                
                if hasattr(optimizer, 'last_sharpe') and optimizer.last_sharpe:
                    print(f"  Expected Sharpe: {optimizer.last_sharpe:.3f}")
                
            except Exception as e:
                print(f"Error in {method} optimization: {e}")
        
        # Generate efficient frontier
        try:
            returns, vols, sharpes = optimizer.efficient_frontier(next_returns, cov_matrix, 20)
            max_sharpe_idx = np.nanargmax(sharpes)
            
            print(f"\nEfficient Frontier:")
            print(f"  Max Sharpe point - Return: {returns[max_sharpe_idx]:.4f}, "
                  f"Vol: {vols[max_sharpe_idx]:.4f}, Sharpe: {sharpes[max_sharpe_idx]:.3f}")
            
        except Exception as e:
            print(f"Error generating efficient frontier: {e}")
        
    except Exception as e:
        print(f"Error in example: {e}")
        print("Note: This example requires other modules to be working")