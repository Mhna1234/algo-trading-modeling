"""
Buy and Hold Strategy - Passive Benchmark

The ultimate passive benchmark that invests initially and never rebalances.
Represents pure market exposure with zero transaction costs.

Mathematical Definition:
    w_0 = 1/N (initial equal weight)
    w_t = w_0 (no rebalancing, weights drift naturally)

Properties:
- Zero rebalancing (minimal transaction costs)
- Weights drift with asset performance
- Pure market exposure
- Simplest possible strategy

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


class BuyAndHoldBenchmark(BenchmarkStrategy):
    """
    Buy and Hold - Passive Benchmark Strategy.

    Invests equal initial capital in all assets and never rebalances.
    Weights drift naturally with asset performance.

    Parameters
    ----------
    strategy : Strategy
        Signal generator (provides asset list)
    optimizer : PortfolioOptimizer, optional
        Not used by Buy and Hold

    References
    ----------
    Sharpe, W. F. (1991).
    "The Arithmetic of Active Management"
    Financial Analysts Journal, 47(1), 7-9.

    Examples
    --------
    >>> bh = BuyAndHoldBenchmark(strategy)
    >>> # On first call, returns equal weights
    >>> # On subsequent calls, returns current portfolio weights (no rebalance)
    """

    def __init__(self, strategy, optimizer=None, **params):
        """Initialize Buy and Hold benchmark."""
        super().__init__("Buy and Hold Benchmark", strategy, optimizer, **params)

    def get_weights(
        self,
        date: pd.Timestamp,
        portfolio_state: PortfolioState
    ) -> Series:
        """
        Return current portfolio weights without rebalancing.

        On first allocation, sets equal weights across all assets.
        Subsequently, returns existing weights to avoid rebalancing.

        Parameters
        ----------
        date : pd.Timestamp
            Current rebalancing date (not used)
        portfolio_state : PortfolioState
            Portfolio state with current holdings

        Returns
        -------
        pd.Series
            Current weights (equal weight on first call, drifting thereafter)
        """
        # Get current weights for risky assets only (exclude CASH)
        current_asset_weights = portfolio_state.current_weights.reindex(
            self.strategy.assets, fill_value=0.0
        )

        # If we have actual allocations in risky assets, use them (no rebalancing)
        if current_asset_weights.sum() > 1e-6:
            return current_asset_weights

        # Initial allocation: equal weight across all risky assets
        n = len(self.strategy.assets)
        return Series(1.0 / n, index=self.strategy.assets)

    def compute_weights(
        self,
        mu: np.ndarray,
        Sigma: np.ndarray,
        **kwargs
    ) -> np.ndarray:
        """
        Compute equal weights for initial allocation.

        Note: This is only called on first allocation. Subsequent calls
        use get_weights() which returns current weights without calling
        this method.

        Parameters
        ----------
        mu : np.ndarray
            Expected returns (N,) - not used
        Sigma : np.ndarray
            Covariance matrix (N, N) - not used

        Returns
        -------
        np.ndarray
            Equal weights (1/N for each asset)
        """
        n = len(mu)
        return np.ones(n) / n
