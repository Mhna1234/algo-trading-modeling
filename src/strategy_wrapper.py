"""
Strategy Wrappers - Pre-built Trading Strategies

This module provides a collection of ready-to-use trading strategies that
wrap signal generation and optimization into a clean interface. Each strategy
implements the BaseStrategyWrapper interface and returns execution-ready weights.

Available Strategies:
Core Strategies:
1. EqualWeightStrategy - Naive 1/N diversification
2. MomentumStrategy - Trend following (top K winners)
3. MeanReversionStrategy - Contrarian (buy losers)
4. InverseVolatilityStrategy - Risk parity style
5. CVaRMinimizationStrategy - Tail risk optimization
6. RegimeSwitchingStrategy - Adaptive momentum
7. MLRandomForestStrategy - ML return forecasting
8. MLGradientBoostingStrategy - Ensemble learning
9. ARMAForecastStrategy - Time series forecasting
10. MultiFactorMLStrategy - Multi-factor combination
11. GlobalMinimumVarianceStrategy - Pure risk minimization (GMVP)

Extended Strategies:
12. BuyAndHoldStrategy - Passive benchmark
13. QuintileFactorStrategy - Factor-based quintile portfolios
14. GMRPStrategy - Global Maximum Return Portfolio
15. MaximumDiversificationStrategy - MDP
16. MaximumDecorrelationStrategy - MDCP
17. TimeSeriesMomentumStrategy - Individual asset momentum
18. MovingAverageCrossoverStrategy - MA crossover signals
19. MarkowitzMVOStrategy - Classic mean-variance optimization
20. LinearRegressionStrategy - Linear regression forecasting

Author: Portfolio Engine Team
Date: December 2025
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd
from pandas import Series, DataFrame
from scipy.optimize import minimize
from sklearn.linear_model import Ridge, Lasso, LinearRegression
from sklearn.preprocessing import StandardScaler
import logging

from src.portfolio_engine import PortfolioState

logger = logging.getLogger(__name__)


class BaseStrategyWrapper(ABC):
    """
    Abstract base class for all strategy wrappers.
    
    All strategies must implement:
    - get_weights(date, portfolio_state) -> pd.Series
    - get_strategy_info() -> dict
    
    The strategy wrapper's job is to:
    1. Generate raw signals (via Strategy class)
    2. Apply risk optimization (via Optimizer class)
    3. Return clean, execution-ready weights
    
    Parameters
    ----------
    name : str
        Human-readable strategy name
    strategy : Strategy
        Signal generation class (from strategy.py)
    optimizer : PortfolioOptimizer
        Risk optimizer class (from optimizer.py)
    **params
        Strategy-specific parameters
    
    Examples
    --------
    >>> from src.strategy_wrapper import MomentumStrategy
    >>> from src.strategy import Strategy
    >>> from src.optimizer import PortfolioOptimizer
    >>> 
    >>> strategy = Strategy(prices)
    >>> optimizer = PortfolioOptimizer(strategy.get_return_matrix())
    >>> 
    >>> momentum = MomentumStrategy(
    ...     strategy, optimizer,
    ...     top_k=10, lookback=126,
    ...     objective='cvar', alpha=0.95
    ... )
    """
    
    def __init__(self, name: str, strategy, optimizer, **params):
        """Initialize strategy wrapper."""
        self.name = name
        self.strategy = strategy
        self.optimizer = optimizer
        self.params = params
    
    @abstractmethod
    def get_weights(
        self,
        date: pd.Timestamp,
        portfolio_state: PortfolioState
    ) -> Series:
        """
        Generate target weights for the given date.
        
        Parameters
        ----------
        date : pd.Timestamp
            Current rebalancing date
        portfolio_state : PortfolioState
            Complete portfolio state including history and metrics
        
        Returns
        -------
        pd.Series
            Target weights for risky assets (excluding cash)
            Must sum to <= 1.0 (remainder allocated to cash)
        """
        pass
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """
        Return strategy metadata for logging and dashboard.
        
        Returns
        -------
        dict
            Strategy name, type, and parameters
        """
        return {
            'name': self.name,
            'type': self.__class__.__name__,
            'parameters': self.params
        }


# ============================================================================
# BASIC STRATEGIES (Simple, No ML)
# ============================================================================

class EqualWeightStrategy(BaseStrategyWrapper):
    """
    1. Equal Weight (1/N) - Naive Diversification
    
    Allocates equal weight to all assets and rebalances periodically.
    This is the simplest strategy and serves as a baseline.
    
    Properties:
    - No forecasting needed
    - Maximum diversification
    - Low turnover (only rebalances to maintain equality)
    - Often surprisingly competitive with complex strategies
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator (unused, kept for interface consistency)
    optimizer : PortfolioOptimizer, optional
        Optimizer (unused for equal weight)
    
    References
    ----------
    DeMiguel, V., Garlappi, L., & Uppal, R. (2009).
    "Optimal versus naive diversification: How inefficient is the 1/N portfolio strategy?"
    Review of Financial Studies, 22(5), 1915-1953.
    
    Examples
    --------
    >>> equal_weight = EqualWeightStrategy(strategy)
    >>> weights = equal_weight.get_weights(date, portfolio_state)
    """
    
    def __init__(self, strategy, optimizer=None):
        """Initialize equal weight strategy."""
        super().__init__("Equal Weight", strategy, optimizer)
    
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> Series:
        """Return equal weights for all assets."""
        n_assets = len(self.strategy.assets)
        weights = Series(1.0 / n_assets, index=self.strategy.assets)
        return weights


class MomentumStrategy(BaseStrategyWrapper):
    """
    2. Momentum (Top-K Winners) - Trend Following
    
    Ranks assets by past returns and invests in top K performers.
    This captures the momentum anomaly - assets that performed well
    recently tend to continue performing well.
    
    Properties:
    - Exploits momentum effect (Jegadeesh & Titman, 1993)
    - Works best in trending markets
    - Can suffer in mean-reverting environments
    - CVaR optimization controls tail risk
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator
    optimizer : PortfolioOptimizer
        Risk optimizer
    top_k : int, default=10
        Number of top assets to hold
    lookback : int, default=126
        Lookback period for momentum calculation (trading days)
    objective : str, default='cvar'
        Optimization objective ('mvo', 'cvar', 'sharpe', etc.)
    alpha : float, default=0.95
        Confidence level for CVaR (95% = protect against worst 5%)
    max_weight : float, default=0.3
        Maximum weight per asset (concentration limit)
    
    References
    ----------
    Jegadeesh, N., & Titman, S. (1993).
    "Returns to buying winners and selling losers: Implications for stock market efficiency."
    Journal of Finance, 48(1), 65-91.
    
    Examples
    --------
    >>> momentum = MomentumStrategy(
    ...     strategy, optimizer,
    ...     top_k=10, lookback=126,
    ...     objective='cvar', alpha=0.95
    ... )
    """
    
    def __init__(
        self,
        strategy,
        optimizer,
        top_k: int = 10,
        lookback: int = 126,
        objective: str = 'cvar',
        alpha: float = 0.95,
        max_weight: float = 0.3
    ):
        """Initialize momentum strategy."""
        super().__init__(
            "Momentum Top-K",
            strategy,
            optimizer,
            top_k=top_k,
            lookback=lookback,
            objective=objective,
            alpha=alpha,
            max_weight=max_weight
        )
    
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> Series:
        """Generate momentum-based weights."""
        lookback = self.params['lookback']
        
        # Check if we have enough data for momentum calculation
        date_idx = self.strategy.prices.index.get_loc(date)
        if date_idx < lookback:
            # During warmup period, use Buy & Hold
            if portfolio_state.current_weights is not None and len(portfolio_state.current_weights) > 0:
                return portfolio_state.current_weights.reindex(self.strategy.assets, fill_value=0.0)
            # First time: set equal weights and hold
            return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)
        
        # Calculate momentum for current date
        momentum_signals = self.strategy.momentum(window=lookback).loc[date]
        
        # Select top K assets
        top_k = self.params['top_k']
        if top_k < len(self.strategy.assets):
            top_assets = momentum_signals.nlargest(top_k).index
            initial_weights = pd.Series(0.0, index=self.strategy.assets)
            initial_weights[top_assets] = 1.0 / top_k
        else:
            # Weight by positive momentum signals
            positive_signals = momentum_signals.clip(lower=0)
            if positive_signals.sum() > 0:
                initial_weights = positive_signals / positive_signals.sum()
            else:
                initial_weights = pd.Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)
        
        # Get returns window for optimization
        start_idx = max(0, date_idx - lookback)
        returns_window = self.strategy.returns.iloc[start_idx:date_idx]
        
        # Optimize with risk constraints
        final_weights = self.optimizer.optimize(
            initial_weights,
            objective=self.params['objective'],
            alpha=self.params.get('alpha', 0.95),
            long_only=True,
            max_weight=self.params['max_weight'],
            returns_data=returns_window
        )
        
        return Series(final_weights, index=self.strategy.assets)


class MeanReversionStrategy(BaseStrategyWrapper):
    """
    3. Mean Reversion - Short-term Contrarian
    
    Buys recent losers and sells recent winners, betting that
    extreme moves will reverse. Works well in range-bound markets.
    
    Properties:
    - Exploits short-term overreaction
    - Opposite of momentum
    - Best in sideways markets
    - High turnover (trades frequently)
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator
    optimizer : PortfolioOptimizer
        Risk optimizer
    top_k : int, default=10
        Number of assets to hold
    window : int, default=5
        Lookback window for mean reversion (short-term)
    objective : str, default='mvo'
        Optimization objective
    risk_aversion : float, default=3.0
        Risk aversion parameter for MVO
    max_weight : float, default=0.25
        Maximum weight per asset
    
    References
    ----------
    Lehmann, B. N. (1990).
    "Fads, martingales, and market efficiency."
    Quarterly Journal of Economics, 105(1), 1-28.
    
    Examples
    --------
    >>> mean_rev = MeanReversionStrategy(
    ...     strategy, optimizer,
    ...     top_k=10, window=5,
    ...     risk_aversion=3.0
    ... )
    """
    
    def __init__(
        self,
        strategy,
        optimizer,
        top_k: int = 10,
        window: int = 5,
        objective: str = 'mvo',
        risk_aversion: float = 3.0,
        max_weight: float = 0.25
    ):
        """Initialize mean reversion strategy."""
        super().__init__(
            "Mean Reversion",
            strategy,
            optimizer,
            top_k=top_k,
            window=window,
            objective=objective,
            risk_aversion=risk_aversion,
            max_weight=max_weight
        )
    
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> Series:
        """Generate mean reversion weights."""
        window = self.params['window']
        
        # Check if we have enough data for mean reversion calculation
        date_idx = self.strategy.prices.index.get_loc(date)
        if date_idx < window + 20:  # Need window + enough for volatility calc
            # During warmup period, use Buy & Hold
            if portfolio_state.current_weights is not None and len(portfolio_state.current_weights) > 0:
                return portfolio_state.current_weights.reindex(self.strategy.assets, fill_value=0.0)
            # First time: set equal weights and hold
            return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)
        
        # Calculate mean reversion signals for current date
        mr_signals = self.strategy.mean_reversion(window=window).loc[date]
        
        # Invert signals (negative z-score = oversold = buy)
        inverted_signals = -mr_signals
        
        # Select top K assets
        top_k = self.params['top_k']
        if top_k < len(self.strategy.assets):
            top_assets = inverted_signals.nlargest(top_k).index
            initial_weights = pd.Series(0.0, index=self.strategy.assets)
            initial_weights[top_assets] = 1.0 / top_k
        else:
            # Weight by inverted signals
            positive_signals = inverted_signals.clip(lower=0)
            if positive_signals.sum() > 0:
                initial_weights = positive_signals / positive_signals.sum()
            else:
                initial_weights = pd.Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)
        
        # Get returns window for optimization
        lookback = max(126, window * 2)  # At least 126 days or 2x window
        start_idx = max(0, date_idx - lookback)
        returns_window = self.strategy.returns.iloc[start_idx:date_idx]
        
        # Optimize
        final_weights = self.optimizer.optimize(
            initial_weights,
            objective=self.params['objective'],
            risk_aversion=self.params.get('risk_aversion', 3.0),
            long_only=True,
            max_weight=self.params['max_weight'],
            returns_data=returns_window
        )
        
        return Series(final_weights, index=self.strategy.assets)


class InverseVolatilityStrategy(BaseStrategyWrapper):
    """
    4. Inverse Volatility - Risk Parity Style
    
    Weights assets inversely proportional to their volatility.
    Low-volatility assets get higher allocations, creating a
    balanced risk contribution across positions.
    
    Properties:
    - Defensive strategy (favors stable assets)
    - Risk parity approach
    - Low turnover
    - Good in volatile markets
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator
    optimizer : PortfolioOptimizer
        Risk optimizer
    vol_window : int, default=21
        Volatility calculation window (21 days = 1 month)
    objective : str, default='risk_parity'
        Optimization objective
    max_weight : float, default=0.4
        Maximum weight per asset
    
    References
    ----------
    Maillard, S., Roncalli, T., & Teïletche, J. (2010).
    "The properties of equally weighted risk contribution portfolios."
    Journal of Portfolio Management, 36(4), 60-70.
    
    Examples
    --------
    >>> inv_vol = InverseVolatilityStrategy(
    ...     strategy, optimizer,
    ...     vol_window=21,
    ...     max_weight=0.4
    ... )
    """
    
    def __init__(
        self,
        strategy,
        optimizer,
        vol_window: int = 21,
        objective: str = 'risk_parity',
        max_weight: float = 0.4
    ):
        """Initialize inverse volatility strategy."""
        super().__init__(
            "Inverse Volatility",
            strategy,
            optimizer,
            vol_window=vol_window,
            objective=objective,
            max_weight=max_weight
        )
    
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> Series:
        """Generate inverse volatility weights."""
        vol_window = self.params['vol_window']
        
        # Check if we have enough data for volatility calculation
        date_idx = self.strategy.prices.index.get_loc(date)
        if date_idx < vol_window:
            # During warmup period, use Buy & Hold
            if portfolio_state.current_weights is not None and len(portfolio_state.current_weights) > 0:
                return portfolio_state.current_weights.reindex(self.strategy.assets, fill_value=0.0)
            # First time: set equal weights and hold
            return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)
        
        # Calculate volatility for current date
        recent_vol = self.strategy.volatility(window=vol_window).loc[date]
        
        # Weight by inverse volatility
        inv_vol = 1.0 / (recent_vol + 1e-8)  # Add small epsilon
        initial_weights = inv_vol / inv_vol.sum()
        
        # Get returns window for optimization
        lookback = max(126, vol_window * 2)
        start_idx = max(0, date_idx - lookback)
        returns_window = self.strategy.returns.iloc[start_idx:date_idx]
        
        # Optimize with risk parity
        final_weights = self.optimizer.optimize(
            initial_weights,
            objective=self.params['objective'],
            long_only=True,
            max_weight=self.params['max_weight'],
            returns_data=returns_window
        )
        
        return Series(final_weights, index=self.strategy.assets)
        
        return Series(final_weights, index=self.strategy.assets)


# ============================================================================
# INTERMEDIATE STRATEGIES (Optimization-Focused)
# ============================================================================

class CVaRMinimizationStrategy(BaseStrategyWrapper):
    """
    5. CVaR Minimization - Tail Risk Focus
    
    Minimizes Conditional Value at Risk (expected loss in worst α% of cases).
    Pure risk-based allocation with no return forecasts. Focuses on
    protecting against extreme downside scenarios.
    
    Properties:
    - Tail risk minimization
    - No return forecasts needed
    - Conservative approach
    - Good for risk-averse investors
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator (used for data access)
    optimizer : PortfolioOptimizer
        Risk optimizer
    alpha : float, default=0.95
        Confidence level (95% = protect worst 5%)
    lookback : int, default=252
        Historical window for CVaR calculation
    max_weight : float, default=0.3
        Maximum weight per asset
    
    References
    ----------
    Rockafellar, R. T., & Uryasev, S. (2000).
    "Optimization of conditional value-at-risk."
    Journal of Risk, 2, 21-42.
    
    Examples
    --------
    >>> cvar_min = CVaRMinimizationStrategy(
    ...     strategy, optimizer,
    ...     alpha=0.95, lookback=252
    ... )
    """
    
    def __init__(
        self,
        strategy,
        optimizer,
        alpha: float = 0.95,
        lookback: int = 252,
        max_weight: float = 0.3
    ):
        """Initialize CVaR minimization strategy."""
        super().__init__(
            "CVaR Minimization",
            strategy,
            optimizer,
            alpha=alpha,
            lookback=lookback,
            max_weight=max_weight
        )
    
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> Series:
        """Generate CVaR-minimizing weights."""
        # Start with equal weights
        n = len(self.strategy.assets)
        initial_weights = np.ones(n) / n
        
        # Get historical returns for CVaR calculation
        lookback = self.params.get('lookback', 252)
        date_idx = self.strategy.prices.index.get_loc(date)
        start_idx = max(0, date_idx - lookback)
        
        # Get returns window ending before current date
        returns_window = self.strategy.returns.iloc[start_idx:date_idx]
        
        # Need sufficient history
        if len(returns_window) < 20:
            return Series(initial_weights, index=self.strategy.assets)
        
        try:
            # Minimize CVaR
            final_weights = self.optimizer.optimize(
                initial_weights,
                objective='cvar',
                alpha=self.params['alpha'],
                long_only=True,
                max_weight=self.params['max_weight'],
                returns_data=returns_window
            )
            return Series(final_weights, index=self.strategy.assets)
        except Exception as e:
            logger.warning(f"CVaR optimization failed: {e}, using equal weights")
            return Series(initial_weights, index=self.strategy.assets)


# ============================================================================
# EXTENDED STRATEGIES
# ============================================================================

class GlobalMinimumVarianceStrategy(BaseStrategyWrapper):
    """
    6. Regime Switching Momentum - Adaptive Strategy
    
    Detects market regime (low/high volatility) and adapts momentum
    speed accordingly:
    - Low volatility: Slow momentum (trend following)
    - High volatility: Fast momentum (quick adaptation)
    
    Properties:
    - Adaptive to market conditions
    - Switches between fast/slow signals
    - Better risk-adjusted returns
    - Handles regime changes
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator
    optimizer : PortfolioOptimizer
        Risk optimizer
    vol_threshold : float, default=0.02
        Volatility threshold for regime switch (annualized)
    fast_window : int, default=21
        Fast momentum window (high vol regime)
    slow_window : int, default=126
        Slow momentum window (low vol regime)
    top_k : int, default=10
        Number of assets to hold
    objective : str, default='cvar'
        Optimization objective
    alpha : float, default=0.95
        CVaR confidence level
    max_weight : float, default=0.3
        Maximum weight per asset
    
    References
    ----------
    Kritzman, M., Page, S., & Turkington, D. (2012).
    "Regime shifts: Implications for dynamic strategies."
    Financial Analysts Journal, 68(3), 22-39.
    
    Examples
    --------
    >>> regime_switch = RegimeSwitchingStrategy(
    ...     strategy, optimizer,
    ...     vol_threshold=0.02,
    ...     fast_window=21, slow_window=126
    ... )
    """
    
    def __init__(
        self,
        strategy,
        optimizer,
        vol_threshold: float = 0.02,
        fast_window: int = 21,
        slow_window: int = 126,
        top_k: int = 10,
        objective: str = 'cvar',
        alpha: float = 0.95,
        max_weight: float = 0.3
    ):
        """Initialize regime switching strategy."""
        super().__init__(
            "Regime Switching",
            strategy,
            optimizer,
            vol_threshold=vol_threshold,
            fast_window=fast_window,
            slow_window=slow_window,
            top_k=top_k,
            objective=objective,
            alpha=alpha,
            max_weight=max_weight
        )
    
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> Series:
        """Generate regime-adaptive weights."""
        # Detect regime based on recent volatility
        recent_vol = self.strategy.volatility(window=20).iloc[-1].mean()
        
        # Choose window based on volatility regime
        if recent_vol > self.params['vol_threshold']:
            window = self.params['fast_window']  # High vol = fast momentum
        else:
            window = self.params['slow_window']  # Low vol = slow momentum
        
        # Use adaptive momentum
        initial_weights = self.strategy.generate_initial_weights(
            method='momentum',
            top_n=self.params['top_k'],
            lookback=window
        )
        
        # Optimize
        final_weights = self.optimizer.optimize(
            initial_weights,
            objective=self.params['objective'],
            alpha=self.params['alpha'],
            long_only=True,
            max_weight=self.params['max_weight'],
            returns_data=self.strategy.get_return_matrix()
        )
        

    """
    7. ML Random Forest - Machine Learning Forecast
    
    Uses Random Forest regression to forecast future returns based on
    technical features (momentum, volatility, RSI, price ratios).
    Ensemble of decision trees reduces overfitting.
    
    Properties:
    - ML-based return forecasting
    - Non-parametric (no distribution assumptions)
    - Captures non-linear relationships
    - Feature importance for interpretability
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator with ML methods
    optimizer : PortfolioOptimizer
        Risk optimizer
    lookback : int, default=252
        Historical window for features
    forecast_days : int, default=21
        Forward return period to predict
    top_k : int, default=10
        Number of top predictions to hold
    n_estimators : int, default=100
        Number of trees in forest
    objective : str, default='cvar'
        Optimization objective
    alpha : float, default=0.95
        CVaR confidence level
    max_weight : float, default=0.3
        Maximum weight per asset
    
    References
    ----------
    Breiman, L. (2001).
    "Random forests."
    Machine Learning, 45(1), 5-32.
    
    Examples
    --------
    >>> rf_strategy = MLRandomForestStrategy(
    ...     strategy, optimizer,
    ...     lookback=252, forecast_days=21,
    ...     n_estimators=100
    ... )
    """
    
    def __init__(
        self,
        strategy,
        optimizer,
        lookback: int = 252,
        forecast_days: int = 21,
        top_k: int = 10,
        n_estimators: int = 100,
        objective: str = 'cvar',
        alpha: float = 0.95,
        max_weight: float = 0.3
    ):
        """Initialize ML Random Forest strategy."""
        super().__init__(
            "ML Random Forest",
            strategy,
            optimizer,
            lookback=lookback,
            forecast_days=forecast_days,
            top_k=top_k,
            n_estimators=n_estimators,
            objective=objective,
            alpha=alpha,
            max_weight=max_weight
        )
    
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> Series:
        """Generate ML Random Forest weights."""
        try:
            from sklearn.ensemble import RandomForestRegressor
            
            lookback = self.params.get('lookback', 252)
            forecast_days = self.params.get('forecast_days', 21)
            top_k = self.params['top_k']
            
            # Get training data
            date_idx = self.strategy.prices.index.get_loc(date)
            if date_idx < lookback + forecast_days:
                # Not enough data, use momentum fallback
                initial_weights = self.strategy.generate_initial_weights(
                    method='momentum', top_n=top_k, lookback=min(126, date_idx)
                )
            else:
                # Train RF model for each asset and predict
                predictions = Series(0.0, index=self.strategy.assets)
                
                for asset in self.strategy.assets:
                    # Get historical returns and features
                    returns = self.strategy.returns[asset].iloc[date_idx-lookback-forecast_days:date_idx]
                    
                    # Create features: lagged returns, rolling stats
                    X_list, y_list = [], []
                    for i in range(len(returns) - forecast_days - 5):
                        features = [
                            returns.iloc[i],  # lag 1
                            returns.iloc[max(0, i-4):i+1].mean(),  # 5-day avg
                            returns.iloc[max(0, i-19):i+1].std(),  # 20-day vol
                        ]
                        target = returns.iloc[i+forecast_days]
                        X_list.append(features)
                        y_list.append(target)
                    
                    if len(X_list) < 50:
                        predictions[asset] = 0
                        continue
                    
                    X = np.array(X_list)
                    y = np.array(y_list)
                    
                    # Train model
                    model = RandomForestRegressor(
                        n_estimators=self.params.get('n_estimators', 100),
                        max_depth=5, random_state=42, n_jobs=-1
                    )
                    model.fit(X, y)
                    
                    # Predict current
                    recent_returns = returns.iloc[-5:]
                    current_features = np.array([[
                        recent_returns.iloc[-1],
                        recent_returns.mean(),
                        recent_returns.std()
                    ]])
                    predictions[asset] = model.predict(current_features)[0]
                
                # Select top K by prediction
                top_assets = predictions.nlargest(top_k).index
                initial_weights = Series(0.0, index=self.strategy.assets)
                initial_weights[top_assets] = 1.0 / top_k
            
            # Optimize
            final_weights = self.optimizer.optimize(
                initial_weights,
                objective=self.params['objective'],
                alpha=self.params['alpha'],
                long_only=True,
                max_weight=self.params['max_weight'],
                returns_data=self.strategy.get_return_matrix()
            )
            
            return Series(final_weights, index=self.strategy.assets)
            
        except Exception as e:
            # Fallback to momentum on any error
            initial_weights = self.strategy.generate_initial_weights(
                method='momentum', top_n=self.params['top_k'], lookback=126
            )
            final_weights = self.optimizer.optimize(
                initial_weights, objective=self.params['objective'],
                alpha=self.params['alpha'], long_only=True,
                max_weight=self.params['max_weight'],
                returns_data=self.strategy.get_return_matrix()
            )

    """
    8. ML Gradient Boosting - Sequential Ensemble Learning
    
    Uses Gradient Boosting Machines (GBM) to forecast returns.
    Sequential ensemble that builds trees to correct previous errors.
    Often outperforms Random Forest on structured data.
    
    Properties:
    - Sequential error correction
    - Better accuracy than Random Forest (usually)
    - Captures complex patterns
    - Regularization via learning rate
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator with ML methods
    optimizer : PortfolioOptimizer
        Risk optimizer
    lookback : int, default=252
        Historical window for features
    forecast_days : int, default=21
        Forward return period to predict
    top_k : int, default=10
        Number of top predictions to hold
    learning_rate : float, default=0.05
        Shrinkage parameter (lower = more conservative)
    objective : str, default='cvar'
        Optimization objective
    alpha : float, default=0.95
        CVaR confidence level
    max_weight : float, default=0.3
        Maximum weight per asset
    
    References
    ----------
    Friedman, J. H. (2001).
    "Greedy function approximation: A gradient boosting machine."
    Annals of Statistics, 29(5), 1189-1232.
    
    Examples
    --------
    >>> gbm_strategy = MLGradientBoostingStrategy(
    ...     strategy, optimizer,
    ...     lookback=252, learning_rate=0.05
    ... )
    """
    
    def __init__(
        self,
        strategy,
        optimizer,
        lookback: int = 252,
        forecast_days: int = 21,
        top_k: int = 10,
        learning_rate: float = 0.05,
        objective: str = 'cvar',
        alpha: float = 0.95,
        max_weight: float = 0.3
    ):
        """Initialize ML Gradient Boosting strategy."""
        super().__init__(
            "ML Gradient Boosting",
            strategy,
            optimizer,
            lookback=lookback,
            forecast_days=forecast_days,
            top_k=top_k,
            learning_rate=learning_rate,
            objective=objective,
            alpha=alpha,
            max_weight=max_weight
        )
    
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> Series:
        """Generate ML Gradient Boosting weights."""
        try:
            from sklearn.ensemble import GradientBoostingRegressor
            
            lookback = self.params.get('lookback', 252)
            forecast_days = self.params.get('forecast_days', 21)
            top_k = self.params['top_k']
            learning_rate = self.params.get('learning_rate', 0.05)
            
            date_idx = self.strategy.prices.index.get_loc(date)
            if date_idx < lookback + forecast_days:
                initial_weights = self.strategy.generate_initial_weights(
                    method='momentum', top_n=top_k, lookback=min(126, date_idx)
                )
            else:
                predictions = Series(0.0, index=self.strategy.assets)
                
                for asset in self.strategy.assets:
                    returns = self.strategy.returns[asset].iloc[date_idx-lookback-forecast_days:date_idx]
                    
                    X_list, y_list = [], []
                    for i in range(len(returns) - forecast_days - 5):
                        features = [
                            returns.iloc[i],
                            returns.iloc[max(0, i-4):i+1].mean(),
                            returns.iloc[max(0, i-19):i+1].std(),
                            returns.iloc[max(0, i-4):i+1].skew() if i >= 4 else 0,
                        ]
                        target = returns.iloc[i+forecast_days]
                        X_list.append(features)
                        y_list.append(target)
                    
                    if len(X_list) < 50:
                        predictions[asset] = 0
                        continue
                    
                    X, y = np.array(X_list), np.array(y_list)
                    
                    model = GradientBoostingRegressor(
                        n_estimators=100, learning_rate=learning_rate,
                        max_depth=3, random_state=42
                    )
                    model.fit(X, y)
                    
                    recent_returns = returns.iloc[-5:]
                    current_features = np.array([[
                        recent_returns.iloc[-1],
                        recent_returns.mean(),
                        recent_returns.std(),
                        recent_returns.skew()
                    ]])
                    predictions[asset] = model.predict(current_features)[0]
                
                top_assets = predictions.nlargest(top_k).index
                initial_weights = Series(0.0, index=self.strategy.assets)
                initial_weights[top_assets] = 1.0 / top_k
            
            final_weights = self.optimizer.optimize(
                initial_weights, objective=self.params['objective'],
                alpha=self.params['alpha'], long_only=True,
                max_weight=self.params['max_weight'],
                returns_data=self.strategy.get_return_matrix()
            )
            return Series(final_weights, index=self.strategy.assets)
        except Exception as e:
            initial_weights = self.strategy.generate_initial_weights(
                method='momentum', top_n=self.params['top_k'], lookback=126
            )
            final_weights = self.optimizer.optimize(
                initial_weights, objective=self.params['objective'],
                alpha=self.params['alpha'], long_only=True,
                max_weight=self.params['max_weight'],
                returns_data=self.strategy.get_return_matrix()
            )

    """
    9. ARMA Time Series Forecast - Classical Statistical Approach
    
    Uses ARMA (AutoRegressive Moving Average) models to forecast returns.
    Classical time series approach that models temporal dependencies:
    - AR(p): Uses past p returns
    - MA(q): Uses past q error terms
    
    Properties:
    - Classical statistical method
    - Captures autocorrelation
    - Works for stationary series
    - Interpretable parameters
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator with ARMA methods
    optimizer : PortfolioOptimizer
        Risk optimizer
    arma_order : tuple, default=(2, 1)
        (p, q) where p=AR order, q=MA order
    forecast_steps : int, default=5
        Number of days ahead to forecast
    top_k : int, default=10
        Number of top forecasts to hold
    objective : str, default='mvo'
        Optimization objective
    risk_aversion : float, default=3.0
        Risk aversion for MVO
    max_weight : float, default=0.3
        Maximum weight per asset
    
    References
    ----------
    Box, G. E., Jenkins, G. M., & Reinsel, G. C. (2015).
    "Time series analysis: Forecasting and control" (5th ed.).
    John Wiley & Sons.
    
    Examples
    --------
    >>> arma_strategy = ARMAForecastStrategy(
    ...     strategy, optimizer,
    ...     arma_order=(2, 1), forecast_steps=5
    ... )
    """
    
    def __init__(
        self,
        strategy,
        optimizer,
        arma_order: tuple = (2, 1),
        forecast_steps: int = 5,
        top_k: int = 10,
        objective: str = 'mvo',
        risk_aversion: float = 3.0,
        max_weight: float = 0.3
    ):
        """Initialize ARMA forecast strategy."""
        super().__init__(
            "ARMA Forecast",
            strategy,
            optimizer,
            arma_order=arma_order,
            forecast_steps=forecast_steps,
            top_k=top_k,
            objective=objective,
            risk_aversion=risk_aversion,
            max_weight=max_weight
        )
    
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> Series:
        """Generate ARMA-based weights."""
        try:
            from statsmodels.tsa.arima.model import ARIMA
            
            arma_order = self.params.get('arma_order', (2, 1))
            forecast_steps = self.params.get('forecast_steps', 5)
            top_k = self.params['top_k']
            
            date_idx = self.strategy.prices.index.get_loc(date)
            if date_idx < 50:  # Need minimum data
                initial_weights = self.strategy.generate_initial_weights(
                    method='mean_reversion', top_n=top_k, window=20
                )
            else:
                predictions = Series(0.0, index=self.strategy.assets)
                
                for asset in self.strategy.assets:
                    try:
                        # Get recent returns
                        returns = self.strategy.returns[asset].iloc[max(0, date_idx-252):date_idx]
                        
                        if len(returns) < 30:
                            predictions[asset] = 0
                            continue
                        
                        # Fit ARIMA model (ARMA is ARIMA with d=0)
                        p, q = arma_order
                        model = ARIMA(returns.values, order=(p, 0, q))
                        fitted_model = model.fit(method_kwargs={'warn_convergence': False})
                        
                        # Forecast
                        forecast = fitted_model.forecast(steps=forecast_steps)
                        # Use mean forecast as prediction
                        predictions[asset] = forecast.mean()
                        
                    except Exception:
                        # If ARMA fails for this asset, use mean reversion signal
                        predictions[asset] = -self.strategy.mean_reversion(window=20).loc[date, asset]
                
                # Select top K by forecast
                top_assets = predictions.nlargest(top_k).index
                initial_weights = Series(0.0, index=self.strategy.assets)
                initial_weights[top_assets] = 1.0 / top_k
            
            # Optimize
            final_weights = self.optimizer.optimize(
                initial_weights,
                objective=self.params['objective'],
                risk_aversion=self.params.get('risk_aversion', 3.0),
                long_only=True,
                max_weight=self.params['max_weight'],
                returns_data=self.strategy.get_return_matrix()
            )
            
            return Series(final_weights, index=self.strategy.assets)
            
        except Exception as e:
            # Fallback to mean reversion
            initial_weights = self.strategy.generate_initial_weights(
                method='mean_reversion', top_n=self.params['top_k'], window=20
            )
            final_weights = self.optimizer.optimize(
                initial_weights,
                objective=self.params['objective'],
                risk_aversion=self.params.get('risk_aversion', 3.0),
                long_only=True,
                max_weight=self.params['max_weight'],
                returns_data=self.strategy.get_return_matrix()
            )

    """
    10. Multi-Factor ML - Factor Combination with ML
    
    Combines multiple factors (momentum, volatility, reversal, trend)
    using machine learning to learn optimal factor weights.
    Robust approach that doesn't rely on single signal.
    
    Properties:
    - Multi-factor diversification
    - ML-based factor weighting
    - Robust to regime changes
    - Captures different return drivers
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator with multi-factor methods
    optimizer : PortfolioOptimizer
        Risk optimizer
    lookback : int, default=252
        Historical window for factors
    top_k : int, default=10
        Number of assets to hold
    objective : str, default='cvar'
        Optimization objective
    alpha : float, default=0.95
        CVaR confidence level
    max_weight : float, default=0.3
        Maximum weight per asset
    
    References
    ----------
    Fama, E. F., & French, K. R. (1993).
    "Common risk factors in the returns on stocks and bonds."
    Journal of Financial Economics, 33(1), 3-56.
    
    Examples
    --------
    >>> multi_factor = MultiFactorMLStrategy(
    ...     strategy, optimizer,
    ...     lookback=252, top_k=10
    ... )
    """
    
    def __init__(
        self,
        strategy,
        optimizer,
        lookback: int = 252,
        top_k: int = 10,
        objective: str = 'cvar',
        alpha: float = 0.95,
        max_weight: float = 0.3
    ):
        """Initialize Multi-Factor ML strategy."""
        super().__init__(
            "Multi-Factor ML",
            strategy,
            optimizer,
            lookback=lookback,
            top_k=top_k,
            objective=objective,
            alpha=alpha,
            max_weight=max_weight
        )
    
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> Series:
        """Generate multi-factor ML weights."""
        lookback = self.params.get('lookback', 252)
        top_k = self.params['top_k']
        
        # Compute multiple factors
        momentum_signal = self.strategy.momentum(window=126).loc[date]
        mean_rev_signal = -self.strategy.mean_reversion(window=20).loc[date]  # Inverted
        vol_signal = 1.0 / (self.strategy.volatility(window=60).loc[date] + 1e-8)  # Inverse vol
        
        # Standardize each factor (z-score)
        def standardize(s):
            return (s - s.mean()) / (s.std() + 1e-8)
        
        momentum_z = standardize(momentum_signal)
        mean_rev_z = standardize(mean_rev_signal)
        vol_z = standardize(vol_signal)
        
        # Combine factors with equal weights (can be ML-learned in future)
        combined_score = (momentum_z * 0.4 + mean_rev_z * 0.3 + vol_z * 0.3)
        
        # Select top K assets
        top_assets = combined_score.nlargest(top_k).index
        initial_weights = Series(0.0, index=self.strategy.assets)
        
        # Weight by combined scores (proportional to scores)
        top_scores = combined_score[top_assets]
        positive_scores = top_scores.clip(lower=0)
        if positive_scores.sum() > 0:
            initial_weights[top_assets] = positive_scores / positive_scores.sum()
        else:
            initial_weights[top_assets] = 1.0 / len(top_assets)
        
        # Optimize
        final_weights = self.optimizer.optimize(
            initial_weights,
            objective=self.params['objective'],
            alpha=self.params['alpha'],
            long_only=True,
            max_weight=self.params['max_weight'],
            returns_data=self.strategy.get_return_matrix()
        )
        
        return Series(final_weights, index=self.strategy.assets)


class GlobalMinimumVarianceStrategy(BaseStrategyWrapper):
    """
    11. Global Minimum Variance Portfolio (GMVP) - Pure Risk Minimization
    
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
# EXTENDED STRATEGIES
# ============================================================================

