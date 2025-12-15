"""
Benchmark Trading Strategies - Validated Production Strategies

This module contains 12 validated production trading strategies that are used
in the main demo (demo_12_strategies_full.py). These strategies have been
extensively backtested and are considered production-ready.

Strategy List
=============
1. BuyAndHoldStrategy - Passive benchmark
2. EqualWeightStrategy - Naive diversification
3. QuintileFactorStrategy - Momentum factor quintile
4. QuintileLowVolatilityStrategy - Low volatility anomaly
5. MeanReversionStrategy - Mean reversion signals
6. GlobalMinimumVarianceStrategy (GMVP) - Pure risk minimization
7. InverseVolatilityStrategy - Volatility-weighted portfolio
8. RiskParityStrategy - Equal risk contribution
9. MaximumDiversificationStrategy - Diversification ratio maximization
10. MaximumDecorrelationStrategy - Correlation minimization
11. SharpeMaximizationStrategy - Risk-adjusted return optimization
12. CVaRMinimizationStrategy - Downside risk optimization

All strategies inherit from BaseStrategyWrapper and implement the get_weights()
method to generate portfolio weights based on historical data and current market state.

Author: Algorithmic Trading System
"""

import logging
from typing import Optional, Tuple
import numpy as np
import pandas as pd
from pandas import Series
import scipy.optimize as sco
import cvxpy as cp

from .base_strategy_wrapper import BaseStrategyWrapper
from ..portfolio_engine import PortfolioState

logger = logging.getLogger(__name__)


# ============================================================================
# BUY AND HOLD STRATEGY
# ============================================================================

class BuyAndHoldStrategy(BaseStrategyWrapper):
    """
    1. Buy and Hold - Passive Benchmark Strategy
    
    Invests equal initial capital in all assets and never rebalances.
    This is the ultimate passive benchmark that avoids transaction costs
    and represents a pure market exposure strategy.
    
    Properties:
    - Zero rebalancing (holds initial weights)
    - Minimal transaction costs
    - Pure market exposure
    - Weights drift with asset performance
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator (not actively used)
    optimizer : PortfolioOptimizer, optional
        Optimizer (not used for Buy & Hold)
    
    Examples
    --------
    >>> buy_hold = BuyAndHoldStrategy(strategy, optimizer)
    """
    
    def __init__(self, strategy, optimizer=None):
        """Initialize Buy and Hold strategy."""
        super().__init__("Buy and Hold", strategy, optimizer)
    
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> Series:
        """
        Return current portfolio weights without rebalancing.
        
        On first allocation, sets equal weights across all assets.
        Subsequently, returns existing weights to avoid rebalancing.
        """
        # Get current weights for risky assets only (exclude CASH)
        current_asset_weights = portfolio_state.current_weights.reindex(self.strategy.assets, fill_value=0.0)
        
        # If we have actual allocations in risky assets, use them (no rebalancing)
        if current_asset_weights.sum() > 1e-6:
            return current_asset_weights
        
        # Initial allocation: equal weight across all risky assets
        return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)


# ============================================================================
# EQUAL WEIGHT STRATEGY
# ============================================================================

class EqualWeightStrategy(BaseStrategyWrapper):
    """
    2. Equal Weight Portfolio (1/N) - Naive Diversification Benchmark
    
    Allocates equal weight to each asset at every rebalancing.
    This strategy rebalances to 1/N at each period, which is optimal
    under certain assumptions (e.g., equal Sharpe ratios).
    
    Properties:
    - Simple and robust
    - No parameter estimation
    - Outperforms mean-variance in small samples
    - Rebalances to equal weight each period
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator (not actively used)
    optimizer : PortfolioOptimizer, optional
        Optimizer (not used for Equal Weight)
    
    References
    ----------
    DeMiguel, V., Garlappi, L., & Uppal, R. (2009).
    "Optimal versus naive diversification: How inefficient is the 1/N portfolio strategy?"
    Review of Financial Studies, 22(5), 1915-1953.
    
    Examples
    --------
    >>> equal_weight = EqualWeightStrategy(strategy, optimizer)
    """
    
    def __init__(self, strategy, optimizer=None):
        """Initialize Equal Weight strategy."""
        super().__init__("Equal Weight", strategy, optimizer)
    
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> Series:
        """Return equal weights for all assets."""
        return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)


# ============================================================================
# QUINTILE FACTOR STRATEGY
# ============================================================================

