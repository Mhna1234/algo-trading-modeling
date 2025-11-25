"""
Time Series Forecasting Module

This module implements ARIMA + GARCH models for forecasting expected returns
and volatility in financial time series data.

Mathematical Background:
- ARIMA(p,d,q): AR(p) + I(d) + MA(q) components
  * AR(p): r_t = φ₁r_{t-1} + φ₂r_{t-2} + ... + φₚr_{t-p} + ε_t
  * I(d): Differencing to achieve stationarity
  * MA(q): ε_t = θ₁ε_{t-1} + θ₂ε_{t-2} + ... + θₚε_{t-q} + a_t

- GARCH(p,q): Generalized Autoregressive Conditional Heteroskedasticity
  * σ²_t = ω + Σα_i·ε²_{t-i} + Σβ_j·σ²_{t-j}
  * For GARCH(1,1): σ²_t = ω + α·ε²_{t-1} + β·σ²_{t-1}

Combined Model:
- ARIMA forecasts conditional mean: E[r_{t+1}|F_t]
- GARCH forecasts conditional variance: Var[r_{t+1}|F_t]
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
import warnings
import logging
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
from arch import arch_model
from sklearn.metrics import mean_squared_error, mean_absolute_error
import matplotlib.pyplot as plt

# Suppress some warnings for cleaner output
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

logger = logging.getLogger(__name__)

class ARIMAGARCHForecaster:
    """
    Combined ARIMA + GARCH forecasting model for financial time series.
    
    This class implements a two-stage approach:
    1. ARIMA model for conditional mean forecasting
    2. GARCH model for conditional volatility forecasting
    """
    
    def __init__(self, 
                 arima_order: Tuple[int, int, int] = (1, 0, 1),
                 garch_order: Tuple[int, int] = (1, 1),
                 auto_order: bool = True,
                 max_p: int = 5,
                 max_q: int = 5):
        """
        Initialize ARIMA-GARCH forecaster.
        
        Args:
            arima_order: (p, d, q) order for ARIMA model
            garch_order: (p, q) order for GARCH model  
            auto_order: Whether to automatically select optimal orders
            max_p: Maximum p for auto order selection
            max_q: Maximum q for auto order selection
        """
        self.arima_order = arima_order
        self.garch_order = garch_order
        self.auto_order = auto_order
        self.max_p = max_p
        self.max_q = max_q
        
        # Store fitted models
        self.arima_models = {}
        self.garch_models = {}
        self.fitted_assets = []
        
    def check_stationarity(self, series: pd.Series, 
                          significance_level: float = 0.05) -> Tuple[bool, float]:
        """
        Check if time series is stationary using Augmented Dickey-Fuller test.
        
        H₀: Series has unit root (non-stationary)
        H₁: Series is stationary
        
        Args:
            series: Time series to test
            significance_level: Significance level for test
            
        Returns:
            Tuple of (is_stationary, p_value)
        """
        # Drop NaN values
        series_clean = series.dropna()
        
        if len(series_clean) < 10:
            logger.warning(f"Series too short for stationarity test: {len(series_clean)}")
            return False, 1.0
        
        try:
            adf_result = adfuller(series_clean, autolag='AIC')
            p_value = adf_result[1]
            is_stationary = p_value < significance_level
            
            logger.debug(f"ADF test p-value: {p_value:.4f}, stationary: {is_stationary}")
            return is_stationary, p_value
            
        except Exception as e:
            logger.warning(f"Error in stationarity test: {e}")
            return False, 1.0
    
    def find_optimal_arima_order(self, series: pd.Series) -> Tuple[int, int, int]:
        """
        Find optimal ARIMA order using information criteria.
        
        This method tries different combinations of (p,d,q) and selects
        the one with the lowest AIC (Akaike Information Criterion).
        
        Args:
            series: Time series data
            
        Returns:
            Optimal (p, d, q) order
        """
        best_aic = np.inf
        best_order = self.arima_order
        
        # Determine d (differencing order) based on stationarity
        d_max = 2
        for d in range(d_max + 1):
            if d == 0:
                test_series = series
            else:
                test_series = series.diff(d).dropna()
            
            is_stationary, _ = self.check_stationarity(test_series)
            if is_stationary:
                break
        else:
            d = 1  # Default to first difference
        
        # Grid search for p and q
        for p in range(self.max_p + 1):
            for q in range(self.max_q + 1):
                try:
                    model = ARIMA(series, order=(p, d, q))
                    fitted_model = model.fit()
                    
                    if fitted_model.aic < best_aic:
                        best_aic = fitted_model.aic
                        best_order = (p, d, q)
                        
                except Exception:
                    continue
        
        logger.info(f"Optimal ARIMA order: {best_order} (AIC: {best_aic:.2f})")
        return best_order
    
    def find_optimal_garch_order(self, residuals: pd.Series) -> Tuple[int, int]:
        """
        Find optimal GARCH order using information criteria.
        
        Args:
            residuals: Residuals from ARIMA model
            
        Returns:
            Optimal (p, q) order for GARCH
        """
        best_aic = np.inf
        best_order = self.garch_order
        
        # Grid search for GARCH orders
        max_order = min(3, len(residuals) // 10)  # Prevent overfitting
        
        for p in range(1, max_order + 1):
            for q in range(1, max_order + 1):
                try:
                    model = arch_model(residuals, vol='GARCH', p=p, q=q)
                    fitted_model = model.fit(disp='off')
                    
                    if fitted_model.aic < best_aic:
                        best_aic = fitted_model.aic
                        best_order = (p, q)
                        
                except Exception:
                    continue
        
        logger.info(f"Optimal GARCH order: {best_order} (AIC: {best_aic:.2f})")
        return best_order
    
    def fit_arima(self, series: pd.Series, asset_name: str) -> object:
        """
        Fit ARIMA model to a single time series.
        
        Args:
            series: Time series data (returns)
            asset_name: Name of the asset
            
        Returns:
            Fitted ARIMA model
        """
        # Remove NaN values
        series_clean = series.dropna()
        
        if len(series_clean) < 50:
            logger.warning(f"Insufficient data for {asset_name}: {len(series_clean)} points")
            return None
        
        try:
            # Determine optimal order if auto_order is True
            if self.auto_order:
                order = self.find_optimal_arima_order(series_clean)
            else:
                order = self.arima_order
            
            # Fit ARIMA model
            model = ARIMA(series_clean, order=order)
            fitted_model = model.fit()
            
            logger.info(f"ARIMA{order} fitted for {asset_name}")
            return fitted_model
            
        except Exception as e:
            logger.error(f"Error fitting ARIMA for {asset_name}: {e}")
            return None
    
    def fit_garch(self, residuals: pd.Series, asset_name: str) -> object:
        """
        Fit GARCH model to ARIMA residuals.
        
        Args:
            residuals: Residuals from ARIMA model
            asset_name: Name of the asset
            
        Returns:
            Fitted GARCH model
        """
        try:
            # Determine optimal order if auto_order is True
            if self.auto_order:
                p, q = self.find_optimal_garch_order(residuals)
            else:
                p, q = self.garch_order
            
            # Fit GARCH model
            model = arch_model(residuals, vol='GARCH', p=p, q=q)
            fitted_model = model.fit(disp='off')
            
            logger.info(f"GARCH({p},{q}) fitted for {asset_name}")
            return fitted_model
            
        except Exception as e:
            logger.error(f"Error fitting GARCH for {asset_name}: {e}")
            return None
    
    def fit(self, returns: pd.DataFrame) -> 'ARIMAGARCHForecaster':
        """
        Fit ARIMA-GARCH models to all assets in the returns DataFrame.
        
        Args:
            returns: DataFrame with returns for multiple assets
            
        Returns:
            Self (fitted forecaster)
        """
        logger.info(f"Fitting ARIMA-GARCH models for {len(returns.columns)} assets")
        
        self.fitted_assets = []
        
        for asset in returns.columns:
            logger.info(f"Fitting models for {asset}")
            
            # Fit ARIMA model
            arima_model = self.fit_arima(returns[asset], asset)
            
            if arima_model is not None:
                self.arima_models[asset] = arima_model
                
                # Get residuals for GARCH
                residuals = arima_model.resid
                
                # Fit GARCH model to residuals
                garch_model = self.fit_garch(residuals, asset)
                
                if garch_model is not None:
                    self.garch_models[asset] = garch_model
                    self.fitted_assets.append(asset)
                else:
                    # Remove ARIMA model if GARCH failed
                    del self.arima_models[asset]
        
        logger.info(f"Successfully fitted models for {len(self.fitted_assets)} assets")
        return self
    
    def forecast_single_asset(self, asset: str, 
                            steps: int = 1) -> Dict[str, np.ndarray]:
        """
        Generate forecasts for a single asset.
        
        Args:
            asset: Asset name
            steps: Number of steps ahead to forecast
            
        Returns:
            Dictionary with mean and volatility forecasts
        """
        if asset not in self.fitted_assets:
            raise ValueError(f"Model not fitted for asset: {asset}")
        
        arima_model = self.arima_models[asset]
        garch_model = self.garch_models[asset]
        
        try:
            # ARIMA forecast for mean
            arima_forecast = arima_model.forecast(steps=steps)
            mean_forecast = arima_forecast.values if hasattr(arima_forecast, 'values') else arima_forecast
            
            # GARCH forecast for volatility
            garch_forecast = garch_model.forecast(horizon=steps)
            vol_forecast = np.sqrt(garch_forecast.variance.values[-1, :])
            
            return {
                'mean': mean_forecast,
                'volatility': vol_forecast
            }
            
        except Exception as e:
            logger.error(f"Error forecasting for {asset}: {e}")
            return {
                'mean': np.zeros(steps),
                'volatility': np.ones(steps) * 0.01  # Default small volatility
            }
    
    def forecast_portfolio(self, returns: pd.DataFrame, 
                         steps: int = 1) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Generate forecasts for all assets in portfolio.
        
        Args:
            returns: Historical returns data
            steps: Number of steps ahead to forecast
            
        Returns:
            Tuple of (mean_forecasts, volatility_forecasts)
        """
        # Fit models if not already fitted
        if not self.fitted_assets:
            self.fit(returns)
        
        mean_forecasts = pd.DataFrame(index=range(steps), columns=self.fitted_assets)
        vol_forecasts = pd.DataFrame(index=range(steps), columns=self.fitted_assets)
        
        for asset in self.fitted_assets:
            forecasts = self.forecast_single_asset(asset, steps)
            mean_forecasts[asset] = forecasts['mean']
            vol_forecasts[asset] = forecasts['volatility']
        
        return mean_forecasts, vol_forecasts
    
    def evaluate_forecast_accuracy(self, returns: pd.DataFrame,
                                 test_period: int = 60) -> Dict[str, Dict[str, float]]:
        """
        Evaluate forecast accuracy using rolling window validation.
        
        Args:
            returns: Full returns data
            test_period: Number of periods for out-of-sample testing
            
        Returns:
            Dictionary with accuracy metrics for each asset
        """
        if test_period >= len(returns):
            raise ValueError("Test period too long for available data")
        
        # Split data
        train_data = returns.iloc[:-test_period]
        test_data = returns.iloc[-test_period:]
        
        # Fit on training data
        self.fit(train_data)
        
        results = {}
        
        for asset in self.fitted_assets:
            mean_errors = []
            vol_errors = []
            
            # Rolling one-step-ahead forecasts
            for i in range(test_period - 1):
                # Forecast next period
                forecasts = self.forecast_single_asset(asset, steps=1)
                
                # Actual values
                actual_return = test_data[asset].iloc[i + 1]
                actual_vol = abs(actual_return)  # Proxy for realized volatility
                
                # Forecast errors
                mean_error = abs(forecasts['mean'][0] - actual_return)
                vol_error = abs(forecasts['volatility'][0] - actual_vol)
                
                mean_errors.append(mean_error)
                vol_errors.append(vol_error)
            
            # Calculate metrics
            results[asset] = {
                'mean_mae': np.mean(mean_errors),
                'mean_rmse': np.sqrt(np.mean(np.array(mean_errors) ** 2)),
                'vol_mae': np.mean(vol_errors),
                'vol_rmse': np.sqrt(np.mean(np.array(vol_errors) ** 2))
            }
        
        return results
    
    def get_model_summary(self, asset: str) -> Dict[str, str]:
        """
        Get summary statistics for fitted models.
        
        Args:
            asset: Asset name
            
        Returns:
            Dictionary with model summaries
        """
        if asset not in self.fitted_assets:
            return {}
        
        arima_summary = str(self.arima_models[asset].summary())
        garch_summary = str(self.garch_models[asset].summary())
        
        return {
            'arima_summary': arima_summary,
            'garch_summary': garch_summary
        }


