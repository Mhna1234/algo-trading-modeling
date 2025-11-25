"""
Algorithmic Trading & Portfolio Optimization System

A comprehensive framework for algorithmic trading research and backtesting.

Modules:
    data_loader: Data downloading and preprocessing
    feature_engineering: Technical indicators and feature computation
    forecasting: ARIMA + GARCH time series forecasting
    signal_generator: Trading signal generation
    optimizer: Portfolio optimization using modern portfolio theory
    backtester: Comprehensive backtesting engine
    evaluator: Performance evaluation and risk analysis
    online_learning: Online/streaming machine learning models
    rl_agent: Reinforcement learning trading agents
    visualizer: Visualization utilities
    utils: Helper functions and configuration management

Usage:
    from src.data_loader import load_data
    from src.optimizer import PortfolioOptimizer
    from src.backtester import Backtester

Author: AI Assistant
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "AI Assistant"

# Import main classes for convenience
from .data_loader import DataLoader, load_data
from .feature_engineering import FeatureEngineer, make_features
from .forecasting import ARIMAGARCHForecaster, forecast_returns_volatility
from .signal_generator import SignalGenerator, generate_signals
from .optimizer import PortfolioOptimizer, optimize_portfolio_forecasted
from .backtester import Backtester, BacktestResults
from .evaluator import PerformanceEvaluator, evaluate_performance
from .utils import TradingConfig, setup_logging

__all__ = [
    # Classes
    'DataLoader',
    'FeatureEngineer', 
    'ARIMAGARCHForecaster',
    'SignalGenerator',
    'PortfolioOptimizer',
    'Backtester',
    'BacktestResults',
    'PerformanceEvaluator',
    'TradingConfig',
    
    # Functions
    'load_data',
    'make_features',
    'forecast_returns_volatility',
    'generate_signals',
    'optimize_portfolio_forecasted',
    'evaluate_performance',
    'setup_logging',
]