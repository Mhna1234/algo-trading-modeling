"""
Utility Functions and Configuration Module

This module provides common utility functions, configuration constants,
and helper classes used across the algorithmic trading system.

Functions include:
- Data validation and cleaning utilities
- Performance calculation helpers
- Date and time utilities
- Configuration management
- Logging setup
- Mathematical utilities
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any
import warnings
import logging
from datetime import datetime, timedelta
import os
from pathlib import Path
import json
import yaml
from dataclasses import dataclass, asdict

# Make matplotlib and seaborn optional (not available in Lambda)
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
except ImportError:
    # Plotting not available - functions using these will need to check
    plt = None
    sns = None

# Configuration constants
TRADING_DAYS_PER_YEAR = 252
HOURS_PER_DAY = 24
MINUTES_PER_HOUR = 60
SECONDS_PER_MINUTE = 60

# Risk-free rate (approximate)
DEFAULT_RISK_FREE_RATE = 0.02

# Default trading parameters
DEFAULT_TRANSACTION_COST = 0.001
DEFAULT_MAX_POSITION_SIZE = 0.3
DEFAULT_REBALANCE_FREQUENCY = 'weekly'

@dataclass
class TradingConfig:
    """Configuration class for trading parameters."""
    
    # Data parameters
    start_date: str = '2020-01-01'
    end_date: str = '2024-01-01'
    tickers: List[str] = None
    data_source: str = 'yfinance'
    
    # Model parameters
    arima_order: Tuple[int, int, int] = (1, 0, 1)
    garch_order: Tuple[int, int] = (1, 1)
    auto_order_selection: bool = True
    forecast_horizon: int = 1
    
    # Signal parameters
    signal_threshold: float = 0.0
    volatility_scaling: bool = True
    signal_smoothing: bool = True
    smoothing_window: int = 3
    
    # Portfolio parameters
    optimization_method: str = 'sharpe'
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE
    max_weight: float = DEFAULT_MAX_POSITION_SIZE
    min_weight: float = 0.0
    transaction_cost: float = DEFAULT_TRANSACTION_COST
    turnover_limit: Optional[float] = None
    rebalance_frequency: str = DEFAULT_REBALANCE_FREQUENCY
    
    # Portfolio class specific parameters
    slippage_bps: float = 0.0  # One-way slippage in basis points
    cash_symbol: str = "CASH"  # Symbol name for cash positions
    long_only: bool = True  # Enforce long-only constraint
    leverage_cap: float = 1.0  # Maximum leverage (sum of absolute weights)
    use_portfolio_class: bool = True  # Use new Portfolio class for backtesting
    ridge_regularization: float = 1e-4  # Ridge regularization for optimization
    min_var_regularization: float = 0.0  # Minimum variance regularization
    
    # Backtesting parameters
    initial_capital: float = 100000.0
    benchmark: str = 'SPY'
    lookback_window: int = 252
    rolling_window: int = 60
    
    def __post_init__(self):
        """Initialize default tickers if not provided."""
        if self.tickers is None:
            self.tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'SPY']
    
    def to_dict(self) -> Dict:
        """Convert config to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'TradingConfig':
        """Create config from dictionary."""
        return cls(**config_dict)
    
    def save(self, filepath: str):
        """Save configuration to file."""
        config_dict = self.to_dict()
        
        if filepath.endswith('.json'):
            with open(filepath, 'w') as f:
                json.dump(config_dict, f, indent=2)
        elif filepath.endswith('.yaml') or filepath.endswith('.yml'):
            with open(filepath, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False)
        else:
            raise ValueError("Unsupported file format. Use .json or .yaml")
    
    @classmethod
    def load(cls, filepath: str) -> 'TradingConfig':
        """Load configuration from file."""
        if filepath.endswith('.json'):
            with open(filepath, 'r') as f:
                config_dict = json.load(f)
        elif filepath.endswith('.yaml') or filepath.endswith('.yml'):
            with open(filepath, 'r') as f:
                config_dict = yaml.safe_load(f)
        else:
            raise ValueError("Unsupported file format. Use .json or .yaml")
        
        return cls.from_dict(config_dict)