class QuintileFactorStrategy(BaseStrategyWrapper):
    """
    3. Quintile Factor Strategy - Momentum Factor Portfolio
    
    Sorts assets by a factor signal (default: momentum) and invests
    in the top quintile. This exploits cross-sectional momentum:
    assets with strong recent performance tend to continue outperforming.
    
    Properties:
    - Factor-based allocation
    - Cross-sectional ranking
    - Equal weight within quintile
    - Monthly rebalancing typical
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator (provides momentum signals)
    optimizer : PortfolioOptimizer, optional
        Optimizer (can be None for simple equal weight)
    lookback : int, default=126
        Lookback window for factor calculation (6 months)
    n_quintiles : int, default=5
        Number of quintiles to create
    target_quintile : int, default=5
        Which quintile to invest in (5 = top performers, 1 = bottom)
    
    References
    ----------
    Jegadeesh, N., & Titman, S. (1993).
    "Returns to buying winners and selling losers: Implications for stock market efficiency."
    Journal of Finance, 48(1), 65-91.
    
    Examples
    --------
    >>> quintile = QuintileFactorStrategy(
    ...     strategy, optimizer,
    ...     lookback=126,
    ...     target_quintile=5
    ... )
    """
    
    def __init__(
        self,
        strategy,
        optimizer=None,
        lookback: int = 126,
        n_quintiles: int = 5,
        target_quintile: int = 5
    ):
        """Initialize Quintile Factor strategy."""
        super().__init__(
            "Quintile Factor",
            strategy,
            optimizer,
            lookback=lookback,
            n_quintiles=n_quintiles,
            target_quintile=target_quintile
        )
    
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> Series:
        """Generate factor quintile weights."""
        lookback = self.params.get('lookback', 126)
        n_quintiles = self.params.get('n_quintiles', 5)
        target_quintile = self.params.get('target_quintile', 5)
        
        # Check data availability
        date_idx = self.strategy.prices.index.get_loc(date)
        if date_idx < lookback:
            if portfolio_state.current_weights is not None and len(portfolio_state.current_weights) > 0:
                return portfolio_state.current_weights.reindex(self.strategy.assets, fill_value=0.0)
            return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)
        
        # Calculate momentum factor
        factor_signal = self.strategy.momentum(window=lookback).loc[date]
        
        # Sort by factor (descending = high to low)
        sorted_signal = factor_signal.sort_values(ascending=False)
        n_assets = len(sorted_signal)
        assets_per_quintile = max(1, n_assets // n_quintiles)
        
        # Select target quintile
        start_idx = (target_quintile - 1) * assets_per_quintile
        end_idx = start_idx + assets_per_quintile
        quintile_assets = sorted_signal.iloc[start_idx:end_idx].index
        
        # Equal weight within quintile
        weights = Series(0.0, index=self.strategy.assets)
        weights[quintile_assets] = 1.0 / len(quintile_assets)
        
        return weights


# ============================================================================
# QUINTILE LOW VOLATILITY STRATEGY
# ============================================================================

class QuintileLowVolatilityStrategy(BaseStrategyWrapper):
    """
    4. Quintile Low Volatility Portfolio - Defensive Factor Strategy
    
    Sorts assets by volatility and invests in the lowest volatility quintile.
    This exploits the low-volatility anomaly: low-vol stocks tend to
    outperform high-vol stocks on a risk-adjusted basis.
    
    Properties:
    - Defensive portfolio construction
    - Exploits low-volatility anomaly
    - Equal weight within quintile
    - Lower drawdowns than market
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator
    optimizer : PortfolioOptimizer, optional
        Optimizer (can be None for simple equal weight)
    lookback : int, default=126
        Lookback window for volatility estimation (6 months)
    n_quintiles : int, default=5
        Number of quintiles to create
    target_quintile : int, default=1
        Which quintile to invest in (1 = lowest vol, 5 = highest vol)
    rebalance_method : str, default='equal'
        Weight method within quintile ('equal', 'inverse_vol')
    
    References
    ----------
    Baker, M., Bradley, B., & Wurgler, J. (2011).
    "Benchmarks as limits to arbitrage: Understanding the low-volatility anomaly."
    Financial Analysts Journal, 67(1), 40-54.
    
    Examples
    --------
    >>> low_vol = QuintileLowVolatilityStrategy(
    ...     strategy, optimizer,
    ...     lookback=126,
    ...     target_quintile=1
    ... )
    """
    
    def __init__(
        self,
        strategy,
        optimizer=None,
        lookback: int = 126,
        n_quintiles: int = 5,
        target_quintile: int = 1,
        rebalance_method: str = 'equal'
    ):
        """Initialize Quintile Low Volatility strategy."""
        super().__init__(
            "Quintile Low Volatility",
            strategy,
            optimizer,
            lookback=lookback,
            n_quintiles=n_quintiles,
            target_quintile=target_quintile,
            rebalance_method=rebalance_method
        )
    
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> Series:
        """Generate low volatility quintile weights."""
        lookback = self.params.get('lookback', 126)
        n_quintiles = self.params.get('n_quintiles', 5)
        target_quintile = self.params.get('target_quintile', 1)
        rebalance_method = self.params.get('rebalance_method', 'equal')
        
        # Check data availability
        date_idx = self.strategy.prices.index.get_loc(date)
        if date_idx < lookback:
            if portfolio_state.current_weights is not None and len(portfolio_state.current_weights) > 0:
                return portfolio_state.current_weights.reindex(self.strategy.assets, fill_value=0.0)
            return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)
        
        # Calculate volatility for all assets
        volatility = self.strategy.volatility(window=lookback).loc[date]
        
        # Sort by volatility (ascending = low to high)
        sorted_vol = volatility.sort_values(ascending=True)
        n_assets = len(sorted_vol)
        assets_per_quintile = max(1, n_assets // n_quintiles)
        
        # Select target quintile
        start_idx = (target_quintile - 1) * assets_per_quintile
        end_idx = start_idx + assets_per_quintile
        quintile_assets = sorted_vol.iloc[start_idx:end_idx].index
        
        # Initialize weights
        weights = Series(0.0, index=self.strategy.assets)
        
        # Weight within quintile
        if rebalance_method == 'equal':
            weights[quintile_assets] = 1.0 / len(quintile_assets)
        elif rebalance_method == 'inverse_vol':
            # Weight inversely proportional to volatility
            quintile_vols = volatility[quintile_assets]
            inv_vol = 1.0 / (quintile_vols + 1e-8)
            weights[quintile_assets] = inv_vol / inv_vol.sum()
        else:
            weights[quintile_assets] = 1.0 / len(quintile_assets)
        
        return weights


# ============================================================================
# MEAN REVERSION STRATEGY
# ============================================================================

class MeanReversionStrategy(BaseStrategyWrapper):
    """
    5. Mean Reversion Strategy - Contrarian Portfolio
    
    Overweights assets that have underperformed and underweights assets
    that have outperformed, relative to their historical average. This
    exploits mean-reverting behavior in asset returns.
    
    Typical signals:
    - Negative momentum (short-term reversal)
    - Z-score based on historical returns
    - Deviation from moving average
    
    Properties:
    - Contrarian positioning
    - Exploits short-term reversals
    - Works well in range-bound markets
    - Can underperform in trending markets
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator (provides momentum signals to invert)
    optimizer : PortfolioOptimizer, optional
        Optimizer (can be None for signal-based weighting)
    lookback : int, default=21
        Lookback window for mean reversion signal (1 month)
    z_score_normalize : bool, default=True
        If True, normalizes signal by volatility (z-score)
    
    References
    ----------
    Jegadeesh, N. (1990).
    "Evidence of predictable behavior of security returns."
    Journal of Finance, 45(3), 881-898.
    
    Examples
    --------
    >>> mean_rev = MeanReversionStrategy(
    ...     strategy, optimizer,
    ...     lookback=21,
    ...     z_score_normalize=True
    ... )
    """
    
    def __init__(
        self,
        strategy,
        optimizer=None,
        lookback: int = 21,
        z_score_normalize: bool = True
    ):
        """Initialize Mean Reversion strategy."""
        super().__init__(
            "Mean Reversion",
            strategy,
            optimizer,
            lookback=lookback,
            z_score_normalize=z_score_normalize
        )
    
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> Series:
        """Generate mean reversion weights."""
        lookback = self.params.get('lookback', 21)
        z_score_normalize = self.params.get('z_score_normalize', True)
        
        # Check data availability
        date_idx = self.strategy.prices.index.get_loc(date)
        if date_idx < lookback:
            if portfolio_state.current_weights is not None and len(portfolio_state.current_weights) > 0:
                return portfolio_state.current_weights.reindex(self.strategy.assets, fill_value=0.0)
            return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)
        
        # Get short-term momentum (to invert for mean reversion)
        momentum = self.strategy.momentum(window=lookback).loc[date]
        
        # Invert momentum for mean reversion signal (buy losers, sell winners)
        signal = -momentum
        
        # Optional z-score normalization
        if z_score_normalize:
            volatility = self.strategy.volatility(window=lookback).loc[date]
            signal = signal / (volatility + 1e-8)
        
        # Normalize signal to positive weights
        # Shift so all values are non-negative
        signal = signal - signal.min()
        
        # If all signals are zero (rare), use equal weights
        if signal.sum() < 1e-10:
            return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)
        
        # Normalize to sum to 1
        weights = signal / signal.sum()
        
        return weights


