"""
Inverse Volatility Portfolio Strategy

Weights inversely proportional to individual asset volatility.
Higher volatility assets receive lower weight.

Mathematical Definition:
    σ_i = sqrt(Σ_ii)  (asset i volatility)
    w_i ∝ 1/σ_i
    w = w / sum(w)

Properties:
- Simple risk-based allocation
- No correlation information used
- Intuitive: reduce exposure to volatile assets
- More stable than inverse variance

Author: Algo Trading Team
Date: January 2026
"""

import numpy as np
import logging

from src.strategies.benchmarks.base_benchmark import BenchmarkStrategy

logger = logging.getLogger(__name__)


class InverseVolatilityBenchmark(BenchmarkStrategy):
    """
    Inverse Volatility Portfolio - Risk-based weighting.
    
    Allocates weights inversely proportional to asset volatility.
    Assets with higher volatility receive lower weight.
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator
    optimizer : PortfolioOptimizer, optional
        Not used
    
    References
    ----------
    Leote de Carvalho, R., Lu, X., & Moulin, P. (2012).
    "Demystifying Equity Risk-Based Strategies: A Simple Alpha Plus Beta Description"
    Journal of Portfolio Management, 38(3), 56-70.
    
    Examples
    --------
    >>> iv = InverseVolatilityBenchmark(strategy)
    >>> weights = iv.compute_weights(mu, Sigma)
    >>> assert np.allclose(weights.sum(), 1.0)
    >>> assert np.all(weights >= 0)
    """
    
    def __init__(self, strategy, optimizer=None, **params):
        """Initialize Inverse Volatility benchmark."""
        super().__init__("Inverse Volatility Benchmark", strategy, optimizer, **params)
    
    def compute_weights(
        self,
        mu: np.ndarray,
        Sigma: np.ndarray,
        **kwargs
    ) -> np.ndarray:
        """
        Compute inverse volatility weights.
        
        Parameters
        ----------
        mu : np.ndarray
            Expected returns (N,) - not used
        Sigma : np.ndarray
            Covariance matrix (N, N)
        
        Returns
        -------
        np.ndarray
            Inverse volatility weights
        """
        # Extract diagonal (variances)
        variances = np.diag(Sigma)
        
        # Compute volatilities
        volatilities = np.sqrt(np.maximum(variances, self.epsilon))
        
        # Inverse volatility weights
        weights = 1.0 / volatilities
        
        # Normalize
        weights = self._normalize(weights)
        
        return weights