def setup_logging(level: str = 'INFO', 
                 log_file: Optional[str] = None,
                 format_string: Optional[str] = None) -> logging.Logger:
    """
    Set up logging configuration for the trading system.
    
    Args:
        level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR')
        log_file: Optional log file path
        format_string: Custom format string
        
    Returns:
        Configured logger
    """
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file) if log_file else logging.NullHandler()
        ]
    )
    
    # Suppress some noisy libraries
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('yfinance').setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)


def validate_data(data: pd.DataFrame, 
                 min_periods: int = 50,
                 max_missing_pct: float = 0.1) -> Tuple[bool, List[str]]:
    """
    Validate input data for trading algorithms.
    
    Args:
        data: DataFrame to validate
        min_periods: Minimum number of periods required
        max_missing_pct: Maximum percentage of missing values allowed
        
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    # Check minimum length
    if len(data) < min_periods:
        issues.append(f"Insufficient data: {len(data)} < {min_periods} periods")
    
    # Check for missing values
    missing_pct = data.isnull().sum().sum() / (len(data) * len(data.columns))
    if missing_pct > max_missing_pct:
        issues.append(f"Too many missing values: {missing_pct:.2%} > {max_missing_pct:.2%}")
    
    # Check for infinite values
    if np.isinf(data.select_dtypes(include=[np.number])).any().any():
        issues.append("Data contains infinite values")
    
    # Check date index
    if not isinstance(data.index, pd.DatetimeIndex):
        issues.append("Index is not DatetimeIndex")
    
    # Check for duplicated dates
    if data.index.duplicated().any():
        issues.append("Duplicated dates found in index")
    
    # Check for non-positive prices (if this looks like price data)
    numeric_cols = data.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        if (data[numeric_cols] <= 0).any().any():
            issues.append("Non-positive values found (possible price data)")
    
    is_valid = len(issues) == 0
    return is_valid, issues


def clean_data(data: pd.DataFrame, 
              method: str = 'forward_fill',
              limit: Optional[int] = None) -> pd.DataFrame:
    """
    Clean financial data by handling missing values and outliers.
    
    Args:
        data: DataFrame to clean
        method: Cleaning method ('forward_fill', 'interpolate', 'drop')
        limit: Maximum number of consecutive NaN values to fill
        
    Returns:
        Cleaned DataFrame
    """
    data_clean = data.copy()
    
    if method == 'forward_fill':
        data_clean = data_clean.fillna(method='ffill', limit=limit)
        data_clean = data_clean.fillna(method='bfill', limit=limit)
    
    elif method == 'interpolate':
        data_clean = data_clean.interpolate(method='linear', limit=limit)
    
    elif method == 'drop':
        data_clean = data_clean.dropna()
    
    else:
        raise ValueError(f"Unknown cleaning method: {method}")
    
    # Remove any remaining NaN values
    data_clean = data_clean.dropna()
    
    return data_clean


def calculate_returns(prices: pd.DataFrame, 
                     method: str = 'simple',
                     periods: int = 1) -> pd.DataFrame:
    """
    Calculate returns from price data.
    
    Args:
        prices: DataFrame with price data
        method: 'simple' or 'log' returns
        periods: Number of periods for return calculation
        
    Returns:
        DataFrame with returns
    """
    if method == 'simple':
        returns = prices.pct_change(periods=periods)
    elif method == 'log':
        returns = np.log(prices / prices.shift(periods))
    else:
        raise ValueError("method must be 'simple' or 'log'")
    
    return returns.dropna()


def annualize_returns(returns: Union[pd.Series, pd.DataFrame],
                     periods_per_year: int = TRADING_DAYS_PER_YEAR) -> Union[float, pd.Series]:
    """
    Annualize returns.
    
    Args:
        returns: Returns data
        periods_per_year: Number of periods per year
        
    Returns:
        Annualized returns
    """
    if isinstance(returns, pd.Series):
        return (1 + returns.mean()) ** periods_per_year - 1
    else:
        return (1 + returns.mean()) ** periods_per_year - 1


def annualize_volatility(returns: Union[pd.Series, pd.DataFrame],
                        periods_per_year: int = TRADING_DAYS_PER_YEAR) -> Union[float, pd.Series]:
    """
    Annualize volatility.
    
    Args:
        returns: Returns data
        periods_per_year: Number of periods per year
        
    Returns:
        Annualized volatility
    """
    return returns.std() * np.sqrt(periods_per_year)


def calculate_sharpe_ratio(returns: Union[pd.Series, pd.DataFrame],
                          risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
                          periods_per_year: int = TRADING_DAYS_PER_YEAR) -> Union[float, pd.Series]:
    """
    Calculate Sharpe ratio.
    
    Mathematical formulation:
    Sharpe = (E[R] - R_f) / σ(R)
    
    Args:
        returns: Returns data
        risk_free_rate: Risk-free rate (annual)
        periods_per_year: Number of periods per year
        
    Returns:
        Sharpe ratio
    """
    excess_returns = returns - risk_free_rate / periods_per_year
    return excess_returns.mean() / excess_returns.std() * np.sqrt(periods_per_year)


def calculate_max_drawdown(returns: Union[pd.Series, pd.DataFrame]) -> Union[float, pd.Series]:
    """
    Calculate maximum drawdown.
    
    Mathematical formulation:
    DD_t = (Peak_t - Trough_t) / Peak_t
    MDD = max(DD_t)
    
    Args:
        returns: Returns data
        
    Returns:
        Maximum drawdown
    """
    cumulative = (1 + returns).cumprod()
    rolling_max = cumulative.expanding().max()
    drawdown = (cumulative - rolling_max) / rolling_max
    return drawdown.min()


def calculate_calmar_ratio(returns: Union[pd.Series, pd.DataFrame],
                          periods_per_year: int = TRADING_DAYS_PER_YEAR) -> Union[float, pd.Series]:
    """
    Calculate Calmar ratio (annual return / max drawdown).
    
    Args:
        returns: Returns data
        periods_per_year: Number of periods per year
        
    Returns:
        Calmar ratio
    """
    annual_return = annualize_returns(returns, periods_per_year)
    max_dd = abs(calculate_max_drawdown(returns))
    
    if isinstance(max_dd, pd.Series):
        max_dd = max_dd.replace(0, np.nan)  # Avoid division by zero
    elif max_dd == 0:
        max_dd = np.nan
    
    return annual_return / max_dd


def rebalance_dates(start_date: Union[str, datetime],
                   end_date: Union[str, datetime],
                   frequency: str = 'monthly') -> List[datetime]:
    """
    Generate rebalancing dates based on frequency.
    
    Args:
        start_date: Start date
        end_date: End date
        frequency: Rebalancing frequency ('daily', 'weekly', 'monthly', 'quarterly')
        
    Returns:
        List of rebalancing dates
    """
    if isinstance(start_date, str):
        start_date = pd.to_datetime(start_date)
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date)
    
    if frequency == 'daily':
        dates = pd.bdate_range(start_date, end_date, freq='B')
    elif frequency == 'weekly':
        dates = pd.bdate_range(start_date, end_date, freq='W-FRI')
    elif frequency == 'monthly':
        dates = pd.bdate_range(start_date, end_date, freq='BM')
    elif frequency == 'quarterly':
        dates = pd.bdate_range(start_date, end_date, freq='BQ')
    else:
        raise ValueError(f"Unknown frequency: {frequency}")
    
    return dates.tolist()


def winsorize_data(data: Union[pd.Series, pd.DataFrame],
                  lower_quantile: float = 0.01,
                  upper_quantile: float = 0.99) -> Union[pd.Series, pd.DataFrame]:
    """
    Winsorize data to handle outliers.
    
    Args:
        data: Data to winsorize
        lower_quantile: Lower quantile for winsorization
        upper_quantile: Upper quantile for winsorization
        
    Returns:
        Winsorized data
    """
    if isinstance(data, pd.Series):
        lower_bound = data.quantile(lower_quantile)
        upper_bound = data.quantile(upper_quantile)
        return data.clip(lower=lower_bound, upper=upper_bound)
    else:
        result = data.copy()
        for col in data.columns:
            lower_bound = data[col].quantile(lower_quantile)
            upper_bound = data[col].quantile(upper_quantile)
            result[col] = data[col].clip(lower=lower_bound, upper=upper_bound)
        return result


def correlation_matrix_plot(data: pd.DataFrame,
                           title: str = "Correlation Matrix",
                           figsize: Tuple[int, int] = (10, 8),
                           save_path: Optional[str] = None) -> None:
    """
    Plot correlation matrix heatmap.

    Args:
        data: Data for correlation calculation
        title: Plot title
        figsize: Figure size
        save_path: Optional path to save the plot
    """
    if plt is None or sns is None:
        raise ImportError("matplotlib and seaborn are required for plotting. Install them with: pip install matplotlib seaborn")

    corr_matrix = data.corr()

    plt.figure(figsize=figsize)
    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0,
                square=True, fmt='.2f', cbar_kws={'shrink': 0.8})
    plt.title(title)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    plt.show()


def ensure_directory_exists(path: str) -> Path:
    """
    Ensure directory exists, create if necessary.
    
    Args:
        path: Directory path
        
    Returns:
        Path object
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def format_percentage(value: float, decimal_places: int = 2) -> str:
    """
    Format value as percentage string.
    
    Args:
        value: Value to format
        decimal_places: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    return f"{value * 100:.{decimal_places}f}%"


def timing_decorator(func):
    """
    Decorator to time function execution.
    
    Args:
        func: Function to time
        
    Returns:
        Wrapped function with timing
    """
    import time
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        logger = logging.getLogger(__name__)
        logger.info(f"{func.__name__} executed in {end_time - start_time:.2f} seconds")
        
        return result
    
    return wrapper


# Global configuration instance
global_config = TradingConfig()


if __name__ == "__main__":
    # Example usage
    print("Trading System Utilities")
    print(f"Trading days per year: {TRADING_DAYS_PER_YEAR}")
    print(f"Default risk-free rate: {format_percentage(DEFAULT_RISK_FREE_RATE)}")
    
    # Test configuration
    config = TradingConfig()
    print(f"\nDefault configuration:")
    print(f"Tickers: {config.tickers}")
    print(f"Start date: {config.start_date}")
    print(f"Optimization method: {config.optimization_method}")
    
    # Test data validation
    test_data = pd.DataFrame({
        'Asset1': np.random.randn(100).cumsum() + 100,
        'Asset2': np.random.randn(100).cumsum() + 100
    }, index=pd.date_range('2020-01-01', periods=100))
    
    is_valid, issues = validate_data(test_data)
    print(f"\nData validation: {'Valid' if is_valid else 'Invalid'}")
    if issues:
        print(f"Issues: {issues}")
    
    # Test returns calculation
    returns = calculate_returns(test_data)
    print(f"\nReturns shape: {returns.shape}")
    print(f"Mean returns: {returns.mean().values}")
    
    # Test performance metrics
    sharpe = calculate_sharpe_ratio(returns)
    max_dd = calculate_max_drawdown(returns)
    
    print(f"\nPerformance metrics:")
    print(f"Sharpe ratios: {sharpe.values}")
    print(f"Max drawdowns: {max_dd.values}")
    
    # Test rebalancing dates
    rebal_dates = rebalance_dates('2023-01-01', '2023-12-31', 'monthly')
    print(f"\nMonthly rebalancing dates in 2023: {len(rebal_dates)} dates")
    print(f"First few: {[d.strftime('%Y-%m-%d') for d in rebal_dates[:3]]}")