# ============================================================================
# BUY AND HOLD STRATEGY
# ============================================================================

class BuyAndHoldStrategy(BaseStrategyWrapper):
    """
    Buy & Hold - Passive Investment Strategy
    
    Invests in assets at the beginning and holds without rebalancing
    (except for initial setup). This serves as a benchmark for active strategies.
    """
    
    def __init__(
        self,
        strategy,
        optimizer=None,
        initial_method: str = 'equal',
        initial_weights: Optional[pd.Series] = None
    ):
        """Initialize Buy & Hold strategy."""
        super().__init__(
            "Buy & Hold",
            strategy,
            optimizer,
            initial_method=initial_method,
            initial_weights=initial_weights
        )
        self._initial_weights = None
        self._initialized = False
    
    def get_weights(
        self,
        date: pd.Timestamp,
        portfolio_state: PortfolioState
    ) -> Series:
        """Return buy-and-hold weights."""
        if not self._initialized:
            method = self.params.get('initial_method', 'equal')
            custom_weights = self.params.get('initial_weights', None)
            
            if method == 'custom' and custom_weights is not None:
                self._initial_weights = custom_weights
            else:
                n_assets = len(self.strategy.assets)
                self._initial_weights = Series(1.0 / n_assets, index=self.strategy.assets)
            
            self._initialized = True
        
        return self._initial_weights


