"""
Global Minimum Variance Portfolio (GMVP)

Finds the portfolio with minimum variance, ignoring expected returns.
This is the leftmost point on the efficient frontier.

Mathematical Definition:
    minimize: w^T Σ w
    subject to: w^T 1 = 1
    
Closed-form solution:
    w* = Σ^(-1) 1 / (1^T Σ^(-1) 1)

Properties:
- No return estimation required (immune to μ estimation error)
- Uses only covariance information
- Optimal for risk-averse investors with no return views
- Leftmost point on efficient frontier

Author: Algo Trading Team
Date: January 2026
"""

import numpy as np
import logging

from src.strategies.benchmarks.base_benchmark import BenchmarkStrategy

logger = logging.getLogger(__name__)


class GlobalMinVarianceBenchmark(BenchmarkStrategy):
    """
    Global Minimum Variance Portfolio (GMVP).
    
    Finds the portfolio with minimum variance. Uses closed-form solution:
        w* = Σ^(-1) 1 / (1^T Σ^(-1) 1)
    
    Never uses matrix inverse explicitly - uses np.linalg.solve instead.
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator
    optimizer : PortfolioOptimizer, optional
        Not used
    ridge : float, optional
        Ridge regularization for numerical stability (default: 1e-5)
    
    References
    ----------
    Markowitz, H. (1952).
    "Portfolio Selection"
    Journal of Finance, 7(1), 77-91.
    
    Clarke, R., De Silva, H., & Thorley, S. (2006).
    "Minimum-Variance Portfolios in the U.S. Equity Market"
    Journal of Portfolio Management, 33(1), 10-24.
    
    Examples
    --------
    >>> gmvp = GlobalMinVarianceBenchmark(strategy)
    >>> weights = gmvp.compute_weights(mu, Sigma)
    >>> assert np.allclose(weights.sum(), 1.0)
    >>> # Verify minimum variance property
    >>> var = weights @ Sigma @ weights
    """
    
    def __init__(self, strategy, optimizer=None, **params):
        """Initialize Global Minimum Variance benchmark."""
        super().__init__("Global Min Variance Benchmark", strategy, optimizer, **params)
    
    def compute_weights(
        self,
        mu: np.ndarray,
        Sigma: np.ndarray,
        **kwargs
    ) -> np.ndarray:
        """
        Compute global minimum variance portfolio weights.
        
        Uses closed-form solution via safe linear solve (never matrix inverse).
        
        Parameters
        ----------
        mu : np.ndarray
            Expected returns (N,) - not used
        Sigma : np.ndarray
            Covariance matrix (N, N)
        
        Returns
        -------
        np.ndarray
            GMVP weights
        """
        n = len(mu)
        ones = np.ones(n)
        
        # Ensure Sigma is PSD
        Sigma_safe = self._safe_cov(Sigma)
        
        # Solve Σ w = 1 instead of w = Σ^(-1) 1
        w_unnorm = self._safe_solve(Sigma_safe, ones)
        
        # Normalize: w = w / (1^T w)
        weights = self._normalize(w_unnorm)
        
        return weights
