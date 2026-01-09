"""
Quintile Factor Strategy - Momentum Factor Portfolio

Sorts assets by momentum factor and invests in top quintile.
Exploits momentum anomaly documented in academic literature.

Mathematical Definition:
    momentum_i = (P_t / P_{t-lookback}) - 1
    Select top K assets by momentum
    w_i = 1/K if asset i in top quintile, else 0

Properties:
- Factor-based selection (momentum)
- Equal weight within selected quintile
- Exploits cross-sectional momentum
- Low turnover within quintile

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


class QuintileFactorBenchmark(BenchmarkStrategy):
    """
    Quintile Factor Portfolio - Momentum-based Asset Selection.

    Sorts assets by momentum and invests equally in the top quintile.
    Exploits the momentum anomaly.

    Parameters
    ----------
    strategy : Strategy
        Signal generator (provides price data)
    optimizer : PortfolioOptimizer, optional
        Not used
    lookback : int, optional
        Lookback window for momentum calculation (default: 126 = 6 months)
    n_quintiles : int, optional
        Number of quintiles to create (default: 5)
    target_quintile : int, optional
        Which quintile to invest in (1=lowest, 5=highest) (default: 5)

    References
    ----------
    Jegadeesh, N., & Titman, S. (1993).
    "Returns to Buying Winners and Selling Losers"
    Journal of Finance, 48(1), 65-91.

    Carhart, M. M. (1997).
    "On Persistence in Mutual Fund Performance"
    Journal of Finance, 52(1), 57-82.

    Examples
    --------
    >>> qf = QuintileFactorBenchmark(strategy, lookback=126, target_quintile=5)
    >>> # Invests in top 20% momentum assets
    """

    def __init__(self, strategy, optimizer=None, **params):
        """Initialize Quintile Factor benchmark."""
        super().__init__("Quintile Factor Benchmark", strategy, optimizer, **params)
        self.lookback = params.get('lookback', 126)
        self.n_quintiles = params.get('n_quintiles', 5)
        self.target_quintile = params.get('target_quintile', 5)

    def get_weights(
        self,
        date: pd.Timestamp,
        portfolio_state: PortfolioState
    ) -> Series:
        """
        Generate quintile factor weights based on momentum.

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

        # Calculate momentum factor (total return over lookback period)
        prices_current = self.strategy.prices.loc[date]
        prices_past = self.strategy.prices.iloc[date_idx - self.lookback]
        momentum = (prices_current / prices_past) - 1.0

        # Sort by momentum (descending = high to low)
        sorted_momentum = momentum.sort_values(ascending=False)
        n_assets = len(sorted_momentum)
        assets_per_quintile = max(1, n_assets // self.n_quintiles)

        # Select target quintile
        start_idx = (self.target_quintile - 1) * assets_per_quintile
        end_idx = start_idx + assets_per_quintile
        quintile_assets = sorted_momentum.iloc[start_idx:end_idx].index

        # Equal weight within quintile
        weights = Series(0.0, index=self.strategy.assets)
        weights[quintile_assets] = 1.0 / len(quintile_assets)

        return weights

    def compute_weights(
        self,
        mu: np.ndarray,
        Sigma: np.ndarray,
        **kwargs
    ) -> np.ndarray:
        """
        Compute quintile factor weights.

        Note: This method is not typically called for QuintileFactor since
        get_weights() directly accesses price data. This is here for
        compatibility with base class.

        Parameters
        ----------
        mu : np.ndarray
            Expected returns (N,) - used as momentum proxy
        Sigma : np.ndarray
            Covariance matrix (N, N) - not used

        Returns
        -------
        np.ndarray
            Quintile weights
        """
        # Sort by expected returns (momentum proxy)
        sorted_indices = np.argsort(mu)[::-1]  # Descending order
        n_assets = len(mu)
        assets_per_quintile = max(1, n_assets // self.n_quintiles)

        # Select target quintile
        start_idx = (self.target_quintile - 1) * assets_per_quintile
        end_idx = start_idx + assets_per_quintile
        quintile_indices = sorted_indices[start_idx:end_idx]

        # Equal weight within quintile
        weights = np.zeros(n_assets)
        weights[quintile_indices] = 1.0 / len(quintile_indices)

        return weights
