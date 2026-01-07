"""
Top-K Equal Weight by Expected Return

Selects the K assets with highest expected returns,
then allocates equal weight among them.

Mathematical Definition:
    1. Rank assets by μ_i
    2. Select top K assets
    3. w_i = 1/K if asset i in top K, else 0

Properties:
- Combines return forecasting with simplicity
- No optimization required
- Can be concentrated (low diversification)
- Sensitive to estimation error in μ

Author: Algo Trading Team
Date: January 2026
"""

import numpy as np
import logging

from src.strategies.benchmarks.base_benchmark import BenchmarkStrategy

logger = logging.getLogger(__name__)


class TopKReturnBenchmark(BenchmarkStrategy):
    """
    Top-K Equal Weight by Expected Return.
    
    Selects K assets with highest expected returns and allocates
    equal weight among them. Ignores risk entirely.
    
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
    >>> topk = TopKReturnBenchmark(strategy, top_k=5)
    >>> weights = topk.compute_weights(mu, Sigma)
    >>> assert np.sum(weights > 0) <= 5
    >>> assert np.allclose(weights.sum(), 1.0)
    """
    
    def __init__(self, strategy, optimizer=None, **params):
        """Initialize Top-K Return benchmark."""
        super().__init__("Top-K Return Benchmark", strategy, optimizer, **params)
        self.top_k = params.get('top_k', 10)
    
    def compute_weights(
        self,
        mu: np.ndarray,
        Sigma: np.ndarray,
        **kwargs
    ) -> np.ndarray:
        """
        Select top K assets by expected return, equal weight.
        
        Parameters
        ----------
        mu : np.ndarray
            Expected returns (N,)
        Sigma : np.ndarray
            Covariance matrix (N, N) - not used
        
        Returns
        -------
        np.ndarray
            Top-K equal weight portfolio
        """
        n = len(mu)
        k = min(self.top_k, n)  # Can't select more than available
        
        # Get indices of top K returns
        top_k_indices = np.argsort(mu)[-k:]
        
        # Allocate equal weight to top K
        weights = np.zeros(n)
        weights[top_k_indices] = 1.0 / k
        
        return weights