class QuintileFactorStrategy(BaseStrategyWrapper):
    """Quintile Factor Portfolios - Factor-Based Sorting Strategy"""
    
    def __init__(
        self,
        strategy,
        optimizer=None,
        factor: str = 'momentum',
        lookback: int = 126,
        n_quintiles: int = 5,
        target_quintile: int = 5,
        **kwargs
    ):
        super().__init__(
            f"Quintile Factor ({factor})",
            strategy,
            optimizer,
            factor=factor,
            lookback=lookback,
            n_quintiles=n_quintiles,
            target_quintile=target_quintile,
            **kwargs
        )
    
    def get_weights(
        self,
        date: pd.Timestamp,
        portfolio_state: PortfolioState
    ) -> Series:
        factor = self.params.get('factor', 'momentum')
        lookback = self.params.get('lookback', 126)
        n_quintiles = self.params.get('n_quintiles', 5)
        target_quintile = self.params.get('target_quintile', 5)
        
        if factor == 'momentum':
            factor_scores = self.strategy.momentum(window=lookback).loc[date]
        else:
            factor_scores = self.strategy.momentum(window=lookback).loc[date]
        
        factor_scores = factor_scores.sort_values(ascending=False)
        n_assets = len(factor_scores)
        assets_per_quintile = max(1, n_assets // n_quintiles)
        
        weights = Series(0.0, index=self.strategy.assets)
        start_idx = (target_quintile - 1) * assets_per_quintile
        end_idx = start_idx + assets_per_quintile
        quintile_assets = factor_scores.iloc[start_idx:end_idx].index
        weights[quintile_assets] = 1.0 / len(quintile_assets)
        
        return weights


class MaximumDiversificationStrategy(BaseStrategyWrapper):
    """Maximum Diversification Portfolio (MDP)"""
    
    def __init__(
        self,
        strategy,
        optimizer=None,
        lookback: int = 252,
        max_weight: float = 0.5,
        min_weight: float = 0.0
    ):
        super().__init__(
            "Maximum Diversification",
            strategy,
            optimizer,
            lookback=lookback,
            max_weight=max_weight,
            min_weight=min_weight
        )
    
    def get_weights(
        self,
        date: pd.Timestamp,
        portfolio_state: PortfolioState
    ) -> Series:
        lookback = self.params.get('lookback', 252)
        max_weight = self.params.get('max_weight', 0.5)
        min_weight = self.params.get('min_weight', 0.0)
        
        date_idx = self.strategy.prices.index.get_loc(date)
        start_idx = max(0, date_idx - lookback)
        returns_window = self.strategy.returns.iloc[start_idx:date_idx]
        
        # During warmup period, use Buy & Hold instead of rebalancing
        if len(returns_window) < 20:
            # Return previous weights to avoid unnecessary rebalancing
            if portfolio_state.current_weights is not None and len(portfolio_state.current_weights) > 0:
                return portfolio_state.current_weights.reindex(self.strategy.assets, fill_value=0.0)
            # First time: set equal weights and hold
            n_assets = len(self.strategy.assets)
            return Series(1.0 / n_assets, index=self.strategy.assets)
        
        cov_matrix = returns_window.cov().values * 252
        volatilities = returns_window.std().values * np.sqrt(252)
        cov_matrix = cov_matrix + 1e-5 * np.eye(len(cov_matrix))
        n_assets = len(volatilities)
        
        def neg_diversification_ratio(w):
            portfolio_vol = np.sqrt(np.dot(w, np.dot(cov_matrix, w)))
            weighted_vol = np.dot(w, volatilities)
            if weighted_vol < 1e-8:
                return 1e8
            return portfolio_vol / weighted_vol
        
        x0 = np.ones(n_assets) / n_assets
        bounds = [(min_weight, max_weight) for _ in range(n_assets)]
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]
        
        result = minimize(
            neg_diversification_ratio,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'ftol': 1e-9, 'disp': False}
        )
        
        if not result.success:
            return Series(1.0 / n_assets, index=self.strategy.assets)
        
        optimal_weights = result.x
        optimal_weights = np.clip(optimal_weights, 0, max_weight)
        optimal_weights = optimal_weights / optimal_weights.sum()
        
        return Series(optimal_weights, index=self.strategy.assets)


