"""
Trading Strategies Package

This package contains all trading strategies organized into three modules:
- base_strategy_wrapper: Base class and utility functions
- benchmark_strategies: 12 validated production strategies  
- advanced_strategies: 10 experimental research strategies

Usage:
    from src.strategies import create_strategy, list_available_strategies
    
    # List all strategies
    available = list_available_strategies()
    
    # Create a strategy
    strategy = create_strategy('equal_weight', signal_gen, optimizer)
"""

from .base_strategy_wrapper import (
    BaseStrategyWrapper,
    list_available_strategies,
    create_strategy
)

# Import all benchmark strategies for direct access
# Make these optional to support Lambda deployment (which uses benchmarks/ folder)
try:
    from .benchmark_strategies import (
        BuyAndHoldStrategy,
        EqualWeightStrategy,
        QuintileFactorStrategy,
        QuintileLowVolatilityStrategy,
        MeanReversionStrategy,
        GlobalMinimumVarianceStrategy,
        InverseVolatilityStrategy,
        RiskParityStrategy,
        MaximumDiversificationStrategy,
        MaximumDecorrelationStrategy,
        SharpeMaximizationStrategy,
        CVaRMinimizationStrategy
    )
except ImportError as e:
    # Skip if scipy/cvxpy not available (Lambda environment)
    import warnings
    warnings.warn(f"Full benchmark strategies not available (missing dependencies): {e}")

# Import all advanced strategies for direct access
try:
    from .advanced_strategies import (
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
except ImportError as e:
    # Skip if advanced dependencies not available
    import warnings
    warnings.warn(f"Advanced strategies not available (missing dependencies): {e}")

# Import bandit strategy wrapper for meta-strategy allocation
from .bandit_strategy_wrapper import (
    BanditStrategyWrapper,
    StrategyPerformanceTracker
)

__all__ = [
    # Base classes and utilities
    'BaseStrategyWrapper',
    'list_available_strategies',
    'create_strategy',
    
    # Benchmark strategies (12)
    'BuyAndHoldStrategy',
    'EqualWeightStrategy',
    'QuintileFactorStrategy',
    'QuintileLowVolatilityStrategy',
    'MeanReversionStrategy',
    'GlobalMinimumVarianceStrategy',
    'InverseVolatilityStrategy',
    'RiskParityStrategy',
    'MaximumDiversificationStrategy',
    'MaximumDecorrelationStrategy',
    'SharpeMaximizationStrategy',
    'CVaRMinimizationStrategy',
    
    # Advanced strategies (13)
    'MomentumStrategy',
    'RegimeSwitchingStrategy',
    'MLRandomForestStrategy',
    'MLGradientBoostingStrategy',
    'ARMAForecastStrategy',
    'MultiFactorMLStrategy',
    'GMRPStrategy',
    'TimeSeriesMomentumStrategy',
    'MovingAverageCrossoverStrategy',
    'MarkowitzMVOStrategy',
    'LinearRegressionStrategy',
    'SVMRegimeStrategy',
    'ARIMAGARCHForecastingStrategy',
    
    # Meta-strategy (Bandit Allocator)
    'BanditStrategyWrapper',
    'StrategyPerformanceTracker',
]