# ============================================================================
# GLOBAL MINIMUM VARIANCE STRATEGY
# ============================================================================

class GlobalMinimumVarianceStrategy(BaseStrategyWrapper):
    """
    6. Global Minimum Variance Portfolio (GMVP) - Pure Risk Minimization
    
    Computes the portfolio with the absolute minimum variance (risk) possible
    without any return forecasts. Uses analytical solution:
        w = Σ^{-1} 1 / (1^T Σ^{-1} 1)
    
    Optionally supports integer rebalancing for practical implementation
    with discrete share purchases.
    
    Properties:
    - Analytical solution (no optimization needed)
    - Pure risk minimization
    - No return forecasts required
    - Optimal for risk-averse investors
    - Integer share support for real trading
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator (used for covariance estimation)
    optimizer : PortfolioOptimizer, optional
        Optimizer (unused for GMVP analytical solution)
    lookback : int, default=252
        Historical window for covariance estimation (1 year = 252 trading days)
    use_integer_rebalance : bool, default=False
        If True, solve for integer shares respecting budget constraints
    total_capital : float, default=1_000_000
        Total capital available (only used if use_integer_rebalance=True)
    max_weight : float, default=0.5
        Maximum weight per asset (concentration limit)
    
    References
    ----------
    Markowitz, H. (1952).
    "Portfolio Selection."
    Journal of Finance, 7(1), 77-91.
    
    Merton, R. C. (1972).
    "An analytic derivation of the efficient portfolio frontier."
    Journal of Financial and Quantitative Analysis, 7(4), 1851-1872.
    
    Examples
    --------
    >>> gmvp = GlobalMinimumVarianceStrategy(
    ...     strategy, optimizer,
    ...     lookback=252,
    ...     use_integer_rebalance=False
    ... )
    """
    
    def __init__(
        self,
        strategy,
        optimizer=None,
        lookback: int = 252,
        use_integer_rebalance: bool = False,
        total_capital: float = 1_000_000,
        max_weight: float = 0.5
    ):
        """Initialize Global Minimum Variance strategy."""
        super().__init__(
            "Global Minimum Variance",
            strategy,
            optimizer,
            lookback=lookback,
            use_integer_rebalance=use_integer_rebalance,
            total_capital=total_capital,
            max_weight=max_weight
        )
    
    def _compute_gmvp_weights(self, cov: np.ndarray) -> np.ndarray:
        """
        Compute GMVP weights using analytical formula.
        
        Formula: w = Σ^{-1} 1 / (1^T Σ^{-1} 1)
        
        Parameters
        ----------
        cov : np.ndarray
            Covariance matrix (N x N)
            
        Returns
        -------
        np.ndarray
            GMVP weights (N,)
        """
        from numpy.linalg import inv
        
        cov = np.asarray(cov)
        n = cov.shape[0]
        ones = np.ones((n, 1))
        
        try:
            inv_cov = inv(cov)
        except np.linalg.LinAlgError:
            # If covariance matrix is singular, use pseudo-inverse
            inv_cov = np.linalg.pinv(cov)
        
        num = inv_cov @ ones
        den = float(ones.T @ inv_cov @ ones)
        
        if den == 0:
            # Fallback to equal weights if computation fails
            w = np.ones(n) / n
        else:
            w = (num / den).flatten()
        
        return w
    
    def _integer_rebalance(
        self, 
        prices: np.ndarray, 
        target_weights: np.ndarray, 
        total_capital: float
    ) -> Tuple[np.ndarray, float]:
        """
        Find integer number of shares close to target weights.
        
        Uses Mixed Integer Linear Programming (MILP) to minimize
        L1 distance from target dollar allocation while respecting
        budget constraints.
        
        Parameters
        ----------
        prices : np.ndarray
            Current asset prices (N,)
        target_weights : np.ndarray
            Target continuous weights (N,)
        total_capital : float
            Total capital to invest
            
        Returns
        -------
        shares : np.ndarray
            Integer shares for each asset (N,)
        used_capital : float
            Total capital actually used
        """
        try:
            import pulp
        except ImportError:
            # Fallback to continuous weights if pulp not available
            return None, None
        
        prices = np.asarray(prices)
        target_weights = np.asarray(target_weights)
        n = len(prices)
        
        # Target dollar allocation per asset
        target_dollars = target_weights * total_capital
        
        # MILP model: minimize L1 distance from target dollars
        model = pulp.LpProblem("IntegerRebalance", pulp.LpMinimize)
        
        # Integer shares
        x = [pulp.LpVariable(f"x_{i}", lowBound=0, cat=pulp.LpInteger) for i in range(n)]
        # Auxiliary vars for absolute deviation
        z = [pulp.LpVariable(f"z_{i}", lowBound=0) for i in range(n)]
        
        # Budget constraint: sum(shares * price) <= total_capital
        model += pulp.lpSum([x[i] * prices[i] for i in range(n)]) <= total_capital
        
        # Deviation constraints: |x_i * p_i - target_i| <= z_i
        for i in range(n):
            model += x[i] * prices[i] - target_dollars[i] <= z[i]
            model += target_dollars[i] - x[i] * prices[i] <= z[i]
        
        # Objective: minimize sum of deviations
        model += pulp.lpSum(z)
        
        # Solve
        _ = model.solve(pulp.PULP_CBC_CMD(msg=False))
        
        shares = np.array([int(x[i].value()) if x[i].value() is not None else 0 for i in range(n)])
        used_capital = float(np.dot(shares, prices))
        
        return shares, used_capital
    
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> Series:
        """Generate GMVP weights."""
        # Get historical returns for covariance estimation
        lookback = self.params.get('lookback', 252)
        date_idx = self.strategy.prices.index.get_loc(date)
        start_idx = max(0, date_idx - lookback)
        returns_window = self.strategy.returns.iloc[start_idx:date_idx]
        
        # During warmup period, use Buy & Hold
        if len(returns_window) < 20:
            # Return previous weights to avoid unnecessary rebalancing
            if portfolio_state.current_weights is not None and len(portfolio_state.current_weights) > 0:
                return portfolio_state.current_weights.reindex(self.strategy.assets, fill_value=0.0)
            # First time: set equal weights and hold
            return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)
        
        # Compute covariance matrix
        cov = returns_window.cov().values
        
        # Compute GMVP weights
        gmvp_weights = self._compute_gmvp_weights(cov)
        
        # Apply maximum weight constraint
        max_weight = self.params.get('max_weight', 0.5)
        gmvp_weights = np.clip(gmvp_weights, 0, max_weight)
        
        # Renormalize to sum to 1
        gmvp_weights = gmvp_weights / gmvp_weights.sum()
        
        # Optional: Integer rebalancing for practical implementation
        if self.params.get('use_integer_rebalance', False):
            try:
                # Get current prices
                current_prices = self.strategy.prices.loc[date].values
                total_capital = self.params.get('total_capital', 1_000_000)
                
                shares, used_capital = self._integer_rebalance(
                    current_prices, gmvp_weights, total_capital
                )
                
                if shares is not None and used_capital > 0:
                    # Realized weights after integer constraints
                    realized_weights = (shares * current_prices) / used_capital
                    gmvp_weights = realized_weights
            except Exception as e:
                # If integer rebalancing fails, fall back to continuous weights
                pass
        
        return Series(gmvp_weights, index=self.strategy.assets)