class MaximumDecorrelationStrategy(BaseStrategyWrapper):
    """Maximum Decorrelation Portfolio (MDCP)"""
    
    def __init__(
        self,
        strategy,
        optimizer=None,
        lookback: int = 252,
        max_weight: float = 0.5,
        min_weight: float = 0.0
    ):
        super().__init__(
            "Maximum Decorrelation",
            strategy,
            optimizer,
            lookback=lookback,
            max_weight=max_weight,
            min_weight=min_weight
        )
    
    def get_weights(
        self,
        date: pd.Timestamp,
        portfolio_state: PortfolioState
    ) -> Series:
        lookback = self.params.get('lookback', 252)
        max_weight = self.params.get('max_weight', 0.5)
        min_weight = self.params.get('min_weight', 0.0)
        
        date_idx = self.strategy.prices.index.get_loc(date)
        start_idx = max(0, date_idx - lookback)
        returns_window = self.strategy.returns.iloc[start_idx:date_idx]
        
        if len(returns_window) < 20:
            n_assets = len(self.strategy.assets)
            return Series(1.0 / n_assets, index=self.strategy.assets)
        
        corr_matrix = returns_window.corr().values
        corr_matrix = corr_matrix + 1e-5 * np.eye(len(corr_matrix))
        n_assets = len(corr_matrix)
        
        def portfolio_correlation(w):
            return np.dot(w, np.dot(corr_matrix, w))
        
        x0 = np.ones(n_assets) / n_assets
        bounds = [(min_weight, max_weight) for _ in range(n_assets)]
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]
        
        result = minimize(
            portfolio_correlation,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'ftol': 1e-9, 'disp': False}
        )
        
        if not result.success:
            return Series(1.0 / n_assets, index=self.strategy.assets)
        
        optimal_weights = result.x
        optimal_weights = np.clip(optimal_weights, 0, max_weight)
        optimal_weights = optimal_weights / optimal_weights.sum()
        
        return Series(optimal_weights, index=self.strategy.assets)


