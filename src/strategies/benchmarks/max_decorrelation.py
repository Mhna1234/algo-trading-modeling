"""
Maximum Decorrelation Portfolio

Applies Global Minimum Variance Portfolio to the correlation matrix
instead of the covariance matrix. This finds the portfolio with
minimum correlation-weighted variance.

Mathematical Definition:
    1. Compute correlation matrix: C = D^(-1) Σ D^(-1)
       where D = diag(sqrt(diag(Σ)))
    2. Apply GMVP to C:
       w* = C^(-1) 1 / (1^T C^(-1) 1)

Properties:
- Reduces correlation exposure
- Treats all volatilities equally
- Useful when correlations are more stable than volatilities
- Related to "most decorrelated" portfolio

Author: Algo Trading Team
Date: January 2026
"""

import numpy as np
import logging

from src.strategies.benchmarks.base_benchmark import BenchmarkStrategy

logger = logging.getLogger(__name__)


class MaxDecorrelationBenchmark(BenchmarkStrategy):
    """
    Maximum Decorrelation Portfolio.
    
    Applies GMVP to the correlation matrix instead of covariance matrix.
    This minimizes correlation-weighted portfolio variance.
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator
    optimizer : PortfolioOptimizer, optional
        Not used
    ridge : float, optional
        Ridge regularization (default: 1e-5)
    
    References
    ----------
    Christoffersen, P., Errunza, V., Jacobs, K., & Langlois, H. (2012).
    "Is the Potential for International Diversification Disappearing?"
    Review of Financial Studies, 25(12), 3711-3751.
    
    Examples
    --------
    >>> maxdecorr = MaxDecorrelationBenchmark(strategy)
    >>> weights = maxdecorr.compute_weights(mu, Sigma)
    >>> assert np.allclose(weights.sum(), 1.0)
    """
    
    def __init__(self, strategy, optimizer=None, **params):
        """Initialize Maximum Decorrelation benchmark."""
        super().__init__("Max Decorrelation Benchmark", strategy, optimizer, **params)
    
    def compute_weights(
        self,
        mu: np.ndarray,
        Sigma: np.ndarray,
        **kwargs
    ) -> np.ndarray:
        """
        Compute maximum decorrelation portfolio weights.
        
        Steps:
        1. Extract volatilities from Sigma
        2. Compute correlation matrix C
        3. Apply GMVP to C
        
        Parameters
        ----------
        mu : np.ndarray
            Expected returns (N,) - not used
        Sigma : np.ndarray
            Covariance matrix (N, N)
        
        Returns
        -------
        np.ndarray
            Max decorrelation weights
        """
        n = len(mu)
        ones = np.ones(n)
        
        # Extract volatilities (diagonal standard deviations)
        variances = np.diag(Sigma)
        volatilities = np.sqrt(np.maximum(variances, self.epsilon))
        
        # Create diagonal matrix D = diag(σ)
        D = np.diag(volatilities)
        D_inv = np.diag(1.0 / volatilities)
        
        # Compute correlation matrix: C = D^(-1) Σ D^(-1)
        C = D_inv @ Sigma @ D_inv
        
        # Ensure C is valid correlation matrix (diag = 1)
        # (numerical errors can make diagonal != 1)
        np.fill_diagonal(C, 1.0)
        
        # Ensure C is PSD
        C_safe = self._safe_cov(C)
        
        # Apply GMVP to correlation matrix: solve C w = 1
        w_unnorm = self._safe_solve(C_safe, ones)
        
        # Normalize
        weights = self._normalize(w_unnorm)
        
        return weights