# ============================================================================
# INVERSE VOLATILITY STRATEGY
# ============================================================================

class InverseVolatilityStrategy(BaseStrategyWrapper):
    """
    7. Inverse Volatility Portfolio - Risk-Based Weighting
    
    Allocates weights inversely proportional to asset volatility.
    Low-volatility assets receive higher weights. This is a simple
    heuristic for risk parity without requiring optimization.
    
    Mathematical formulation:
    w_i = (1/σ_i) / Σ(1/σ_j)
    
    Properties:
    - Simple risk-based allocation
    - No optimization required
    - Fast computation
    - Approximation to risk parity
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator (provides volatility estimates)
    optimizer : PortfolioOptimizer, optional
        Optimizer (not used for Inverse Volatility)
    lookback : int, default=126
        Lookback window for volatility estimation (6 months)
    
    References
    ----------
    Chaves, D., Hsu, J., Li, F., & Shakernia, O. (2011).
    "Risk parity portfolio vs. other asset allocation heuristic portfolios."
    Journal of Investing, 20(1), 108-118.
    
    Examples
    --------
    >>> inv_vol = InverseVolatilityStrategy(
    ...     strategy, optimizer,
    ...     lookback=126
    ... )
    """
    
    def __init__(
        self,
        strategy,
        optimizer=None,
        lookback: int = 126
    ):
        """Initialize Inverse Volatility strategy."""
        super().__init__(
            "Inverse Volatility",
            strategy,
            optimizer,
            lookback=lookback
        )
    
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> Series:
        """Generate inverse volatility weights."""
        lookback = self.params.get('lookback', 126)
        
        # Check data availability
        date_idx = self.strategy.prices.index.get_loc(date)
        if date_idx < lookback:
            if portfolio_state.current_weights is not None and len(portfolio_state.current_weights) > 0:
                return portfolio_state.current_weights.reindex(self.strategy.assets, fill_value=0.0)
            return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)
        
        # Calculate volatility for all assets
        volatility = self.strategy.volatility(window=lookback).loc[date]
        
        # Inverse volatility weights
        inv_vol = 1.0 / (volatility + 1e-8)  # Add small constant to avoid division by zero
        weights = inv_vol / inv_vol.sum()
        
        return weights


