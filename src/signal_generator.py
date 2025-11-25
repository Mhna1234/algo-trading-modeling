"""
Signal Generation Module

This module converts forecasts and technical indicators into trading signals.
It implements various signal generation strategies:
- Momentum signals (moving average crossovers, MACD)
- Mean-reversion signals (RSI, Bollinger Bands)
- Forecast-based signals (expected return thresholds)
- Volatility-scaled signals
- Combined signals with multiple strategies

Mathematical Formulations:
- Basic Signal: signal_t = sign(indicator_t - threshold)
- Volatility-Scaled Signal: weight_t = signal_t / σ_t
- Z-Score Signal: z_t = (x_t - μ_t) / σ_t
- Momentum Signal: signal_t = sign(MA_fast - MA_slow)
- Mean Reversion: signal_t = -sign(z_score) if |z_score| > threshold
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Callable
import warnings
import logging

logger = logging.getLogger(__name__)

class SignalGenerator:
    """
    Comprehensive signal generation for algorithmic trading.
    
    This class provides methods to generate various types of trading signals
    based on forecasts, technical indicators, and market conditions.
    """
    
    def __init__(self, 
                 signal_threshold: float = 0.0,
                 volatility_scaling: bool = True,
                 signal_smoothing: bool = True,
                 smoothing_window: int = 3):
        """
        Initialize SignalGenerator with configuration parameters.
        
        Args:
            signal_threshold: Minimum threshold for signal generation
            volatility_scaling: Whether to scale signals by volatility
            signal_smoothing: Whether to apply smoothing to signals
            smoothing_window: Window size for signal smoothing
        """
        self.signal_threshold = signal_threshold
        self.volatility_scaling = volatility_scaling
        self.signal_smoothing = signal_smoothing
        self.smoothing_window = smoothing_window
        
    def momentum_ma_crossover(self, prices: pd.DataFrame,
                            fast_window: int = 5,
                            slow_window: int = 20) -> pd.DataFrame:
        """
        Generate momentum signals based on moving average crossovers.
        
        Mathematical formulation:
        signal_t = {
            +1 if MA_fast(t) > MA_slow(t) and MA_fast(t-1) <= MA_slow(t-1)
            -1 if MA_fast(t) < MA_slow(t) and MA_fast(t-1) >= MA_slow(t-1)
             0 otherwise
        }
        
        Args:
            prices: DataFrame with asset prices
            fast_window: Fast moving average window
            slow_window: Slow moving average window
            
        Returns:
            DataFrame with momentum signals (-1, 0, +1)
        """
        # Calculate moving averages
        ma_fast = prices.rolling(window=fast_window).mean()
        ma_slow = prices.rolling(window=slow_window).mean()
        
        # Generate crossover signals
        signals = pd.DataFrame(index=prices.index, columns=prices.columns, dtype=float)
        
        for asset in prices.columns:
            # Current position: 1 if fast > slow, -1 if fast < slow
            position = np.where(ma_fast[asset] > ma_slow[asset], 1, -1)
            
            # Detect crossovers (changes in position)
            position_series = pd.Series(position, index=prices.index)
            crossovers = position_series.diff()
            
            # Convert to signals
            signals[asset] = np.where(crossovers == 2, 1,  # Bullish crossover
                                    np.where(crossovers == -2, -1,  # Bearish crossover
                                           0))  # No signal
        
        logger.info(f"Generated MA crossover signals (fast={fast_window}, slow={slow_window})")
        return signals
    
    def momentum_macd(self, prices: pd.DataFrame,
                     fast_period: int = 12,
                     slow_period: int = 26,
                     signal_period: int = 9) -> pd.DataFrame:
        """
        Generate momentum signals based on MACD indicator.
        
        Mathematical formulation:
        MACD_t = EMA_fast(P_t) - EMA_slow(P_t)
        Signal_line_t = EMA_signal(MACD_t)
        Histogram_t = MACD_t - Signal_line_t
        
        signal_t = sign(Histogram_t) if |Histogram_t| > threshold
        
        Args:
            prices: DataFrame with asset prices
            fast_period: Fast EMA period for MACD
            slow_period: Slow EMA period for MACD  
            signal_period: Signal line EMA period
            
        Returns:
            DataFrame with MACD-based signals
        """
        signals = pd.DataFrame(index=prices.index, columns=prices.columns, dtype=float)
        
        for asset in prices.columns:
            # Calculate MACD components
            ema_fast = prices[asset].ewm(span=fast_period).mean()
            ema_slow = prices[asset].ewm(span=slow_period).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal_period).mean()
            histogram = macd_line - signal_line
            
            # Generate signals based on histogram crossover
            signals[asset] = np.where(histogram > 0, 1,
                                    np.where(histogram < 0, -1, 0))
        
        logger.info(f"Generated MACD signals (periods: {fast_period}, {slow_period}, {signal_period})")
        return signals
    
    def mean_reversion_rsi(self, prices: pd.DataFrame,
                          rsi_period: int = 14,
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
        
        Args:
            prices: DataFrame with asset prices
            rsi_period: Period for RSI calculation
            oversold_threshold: RSI level considered oversold
            overbought_threshold: RSI level considered overbought
            
        Returns:
            DataFrame with RSI-based mean reversion signals
        """
        signals = pd.DataFrame(index=prices.index, columns=prices.columns, dtype=float)
        
        for asset in prices.columns:
            # Calculate RSI
            delta = prices[asset].diff()
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
    
    def mean_reversion_bollinger(self, prices: pd.DataFrame,
                               window: int = 20,
                               num_std: float = 2.0) -> pd.DataFrame:
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
        
        Args:
            prices: DataFrame with asset prices
            window: Rolling window for mean and std calculation
            num_std: Number of standard deviations for bands
            
        Returns:
            DataFrame with Bollinger Band mean reversion signals
        """
        signals = pd.DataFrame(index=prices.index, columns=prices.columns, dtype=float)
        
        # Calculate Bollinger Bands
        rolling_mean = prices.rolling(window=window).mean()
        rolling_std = prices.rolling(window=window).std()
        
        upper_band = rolling_mean + (num_std * rolling_std)
        lower_band = rolling_mean - (num_std * rolling_std)
        
        # Generate mean reversion signals
        signals = np.where(prices < lower_band, 1,
                         np.where(prices > upper_band, -1, 0))
        
        signals = pd.DataFrame(signals, index=prices.index, columns=prices.columns)
        
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
        
        Args:
            mean_forecast: Forecasted expected returns
            vol_forecast: Forecasted volatility
            return_threshold: Minimum expected return threshold
            
        Returns:
            DataFrame with forecast-based signals
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
    
    def volatility_breakout_signals(self, returns: pd.DataFrame,
                                  volatility: pd.DataFrame,
                                  vol_threshold_pct: float = 75) -> pd.DataFrame:
        """
        Generate signals based on volatility breakouts.
        
        Mathematical formulation:
        vol_percentile_t = percentile(σ_t, window)
        signal_t = sign(r_t) if vol_percentile_t > threshold
        
        Args:
            returns: DataFrame with asset returns
            volatility: DataFrame with volatility estimates
            vol_threshold_pct: Volatility percentile threshold
            
        Returns:
            DataFrame with volatility breakout signals
        """
        signals = pd.DataFrame(index=returns.index, columns=returns.columns, dtype=float)
        
        for asset in returns.columns:
            if asset in volatility.columns:
                # Calculate rolling volatility percentiles
                vol_percentile = volatility[asset].rolling(window=60).rank(pct=True) * 100
                
                # Generate signals when volatility is high
                high_vol_mask = vol_percentile > vol_threshold_pct
                signals[asset] = np.where(high_vol_mask, np.sign(returns[asset]), 0)
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
        
        Args:
            signal_dict: Dictionary of signal DataFrames
            weights: Optional weights for each signal type
            
        Returns:
            DataFrame with combined signals
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
        combined = np.where(np.abs(combined) > self.signal_threshold, 
                          np.sign(combined), 0)
        
        logger.info(f"Combined {len(signal_dict)} signal sources")
        return combined
    
    def smooth_signals(self, signals: pd.DataFrame,
                      window: Optional[int] = None) -> pd.DataFrame:
        """
        Apply smoothing to signals to reduce noise.
        
        Args:
            signals: DataFrame with trading signals
            window: Smoothing window size
            
        Returns:
            DataFrame with smoothed signals
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
    
    def generate_signals(self, data: Dict[str, pd.DataFrame],
                        strategies: List[str] = None,
                        strategy_weights: Optional[Dict[str, float]] = None) -> pd.DataFrame:
        """
        Main method to generate trading signals using multiple strategies.
        
        Args:
            data: Dictionary containing price data, forecasts, and indicators
            strategies: List of strategies to use
            strategy_weights: Weights for combining strategies
            
        Returns:
            DataFrame with final trading signals
        """
        if strategies is None:
            strategies = ['ma_crossover', 'macd', 'rsi', 'forecast']
        
        signal_dict = {}
        
        # Generate signals for each strategy
        for strategy in strategies:
            try:
                if strategy == 'ma_crossover' and 'prices' in data:
                    signal_dict['ma_crossover'] = self.momentum_ma_crossover(data['prices'])
                
                elif strategy == 'macd' and 'prices' in data:
                    signal_dict['macd'] = self.momentum_macd(data['prices'])
                
                elif strategy == 'rsi' and 'prices' in data:
                    signal_dict['rsi'] = self.mean_reversion_rsi(data['prices'])
                
                elif strategy == 'bollinger' and 'prices' in data:
                    signal_dict['bollinger'] = self.mean_reversion_bollinger(data['prices'])
                
                elif strategy == 'forecast' and 'mean_forecast' in data and 'vol_forecast' in data:
                    signal_dict['forecast'] = self.forecast_based_signals(
                        data['mean_forecast'], data['vol_forecast'])
                
                elif strategy == 'vol_breakout' and 'returns' in data and 'volatility' in data:
                    signal_dict['vol_breakout'] = self.volatility_breakout_signals(
                        data['returns'], data['volatility'])
                
            except Exception as e:
                logger.warning(f"Failed to generate {strategy} signals: {e}")
                continue
        
        if not signal_dict:
            logger.warning("No signals generated")
            # Return empty signals
            if 'prices' in data:
                return pd.DataFrame(index=data['prices'].index, 
                                  columns=data['prices'].columns).fillna(0)
            else:
                raise ValueError("No valid data provided for signal generation")
        
        # Combine signals
        combined_signals = self.combine_signals(signal_dict, strategy_weights)
        
        # Apply smoothing if enabled
        if self.signal_smoothing:
            combined_signals = self.smooth_signals(combined_signals)
        
        logger.info("Signal generation completed")
        return combined_signals


