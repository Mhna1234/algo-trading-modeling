"""
Equal Weight Portfolio Strategy (1/N)

The simplest and most robust benchmark strategy.
Allocates equal weight to all N assets.

Mathematical Definition:
    w_i = 1/N for all i

Properties:
- No parameter estimation required
- Immune to estimation error
- Optimal under certain conditions (equal Sharpe ratios)
- Serves as baseline for comparing sophisticated strategies

Author: Algo Trading Team
Date: January 2026
"""

import numpy as np
import logging

from src.strategies.benchmarks.base_benchmark import BenchmarkStrategy

logger = logging.getLogger(__name__)


class EqualWeightBenchmark(BenchmarkStrategy):
    """
    Equal Weight Portfolio (1/N) - Naive Diversification Benchmark.
    
    Allocates exactly 1/N to each asset, regardless of expected returns
    or covariance structure.
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator (provides asset list)
    optimizer : PortfolioOptimizer, optional
        Not used by Equal Weight
    
    References
    ----------
    DeMiguel, V., Garlappi, L., & Uppal, R. (2009).
    "Optimal versus naive diversification: How inefficient is the 1/N portfolio strategy?"
    Review of Financial Studies, 22(5), 1915-1953.
    
    Examples
    --------
    >>> ew = EqualWeightBenchmark(strategy)
    >>> weights = ew.compute_weights(mu, Sigma)
    >>> assert np.allclose(weights.sum(), 1.0)
    >>> assert np.all(weights == 1/len(mu))
    """
    
    def __init__(self, strategy, optimizer=None, **params):
        """Initialize Equal Weight benchmark."""
        super().__init__("Equal Weight Benchmark", strategy, optimizer, **params)
    
    def compute_weights(
        self,
        mu: np.ndarray,
        Sigma: np.ndarray,
        **kwargs
    ) -> np.ndarray:
        """
        Compute equal weights for all assets.
        
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
        weights = np.ones(n) / n
        
        return weights