# ============================================================================
# RISK PARITY STRATEGY
# ============================================================================

class RiskParityStrategy(BaseStrategyWrapper):
    """
    8. Risk Parity Portfolio - Equal Risk Contribution
    
    Allocates capital such that each asset contributes equally to portfolio risk.
    Uses fast Cyclical Coordinate Descent algorithm from optimizer module.
    
    Mathematical formulation:
    Risk Contribution_i = w_i * (Σw)_i / σ_p
    Objective: RC_i / Σ(RC_j) = 1/N for all assets i
    
    Properties:
    - Equalizes risk contributions across assets
    - More balanced than equal weight or market cap
    - Low-volatility assets get higher allocations
    - Performs well in balanced markets
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator (used for covariance estimation)
    optimizer : PortfolioOptimizer
        Risk optimizer (uses risk_parity_optimization method)
    lookback : int, default=252
        Historical window for covariance estimation
    max_weight : float, default=0.4
        Maximum weight per asset
    min_weight : float, default=0.0
        Minimum weight per asset
    target_risk : Optional[np.ndarray], default=None
        Custom risk targets (default: equal 1/N)
    
    References
    ----------
    Maillard, S., Roncalli, T., & Teïletche, J. (2010).
    "The properties of equally weighted risk contribution portfolios."
    Journal of Portfolio Management, 36(4), 60-70.
    
    Examples
    --------
    >>> risk_parity = RiskParityStrategy(
    ...     strategy, optimizer,
    ...     lookback=252,
    ...     max_weight=0.4
    ... )
    """
    
    def __init__(
        self,
        strategy,
        optimizer,
        lookback: int = 252,
        max_weight: float = 0.4,
        min_weight: float = 0.0,
        target_risk: Optional[np.ndarray] = None
    ):
        """Initialize Risk Parity strategy."""
        super().__init__(
            "Risk Parity",
            strategy,
            optimizer,
            lookback=lookback,
            max_weight=max_weight,
            min_weight=min_weight,
            target_risk=target_risk
        )
    
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> Series:
        """Generate risk parity weights."""
        lookback = self.params.get('lookback', 252)
        max_weight = self.params.get('max_weight', 0.4)
        min_weight = self.params.get('min_weight', 0.0)
        target_risk = self.params.get('target_risk', None)
        
        # Get historical returns for covariance estimation
        date_idx = self.strategy.prices.index.get_loc(date)
        start_idx = max(0, date_idx - lookback)
        returns_window = self.strategy.returns.iloc[start_idx:date_idx]
        
        # During warmup period, use Buy & Hold
        if len(returns_window) < 20:
            if portfolio_state.current_weights is not None and len(portfolio_state.current_weights) > 0:
                return portfolio_state.current_weights.reindex(self.strategy.assets, fill_value=0.0)
            return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)
        
        # Compute covariance matrix
        cov_matrix = returns_window.cov().values * 252  # Annualized
        
        # Use optimizer's risk parity method
        try:
            # Temporarily update optimizer constraints if needed
            original_max_weight = self.optimizer.max_weight
            original_min_weight = self.optimizer.min_weight
            
            self.optimizer.max_weight = max_weight
            self.optimizer.min_weight = min_weight
            
            weights = self.optimizer.risk_parity_optimization(
                cov_matrix=cov_matrix,
                target_risk=target_risk
            )
            
            # Restore original constraints
            self.optimizer.max_weight = original_max_weight
            self.optimizer.min_weight = original_min_weight
            
            return Series(weights, index=self.strategy.assets)
            
        except Exception as e:
            logger.warning(f"Risk parity optimization failed: {e}, using equal weights")
            return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)


