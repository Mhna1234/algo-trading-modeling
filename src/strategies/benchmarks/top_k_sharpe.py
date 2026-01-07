"""
Top-K Equal Weight by Sharpe Proxy

Selects the K assets with highest Sharpe ratio proxy,
then allocates equal weight among them.

Mathematical Definition:
    1. Compute Sharpe proxy: S_i = μ_i / sqrt(Σ_ii)
    2. Select top K assets by S_i
    3. w_i = 1/K if asset i in top K, else 0

Properties:
- Risk-adjusted selection
- Simple equal weighting
- Better than return-only selection
- Ignores correlations in selection

Author: Algo Trading Team
Date: January 2026
"""

import numpy as np
import logging

from src.strategies.benchmarks.base_benchmark import BenchmarkStrategy

logger = logging.getLogger(__name__)


class TopKSharpeBenchmark(BenchmarkStrategy):
    """
    Top-K Equal Weight by Sharpe Proxy.
    
    Selects K assets with highest Sharpe ratio proxy (μ/σ)
    and allocates equal weight among them.
    
    Parameters
    ----------
    strategy : Strategy
        Signal generator
    optimizer : PortfolioOptimizer, optional
        Not used
    top_k : int, optional
        Number of assets to select (default: 10)
    
    Examples
    --------
    >>> topk = TopKSharpeBenchmark(strategy, top_k=5)
    >>> weights = topk.compute_weights(mu, Sigma)
    >>> assert np.sum(weights > 0) <= 5
    >>> assert np.allclose(weights.sum(), 1.0)
    """
    
    def __init__(self, strategy, optimizer=None, **params):
        """Initialize Top-K Sharpe benchmark."""
        super().__init__("Top-K Sharpe Benchmark", strategy, optimizer, **params)
        self.top_k = params.get('top_k', 10)
    
    def compute_weights(
        self,
        mu: np.ndarray,
        Sigma: np.ndarray,
        **kwargs
    ) -> np.ndarray:
        """
        Select top K assets by Sharpe proxy, equal weight.
        
        Parameters
        ----------
        mu : np.ndarray
            Expected returns (N,)
        Sigma : np.ndarray
            Covariance matrix (N, N)
        
        Returns
        -------
        np.ndarray
            Top-K Sharpe equal weight portfolio
        """
        n = len(mu)
        k = min(self.top_k, n)
        
        # Compute volatilities
        volatilities = np.sqrt(np.maximum(np.diag(Sigma), self.epsilon))
        
        # Compute Sharpe proxy
        sharpe_proxy = mu / volatilities
        
        # Get indices of top K Sharpe ratios
        top_k_indices = np.argsort(sharpe_proxy)[-k:]
        
        # Allocate equal weight to top K
        weights = np.zeros(n)
        weights[top_k_indices] = 1.0 / k
        
        return weights
