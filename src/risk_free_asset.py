"""
Risk-Free Asset Module

This module implements a risk-free asset (cash/money-market) that can be used
as a portfolio component in the MAB framework. The risk-free asset can be
treated either as an arm (strategy) or as a base asset for unallocated capital.

Key Features:
- Dynamic rate retrieval from FRED API
- Configurable fallback rates
- Daily return calculation
- Integration with portfolio engine

Author: Portfolio Engine Team
Date: December 2025
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta
import logging
import requests
from dataclasses import dataclass

from .strategies.base_strategy_wrapper import BaseStrategyWrapper
from .utils import TradingConfig

logger = logging.getLogger(__name__)


@dataclass
class RiskFreeRate:
    """Container for risk-free rate data."""
    
    date: pd.Timestamp
    rate: float  # Annual rate (e.g., 0.05 for 5%)
    source: str  # 'FRED', 'config', 'fallback'
    maturity: str = '1M'  # Rate maturity (1M, 3M, 6M, 1Y, etc.)


class RiskFreeAsset:
    """
    Risk-free asset implementation for portfolio allocation.
    
    This class represents cash or money-market investments that provide
    a risk-free return. It can be used as:
    1. An arm in the MAB allocation (treated like a strategy)
    2. A base asset for unallocated capital
    
    Features:
    - Dynamic rate updates from FRED API
    - Configurable fallback rates
    - Daily compounding of returns
    - Historical rate storage
    """
    
    def __init__(self,
                 initial_rate: float = 0.05,
                 rate_source: str = 'config',
                 maturity: str = '3M',
                 api_key: Optional[str] = None,
                 update_frequency: str = 'D'):
        """
        Initialize risk-free asset.
        
        Args:
            initial_rate: Initial annual risk-free rate (0.05 = 5%)
            rate_source: Source for rates ('fred', 'config', 'fallback')
            maturity: Rate maturity ('1M', '3M', '6M', '1Y', etc.)
            api_key: FRED API key (if using FRED)
            update_frequency: How often to update rates ('D', 'W', 'M')
        """
        self.initial_rate = initial_rate
        self.rate_source = rate_source.lower()
        self.maturity = maturity
        self.api_key = api_key
        self.update_frequency = update_frequency
        
        # Rate history storage
        self.rate_history: Dict[pd.Timestamp, RiskFreeRate] = {}
        
        # Current rate
        self.current_rate = initial_rate
        
        # FRED series IDs for different maturities
        self.fred_series = {
            '1M': 'DGS1MO',   # 1-Month Treasury Constant Maturity Rate
            '3M': 'DGS3MO',   # 3-Month Treasury Constant Maturity Rate
            '6M': 'DGS6MO',   # 6-Month Treasury Constant Maturity Rate
            '1Y': 'DGS1',     # 1-Year Treasury Constant Maturity Rate
            '2Y': 'DGS2',     # 2-Year Treasury Constant Maturity Rate
            '5Y': 'DGS5',     # 5-Year Treasury Constant Maturity Rate
            '10Y': 'DGS10',   # 10-Year Treasury Constant Maturity Rate
            '30Y': 'DGS30'    # 30-Year Treasury Constant Maturity Rate
        }
        
        logger.info(f"RiskFreeAsset initialized with rate_source={self.rate_source}, "
                   f"maturity={maturity}, initial_rate={initial_rate:.1%}")
    
    def get_daily_return(self, date: pd.Timestamp) -> float:
        """
        Get the daily return for the risk-free asset on a given date.
        
        Args:
            date: Date for which to calculate return
            
        Returns:
            Daily return (e.g., 0.000123 for ~0.0123% daily)
        """
        # Get the annual rate for this date
        annual_rate = self.get_rate(date)
        
        # Convert to daily return (assuming 252 trading days)
        daily_return = annual_rate / 252
        
        return daily_return
    
    def get_rate(self, date: pd.Timestamp) -> float:
        """
        Get the annual risk-free rate for a given date.
        
        Args:
            date: Date for which to get the rate
            
        Returns:
            Annual rate (e.g., 0.05 for 5%)
        """
        # Check if we have a cached rate for this date
        if date in self.rate_history:
            return self.rate_history[date].rate
        
        # Try to fetch/update rate based on source
        try:
            if self.rate_source == 'fred':
                rate = self._fetch_fred_rate(date)
            elif self.rate_source == 'config':
                rate = self.initial_rate
            else:
                rate = self._get_fallback_rate(date)
            
            # Cache the rate
            self.rate_history[date] = RiskFreeRate(
                date=date,
                rate=rate,
                source=self.rate_source,
                maturity=self.maturity
            )
            
            self.current_rate = rate
            return rate
            
        except Exception as e:
            logger.warning(f"Failed to get rate for {date.date()}: {e}")
            # Use fallback
            fallback_rate = self._get_fallback_rate(date)
            self.rate_history[date] = RiskFreeRate(
                date=date,
                rate=fallback_rate,
                source='fallback',
                maturity=self.maturity
            )
            return fallback_rate
    
    def _fetch_fred_rate(self, date: pd.Timestamp) -> float:
        """
        Fetch risk-free rate from FRED API.
        
        Args:
            date: Date for which to fetch rate
            
        Returns:
            Annual rate
        """
        if not self.api_key:
            raise ValueError("FRED API key required for FRED rate source")
        
        series_id = self.fred_series.get(self.maturity)
        if not series_id:
            raise ValueError(f"Unsupported maturity: {self.maturity}")
        
        # FRED API endpoint
        url = f"https://api.stlouisfed.org/fred/series/observations"
        params = {
            'series_id': series_id,
            'api_key': self.api_key,
            'file_type': 'json',
            'observation_start': (date - timedelta(days=30)).strftime('%Y-%m-%d'),
            'observation_end': date.strftime('%Y-%m-%d'),
            'limit': 1,
            'sort_order': 'desc'
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if not data.get('observations'):
            raise ValueError(f"No FRED data available for {date.date()}")
        
        # Get the most recent observation
        observation = data['observations'][0]
        rate_str = observation.get('value')
        
        if rate_str == '.':
            raise ValueError(f"Missing FRED data for {date.date()}")
        
        # Convert to decimal (FRED rates are in percent)
        rate = float(rate_str) / 100.0
        
        logger.debug(f"Fetched FRED rate for {date.date()}: {rate:.4%}")
        return rate
    
    def _get_fallback_rate(self, date: pd.Timestamp) -> float:
        """
        Get fallback risk-free rate based on historical averages.
        
        Args:
            date: Date for rate
            
        Returns:
            Fallback annual rate
        """
        # Historical average rates by decade (in decimal)
        fallback_rates = {
            '1950s': 0.035,  # 3.5%
            '1960s': 0.042,  # 4.2%
            '1970s': 0.065,  # 6.5%
            '1980s': 0.085,  # 8.5%
            '1990s': 0.052,  # 5.2%
            '2000s': 0.038,  # 3.8%
            '2010s': 0.018,  # 1.8%
            '2020s': 0.042   # 4.2%
        }
        
        decade = f"{(date.year // 10) * 10}s"
        rate = fallback_rates.get(decade, self.initial_rate)
        
        logger.debug(f"Using fallback rate for {decade}: {rate:.4%}")
        return rate
    
    def update_rate(self, date: pd.Timestamp, new_rate: Optional[float] = None) -> None:
        """
        Manually update the risk-free rate.
        
        Args:
            date: Date for the rate update
            new_rate: New annual rate (if None, will fetch from source)
        """
        if new_rate is not None:
            self.rate_history[date] = RiskFreeRate(
                date=date,
                rate=new_rate,
                source='manual',
                maturity=self.maturity
            )
            self.current_rate = new_rate
            logger.info(f"Manually updated rate to {new_rate:.4%} for {date.date()}")
        else:
            # Fetch from source
            rate = self.get_rate(date)
            logger.info(f"Updated rate to {rate:.4%} for {date.date()} from {self.rate_source}")
    
    def get_rate_history(self, start_date: Optional[pd.Timestamp] = None,
                        end_date: Optional[pd.Timestamp] = None) -> pd.Series:
        """
        Get historical risk-free rates.
        
        Args:
            start_date: Start date for history
            end_date: End date for history
            
        Returns:
            Series of annual rates indexed by date
        """
        if not self.rate_history:
            return pd.Series(dtype=float)
        
        rates = pd.Series({
            date: rate.rate 
            for date, rate in self.rate_history.items()
        }).sort_index()
        
        if start_date is not None:
            rates = rates[rates.index >= start_date]
        if end_date is not None:
            rates = rates[rates.index <= end_date]
            
        return rates
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata about the risk-free asset."""
        return {
            'type': 'risk_free_asset',
            'rate_source': self.rate_source,
            'maturity': self.maturity,
            'current_rate': self.current_rate,
            'initial_rate': self.initial_rate,
            'update_frequency': self.update_frequency,
            'api_key_configured': self.api_key is not None,
            'rate_history_length': len(self.rate_history)
        }


