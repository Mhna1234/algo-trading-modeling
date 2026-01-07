"""
Base Benchmark Strategy - Foundation for Mathematically Correct Benchmarks

This module provides the base class for all benchmark strategies that use
only numpy/numpy.linalg operations. All strategies are guaranteed to be:
- Long-only (all weights >= 0)
- Fully invested (weights sum to 1.0)
- Numerically stable
- Deterministic

Author: Algo Trading Team
Date: January 2026
"""

import numpy as np
import pandas as pd
from pandas import Series
from typing import Optional
import logging

from src.strategies.base_strategy_wrapper import BaseStrategyWrapper
from src.portfolio_engine import PortfolioState

logger = logging.getLogger(__name__)


class BenchmarkStrategy(BaseStrategyWrapper):
    """
    Abstract base class for numpy-only benchmark strategies.
    
    Provides helper utilities for:
    - Weight normalization
    - Safe linear algebra operations
    - Covariance matrix regularization
    - Validation of portfolio constraints
    
    All subclasses must implement:
        compute_weights(mu, Sigma, **kwargs) -> np.ndarray
    
    Parameters
    ----------
    name : str
        Strategy name
    strategy : Strategy
        Signal generator (provides assets and data)
    optimizer : PortfolioOptimizer, optional
        Not used by benchmark strategies
    **params
        Additional parameters
    """
    
    def __init__(self, name: str, strategy, optimizer=None, **params):
        """Initialize benchmark strategy."""
        super().__init__(name, strategy, optimizer, **params)
        self.epsilon = params.get('epsilon', 1e-8)  # Regularization parameter
        self.ridge = params.get('ridge', 1e-5)  # Ridge for ill-conditioned matrices
    
    def get_weights(
        self,
        date: pd.Timestamp,
        portfolio_state: PortfolioState
    ) -> Series:
        """
        Generate target weights using only numpy operations.
        
        Parameters
        ----------
        date : pd.Timestamp
            Current rebalancing date
        portfolio_state : PortfolioState
            Portfolio state (not typically used by benchmarks)
        
        Returns
        -------
        pd.Series
            Target weights for risky assets
        """
        # Get expected returns and covariance from strategy
        # Note: Strategy methods use window parameter, not date
        mu = self.strategy.get_expected_returns(window=252)  # 1-year lookback
        Sigma = self.strategy.get_covariance_matrix(window=252)  # 1-year lookback
        
        # Convert to numpy arrays
        mu_np = mu.values if hasattr(mu, 'values') else np.array(mu)
        Sigma_np = Sigma.values if hasattr(Sigma, 'values') else np.array(Sigma)
        assets = mu.index if hasattr(mu, 'index') else self.strategy.assets
        
        # Compute weights using numpy-only operations
        weights_np = self.compute_weights(mu_np, Sigma_np)
        
        # Validate and normalize
        weights_np = self._validate_and_normalize(weights_np)
        
        # Convert back to pandas Series
        return Series(weights_np, index=assets)
    
    def compute_weights(
        self,
        mu: np.ndarray,
        Sigma: np.ndarray,
        **kwargs
    ) -> np.ndarray:
        """
        Compute portfolio weights using only numpy operations.
        
        Must be implemented by subclasses.
        
        Parameters
        ----------
        mu : np.ndarray
            Expected returns (1D array of length N)
        Sigma : np.ndarray
            Covariance matrix (N x N)
        **kwargs
            Additional parameters
        
        Returns
        -------
        np.ndarray
            Portfolio weights (1D array of length N)
        """
        raise NotImplementedError("Subclasses must implement compute_weights")
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def _normalize(self, weights: np.ndarray) -> np.ndarray:
        """
        Normalize weights to sum to 1.0.
        
        Parameters
        ----------
        weights : np.ndarray
            Raw weights
        
        Returns
        -------
        np.ndarray
            Normalized weights summing to 1.0
        """
        weights = np.maximum(weights, 0.0)  # Ensure non-negative
        total = np.sum(weights)
        
        if total < self.epsilon:
            # If all weights are effectively zero, use equal weight
            n = len(weights)
            return np.ones(n) / n
        
        return weights / total
    
    def _validate_and_normalize(self, weights: np.ndarray) -> np.ndarray:
        """
        Validate and normalize weights to satisfy constraints.
        
        Ensures:
        - All weights >= 0 (long-only)
        - Sum of weights = 1.0 (fully invested)
        - No NaN or Inf values
        
        Parameters
        ----------
        weights : np.ndarray
            Raw weights
        
        Returns
        -------
        np.ndarray
            Valid, normalized weights
        """
        # Check for invalid values
        if np.any(np.isnan(weights)) or np.any(np.isinf(weights)):
            logger.warning(f"{self.name}: Invalid weights detected (NaN/Inf), using equal weight")
            return np.ones(len(weights)) / len(weights)
        
        # Normalize
        weights = self._normalize(weights)
        
        # Final validation
        assert np.all(weights >= -self.epsilon), f"{self.name}: Negative weights detected"
        assert np.abs(np.sum(weights) - 1.0) < 1e-6, f"{self.name}: Weights don't sum to 1.0"
        
        return weights
    
    def _safe_solve(
        self,
        A: np.ndarray,
        b: np.ndarray,
        ridge: Optional[float] = None
    ) -> np.ndarray:
        """
        Safely solve Ax = b using ridge regularization if needed.
        
        Never uses matrix inverse explicitly. Adds ridge regularization
        to handle near-singular or ill-conditioned matrices.
        
        Parameters
        ----------
        A : np.ndarray
            Coefficient matrix (N x N)
        b : np.ndarray
            Right-hand side (N,) or (N, k)
        ridge : float, optional
            Ridge regularization parameter (default: self.ridge)
        
        Returns
        -------
        np.ndarray
            Solution x
        """
        if ridge is None:
            ridge = self.ridge
        
        # Add ridge to diagonal for numerical stability
        A_reg = A + ridge * np.eye(len(A))
        
        try:
            # Use solve, never inv
            x = np.linalg.solve(A_reg, b)
        except np.linalg.LinAlgError:
            # If still singular, increase ridge
            logger.warning(f"{self.name}: Singular matrix, using larger ridge")
            A_reg = A + 10 * ridge * np.eye(len(A))
            x = np.linalg.solve(A_reg, b)
        
        return x
    
    def _safe_cov(self, Sigma: np.ndarray) -> np.ndarray:
        """
        Ensure covariance matrix is positive semi-definite.
        
        Adds small ridge to diagonal if needed.
        
        Parameters
        ----------
        Sigma : np.ndarray
            Covariance matrix (N x N)
        
        Returns
        -------
        np.ndarray
            Regularized covariance matrix
        """
        # Check if already PSD
        min_eig = np.min(np.linalg.eigvalsh(Sigma))
        
        if min_eig < 0:
            # Add small ridge to make PSD
            Sigma_safe = Sigma + (abs(min_eig) + self.epsilon) * np.eye(len(Sigma))
            return Sigma_safe
        
        return Sigma
    
    def _project_simplex(self, weights: np.ndarray) -> np.ndarray:
        """
        Project weights onto probability simplex (w >= 0, sum(w) = 1).
        
        Uses efficient sorting-based projection algorithm.
        
        Parameters
        ----------
        weights : np.ndarray
            Arbitrary weights
        
        Returns
        -------
        np.ndarray
            Projected weights on simplex
        """
        n = len(weights)
        
        # Sort in descending order
        u = np.sort(weights)[::-1]
        
        # Find rho (largest j : u[j] + (1 - sum u[0:j+1]) / (j+1) > 0)
        cumsum = np.cumsum(u)
        rho = np.where(u + (1.0 - cumsum) / (np.arange(n) + 1) > 0)[0]
        
        if len(rho) == 0:
            # All negative, return equal weight
            return np.ones(n) / n
        
        rho = rho[-1]
        
        # Compute threshold
        theta = (1.0 - cumsum[rho]) / (rho + 1)
        
        # Project
        w_proj = np.maximum(weights + theta, 0.0)
        
        return w_proj
