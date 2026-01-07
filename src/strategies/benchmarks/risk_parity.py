"""
Risk Parity Portfolio (Equal Risk Contribution)

Allocates weights such that each asset contributes equally to portfolio risk.

Mathematical Definition:
    Risk Contribution: RC_i = w_i * (Σw)_i
    
    Goal: RC_i = RC_j for all i, j
    
    Equivalently: w_i * (Σw)_i / sqrt(w^T Σ w) = 1/N

Properties:
- Equalizes risk contribution across assets
- More diversified than market-cap or equal weight
- Requires iterative solution (no closed form)
- Used by many institutional investors

Algorithm:
    Uses multiplicative update with simplex projection:
    w^(t+1)_i = w^(t)_i * (target_RC / RC^(t)_i)^η
    Then project onto simplex

Author: Algo Trading Team
Date: January 2026
"""

import numpy as np
import logging

from src.strategies.benchmarks.base_benchmark import BenchmarkStrategy

logger = logging.getLogger(__name__)


class RiskParityBenchmark(BenchmarkStrategy):
    """
    Risk Parity Portfolio (Equal Risk Contribution).
    
    Finds portfolio where each asset contributes equally to total risk.
    Uses iterative multiplicative updates.
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator
    optimizer : PortfolioOptimizer, optional
        Not used
    max_iter : int, optional
        Maximum iterations (default: 1000)
    learning_rate : float, optional
        Step size for updates (default: 0.05)
    
    References
    ----------
    Maillard, S., Roncalli, T., & Teiletche, J. (2010).
    "The Properties of Equally Weighted Risk Contribution Portfolios"
    Journal of Portfolio Management, 36(4), 60-70.
    
    Bruder, B., & Roncalli, T. (2012).
    "Managing Risk Exposures using the Risk Budgeting Approach"
    
    Examples
    --------
    >>> rp = RiskParityBenchmark(strategy, max_iter=500)
    >>> weights = rp.compute_weights(mu, Sigma)
    >>> # Verify equal risk contribution
    >>> rc = weights * (Sigma @ weights)
    >>> assert np.allclose(rc, rc.mean(), rtol=0.1)
    """
    
    def __init__(self, strategy, optimizer=None, **params):
        """Initialize Risk Parity benchmark."""
        super().__init__("Risk Parity Benchmark", strategy, optimizer, **params)
        self.max_iter = params.get('max_iter', 1000)
        self.learning_rate = params.get('learning_rate', 0.05)
    
    def compute_weights(
        self,
        mu: np.ndarray,
        Sigma: np.ndarray,
        **kwargs
    ) -> np.ndarray:
        """
        Compute risk parity portfolio weights.
        
        Uses iterative multiplicative updates to equalize risk contributions.
        
        Parameters
        ----------
        mu : np.ndarray
            Expected returns (N,) - not used
        Sigma : np.ndarray
            Covariance matrix (N, N)
        
        Returns
        -------
        np.ndarray
            Risk parity weights
        """
        n = len(mu)
        
        # Initialize with equal weights
        weights = np.ones(n) / n
        
        # Target risk contribution (equal for all assets)
        target_rc = 1.0 / n
        
        # Ensure Sigma is PSD
        Sigma_safe = self._safe_cov(Sigma)
        
        # Iterative updates
        for iteration in range(self.max_iter):
            # Compute portfolio variance
            port_var = weights @ Sigma_safe @ weights
            
            if port_var < self.epsilon:
                # Degenerate case
                logger.warning("Risk Parity: zero portfolio variance, using equal weight")
                return np.ones(n) / n
            
            # Compute marginal risk contributions
            mrc = Sigma_safe @ weights  # Marginal RC
            
            # Compute risk contributions
            rc = weights * mrc
            
            # Compute percentage risk contributions
            prc = rc / np.sum(rc)  # Sum to 1
            
            # Multiplicative update toward target
            # w_i <- w_i * (target / prc_i)^η
            ratio = target_rc / np.maximum(prc, self.epsilon)
            
            # Update with damping
            weights = weights * (ratio ** self.learning_rate)
            
            # Project onto simplex (w >= 0, sum = 1)
            weights = self._project_simplex(weights)
            
            # Check convergence (all risk contributions approximately equal)
            max_deviation = np.max(np.abs(prc - target_rc))
            if max_deviation < 1e-4:
                break
        
        # Final normalization
        weights = self._normalize(weights)
        
        return weights