class TimeSeriesMomentumStrategy(BaseStrategyWrapper):
    """Time-Series Momentum (Trend Following)"""
    
    def __init__(
        self,
        strategy,
        optimizer=None,
        lookback: int = 126,
        signal_threshold: float = 0.0,
        volatility_scaling: bool = True,
        long_only: bool = True,
        **kwargs
    ):
        super().__init__(
            "Time-Series Momentum",
            strategy,
            optimizer,
            lookback=lookback,
            signal_threshold=signal_threshold,
            volatility_scaling=volatility_scaling,
            long_only=long_only,
            **kwargs
        )
    
    def get_weights(
        self,
        date: pd.Timestamp,
        portfolio_state: PortfolioState
    ) -> Series:
        lookback = self.params.get('lookback', 126)
        signal_threshold = self.params.get('signal_threshold', 0.0)
        volatility_scaling = self.params.get('volatility_scaling', True)
        long_only = self.params.get('long_only', True)
        
        momentum_signals = self.strategy.momentum(window=lookback).loc[date]
        
        # During warmup period (NaN in momentum), use Buy & Hold
        if momentum_signals.isna().any():
            # Return previous weights to avoid unnecessary rebalancing
            if portfolio_state.current_weights is not None and len(portfolio_state.current_weights) > 0:
                return portfolio_state.current_weights.reindex(self.strategy.assets, fill_value=0.0)
            # First time: set equal weights and hold
            return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)
        
        signals = pd.Series(0.0, index=momentum_signals.index)
        signals[momentum_signals > signal_threshold] = 1.0
        if not long_only:
            signals[momentum_signals < -signal_threshold] = -1.0
        
        if volatility_scaling:
            recent_vol = self.strategy.volatility(window=21).loc[date]
            inv_vol = 1.0 / (recent_vol + 1e-8)
            signals = signals * inv_vol
        
        if long_only:
            positive_signals = signals.clip(lower=0)
            if positive_signals.sum() > 0:
                weights = positive_signals / positive_signals.sum()
            else:
                weights = Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)
        else:
            if signals.abs().sum() > 0:
                weights = signals / signals.abs().sum()
            else:
                weights = Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)
        
        return weights


