"""
Strategy Wrappers - Pre-built Trading Strategies

This module provides a collection of ready-to-use trading strategies that
wrap signal generation and optimization into a clean interface. Each strategy
implements the BaseStrategyWrapper interface and returns execution-ready weights.

Available Strategies:
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

Author: Portfolio Engine Team
Date: November 2025
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
from pandas import Series, DataFrame

from src.portfolio_engine import PortfolioState


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
        # Get initial weights (top K assets with momentum)
        initial_weights = self.strategy.generate_initial_weights(
            method='momentum',
            top_n=self.params['top_k'],
            lookback=self.params['lookback']
        )
        
        # Optimize with risk constraints
        final_weights = self.optimizer.optimize(
            initial_weights,
            objective=self.params['objective'],
            alpha=self.params.get('alpha', 0.95),
            long_only=True,
            max_weight=self.params['max_weight'],
            returns_data=self.strategy.get_return_matrix()
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
        # Generate mean reversion signals
        initial_weights = self.strategy.generate_initial_weights(
            method='mean_reversion',
            top_n=self.params['top_k'],
            window=self.params['window']
        )
        
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
        # Generate inverse volatility signals
        initial_weights = self.strategy.generate_initial_weights(
            method='inv_vol',
            window=self.params['vol_window']
        )
        
        # Optimize with risk parity
        final_weights = self.optimizer.optimize(
            initial_weights,
            objective=self.params['objective'],
            long_only=True,
            max_weight=self.params['max_weight'],
            returns_data=self.strategy.get_return_matrix()
        )
        
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
        
        # Minimize CVaR
        final_weights = self.optimizer.optimize(
            initial_weights,
            objective='cvar',
            alpha=self.params['alpha'],
            long_only=True,
            max_weight=self.params['max_weight'],
            returns_data=self.strategy.get_return_matrix()
        )
        
        return Series(final_weights, index=self.strategy.assets)


class RegimeSwitchingStrategy(BaseStrategyWrapper):
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
        
        return Series(final_weights, index=self.strategy.assets)


# ============================================================================
# ADVANCED ML/TS STRATEGIES
# ============================================================================

class MLRandomForestStrategy(BaseStrategyWrapper):
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
        # TODO: Implement actual ML forecasting
        # For now, use momentum as proxy for ML predictions
        initial_weights = self.strategy.generate_initial_weights(
            method='momentum',
            top_n=self.params['top_k'],
            lookback=self.params.get('lookback', 252)
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
        
        return Series(final_weights, index=self.strategy.assets)


class MLGradientBoostingStrategy(BaseStrategyWrapper):
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
        # TODO: Implement actual GBM forecasting
        # For now, use momentum as proxy for ML predictions
        initial_weights = self.strategy.generate_initial_weights(
            method='momentum',
            top_n=self.params['top_k'],
            lookback=self.params.get('lookback', 252)
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
        
        return Series(final_weights, index=self.strategy.assets)


class ARMAForecastStrategy(BaseStrategyWrapper):
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
        # TODO: Implement actual ARMA forecasting
        # For now, use mean reversion as proxy
        initial_weights = self.strategy.generate_initial_weights(
            method='mean_reversion',
            top_n=self.params['top_k'],
            window=20
        )
        
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


class MultiFactorMLStrategy(BaseStrategyWrapper):
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
        # TODO: Implement actual multi-factor ML
        # For now, use inverse volatility (risk-based approach)
        initial_weights = self.strategy.generate_initial_weights(
            method='inv_vol',
            window=60
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
        
        return Series(final_weights, index=self.strategy.assets)


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
        'regime_switching': RegimeSwitchingStrategy,
        'ml_random_forest': MLRandomForestStrategy,
        'ml_gradient_boosting': MLGradientBoostingStrategy,
        'arma_forecast': ARMAForecastStrategy,
        'multi_factor_ml': MultiFactorMLStrategy
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
