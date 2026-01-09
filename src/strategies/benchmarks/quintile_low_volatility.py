"""
Quintile Low Volatility Strategy - Defensive Factor Portfolio

Sorts assets by volatility and invests in lowest volatility quintile.
Exploits the low-volatility anomaly in equity markets.

Mathematical Definition:
    vol_i = std(returns_i) over lookback window
    Select bottom K assets by volatility
    w_i = 1/K if asset i in low-vol quintile, else 0

Properties:
- Defensive portfolio construction
- Exploits low-volatility anomaly
- Equal weight within selected quintile
- Lower drawdowns than market

Author: Algo Trading Team
Date: January 2026
"""

import numpy as np
import pandas as pd
from pandas import Series
import logging

from src.strategies.benchmarks.base_benchmark import BenchmarkStrategy
from src.portfolio_engine import PortfolioState

logger = logging.getLogger(__name__)


class QuintileLowVolatilityBenchmark(BenchmarkStrategy):
    """
    Quintile Low Volatility Portfolio - Defensive Asset Selection.

    Sorts assets by volatility and invests equally in the lowest quintile.
    Exploits the low-volatility anomaly.

    Parameters
    ----------
    strategy : Strategy
        Signal generator (provides returns data)
    optimizer : PortfolioOptimizer, optional
        Not used
    lookback : int, optional
        Lookback window for volatility calculation (default: 126 = 6 months)
    n_quintiles : int, optional
        Number of quintiles to create (default: 5)
    target_quintile : int, optional
        Which quintile to invest in (1=lowest vol, 5=highest vol) (default: 1)
    rebalance_method : str, optional
        Weight method within quintile ('equal' or 'inverse_vol') (default: 'equal')

    References
    ----------
    Baker, M., Bradley, B., & Wurgler, J. (2011).
    "Benchmarks as Limits to Arbitrage: Understanding the Low-Volatility Anomaly"
    Financial Analysts Journal, 67(1), 40-54.

    Blitz, D., & van Vliet, P. (2007).
    "The Volatility Effect"
    Journal of Portfolio Management, 34(1), 102-113.

    Examples
    --------
    >>> qlv = QuintileLowVolatilityBenchmark(strategy, lookback=126, target_quintile=1)
    >>> # Invests in lowest 20% volatility assets
    """

    def __init__(self, strategy, optimizer=None, **params):
        """Initialize Quintile Low Volatility benchmark."""
        super().__init__("Quintile Low Volatility Benchmark", strategy, optimizer, **params)
        self.lookback = params.get('lookback', 126)
        self.n_quintiles = params.get('n_quintiles', 5)
        self.target_quintile = params.get('target_quintile', 1)
        self.rebalance_method = params.get('rebalance_method', 'equal')

    def get_weights(
        self,
        date: pd.Timestamp,
        portfolio_state: PortfolioState
    ) -> Series:
        """
        Generate low volatility quintile weights.

        Parameters
        ----------
        date : pd.Timestamp
            Current rebalancing date
        portfolio_state : PortfolioState
            Portfolio state (used for fallback during warmup)

        Returns
        -------
        pd.Series
            Target weights for risky assets
        """
        # Check data availability
        try:
            date_idx = self.strategy.prices.index.get_loc(date)
        except KeyError:
            logger.warning(f"Date {date} not in price index, using equal weight")
            return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)

        if date_idx < self.lookback:
            # Not enough history, use equal weight or current weights
            if portfolio_state.current_weights is not None and len(portfolio_state.current_weights) > 0:
                return portfolio_state.current_weights.reindex(self.strategy.assets, fill_value=0.0)
            return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)

        # Calculate volatility for all assets
        returns_window = self.strategy.returns.iloc[date_idx - self.lookback:date_idx]
        volatility = returns_window.std()

        # Sort by volatility (ascending = low to high)
        sorted_vol = volatility.sort_values(ascending=True)
        n_assets = len(sorted_vol)
        assets_per_quintile = max(1, n_assets // self.n_quintiles)

        # Select target quintile
        start_idx = (self.target_quintile - 1) * assets_per_quintile
        end_idx = start_idx + assets_per_quintile
        quintile_assets = sorted_vol.iloc[start_idx:end_idx].index

        # Initialize weights
        weights = Series(0.0, index=self.strategy.assets)

        # Weight within quintile
        if self.rebalance_method == 'equal':
            weights[quintile_assets] = 1.0 / len(quintile_assets)
        elif self.rebalance_method == 'inverse_vol':
            # Weight inversely proportional to volatility
            quintile_vols = volatility[quintile_assets]
            inv_vol = 1.0 / (quintile_vols + 1e-8)
            weights[quintile_assets] = inv_vol / inv_vol.sum()
        else:
            weights[quintile_assets] = 1.0 / len(quintile_assets)

        return weights

    def compute_weights(
        self,
        mu: np.ndarray,
        Sigma: np.ndarray,
        **kwargs
    ) -> np.ndarray:
        """
        Compute quintile low volatility weights.

        Parameters
        ----------
        mu : np.ndarray
            Expected returns (N,) - not used
        Sigma : np.ndarray
            Covariance matrix (N, N) - used to extract volatilities

        Returns
        -------
        np.ndarray
            Quintile weights
        """
        # Extract volatilities from diagonal of covariance matrix
        volatilities = np.sqrt(np.diag(Sigma))

        # Sort by volatility (ascending = low to high)
        sorted_indices = np.argsort(volatilities)
        n_assets = len(volatilities)
        assets_per_quintile = max(1, n_assets // self.n_quintiles)

        # Select target quintile
        start_idx = (self.target_quintile - 1) * assets_per_quintile
        end_idx = start_idx + assets_per_quintile
        quintile_indices = sorted_indices[start_idx:end_idx]

        # Weight within quintile
        weights = np.zeros(n_assets)
        if self.rebalance_method == 'equal':
            weights[quintile_indices] = 1.0 / len(quintile_indices)
        elif self.rebalance_method == 'inverse_vol':
            quintile_vols = volatilities[quintile_indices]
            inv_vol = 1.0 / (quintile_vols + 1e-8)
            weights[quintile_indices] = inv_vol / inv_vol.sum()
        else:
            weights[quintile_indices] = 1.0 / len(quintile_indices)

        return weights
