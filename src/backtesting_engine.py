"""
Backtesting Engine Module - Legacy Wrapper

This module provides backward compatibility with the old backtesting API
while using the new PortfolioEngine architecture underneath.

For new code, use PortfolioEngine and strategy wrappers directly:
    from src.portfolio_engine import PortfolioEngine
    from src.strategies import MomentumStrategy
    
    portfolio = PortfolioEngine(prices)
    strategy = MomentumStrategy(...)
    result = portfolio.run_backtest(strategy, ...)

Mathematical Formulations:
- Portfolio Return: R_p,t = Σ w_{i,t-1} * R_{i,t}
- Transaction Costs: TC_t = κ * Σ |w_{i,t} - w_{i,t-1}|
- Net Asset Value: NAV_t = NAV_{t-1} * (1 + R_p,t - TC_t)
- Drawdown: DD_t = (Peak_t - NAV_t) / Peak_t
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Callable
import warnings
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
import matplotlib.pyplot as plt

from .portfolio_engine import PortfolioEngine, PortfolioResult
from .strategies import MomentumStrategy, BaseStrategyWrapper
from .backtesting_methods import WalkForwardFold
from .utils import (
    TradingConfig, calculate_returns, rebalance_dates, 
    calculate_sharpe_ratio, calculate_max_drawdown, timing_decorator
)

logger = logging.getLogger(__name__)

@dataclass
class BacktestResults:
    """Container for backtest results and metrics."""
    
    # Time series data
    portfolio_returns: pd.Series
    portfolio_weights: pd.DataFrame
    portfolio_nav: pd.Series
    benchmark_returns: pd.Series
    benchmark_nav: pd.Series
    transaction_costs: pd.Series
    turnover: pd.Series
    
    # Summary metrics
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    calmar_ratio: float
    
    # Benchmark comparison
    benchmark_total_return: float
    benchmark_sharpe: float
    excess_return: float
    information_ratio: float
    beta: float
    alpha: float
    
    # Trading metrics
    total_trades: int
    avg_turnover: float
    total_transaction_costs: float
    
    # Risk metrics
    var_95: float
    cvar_95: float
    downside_deviation: float
    sortino_ratio: float
    
    def summary(self) -> Dict[str, float]:
        """Return summary dictionary of key metrics."""
        return {
            'Total Return': self.total_return,
            'Annualized Return': self.annualized_return,
            'Volatility': self.volatility,
            'Sharpe Ratio': self.sharpe_ratio,
            'Max Drawdown': self.max_drawdown,
            'Calmar Ratio': self.calmar_ratio,
            'Benchmark Return': self.benchmark_total_return,
            'Excess Return': self.excess_return,
            'Information Ratio': self.information_ratio,
            'Beta': self.beta,
            'Alpha': self.alpha,
            'Total Trades': self.total_trades,
            'Avg Turnover': self.avg_turnover,
            'Transaction Costs': self.total_transaction_costs
        }


class Backtester:
    """
    LEGACY WRAPPER - Maintains old API while using new PortfolioEngine.
    
    For new code, use PortfolioEngine directly:
        portfolio = PortfolioEngine(prices)
        strategy = MomentumStrategy(...)
        result = portfolio.run_backtest(strategy, ...)
    
    This class provides backward compatibility with existing code that uses
    the old Backtester API.
    """
    
    def __init__(self, 
                 strategy=None,
                 optimizer=None,
                 rebal_freq: str = 'M',
                 tc_bps: float = 5.0,
                 slippage_bps: float = 1.0,
                 config: Optional[TradingConfig] = None,
                 initial_capital: float = 1000000.0,
                 transaction_cost: float = 0.0005,
                 rebalance_frequency: str = 'monthly',
                 benchmark_ticker: str = 'SPY'):
        """
        Initialize Backtester with configuration.
        
        Args:
            strategy: Strategy object (from strategy.py)
            optimizer: PortfolioOptimizer object
            rebal_freq: Rebalancing frequency ('D', 'W', 'M', 'Q')
            tc_bps: Transaction cost in basis points
            slippage_bps: Slippage in basis points
            config: Trading configuration object (legacy)
            initial_capital: Starting portfolio value
            transaction_cost: Transaction cost rate (legacy, converted to bps)
            rebalance_frequency: How often to rebalance (legacy)
            benchmark_ticker: Benchmark ticker for comparison
        """
        # New API parameters
        self.strategy = strategy
        self.optimizer = optimizer
        self.rebal_freq = rebal_freq
        
        # Convert legacy parameters to new format
        if tc_bps == 5.0 and transaction_cost != 0.0005:
            # User provided old transaction_cost
            tc_bps = transaction_cost * 10000
        
        self.tc_bps = tc_bps
        self.slippage_bps = slippage_bps
        
        # Legacy parameters
        self.config = config or TradingConfig()
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        self.benchmark_ticker = benchmark_ticker
        
        # Map old frequency to new
        freq_map = {'daily': 'D', 'weekly': 'W', 'monthly': 'M', 'quarterly': 'Q'}
        if rebalance_frequency.lower() in freq_map:
            self.rebal_freq = freq_map[rebalance_frequency.lower()]
        else:
            self.rebalance_frequency = rebalance_frequency
        
        # Portfolio engine (created when needed)
        self.portfolio = None
        self._result = None
        
        # Results storage
        self.results = None
        self.is_fitted = False
        self.weights = None
        self.trades = None
        
    def run(self,
            start_date: str,
            end_date: Optional[str] = None,
            objective: str = 'cvar',
            top_n: int = 10,
            **kwargs) -> pd.DataFrame:
        """
        Legacy run method - converts to new PortfolioEngine API.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (optional)
            objective: Optimization objective ('cvar', 'mvo', 'sharpe', etc.)
            top_n: Number of assets to hold
            **kwargs: Additional strategy parameters
        
        Returns:
            DataFrame with legacy format (wealth, return columns)
        """
        if self.strategy is None or self.optimizer is None:
            raise ValueError("Must provide strategy and optimizer to use legacy run() method")
        
        # Create portfolio engine
        self.portfolio = PortfolioEngine(
            prices=self.strategy.prices,
            initial_capital=self.initial_capital,
            transaction_cost_bps=self.tc_bps,
            slippage_bps=self.slippage_bps
        )
        
        # Create strategy wrapper based on objective
        if objective == 'cvar':
            from .strategies import CVaRMinimizationStrategy
            wrapper = CVaRMinimizationStrategy(
                self.strategy, self.optimizer,
                alpha=kwargs.get('alpha', 0.95),
                max_weight=kwargs.get('max_weight', 0.4)
            )
        elif objective in ['momentum', 'mom']:
            from .strategies import MomentumStrategy
            wrapper = MomentumStrategy(
                self.strategy, self.optimizer,
                top_k=top_n,
                objective='cvar',
                **kwargs
            )
        else:
            # Default to momentum with specified objective
            wrapper = MomentumStrategy(
                self.strategy, self.optimizer,
                top_k=top_n,
                objective=objective,
                **kwargs
            )
        
        # Run backtest
        self._result = self.portfolio.run_backtest(
            wrapper,
            start_date=start_date,
            end_date=end_date,
            rebalance_freq=self.rebal_freq
        )
        
        # Store for legacy methods
        self.weights = self._result.weights_history
        self.trades = self._result.trades_history
        self.is_fitted = True
        
        # Convert to legacy DataFrame format
        return self._build_legacy_dataframe(self._result)
    
    def _build_legacy_dataframe(self, result: PortfolioResult) -> pd.DataFrame:
        """Convert new PortfolioResult to old DataFrame format."""
        df = pd.DataFrame({
            'wealth': result.equity_curve,
            'return': result.returns_series
        })
        return df
    
    def metrics(self) -> dict:
        """Return performance metrics (legacy method)."""
        if self._result is None:
            raise ValueError("Must call run() first")
        
        # Map new metric names to old names for compatibility
        old_metrics = {
            'Annual Return': self._result.summary_metrics['annual_return'],
            'Annual Volatility': self._result.summary_metrics['annual_volatility'],
            'Sharpe Ratio': self._result.summary_metrics['sharpe_ratio'],
            'Max Drawdown': self._result.summary_metrics['max_drawdown'],
            'Calmar Ratio': self._result.summary_metrics.get('calmar_ratio', 0.0),
            'Total Return': self._result.summary_metrics['total_return'],
        }
        
        return old_metrics
    
    def calculate_transaction_costs(self, 
                                  old_weights: np.ndarray,
                                  new_weights: np.ndarray,
                                  portfolio_value: float) -> float:
        """
        Calculate transaction costs based on weight changes.
        
        Mathematical formulation:
        TC = κ * Σ |w_new - w_old| * Portfolio_Value
        
        Args:
            old_weights: Previous portfolio weights
            new_weights: New target weights
            portfolio_value: Current portfolio value
            
        Returns:
            Transaction costs in dollars
        """
        if old_weights is None:
            # First period: assume we're moving from cash
            turnover = np.sum(np.abs(new_weights))
        else:
            turnover = np.sum(np.abs(new_weights - old_weights))
        
        return self.transaction_cost * turnover * portfolio_value
    
    def rebalance_portfolio(self, 
                          target_weights: np.ndarray,
                          current_weights: Optional[np.ndarray],
                          current_value: float,
                          min_trade_size: float = 100.0) -> Tuple[np.ndarray, float]:
        """
        Rebalance portfolio to target weights.
        
        Args:
            target_weights: Target portfolio weights
            current_weights: Current portfolio weights
            current_value: Current portfolio value
            min_trade_size: Minimum trade size to execute
            
        Returns:
            Tuple of (actual_weights, transaction_costs)
        """
        # Calculate transaction costs
        transaction_costs = self.calculate_transaction_costs(
            current_weights, target_weights, current_value)
        
        # Check if trades are worth executing
        if current_weights is not None:
            weight_changes = np.abs(target_weights - current_weights)
            trade_values = weight_changes * current_value
            
            # Don't trade if all changes are below minimum trade size
            if np.all(trade_values < min_trade_size):
                return current_weights, 0.0
        
        return target_weights, transaction_costs
    
    @timing_decorator
    def run_backtest(self, 
                    price_data: pd.DataFrame,
                    weight_data: pd.DataFrame,
                    benchmark_data: Optional[pd.DataFrame] = None,
                    signals_data: Optional[pd.DataFrame] = None) -> BacktestResults:
        """
        Run the backtest simulation.
        
        Args:
            price_data: Historical price data for assets
            weight_data: Target portfolio weights over time
            benchmark_data: Benchmark price data
            signals_data: Optional trading signals data
            
        Returns:
            BacktestResults object with comprehensive metrics
        """
        logger.info("Starting backtest simulation")
        
        # Align data
        common_dates = price_data.index.intersection(weight_data.index)
        price_data = price_data.loc[common_dates]
        weight_data = weight_data.loc[common_dates]
        
        if benchmark_data is not None:
            benchmark_data = benchmark_data.loc[common_dates]
        
        # Calculate returns
        returns_data = calculate_returns(price_data)
        
        # Initialize tracking variables
        portfolio_nav = [self.initial_capital]
        portfolio_returns = []
        actual_weights = []
        transaction_costs = []
        turnover = []
        
        current_weights = None
        current_nav = self.initial_capital
        
        # Determine rebalancing dates
        rebal_dates = rebalance_dates(
            common_dates[0], common_dates[-1], self.rebalance_frequency)
        rebal_dates = [d for d in rebal_dates if d in common_dates]
        
        logger.info(f"Backtesting over {len(common_dates)} days with {len(rebal_dates)} rebalances")
        
        # Main simulation loop
        for i, date in enumerate(common_dates):
            # Check if this is a rebalancing date
            is_rebalance_date = date in rebal_dates
            
            # Get target weights for this date
            if date in weight_data.index:
                target_weights = weight_data.loc[date].values
                
                # Ensure weights sum to 1 and handle NaN
                target_weights = np.nan_to_num(target_weights)
                if np.sum(target_weights) > 0:
                    target_weights = target_weights / np.sum(target_weights)
                else:
                    target_weights = np.ones(len(target_weights)) / len(target_weights)
            else:
                # Use previous weights if no new weights available
                target_weights = current_weights if current_weights is not None else \
                               np.ones(len(price_data.columns)) / len(price_data.columns)
            
            # Rebalance if needed
            transaction_cost = 0.0
            if is_rebalance_date or current_weights is None:
                current_weights, transaction_cost = self.rebalance_portfolio(
                    target_weights, current_weights, current_nav)
            
            # Calculate daily return
            if i > 0 and date in returns_data.index:
                daily_returns = returns_data.loc[date].values
                portfolio_return = np.dot(current_weights, daily_returns)
                
                # Update NAV after return and transaction costs
                current_nav = current_nav * (1 + portfolio_return) - transaction_cost
            else:
                portfolio_return = 0.0
                current_nav = current_nav - transaction_cost
            
            # Store results
            portfolio_nav.append(current_nav)
            portfolio_returns.append(portfolio_return)
            actual_weights.append(current_weights.copy())
            transaction_costs.append(transaction_cost)
            
            # Calculate turnover
            if i > 0 and len(actual_weights) > 1:
                turnover_val = np.sum(np.abs(actual_weights[-1] - actual_weights[-2]))
            else:
                turnover_val = np.sum(np.abs(current_weights)) if current_weights is not None else 0.0
            turnover.append(turnover_val)
        
        # Convert to pandas objects
        portfolio_nav = pd.Series(portfolio_nav[1:], index=common_dates, name='Portfolio_NAV')
        portfolio_returns = pd.Series(portfolio_returns, index=common_dates, name='Portfolio_Return')
        actual_weights_df = pd.DataFrame(actual_weights, index=common_dates, columns=price_data.columns)
        transaction_costs_series = pd.Series(transaction_costs, index=common_dates, name='Transaction_Costs')
        turnover_series = pd.Series(turnover, index=common_dates, name='Turnover')
        
        # Process benchmark
        if benchmark_data is not None:
            benchmark_returns = calculate_returns(benchmark_data.iloc[:, 0])
            benchmark_nav = (1 + benchmark_returns).cumprod() * self.initial_capital
        else:
            benchmark_returns = pd.Series(index=common_dates, dtype=float).fillna(0)
            benchmark_nav = pd.Series(index=common_dates, dtype=float).fillna(self.initial_capital)
        
        # Calculate metrics
        results = self._calculate_metrics(
            portfolio_returns, portfolio_nav, actual_weights_df,
            transaction_costs_series, turnover_series,
            benchmark_returns, benchmark_nav
        )
        
        self.results = results
        self.is_fitted = True
        
        logger.info("Backtest completed successfully")
        return results
    
    def _calculate_metrics(self,
                          portfolio_returns: pd.Series,
                          portfolio_nav: pd.Series,
                          weights: pd.DataFrame,
                          transaction_costs: pd.Series,
                          turnover: pd.Series,
                          benchmark_returns: pd.Series,
                          benchmark_nav: pd.Series) -> BacktestResults:
        """Calculate comprehensive performance metrics."""
        
        # Portfolio metrics
        total_return = (portfolio_nav.iloc[-1] / self.initial_capital) - 1
        annualized_return = (1 + total_return) ** (252 / len(portfolio_returns)) - 1
        volatility = portfolio_returns.std() * np.sqrt(252)
        sharpe_ratio = calculate_sharpe_ratio(portfolio_returns, self.config.risk_free_rate)
        max_drawdown = calculate_max_drawdown(portfolio_returns)
        
        # Calmar ratio
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else np.nan
        
        # Benchmark metrics
        if len(benchmark_returns) > 0 and not benchmark_returns.isna().all():
            benchmark_total_return = (benchmark_nav.iloc[-1] / self.initial_capital) - 1
            benchmark_sharpe = calculate_sharpe_ratio(benchmark_returns, self.config.risk_free_rate)
            
            # Excess return and information ratio
            excess_returns = portfolio_returns - benchmark_returns
            excess_return = excess_returns.mean() * 252
            information_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252) \
                              if excess_returns.std() > 0 else 0
            
            # Beta and Alpha
            aligned_returns = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
            if len(aligned_returns) > 10:
                beta = aligned_returns.cov().iloc[0, 1] / aligned_returns.iloc[:, 1].var()
                alpha = (annualized_return - self.config.risk_free_rate) - \
                       beta * (benchmark_sharpe * volatility)
            else:
                beta, alpha = np.nan, np.nan
        else:
            benchmark_total_return = 0
            benchmark_sharpe = 0
            excess_return = annualized_return
            information_ratio = 0
            beta, alpha = np.nan, np.nan
        
        # Trading metrics
        total_trades = len(weights)
        avg_turnover = turnover.mean()
        total_transaction_costs = transaction_costs.sum()
        
        # Risk metrics
        var_95 = portfolio_returns.quantile(0.05)
        cvar_95 = portfolio_returns[portfolio_returns <= var_95].mean()
        
        # Downside deviation and Sortino ratio
        downside_returns = portfolio_returns[portfolio_returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        sortino_ratio = annualized_return / downside_deviation if downside_deviation > 0 else np.nan
        
        return BacktestResults(
            portfolio_returns=portfolio_returns,
            portfolio_weights=weights,
            portfolio_nav=portfolio_nav,
            benchmark_returns=benchmark_returns,
            benchmark_nav=benchmark_nav,
            transaction_costs=transaction_costs,
            turnover=turnover,
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            calmar_ratio=calmar_ratio,
            benchmark_total_return=benchmark_total_return,
            benchmark_sharpe=benchmark_sharpe,
            excess_return=excess_return,
            information_ratio=information_ratio,
            beta=beta,
            alpha=alpha,
            total_trades=total_trades,
            avg_turnover=avg_turnover,
            total_transaction_costs=total_transaction_costs,
            var_95=var_95,
            cvar_95=cvar_95,
            downside_deviation=downside_deviation,
            sortino_ratio=sortino_ratio
        )
    
    def rolling_metrics(self, window: int = 252) -> pd.DataFrame:
        """
        Calculate rolling performance metrics.
        
        Args:
            window: Rolling window size in days
            
        Returns:
            DataFrame with rolling metrics
        """
        if not self.is_fitted:
            raise ValueError("Backtester must be run before calculating rolling metrics")
        
        returns = self.results.portfolio_returns
        
        rolling_metrics = pd.DataFrame(index=returns.index)
        rolling_metrics['Rolling_Return'] = returns.rolling(window).mean() * 252
        rolling_metrics['Rolling_Volatility'] = returns.rolling(window).std() * np.sqrt(252)
        rolling_metrics['Rolling_Sharpe'] = (
            (returns.rolling(window).mean() - self.config.risk_free_rate / 252) /
            returns.rolling(window).std() * np.sqrt(252)
        )
        
        # Rolling max drawdown
        nav = self.results.portfolio_nav
        rolling_max = nav.rolling(window).max()
        rolling_drawdown = (nav - rolling_max) / rolling_max
        rolling_metrics['Rolling_MaxDD'] = rolling_drawdown.rolling(window).min()
        
        return rolling_metrics
    
    def plot_results(self, figsize: Tuple[int, int] = (15, 10), save_path: Optional[str] = None):
        """
        Plot backtest results.
        
        Args:
            figsize: Figure size
            save_path: Optional path to save the plot
        """
        if not self.is_fitted:
            raise ValueError("Backtester must be run before plotting")
        
        fig, axes = plt.subplots(2, 2, figsize=figsize)
        
        # Portfolio NAV
        axes[0, 0].plot(self.results.portfolio_nav.index, self.results.portfolio_nav.values, 
                       label='Portfolio', linewidth=2)
        if not self.results.benchmark_nav.isna().all():
            axes[0, 0].plot(self.results.benchmark_nav.index, self.results.benchmark_nav.values,
                           label='Benchmark', linewidth=1, alpha=0.7)
        axes[0, 0].set_title('Portfolio Value Over Time')
        axes[0, 0].set_ylabel('Portfolio Value ($)')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # Rolling Sharpe ratio
        rolling_metrics = self.rolling_metrics(window=60)
        axes[0, 1].plot(rolling_metrics.index, rolling_metrics['Rolling_Sharpe'])
        axes[0, 1].set_title('Rolling Sharpe Ratio (60-day)')
        axes[0, 1].set_ylabel('Sharpe Ratio')
        axes[0, 1].grid(True, alpha=0.3)
        
        # Drawdown
        cumulative = self.results.portfolio_nav / self.initial_capital
        rolling_max = cumulative.expanding().max()
        drawdown = (cumulative - rolling_max) / rolling_max
        axes[1, 0].fill_between(drawdown.index, drawdown.values, 0, alpha=0.7, color='red')
        axes[1, 0].set_title('Portfolio Drawdown')
        axes[1, 0].set_ylabel('Drawdown (%)')
        axes[1, 0].grid(True, alpha=0.3)
        
        # Portfolio weights over time
        if len(self.results.portfolio_weights.columns) <= 10:
            self.results.portfolio_weights.plot(kind='area', stacked=True, ax=axes[1, 1], alpha=0.7)
            axes[1, 1].set_title('Portfolio Weights Over Time')
            axes[1, 1].set_ylabel('Weight')
            axes[1, 1].legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        else:
            # Too many assets, just show total exposure
            total_exposure = self.results.portfolio_weights.sum(axis=1)
            axes[1, 1].plot(total_exposure.index, total_exposure.values)
            axes[1, 1].set_title('Total Portfolio Exposure')
            axes[1, 1].set_ylabel('Total Weight')
        
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()


if __name__ == "__main__":
    # Example usage
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from src.data_loader import load_data
    from src.feature_engineering import make_features
    # from src.forecasting import forecast_returns_volatility  # Removed: forecasting module deprecated
    from src.optimizer import optimize_portfolio_forecasted
    
    # Load sample data
    tickers = ['AAPL', 'MSFT', 'SPY']
    start_date = '2020-01-01'
    end_date = '2023-01-01'
    
    try:
        _, price_data = load_data(tickers, start_date, end_date)
        features = make_features(price_data)
        
        # Create simple equal-weight strategy for testing
        weights = pd.DataFrame(
            index=price_data.index,
            columns=price_data.columns,
            data=1/len(price_data.columns)
        )
        
        # Initialize backtester
        config = TradingConfig()
        config.risk_free_rate = 0.02
        
        backtester = Backtester(
            config=config,
            initial_capital=100000,
            transaction_cost=0.001,
            rebalance_frequency='monthly'
        )
        
        # Run backtest
        results = backtester.run_backtest(
            price_data=price_data,
            weight_data=weights,
            benchmark_data=price_data[['SPY']]  # Use SPY as benchmark
        )
        
        # Print results
        print("Backtest Results:")
        print("-" * 50)
        summary = results.summary()
        for metric, value in summary.items():
            if isinstance(value, float):
                if 'Return' in metric or 'Alpha' in metric:
                    print(f"{metric}: {value:.2%}")
                elif 'Ratio' in metric or 'Beta' in metric:
                    print(f"{metric}: {value:.3f}")
                elif 'Costs' in metric:
                    print(f"{metric}: ${value:,.2f}")
                else:
                    print(f"{metric}: {value:.4f}")
            else:
                print(f"{metric}: {value}")
        
        # Plot results
        backtester.plot_results(figsize=(12, 8))
        
    except Exception as e:
        print(f"Error in example: {e}")
        print("Note: This example requires other modules to be working")


"""
Advanced Backtesting Methods Module

