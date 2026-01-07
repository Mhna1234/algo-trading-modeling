"""
Most Diversified Portfolio

Maximizes the diversification ratio:
    DR(w) = (w^T σ) / sqrt(w^T Σ w)

where σ is the vector of individual asset volatilities.

Mathematical Definition:
    maximize: DR(w) = (Σ w_i σ_i) / sqrt(w^T Σ w)
    subject to: w >= 0, w^T 1 = 1

Properties:
- Maximizes weighted average volatility relative to portfolio volatility
- Exploits diversification benefits from low correlations
- No return forecasts needed
- Requires iterative optimization (no closed form)

Algorithm:
    Projected gradient ascent on the simplex with normalized gradient.

Author: Algo Trading Team
Date: January 2026
"""

import numpy as np
import logging

from src.strategies.benchmarks.base_benchmark import BenchmarkStrategy

logger = logging.getLogger(__name__)


class MostDiversifiedBenchmark(BenchmarkStrategy):
    """
    Most Diversified Portfolio (MDP).
    
    Maximizes diversification ratio using projected gradient ascent.
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator
    optimizer : PortfolioOptimizer, optional
        Not used
    max_iter : int, optional
        Maximum iterations (default: 1000)
    learning_rate : float, optional
        Step size (default: 0.01)
    
    References
    ----------
    Choueifaty, Y., & Coignard, Y. (2008).
    "Toward Maximum Diversification"
    Journal of Portfolio Management, 35(1), 40-51.
    
    Choueifaty, Y., Froidure, T., & Reynier, J. (2013).
    "Properties of the Most Diversified Portfolio"
    Journal of Investment Strategies, 2(2), 49-70.
    
    Examples
    --------
    >>> mdp = MostDiversifiedBenchmark(strategy, max_iter=500)
    >>> weights = mdp.compute_weights(mu, Sigma)
    >>> # Verify diversification ratio
    >>> sigma = np.sqrt(np.diag(Sigma))
    >>> dr = (weights @ sigma) / np.sqrt(weights @ Sigma @ weights)
    """
    
    def __init__(self, strategy, optimizer=None, **params):
        """Initialize Most Diversified Portfolio benchmark."""
        super().__init__("Most Diversified Benchmark", strategy, optimizer, **params)
        self.max_iter = params.get('max_iter', 1000)
        self.learning_rate = params.get('learning_rate', 0.01)
    
    def compute_weights(
        self,
        mu: np.ndarray,
        Sigma: np.ndarray,
        **kwargs
    ) -> np.ndarray:
        """
        Compute most diversified portfolio weights.
        
        Uses projected gradient ascent to maximize:
            DR(w) = (w^T σ) / sqrt(w^T Σ w)
        
        Parameters
        ----------
        mu : np.ndarray
            Expected returns (N,) - not used
        Sigma : np.ndarray
            Covariance matrix (N, N)
        
        Returns
        -------
        np.ndarray
            Most diversified portfolio weights
        """
        n = len(mu)
        
        # Extract volatilities
        volatilities = np.sqrt(np.maximum(np.diag(Sigma), self.epsilon))
        
        # Ensure Sigma is PSD
        Sigma_safe = self._safe_cov(Sigma)
        
        # Initialize with equal weights
        weights = np.ones(n) / n
        
        # Gradient ascent
        for iteration in range(self.max_iter):
            # Compute current diversification ratio
            numerator = weights @ volatilities
            port_var = weights @ Sigma_safe @ weights
            port_vol = np.sqrt(port_var)
            
            if port_vol < self.epsilon:
                logger.warning("MDP: zero portfolio volatility, using equal weight")
                return np.ones(n) / n
            
            # Compute gradient of DR with respect to w
            # d/dw [w^T σ / sqrt(w^T Σ w)]
            # = σ / sqrt(w^T Σ w) - (w^T σ) * (Σ w) / (w^T Σ w)^(3/2)
            
            grad_numerator = volatilities / port_vol
            grad_denominator = (numerator / (port_var ** 1.5)) * (Sigma_safe @ weights)
            
            gradient = grad_numerator - grad_denominator
            
            # Normalize gradient (for stability)
            grad_norm = np.linalg.norm(gradient)
            if grad_norm > self.epsilon:
                gradient = gradient / grad_norm
            
            # Gradient ascent step
            weights_new = weights + self.learning_rate * gradient
            
            # Project onto simplex
            weights = self._project_simplex(weights_new)
            
            # Check convergence (gradient small)
            if grad_norm < 1e-5:
                break
        
        # Final normalization
        weights = self._normalize(weights)
        
        return weights
