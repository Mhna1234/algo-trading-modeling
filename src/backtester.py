"""
Backtesting Engine Module

This module provides a comprehensive backtesting framework for algorithmic trading strategies.
It supports:
- Portfolio rebalancing with transaction costs
- Rolling window re-estimation
- Multiple performance metrics tracking
- Benchmark comparison
- Position sizing and risk management

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
    Comprehensive backtesting engine for algorithmic trading strategies.
    
    This class simulates the execution of a trading strategy over historical data,
    accounting for transaction costs, rebalancing frequency, and various constraints.
    """
    
    def __init__(self, 
                 config: Optional[TradingConfig] = None,
                 initial_capital: float = 100000.0,
                 transaction_cost: float = 0.001,
                 rebalance_frequency: str = 'monthly',
                 benchmark_ticker: str = 'SPY'):
        """
        Initialize Backtester with configuration.
        
        Args:
            config: Trading configuration object
            initial_capital: Starting portfolio value
            transaction_cost: Transaction cost rate (e.g., 0.001 = 0.1%)
            rebalance_frequency: How often to rebalance ('daily', 'weekly', 'monthly')
            benchmark_ticker: Benchmark ticker for comparison
        """
        self.config = config or TradingConfig()
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        self.rebalance_frequency = rebalance_frequency
        self.benchmark_ticker = benchmark_ticker
        
        # Results storage
        self.results = None
        self.is_fitted = False
        
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
    from src.forecasting import forecast_returns_volatility
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