This module implements multiple sophisticated backtesting methodologies to validate
trading strategies and reduce overfitting risk:

1. Vanilla Backtest - Traditional single-run historical backtest
2. Walk-Forward Backtest - Rolling/expanding window with train/test splits
3. Cross-Validation Backtest - Time-series k-fold validation
4. Monte Carlo Backtest - Synthetic data generation for robustness testing
5. Randomized Backtest - Multiple randomized starting points

Mathematical Foundations:
- Walk-Forward: Periodic re-optimization with out-of-sample testing
- Cross-Validation: Temporal splits preserving time-series order
- Monte Carlo: Bootstrap resampling and parametric simulation
- Randomized: Permutation testing for statistical significance
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Callable, Union
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm

from .portfolio_engine import PortfolioEngine, PortfolioResult
from .strategies import BaseStrategyWrapper
from .utils import calculate_sharpe_ratio, calculate_max_drawdown

logger = logging.getLogger(__name__)


@dataclass
class BacktestMethodResult:
    """Container for results from advanced backtesting methods."""
    
    method_name: str
    individual_results: List[PortfolioResult]
    aggregate_metrics: Dict[str, float]
    confidence_intervals: Dict[str, Tuple[float, float]]
    metadata: Dict[str, any]
    
    def summary(self) -> Dict[str, any]:
        """Return comprehensive summary of results."""
        return {
            'method': self.method_name,
            'num_runs': len(self.individual_results),
            'metrics': self.aggregate_metrics,
            'confidence_intervals': self.confidence_intervals,
            'metadata': self.metadata
        }