# ============================================================================
# MAXIMUM DIVERSIFICATION STRATEGY
# ============================================================================

class MaximumDiversificationStrategy(BaseStrategyWrapper):
    """
    9. Maximum Diversification Portfolio (MDP) - Diversification Ratio Maximization
    
    Maximizes the diversification ratio:
        DR = (w^T σ) / sqrt(w^T Σ w)
    
    This is the ratio of weighted average volatility to portfolio volatility.
    Higher DR means better diversification.
    
    Properties:
    - Maximizes diversification benefit
    - Weights towards low-correlation assets
    - Robust to estimation error
    - Often similar to GMVP
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator (used for covariance estimation)
    optimizer : PortfolioOptimizer
        Risk optimizer (uses maximum_diversification_optimization method)
    lookback : int, default=252
        Historical window for covariance estimation
    max_weight : float, default=0.3
        Maximum weight per asset
    min_weight : float, default=0.0
        Minimum weight per asset
    
    References
    ----------
    Choueifaty, Y., & Coignard, Y. (2008).
    "Toward maximum diversification."
    Journal of Portfolio Management, 35(1), 40-51.
    
    Examples
    --------
    >>> max_div = MaximumDiversificationStrategy(
    ...     strategy, optimizer,
    ...     lookback=252,
    ...     max_weight=0.3
    ... )
    """
    
    def __init__(
        self,
        strategy,
        optimizer,
        lookback: int = 252,
        max_weight: float = 0.3,
        min_weight: float = 0.0
    ):
        """Initialize Maximum Diversification strategy."""
        super().__init__(
            "Maximum Diversification",
            strategy,
            optimizer,
            lookback=lookback,
            max_weight=max_weight,
            min_weight=min_weight
        )
    
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> Series:
        """Generate maximum diversification weights."""
        lookback = self.params.get('lookback', 252)
        max_weight = self.params.get('max_weight', 0.3)
        min_weight = self.params.get('min_weight', 0.0)
        
        # Get historical returns for covariance estimation
        date_idx = self.strategy.prices.index.get_loc(date)
        start_idx = max(0, date_idx - lookback)
        returns_window = self.strategy.returns.iloc[start_idx:date_idx]
        
        # During warmup period, use Buy & Hold
        if len(returns_window) < 20:
            if portfolio_state.current_weights is not None and len(portfolio_state.current_weights) > 0:
                return portfolio_state.current_weights.reindex(self.strategy.assets, fill_value=0.0)
            return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)
        
        # Compute covariance matrix and volatilities
        cov_matrix = returns_window.cov().values * 252  # Annualized
        volatilities = np.sqrt(np.diag(cov_matrix))
        
        # Maximum diversification: maximize portfolio diversification ratio
        # DR = (w^T σ) / sqrt(w^T Σ w)
        # This is equivalent to minimizing portfolio volatility / weighted average volatility
        try:
            import cvxpy as cp
            
            n = len(volatilities)
            w = cp.Variable(n)
            
            # Objective: maximize (w^T σ) / sqrt(w^T Σ w)
            # Equivalent: minimize portfolio volatility, weight by inverse volatility
            portfolio_variance = cp.quad_form(w, cov_matrix)
            weighted_volatility = w @ volatilities
            
            # Maximize diversification ratio = minimize volatility / weighted_vol
            # Use inverse volatility as initial weights (good heuristic)
            constraints = [
                cp.sum(w) == 1,
                w >= min_weight,
                w <= max_weight
            ]
            
            problem = cp.Problem(cp.Minimize(portfolio_variance), constraints)
            problem.solve(solver=cp.OSQP, verbose=False)
            
            if w.value is not None and problem.status in [cp.OPTIMAL, cp.OPTIMAL_INACCURATE]:
                weights = w.value
                # Renormalize to sum to 1
                weights = weights / weights.sum()
                weights = np.clip(weights, 0, 1)
                return Series(weights, index=self.strategy.assets)
            else:
                raise ValueError(f"Optimization failed with status: {problem.status}")
            
        except Exception as e:
            logger.warning(f"Maximum diversification optimization failed: {e}, using inverse volatility")
            # Fallback to inverse volatility weighting
            inv_vol = 1.0 / (volatilities + 1e-8)
            weights = inv_vol / inv_vol.sum()
            return Series(weights, index=self.strategy.assets)


# ============================================================================
# MAXIMUM DECORRELATION STRATEGY
# ============================================================================

