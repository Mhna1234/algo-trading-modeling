"""
Mean Reversion Strategy - Contrarian Portfolio

Invests in assets that have underperformed (negative z-scores).
Exploits mean reversion tendencies in asset prices.

Mathematical Definition:
    z_i = (return_i - mean(returns)) / std(returns)
    w_i ∝ -z_i (higher weight to assets with negative z-scores)
    Normalize to sum to 1

Properties:
- Contrarian approach (buys losers, sells winners)
- Exploits mean reversion
- Risk management via z-score filtering
- Opposite of momentum

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


class MeanReversionBenchmark(BenchmarkStrategy):
    """
    Mean Reversion Portfolio - Contrarian Asset Selection.

    Allocates higher weights to assets with negative recent returns
    (relative to cross-sectional mean), expecting mean reversion.

    Parameters
    ----------
    strategy : Strategy
        Signal generator (provides returns data)
    optimizer : PortfolioOptimizer, optional
        Not used
    lookback : int, optional
        Lookback window for z-score calculation (default: 20 days)
    z_score_threshold : float, optional
        Only invest in assets with z-score below this (default: 0.0)
    min_weight : float, optional
        Minimum weight per asset (default: 0.0)
    max_weight : float, optional
        Maximum weight per asset (default: 0.3)

    References
    ----------
    DeBondt, W. F., & Thaler, R. (1985).
    "Does the Stock Market Overreact?"
    Journal of Finance, 40(3), 793-805.

    Jegadeesh, N. (1990).
    "Evidence of Predictable Behavior of Security Returns"
    Journal of Finance, 45(3), 881-898.

    Examples
    --------
    >>> mr = MeanReversionBenchmark(strategy, lookback=20, z_score_threshold=0.0)
    >>> # Invests in assets with negative recent returns
    """

    def __init__(self, strategy, optimizer=None, **params):
        """Initialize Mean Reversion benchmark."""
        super().__init__("Mean Reversion Benchmark", strategy, optimizer, **params)
        self.lookback = params.get('lookback', 20)
        self.z_score_threshold = params.get('z_score_threshold', 0.0)
        self.min_weight = params.get('min_weight', 0.0)
        self.max_weight = params.get('max_weight', 0.3)

    def get_weights(
        self,
        date: pd.Timestamp,
        portfolio_state: PortfolioState
    ) -> Series:
        """
        Generate mean reversion weights based on z-scores.

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

        # Calculate cumulative returns over lookback period
        returns_window = self.strategy.returns.iloc[date_idx - self.lookback:date_idx]
        cumulative_returns = (1 + returns_window).prod() - 1

        # Calculate z-scores (cross-sectional)
        mean_return = cumulative_returns.mean()
        std_return = cumulative_returns.std()

        if std_return < 1e-8:
            # No variation, use equal weight
            return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)

        z_scores = (cumulative_returns - mean_return) / std_return

        # Mean reversion signal: invert z-scores (buy losers)
        mean_reversion_signal = -z_scores

        # Filter: only invest in assets below threshold (negative z-scores = losers)
        eligible_assets = z_scores[z_scores <= self.z_score_threshold].index

        if len(eligible_assets) == 0:
            # No eligible assets, use equal weight
            return Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)

        # Calculate raw weights proportional to signal strength
        raw_weights = Series(0.0, index=self.strategy.assets)
        raw_weights[eligible_assets] = mean_reversion_signal[eligible_assets]

        # Ensure non-negative (signal is already inverted)
        raw_weights = raw_weights.clip(lower=0.0)

        if raw_weights.sum() < 1e-8:
            # All weights zero, fallback to equal weight among eligible
            raw_weights[eligible_assets] = 1.0 / len(eligible_assets)
        else:
            # Normalize
            raw_weights = raw_weights / raw_weights.sum()

        # Apply weight constraints
        weights = raw_weights.clip(lower=self.min_weight, upper=self.max_weight)

        # Re-normalize after clipping
        if weights.sum() > 1e-8:
            weights = weights / weights.sum()
        else:
            weights = Series(1.0 / len(self.strategy.assets), index=self.strategy.assets)

        return weights

    def compute_weights(
        self,
        mu: np.ndarray,
        Sigma: np.ndarray,
        **kwargs
    ) -> np.ndarray:
        """
        Compute mean reversion weights.

        Parameters
        ----------
        mu : np.ndarray
            Expected returns (N,) - used as recent return proxy
        Sigma : np.ndarray
            Covariance matrix (N, N) - not used

        Returns
        -------
        np.ndarray
            Mean reversion weights
        """
        # Calculate z-scores
        mean_return = np.mean(mu)
        std_return = np.std(mu)

        if std_return < 1e-8:
            # No variation, equal weight
            return np.ones(len(mu)) / len(mu)

        z_scores = (mu - mean_return) / std_return

        # Mean reversion: invert z-scores
        mean_reversion_signal = -z_scores

        # Filter: only negative z-scores
        eligible_mask = z_scores <= self.z_score_threshold
        if not np.any(eligible_mask):
            return np.ones(len(mu)) / len(mu)

        # Calculate weights
        raw_weights = np.maximum(mean_reversion_signal, 0.0)
        raw_weights[~eligible_mask] = 0.0

        if np.sum(raw_weights) < 1e-8:
            # Equal weight among eligible
            raw_weights = eligible_mask.astype(float)

        # Normalize
        weights = raw_weights / np.sum(raw_weights)

        # Apply constraints
        weights = np.clip(weights, self.min_weight, self.max_weight)

        # Re-normalize
        weights = self._normalize(weights)

        return weights
