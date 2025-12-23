"""
Rebalancing Scheduler Module

Abstract base class for managing rebalancing schedules.
Supports global and per-strategy rebalancing logic.
"""

from abc import ABC, abstractmethod
from typing import List
import pandas as pd


class RebalancingScheduler(ABC):
    """
    Abstract base class for rebalancing schedulers.
    
    Handles both global rebalancing (e.g., monthly) and per-strategy
    rebalancing (e.g., some strategies rebalance weekly).
    """
    
    def __init__(self, global_freq: str = 'M'):
        """
        Initialize with global rebalancing frequency.
        
        Parameters
        ----------
        global_freq : str
            Global rebalancing frequency (e.g., 'D', 'W', 'M', 'Q')
        """
        self.global_freq = global_freq
    
    @abstractmethod
    def get_global_rebalance_dates(
        self, 
        start_date: pd.Timestamp, 
        end_date: pd.Timestamp
    ) -> List[pd.Timestamp]:
        """
        Get dates for global rebalancing.
        
        Parameters
        ----------
        start_date : pd.Timestamp
            Backtest start date
        end_date : pd.Timestamp
            Backtest end date
        
        Returns
        -------
        List[pd.Timestamp]
            Dates when global rebalancing should occur
        """
        pass
    
    @abstractmethod
    def should_strategy_rebalance(
        self, 
        strategy_name: str, 
        current_date: pd.Timestamp, 
        last_rebalance: pd.Timestamp
    ) -> bool:
        """
        Check if a specific strategy should rebalance.
        
        Parameters
        ----------
        strategy_name : str
            Name of the strategy
        current_date : pd.Timestamp
            Current date
        last_rebalance : pd.Timestamp
            Strategy's last rebalance date
        
        Returns
        -------
        bool
            True if strategy should rebalance
        """
        pass


class SimpleRebalancingScheduler(RebalancingScheduler):
    """
    Simple scheduler: global rebalancing at fixed intervals,
    strategies rebalance at their specified frequency.
    """
    
    def __init__(self, global_freq: str = 'M', strategy_freqs: dict = None, prices: pd.DataFrame = None):
        super().__init__(global_freq)
        self.strategy_freqs = strategy_freqs or {}
        self.prices = prices
    
    def get_global_rebalance_dates(
        self, 
        start_date: pd.Timestamp, 
        end_date: pd.Timestamp
    ) -> List[pd.Timestamp]:
        # Replicate PortfolioEngine._get_rebalance_dates logic
        if self.prices is not None:
            dates = self.prices.loc[start_date:end_date].index
        else:
            # Fallback to date_range, but may not match business days
            dates = pd.date_range(start_date, end_date, freq='D')
        
        if self.global_freq == 'D':
            return dates.tolist()
        elif self.global_freq == 'W':
            # Last business day of each week
            is_week_end = dates.to_series().groupby(dates.to_period('W')).transform('last') == dates
            return dates[is_week_end].tolist()
        elif self.global_freq == 'M':
            # Last business day of each month
            is_month_end = dates.to_series().groupby(dates.to_period('M')).transform('last') == dates
            return dates[is_month_end].tolist()
        elif self.global_freq == 'Q':
            # Last business day of each quarter
            is_quarter_end = dates.to_series().groupby(dates.to_period('Q')).transform('last') == dates
            return dates[is_quarter_end].tolist()
        else:
            raise ValueError(f"Unknown frequency: {self.global_freq}")
    
    def should_strategy_rebalance(
        self, 
        strategy_name: str, 
        current_date: pd.Timestamp, 
        last_rebalance: pd.Timestamp
    ) -> bool:
        freq = self.strategy_freqs.get(strategy_name, self.global_freq)
        # Simple check: if enough time has passed based on freq
        if freq == 'D':
            return True
        elif freq == 'W':
            return (current_date - last_rebalance).days >= 7
        elif freq == 'M':
            return current_date.month != last_rebalance.month
        elif freq == 'Q':
            return current_date.quarter != last_rebalance.quarter
        return False