def generate_signals(data: Dict[str, pd.DataFrame],
                   strategies: List[str] = None,
                   strategy_weights: Optional[Dict[str, float]] = None,
                   **kwargs) -> pd.DataFrame:
    """
    Convenience function to generate trading signals.
    
    Args:
        data: Dictionary containing market data and forecasts
        strategies: List of signal strategies to use
        strategy_weights: Weights for combining strategies
        **kwargs: Additional parameters for SignalGenerator
        
    Returns:
        DataFrame with trading signals
    """
    generator = SignalGenerator(**kwargs)
    return generator.generate_signals(data, strategies, strategy_weights)


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
        
        # Generate signals
        generator = SignalGenerator(
            signal_threshold=0.1,
            volatility_scaling=True,
            signal_smoothing=True
        )
        
        strategies = ['ma_crossover', 'macd', 'rsi', 'forecast']
        weights = {'ma_crossover': 0.3, 'macd': 0.2, 'rsi': 0.2, 'forecast': 0.3}
        
        signals = generator.generate_signals(signal_data, strategies, weights)
        
        print("Signal Generation Results:")
        print(f"Signals shape: {signals.shape}")
        print(f"Signal distribution:")
        print(signals.apply(lambda x: x.value_counts()).fillna(0))
        
        print(f"\nRecent signals:")
        print(signals.tail())
        
        # Test individual strategies
        ma_signals = generator.momentum_ma_crossover(price_data)
        rsi_signals = generator.mean_reversion_rsi(price_data)
        
        print(f"\nMA crossover signals count: {(ma_signals != 0).sum().sum()}")
        print(f"RSI signals count: {(rsi_signals != 0).sum().sum()}")
        
    except Exception as e:
        print(f"Error in example: {e}")
        print("Note: This example requires other modules to be working")