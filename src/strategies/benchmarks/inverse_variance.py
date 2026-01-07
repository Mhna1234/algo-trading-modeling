"""
Inverse Variance Portfolio Strategy

Weights inversely proportional to asset variance.
More aggressive penalization of high-volatility assets than inverse volatility.

Mathematical Definition:
    σ²_i = Σ_ii  (asset i variance)
    w_i ∝ 1/σ²_i
    w = w / sum(w)

Properties:
- Stronger penalty for volatility than inverse volatility
- Still ignores correlations
- Simple to implement
- Can be concentrated in low-vol assets

Author: Algo Trading Team
Date: January 2026
"""

import numpy as np
import logging

from src.strategies.benchmarks.base_benchmark import BenchmarkStrategy

logger = logging.getLogger(__name__)


class InverseVarianceBenchmark(BenchmarkStrategy):
    """
    Inverse Variance Portfolio - Aggressive risk-based weighting.
    
    Allocates weights inversely proportional to asset variance.
    Penalizes volatility more heavily than inverse volatility strategy.
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator
    optimizer : PortfolioOptimizer, optional
        Not used
    
    References
    ----------
    Clarke, R., De Silva, H., & Thorley, S. (2011).
    "Minimum-Variance Portfolio Composition"
    Journal of Portfolio Management, 37(2), 31-45.
    
    Examples
    --------
    >>> iv = InverseVarianceBenchmark(strategy)
    >>> weights = iv.compute_weights(mu, Sigma)
    >>> assert np.allclose(weights.sum(), 1.0)
    >>> assert np.all(weights >= 0)
    """
    
    def __init__(self, strategy, optimizer=None, **params):
        """Initialize Inverse Variance benchmark."""
        super().__init__("Inverse Variance Benchmark", strategy, optimizer, **params)
    
    def compute_weights(
        self,
        mu: np.ndarray,
        Sigma: np.ndarray,
        **kwargs
    ) -> np.ndarray:
        """
        Compute inverse variance weights.
        
        Parameters
        ----------
        mu : np.ndarray
            Expected returns (N,) - not used
        Sigma : np.ndarray
            Covariance matrix (N, N)
        
        Returns
        -------
        np.ndarray
            Inverse variance weights
        """
        # Extract diagonal (variances)
        variances = np.diag(Sigma)
        
        # Ensure positive variances
        variances = np.maximum(variances, self.epsilon)
        
        # Inverse variance weights
        weights = 1.0 / variances
        
        # Normalize
        weights = self._normalize(weights)
        
        return weights
