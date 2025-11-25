"""
Strategy - Signal Generation and Data Management

This module provides the Strategy class that serves as a data container
and signal generator for strategy wrappers. It handles price data,
return calculations, and basic signal generation.

Author: Portfolio Engine Team
Date: November 2025
"""

import pandas as pd
import numpy as np
from typing import Optional, List
import warnings


class Strategy:
    """
    Data container and signal generator for trading strategies.
    
    This class provides:
    - Price and return data management
    - Basic signal generation (momentum, mean reversion)
    - Data access methods for strategy wrappers
    
    Parameters
    ----------
    prices : pd.DataFrame
        Historical price data (index=dates, columns=assets)
    risk_free_rate : float, default=0.02
        Annual risk-free rate for Sharpe calculations
    
    Examples
    --------
    >>> prices = pd.read_csv('prices.csv', index_col=0, parse_dates=True)
    >>> strategy = Strategy(prices)
    >>> returns = strategy.get_return_matrix()
    >>> momentum_signals = strategy.momentum(window=126)
    """
    
    def __init__(self, prices: pd.DataFrame, risk_free_rate: float = 0.02):
        """
        Initialize Strategy with price data.
        
        Parameters
        ----------
        prices : pd.DataFrame
            Historical price data (index=dates, columns=assets)
        risk_free_rate : float
            Annual risk-free rate
        """
        self.prices = prices
        self.risk_free_rate = risk_free_rate
        self.assets = list(prices.columns)
        self.dates = prices.index
        
        # Calculate returns
        self.returns = prices.pct_change().fillna(0.0)
        
    def get_return_matrix(self, start_date: Optional[pd.Timestamp] = None,
                         end_date: Optional[pd.Timestamp] = None) -> pd.DataFrame:
        """
        Get return matrix for specified date range.
        
        Parameters
        ----------
        start_date : pd.Timestamp, optional
            Start date for returns
        end_date : pd.Timestamp, optional
            End date for returns
        
        Returns
        -------
        pd.DataFrame
            Return matrix (index=dates, columns=assets)
        """
        returns = self.returns.copy()
        
        if start_date is not None:
            returns = returns[returns.index >= start_date]
        if end_date is not None:
            returns = returns[returns.index <= end_date]
            
        return returns
    
    def get_price_matrix(self, start_date: Optional[pd.Timestamp] = None,
                        end_date: Optional[pd.Timestamp] = None) -> pd.DataFrame:
        """
        Get price matrix for specified date range.
        
        Parameters
        ----------
        start_date : pd.Timestamp, optional
            Start date
        end_date : pd.Timestamp, optional
            End date
        
        Returns
        -------
        pd.DataFrame
            Price matrix (index=dates, columns=assets)
        """
        prices = self.prices.copy()
        
        if start_date is not None:
            prices = prices[prices.index >= start_date]
        if end_date is not None:
            prices = prices[prices.index <= end_date]
            
        return prices
    
    def momentum(self, window: int = 126) -> pd.DataFrame:
        """
        Calculate momentum signals (cumulative returns over window).
        
        Parameters
        ----------
        window : int, default=126
            Lookback window in trading days (252 days/year)
        
        Returns
        -------
        pd.DataFrame
            Momentum signals for each asset
        """
        # Calculate cumulative returns over window
        momentum = self.prices.pct_change(window).fillna(0.0)
        return momentum
    
    def mean_reversion(self, window: int = 20) -> pd.DataFrame:
        """
        Calculate mean reversion signals (z-scores).
        
        Parameters
        ----------
        window : int, default=20
            Lookback window for mean/std calculation
        
        Returns
        -------
        pd.DataFrame
            Z-scores for each asset (negative = oversold)
        """
        # Calculate rolling z-scores
        rolling_mean = self.prices.rolling(window).mean()
        rolling_std = self.prices.rolling(window).std()
        
        z_scores = (self.prices - rolling_mean) / rolling_std
        return z_scores.fillna(0.0)
    
    def volatility(self, window: int = 20) -> pd.DataFrame:
        """
        Calculate rolling volatility.
        
        Parameters
        ----------
        window : int, default=20
            Lookback window
        
        Returns
        -------
        pd.DataFrame
            Annualized volatility for each asset
        """
        # Calculate rolling volatility (annualized)
        vol = self.returns.rolling(window).std() * np.sqrt(252)
        return vol.fillna(0.0)
    
    def generate_initial_weights(self, method: str = 'equal',
                                 signals: Optional[pd.Series] = None,
                                 top_n: Optional[int] = None,
                                 lookback: Optional[int] = None,
                                 window: Optional[int] = None,
                                 **kwargs) -> pd.Series:
        """
        Generate initial weights before optimization.
        
        Parameters
        ----------
        method : str, default='equal'
            Weight generation method:
            - 'equal': Equal weights (1/N)
            - 'momentum': Weight by momentum signals
            - 'mean_reversion': Weight by mean reversion (buy losers)
            - 'inverse_vol': Weight by inverse volatility
            - 'inv_vol': Alias for inverse_vol
        signals : pd.Series, optional
            Signal values for each asset (used with 'momentum' method)
        top_n : int, optional
            Number of top assets to select
        lookback : int, optional
            Lookback window for signals
        window : int, optional
            Window parameter for specific methods
        
        Returns
        -------
        pd.Series
            Initial weights (before optimization)
        """
        n = len(self.assets)
        
        if method == 'equal':
            weights = pd.Series(1.0 / n, index=self.assets)
            
        elif method == 'momentum':
            # Use momentum as signals if not provided
            if signals is None:
                mom_window = lookback if lookback else 126
                signals = self.momentum(window=mom_window).iloc[-1]
            
            # Select top N assets if specified
            if top_n is not None and top_n < n:
                # Sort by signals and take top N
                top_assets = signals.nlargest(top_n).index
                weights = pd.Series(0.0, index=self.assets)
                weights[top_assets] = 1.0 / top_n
            else:
                # Weight by positive signals
                positive_signals = signals.clip(lower=0)
                if positive_signals.sum() > 0:
                    weights = positive_signals / positive_signals.sum()
                else:
                    weights = pd.Series(1.0 / n, index=self.assets)
        
        elif method == 'mean_reversion':
            # Use mean reversion signals (buy losers, sell winners)
            mr_window = window if window else 5
            signals = self.mean_reversion(window=mr_window).iloc[-1]
            
            # Invert signals (negative z-score = oversold = buy)
            inverted_signals = -signals
            
            # Select top N assets if specified
            if top_n is not None and top_n < n:
                top_assets = inverted_signals.nlargest(top_n).index
                weights = pd.Series(0.0, index=self.assets)
                weights[top_assets] = 1.0 / top_n
            else:
                # Weight by inverted signals
                positive_signals = inverted_signals.clip(lower=0)
                if positive_signals.sum() > 0:
                    weights = positive_signals / positive_signals.sum()
                else:
                    weights = pd.Series(1.0 / n, index=self.assets)
                
        elif method in ['inverse_vol', 'inv_vol']:
            # Weight by inverse volatility
            vol_window = window if window else 20
            recent_vol = self.volatility(window=vol_window).iloc[-1]
            inv_vol = 1.0 / (recent_vol + 1e-8)  # Add small epsilon
            weights = inv_vol / inv_vol.sum()
            
        else:
            # Default to equal weight
            weights = pd.Series(1.0 / n, index=self.assets)
        
        return weights
    
    def get_covariance_matrix(self, window: int = 126) -> pd.DataFrame:
        """
        Calculate covariance matrix of returns.
        
        Parameters
        ----------
        window : int, default=126
            Lookback window for covariance estimation
        
        Returns
        -------
        pd.DataFrame
            Covariance matrix (annualized)
        """
        recent_returns = self.returns.iloc[-window:]
        cov_matrix = recent_returns.cov() * 252  # Annualize
        return cov_matrix
    
    def get_expected_returns(self, window: int = 126, method: str = 'mean') -> pd.Series:
        """
        Estimate expected returns.
        
        Parameters
        ----------
        window : int, default=126
            Lookback window
        method : str, default='mean'
            Estimation method:
            - 'mean': Historical mean
            - 'momentum': Recent momentum
        
        Returns
        -------
        pd.Series
            Expected returns (annualized)
        """
        if method == 'mean':
            # Historical mean return
            expected_returns = self.returns.iloc[-window:].mean() * 252
        elif method == 'momentum':
            # Use recent momentum as proxy
            expected_returns = self.momentum(window=window).iloc[-1]
        else:
            expected_returns = self.returns.iloc[-window:].mean() * 252
            
        return expected_returns
    
    def __repr__(self) -> str:
        """String representation."""
        return (f"Strategy(assets={len(self.assets)}, "
                f"dates={len(self.dates)}, "
                f"period={self.dates[0].date()} to {self.dates[-1].date()})")
