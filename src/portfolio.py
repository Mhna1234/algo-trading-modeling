"""
Portfolio Backtesting and Analytics Module

This module provides a comprehensive, batteries-included portfolio backtesting
and analytics class that integrates with the existing algorithmic trading system.

The Portfolio class offers:
- Robust backtesting with transaction costs and slippage
- Multiple optimization methods (tangency, target return MVO)
- Flexible rule-based portfolio construction
- Comprehensive performance metrics
- Built-in utilities for equal weight, momentum, and volatility targeting

Key Features:
- Cash is modeled explicitly with risk-free return
- Transaction costs and slippage are properly accounted for
- Rolling rebalancing with customizable frequencies
- No external optimizer dependencies (uses closed-form solutions)
- Extensive performance analytics and risk metrics

Integration with existing system:
- Compatible with ARIMA-GARCH forecasting module
- Works with existing signal generation framework
- Replaces and enhances the backtester module
- Maintains consistency with utils.TradingConfig
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Tuple
import numpy as np
import pandas as pd
from pandas import DataFrame, Series
import logging

logger = logging.getLogger(__name__)


@dataclass
class PortfolioResult:
    """
    Container for portfolio backtest results.
    
    Attributes:
        equity_curve: Portfolio value over time
        weights: Portfolio weights over time (including cash)
        trades: Daily trading activity (weight changes)
        perf: Dictionary of performance metrics
    """
    equity_curve: Series
    weights: DataFrame
    trades: DataFrame
    perf: Dict[str, float]


class Portfolio:
    """
    A compact, batteries-included portfolio backtesting and analytics class.

    This class provides comprehensive portfolio backtesting capabilities including
    transaction costs, slippage, multiple optimization methods, and extensive
    performance analytics. It integrates seamlessly with the existing algorithmic
    trading system's forecasting and signal generation modules.

    Parameters
    ----------
    prices : DataFrame
        Wide-form price DataFrame indexed by datetime, columns = tickers.
    rf : float, optional
        Risk-free rate per period of `prices` frequency (e.g., daily). Default 0.0.
    trading_cost_bps : float, optional
        Round-trip trading cost in basis points applied per turnover (default 0).
        For one-way, cost per trade side = trading_cost_bps / 2.
    slippage_bps : float, optional
        One-way slippage in basis points applied on fills (default 0).
    cash_symbol : str, optional
        Name used for cash in weights outputs (default "CASH").
    """

    def __init__(
        self,
        prices: DataFrame,
        rf: float = 0.0,
        trading_cost_bps: float = 0.0,
        slippage_bps: float = 0.0,
        cash_symbol: str = "CASH",
    ) -> None:
        """
        Initialize Portfolio with price data and cost parameters.
        
        Args:
            prices: Price data with DatetimeIndex and asset columns
            rf: Risk-free rate per period (daily if daily prices)
            trading_cost_bps: Round-trip trading costs in basis points
            slippage_bps: One-way slippage in basis points
            cash_symbol: Symbol name for cash positions
        """
        logger.info(f"Initializing Portfolio with {len(prices.columns)} assets")
        
        # Process and validate price data
        self.prices: DataFrame = prices.sort_index().astype(float)
        if self.prices.isnull().any().any():
            logger.warning("Found NaN values in price data, forward filling...")
            self.prices = self.prices.ffill().dropna(how="all")
        
        self.assets: list[str] = list(self.prices.columns)
        self.rf = rf
        self.trading_cost_bps = float(trading_cost_bps)
        self.slippage_bps = float(slippage_bps)
        self.cash_symbol = cash_symbol

        # Calculate returns
        self.returns = self.prices.pct_change().dropna()
        
        # Align rf series if provided as scalar per period
        if np.ndim(self.rf) == 0:
            self.rf_series = pd.Series(self.rf, index=self.returns.index)
        else:
            rf_series = pd.Series(self.rf).reindex(self.returns.index).ffill().fillna(0.0)
            self.rf_series = rf_series
            
        logger.info(f"Portfolio initialized: {len(self.returns)} periods, "
                   f"RF rate: {self.rf:.4f}, Trading cost: {self.trading_cost_bps}bps")

    # ---------- Utilities

    @staticmethod
    def _annualization_factor(freq: Optional[str], index: pd.DatetimeIndex) -> float:
        """
        Determine annualization factor based on data frequency.
        
        Args:
            freq: Frequency string or None for auto-detection
            index: DatetimeIndex for frequency inference
            
        Returns:
            Annualization factor (252 for daily, 12 for monthly, etc.)
        """
        if freq is None:
            # infer from index
            freq = pd.infer_freq(index) or "D"
        freq = freq.upper()
        if freq.startswith("B") or freq.startswith("D"):
            return 252.0
        if freq.startswith("W"):
            return 52.0
        if freq.startswith("M"):
            return 12.0
        if freq.startswith("Q"):
            return 4.0
        if freq.startswith("A") or freq.startswith("Y"):
            return 1.0
        # fallback heuristic based on median spacing
        days = np.median(np.diff(index.values).astype("timedelta64[D]").astype(int))
        return 252.0 if days <= 2 else 12.0

    @staticmethod
    def _clip_and_renorm(weights: Series, long_only: bool = True, leverage_cap: float = 1.0) -> Series:
        """
        Clip negative weights (if long-only) and renormalize to leverage cap.
        
        Args:
            weights: Portfolio weights
            long_only: Whether to enforce long-only constraint
            leverage_cap: Maximum leverage (sum of absolute weights)
            
        Returns:
            Clipped and renormalized weights
        """
        w = weights.copy().astype(float)
        if long_only:
            w[w < 0.0] = 0.0
        gross = float(w.abs().sum())
        if gross == 0.0:
            return w
        w = w / gross * min(leverage_cap, gross)
        # Renormalize to total weight <= leverage_cap, keep proportions
        total = float(w.sum())
        if total > leverage_cap:
            w = w * (leverage_cap / total)
        return w

    @staticmethod
    def _ridge_inverse(cov: DataFrame, ridge: float = 1e-6) -> np.ndarray:
        """
        Compute ridge-regularized pseudo-inverse of covariance matrix.
        
        Args:
            cov: Covariance matrix
            ridge: Ridge regularization parameter
            
        Returns:
            Regularized inverse matrix
        """
        c = cov.values
        k = cov.shape[0]
        return np.linalg.pinv(c + ridge * np.eye(k))

    # ---------- Optimizers (no external solvers)

    def tangency_weights(
        self,
        lookback: int = 252,
        ridge: float = 1e-4,
        long_only: bool = True,
        leverage_cap: float = 1.0,
        min_var_reg: float = 0.0,
        date: Optional[pd.Timestamp] = None,
    ) -> Series:
        """
        Compute (approximate) tangency portfolio using sample mean/cov with ridge regularization.
        
        This method maximizes the Sharpe ratio using closed-form solutions with
        regularization to handle numerical instability.
        
        Args:
            lookback: Number of periods for estimation window
            ridge: Ridge regularization parameter
            long_only: Whether to enforce long-only constraint
            leverage_cap: Maximum leverage
            min_var_reg: Minimum variance regularization
            date: Specific date for calculation (default: lookback periods from start)
            
        Returns:
            Portfolio weights as Series
        """
        if date is None:
            date = self.returns.index[lookback]
        end_loc = self.returns.index.get_indexer([date], method="pad")[0]
        start_loc = max(0, end_loc - lookback)
        window = self.returns.iloc[start_loc:end_loc]
        mu = window.mean()
        cov = window.cov()
        
        # Add minimum variance regularization if specified
        if min_var_reg > 0:
            cov = cov + np.eye(cov.shape[0]) * min_var_reg * np.trace(cov) / cov.shape[0]
        
        # Compute tangency weights
        inv = self._ridge_inverse(cov, ridge=ridge)
        w = inv @ (mu.values - self.rf_series.iloc[start_loc:end_loc].mean())
        w = pd.Series(w, index=mu.index)
        
        # normalize to sum to 1
        if w.abs().sum() > 0:
            w = w / w.abs().sum()
        
        # Apply constraints
        if long_only or leverage_cap is not None:
            w = self._clip_and_renorm(w, long_only=long_only, leverage_cap=leverage_cap)
        
        logger.debug(f"Computed tangency weights for {date}: {w.sum():.3f} total weight")
        return w

    def target_return_mvo(
        self,
        target_return: float,
        lookback: int = 252,
        ridge: float = 1e-4,
        long_only: bool = True,
        leverage_cap: float = 1.0,
        date: Optional[pd.Timestamp] = None,
    ) -> Series:
        """
        Mean-variance optimization with target return using Lagrangian closed form.
        
        Solves the optimization problem:
        min w'Σw subject to w'μ = target_return, w'1 = 1
        
        Args:
            target_return: Target portfolio return
            lookback: Estimation window length
            ridge: Ridge regularization
            long_only: Long-only constraint
            leverage_cap: Maximum leverage
            date: Date for calculation
            
        Returns:
            Optimal portfolio weights
        """
        if date is None:
            date = self.returns.index[lookback]
        end_loc = self.returns.index.get_indexer([date], method="pad")[0]
        start_loc = max(0, end_loc - lookback)
        window = self.returns.iloc[start_loc:end_loc]
        mu = window.mean().values
        cov = window.cov()
        inv = self._ridge_inverse(cov, ridge=ridge)

        # Lagrangian multiplier solution
        ones = np.ones_like(mu)
        A = ones @ inv @ ones
        B = ones @ inv @ mu
        C = mu @ inv @ mu
        
        # Compute multipliers
        denom = A * C - B * B + 1e-12
        lam = (target_return * A - B) / denom
        gamma = (C - target_return * B) / denom
        
        # Compute weights
        w = lam * (inv @ mu) + gamma * (inv @ ones)
        w = pd.Series(w, index=window.columns)
        w = w / w.sum()  # enforce sum-to-1

        # Apply constraints
        if long_only or leverage_cap is not None:
            w = self._clip_and_renorm(w, long_only=long_only, leverage_cap=leverage_cap)
        
        logger.debug(f"Computed target return MVO weights for {date}: return={target_return:.4f}")
        return w

    # ---------- Backtesting

    def rebalance(
        self,
        target_weights: DataFrame,
        initial_equity: float = 1_000_000.0,
    ) -> PortfolioResult:
        """
        Execute a weights-vs-time backtest with costs & slippage.
        
        This is the core backtesting engine that simulates portfolio performance
        given a time series of target weights, accounting for transaction costs
        and slippage.
        
        Args:
            target_weights: DataFrame with target portfolio weights over time
            initial_equity: Starting portfolio value
            
        Returns:
            PortfolioResult with equity curve, weights, trades, and performance metrics
        """
        logger.info(f"Starting backtest with initial equity: ${initial_equity:,.0f}")
        
        # Align target weights with returns data
        target_weights = target_weights.reindex(self.returns.index).ffill().fillna(0.0)
        
        # Include cash implicitly so weights sum to 1
        cash_w = 1.0 - target_weights.sum(axis=1).clip(lower=-np.inf, upper=np.inf)
        weights = target_weights.copy()
        weights[self.cash_symbol] = cash_w

        # Compute gross returns including cash rf
        asset_rets = self.returns.copy()
        # extend with cash return
        cash_ret = self.rf_series.reindex(asset_rets.index).fillna(0.0)
        asset_rets[self.cash_symbol] = cash_ret.values

        # Calculate turnover and costs
        weights_shift = weights.shift().fillna(0.0)
        turnover = (weights - weights_shift).abs().sum(axis=1)
        one_way_cost = self.trading_cost_bps / 2.0 / 10_000.0
        slippage = self.slippage_bps / 10_000.0
        cost_series = turnover * (one_way_cost + slippage)

        # Daily portfolio return net of costs
        port_ret_gross = (weights * asset_rets).sum(axis=1)
        port_ret_net = port_ret_gross - cost_series

        # Calculate equity curve
        equity = (1.0 + port_ret_net).cumprod() * initial_equity

        # Track trades
        trades = (weights - weights_shift).fillna(0.0)
        
        # Calculate performance metrics
        perf = self._performance_from_returns(port_ret_net)
        
        logger.info(f"Backtest completed: {len(equity)} periods, "
                   f"Final equity: ${equity.iloc[-1]:,.0f}")
        
        return PortfolioResult(
            equity_curve=equity, 
            weights=weights, 
            trades=trades, 
            perf=perf
        )

    def build_target_weights_from_rule(
        self,
        rule: Callable[[pd.Timestamp, Series], Series],
        schedule: Optional[str] = "M",
        lookback: int = 252,
        long_only: bool = True,
        leverage_cap: float = 1.0,
    ) -> DataFrame:
        """
        Apply a rule(date, past_returns_window) -> weights across time on a resampled schedule.
        
        This method enables flexible portfolio construction by applying user-defined
        rules at specified rebalancing frequencies.
        
        Args:
            rule: Function that takes (date, returns_window) and returns weights
            schedule: Rebalancing schedule ('M'=monthly, 'W'=weekly, 'D'=daily, etc.)
            lookback: Lookback window for rule application
            long_only: Enforce long-only constraint
            leverage_cap: Maximum leverage
            
        Returns:
            DataFrame with target weights over time
        """
        logger.info(f"Building target weights with schedule '{schedule}', lookback {lookback}")
        
        idx = self.returns.index
        if schedule is not None:
            try:
                # Convert to period and back to get rebalancing dates
                dates = idx.to_period(schedule).to_timestamp(how="end")
                dates = dates[dates.isin(idx)]
                rebal_dates = dates.unique()
            except (ValueError, AttributeError):
                # Fallback for pandas 2.x: use resample instead
                rebal_dates = idx.to_series().resample(schedule).last().dropna().index
        else:
            rebal_dates = idx

        all_w = []
        for i, d in enumerate(rebal_dates):
            try:
                end_loc = idx.get_indexer([d], method="pad")[0]
                start_loc = max(0, end_loc - lookback)
                window = self.returns.iloc[start_loc:end_loc]
                
                # Apply the rule
                w = rule(d, window.mean())
                w = w.reindex(self.assets).fillna(0.0)
                
                # Apply constraints
                if long_only or leverage_cap is not None:
                    w = self._clip_and_renorm(w, long_only=long_only, leverage_cap=leverage_cap)
                
                s = pd.Series(w, name=d)
                all_w.append(s)
                
            except Exception as e:
                logger.warning(f"Failed to apply rule for date {d}: {e}")
                # Use equal weights as fallback
                w = pd.Series(1.0 / len(self.assets), index=self.assets)
                s = pd.Series(w, name=d)
                all_w.append(s)
        
        # Construct weights DataFrame
        W = pd.DataFrame(all_w).rename_axis(index="date")
        W.index = pd.to_datetime(W.index)
        W = W.reindex(idx).ffill().fillna(0.0)
        
        logger.info(f"Generated weights for {len(rebal_dates)} rebalancing dates")
        return W

    # ---------- Metrics

    def _performance_from_returns(self, r: Series, freq: Optional[str] = None) -> Dict[str, float]:
        """
        Calculate comprehensive performance metrics from return series.
        
        Args:
            r: Return series
            freq: Data frequency for annualization
            
        Returns:
            Dictionary of performance metrics
        """
        ann = self._annualization_factor(freq, r.index)
        
        # Basic metrics
        mean = float(r.mean()) * ann
        vol = float(r.std(ddof=0)) * np.sqrt(ann)
        sharpe = mean / (vol + 1e-12)
        
        # Downside metrics
        downside = r.copy()
        downside[downside > 0] = 0
        downside_vol = float(downside.std(ddof=0)) * np.sqrt(ann)
        sortino = mean / (downside_vol + 1e-12)
        
        # Drawdown metrics
        eq = (1.0 + r).cumprod()
        roll_max = eq.cummax()
        drawdown = (eq / roll_max - 1.0).min()
        
        # Drawdown duration
        is_dd = eq != roll_max
        dd_groups = is_dd.astype(int).groupby((~is_dd).cumsum())
        duration = int(dd_groups.cumcount().max()) if len(dd_groups) > 0 else 0
        
        # Calmar ratio
        calmar = mean / (abs(drawdown) + 1e-12)
        
        # CAGR
        cagr = float((eq.iloc[-1] / eq.iloc[0]) ** (ann / len(r)) - 1.0) if len(r) > 0 else 0.0
        
        return {
            "ann_return": mean,
            "ann_vol": vol,
            "sharpe": sharpe,
            "sortino": sortino,
            "max_drawdown": float(drawdown),
            "max_dd_duration_days": duration,
            "calmar": calmar,
            "cagr": cagr,
        }

    # ---------- Convenience helpers

    @staticmethod
    def from_prices_csv(path: str, **kwargs) -> "Portfolio":
        """
        Create Portfolio instance from CSV file.
        
        Args:
            path: Path to CSV file with price data
            **kwargs: Additional Portfolio initialization parameters
            
        Returns:
            Portfolio instance
        """
        prices = pd.read_csv(path, index_col=0, parse_dates=True)
        return Portfolio(prices, **kwargs)

    def equal_weight_rule(self) -> Callable[[pd.Timestamp, Series], Series]:
        """
        Create equal weight rule for use with build_target_weights_from_rule.
        
        Returns:
            Rule function that returns equal weights
        """
        def rule(date, mu):
            w = pd.Series(1.0 / len(self.assets), index=self.assets)
            return w
        return rule

    def momentum_rule(self, top_k: int = 5) -> Callable[[pd.Timestamp, Series], Series]:
        """
        Create momentum rule that selects top-k assets by recent performance.
        
        Args:
            top_k: Number of top assets to select
            
        Returns:
            Rule function that implements momentum strategy
        """
        def rule(date, mu):
            ranked = mu.sort_values(ascending=False)
            chosen = ranked.index[:top_k]
            w = pd.Series(0.0, index=self.assets)
            w.loc[chosen] = 1.0 / max(1, len(chosen))
            return w
        return rule

    def vol_target_sizer(self, target_vol: float = 0.10, lookback: int = 63) -> Series:
        """
        Create volatility-targeted position sizes.
        
        Args:
            target_vol: Target portfolio volatility
            lookback: Lookback window for volatility estimation
            
        Returns:
            Volatility-adjusted weights
        """
        rets = self.returns.iloc[-lookback:]
        vol = rets.std().mean() * np.sqrt(self._annualization_factor(None, self.returns.index))
        scale = min(3.0, max(0.1, target_vol / (vol + 1e-12)))
        w = pd.Series(1.0 / len(self.assets), index=self.assets) * scale
        return self._clip_and_renorm(w, long_only=True, leverage_cap=1.0)

    # ---------- Integration helpers for existing system
    
    def integrate_with_forecaster(self, 
                                 forecaster,
                                 lookback: int = 252,
                                 method: str = 'tangency',
                                 **kwargs) -> Callable[[pd.Timestamp, Series], Series]:
        """
        Create a rule that integrates with the existing ARIMA-GARCH forecaster.
        
        Args:
            forecaster: ARIMAGARCHForecaster instance
            lookback: Lookback window for estimation
            method: Optimization method ('tangency' or 'target_return')
            **kwargs: Additional parameters for optimization method
            
        Returns:
            Rule function that uses forecaster predictions
        """
        def forecast_rule(date, past_returns):
            try:
                # Get forecast from existing forecaster
                forecast_window = self.returns.loc[self.returns.index <= date].iloc[-lookback:]
                if len(forecast_window) < 10:  # Minimum data requirement
                    return pd.Series(1.0 / len(self.assets), index=self.assets)
                
                # Use forecaster to predict returns
                mean_forecast, _ = forecaster.forecast_returns(forecast_window.iloc[-1:])
                
                if method == 'tangency':
                    weights = self.tangency_weights(
                        lookback=min(lookback, len(forecast_window)),
                        date=date,
                        **kwargs
                    )
                elif method == 'target_return':
                    target_ret = kwargs.get('target_return', mean_forecast.mean())
                    weights = self.target_return_mvo(
                        target_return=target_ret,
                        lookback=min(lookback, len(forecast_window)),
                        date=date,
                        **{k: v for k, v in kwargs.items() if k != 'target_return'}
                    )
                else:
                    # Fallback to equal weights
                    weights = pd.Series(1.0 / len(self.assets), index=self.assets)
                
                return weights
                
            except Exception as e:
                logger.warning(f"Forecast rule failed for {date}: {e}")
                # Fallback to equal weights
                return pd.Series(1.0 / len(self.assets), index=self.assets)
        
        return forecast_rule

    def integrate_with_signals(self, 
                              signals_data: DataFrame,
                              signal_threshold: float = 0.0) -> Callable[[pd.Timestamp, Series], Series]:
        """
        Create a rule that integrates with existing signal generation system.
        
        Args:
            signals_data: DataFrame with trading signals
            signal_threshold: Threshold for signal activation
            
        Returns:
            Rule function that uses signals to determine weights
        """
        def signal_rule(date, past_returns):
            try:
                if date not in signals_data.index:
                    return pd.Series(1.0 / len(self.assets), index=self.assets)
                
                signals = signals_data.loc[date]
                
                # Convert signals to weights
                active_signals = signals[abs(signals) > signal_threshold]
                
                if len(active_signals) == 0:
                    # No active signals, equal weight
                    weights = pd.Series(1.0 / len(self.assets), index=self.assets)
                else:
                    # Weight by signal strength
                    weights = pd.Series(0.0, index=self.assets)
                    signal_sum = abs(active_signals).sum()
                    
                    for asset in active_signals.index:
                        if asset in self.assets:
                            weights[asset] = abs(active_signals[asset]) / signal_sum
                    
                    # Handle any remaining weight
                    remaining_weight = 1.0 - weights.sum()
                    if remaining_weight > 0:
                        # Distribute equally among all assets
                        weights += remaining_weight / len(self.assets)
                
                return weights
                
            except Exception as e:
                logger.warning(f"Signal rule failed for {date}: {e}")
                return pd.Series(1.0 / len(self.assets), index=self.assets)
        
        return signal_rule