class MovingAverageCrossoverStrategy(BaseStrategyWrapper):
    """Moving Average Crossover Strategy"""
    
    def __init__(
        self,
        strategy,
        optimizer=None,
        fast_window: int = 50,
        slow_window: int = 200,
        signal_type: str = 'binary',
        long_only: bool = True,
        **kwargs
    ):
        super().__init__(
            f"MA Crossover ({fast_window}/{slow_window})",
            strategy,
            optimizer,
            fast_window=fast_window,
            slow_window=slow_window,
            signal_type=signal_type,
            long_only=long_only,
            **kwargs
        )
    
    def get_weights(
        self,
        date: pd.Timestamp,
        portfolio_state: PortfolioState
    ) -> Series:
        fast_window = self.params.get('fast_window', 50)
        slow_window = self.params.get('slow_window', 200)
        signal_type = self.params.get('signal_type', 'binary')
        long_only = self.params.get('long_only', True)
        
        prices = self.strategy.prices
        fast_ma = prices.rolling(window=fast_window).mean()
        slow_ma = prices.rolling(window=slow_window).mean()
        
        fast_ma_current = fast_ma.loc[date]
        slow_ma_current = slow_ma.loc[date]
        
        # During warmup period (not enough data), use Buy & Hold
        if fast_ma_current.isna().any() or slow_ma_current.isna().any():
            # Return previous weights to avoid unnecessary rebalancing
            if portfolio_state.current_weights is not None and len(portfolio_state.current_weights) > 0:
                return portfolio_state.current_weights.reindex(self.strategy.assets, fill_value=0.0)
            # First time: set equal weights and hold
            return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)
        
        if signal_type == 'binary':
            signals = pd.Series(0.0, index=self.strategy.assets)
            signals[fast_ma_current > slow_ma_current] = 1.0
            if not long_only:
                signals[fast_ma_current < slow_ma_current] = -1.0
        else:
            ma_diff = (fast_ma_current - slow_ma_current) / slow_ma_current
            signals = ma_diff
            if long_only:
                signals = signals.clip(lower=0)
        
        if long_only:
            positive_signals = signals.clip(lower=0)
            if positive_signals.sum() > 0:
                weights = positive_signals / positive_signals.sum()
            else:
                weights = Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)
        else:
            if signals.abs().sum() > 0:
                weights = signals / signals.abs().sum()
            else:
                weights = Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)
        
        return weights


