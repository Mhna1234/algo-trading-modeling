"""
Feature Engineering Module

This module computes technical indicators and statistical features for algorithmic trading.

Role:
-----
This is the CANONICAL source for technical indicator computation. All technical
indicators should be computed here to avoid code duplication.

- Used by: ML strategies, analysis tools, signal_generator (via delegation)
- Focus: Pure computation of technical indicators and statistical features
- Output: DataFrames with indicator values (not trading signals)

Components:
-----------
- Price-based returns (simple, log returns)
- Moving averages (simple, exponential)
- Volatility measures (rolling, EWMA, annualized)
- Technical indicators (RSI, MACD, Bollinger Bands)
- Statistical features (skewness, kurtosis, rolling statistics)
- Momentum features (multi-period)

Mathematical Formulations:
--------------------------
- Simple Return: r_t = (P_t - P_{t-1}) / P_{t-1}
- Log Return: r_t = ln(P_t / P_{t-1})
- Rolling Volatility: σ_t = sqrt(Σ(r_{t-i})^2 / (n-1)) for i=0 to n-1
- RSI: RSI_t = 100 - (100 / (1 + RS_t)), RS_t = AvgGain_t / AvgLoss_t
- MACD: MACD_t = EMA_12(P_t) - EMA_26(P_t)
- Bollinger Bands: Upper/Lower = MA ± (k × σ)

Note:
-----
signal_generator.py converts these indicators into trading signals.
This module only computes the raw indicator values.

Author: Portfolio Engine Team
Date: December 2025
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import warnings
import logging

logger = logging.getLogger(__name__)

class FeatureEngineer:
    """
    Comprehensive feature engineering for financial time series data.
    
    This is the CANONICAL source for technical indicator computation.
    
    Purpose:
    --------
    - Compute raw technical indicators (RSI values, MACD lines, Bollinger Bands, etc.)
    - Calculate statistical features for ML models
    - Provide consistent, well-tested indicator implementations
    
    NOT for:
    --------
    - Generating trading signals (use signal_generator.py)
    - Portfolio weight optimization (use optimizer.py)
    - Backtesting (use portfolio_engine.py)
    
    Output:
    -------
    Returns DataFrames with raw indicator values, NOT trading signals.
    For example:
    - compute_rsi() returns RSI values (0-100)
    - signal_generator.mean_reversion_rsi() converts to signals (-1, 0, +1)
    
    Methods:
    --------
    All methods return DataFrames/dicts with computed features.
    Use make_features() to compute all features at once.
    """
    
    def __init__(self):
        """Initialize FeatureEngineer with default parameters."""
        self.default_params = {
            'ma_periods': [5, 20, 50],
            'vol_window': 20,
            'rsi_period': 14,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'bb_period': 20,
            'bb_std': 2.0
        }
    
    def compute_returns(self, prices: pd.DataFrame, 
                       method: str = 'simple') -> pd.DataFrame:
        """
        Compute price returns for all assets.
        
        Mathematical formulations:
        - Simple return: r_t = (P_t - P_{t-1}) / P_{t-1}
        - Log return: r_t = ln(P_t / P_{t-1})
        
        Args:
            prices: DataFrame with asset prices (columns = assets, index = dates)
            method: 'simple' or 'log' returns
            
        Returns:
            DataFrame with returns for each asset
        """
        if method == 'simple':
            returns = prices.pct_change()
        elif method == 'log':
            returns = np.log(prices / prices.shift(1))
        else:
            raise ValueError("method must be 'simple' or 'log'")
        
        # Drop first row (NaN)
        returns = returns.dropna()
        
        logger.info(f"Computed {method} returns for {len(prices.columns)} assets")
        return returns
    
    def compute_moving_averages(self, prices: pd.DataFrame, 
                               periods: List[int] = None) -> Dict[str, pd.DataFrame]:
        """
        Compute simple moving averages for multiple periods.
        
        Mathematical formulation:
        MA_t(n) = (1/n) * Σ P_{t-i} for i=0 to n-1
        
        Args:
            prices: DataFrame with asset prices
            periods: List of periods for moving averages
            
        Returns:
            Dictionary with moving averages for each period
        """
        if periods is None:
            periods = self.default_params['ma_periods']
        
        ma_dict = {}
        for period in periods:
            ma_dict[f'MA_{period}'] = prices.rolling(window=period).mean()
        
        logger.info(f"Computed moving averages for periods: {periods}")
        return ma_dict
    
    def compute_exponential_ma(self, prices: pd.DataFrame,
                              spans: List[int] = None) -> Dict[str, pd.DataFrame]:
        """
        Compute exponential moving averages.
        
        Mathematical formulation:
        EMA_t = α * P_t + (1-α) * EMA_{t-1}
        where α = 2 / (span + 1)
        
        Args:
            prices: DataFrame with asset prices
            spans: List of spans for exponential moving averages
            
        Returns:
            Dictionary with exponential moving averages
        """
        if spans is None:
            spans = [12, 26]  # Common for MACD
        
        ema_dict = {}
        for span in spans:
            ema_dict[f'EMA_{span}'] = prices.ewm(span=span).mean()
        
        logger.info(f"Computed exponential moving averages for spans: {spans}")
        return ema_dict
    
    def compute_volatility(self, returns: pd.DataFrame, 
                          window: int = None,
                          method: str = 'rolling') -> pd.DataFrame:
        """
        Compute rolling volatility (standard deviation of returns).
        
        Mathematical formulation:
        σ_t = sqrt((1/n) * Σ(r_{t-i} - μ)^2) for i=0 to n-1
        where μ is the mean return over the window
        
        Args:
            returns: DataFrame with asset returns
            window: Rolling window size
            method: 'rolling' or 'ewm' (exponentially weighted)
            
        Returns:
            DataFrame with volatility for each asset
        """
        if window is None:
            window = self.default_params['vol_window']
        
        if method == 'rolling':
            volatility = returns.rolling(window=window).std()
        elif method == 'ewm':
            volatility = returns.ewm(span=window).std()
        else:
            raise ValueError("method must be 'rolling' or 'ewm'")
        
        # Annualize volatility (multiply by sqrt(252) for daily data)
        volatility_annualized = volatility * np.sqrt(252)
        
        logger.info(f"Computed {method} volatility with window {window}")
        return volatility_annualized
    
    def compute_rsi(self, prices: pd.DataFrame, 
                   period: int = None) -> pd.DataFrame:
        """
        Compute Relative Strength Index (RSI).
        
        Mathematical formulation:
        RSI_t = 100 - (100 / (1 + RS_t))
        RS_t = AvgGain_t / AvgLoss_t
        
        Where:
        AvgGain_t = EMA of gains over period
        AvgLoss_t = EMA of losses over period
        
        Args:
            prices: DataFrame with asset prices
            period: Period for RSI calculation
            
        Returns:
            DataFrame with RSI values (0-100)
        """
        if period is None:
            period = self.default_params['rsi_period']
        
        # Calculate price changes
        delta = prices.diff()
        
        # Separate gains and losses
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        
        # Calculate average gains and losses using EMA
        avg_gains = gains.ewm(span=period).mean()
        avg_losses = losses.ewm(span=period).mean()
        
        # Calculate RS and RSI
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        logger.info(f"Computed RSI with period {period}")
        return rsi
    
    def compute_macd(self, prices: pd.DataFrame,
                    fast: int = None, slow: int = None, 
                    signal: int = None) -> Dict[str, pd.DataFrame]:
        """
        Compute MACD (Moving Average Convergence Divergence).
        
        Mathematical formulation:
        MACD_t = EMA_fast(P_t) - EMA_slow(P_t)
        Signal_t = EMA_signal(MACD_t)
        Histogram_t = MACD_t - Signal_t
        
        Args:
            prices: DataFrame with asset prices
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line EMA period
            
        Returns:
            Dictionary with MACD, Signal, and Histogram
        """
        if fast is None:
            fast = self.default_params['macd_fast']
        if slow is None:
            slow = self.default_params['macd_slow']
        if signal is None:
            signal = self.default_params['macd_signal']
        
        # Calculate EMAs
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        
        # Calculate MACD line
        macd_line = ema_fast - ema_slow
        
        # Calculate signal line
        signal_line = macd_line.ewm(span=signal).mean()
        
        # Calculate histogram
        histogram = macd_line - signal_line
        
        macd_dict = {
            'MACD': macd_line,
            'MACD_Signal': signal_line,
            'MACD_Histogram': histogram
        }
        
        logger.info(f"Computed MACD with periods: fast={fast}, slow={slow}, signal={signal}")
        return macd_dict
    
    def compute_bollinger_bands(self, prices: pd.DataFrame,
                               period: int = None, 
                               std_dev: float = None) -> Dict[str, pd.DataFrame]:
        """
        Compute Bollinger Bands.
        
        Mathematical formulation:
        Middle Band = MA_t(period)
        Upper Band = MA_t(period) + (std_dev * σ_t(period))
        Lower Band = MA_t(period) - (std_dev * σ_t(period))
        
        Args:
            prices: DataFrame with asset prices
            period: Period for moving average and standard deviation
            std_dev: Number of standard deviations for bands
            
        Returns:
            Dictionary with Upper, Middle, Lower bands and %B indicator
        """
        if period is None:
            period = self.default_params['bb_period']
        if std_dev is None:
            std_dev = self.default_params['bb_std']
        
        # Calculate middle band (SMA)
        middle_band = prices.rolling(window=period).mean()
        
        # Calculate standard deviation
        rolling_std = prices.rolling(window=period).std()
        
        # Calculate upper and lower bands
        upper_band = middle_band + (std_dev * rolling_std)
        lower_band = middle_band - (std_dev * rolling_std)
        
        # Calculate %B (position within bands)
        percent_b = (prices - lower_band) / (upper_band - lower_band)
        
        bb_dict = {
            'BB_Upper': upper_band,
            'BB_Middle': middle_band,
            'BB_Lower': lower_band,
            'BB_PercentB': percent_b
        }
        
        logger.info(f"Computed Bollinger Bands with period {period} and std {std_dev}")
        return bb_dict
    
    def compute_statistical_features(self, returns: pd.DataFrame,
                                   window: int = 20) -> Dict[str, pd.DataFrame]:
        """
        Compute statistical features of returns.
        
        Args:
            returns: DataFrame with asset returns
            window: Rolling window for statistics
            
        Returns:
            Dictionary with skewness, kurtosis, and other statistics
        """
        stats_dict = {
            'Skewness': returns.rolling(window=window).skew(),
            'Kurtosis': returns.rolling(window=window).kurt(),
            'Mean': returns.rolling(window=window).mean(),
            'Std': returns.rolling(window=window).std(),
            'Min': returns.rolling(window=window).min(),
            'Max': returns.rolling(window=window).max()
        }
        
        logger.info(f"Computed statistical features with window {window}")
        return stats_dict
    
    def compute_momentum_features(self, prices: pd.DataFrame,
                                periods: List[int] = None) -> Dict[str, pd.DataFrame]:
        """
        Compute momentum features.
        
        Mathematical formulation:
        Momentum_t(n) = P_t / P_{t-n} - 1
        
        Args:
            prices: DataFrame with asset prices
            periods: List of periods for momentum calculation
            
        Returns:
            Dictionary with momentum features
        """
        if periods is None:
            periods = [5, 10, 20, 60]
        
        momentum_dict = {}
        for period in periods:
            momentum_dict[f'Momentum_{period}'] = (prices / prices.shift(period)) - 1
        
        logger.info(f"Computed momentum features for periods: {periods}")
        return momentum_dict
    
    def make_features(self, prices: pd.DataFrame,
                     include_returns: bool = True,
                     include_ma: bool = True,
                     include_volatility: bool = True,
                     include_rsi: bool = True,
                     include_macd: bool = True,
                     include_bb: bool = True,
                     include_stats: bool = True,
                     include_momentum: bool = True) -> Dict[str, pd.DataFrame]:
        """
        Main method to compute all features for the given price data.
        
        Args:
            prices: DataFrame with asset prices
            include_*: Boolean flags to control which features to compute
            
        Returns:
            Dictionary containing all computed features
        """
        logger.info(f"Computing features for {len(prices.columns)} assets")
        
        features = {}
        
        # Compute returns first (needed for other calculations)
        if include_returns:
            features['returns'] = self.compute_returns(prices, method='simple')
            features['log_returns'] = self.compute_returns(prices, method='log')
        
        # Moving averages
        if include_ma:
            ma_features = self.compute_moving_averages(prices)
            features.update(ma_features)
            
            # Add EMA
            ema_features = self.compute_exponential_ma(prices)
            features.update(ema_features)
        
        # Volatility
        if include_volatility and include_returns:
            features['volatility'] = self.compute_volatility(features['returns'])
        
        # RSI
        if include_rsi:
            features['RSI'] = self.compute_rsi(prices)
        
        # MACD
        if include_macd:
            macd_features = self.compute_macd(prices)
            features.update(macd_features)
        
        # Bollinger Bands
        if include_bb:
            bb_features = self.compute_bollinger_bands(prices)
            features.update(bb_features)
        
        # Statistical features
        if include_stats and include_returns:
            stats_features = self.compute_statistical_features(features['returns'])
            features.update(stats_features)
        
        # Momentum features
        if include_momentum:
            momentum_features = self.compute_momentum_features(prices)
            features.update(momentum_features)
        
        # Compute covariance matrix of returns
        if include_returns:
            features['cov'] = features['returns'].cov()
            features['corr'] = features['returns'].corr()
        
        logger.info(f"Feature engineering completed. Generated {len(features)} feature sets")
        return features


def make_features(prices: pd.DataFrame, **kwargs) -> Dict[str, pd.DataFrame]:
    """
    Convenience function to compute features.
    
    Args:
        prices: DataFrame with asset prices
        **kwargs: Additional parameters for feature computation
        
    Returns:
        Dictionary containing all computed features
    """
    engineer = FeatureEngineer()
    return engineer.make_features(prices, **kwargs)


if __name__ == "__main__":
    # Example usage
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from src.data_loader import load_data
    
    # Load sample data
    tickers = ['AAPL', 'MSFT', 'SPY']
    start_date = '2022-01-01'
    end_date = '2024-01-01'
    
    try:
        _, price_data = load_data(tickers, start_date, end_date)
        
        # Compute features
        engineer = FeatureEngineer()
        features = engineer.make_features(price_data)
        
        print("Feature Engineering Results:")
        print(f"Price data shape: {price_data.shape}")
        print(f"\nGenerated features:")
        for name, data in features.items():
            if isinstance(data, pd.DataFrame):
                print(f"  {name}: {data.shape}")
            else:
                print(f"  {name}: {type(data)}")
        
        # Show sample of returns
        if 'returns' in features:
            print(f"\nSample returns:")
            print(features['returns'].head())
            
        # Show sample of RSI
        if 'RSI' in features:
            print(f"\nSample RSI:")
            print(features['RSI'].tail())
            
    except Exception as e:
        print(f"Error in example: {e}")
        print("Note: This example requires running data_loader.py first")