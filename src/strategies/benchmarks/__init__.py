"""
Benchmark Portfolio Strategies
================================

Mathematically correct benchmark strategies implemented using only numpy/numpy.linalg.

All strategies:
- Are long-only (w >= 0)
- Are fully invested (sum(w) = 1)
- Use deterministic algorithms
- Are numerically stable
- Compatible with BaseStrategyWrapper

Strategy Categories:

1. Heuristic Benchmarks
   - EqualWeightBenchmark: 1/N allocation
   - TopKReturnBenchmark: Top K by expected return
   - TopKSharpeBenchmark: Top K by Sharpe proxy

2. Risk-Based Benchmarks
   - InverseVolatilityBenchmark: w ∝ 1/σ
   - InverseVarianceBenchmark: w ∝ 1/σ²
   - GlobalMinVarianceBenchmark: Minimum variance portfolio
   - MaxDecorrelationBenchmark: GMVP on correlation matrix

3. Iterative Benchmarks
   - RiskParityBenchmark: Equal risk contribution
   - MostDiversifiedBenchmark: Maximum diversification ratio

Usage:
    from src.strategies.benchmarks import EqualWeightBenchmark
    
    strategy = EqualWeightBenchmark(signal_generator)
    weights = strategy.get_weights(date, portfolio_state)

Author: Algo Trading Team
Date: January 2026
"""

from src.strategies.benchmarks.base_benchmark import BenchmarkStrategy

# Heuristic Benchmarks
from src.strategies.benchmarks.equal_weight import EqualWeightBenchmark
from src.strategies.benchmarks.top_k_return import TopKReturnBenchmark
from src.strategies.benchmarks.top_k_sharpe import TopKSharpeBenchmark

# Risk-Based Benchmarks
from src.strategies.benchmarks.inverse_volatility import InverseVolatilityBenchmark
from src.strategies.benchmarks.inverse_variance import InverseVarianceBenchmark
from src.strategies.benchmarks.global_min_variance import GlobalMinVarianceBenchmark
from src.strategies.benchmarks.max_decorrelation import MaxDecorrelationBenchmark

# Iterative Benchmarks
from src.strategies.benchmarks.risk_parity import RiskParityBenchmark
from src.strategies.benchmarks.most_diversified import MostDiversifiedBenchmark


__all__ = [
    # Base class
    'BenchmarkStrategy',
    
    # Heuristic
    'EqualWeightBenchmark',
    'TopKReturnBenchmark',
    'TopKSharpeBenchmark',
    
    # Risk-based
    'InverseVolatilityBenchmark',
    'InverseVarianceBenchmark',
    'GlobalMinVarianceBenchmark',
    'MaxDecorrelationBenchmark',
    
    # Iterative
    'RiskParityBenchmark',
    'MostDiversifiedBenchmark',
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
    """
    return {
        # Heuristic
        'equal_weight': EqualWeightBenchmark,
        'top_k_return': TopKReturnBenchmark,
        'top_k_sharpe': TopKSharpeBenchmark,
        
        # Risk-based
        'inverse_volatility': InverseVolatilityBenchmark,
        'inverse_variance': InverseVarianceBenchmark,
        'global_min_variance': GlobalMinVarianceBenchmark,
        'max_decorrelation': MaxDecorrelationBenchmark,
        
        # Iterative
        'risk_parity': RiskParityBenchmark,
        'most_diversified': MostDiversifiedBenchmark,
    }
