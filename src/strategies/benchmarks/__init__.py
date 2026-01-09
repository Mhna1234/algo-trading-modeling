"""
Benchmark Portfolio Strategies - Complete Lambda-Compatible Suite
==================================================================

Complete set of 15 benchmark strategies implemented using only numpy/numpy.linalg.
All strategies are AWS Lambda compatible (no scipy/cvxpy dependencies).

All strategies:
- Are long-only (w >= 0)
- Are fully invested (sum(w) = 1)
- Use deterministic algorithms
- Are numerically stable
- Compatible with BaseStrategyWrapper
- AWS Lambda compatible (~150MB deployment)

Strategy Categories:

1. Passive Benchmarks (1)
   - BuyAndHoldBenchmark: Passive investment, no rebalancing

2. Heuristic Benchmarks (5)
   - EqualWeightBenchmark: 1/N allocation
   - TopKReturnBenchmark: Top K by expected return
   - TopKSharpeBenchmark: Top K by Sharpe proxy
   - QuintileFactorBenchmark: Momentum quintile selection
   - QuintileLowVolatilityBenchmark: Low volatility quintile

3. Risk-Based Benchmarks (6)
   - InverseVolatilityBenchmark: w ∝ 1/σ
   - InverseVarianceBenchmark: w ∝ 1/σ²
   - GlobalMinVarianceBenchmark: Minimum variance portfolio
   - MaxDecorrelationBenchmark: GMVP on correlation matrix
   - RiskParityBenchmark: Equal risk contribution
   - MostDiversifiedBenchmark: Maximum diversification ratio

4. Factor/Signal Benchmarks (1)
   - MeanReversionBenchmark: Contrarian strategy

5. Optimization Benchmarks (2)
   - SharpeMaximizationBenchmark: Risk-adjusted return (unconstrained)
   - CVaRMinimizationBenchmark: Downside risk minimization (heuristic)

Usage:
    from src.strategies.benchmarks import EqualWeightBenchmark

    strategy = EqualWeightBenchmark(signal_generator)
    weights = strategy.get_weights(date, portfolio_state)

Author: Algo Trading Team
Date: January 2026
"""

from src.strategies.benchmarks.base_benchmark import BenchmarkStrategy

# Passive Benchmarks
from src.strategies.benchmarks.buy_and_hold import BuyAndHoldBenchmark

# Heuristic Benchmarks
from src.strategies.benchmarks.equal_weight import EqualWeightBenchmark
from src.strategies.benchmarks.top_k_return import TopKReturnBenchmark
from src.strategies.benchmarks.top_k_sharpe import TopKSharpeBenchmark
from src.strategies.benchmarks.quintile_factor import QuintileFactorBenchmark
from src.strategies.benchmarks.quintile_low_volatility import QuintileLowVolatilityBenchmark

# Risk-Based Benchmarks
from src.strategies.benchmarks.inverse_volatility import InverseVolatilityBenchmark
from src.strategies.benchmarks.inverse_variance import InverseVarianceBenchmark
from src.strategies.benchmarks.global_min_variance import GlobalMinVarianceBenchmark
from src.strategies.benchmarks.max_decorrelation import MaxDecorrelationBenchmark
from src.strategies.benchmarks.risk_parity import RiskParityBenchmark
from src.strategies.benchmarks.most_diversified import MostDiversifiedBenchmark

# Factor/Signal Benchmarks
from src.strategies.benchmarks.mean_reversion import MeanReversionBenchmark

# Optimization Benchmarks
from src.strategies.benchmarks.sharpe_maximization import SharpeMaximizationBenchmark
from src.strategies.benchmarks.cvar_minimization import CVaRMinimizationBenchmark


__all__ = [
    # Base class
    'BenchmarkStrategy',

    # Passive
    'BuyAndHoldBenchmark',

    # Heuristic
    'EqualWeightBenchmark',
    'TopKReturnBenchmark',
    'TopKSharpeBenchmark',
    'QuintileFactorBenchmark',
    'QuintileLowVolatilityBenchmark',

    # Risk-based
    'InverseVolatilityBenchmark',
    'InverseVarianceBenchmark',
    'GlobalMinVarianceBenchmark',
    'MaxDecorrelationBenchmark',
    'RiskParityBenchmark',
    'MostDiversifiedBenchmark',

    # Factor/Signal
    'MeanReversionBenchmark',

    # Optimization
    'SharpeMaximizationBenchmark',
    'CVaRMinimizationBenchmark',
]


def list_benchmarks():
    """
    Get dictionary of all available benchmark strategies.

    Returns
    -------
    dict
        Mapping of strategy names to classes

    Examples
    --------
    >>> benchmarks = list_benchmarks()
    >>> print(benchmarks.keys())
    >>> # dict_keys(['buy_and_hold', 'equal_weight', ...])
    """
    return {
        # Passive
        'buy_and_hold': BuyAndHoldBenchmark,

        # Heuristic
        'equal_weight': EqualWeightBenchmark,
        'top_k_return': TopKReturnBenchmark,
        'top_k_sharpe': TopKSharpeBenchmark,
        'quintile_factor': QuintileFactorBenchmark,
        'quintile_low_volatility': QuintileLowVolatilityBenchmark,

        # Risk-based
        'inverse_volatility': InverseVolatilityBenchmark,
        'inverse_variance': InverseVarianceBenchmark,
        'global_min_variance': GlobalMinVarianceBenchmark,
        'max_decorrelation': MaxDecorrelationBenchmark,
        'risk_parity': RiskParityBenchmark,
        'most_diversified': MostDiversifiedBenchmark,

        # Factor/Signal
        'mean_reversion': MeanReversionBenchmark,

        # Optimization
        'sharpe_maximization': SharpeMaximizationBenchmark,
        'cvar_minimization': CVaRMinimizationBenchmark,
    }
