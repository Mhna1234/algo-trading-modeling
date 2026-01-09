"""
CVaR Minimization Portfolio - Downside Risk Optimization

Minimizes Conditional Value at Risk (Expected Shortfall) using historical
simulation method. This is a numpy-only approximation without cvxpy.

Mathematical Definition:
    CVaR_α(w) = E[Loss | Loss > VaR_α(w)]

    For historical simulation:
    1. Calculate portfolio returns for each scenario: r_i = w^T R_i
    2. Find VaR_α (α-quantile of losses)
    3. CVaR = average of losses beyond VaR

Properties:
- Focuses on tail risk (downside protection)
- More conservative than variance minimization
- Uses historical simulation (no distributional assumptions)
- Coherent risk measure

Note: This is a numpy-only heuristic implementation. For exact CVaR
optimization, use the cvxpy version in benchmark_strategies.py.

Algorithm:
- Uses iterative search over weight simplex
- Evaluates CVaR for candidate portfolios
- Selects portfolio with minimum CVaR

Author: Algo Trading Team
Date: January 2026
"""

import numpy as np
import logging

from src.strategies.benchmarks.base_benchmark import BenchmarkStrategy

logger = logging.getLogger(__name__)


class CVaRMinimizationBenchmark(BenchmarkStrategy):
    """
    CVaR Minimization Portfolio (Historical Simulation).

    Minimizes Conditional Value at Risk using historical returns.
    This is an approximate method without cvxpy optimization.

    Uses iterative search heuristic:
    1. Start with global minimum variance portfolio
    2. Perturb weights and evaluate CVaR
    3. Keep improvements
    4. Repeat until convergence

    Parameters
    ----------
    strategy : Strategy
        Signal generator
    optimizer : PortfolioOptimizer, optional
        Not used
    alpha : float, optional
        Confidence level for CVaR (default: 0.05 = 95% CVaR)
    max_iter : int, optional
        Maximum iterations for optimization (default: 100)
    n_scenarios : int, optional
        Number of historical scenarios to use (default: 252 = 1 year)

    References
    ----------
    Rockafellar, R. T., & Uryasev, S. (2000).
    "Optimization of Conditional Value-at-Risk"
    Journal of Risk, 2, 21-42.

    Krokhmal, P., Palmquist, J., & Uryasev, S. (2002).
    "Portfolio Optimization with Conditional Value-at-Risk Objective and Constraints"
    Journal of Risk, 4(2), 43-68.

    Examples
    --------
    >>> cvar = CVaRMinimizationBenchmark(strategy, alpha=0.05)
    >>> weights = cvar.compute_weights(mu, Sigma)
    """

    def __init__(self, strategy, optimizer=None, **params):
        """Initialize CVaR Minimization benchmark."""
        super().__init__("CVaR Minimization Benchmark", strategy, optimizer, **params)
        self.alpha = params.get('alpha', 0.05)
        self.max_iter = params.get('max_iter', 100)
        self.n_scenarios = params.get('n_scenarios', 252)
        self.temperature = params.get('temperature', 0.1)  # For simulated annealing

    def _calculate_cvar(
        self,
        weights: np.ndarray,
        returns_scenarios: np.ndarray
    ) -> float:
        """
        Calculate CVaR for given weights and return scenarios.

        Parameters
        ----------
        weights : np.ndarray
            Portfolio weights (N,)
        returns_scenarios : np.ndarray
            Historical returns (T, N) where T = scenarios, N = assets

        Returns
        -------
        float
            CVaR value (higher = worse)
        """
        # Calculate portfolio returns for each scenario
        portfolio_returns = returns_scenarios @ weights

        # Calculate losses (negative returns)
        losses = -portfolio_returns

        # Find VaR (α-quantile of losses)
        var = np.percentile(losses, 100 * (1 - self.alpha))

        # Calculate CVaR (average of losses beyond VaR)
        cvar = np.mean(losses[losses >= var])

        return cvar

    def compute_weights(
        self,
        mu: np.ndarray,
        Sigma: np.ndarray,
        **kwargs
    ) -> np.ndarray:
        """
        Compute CVaR-minimizing portfolio weights.

        Uses heuristic iterative search with historical simulation.

        Parameters
        ----------
        mu : np.ndarray
            Expected returns (N,) - not directly used
        Sigma : np.ndarray
            Covariance matrix (N, N) - used for initialization

        Returns
        -------
        np.ndarray
            CVaR-minimizing weights
        """
        n = len(mu)

        # Generate historical return scenarios from covariance matrix
        # Use multivariate normal as proxy if historical data not available
        try:
            # Try to get actual historical returns from strategy
            if hasattr(self.strategy, 'returns') and self.strategy.returns is not None:
                # Use actual historical returns (last n_scenarios periods)
                returns_scenarios = self.strategy.returns.iloc[-self.n_scenarios:].values
            else:
                # Generate synthetic scenarios from distribution
                returns_scenarios = np.random.multivariate_normal(
                    mu, Sigma, size=self.n_scenarios
                )
        except Exception as e:
            logger.warning(f"Could not get historical returns, using synthetic: {e}")
            # Ensure Sigma is PSD for random generation
            Sigma_safe = self._safe_cov(Sigma)
            returns_scenarios = np.random.multivariate_normal(
                mu, Sigma_safe, size=self.n_scenarios
            )

        # Initialize with global minimum variance portfolio
        ones = np.ones(n)
        Sigma_safe = self._safe_cov(Sigma)
        w_gmvp = self._safe_solve(Sigma_safe, ones)
        current_weights = self._normalize(w_gmvp)
        current_cvar = self._calculate_cvar(current_weights, returns_scenarios)

        # Iterative improvement using random perturbations
        best_weights = current_weights.copy()
        best_cvar = current_cvar

        for iteration in range(self.max_iter):
            # Generate candidate by perturbing current weights
            perturbation = np.random.randn(n) * self.temperature
            candidate_weights = current_weights + perturbation

            # Project onto simplex (w >= 0, sum = 1)
            candidate_weights = self._project_simplex(candidate_weights)

            # Evaluate CVaR
            candidate_cvar = self._calculate_cvar(candidate_weights, returns_scenarios)

            # Accept if better
            if candidate_cvar < best_cvar:
                best_weights = candidate_weights.copy()
                best_cvar = candidate_cvar
                current_weights = candidate_weights.copy()
            elif iteration < self.max_iter // 2:
                # Early iterations: occasionally accept worse solutions (exploration)
                acceptance_prob = np.exp(-(candidate_cvar - best_cvar) / self.temperature)
                if np.random.rand() < acceptance_prob:
                    current_weights = candidate_weights.copy()

            # Reduce temperature (simulated annealing)
            if iteration % 10 == 0:
                self.temperature *= 0.95

        return best_weights