class MarkowitzMVOStrategy(BaseStrategyWrapper):
    """Classic Markowitz Mean-Variance Optimization"""
    
    def __init__(
        self,
        strategy,
        optimizer=None,
        lookback: int = 252,
        risk_aversion: float = 1.0,
        return_forecast_method: str = 'historical',
        max_weight: float = 0.5,
        **kwargs
    ):
        super().__init__(
            f"Markowitz MVO (λ={risk_aversion})",
            strategy,
            optimizer,
            lookback=lookback,
            risk_aversion=risk_aversion,
            return_forecast_method=return_forecast_method,
            max_weight=max_weight,
            **kwargs
        )
    
    def get_weights(
        self,
        date: pd.Timestamp,
        portfolio_state: PortfolioState
    ) -> Series:
        lookback = self.params.get('lookback', 252)
        risk_aversion = self.params.get('risk_aversion', 1.0)
        return_method = self.params.get('return_forecast_method', 'historical')
        max_weight = self.params.get('max_weight', 0.5)
        
        date_idx = self.strategy.prices.index.get_loc(date)
        start_idx = max(0, date_idx - lookback)
        returns_window = self.strategy.returns.iloc[start_idx:date_idx]
        
        # During warmup period, use Buy & Hold instead of rebalancing
        if len(returns_window) < 20:
            # Return previous weights to avoid unnecessary rebalancing
            if portfolio_state.current_weights is not None and len(portfolio_state.current_weights) > 0:
                return portfolio_state.current_weights.reindex(self.strategy.assets, fill_value=0.0)
            # First time: set equal weights and hold
            n_assets = len(self.strategy.assets)
            return Series(1.0 / n_assets, index=self.strategy.assets)
        
        if return_method == 'historical':
            expected_returns = returns_window.mean().values * 252
        elif return_method == 'momentum':
            momentum_lookback = min(126, lookback)
            expected_returns = self.strategy.momentum(window=momentum_lookback).loc[date].values
        else:
            expected_returns = returns_window.mean().values * 252
        
        cov_matrix = returns_window.cov().values * 252
        cov_matrix = cov_matrix + 1e-5 * np.eye(len(cov_matrix))
        
        if self.optimizer is not None:
            try:
                weights = self.optimizer.mean_variance_optimization(
                    expected_returns,
                    cov_matrix,
                    risk_aversion=risk_aversion
                )
                return Series(weights, index=self.strategy.assets)
            except:
                pass
        
        n_assets = len(expected_returns)
        
        def mvo_objective(w):
            portfolio_return = np.dot(w, expected_returns)
            portfolio_variance = np.dot(w, np.dot(cov_matrix, w))
            return -portfolio_return + (risk_aversion / 2.0) * portfolio_variance
        
        x0 = np.ones(n_assets) / n_assets
        bounds = [(0.0, max_weight) for _ in range(n_assets)]
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]
        
        result = minimize(
            mvo_objective,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'ftol': 1e-9, 'disp': False}
        )
        
        if not result.success:
            return Series(1.0 / n_assets, index=self.strategy.assets)
        
        optimal_weights = result.x
        optimal_weights = optimal_weights / optimal_weights.sum()
        
        return Series(optimal_weights, index=self.strategy.assets)


