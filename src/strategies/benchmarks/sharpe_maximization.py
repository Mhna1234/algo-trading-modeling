"""
Sharpe Maximization Portfolio - Mean-Variance Optimization

Maximizes the Sharpe ratio using analytical solution for unconstrained case.
Classic Markowitz mean-variance optimization.

Mathematical Definition (unconstrained):
    max: (μ^T w - r_f) / sqrt(w^T Σ w)

    Analytical solution:
    w* ∝ Σ^(-1) (μ - r_f·1)

Properties:
- Maximizes risk-adjusted returns
- Requires return forecasts (subject to estimation error)
- Unconstrained (can have concentrated positions)
- Efficient frontier portfolio

Note: This is a numpy-only implementation without cvxpy. It uses the
analytical solution for the unconstrained case. For constrained optimization
(position limits, etc.), use the full cvxpy version in benchmark_strategies.py.

Author: Algo Trading Team
Date: January 2026
"""

import numpy as np
import logging

from src.strategies.benchmarks.base_benchmark import BenchmarkStrategy

logger = logging.getLogger(__name__)


class SharpeMaximizationBenchmark(BenchmarkStrategy):
    """
    Sharpe Maximization Portfolio (Unconstrained).

    Maximizes Sharpe ratio using analytical solution:
        w* ∝ Σ^(-1) (μ - r_f·1)

    Note: This is unconstrained optimization. Positions can be concentrated.
    For production use with position limits, use the cvxpy version.

    Parameters
    ----------
    strategy : Strategy
        Signal generator
    optimizer : PortfolioOptimizer, optional
        Not used
    risk_free_rate : float, optional
        Annual risk-free rate (default: 0.02 = 2%)
    min_weight : float, optional
        Minimum weight (applied after optimization) (default: 0.0)
    max_weight : float, optional
        Maximum weight (applied after optimization) (default: 1.0)

    References
    ----------
    Markowitz, H. (1952).
    "Portfolio Selection"
    Journal of Finance, 7(1), 77-91.

    Sharpe, W. F. (1966).
    "Mutual Fund Performance"
    Journal of Business, 39(1), 119-138.

    Examples
    --------
    >>> sm = SharpeMaximizationBenchmark(strategy, risk_free_rate=0.02)
    >>> weights = sm.compute_weights(mu, Sigma)
    """

    def __init__(self, strategy, optimizer=None, **params):
        """Initialize Sharpe Maximization benchmark."""
        super().__init__("Sharpe Maximization Benchmark", strategy, optimizer, **params)
        self.risk_free_rate = params.get('risk_free_rate', 0.02)
        self.min_weight = params.get('min_weight', 0.0)
        self.max_weight = params.get('max_weight', 1.0)

    def compute_weights(
        self,
        mu: np.ndarray,
        Sigma: np.ndarray,
        **kwargs
    ) -> np.ndarray:
        """
        Compute Sharpe-maximizing portfolio weights.

        Uses analytical solution for unconstrained case:
            w* ∝ Σ^(-1) (μ - r_f·1)

        Parameters
        ----------
        mu : np.ndarray
            Expected returns (annualized)
        Sigma : np.ndarray
            Covariance matrix (annualized)

        Returns
        -------
        np.ndarray
            Sharpe-maximizing weights
        """
        n = len(mu)

        # Convert to daily risk-free rate (assuming 252 trading days)
        rf_daily = self.risk_free_rate / 252

        # Excess returns
        excess_returns = mu - rf_daily

        # Check if all excess returns are negative or zero
        if np.all(excess_returns <= 0):
            logger.warning("All excess returns <= 0, using global minimum variance")
            # Fallback to GMVP
            ones = np.ones(n)
            Sigma_safe = self._safe_cov(Sigma)
            w_unnorm = self._safe_solve(Sigma_safe, ones)
            return self._normalize(w_unnorm)

        # Ensure Sigma is PSD
        Sigma_safe = self._safe_cov(Sigma)

        # Analytical solution: w* ∝ Σ^(-1) (μ - r_f·1)
        try:
            w_unnorm = self._safe_solve(Sigma_safe, excess_returns)
        except np.linalg.LinAlgError:
            logger.warning("Singular covariance matrix, using equal weight")
            return np.ones(n) / n

        # Check for negative weights (short positions)
        if np.any(w_unnorm < 0):
            logger.warning("Unconstrained optimization produced short positions, setting to zero")
            # Set negative weights to zero (long-only constraint)
            w_unnorm = np.maximum(w_unnorm, 0.0)

        # Normalize
        weights = self._normalize(w_unnorm)

        # Apply weight constraints (soft constraints via clipping)
        if self.max_weight < 1.0 or self.min_weight > 0.0:
            weights = np.clip(weights, self.min_weight, self.max_weight)
            # Re-normalize after clipping
            weights = self._normalize(weights)

        return weights
