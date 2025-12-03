"""
Algorithmic Trading & Portfolio Management System

A comprehensive framework for algorithmic trading strategy development,
backtesting, and portfolio management.

Core Components:
    portfolio_engine: Strategy-agnostic portfolio management system
    strategy_wrapper: 10 pre-built trading strategies (basic to advanced)
    strategy: Signal generation, ML models, and time series forecasting
    optimizer: Portfolio optimization and risk management
    backtester: Legacy compatibility wrapper
    evaluator: Performance analysis and comparison
    data_loader: Data downloading and preprocessing
    feature_engineering: Technical indicators and feature computation
    utils: Helper functions and configuration

Quick Start:
    # New API (Strategy-Agnostic)
    from src import PortfolioEngine, MomentumStrategy
    
    strategy = MomentumStrategy(lookback=60)
    engine = PortfolioEngine(prices, strategy)
    result = engine.run_backtest()
    
    # Legacy API (Still Supported)
    from src import Backtester
    backtester = Backtester(prices)
    results = backtester.run(initial_capital=100000)

Available Strategies:
    Used in Demo (12):
    - EqualWeightStrategy: 1/N portfolio
    - BuyAndHoldStrategy: Passive investment benchmark
    - MomentumStrategy: Price momentum with mean reversion filter
    - MeanReversionStrategy: Z-score based reversion
    - InverseVolatilityStrategy: Risk parity approach
    - GlobalMinimumVarianceStrategy: Minimum variance portfolio
    - CVaRMinimizationStrategy: Downside risk optimization
    - MaximumDiversificationStrategy: Maximum Diversification Portfolio
    - TimeSeriesMomentumStrategy: Time-series momentum (trend following)
    - MovingAverageCrossoverStrategy: Moving average crossover
    - MarkowitzMVOStrategy: Markowitz Mean-Variance Optimization
    - LinearRegressionStrategy: Linear regression prediction

Author: AI Assistant
Version: 2.1.0
"""

__version__ = "2.1.0"
__author__ = "AI Assistant"

# Core portfolio management (NEW)
from .portfolio_engine import PortfolioEngine, PortfolioState, PortfolioResult

# Strategy wrappers - 12 strategies used in demo
from .strategy_wrapper import (
    BaseStrategyWrapper,
    # Core strategies
    EqualWeightStrategy,
    MomentumStrategy,
    MeanReversionStrategy,
    InverseVolatilityStrategy,
    CVaRMinimizationStrategy,
    GlobalMinimumVarianceStrategy,
    # Extended strategies
    BuyAndHoldStrategy,
    MaximumDiversificationStrategy,
    MaximumDecorrelationStrategy,
    QuintileFactorStrategy,
    TimeSeriesMomentumStrategy,
    MovingAverageCrossoverStrategy,
    MarkowitzMVOStrategy,
    LinearRegressionStrategy,
    ARIMAGARCHForecastingStrategy,
    # Utility functions
    list_available_strategies,
    create_strategy
)

# Signal generation and forecasting (EXISTING)
from .signal_generator import StrategySignalGenerator, Strategy, SignalGenerator, generate_signals

# Portfolio optimization (EXISTING)
from .optimizer import PortfolioOptimizer, optimize_portfolio_forecasted

# Advanced backtesting methods (NEW v2.0)
from .backtesting_methods import BacktestingMethods, BacktestMethodResult

# Legacy compatibility (UPDATED)
from .backtester import Backtester, BacktestResults
from .evaluator import Evaluator, PerformanceEvaluator, evaluate_performance

# Data and utilities (EXISTING)
from .data_loader import DataLoader, load_data
from .feature_engineering import FeatureEngineer, make_features
from .forecasting import ARIMAGARCHForecaster, forecast_returns_volatility
from .utils import TradingConfig, setup_logging

__all__ = [
    # Core Portfolio Engine (v2.0)
    'PortfolioEngine',
    'PortfolioState',
    'PortfolioResult',
    
    # Strategy Wrappers (v2.1.0 - All implemented strategies)
    'BaseStrategyWrapper',
    # Core strategies
    'EqualWeightStrategy',
    'MomentumStrategy',
    'MeanReversionStrategy',
    'InverseVolatilityStrategy',
    'CVaRMinimizationStrategy',
    'GlobalMinimumVarianceStrategy',
    # Extended strategies
    'BuyAndHoldStrategy',
    'QuintileFactorStrategy',
    'MaximumDiversificationStrategy',
    'MaximumDecorrelationStrategy',
    'TimeSeriesMomentumStrategy',
    'MovingAverageCrossoverStrategy',
    'MarkowitzMVOStrategy',
    'LinearRegressionStrategy',
    'ARIMAGARCHForecastingStrategy',
    # Utility functions
    'list_available_strategies',
    'create_strategy',
    
    # Signal Generation
    'StrategySignalGenerator',
    'Strategy',  # Backward compatibility alias
    'SignalGenerator',  # Backward compatibility alias
    'generate_signals',
    
    # Portfolio Optimization
    'PortfolioOptimizer',
    'optimize_portfolio_forecasted',
    
    # Advanced Backtesting Methods (v2.0)
    'BacktestingMethods',
    'BacktestMethodResult',
    
    # Legacy API (Backward Compatible)
    'Backtester',
    'BacktestResults',
    'Evaluator',
    'PerformanceEvaluator',
    'evaluate_performance',
    
    # Data & Feature Engineering
    'DataLoader',
    'load_data',
    'FeatureEngineer',
    'make_features',
    
    # Forecasting
    'ARIMAGARCHForecaster',
    'forecast_returns_volatility',
    
    # Utilities
    'TradingConfig',
    'setup_logging',
]