class RiskFreeStrategyWrapper(BaseStrategyWrapper):
    """
    Strategy wrapper for risk-free asset when used as an MAB arm.
    
    This allows the risk-free asset to be treated like any other strategy
    in the MAB allocation framework.
    """
    
    def __init__(self, risk_free_asset: RiskFreeAsset, name: str = "Risk-Free Asset"):
        """
        Initialize risk-free strategy wrapper.
        
        Args:
            risk_free_asset: RiskFreeAsset instance
            name: Strategy name
        """
        super().__init__(name, None, None)  # No strategy or optimizer needed
        self.risk_free_asset = risk_free_asset
    
    def get_weights(self, date: pd.Timestamp, portfolio_state) -> pd.Series:
        """
        Return weights for risk-free asset.
        
        Since this is a single asset (cash), it returns weight of 1.0
        for the cash symbol. In practice, the MAB will allocate a portion
        of capital to this "strategy", which gets invested in cash.
        """
        # This represents 100% allocation to risk-free asset
        # The actual weight will be determined by MAB allocation
        return pd.Series({portfolio_state.cash_symbol: 1.0})
    
    def evaluate_reward(self, portfolio_state) -> float:
        """
        Evaluate the reward for the risk-free asset.
        
        Returns the risk-free rate as the reward metric.
        """
        if portfolio_state is None:
            # For testing/demo purposes, use current date
            current_date = pd.Timestamp.now().normalize()
        else:
            current_date = portfolio_state.date
        return self.risk_free_asset.get_rate(current_date)
    
    def get_rebalancing_frequency(self) -> str:
        """Risk-free assets don't need frequent rebalancing."""
        return 'M'  # Monthly
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy metadata."""
        return {
            'name': self.name,
            'type': 'risk_free',
            'rate_source': self.risk_free_asset.rate_source,
            'current_rate': self.risk_free_asset.current_rate,
            'maturity': self.risk_free_asset.maturity
        }


if __name__ == "__main__":
    # Example usage
    print("Risk-Free Asset Module")
    print("======================")
    
    # Create risk-free asset with config rate
    rfa = RiskFreeAsset(initial_rate=0.04, rate_source='config')
    
    # Test daily return calculation
    test_date = pd.Timestamp('2023-01-01')
    daily_return = rfa.get_daily_return(test_date)
    print(f"Daily return on {test_date.date()}: {daily_return:.6f} ({daily_return*100:.4f}%)")
    
    # Test with fallback rates
    rfa_fallback = RiskFreeAsset(rate_source='fallback')
    rate_2020 = rfa_fallback.get_rate(pd.Timestamp('2020-06-01'))
    rate_2010 = rfa_fallback.get_rate(pd.Timestamp('2010-06-01'))
    print(f"Fallback rate 2020: {rate_2020:.1%}")
    print(f"Fallback rate 2010: {rate_2010:.1%}")
    
    print("\nRisk-free asset ready for integration!")