def forecast_returns_volatility(returns: pd.DataFrame,
                               arima_order: Tuple[int, int, int] = (1, 0, 1),
                               garch_order: Tuple[int, int] = (1, 1),
                               auto_order: bool = True,
                               steps: int = 1) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Convenience function to forecast returns and volatility.
    
    Args:
        returns: Historical returns data
        arima_order: ARIMA model order
        garch_order: GARCH model order
        auto_order: Whether to automatically select orders
        steps: Forecast horizon
        
    Returns:
        Tuple of (mean_forecasts, volatility_forecasts)
    """
    forecaster = ARIMAGARCHForecaster(
        arima_order=arima_order,
        garch_order=garch_order,
        auto_order=auto_order
    )
    
    return forecaster.forecast_portfolio(returns, steps)


if __name__ == "__main__":
    # Example usage
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from src.data_loader import load_data
    from src.feature_engineering import make_features
    
    # Load sample data
    tickers = ['AAPL', 'MSFT', 'SPY']
    start_date = '2020-01-01'
    end_date = '2024-01-01'
    
    try:
        _, price_data = load_data(tickers, start_date, end_date)
        features = make_features(price_data)
        returns = features['returns']
        
        # Initialize forecaster
        forecaster = ARIMAGARCHForecaster(auto_order=True)
        
        # Fit models
        forecaster.fit(returns)
        
        # Generate forecasts
        mean_forecast, vol_forecast = forecaster.forecast_portfolio(returns, steps=5)
        
        print("ARIMA-GARCH Forecasting Results:")
        print(f"Successfully fitted models for: {forecaster.fitted_assets}")
        print(f"\nMean forecasts (next 5 days):")
        print(mean_forecast)
        print(f"\nVolatility forecasts (next 5 days):")
        print(vol_forecast)
        
        # Evaluate accuracy (if enough data)
        if len(returns) > 100:
            accuracy = forecaster.evaluate_forecast_accuracy(returns, test_period=30)
            print(f"\nForecast accuracy (30-day test):")
            for asset, metrics in accuracy.items():
                print(f"{asset}: Mean MAE={metrics['mean_mae']:.4f}, Vol MAE={metrics['vol_mae']:.4f}")
        
    except Exception as e:
        print(f"Error in example: {e}")
        print("Note: This example requires data_loader.py and feature_engineering.py")