"""
Base Strategy Wrapper - Foundation for Trading Strategies

This module provides the abstract base class that all trading strategies
must implement. It defines the interface contract for strategy wrappers
and includes utility functions for strategy management.

Author: Portfolio Engine Team
Date: December 2025
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd
from pandas import Series
import logging
import numpy as np

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
        Signal generation class (from signal_generator.py)
    optimizer : PortfolioOptimizer
        Risk optimizer class (from optimizer.py)
    **params
        Strategy-specific parameters
    
    Examples
    --------
    >>> from src.strategies.benchmark_strategies import MomentumStrategy
    >>> from src.signal_generator import Strategy
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
    
    def get_rebalancing_frequency(self) -> str:
        """Return rebalancing frequency hint (default 'M'). PortfolioEngine uses this."""
        return self.params.get('rebalancing_frequency', 'M')
    
    def evaluate_reward(self, returns: pd.Series, risk_free_rate: float = 0.0) -> float:
        """Compute reward for bandit (default Sharpe-like)."""
        from src.rewards import sharpe_like_reward
        ret = returns.mean() * 252  # Annualized return
        vol = returns.std() * np.sqrt(252)
        return sharpe_like_reward(ret, vol, risk_free_rate=risk_free_rate)
    
    def get_metadata(self) -> Dict[str, Any]:
        """Return strategy info."""
        return {'name': self.name, **self.params}


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
    # Import here to avoid circular imports
    from src.strategies.benchmark_strategies import (
        EqualWeightStrategy,
        MeanReversionStrategy,
        InverseVolatilityStrategy,
        CVaRMinimizationStrategy,
        GlobalMinimumVarianceStrategy,
        BuyAndHoldStrategy,
        MaximumDiversificationStrategy,
        MaximumDecorrelationStrategy,
        QuintileFactorStrategy,
        RiskParityStrategy,
        SharpeMaximizationStrategy,
        QuintileLowVolatilityStrategy
    )
    
    from src.strategies.advanced_strategies import (
        MomentumStrategy,
        RegimeSwitchingStrategy,
        MLRandomForestStrategy,
        MLGradientBoostingStrategy,
        ARMAForecastStrategy,
        MultiFactorMLStrategy,
        GMRPStrategy,
        TimeSeriesMomentumStrategy,
        MovingAverageCrossoverStrategy,
        MarkowitzMVOStrategy,
        LinearRegressionStrategy,
        SVMRegimeStrategy,
        ARIMAGARCHForecastingStrategy
    )
    
    return {
        # Benchmark strategies (12 validated)
        'equal_weight': EqualWeightStrategy,
        'mean_reversion': MeanReversionStrategy,
        'inverse_volatility': InverseVolatilityStrategy,
        'cvar_minimization': CVaRMinimizationStrategy,
        'gmvp': GlobalMinimumVarianceStrategy,
        'buy_and_hold': BuyAndHoldStrategy,
        'quintile_factor': QuintileFactorStrategy,
        'quintile_low_volatility': QuintileLowVolatilityStrategy,
        'max_diversification': MaximumDiversificationStrategy,
        'max_decorrelation': MaximumDecorrelationStrategy,
        'risk_parity': RiskParityStrategy,
        'sharpe_maximization': SharpeMaximizationStrategy,
        
        # Advanced strategies (13 experimental)
        'momentum': MomentumStrategy,
        'regime_switching': RegimeSwitchingStrategy,
        'ml_random_forest': MLRandomForestStrategy,
        'ml_gradient_boosting': MLGradientBoostingStrategy,
        'arma_forecast': ARMAForecastStrategy,
        'multi_factor_ml': MultiFactorMLStrategy,
        'gmrp': GMRPStrategy,
        'time_series_momentum': TimeSeriesMomentumStrategy,
        'ma_crossover': MovingAverageCrossoverStrategy,
        'markowitz_mvo': MarkowitzMVOStrategy,
        'linear_regression': LinearRegressionStrategy,
        'svm_regime': SVMRegimeStrategy,
        'arima_garch': ARIMAGARCHForecastingStrategy,
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
