"""
Portfolio Engine - Strategy-Agnostic Portfolio Management System

This module provides a complete portfolio management system that:
- Tracks positions, cash, and portfolio value over time
- Executes rebalancing with transaction costs and slippage
- Calculates comprehensive performance metrics in real-time
- Provides dashboard-ready data exports
- Works with any strategy wrapper implementing BaseStrategyWrapper

Author: Portfolio Engine Team
Date: December 2025
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
import warnings
import logging

import numpy as np
import pandas as pd
from pandas import DataFrame, Series

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


@dataclass
class PortfolioState:
    """
    Snapshot of portfolio state at a specific point in time.
    
    This object is passed to strategy wrappers so they can make
    informed decisions based on current positions, historical data,
    and performance metrics.
    
    Attributes
    ----------
    date : pd.Timestamp
        Current date
    current_weights : pd.Series
        Current position weights (including CASH)
    current_shares : pd.Series
        Actual shares held for each asset
    cash : float
        Available cash in portfolio
    equity : float
        Total portfolio value (positions + cash)
    price_history : pd.DataFrame
        Full price history up to current date
    return_history : pd.DataFrame
        Full return history up to current date
    last_rebalance_date : pd.Timestamp
        Date of last rebalance
    days_since_rebalance : int
        Trading days since last rebalance
    recent_sharpe : float
        Rolling 252-day Sharpe ratio
    recent_vol : float
        Rolling 63-day annualized volatility
    current_drawdown : float
        Current drawdown from peak
    portfolio_var : float
        95% Value at Risk
    portfolio_cvar : float
        95% Conditional Value at Risk
    total_return : float
        Total return since inception
    """
    date: pd.Timestamp
    current_weights: Series
    current_shares: Series
    cash: float
    equity: float
    price_history: DataFrame
    return_history: DataFrame
    last_rebalance_date: Optional[pd.Timestamp] = None
    days_since_rebalance: int = 0
    recent_sharpe: float = 0.0
    recent_vol: float = 0.0
    current_drawdown: float = 0.0
    portfolio_var: float = 0.0
    portfolio_cvar: float = 0.0
    total_return: float = 0.0


@dataclass
class PortfolioResult:
    """
    Complete results from a portfolio backtest.
    
    Contains all data needed for analysis, visualization, and dashboard display.
    
    Attributes
    ----------
    equity_curve : pd.Series
        Portfolio value over time
    weights_history : pd.DataFrame
        Asset weights over time (including CASH)
    trades_history : pd.DataFrame
        Daily weight changes (turnover proxy)
    returns_series : pd.Series
        Daily portfolio returns
    summary_metrics : Dict[str, float]
        Key performance metrics (Sharpe, drawdown, etc.)
    rolling_metrics : pd.DataFrame
        Time series of rolling metrics
    drawdown_series : pd.Series
        Drawdown from peak over time
    position_pnl : pd.DataFrame
        Profit/loss per asset per day
    turnover_history : pd.Series
        Daily turnover
    transaction_costs : pd.Series
        Daily transaction costs
    slippage_costs : pd.Series
        Daily slippage costs
    cash_history : pd.Series
        Cash balance over time
    benchmark_comparison : Optional[pd.DataFrame]
        Comparison with benchmark(s)
    strategy_name : str
        Name of strategy used
    """
    equity_curve: Series
    weights_history: DataFrame
    trades_history: DataFrame
    returns_series: Series
    summary_metrics: Dict[str, float]
    rolling_metrics: DataFrame
    drawdown_series: Series
    position_pnl: DataFrame
    turnover_history: Series
    transaction_costs: Series
    slippage_costs: Series
    cash_history: Series
    benchmark_comparison: Optional[DataFrame] = None
    strategy_name: str = "Unknown Strategy"


class PortfolioEngine:
    """
    Strategy-Agnostic Portfolio Management Engine.
    
    This class manages the complete lifecycle of a portfolio backtest:
    1. Receives target weights from strategy wrapper at each rebalance
    2. Executes trades with realistic costs and slippage
    3. Tracks positions, cash, and portfolio value
    4. Calculates comprehensive performance metrics in real-time
    5. Exports data for visualization and analysis
    
    The engine is completely strategy-agnostic - it only cares about
    receiving weights and executing them efficiently.
    
    Parameters
    ----------
    prices : pd.DataFrame
        Price data, index = dates, columns = asset tickers
    initial_capital : float, default=1_000_000
        Starting portfolio value
    transaction_cost_bps : float, default=5.0
        Round-trip transaction cost in basis points
    slippage_bps : float, default=1.0
        One-way slippage in basis points
    benchmark_tickers : List[str], optional
        Benchmark tickers to download and compare against
    cash_symbol : str, default='CASH'
        Symbol used for cash in weights
    
    Examples
    --------
    >>> from src.portfolio_engine import PortfolioEngine
    >>> from src.strategies import MomentumStrategy
    >>> 
    >>> # Create engine
    >>> portfolio = PortfolioEngine(prices, initial_capital=1_000_000)
    >>> 
    >>> # Run backtest with strategy
    >>> result = portfolio.run_backtest(
    ...     strategy_wrapper=momentum_strategy,
    ...     start_date='2020-01-01',
    ...     end_date='2023-12-31',
    ...     rebalance_freq='M'
    ... )
    >>> 
    >>> # Access results
    >>> print(result.summary_metrics)
    >>> result.equity_curve.plot()
    >>> 
    >>> # Export for dashboard
    >>> dashboard_data = portfolio.get_dashboard_data()
    """
    
    def __init__(
        self,
        prices: DataFrame,
        initial_capital: float = 1_000_000.0,
        transaction_cost_bps: float = 10.0,  # 0.10% commission (updated for realistic costs)
        slippage_bps: float = 5.0,            # 0.05% slippage (updated for realistic costs)
        benchmark_tickers: Optional[List[str]] = None,
        cash_symbol: str = 'CASH'
    ):
        """Initialize portfolio engine with price data and parameters."""
        # Core data
        self._prices = prices.sort_index().astype(float)
        if self._prices.isnull().any().any():
            self._prices = self._prices.ffill().dropna(how='all')
        
        self._returns = self._prices.pct_change().dropna()
        self.assets = list(self._prices.columns)
        self.n_assets = len(self.assets)
        
        # Parameters
        self.initial_capital = float(initial_capital)
        self.transaction_cost_bps = float(transaction_cost_bps)
        self.slippage_bps = float(slippage_bps)
        self.cash_symbol = cash_symbol
        
        # State tracking (initialized in run_backtest)
        self._equity_curve = Series(dtype=float)
        self._weights_history = DataFrame()
        self._trades_history = DataFrame()
        self._returns_history = Series(dtype=float)
        self._cash_history = Series(dtype=float)
        self._shares_history = DataFrame()
        
        # Performance metrics
        self._drawdown_series = Series(dtype=float)
        self._turnover_history = Series(dtype=float)
        self._transaction_costs_series = Series(dtype=float)
        self._slippage_costs_series = Series(dtype=float)
        self._position_pnl = DataFrame()
        
        # Rolling metrics
        self._rolling_sharpe = Series(dtype=float)
        self._rolling_sortino = Series(dtype=float)
        self._rolling_vol = Series(dtype=float)
        self._var_series = Series(dtype=float)
        self._cvar_series = Series(dtype=float)
        
        # Benchmark data
        self._benchmark_data = None
        if benchmark_tickers:
            self._load_benchmarks(benchmark_tickers)
        
        # Current state
        self._current_equity = initial_capital
        self._current_cash = initial_capital
        self._current_shares = Series(0.0, index=self.assets)
        self._current_weights = Series(0.0, index=self.assets + [cash_symbol])
        self._current_weights[cash_symbol] = 1.0
        self._last_rebalance_date = None
        
        # Strategy info
        self._strategy_name = "Unknown"
    
    def run_backtest(
        self,
        strategy_wrapper: 'BaseStrategyWrapper',
        start_date: str,
        end_date: Optional[str] = None,
        rebalance_freq: str = 'M',
        initial_capital: Optional[float] = None,
        soft_rebalance: bool = True,
        drift_threshold: float = 0.05
    ) -> PortfolioResult:
        """
        Run complete backtest with strategy wrapper.
        
        Parameters
        ----------
        strategy_wrapper : BaseStrategyWrapper
            Strategy that generates target weights
        start_date : str
            Start date for backtest (YYYY-MM-DD)
        end_date : str, optional
            End date for backtest (defaults to last date in prices)
        rebalance_freq : str, default='M'
            Rebalancing frequency:
            - 'D': Daily
            - 'W': Weekly
            - 'M': Monthly (end of month)
            - 'Q': Quarterly
        initial_capital : float, optional
            Override initial capital for this backtest
        soft_rebalance : bool, default=True
            If True, only rebalance when weight drift exceeds threshold
        drift_threshold : float, default=0.05
            Minimum weight drift (5%) to trigger rebalancing
        
        Returns
        -------
        PortfolioResult
            Complete backtest results with all metrics and data
        """
        # Reset state
        if initial_capital is not None:
            self.initial_capital = float(initial_capital)
        self._reset_state()
        
        # Get strategy info
        strategy_info = strategy_wrapper.get_strategy_info()
        self._strategy_name = strategy_info.get('name', 'Unknown Strategy')
        
        # Parse dates
        start_date = pd.Timestamp(start_date)
        if end_date is None:
            end_date = self._prices.index[-1]
        else:
            end_date = pd.Timestamp(end_date)
        
        # Get backtest dates
        backtest_dates = self._prices.loc[start_date:end_date].index
        if len(backtest_dates) == 0:
            raise ValueError(f"No data between {start_date} and {end_date}")
        
        # Get rebalance dates
        rebalance_dates = self._get_rebalance_dates(start_date, end_date, rebalance_freq)
        
        print(f"Running backtest: {start_date.date()} to {end_date.date()}")
        print(f"Rebalancing: {rebalance_freq} ({len(rebalance_dates)} rebalances)")
        print(f"Strategy: {self._strategy_name}")
        
        # Initialize on first date
        self._last_rebalance_date = backtest_dates[0]
        
        # Run backtest
        for i, date in enumerate(backtest_dates):
            # Check if rebalance needed
            if date in rebalance_dates:
                # Build portfolio state
                state = self._build_portfolio_state(date)
                
                # Get new weights from strategy
                try:
                    new_weights = strategy_wrapper.get_weights(date, state)
                    
                    # Validate weights
                    if not isinstance(new_weights, Series):
                        new_weights = Series(new_weights, index=self.assets)
                    
                    new_weights = new_weights.reindex(self.assets).fillna(0.0)
                    
                    # Ensure weights are valid
                    if new_weights.sum() > 1.01:  # Allow small tolerance
                        logger.warning(f"Weights sum to {new_weights.sum():.3f} on {date.date()}, normalizing")
                        new_weights = new_weights / new_weights.sum()
                    
                    # Execute rebalance (soft or hard based on parameter)
                    if soft_rebalance:
                        self._execute_soft_rebalance(date, new_weights, drift_threshold)
                    else:
                        self._execute_rebalance(date, new_weights)
                    self._last_rebalance_date = date
                    
                except (ValueError, KeyError, IndexError) as e:
                    logger.error(f"Strategy error on {date.date()}: {e}", exc_info=True)
                    print(f"Warning: Strategy error on {date.date()}: {e}")
                    # Keep previous weights
                    new_weights = self._current_weights.drop(self.cash_symbol, errors='ignore')
                except Exception as e:
                    logger.error(f"Unexpected error on {date.date()}: {e}", exc_info=True)
                    print(f"Error getting weights on {date.date()}: {e}")
                    # Keep previous weights
                    new_weights = self._current_weights.drop(self.cash_symbol, errors='ignore')
            else:
                # No rebalance, just track portfolio value
                new_weights = None
            
            # Update portfolio value and metrics
            self._update_daily(date, new_weights)
            
            # Progress update
            if (i + 1) % 252 == 0:
                print(f"Progress: {i + 1}/{len(backtest_dates)} days ({(i+1)/len(backtest_dates)*100:.1f}%)")
        
        print("Backtest complete!")
        
        # Build and return result
        return self._build_result()
    
    def _reset_state(self):
        """Reset all state tracking for new backtest."""
        self._current_equity = self.initial_capital
        self._current_cash = self.initial_capital
        self._current_shares = Series(0.0, index=self.assets)
        self._current_weights = Series(0.0, index=self.assets + [self.cash_symbol])
        self._current_weights[self.cash_symbol] = 1.0
        self._last_rebalance_date = None
        
        self._equity_curve = Series(dtype=float)
        self._weights_history = DataFrame()
        self._trades_history = DataFrame()
        self._returns_history = Series(dtype=float)
        self._cash_history = Series(dtype=float)
        self._shares_history = DataFrame()
        self._drawdown_series = Series(dtype=float)
        self._turnover_history = Series(dtype=float)
        self._transaction_costs_series = Series(dtype=float)
        self._slippage_costs_series = Series(dtype=float)
        self._position_pnl = DataFrame()
        self._rolling_sharpe = Series(dtype=float)
        self._rolling_sortino = Series(dtype=float)
        self._rolling_vol = Series(dtype=float)
        self._var_series = Series(dtype=float)
        self._cvar_series = Series(dtype=float)
    
    def _get_rebalance_dates(
        self,
        start_date: pd.Timestamp,
        end_date: pd.Timestamp,
        freq: str
    ) -> List[pd.Timestamp]:
        """Generate rebalancing dates based on frequency."""
        dates = self._prices.loc[start_date:end_date].index
        
        if freq == 'D':
            return dates.tolist()
        elif freq == 'W':
            # Last business day of each week
            is_week_end = dates.to_series().groupby(dates.to_period('W')).transform('last') == dates
            return dates[is_week_end].tolist()
        elif freq == 'M':
            # Last business day of each month
            is_month_end = dates.to_series().groupby(dates.to_period('M')).transform('last') == dates
            return dates[is_month_end].tolist()
        elif freq == 'Q':
            # Last business day of each quarter
            is_quarter_end = dates.to_series().groupby(dates.to_period('Q')).transform('last') == dates
            return dates[is_quarter_end].tolist()
        else:
            raise ValueError(f"Unknown frequency: {freq}")
    
    def _build_portfolio_state(self, date: pd.Timestamp) -> PortfolioState:
        """Build PortfolioState object for strategy wrapper."""
        # Get historical data up to current date
        price_history = self._prices.loc[:date]
        return_history = self._returns.loc[:date]
        
        # Calculate recent metrics
        recent_sharpe = self._calculate_rolling_sharpe(252) if len(self._returns_history) > 252 else 0.0
        recent_vol = self._calculate_rolling_vol(63) if len(self._returns_history) > 63 else 0.0
        current_dd = self._calculate_current_drawdown()
        
        # Calculate VaR/CVaR
        port_var, port_cvar = self._calculate_var_cvar()
        
        # Days since rebalance
        days_since = 0
        if self._last_rebalance_date is not None:
            days_since = len(self._prices.loc[self._last_rebalance_date:date]) - 1
        
        # Total return
        total_return = (self._current_equity / self.initial_capital) - 1.0
        
        return PortfolioState(
            date=date,
            current_weights=self._current_weights.copy(),
            current_shares=self._current_shares.copy(),
            cash=self._current_cash,
            equity=self._current_equity,
            price_history=price_history,
            return_history=return_history,
            last_rebalance_date=self._last_rebalance_date,
            days_since_rebalance=days_since,
            recent_sharpe=recent_sharpe,
            recent_vol=recent_vol,
            current_drawdown=current_dd,
            portfolio_var=port_var,
            portfolio_cvar=port_cvar,
            total_return=total_return
        )
    
    def _execute_rebalance(self, date: pd.Timestamp, target_weights: Series):
        """
        Execute rebalancing trades with costs and slippage.
        
        Parameters
        ----------
        date : pd.Timestamp
            Rebalance date
        target_weights : pd.Series
            Target weights for risky assets (excluding cash)
        """
        # Get current prices
        current_prices = self._prices.loc[date]
        
        # Calculate target positions in dollars
        target_weights = target_weights.clip(lower=0)  # No shorts
        target_weights_sum = target_weights.sum()
        
        if target_weights_sum > 1.0:
            target_weights = target_weights / target_weights_sum
        
        # Cash weight
        cash_weight = 1.0 - target_weights.sum()
        
        # Target dollar amounts
        target_dollars = target_weights * self._current_equity
        target_shares = target_dollars / current_prices
        
        # Calculate trades
        trades_shares = target_shares - self._current_shares
        trades_dollars = trades_shares * current_prices
        
        # Calculate turnover (sum of absolute trades as fraction of equity)
        # This already accounts for both buys and sells
        turnover = trades_dollars.abs().sum() / self._current_equity
        
        # Calculate costs - turnover already includes both sides
        # transaction_cost_bps is the cost per trade (e.g., 10 bps = 0.1%)
        # We apply it once to the total turnover
        transaction_cost_rate = self.transaction_cost_bps / 10000.0
        slippage_rate = self.slippage_bps / 10000.0
        total_cost_rate = transaction_cost_rate + slippage_rate
        
        # Costs are applied to the dollar volume traded
        transaction_costs = turnover * self._current_equity * transaction_cost_rate
        slippage_costs = turnover * self._current_equity * slippage_rate
        total_costs = transaction_costs + slippage_costs
        
        # Execute trades - deduct costs from the portfolio
        self._current_shares = target_shares
        self._current_cash = cash_weight * self._current_equity - total_costs
        
        # Update equity after costs
        self._current_equity = self._current_equity - total_costs
        
        # Update weights
        position_values = self._current_shares * current_prices
        total_value = position_values.sum() + self._current_cash
        
        asset_weights = position_values / total_value
        self._current_weights = pd.concat([
            asset_weights,
            Series([self._current_cash / total_value], index=[self.cash_symbol])
        ])
        
        # Record trades and costs
        self._turnover_history.loc[date] = turnover
        self._transaction_costs_series.loc[date] = transaction_costs
        self._slippage_costs_series.loc[date] = slippage_costs
    
    
    def _execute_soft_rebalance(self, date: pd.Timestamp, target_weights: Series, drift_threshold: float = 0.05):
        """
        Execute soft rebalancing - only trade if weight drift exceeds threshold.
        
        This implements the "soft rebalancing" logic where positions are only adjusted
        if they have drifted more than drift_threshold (default 5%) from target weights.
        
        Parameters
        ----------
        date : pd.Timestamp
            Rebalance date
        target_weights : pd.Series
            Target weights for risky assets (excluding cash)
        drift_threshold : float, default=0.05
            Minimum weight drift to trigger trade (5% = 0.05)
        """
        # Get current prices
        current_prices = self._prices.loc[date]
        
        # Calculate current actual weights after market movements (natural drift)
        position_values = self._current_shares * current_prices
        total_value = position_values.sum() + self._current_cash
        
        # Prevent division by zero
        if total_value <= 0:
            return
        
        current_asset_weights = position_values / total_value
        
        # Normalize target weights
        target_weights = target_weights.clip(lower=0)
        target_weights_sum = target_weights.sum()
        
        if target_weights_sum > 1.0:
            target_weights = target_weights / target_weights_sum
        
        # Calculate weight drift for each asset
        weight_drift = (target_weights - current_asset_weights).abs()
        
        # Identify assets that need rebalancing
        needs_rebalancing = weight_drift >= drift_threshold
        
        if not needs_rebalancing.any():
            # No trades needed - all weights within tolerance
            self._turnover_history.loc[date] = 0.0
            self._transaction_costs_series.loc[date] = 0.0
            self._slippage_costs_series.loc[date] = 0.0
            return
        
        # Execute rebalance for assets exceeding threshold
        # Target dollar amounts
        target_dollars = target_weights * self._current_equity
        target_shares = target_dollars / current_prices
        
        # Calculate trades
        trades_shares = target_shares - self._current_shares
        trades_dollars = trades_shares * current_prices
        
        # Calculate turnover (sum of absolute trades as fraction of equity)
        turnover = trades_dollars.abs().sum() / self._current_equity
        
        # Calculate costs
        transaction_cost_rate = self.transaction_cost_bps / 10000.0
        slippage_rate = self.slippage_bps / 10000.0
        
        transaction_costs = turnover * self._current_equity * transaction_cost_rate
        slippage_costs = turnover * self._current_equity * slippage_rate
        total_costs = transaction_costs + slippage_costs
        
        # Execute trades - deduct costs from the portfolio
        self._current_shares = target_shares
        
        # Cash weight after rebalancing
        cash_weight = 1.0 - target_weights.sum()
        self._current_cash = cash_weight * self._current_equity - total_costs
        
        # Update equity after costs
        self._current_equity = self._current_equity - total_costs
        
        # Update weights
        position_values = self._current_shares * current_prices
        total_value = position_values.sum() + self._current_cash
        
        asset_weights = position_values / total_value
        self._current_weights = pd.concat([
            asset_weights,
            Series([self._current_cash / total_value], index=[self.cash_symbol])
        ])
        
        # Record trades and costs
        self._turnover_history.loc[date] = turnover
        self._transaction_costs_series.loc[date] = transaction_costs
        self._slippage_costs_series.loc[date] = slippage_costs
    def _execute_int_rebalance(self, date: pd.Timestamp, target_weights: Series):
        """
        Execute rebalancing trades with INTEGER share constraints.
        
        This method enforces realistic trading constraints where only whole shares
        can be purchased. Uses a greedy algorithm to allocate remaining budget
        after floor allocation, prioritizing assets with largest fractional parts.
        Cash automatically absorbs the residual from integer rounding.
        
        Parameters
        ----------
        date : pd.Timestamp
            Rebalance date
        target_weights : pd.Series
            Target weights for risky assets (excluding cash)
        
        Notes
        -----
        Algorithm:
        1. Calculate target shares from weights (fractional)
        2. Apply floor() to get conservative integer allocation
        3. Calculate remaining budget
        4. Greedily add shares where fractional part was highest
        5. Cash absorbs leftover capital from integer constraints
        
        This approach works with ANY strategy, whether or not the strategy
        is aware of integer constraints.
        """
        # Get current prices
        current_prices = self._prices.loc[date]
        
        # Calculate target positions in dollars
        target_weights = target_weights.clip(lower=0)  # No shorts
        target_weights_sum = target_weights.sum()
        
        if target_weights_sum > 1.0:
            target_weights = target_weights / target_weights_sum
        
        # Target dollar amounts
        target_dollars = target_weights * self._current_equity
        target_shares_float = target_dollars / current_prices
        
        # Apply integer constraint: Floor + Greedy allocation
        target_shares = np.floor(target_shares_float)
        
        # Calculate remaining budget after floor allocation
        used_capital = (target_shares * current_prices).sum()
        remaining_budget = self._current_equity - used_capital
        
        # Greedily add shares where we're furthest below target
        # Priority = fractional part (how close we were to rounding up)
        fractional_parts = target_shares_float - target_shares
        
        # Sort by fractional part (descending) - assets closest to rounding up get priority
        priority_order = fractional_parts.sort_values(ascending=False).index
        
        for asset in priority_order:
            price = current_prices[asset]
            # If we can afford one more share and we had significant fractional part
            if remaining_budget >= price and fractional_parts[asset] > 0.01:
                target_shares[asset] += 1
                remaining_budget -= price
        
        # Recalculate actual used capital with integer shares
        used_capital = (target_shares * current_prices).sum()
        
        # Calculate trades
        trades_shares = target_shares - self._current_shares
        trades_dollars = trades_shares * current_prices
        
        # Calculate turnover (sum of absolute trades as fraction of equity)
        turnover = trades_dollars.abs().sum() / self._current_equity
        
        # Calculate costs
        transaction_cost_rate = self.transaction_cost_bps / 10000.0
        slippage_rate = self.slippage_bps / 10000.0
        
        transaction_costs = turnover * self._current_equity * transaction_cost_rate
        slippage_costs = turnover * self._current_equity * slippage_rate
        total_costs = transaction_costs + slippage_costs
        
        # Execute trades - deduct costs from the portfolio
        self._current_shares = target_shares
        
        # Cash = unused capital from integer constraints - transaction costs
        self._current_cash = (self._current_equity - used_capital) - total_costs
        
        # Update equity after costs
        self._current_equity = self._current_equity - total_costs
        
        # Update weights (recalculate actual weights after integer constraints)
        position_values = self._current_shares * current_prices
        total_value = position_values.sum() + self._current_cash
        
        asset_weights = position_values / total_value
        self._current_weights = pd.concat([
            asset_weights,
            Series([self._current_cash / total_value], index=[self.cash_symbol])
        ])
        
        # Record trades and costs
        self._turnover_history.loc[date] = turnover
        self._transaction_costs_series.loc[date] = transaction_costs
        self._slippage_costs_series.loc[date] = slippage_costs
    
    def _update_daily(self, date: pd.Timestamp, rebalance_weights: Optional[Series]):
        """Update portfolio value and metrics for current day."""
        # Get current prices
        current_prices = self._prices.loc[date]
        
        # Calculate position values
        position_values = self._current_shares * current_prices
        total_value = position_values.sum() + self._current_cash
        
        # Update equity
        self._current_equity = total_value
        
        # Calculate return
        if len(self._equity_curve) > 0:
            prev_equity = self._equity_curve.iloc[-1]
            daily_return = (total_value / prev_equity) - 1.0
        else:
            daily_return = 0.0
        
        # Record state
        self._equity_curve.loc[date] = total_value
        self._returns_history.loc[date] = daily_return
        self._cash_history.loc[date] = self._current_cash
        
        # Record weights
        asset_weights = position_values / total_value if total_value > 0 else Series(0.0, index=self.assets)
        weights_row = pd.concat([
            asset_weights,
            Series([self._current_cash / total_value], index=[self.cash_symbol])
        ])
        self._weights_history = pd.concat([
            self._weights_history,
            DataFrame([weights_row], index=[date])
        ])
        
        # Record shares
        shares_row = self._current_shares.copy()
        self._shares_history = pd.concat([
            self._shares_history,
            DataFrame([shares_row], index=[date])
        ])
        
        # Calculate drawdown
        if len(self._equity_curve) > 0:
            peak = self._equity_curve.cummax().loc[date]
            drawdown = (total_value / peak) - 1.0
            self._drawdown_series.loc[date] = drawdown
        
        # Calculate position P&L
        if len(self._shares_history) > 1:
            prev_prices = self._prices.loc[self._shares_history.index[-2]]
            prev_values = self._current_shares * prev_prices
            current_values = position_values
            pnl = current_values - prev_values
            self._position_pnl = pd.concat([
                self._position_pnl,
                DataFrame([pnl], index=[date])
            ])
        
        # Record trades if rebalance occurred
        if rebalance_weights is not None:
            if len(self._weights_history) > 1:
                prev_weights = self._weights_history.iloc[-2].drop(self.cash_symbol, errors='ignore')
                weight_changes = rebalance_weights - prev_weights.reindex(self.assets).fillna(0)
            else:
                weight_changes = rebalance_weights
            
            self._trades_history = pd.concat([
                self._trades_history,
                DataFrame([weight_changes], index=[date])
            ])
        
        # Update rolling metrics (every day)
        if len(self._returns_history) >= 252:
            self._rolling_sharpe.loc[date] = self._calculate_rolling_sharpe(252)
        if len(self._returns_history) >= 63:
            self._rolling_vol.loc[date] = self._calculate_rolling_vol(63)
            self._rolling_sortino.loc[date] = self._calculate_rolling_sortino(252)
        if len(self._returns_history) >= 21:
            var, cvar = self._calculate_var_cvar()
            self._var_series.loc[date] = var
            self._cvar_series.loc[date] = cvar
    
    def _calculate_rolling_sharpe(self, window: int) -> float:
        """Calculate rolling Sharpe ratio."""
        if len(self._returns_history) < window:
            return 0.0
        recent_returns = self._returns_history.iloc[-window:]
        mean_ret = recent_returns.mean() * 252
        vol = recent_returns.std() * np.sqrt(252)
        return mean_ret / vol if vol > 0 else 0.0
    
    def _calculate_rolling_sortino(self, window: int) -> float:
        """Calculate rolling Sortino ratio."""
        if len(self._returns_history) < window:
            return 0.0
        recent_returns = self._returns_history.iloc[-window:]
        mean_ret = recent_returns.mean() * 252
        downside = recent_returns[recent_returns < 0]
        downside_vol = downside.std() * np.sqrt(252) if len(downside) > 0 else 1e-10
        return mean_ret / downside_vol
    
    def _calculate_rolling_vol(self, window: int) -> float:
        """Calculate rolling volatility."""
        if len(self._returns_history) < window:
            return 0.0
        recent_returns = self._returns_history.iloc[-window:]
        return recent_returns.std() * np.sqrt(252)
    
    def _calculate_current_drawdown(self) -> float:
        """Calculate current drawdown from peak."""
        if len(self._equity_curve) == 0:
            return 0.0
        peak = self._equity_curve.cummax().iloc[-1]
        current = self._equity_curve.iloc[-1]
        return (current / peak) - 1.0
    
    def _calculate_var_cvar(self, alpha: float = 0.95) -> Tuple[float, float]:
        """Calculate Value at Risk and Conditional VaR."""
        if len(self._returns_history) < 21:
            return 0.0, 0.0
        
        recent_returns = self._returns_history.iloc[-252:] if len(self._returns_history) >= 252 else self._returns_history
        var = np.percentile(recent_returns, (1 - alpha) * 100)
        cvar = recent_returns[recent_returns <= var].mean() if (recent_returns <= var).any() else var
        
        return float(var), float(cvar)
    
    def _build_result(self) -> PortfolioResult:
        """Build PortfolioResult object with all data."""
        # Calculate summary metrics
        summary_metrics = self._calculate_summary_metrics()
        
        # Build rolling metrics DataFrame
        rolling_metrics = DataFrame({
            'sharpe': self._rolling_sharpe,
            'sortino': self._rolling_sortino,
            'volatility': self._rolling_vol,
            'var_95': self._var_series,
            'cvar_95': self._cvar_series
        })
        
        # Benchmark comparison
        benchmark_comparison = None
        if self._benchmark_data is not None:
            benchmark_comparison = self._compare_to_benchmarks()
        
        return PortfolioResult(
            equity_curve=self._equity_curve,
            weights_history=self._weights_history,
            trades_history=self._trades_history,
            returns_series=self._returns_history,
            summary_metrics=summary_metrics,
            rolling_metrics=rolling_metrics,
            drawdown_series=self._drawdown_series,
            position_pnl=self._position_pnl,
            turnover_history=self._turnover_history,
            transaction_costs=self._transaction_costs_series,
            slippage_costs=self._slippage_costs_series,
            cash_history=self._cash_history,
            benchmark_comparison=benchmark_comparison,
            strategy_name=self._strategy_name
        )
    
    def _calculate_summary_metrics(self) -> Dict[str, float]:
        """Calculate comprehensive summary metrics."""
        if len(self._returns_history) == 0:
            return {}
        
        returns = self._returns_history
        equity = self._equity_curve
        
        # Basic returns
        total_return = (equity.iloc[-1] / equity.iloc[0]) - 1.0
        n_years = len(returns) / 252.0
        annual_return = (1 + total_return) ** (1 / n_years) - 1.0 if n_years > 0 else 0.0
        
        # Volatility
        annual_vol = returns.std() * np.sqrt(252)
        
        # Sharpe ratio
        sharpe = annual_return / annual_vol if annual_vol > 0 else 0.0
        
        # Sortino ratio
        downside_returns = returns[returns < 0]
        downside_vol = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 1e-10
        sortino = annual_return / downside_vol
        
        # Drawdown metrics
        peak = equity.cummax()
        drawdown = (equity / peak) - 1.0
        max_drawdown = drawdown.min()
        
        # Max drawdown duration
        is_dd = drawdown < 0
        dd_groups = (is_dd != is_dd.shift()).cumsum()
        dd_durations = drawdown[is_dd].groupby(dd_groups[is_dd]).count()
        max_dd_duration = int(dd_durations.max()) if len(dd_durations) > 0 else 0
        
        # Calmar ratio
        calmar = annual_return / abs(max_drawdown) if max_drawdown < 0 else 0.0
        
        # Win rate
        winning_days = (returns > 0).sum()
        win_rate = winning_days / len(returns) if len(returns) > 0 else 0.0
        
        # Profit factor
        gains = returns[returns > 0].sum()
        losses = abs(returns[returns < 0].sum())
        profit_factor = gains / losses if losses > 0 else 0.0
        
        # VaR and CVaR
        var_95 = np.percentile(returns, 5)
        cvar_95 = returns[returns <= var_95].mean() if (returns <= var_95).any() else var_95
        
        # Trading metrics
        total_trades = len(self._trades_history)
        avg_turnover = self._turnover_history.mean() if len(self._turnover_history) > 0 else 0.0
        total_costs = self._transaction_costs_series.sum() + self._slippage_costs_series.sum()
        
        return {
            'total_return': float(total_return),
            'annual_return': float(annual_return),
            'annual_volatility': float(annual_vol),
            'sharpe_ratio': float(sharpe),
            'sortino_ratio': float(sortino),
            'max_drawdown': float(max_drawdown),
            'max_drawdown_duration_days': max_dd_duration,
            'calmar_ratio': float(calmar),
            'win_rate': float(win_rate),
            'profit_factor': float(profit_factor),
            'var_95': float(var_95),
            'cvar_95': float(cvar_95),
            'total_trades': total_trades,
            'avg_turnover': float(avg_turnover),
            'total_transaction_costs': float(self._transaction_costs_series.sum()),
            'total_slippage': float(self._slippage_costs_series.sum()),
            'total_costs': float(total_costs),
            'final_equity': float(equity.iloc[-1]),
            'n_trading_days': len(returns)
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Export all data for dashboard visualization.
        
        Returns
        -------
        dict
            Dictionary with all portfolio data organized for dashboard
        """
        return {
            'equity_curve': self._equity_curve,
            'weights_history': self._weights_history,
            'summary_metrics': self._calculate_summary_metrics(),
            'rolling_metrics': DataFrame({
                'sharpe': self._rolling_sharpe,
                'sortino': self._rolling_sortino,
                'volatility': self._rolling_vol,
                'var_95': self._var_series,
                'cvar_95': self._cvar_series
            }),
            'drawdown_series': self._drawdown_series,
            'returns_distribution': self._returns_history,
            'turnover': self._turnover_history,
            'costs': {
                'transaction_costs': self._transaction_costs_series,
                'slippage': self._slippage_costs_series,
                'total': self._transaction_costs_series + self._slippage_costs_series
            },
            'position_pnl': self._position_pnl,
            'benchmark_comparison': self._benchmark_data,
            'risk_metrics': {
                'var_series': self._var_series,
                'cvar_series': self._cvar_series,
                'volatility': self._rolling_vol
            },
            'trades': self._trades_history,
            'cash': self._cash_history,
            'strategy_name': self._strategy_name
        }
    
    def _load_benchmarks(self, tickers: List[str]):
        """Load benchmark data using yfinance."""
        try:
            import yfinance as yf
            print(f"Downloading benchmark data: {tickers}")
            
            start_date = self._prices.index[0]
            bench_data = yf.download(tickers, start=start_date, progress=False)['Close']
            
            if isinstance(bench_data, Series):
                bench_data = DataFrame(bench_data)
            
            self._benchmark_data = bench_data
            print("Benchmark data loaded successfully")
        except Exception as e:
            print(f"Warning: Could not load benchmark data: {e}")
            self._benchmark_data = None
    
    def _compare_to_benchmarks(self) -> DataFrame:
        """Compare portfolio performance to benchmarks."""
        if self._benchmark_data is None:
            return None
        
        # Align dates
        common_dates = self._equity_curve.index.intersection(self._benchmark_data.index)
        
        if len(common_dates) == 0:
            return None
        
        # Normalize to start at same value
        port_norm = self._equity_curve.loc[common_dates] / self._equity_curve.loc[common_dates[0]]
        bench_norm = self._benchmark_data.loc[common_dates] / self._benchmark_data.loc[common_dates].iloc[0]
        
        # Combine
        comparison = DataFrame({
            'Portfolio': port_norm
        })
        
        for col in bench_norm.columns:
            comparison[col] = bench_norm[col]
        
        return comparison