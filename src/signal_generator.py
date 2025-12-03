"""
Signal Generation Module

This module provides comprehensive signal generation and data management for trading strategies.
It combines data container functionality with advanced signal generation in a unified class.

Components:
    StrategySignalGenerator: Unified class for data management and signal generation
        - Price and return data management
        - Basic signal generation (momentum, mean reversion, volatility)
        - Advanced technical indicators (MA crossover, MACD, RSI, Bollinger Bands)
        - Forecast-based signals (expected return thresholds)
        - Volatility-scaled signals
        - Combined signals with multiple strategies
        - Data access methods for strategy wrappers
        - Initial weight generation
        - Covariance and expected return estimation
    
    Strategy: Alias for StrategySignalGenerator (backward compatibility)

Mathematical Formulations:
    - Basic Signal: signal_t = sign(indicator_t - threshold)
    - Volatility-Scaled Signal: weight_t = signal_t / σ_t
    - Z-Score Signal: z_t = (x_t - μ_t) / σ_t
    - Momentum Signal: signal_t = sign(MA_fast - MA_slow)
    - Mean Reversion: signal_t = -sign(z_score) if |z_score| > threshold
    - MACD: MACD_t = EMA_fast(P_t) - EMA_slow(P_t)
    - RSI: RSI_t = 100 - (100 / (1 + RS_t))
    - Bollinger Bands: Upper/Lower = MA ± (num_std × σ)

Author: Portfolio Engine Team
Date: December 2025
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Callable
import warnings
import logging

logger = logging.getLogger(__name__)


class StrategySignalGenerator:
    """
    Unified data container and signal generator for trading strategies.
    
    This class provides comprehensive functionality for:
    - Price and return data management
    - Basic signal generation (momentum, mean reversion, volatility)
    - Advanced technical indicators (MA crossover, MACD, RSI, Bollinger Bands)
    - Forecast-based signals
    - Data access methods for strategy wrappers
    - Initial weight generation
    - Risk metrics calculation
    
    Parameters
    ----------
    prices : pd.DataFrame
        Historical price data (index=dates, columns=assets)
    risk_free_rate : float, default=0.02
        Annual risk-free rate for Sharpe calculations
    signal_threshold : float, default=0.0
        Minimum threshold for signal generation
    volatility_scaling : bool, default=True
        Whether to scale signals by volatility
    signal_smoothing : bool, default=True
        Whether to apply smoothing to signals
    smoothing_window : int, default=3
        Window size for signal smoothing
    
    Examples
    --------
    >>> prices = pd.read_csv('prices.csv', index_col=0, parse_dates=True)
    >>> strategy = StrategySignalGenerator(prices)
    >>> returns = strategy.get_return_matrix()
    >>> momentum_signals = strategy.momentum(window=126)
    >>> ma_crossover = strategy.momentum_ma_crossover(fast_window=5, slow_window=20)
    """
    
    def __init__(self, 
                 prices: pd.DataFrame, 
                 risk_free_rate: float = 0.02,
                 signal_threshold: float = 0.0,
                 volatility_scaling: bool = True,
                 signal_smoothing: bool = True,
                 smoothing_window: int = 3):
        """
        Initialize StrategySignalGenerator with price data and configuration.
        
        Parameters
        ----------
        prices : pd.DataFrame
            Historical price data (index=dates, columns=assets)
        risk_free_rate : float
            Annual risk-free rate
        signal_threshold : float
            Minimum threshold for signal generation
        volatility_scaling : bool
            Whether to scale signals by volatility
        signal_smoothing : bool
            Whether to apply smoothing to signals
        smoothing_window : int
            Window size for signal smoothing
        """
        self.prices = prices
        self.risk_free_rate = risk_free_rate
        self.assets = list(prices.columns)
        self.dates = prices.index
        
        # Calculate returns
        self.returns = prices.pct_change().fillna(0.0)
        
        # Signal generation parameters
        self.signal_threshold = signal_threshold
        self.volatility_scaling = volatility_scaling
        self.signal_smoothing = signal_smoothing
        self.smoothing_window = smoothing_window
        
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
    
    # ==================== Advanced Signal Generation Methods ====================
    
    def momentum_ma_crossover(self, fast_window: int = 5, slow_window: int = 20) -> pd.DataFrame:
        """
        Generate momentum signals based on moving average crossovers.
        
        Mathematical formulation:
        signal_t = {
            +1 if MA_fast(t) > MA_slow(t) and MA_fast(t-1) <= MA_slow(t-1)
            -1 if MA_fast(t) < MA_slow(t) and MA_fast(t-1) >= MA_slow(t-1)
             0 otherwise
        }
        
        Parameters
        ----------
        fast_window : int, default=5
            Fast moving average window
        slow_window : int, default=20
            Slow moving average window
            
        Returns
        -------
        pd.DataFrame
            Momentum signals (-1, 0, +1)
        """
        # Calculate moving averages
        ma_fast = self.prices.rolling(window=fast_window).mean()
        ma_slow = self.prices.rolling(window=slow_window).mean()
        
        # Generate crossover signals
        signals = pd.DataFrame(index=self.prices.index, columns=self.prices.columns, dtype=float)
        
        for asset in self.prices.columns:
            # Current position: 1 if fast > slow, -1 if fast < slow
            position = np.where(ma_fast[asset] > ma_slow[asset], 1, -1)
            
            # Detect crossovers (changes in position)
            position_series = pd.Series(position, index=self.prices.index)
            crossovers = position_series.diff()
            
            # Convert to signals
            signals[asset] = np.where(crossovers == 2, 1,  # Bullish crossover
                                    np.where(crossovers == -2, -1,  # Bearish crossover
                                           0))  # No signal
        
        logger.info(f"Generated MA crossover signals (fast={fast_window}, slow={slow_window})")
        return signals
    
    def momentum_macd(self, fast_period: int = 12, slow_period: int = 26, 
                     signal_period: int = 9) -> pd.DataFrame:
        """
        Generate momentum signals based on MACD indicator.
        
        Mathematical formulation:
        MACD_t = EMA_fast(P_t) - EMA_slow(P_t)
        Signal_line_t = EMA_signal(MACD_t)
        Histogram_t = MACD_t - Signal_line_t
        
        signal_t = sign(Histogram_t) if |Histogram_t| > threshold
        
        Parameters
        ----------
        fast_period : int, default=12
            Fast EMA period for MACD
        slow_period : int, default=26
            Slow EMA period for MACD  
        signal_period : int, default=9
            Signal line EMA period
            
        Returns
        -------
        pd.DataFrame
            MACD-based signals
        """
        signals = pd.DataFrame(index=self.prices.index, columns=self.prices.columns, dtype=float)
        
        for asset in self.prices.columns:
            # Calculate MACD components
            ema_fast = self.prices[asset].ewm(span=fast_period).mean()
            ema_slow = self.prices[asset].ewm(span=slow_period).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal_period).mean()
            histogram = macd_line - signal_line
            
            # Generate signals based on histogram crossover
            signals[asset] = np.where(histogram > 0, 1,
                                    np.where(histogram < 0, -1, 0))
        
        logger.info(f"Generated MACD signals (periods: {fast_period}, {slow_period}, {signal_period})")
        return signals
    
    def mean_reversion_rsi(self, rsi_period: int = 14,
                          oversold_threshold: float = 30,
                          overbought_threshold: float = 70) -> pd.DataFrame:
        """
        Generate mean-reversion signals based on RSI indicator.
        
        Mathematical formulation:
        RSI_t = 100 - (100 / (1 + RS_t))
        
        signal_t = {
            +1 if RSI_t < oversold_threshold (buy oversold)
            -1 if RSI_t > overbought_threshold (sell overbought) 
             0 otherwise
        }
        
        Parameters
        ----------
        rsi_period : int, default=14
            Period for RSI calculation
        oversold_threshold : float, default=30
            RSI level considered oversold
        overbought_threshold : float, default=70
            RSI level considered overbought
            
        Returns
        -------
        pd.DataFrame
            RSI-based mean reversion signals
        """
        signals = pd.DataFrame(index=self.prices.index, columns=self.prices.columns, dtype=float)
        
        for asset in self.prices.columns:
            # Calculate RSI
            delta = self.prices[asset].diff()
            gains = delta.where(delta > 0, 0)
            losses = -delta.where(delta < 0, 0)
            
            avg_gains = gains.ewm(span=rsi_period).mean()
            avg_losses = losses.ewm(span=rsi_period).mean()
            
            rs = avg_gains / avg_losses
            rsi = 100 - (100 / (1 + rs))
            
            # Generate mean reversion signals
            signals[asset] = np.where(rsi < oversold_threshold, 1,
                                    np.where(rsi > overbought_threshold, -1, 0))
        
        logger.info(f"Generated RSI mean reversion signals (thresholds: {oversold_threshold}, {overbought_threshold})")
        return signals
    
    def mean_reversion_bollinger(self, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
        """
        Generate mean-reversion signals based on Bollinger Bands.
        
        Mathematical formulation:
        Upper_band = MA + (num_std × σ)
        Lower_band = MA - (num_std × σ)
        
        signal_t = {
            +1 if P_t < Lower_band (buy when price breaks below)
            -1 if P_t > Upper_band (sell when price breaks above)
             0 otherwise
        }
        
        Parameters
        ----------
        window : int, default=20
            Rolling window for mean and std calculation
        num_std : float, default=2.0
            Number of standard deviations for bands
            
        Returns
        -------
        pd.DataFrame
            Bollinger Band mean reversion signals
        """
        # Calculate Bollinger Bands
        rolling_mean = self.prices.rolling(window=window).mean()
        rolling_std = self.prices.rolling(window=window).std()
        
        upper_band = rolling_mean + (num_std * rolling_std)
        lower_band = rolling_mean - (num_std * rolling_std)
        
        # Generate mean reversion signals
        signals = np.where(self.prices < lower_band, 1,
                         np.where(self.prices > upper_band, -1, 0))
        
        signals = pd.DataFrame(signals, index=self.prices.index, columns=self.prices.columns)
        
        logger.info(f"Generated Bollinger Band signals (window={window}, std={num_std})")
        return signals
    
    def forecast_based_signals(self, mean_forecast: pd.DataFrame,
                             vol_forecast: pd.DataFrame,
                             return_threshold: float = 0.001) -> pd.DataFrame:
        """
        Generate signals based on forecasted returns and volatility.
        
        Mathematical formulation:
        z_score_t = μ_forecast_t / σ_forecast_t
        signal_t = sign(μ_forecast_t) if |μ_forecast_t| > threshold
        
        Parameters
        ----------
        mean_forecast : pd.DataFrame
            Forecasted expected returns
        vol_forecast : pd.DataFrame
            Forecasted volatility
        return_threshold : float, default=0.001
            Minimum expected return threshold
            
        Returns
        -------
        pd.DataFrame
            Forecast-based signals
        """
        # Normalize forecasts by volatility (risk-adjusted signals)
        if self.volatility_scaling:
            risk_adjusted_forecast = mean_forecast / (vol_forecast + 1e-8)  # Add small epsilon
            signals = np.where(np.abs(risk_adjusted_forecast) > return_threshold,
                             np.sign(risk_adjusted_forecast), 0)
        else:
            signals = np.where(np.abs(mean_forecast) > return_threshold,
                             np.sign(mean_forecast), 0)
        
        signals = pd.DataFrame(signals, index=mean_forecast.index, columns=mean_forecast.columns)
        
        logger.info(f"Generated forecast-based signals (threshold={return_threshold})")
        return signals
    
    def volatility_breakout_signals(self, volatility: Optional[pd.DataFrame] = None,
                                  vol_threshold_pct: float = 75,
                                  vol_window: int = 20) -> pd.DataFrame:
        """
        Generate signals based on volatility breakouts.
        
        Mathematical formulation:
        vol_percentile_t = percentile(σ_t, window)
        signal_t = sign(r_t) if vol_percentile_t > threshold
        
        Parameters
        ----------
        volatility : pd.DataFrame, optional
            Volatility estimates (if None, calculated from returns)
        vol_threshold_pct : float, default=75
            Volatility percentile threshold
        vol_window : int, default=20
            Window for volatility calculation if not provided
            
        Returns
        -------
        pd.DataFrame
            Volatility breakout signals
        """
        # Calculate volatility if not provided
        if volatility is None:
            volatility = self.volatility(window=vol_window)
        
        signals = pd.DataFrame(index=self.returns.index, columns=self.returns.columns, dtype=float)
        
        for asset in self.returns.columns:
            if asset in volatility.columns:
                # Calculate rolling volatility percentiles
                vol_percentile = volatility[asset].rolling(window=60).rank(pct=True) * 100
                
                # Generate signals when volatility is high
                high_vol_mask = vol_percentile > vol_threshold_pct
                signals[asset] = np.where(high_vol_mask, np.sign(self.returns[asset]), 0)
            else:
                signals[asset] = 0
        
        logger.info(f"Generated volatility breakout signals (threshold={vol_threshold_pct}%)")
        return signals
    
    def combine_signals(self, signal_dict: Dict[str, pd.DataFrame],
                       weights: Optional[Dict[str, float]] = None) -> pd.DataFrame:
        """
        Combine multiple signal sources with optional weighting.
        
        Mathematical formulation:
        combined_signal_t = Σ(w_i × signal_i_t) / Σ(w_i)
        
        Parameters
        ----------
        signal_dict : Dict[str, pd.DataFrame]
            Dictionary of signal DataFrames
        weights : Dict[str, float], optional
            Optional weights for each signal type
            
        Returns
        -------
        pd.DataFrame
            Combined signals
        """
        if weights is None:
            weights = {name: 1.0 for name in signal_dict.keys()}
        
        # Initialize combined signals
        first_signals = list(signal_dict.values())[0]
        combined = pd.DataFrame(index=first_signals.index, 
                              columns=first_signals.columns, 
                              dtype=float).fillna(0)
        
        total_weight = 0
        
        for signal_name, signals in signal_dict.items():
            weight = weights.get(signal_name, 1.0)
            combined += weight * signals.fillna(0)
            total_weight += weight
        
        # Normalize by total weight
        if total_weight > 0:
            combined = combined / total_weight
        
        # Apply signal threshold
        combined_values = np.where(np.abs(combined) > self.signal_threshold, 
                                  np.sign(combined), 0)
        combined = pd.DataFrame(combined_values, index=combined.index, columns=combined.columns)
        
        logger.info(f"Combined {len(signal_dict)} signal sources")
        return combined
    
    def smooth_signals(self, signals: pd.DataFrame,
                      window: Optional[int] = None) -> pd.DataFrame:
        """
        Apply smoothing to signals to reduce noise.
        
        Parameters
        ----------
        signals : pd.DataFrame
            DataFrame with trading signals
        window : int, optional
            Smoothing window size (uses self.smoothing_window if None)
            
        Returns
        -------
        pd.DataFrame
            Smoothed signals
        """
        if window is None:
            window = self.smoothing_window
        
        # Apply rolling mean and then threshold
        smoothed = signals.rolling(window=window, center=True).mean()
        smoothed = np.where(np.abs(smoothed) > self.signal_threshold,
                          np.sign(smoothed), 0)
        
        smoothed = pd.DataFrame(smoothed, index=signals.index, columns=signals.columns)
        
        logger.info(f"Applied signal smoothing with window {window}")
        return smoothed
    
    def generate_signals(self, data: Optional[Dict[str, pd.DataFrame]] = None,
                        strategies: Optional[List[str]] = None,
                        strategy_weights: Optional[Dict[str, float]] = None) -> pd.DataFrame:
        """
        Main method to generate trading signals using multiple strategies.
        
        Parameters
        ----------
        data : Dict[str, pd.DataFrame], optional
            Dictionary containing price data, forecasts, and indicators
            If None, uses self.prices and self.returns
        strategies : List[str], optional
            List of strategies to use (default: ['ma_crossover', 'macd', 'rsi', 'forecast'])
        strategy_weights : Dict[str, float], optional
            Weights for combining strategies
            
        Returns
        -------
        pd.DataFrame
            Final trading signals
        """
        if strategies is None:
            strategies = ['ma_crossover', 'macd', 'rsi']
        
        # Use internal data if not provided
        if data is None:
            data = {
                'prices': self.prices,
                'returns': self.returns,
                'volatility': self.volatility()
            }
        
        signal_dict = {}
        
        # Generate signals for each strategy
        for strategy in strategies:
            try:
                if strategy == 'ma_crossover':
                    signal_dict['ma_crossover'] = self.momentum_ma_crossover()
                
                elif strategy == 'macd':
                    signal_dict['macd'] = self.momentum_macd()
                
                elif strategy == 'rsi':
                    signal_dict['rsi'] = self.mean_reversion_rsi()
                
                elif strategy == 'bollinger':
                    signal_dict['bollinger'] = self.mean_reversion_bollinger()
                
                elif strategy == 'forecast' and 'mean_forecast' in data and 'vol_forecast' in data:
                    signal_dict['forecast'] = self.forecast_based_signals(
                        data['mean_forecast'], data['vol_forecast'])
                
                elif strategy == 'vol_breakout':
                    vol_data = data.get('volatility', self.volatility())
                    signal_dict['vol_breakout'] = self.volatility_breakout_signals(vol_data)
                
            except Exception as e:
                logger.warning(f"Failed to generate {strategy} signals: {e}")
                continue
        
        if not signal_dict:
            logger.warning("No signals generated")
            # Return empty signals
            return pd.DataFrame(index=self.prices.index, 
                              columns=self.prices.columns).fillna(0)
        
        # Combine signals
        combined_signals = self.combine_signals(signal_dict, strategy_weights)
        
        # Apply smoothing if enabled
        if self.signal_smoothing:
            combined_signals = self.smooth_signals(combined_signals)
        
        logger.info("Signal generation completed")
        return combined_signals
    
    def __repr__(self) -> str:
        """String representation."""
        return (f"StrategySignalGenerator(assets={len(self.assets)}, "
                f"dates={len(self.dates)}, "
                f"period={self.dates[0].date()} to {self.dates[-1].date()})")


# Backward compatibility alias
Strategy = StrategySignalGenerator


def generate_signals(prices: pd.DataFrame,
                   strategies: Optional[List[str]] = None,
                   strategy_weights: Optional[Dict[str, float]] = None,
                   data: Optional[Dict[str, pd.DataFrame]] = None,
                   **kwargs) -> pd.DataFrame:
    """
    Convenience function to generate trading signals.
    
    Parameters
    ----------
    prices : pd.DataFrame
        Price data for creating StrategySignalGenerator
    strategies : List[str], optional
        List of signal strategies to use
    strategy_weights : Dict[str, float], optional
        Weights for combining strategies
    data : Dict[str, pd.DataFrame], optional
        Optional additional data (returns, volatility, forecasts)
    **kwargs
        Additional parameters for StrategySignalGenerator
        
    Returns
    -------
    pd.DataFrame
        Trading signals
        
    Examples
    --------
    >>> signals = generate_signals(prices, strategies=['ma_crossover', 'rsi'])
    >>> signals = generate_signals(prices, strategies=['forecast'], 
    ...                           data={'mean_forecast': mu, 'vol_forecast': sigma})
    """
    generator = StrategySignalGenerator(prices, **kwargs)
    return generator.generate_signals(data, strategies, strategy_weights)


# Backward compatibility
SignalGenerator = StrategySignalGenerator


if __name__ == "__main__":
    # Example usage
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from src.data_loader import load_data
    from src.feature_engineering import make_features
    from src.forecasting import forecast_returns_volatility
    
    # Load sample data
    tickers = ['AAPL', 'MSFT', 'SPY']
    start_date = '2022-01-01'
    end_date = '2024-01-01'
    
    try:
        _, price_data = load_data(tickers, start_date, end_date)
        features = make_features(price_data)
        
        # Generate forecasts
        mean_forecast, vol_forecast = forecast_returns_volatility(
            features['returns'], auto_order=False, steps=1)
        
        # Prepare data for signal generation
        signal_data = {
            'prices': price_data,
            'returns': features['returns'],
            'volatility': features['volatility'],
            'mean_forecast': mean_forecast,
            'vol_forecast': vol_forecast
        }
        
        # Generate signals using unified class
        strategy_gen = StrategySignalGenerator(
            price_data,
            signal_threshold=0.1,
            volatility_scaling=True,
            signal_smoothing=True
        )
        
        strategies = ['ma_crossover', 'macd', 'rsi', 'forecast']
        weights = {'ma_crossover': 0.3, 'macd': 0.2, 'rsi': 0.2, 'forecast': 0.3}
        
        signals = strategy_gen.generate_signals(signal_data, strategies, weights)
        
        print("Signal Generation Results:")
        print(f"Signals shape: {signals.shape}")
        print(f"Signal distribution:")
        print(signals.apply(lambda x: x.value_counts()).fillna(0))
        
        print(f"\nRecent signals:")
        print(signals.tail())
        
        # Test individual strategies
        ma_signals = strategy_gen.momentum_ma_crossover()
        rsi_signals = strategy_gen.mean_reversion_rsi()
        
        print(f"\nMA crossover signals count: {(ma_signals != 0).sum().sum()}")
        print(f"RSI signals count: {(rsi_signals != 0).sum().sum()}")
        
        # Test using convenience function
        quick_signals = generate_signals(price_data, strategies=['ma_crossover', 'rsi'])
        print(f"\nQuick signals generated: {quick_signals.shape}")
        
    except Exception as e:
        print(f"Error in example: {e}")
        print("Note: This example requires other modules to be working")