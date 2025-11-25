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
    - EqualWeightStrategy: 1/N portfolio
    - MomentumStrategy: Price momentum with mean reversion filter
    - MeanReversionStrategy: Z-score based reversion
    - InverseVolatilityStrategy: Risk parity approach
    - CVaRMinimizationStrategy: Downside risk optimization
    - RegimeSwitchingStrategy: Market regime detection
    - MLRandomForestStrategy: Random Forest predictions
    - MLGradientBoostingStrategy: Gradient Boosting predictions
    - ARMAForecastStrategy: Time series forecasting
    - MultiFactorMLStrategy: Multi-factor ML ensemble

Author: AI Assistant
Version: 2.0.0
"""

__version__ = "2.0.0"
__author__ = "AI Assistant"

# Core portfolio management (NEW)
from .portfolio_engine import PortfolioEngine, PortfolioState, PortfolioResult

# Strategy wrappers - 10 pre-built strategies (NEW)
from .strategy_wrapper import (
    BaseStrategyWrapper,
    EqualWeightStrategy,
    MomentumStrategy,
    MeanReversionStrategy,
    InverseVolatilityStrategy,
    CVaRMinimizationStrategy,
    RegimeSwitchingStrategy,
    MLRandomForestStrategy,
    MLGradientBoostingStrategy,
    ARMAForecastStrategy,
    MultiFactorMLStrategy,
    list_available_strategies,
    create_strategy
)

# Signal generation and forecasting (EXISTING)
from .strategy import Strategy

# Portfolio optimization (EXISTING)
from .optimizer import PortfolioOptimizer, optimize_portfolio_forecasted

# Legacy compatibility (UPDATED)
from .backtester import Backtester, BacktestResults
from .evaluator import Evaluator, PerformanceEvaluator, evaluate_performance

# Data and utilities (EXISTING)
from .data_loader import DataLoader, load_data
from .feature_engineering import FeatureEngineer, make_features
from .forecasting import ARIMAGARCHForecaster, forecast_returns_volatility
from .signal_generator import SignalGenerator, generate_signals
from .utils import TradingConfig, setup_logging

__all__ = [
    # Core Portfolio Engine (v2.0)
    'PortfolioEngine',
    'PortfolioState',
    'PortfolioResult',
    
    # Strategy Wrappers (v2.0)
    'BaseStrategyWrapper',
    'EqualWeightStrategy',
    'MomentumStrategy',
    'MeanReversionStrategy',
    'InverseVolatilityStrategy',
    'CVaRMinimizationStrategy',
    'RegimeSwitchingStrategy',
    'MLRandomForestStrategy',
    'MLGradientBoostingStrategy',
    'ARMAForecastStrategy',
    'MultiFactorMLStrategy',
    'list_available_strategies',
    'create_strategy',
    
    # Signal Generation
    'Strategy',
    
    # Portfolio Optimization
    'PortfolioOptimizer',
    'optimize_portfolio_forecasted',
    
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
    
    # Signal Generation (Legacy)
    'SignalGenerator',
    'generate_signals',
    
    # Utilities
    'TradingConfig',
    'setup_logging',
]