class LinearRegressionStrategy(BaseStrategyWrapper):
    """Linear Regression Prediction Strategy"""
    
    def __init__(
        self,
        strategy,
        optimizer=None,
        lookback: int = 252,
        forecast_horizon: int = 1,
        features: list = None,
        regularization: str = 'ridge',
        alpha: float = 0.1,
        **kwargs
    ):
        if features is None:
            features = ['returns_lag1', 'ma_ratio', 'volatility']
        
        super().__init__(
            "Linear Regression",
            strategy,
            optimizer,
            lookback=lookback,
            forecast_horizon=forecast_horizon,
            features=features,
            regularization=regularization,
            alpha=alpha,
            **kwargs
        )
        self._models = {}
        self._scalers = {}
    
    def get_weights(
        self,
        date: pd.Timestamp,
        portfolio_state: PortfolioState
    ) -> Series:
        lookback = self.params.get('lookback', 252)
        forecast_horizon = self.params.get('forecast_horizon', 1)
        regularization = self.params.get('regularization', 'ridge')
        alpha = self.params.get('alpha', 0.1)
        
        date_idx = self.strategy.prices.index.get_loc(date)
        
        # During warmup period, use Buy & Hold
        if date_idx < lookback + 10:
            # Return previous weights to avoid unnecessary rebalancing
            if portfolio_state.current_weights is not None and len(portfolio_state.current_weights) > 0:
                return portfolio_state.current_weights.reindex(self.strategy.assets, fill_value=0.0)
            # First time: set equal weights and hold
            return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)
        
        train_start = max(0, date_idx - lookback)
        train_end = date_idx
        forecasts = pd.Series(0.0, index=self.strategy.assets)
        
        for asset in self.strategy.assets:
            returns_train = self.strategy.returns[asset].iloc[train_start:train_end]
            prices_train = self.strategy.prices[asset].iloc[train_start:train_end]
            
            n_samples = len(returns_train) - forecast_horizon - 1
            if n_samples < 10:
                forecasts[asset] = 0.0
                continue
            
            feature_list = self.params.get('features', ['returns_lag1', 'ma_ratio', 'volatility'])
            X_list = []
            
            for i in range(n_samples):
                sample_features = []
                
                if 'returns_lag1' in feature_list:
                    val = returns_train.iloc[i] if i > 0 else 0
                    sample_features.append(0.0 if pd.isna(val) else val)
                if 'ma_ratio' in feature_list:
                    if i >= 20:
                        ma20 = prices_train.iloc[i-19:i+1].mean()
                        ma50 = prices_train.iloc[max(0, i-49):i+1].mean()
                        if pd.isna(ma20) or pd.isna(ma50) or ma50 == 0:
                            sample_features.append(0.0)
                        else:
                            sample_features.append((ma20 - ma50) / ma50)
                    else:
                        sample_features.append(0.0)
                if 'volatility' in feature_list:
                    vol = returns_train.iloc[max(0, i-19):i+1].std() if i >= 0 else 0
                    sample_features.append(0.0 if pd.isna(vol) else vol)
                
                X_list.append(sample_features)
            
            y_list = returns_train.iloc[forecast_horizon:forecast_horizon + n_samples].values
            
            if len(X_list) < 10:
                forecasts[asset] = 0.0
                continue
            
            X_train = np.array(X_list)
            y_train = np.array(y_list)
            
            # Handle any remaining NaN values
            if np.any(np.isnan(X_train)):
                X_train = np.nan_to_num(X_train, nan=0.0)
            if np.any(np.isnan(y_train)):
                y_train = np.nan_to_num(y_train, nan=0.0)
            
            if asset not in self._scalers:
                self._scalers[asset] = StandardScaler()
            X_train_scaled = self._scalers[asset].fit_transform(X_train)
            
            if regularization == 'ridge':
                model = Ridge(alpha=alpha)
            elif regularization == 'lasso':
                model = Lasso(alpha=alpha)
            else:
                model = LinearRegression()
            
            model.fit(X_train_scaled, y_train)
            self._models[asset] = model
            
            current_features = []
            
            if 'returns_lag1' in feature_list:
                val = returns_train.iloc[-1]
                current_features.append(0.0 if pd.isna(val) else val)
            if 'ma_ratio' in feature_list:
                ma20 = prices_train.iloc[-20:].mean()
                ma50 = prices_train.iloc[-50:].mean()
                if pd.isna(ma20) or pd.isna(ma50) or ma50 == 0:
                    current_features.append(0.0)
                else:
                    current_features.append((ma20 - ma50) / ma50)
            if 'volatility' in feature_list:
                vol = returns_train.iloc[-20:].std()
                current_features.append(0.0 if pd.isna(vol) else vol)
            
            X_current = np.array(current_features).reshape(1, -1)
            # Check for NaN in X_current before scaling
            if np.any(np.isnan(X_current)):
                X_current = np.nan_to_num(X_current, nan=0.0)
            
            X_current_scaled = self._scalers[asset].transform(X_current)
            forecast = model.predict(X_current_scaled)[0]
            forecasts[asset] = forecast if not pd.isna(forecast) else 0.0
        
        positive_forecasts = forecasts.clip(lower=0)
        
        if positive_forecasts.sum() > 0:
            weights = positive_forecasts / positive_forecasts.sum()
        else:
            weights = Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)
        
        return weights


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def list_available_strategies() -> Dict[str, type]:
    """
    Get dictionary of all available strategy classes.
    
    Returns
    -------
    dict
        Mapping of strategy names to classes
    
    Examples
    --------
    >>> strategies = list_available_strategies()
    >>> print(strategies.keys())
    """
    return {
        'equal_weight': EqualWeightStrategy,
        'momentum': MomentumStrategy,
        'mean_reversion': MeanReversionStrategy,
        'inverse_volatility': InverseVolatilityStrategy,
        'cvar_minimization': CVaRMinimizationStrategy,
        'gmvp': GlobalMinimumVarianceStrategy,
        # Extended strategies
        'buy_and_hold': BuyAndHoldStrategy,
        'quintile_factor': QuintileFactorStrategy,
        'max_diversification': MaximumDiversificationStrategy,
        'max_decorrelation': MaximumDecorrelationStrategy,
        'time_series_momentum': TimeSeriesMomentumStrategy,
        'ma_crossover': MovingAverageCrossoverStrategy,
        'markowitz_mvo': MarkowitzMVOStrategy,
        'linear_regression': LinearRegressionStrategy
    }


def create_strategy(
    strategy_name: str,
    strategy,
    optimizer,
    **params
) -> BaseStrategyWrapper:
    """
    Factory function to create strategy by name.
    
    Parameters
    ----------
    strategy_name : str
        Name of strategy to create
    strategy : Strategy
        Signal generator
    optimizer : PortfolioOptimizer
        Risk optimizer
    **params
        Strategy-specific parameters
    
    Returns
    -------
    BaseStrategyWrapper
        Initialized strategy instance
    
    Examples
    --------
    >>> momentum = create_strategy(
    ...     'momentum',
    ...     strategy, optimizer,
    ...     top_k=10, lookback=126
    ... )
    """
    strategies = list_available_strategies()
    
    if strategy_name not in strategies:
        raise ValueError(
            f"Unknown strategy: {strategy_name}. "
            f"Available: {list(strategies.keys())}"
        )
    
    strategy_class = strategies[strategy_name]
    return strategy_class(strategy, optimizer, **params)