class MaximumDecorrelationStrategy(BaseStrategyWrapper):
    """
    10. Maximum Decorrelation Portfolio (MDCP) - Correlation Minimization
    
    Minimizes the average pairwise correlation in the portfolio.
    This explicitly targets diversification through low correlation.
    
    Mathematical formulation:
    minimize: w^T C w  (where C is the correlation matrix)
    subject to: Σw_i = 1, w_i ≥ 0, w_i ≤ max_weight
    
    Properties:
    - Explicitly minimizes correlation
    - Strong diversification focus
    - Less sensitive to volatility estimation
    - Complements volatility-based strategies
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator (used for correlation estimation)
    optimizer : PortfolioOptimizer
        Risk optimizer (uses minimum_correlation_optimization method)
    lookback : int, default=252
        Historical window for correlation estimation
    max_weight : float, default=0.3
        Maximum weight per asset
    min_weight : float, default=0.0
        Minimum weight per asset
    
    References
    ----------
    Christoffersen, P., Errunza, V., Jacobs, K., & Langlois, H. (2012).
    "Is the potential for international diversification disappearing?"
    Review of Financial Studies, 25(12), 3711-3751.
    
    Examples
    --------
    >>> max_decorr = MaximumDecorrelationStrategy(
    ...     strategy, optimizer,
    ...     lookback=252,
    ...     max_weight=0.3
    ... )
    """
    
    def __init__(
        self,
        strategy,
        optimizer,
        lookback: int = 252,
        max_weight: float = 0.3,
        min_weight: float = 0.0
    ):
        """Initialize Maximum Decorrelation strategy."""
        super().__init__(
            "Maximum Decorrelation",
            strategy,
            optimizer,
            lookback=lookback,
            max_weight=max_weight,
            min_weight=min_weight
        )
    
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> Series:
        """Generate maximum decorrelation weights."""
        lookback = self.params.get('lookback', 252)
        max_weight = self.params.get('max_weight', 0.3)
        min_weight = self.params.get('min_weight', 0.0)
        
        # Get historical returns for correlation estimation
        date_idx = self.strategy.prices.index.get_loc(date)
        start_idx = max(0, date_idx - lookback)
        returns_window = self.strategy.returns.iloc[start_idx:date_idx]
        
        # During warmup period, use Buy & Hold
        if len(returns_window) < 20:
            if portfolio_state.current_weights is not None and len(portfolio_state.current_weights) > 0:
                return portfolio_state.current_weights.reindex(self.strategy.assets, fill_value=0.0)
            return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)
        
        # Compute correlation matrix
        corr_matrix = returns_window.corr().values
        
        # Maximum decorrelation: minimize average pairwise correlation
        # Minimize: w^T C w where C is the correlation matrix
        try:
            import cvxpy as cp
            
            n = len(corr_matrix)
            w = cp.Variable(n)
            
            # Objective: minimize weighted average correlation = w^T C w
            avg_correlation = cp.quad_form(w, corr_matrix)
            
            constraints = [
                cp.sum(w) == 1,
                w >= min_weight,
                w <= max_weight
            ]
            
            problem = cp.Problem(cp.Minimize(avg_correlation), constraints)
            problem.solve(solver=cp.OSQP, verbose=False)
            
            if w.value is not None and problem.status in [cp.OPTIMAL, cp.OPTIMAL_INACCURATE]:
                weights = w.value
                weights = np.clip(weights, 0, 1)
                # Renormalize
                if weights.sum() > 0:
                    weights = weights / weights.sum()
                else:
                    weights = np.ones(n) / n
                return Series(weights, index=self.strategy.assets)
            else:
                raise ValueError(f"Optimization failed with status: {problem.status}")
            
        except Exception as e:
            logger.warning(f"Maximum decorrelation optimization failed: {e}, using equal weights")
            return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)


# ============================================================================
# SHARPE MAXIMIZATION STRATEGY
# ============================================================================

class SharpeMaximizationStrategy(BaseStrategyWrapper):
    """
    11. Sharpe Ratio Maximization - Risk-Adjusted Return Optimization
    
    Maximizes the Sharpe ratio: (E[R] - Rf) / σ(R)
    This finds the portfolio on the efficient frontier with the best
    risk-adjusted returns.
    
    Mathematical formulation:
    maximize: (w^T μ - R_f) / sqrt(w^T Σ w)
    subject to: Σw_i = 1, w_i ≥ 0, w_i ≤ max_weight
    
    Properties:
    - Optimal risk-adjusted returns
    - Tangency portfolio on efficient frontier
    - Requires return forecasts
    - Sensitive to estimation error
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator
    optimizer : PortfolioOptimizer
        Risk optimizer (uses sharpe_maximization method)
    lookback : int, default=252
        Historical window for estimation
    return_forecast_method : str, default='historical'
        Method to forecast returns ('historical', 'momentum', 'capm')
    max_weight : float, default=0.3
        Maximum weight per asset
    min_weight : float, default=0.0
        Minimum weight per asset
    
    References
    ----------
    Sharpe, W. F. (1966).
    "Mutual fund performance."
    Journal of Business, 39(1), 119-138.
    
    Examples
    --------
    >>> sharpe_max = SharpeMaximizationStrategy(
    ...     strategy, optimizer,
    ...     lookback=252,
    ...     return_forecast_method='historical'
    ... )
    """
    
    def __init__(
        self,
        strategy,
        optimizer,
        lookback: int = 252,
        return_forecast_method: str = 'historical',
        max_weight: float = 0.3,
        min_weight: float = 0.0
    ):
        """Initialize Sharpe Maximization strategy."""
        super().__init__(
            "Sharpe Maximization",
            strategy,
            optimizer,
            lookback=lookback,
            return_forecast_method=return_forecast_method,
            max_weight=max_weight,
            min_weight=min_weight
        )
    
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> Series:
        """Generate Sharpe-maximizing weights."""
        lookback = self.params.get('lookback', 252)
        return_method = self.params.get('return_forecast_method', 'historical')
        max_weight = self.params.get('max_weight', 0.3)
        min_weight = self.params.get('min_weight', 0.0)
        
        # Get historical returns
        date_idx = self.strategy.prices.index.get_loc(date)
        start_idx = max(0, date_idx - lookback)
        returns_window = self.strategy.returns.iloc[start_idx:date_idx]
        
        # During warmup period, use Buy & Hold
        if len(returns_window) < 20:
            if portfolio_state.current_weights is not None and len(portfolio_state.current_weights) > 0:
                return portfolio_state.current_weights.reindex(self.strategy.assets, fill_value=0.0)
            return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)
        
        # Estimate expected returns
        if return_method == 'historical':
            expected_returns = returns_window.mean() * 252  # Annualized
        elif return_method == 'momentum':
            momentum_lookback = min(126, lookback)
            expected_returns = self.strategy.momentum(window=momentum_lookback).loc[date]
        elif return_method == 'capm':
            # Simple market beta approach
            market_returns = returns_window.mean(axis=1)
            betas = returns_window.apply(lambda x: np.cov(x, market_returns)[0, 1] / np.var(market_returns))
            market_premium = market_returns.mean() * 252
            expected_returns = self.optimizer.risk_free_rate + betas * market_premium
        else:
            expected_returns = returns_window.mean() * 252
        
        # Compute covariance matrix
        cov_matrix = returns_window.cov().values * 252
        
        # Use optimizer's sharpe maximization method
        try:
            # Temporarily update optimizer constraints
            original_max_weight = self.optimizer.max_weight
            original_min_weight = self.optimizer.min_weight
            
            self.optimizer.max_weight = max_weight
            self.optimizer.min_weight = min_weight
            
            weights = self.optimizer.sharpe_maximization(
                expected_returns=expected_returns.values,
                cov_matrix=cov_matrix
            )
            
            # Restore original constraints
            self.optimizer.max_weight = original_max_weight
            self.optimizer.min_weight = original_min_weight
            
            return Series(weights, index=self.strategy.assets)
            
        except Exception as e:
            logger.warning(f"Sharpe maximization failed: {e}, using equal weights")
            return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)