class BacktestingMethods:
    """
    Advanced backtesting methodologies for robust strategy validation.
    
    This class provides multiple backtesting approaches to assess strategy
    performance under different conditions and reduce overfitting risk.
    """
    
    def __init__(self,
                 prices: pd.DataFrame,
                 initial_capital: float = 1000000.0,
                 transaction_cost_bps: float = 5.0,
                 slippage_bps: float = 1.0,
                 enable_soft_rebalance: bool = False,
                 drift_threshold: float = 0.05):
        """
        Initialize backtesting methods framework.
        
        Args:
            prices: Historical price data
            initial_capital: Starting portfolio value
            transaction_cost_bps: Transaction costs in basis points
            slippage_bps: Slippage in basis points
        """
        self.prices = prices
        self.initial_capital = initial_capital
        self.transaction_cost_bps = transaction_cost_bps
        self.slippage_bps = slippage_bps
        self.enable_soft_rebalance = enable_soft_rebalance
        self.drift_threshold = drift_threshold
        
    def vanilla_backtest(self,
                        strategy: BaseStrategyWrapper,
                        start_date: str,
                        end_date: Optional[str] = None,
                        rebalance_freq: str = 'M') -> BacktestMethodResult:
        """
        Traditional single-run backtest over entire historical period.
        
        Args:
            strategy: Strategy wrapper to test
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (optional)
            rebalance_freq: Rebalancing frequency
            
        Returns:
            BacktestMethodResult with single run
        """
        logger.info("Running Vanilla Backtest")
        
        portfolio = PortfolioEngine(
            self.prices,
            initial_capital=self.initial_capital,
            transaction_cost_bps=self.transaction_cost_bps,
            slippage_bps=self.slippage_bps
        )
        result = portfolio.run_backtest(
            strategy,
            start_date=start_date,
            end_date=end_date,
            rebalance_freq=rebalance_freq,
            soft_rebalance=self.enable_soft_rebalance,
            drift_threshold=self.drift_threshold,
            backtest_method='vanilla'
        )
        
        return BacktestMethodResult(
            method_name='Vanilla Backtest',
            individual_results=[result],
            aggregate_metrics=result.summary_metrics,
            confidence_intervals={},
            metadata={
                'start_date': start_date,
                'end_date': end_date,
                'rebalance_freq': rebalance_freq
            }
        )
    
    def walk_forward_backtest(self,
                             strategy: BaseStrategyWrapper,
                             start_date: str,
                             end_date: Optional[str] = None,
                             train_window_months: int = 24,
                             test_window_months: int = 6,
                             step_months: int = 3,
                             rebalance_freq: str = 'M',
                             anchored: bool = False) -> BacktestMethodResult:
        """
        Walk-forward analysis with rolling/expanding windows.

        This method implements mathematically correct walk-forward backtesting:
        1. Splits data into non-overlapping train/test periods
        2. Restricts strategy data access to training period during testing
        3. Validates fold boundaries to prevent information leakage
        4. Rolls forward and repeats with proper temporal isolation

        Mathematical Foundation:
        - Rolling Window: Train[t-k, t] → Test[t+1, t+m]
        - Expanding Window: Train[0, t] → Test[t+1, t+m]
        - No overlap: train_end < test_start
        - No look-ahead: max_date = train_end during testing

        Args:
            strategy: Strategy wrapper to test
            start_date: Start date
            end_date: End date (optional)
            train_window_months: Training window size in months
            test_window_months: Test window size in months
            step_months: Step size for rolling window in months
            rebalance_freq: Rebalancing frequency
            anchored: If True, use expanding window; if False, use rolling window

        Returns:
            BacktestMethodResult with multiple walk-forward runs
        """
        logger.info(f"Running Walk-Forward Backtest ({'Anchored' if anchored else 'Rolling'})")

        # Parse dates
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date) if end_date else self.prices.index[-1]

        results = []
        folds = []

        current_train_start = start

        while True:
            # Define train period
            if anchored:
                train_start = start  # Expanding window
            else:
                train_start = current_train_start  # Rolling window

            train_end = current_train_start + pd.DateOffset(months=train_window_months)

            # Define test period
            test_start = train_end + pd.Timedelta(days=1)
            test_end = test_start + pd.DateOffset(months=test_window_months)

            # Check if we've reached the end
            if test_end > end:
                break

            # Create fold object with validation
            fold = WalkForwardFold(
                fold_number=len(folds) + 1,
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                metadata={
                    'window_type': 'anchored' if anchored else 'rolling',
                    'train_window_months': train_window_months,
                    'test_window_months': test_window_months
                }
            )

            # Validate fold boundaries to prevent information leakage
            if not fold.validate_fold_boundaries():
                logger.warning(f"Invalid fold boundaries for fold {fold.fold_number}: {fold.get_fold_info()}")
                # Skip invalid fold
                current_train_start += pd.DateOffset(months=step_months)
                continue

            logger.info(f"Fold {fold.fold_number}: {fold.get_fold_info()}")
            folds.append(fold)

            # Reset strategy state for fold isolation (e.g., MAB reset)
            if hasattr(strategy, 'reset'):
                strategy.reset()

            # Set data availability to training period end to prevent look-ahead bias
            def set_max_date_recursive(strat, max_date):
                """Recursively set max_date on strategy and any child strategies."""
                if hasattr(strat, 'strategy') and hasattr(strat.strategy, 'set_max_date'):
                    strat.strategy.set_max_date(max_date)
                # For bandit wrappers, also set on child strategies
                if hasattr(strat, 'child_strategies'):
                    for child in strat.child_strategies:
                        set_max_date_recursive(child, max_date)

            set_max_date_recursive(strategy, train_end)

            try:
                # Run backtest on test period with data restriction
                portfolio = PortfolioEngine(
                    self.prices,
                    initial_capital=self.initial_capital,
                    transaction_cost_bps=self.transaction_cost_bps,
                    slippage_bps=self.slippage_bps
                )

                result = portfolio.run_backtest(
                    strategy,
                    start_date=test_start.strftime('%Y-%m-%d'),
                    end_date=test_end.strftime('%Y-%m-%d'),
                    rebalance_freq=rebalance_freq,
                    soft_rebalance=self.enable_soft_rebalance,
                    drift_threshold=self.drift_threshold,
                    backtest_method='vanilla'
                )

                results.append(result)

                # Store fold information in result metadata
                if hasattr(result, 'metadata'):
                    result.metadata.update({
                        'fold_info': fold.get_fold_info(),
                        'fold_number': fold.fold_number
                    })

            except Exception as e:
                logger.warning(f"Fold {fold.fold_number} backtest failed: {e}")

            # Roll forward
            current_train_start += pd.DateOffset(months=step_months)

        # Aggregate results
        aggregate_metrics = self._aggregate_results(results)
        confidence_intervals = self._calculate_confidence_intervals(results)

        method_type = 'Anchored' if anchored else 'Rolling'
        return BacktestMethodResult(
            method_name=f'Walk-Forward Backtest ({method_type})',
            individual_results=results,
            aggregate_metrics=aggregate_metrics,
            confidence_intervals=confidence_intervals,
            metadata={
                'train_window_months': train_window_months,
                'test_window_months': test_window_months,
                'step_months': step_months,
                'anchored': anchored,
                'num_folds': len(folds),
                'folds': [fold.get_fold_info() for fold in folds]
            }
        )
    
    def _block_bootstrap(self, returns: pd.DataFrame, block_size: int) -> pd.DataFrame:
        """Block bootstrap resampling of returns."""
        n_periods = len(returns)
        n_blocks = n_periods // block_size
        
        # Sample blocks with replacement
        sampled_indices = []
        for _ in range(n_blocks + 1):
            start_idx = np.random.randint(0, max(1, n_periods - block_size))
            sampled_indices.extend(range(start_idx, min(start_idx + block_size, n_periods)))
        
        # Trim to original length
        sampled_indices = sampled_indices[:n_periods]
        
        return returns.iloc[sampled_indices].reset_index(drop=True)
    
    def _parametric_simulation(self, returns: pd.DataFrame) -> pd.DataFrame:
        """Generate returns from fitted normal distribution."""
        means = returns.mean()
        cov_matrix = returns.cov()
        
        # Generate multivariate normal samples
        synthetic = np.random.multivariate_normal(means, cov_matrix, size=len(returns))
        
        return pd.DataFrame(synthetic, columns=returns.columns)
    
    def _geometric_brownian_motion(self, returns: pd.DataFrame) -> pd.DataFrame:
        """Generate returns using Geometric Brownian Motion."""
        dt = 1/252  # Daily time step
        means = returns.mean()
        stds = returns.std()
        
        # GBM: dS/S = μ*dt + σ*dW
        synthetic = pd.DataFrame(index=range(len(returns)), columns=returns.columns)
        
        for col in returns.columns:
            mu = means[col]
            sigma = stds[col]
            
            # Generate random shocks
            shocks = np.random.standard_normal(len(returns))
            synthetic[col] = mu * dt + sigma * np.sqrt(dt) * shocks
        
        return synthetic
    
    def _aggregate_results(self, results: List[PortfolioResult]) -> Dict[str, float]:
        """Aggregate metrics across multiple backtest results."""
        if not results:
            return {}
        
        metrics = {}
        
        # Collect all metric values
        metric_values = {}
        for result in results:
            for metric_name, value in result.summary_metrics.items():
                if metric_name not in metric_values:
                    metric_values[metric_name] = []
                metric_values[metric_name].append(value)
        
        # Calculate aggregate statistics
        for metric_name, values in metric_values.items():
            values_array = np.array(values)
            metrics[f'{metric_name}_mean'] = np.mean(values_array)
            metrics[f'{metric_name}_median'] = np.median(values_array)
            metrics[f'{metric_name}_std'] = np.std(values_array)
            metrics[f'{metric_name}_min'] = np.min(values_array)
            metrics[f'{metric_name}_max'] = np.max(values_array)
        
        return metrics
    
    def _calculate_confidence_intervals(self,
                                       results: List[PortfolioResult],
                                       confidence_level: float = 0.95) -> Dict[str, Tuple[float, float]]:
        """Calculate confidence intervals for metrics."""
        if not results:
            return {}
        
        intervals = {}
        alpha = 1 - confidence_level
        
        # Collect metric values
        metric_values = {}
        for result in results:
            for metric_name, value in result.summary_metrics.items():
                if metric_name not in metric_values:
                    metric_values[metric_name] = []
                metric_values[metric_name].append(value)
        
        # Calculate confidence intervals
        for metric_name, values in metric_values.items():
            values_array = np.array(values)
            lower = np.percentile(values_array, alpha/2 * 100)
            upper = np.percentile(values_array, (1 - alpha/2) * 100)
            intervals[metric_name] = (lower, upper)
        
        return intervals
    
    def compare_methods(self,
                       results: List[BacktestMethodResult],
                       save_path: Optional[str] = None) -> pd.DataFrame:
        """
        Compare results from different backtesting methods.
        
        Args:
            results: List of BacktestMethodResult objects
            save_path: Optional path to save comparison table
            
        Returns:
            DataFrame with method comparison
        """
        comparison_data = []
        
        for result in results:
            row = {'Method': result.method_name}
            
            # Add aggregate metrics
            for metric_name, value in result.aggregate_metrics.items():
                row[metric_name] = value
            
            # Add confidence interval widths
            for metric_name, (lower, upper) in result.confidence_intervals.items():
                row[f'{metric_name}_ci_width'] = upper - lower
            
            comparison_data.append(row)
        
        comparison_df = pd.DataFrame(comparison_data)
        
        if save_path:
            comparison_df.to_csv(save_path, index=False)
            logger.info(f"Comparison saved to {save_path}")
        
        return comparison_df


if __name__ == "__main__":
    # Example usage
    print("Backtesting Methods Module")
    print("===========================")
    print("\nAvailable methods:")
    print("1. Vanilla Backtest - Traditional single-run backtest")
    print("2. Walk-Forward Backtest - Rolling/expanding window analysis with proper temporal isolation")
    print("\nMathematically correct walk-forward backtesting prevents look-ahead bias by:")
    print("- Restricting strategy data access to training period during testing")
    print("- Validating fold boundaries to prevent information leakage")
    print("- Using WalkForwardFold structure for proper temporal separation")