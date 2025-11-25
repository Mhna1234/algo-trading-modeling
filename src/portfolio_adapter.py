"""
Portfolio Integration Adapter

This module provides adapter functions and utilities to seamlessly integrate
the new Portfolio class with the existing algorithmic trading system components.

Key Features:
- Bridges ARIMA-GARCH forecasting with Portfolio optimization
- Converts existing signal generation to Portfolio rule system
- Provides backward compatibility with existing backtester interface
- Handles configuration translation between old and new systems

Integration Components:
- ForecastPortfolioAdapter: Integrates forecasting with Portfolio class
- SignalPortfolioAdapter: Converts signals to Portfolio rules
- BacktesterAdapter: Provides compatible interface with old backtester
- ConfigurationAdapter: Handles parameter translation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Callable, Any
import logging
from dataclasses import dataclass

from .portfolio import Portfolio, PortfolioResult
from .utils import TradingConfig

logger = logging.getLogger(__name__)


@dataclass
class AdapterResult:
    """
    Result container that provides compatibility with old BacktestResults interface.
    
    This allows existing code to work with minimal changes while using the new
    Portfolio class under the hood.
    """
    # Portfolio class results
    portfolio_result: PortfolioResult
    
    # Computed compatibility fields
    portfolio_returns: pd.Series
    portfolio_weights: pd.DataFrame
    portfolio_nav: pd.Series
    benchmark_returns: pd.Series
    benchmark_nav: pd.Series
    transaction_costs: pd.Series
    turnover: pd.Series
    
    # Performance metrics (computed from Portfolio.perf)
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    calmar_ratio: float
    
    # Benchmark comparison (placeholders for compatibility)
    benchmark_total_return: float = 0.0
    benchmark_sharpe: float = 0.0
    excess_return: float = 0.0
    information_ratio: float = 0.0
    beta: float = 1.0
    alpha: float = 0.0
    
    # Trading metrics
    total_trades: int = 0
    avg_turnover: float = 0.0
    total_transaction_costs: float = 0.0
    
    # Risk metrics
    var_95: float = 0.0
    cvar_95: float = 0.0
    downside_deviation: float = 0.0
    sortino_ratio: float = 0.0
    
    def summary(self) -> Dict[str, float]:
        """Return summary dictionary compatible with old BacktestResults."""
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


class ConfigurationAdapter:
    """
    Handles configuration translation between TradingConfig and Portfolio parameters.
    """
    
    @staticmethod
    def trading_config_to_portfolio_params(config: TradingConfig) -> Dict[str, Any]:
        """
        Convert TradingConfig parameters to Portfolio class initialization parameters.
        
        Args:
            config: TradingConfig instance
            
        Returns:
            Dictionary with Portfolio initialization parameters
        """
        # Convert annual risk-free rate to daily
        daily_rf = config.risk_free_rate / 252.0
        
        # Convert transaction cost percentage to basis points
        trading_cost_bps = config.transaction_cost * 10000.0
        
        return {
            'rf': daily_rf,
            'trading_cost_bps': trading_cost_bps,
            'slippage_bps': config.slippage_bps,
            'cash_symbol': config.cash_symbol
        }
    
    @staticmethod
    def trading_config_to_optimization_params(config: TradingConfig) -> Dict[str, Any]:
        """
        Convert TradingConfig to optimization method parameters.
        
        Args:
            config: TradingConfig instance
            
        Returns:
            Dictionary with optimization parameters
        """
        return {
            'long_only': config.long_only,
            'leverage_cap': config.leverage_cap,
            'ridge': config.ridge_regularization,
            'min_var_reg': config.min_var_regularization,
            'lookback': config.lookback_window
        }


class ForecastPortfolioAdapter:
    """
    Adapter to integrate ARIMA-GARCH forecasting with Portfolio class optimization.
    """
    
    def __init__(self, 
                 portfolio: Portfolio,
                 config: TradingConfig):
        """
        Initialize adapter with Portfolio instance and configuration.
        
        Args:
            portfolio: Portfolio class instance
            config: Trading configuration
        """
        self.portfolio = portfolio
        self.config = config
        self.optimization_params = ConfigurationAdapter.trading_config_to_optimization_params(config)
        
        logger.info(f"Initialized ForecastPortfolioAdapter with method: {config.optimization_method}")
    
    def create_forecast_rule(self, 
                           forecaster,
                           method: Optional[str] = None) -> Callable[[pd.Timestamp, pd.Series], pd.Series]:
        """
        Create a Portfolio rule that uses ARIMA-GARCH forecasts for optimization.
        
        Args:
            forecaster: ARIMAGARCHForecaster instance
            method: Override optimization method ('tangency', 'target_return', or None for config)
            
        Returns:
            Rule function for use with Portfolio.build_target_weights_from_rule()
        """
        opt_method = method or self.config.optimization_method
        
        def forecast_rule(date: pd.Timestamp, past_returns: pd.Series) -> pd.Series:
            """
            Portfolio rule that uses forecaster to generate optimal weights.
            
            Args:
                date: Current rebalancing date
                past_returns: Historical returns window
                
            Returns:
                Portfolio weights for the assets
            """
            try:
                # Get the data window for forecasting
                end_idx = self.portfolio.returns.index.get_loc(date) if date in self.portfolio.returns.index else -1
                start_idx = max(0, end_idx - self.config.lookback_window)
                
                forecast_window = self.portfolio.returns.iloc[start_idx:end_idx+1]
                
                if len(forecast_window) < 20:  # Minimum data requirement
                    logger.warning(f"Insufficient data for forecasting at {date}, using equal weights")
                    return pd.Series(1.0 / len(self.portfolio.assets), index=self.portfolio.assets)
                
                # Generate forecasts using existing forecaster
                try:
                    mean_forecasts, vol_forecasts = forecaster.forecast_portfolio(
                        returns=forecast_window,
                        steps=1
                    )
                    
                    # Use the latest forecast
                    if len(mean_forecasts) > 0:
                        expected_returns = mean_forecasts.iloc[-1]
                    else:
                        # Fallback to historical mean
                        expected_returns = past_returns
                        
                except Exception as forecast_error:
                    logger.warning(f"Forecasting failed at {date}: {forecast_error}, using historical mean")
                    expected_returns = past_returns
                
                # Apply optimization based on method
                if opt_method == 'sharpe' or opt_method == 'tangency':
                    weights = self.portfolio.tangency_weights(
                        date=date,
                        **self.optimization_params
                    )
                    
                elif opt_method == 'mean_variance':
                    # Use target return based on expected returns
                    target_return = expected_returns.mean() * 1.2  # 20% above mean
                    weights = self.portfolio.target_return_mvo(
                        target_return=target_return,
                        date=date,
                        **{k: v for k, v in self.optimization_params.items() if k != 'min_var_reg'}
                    )
                    
                elif opt_method == 'risk_parity':
                    # Simple risk parity approximation using inverse volatility
                    if len(vol_forecasts) > 0:
                        vols = vol_forecasts.iloc[-1]
                    else:
                        vols = forecast_window.std()
                    
                    inv_vol = 1.0 / (vols + 1e-8)
                    weights = inv_vol / inv_vol.sum()
                    weights = pd.Series(weights, index=self.portfolio.assets)
                    
                else:
                    # Default to equal weights
                    logger.warning(f"Unknown optimization method: {opt_method}, using equal weights")
                    weights = pd.Series(1.0 / len(self.portfolio.assets), index=self.portfolio.assets)
                
                # Ensure weights are properly formatted
                weights = weights.reindex(self.portfolio.assets).fillna(0.0)
                
                # Apply constraints
                if self.config.long_only or self.config.leverage_cap < float('inf'):
                    weights = self.portfolio._clip_and_renorm(
                        weights, 
                        long_only=self.config.long_only, 
                        leverage_cap=self.config.leverage_cap
                    )
                
                logger.debug(f"Generated forecast-based weights for {date}: sum={weights.sum():.3f}")
                return weights
                
            except Exception as e:
                logger.error(f"Forecast rule failed for {date}: {e}")
                # Emergency fallback to equal weights
                return pd.Series(1.0 / len(self.portfolio.assets), index=self.portfolio.assets)
        
        return forecast_rule
    
    def generate_weights_from_forecasts(self,
                                      forecaster,
                                      schedule: str = "M") -> pd.DataFrame:
        """
        Generate complete time series of weights using forecasts.
        
        Args:
            forecaster: ARIMAGARCHForecaster instance
            schedule: Rebalancing schedule
            
        Returns:
            DataFrame with target weights over time
        """
        logger.info(f"Generating forecast-based weights with schedule: {schedule}")
        
        forecast_rule = self.create_forecast_rule(forecaster)
        
        weights_df = self.portfolio.build_target_weights_from_rule(
            rule=forecast_rule,
            schedule=schedule,
            lookback=self.config.lookback_window,
            long_only=self.config.long_only,
            leverage_cap=self.config.leverage_cap
        )
        
        logger.info(f"Generated weights for {len(weights_df)} periods")
        return weights_df


class SignalPortfolioAdapter:
    """
    Adapter to integrate existing signal generation with Portfolio class.
    """
    
    def __init__(self, 
                 portfolio: Portfolio,
                 config: TradingConfig):
        """
        Initialize adapter.
        
        Args:
            portfolio: Portfolio instance
            config: Trading configuration
        """
        self.portfolio = portfolio
        self.config = config
        
        logger.info("Initialized SignalPortfolioAdapter")
    
    def create_signal_rule(self, 
                          signals_data: pd.DataFrame,
                          signal_threshold: Optional[float] = None) -> Callable[[pd.Timestamp, pd.Series], pd.Series]:
        """
        Create Portfolio rule from existing signals data.
        
        Args:
            signals_data: DataFrame with trading signals over time
            signal_threshold: Threshold for signal activation (default from config)
            
        Returns:
            Rule function for Portfolio class
        """
        threshold = signal_threshold or self.config.signal_threshold
        
        def signal_rule(date: pd.Timestamp, past_returns: pd.Series) -> pd.Series:
            """
            Convert signals to portfolio weights.
            
            Args:
                date: Current date
                past_returns: Historical returns (not used for signals)
                
            Returns:
                Portfolio weights based on signals
            """
            try:
                if date not in signals_data.index:
                    # No signals for this date, use equal weights
                    return pd.Series(1.0 / len(self.portfolio.assets), index=self.portfolio.assets)
                
                signals = signals_data.loc[date]
                
                # Filter signals by threshold
                active_signals = signals[abs(signals) > threshold]
                
                if len(active_signals) == 0:
                    # No active signals, equal weight
                    weights = pd.Series(1.0 / len(self.portfolio.assets), index=self.portfolio.assets)
                else:
                    # Weight proportionally to signal strength
                    weights = pd.Series(0.0, index=self.portfolio.assets)
                    
                    # Normalize active signals
                    signal_weights = abs(active_signals) / abs(active_signals).sum()
                    
                    for asset in active_signals.index:
                        if asset in self.portfolio.assets:
                            weights[asset] = signal_weights[asset]
                    
                    # Distribute any remaining weight equally
                    total_weight = weights.sum()
                    if total_weight < 1.0:
                        remaining = 1.0 - total_weight
                        weights += remaining / len(self.portfolio.assets)
                
                logger.debug(f"Generated signal-based weights for {date}: "
                           f"{len(active_signals)} active signals")
                return weights
                
            except Exception as e:
                logger.warning(f"Signal rule failed for {date}: {e}")
                return pd.Series(1.0 / len(self.portfolio.assets), index=self.portfolio.assets)
        
        return signal_rule
    
    def generate_weights_from_signals(self,
                                    signals_data: pd.DataFrame,
                                    schedule: str = "M") -> pd.DataFrame:
        """
        Generate weights time series from signals.
        
        Args:
            signals_data: Signals DataFrame
            schedule: Rebalancing schedule
            
        Returns:
            Target weights DataFrame
        """
        logger.info("Generating signal-based weights")
        
        signal_rule = self.create_signal_rule(signals_data)
        
        weights_df = self.portfolio.build_target_weights_from_rule(
            rule=signal_rule,
            schedule=schedule,
            lookback=self.config.lookback_window,
            long_only=self.config.long_only,
            leverage_cap=self.config.leverage_cap
        )
        
        return weights_df


class BacktesterAdapter:
    """
    Adapter that provides backward compatibility with the old Backtester interface.
    """
    
    def __init__(self, config: TradingConfig):
        """
        Initialize adapter with configuration.
        
        Args:
            config: Trading configuration
        """
        self.config = config
        self.portfolio = None
        self.portfolio_params = ConfigurationAdapter.trading_config_to_portfolio_params(config)
        
        logger.info("Initialized BacktesterAdapter")
    
    def run_backtest(self,
                    price_data: pd.DataFrame,
                    weight_data: pd.DataFrame,
                    benchmark_data: Optional[pd.DataFrame] = None,
                    signals_data: Optional[pd.DataFrame] = None) -> AdapterResult:
        """
        Run backtest using Portfolio class with old Backtester interface.
        
        Args:
            price_data: Historical price data
            weight_data: Target portfolio weights
            benchmark_data: Benchmark price data (optional)
            signals_data: Trading signals (optional, not used directly)
            
        Returns:
            AdapterResult with compatibility interface
        """
        logger.info("Running backtest via BacktesterAdapter")
        
        # Initialize Portfolio with price data
        self.portfolio = Portfolio(price_data, **self.portfolio_params)
        
        # Run the backtest
        portfolio_result = self.portfolio.rebalance(
            target_weights=weight_data,
            initial_equity=self.config.initial_capital
        )
        
        # Calculate additional metrics for compatibility
        adapter_result = self._create_adapter_result(
            portfolio_result, 
            benchmark_data,
            price_data.index
        )
        
        logger.info("Backtest completed via adapter")
        return adapter_result
    
    def _create_adapter_result(self,
                             portfolio_result: PortfolioResult,
                             benchmark_data: Optional[pd.DataFrame],
                             date_index: pd.DatetimeIndex) -> AdapterResult:
        """
        Create AdapterResult from PortfolioResult with computed compatibility fields.
        
        Args:
            portfolio_result: Result from Portfolio.rebalance()
            benchmark_data: Benchmark data for comparison
            date_index: Date index for alignment
            
        Returns:
            AdapterResult with all compatibility fields
        """
        # Extract basic series
        equity_curve = portfolio_result.equity_curve
        weights = portfolio_result.weights
        trades = portfolio_result.trades
        perf = portfolio_result.perf
        
        # Calculate portfolio returns from equity curve
        portfolio_returns = equity_curve.pct_change().dropna()
        
        # Calculate transaction costs and turnover from trades
        turnover = trades.abs().sum(axis=1)
        transaction_costs = turnover * (self.config.transaction_cost + self.config.slippage_bps / 10000.0)
        
        # Process benchmark data
        if benchmark_data is not None and len(benchmark_data) > 0:
            benchmark_prices = benchmark_data.iloc[:, 0]
            benchmark_returns = benchmark_prices.pct_change().dropna()
            benchmark_nav = (1 + benchmark_returns).cumprod() * self.config.initial_capital
            
            # Align with portfolio data
            common_dates = portfolio_returns.index.intersection(benchmark_returns.index)
            if len(common_dates) > 0:
                port_ret_aligned = portfolio_returns.loc[common_dates]
                bench_ret_aligned = benchmark_returns.loc[common_dates]
                
                # Calculate benchmark metrics
                benchmark_total_return = (benchmark_nav.iloc[-1] / self.config.initial_capital) - 1
                benchmark_sharpe = bench_ret_aligned.mean() / bench_ret_aligned.std() * np.sqrt(252)
                
                # Calculate relative metrics
                excess_returns = port_ret_aligned - bench_ret_aligned
                excess_return = excess_returns.mean() * 252
                information_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252) \
                                 if excess_returns.std() > 0 else 0.0
                
                # Simple beta calculation
                if len(common_dates) > 10:
                    cov_matrix = pd.concat([port_ret_aligned, bench_ret_aligned], axis=1).cov()
                    beta = cov_matrix.iloc[0, 1] / cov_matrix.iloc[1, 1] if cov_matrix.iloc[1, 1] != 0 else 1.0
                    alpha = (perf['ann_return'] - self.config.risk_free_rate) - \
                           beta * (benchmark_sharpe * perf['ann_vol'])
                else:
                    beta, alpha = 1.0, 0.0
            else:
                benchmark_total_return = 0.0
                benchmark_sharpe = 0.0
                excess_return = perf['ann_return']
                information_ratio = 0.0
                beta, alpha = 1.0, 0.0
                benchmark_nav = pd.Series(self.config.initial_capital, index=date_index)
                benchmark_returns = pd.Series(0.0, index=date_index)
        else:
            benchmark_total_return = 0.0
            benchmark_sharpe = 0.0
            excess_return = perf['ann_return']
            information_ratio = 0.0
            beta, alpha = 1.0, 0.0
            benchmark_nav = pd.Series(self.config.initial_capital, index=date_index)
            benchmark_returns = pd.Series(0.0, index=date_index)
        
        # Calculate additional risk metrics
        var_95 = portfolio_returns.quantile(0.05) if len(portfolio_returns) > 0 else 0.0
        cvar_95 = portfolio_returns[portfolio_returns <= var_95].mean() if len(portfolio_returns) > 0 else 0.0
        
        downside_returns = portfolio_returns[portfolio_returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0.0
        
        return AdapterResult(
            portfolio_result=portfolio_result,
            portfolio_returns=portfolio_returns,
            portfolio_weights=weights.drop(columns=[self.config.cash_symbol], errors='ignore'),
            portfolio_nav=equity_curve,
            benchmark_returns=benchmark_returns,
            benchmark_nav=benchmark_nav,
            transaction_costs=transaction_costs,
            turnover=turnover,
            total_return=(equity_curve.iloc[-1] / self.config.initial_capital) - 1,
            annualized_return=perf['ann_return'],
            volatility=perf['ann_vol'],
            sharpe_ratio=perf['sharpe'],
            max_drawdown=perf['max_drawdown'],
            calmar_ratio=perf['calmar'],
            benchmark_total_return=benchmark_total_return,
            benchmark_sharpe=benchmark_sharpe,
            excess_return=excess_return,
            information_ratio=information_ratio,
            beta=beta,
            alpha=alpha,
            total_trades=len(trades[trades.abs().sum(axis=1) > 0]),
            avg_turnover=turnover.mean(),
            total_transaction_costs=transaction_costs.sum(),
            var_95=var_95,
            cvar_95=cvar_95,
            downside_deviation=downside_deviation,
            sortino_ratio=perf['sortino']
        )