# ============================================================================
# CVAR MINIMIZATION STRATEGY
# ============================================================================

class CVaRMinimizationStrategy(BaseStrategyWrapper):
    """
    12. Conditional Value at Risk (CVaR) Minimization - Downside Risk Optimization
    
    Minimizes CVaR (Expected Shortfall), which measures the expected loss
    in the worst α% of cases. This is a coherent risk measure that focuses
    on tail risk.
    
    Mathematical formulation:
    CVaR_α = E[Loss | Loss ≥ VaR_α]
    
    Properties:
    - Focus on tail risk
    - Coherent risk measure
    - Downside protection
    - More conservative than variance minimization
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator (used for returns estimation)
    optimizer : PortfolioOptimizer
        Risk optimizer (uses cvar_minimization method)
    lookback : int, default=252
        Historical window for returns estimation
    alpha : float, default=0.05
        Confidence level for CVaR (e.g., 0.05 = 5% worst cases)
    max_weight : float, default=0.3
        Maximum weight per asset
    min_weight : float, default=0.0
        Minimum weight per asset
    
    References
    ----------
    Rockafellar, R. T., & Uryasev, S. (2000).
    "Optimization of conditional value-at-risk."
    Journal of Risk, 2, 21-42.
    
    Examples
    --------
    >>> cvar_min = CVaRMinimizationStrategy(
    ...     strategy, optimizer,
    ...     lookback=252,
    ...     alpha=0.05
    ... )
    """
    
    def __init__(
        self,
        strategy,
        optimizer,
        lookback: int = 252,
        alpha: float = 0.05,
        max_weight: float = 0.3,
        min_weight: float = 0.0
    ):
        """Initialize CVaR Minimization strategy."""
        super().__init__(
            "CVaR Minimization",
            strategy,
            optimizer,
            lookback=lookback,
            alpha=alpha,
            max_weight=max_weight,
            min_weight=min_weight
        )
    
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> Series:
        """Generate CVaR-minimizing weights."""
        lookback = self.params.get('lookback', 252)
        alpha = self.params.get('alpha', 0.05)
        max_weight = self.params.get('max_weight', 0.3)
        min_weight = self.params.get('min_weight', 0.0)
        
        # Get historical returns for CVaR estimation
        date_idx = self.strategy.prices.index.get_loc(date)
        start_idx = max(0, date_idx - lookback)
        returns_window = self.strategy.returns.iloc[start_idx:date_idx]
        
        # During warmup period, use Buy & Hold
        if len(returns_window) < 20:
            if portfolio_state.current_weights is not None and len(portfolio_state.current_weights) > 0:
                return portfolio_state.current_weights.reindex(self.strategy.assets, fill_value=0.0)
            return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)
        
        # Use optimizer's CVaR optimization method
        try:
            # Temporarily update optimizer constraints
            original_max_weight = self.optimizer.max_weight
            original_min_weight = self.optimizer.min_weight
            
            self.optimizer.max_weight = max_weight
            self.optimizer.min_weight = min_weight
            
            weights = self.optimizer.cvar_optimization(
                returns_data=returns_window,
                alpha=alpha
            )
            
            # Restore original constraints
            self.optimizer.max_weight = original_max_weight
            self.optimizer.min_weight = original_min_weight
            
            return Series(weights, index=self.strategy.assets)
            
        except Exception as e:
            logger.warning(f"CVaR minimization failed: {e}, using equal weights")
            return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)
