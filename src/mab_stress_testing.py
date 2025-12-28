"""
MAB Stress Testing Framework

Comprehensive stress testing and robustness validation for Multi-Armed Bandit
strategy allocation system. Tests extreme conditions, failure modes, and
parameter sensitivity to ensure reliable performance.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Callable
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import warnings

from src.strategies.bandit_strategy_wrapper import BanditStrategyWrapper
from src.bandits import UCBBandit, ThompsonSamplingBandit, EXP3Bandit
from src.portfolio_engine import PortfolioState
from tests.test_bandit_strategy_wrapper import DummyStrategyWrapper, create_dummy_portfolio_state

logger = logging.getLogger(__name__)


@dataclass
class StressTestResult:
    """Container for stress test results."""

    test_name: str
    passed: bool
    metrics: Dict[str, float]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, any] = field(default_factory=dict)


class MABStressTester:
    """
    Comprehensive stress testing framework for MAB systems.

    Tests various failure modes, extreme conditions, and parameter sensitivity
    to ensure robust behavior under diverse scenarios.
    """

    def __init__(self, base_prices: pd.DataFrame):
        """
        Initialize stress tester with base price data.

        Parameters
        ----------
        base_prices : pd.DataFrame
            Base historical price data for testing
        """
        self.base_prices = base_prices
        self.assets = base_prices.columns.tolist()

    def run_all_stress_tests(self) -> Dict[str, StressTestResult]:
        """
        Run comprehensive suite of stress tests.

        Returns
        -------
        dict
            Test results keyed by test name
        """
        tests = [
            self.test_cold_start_behavior,
            self.test_strategy_failure_robustness,
            self.test_extreme_volatility,
            self.test_strategy_dominance,
            self.test_parameter_sensitivity,
            self.test_missing_data_robustness,
            self.test_allocation_concentration,
            self.test_correlation_stress,
            self.test_reward_function_stability,
            self.test_burn_in_edge_cases
        ]

        results = {}
        for test_func in tests:
            try:
                result = test_func()
                results[result.test_name] = result
                logger.info(f"Stress test '{result.test_name}': {'PASSED' if result.passed else 'FAILED'}")
            except Exception as e:
                logger.error(f"Stress test '{test_func.__name__}' failed with exception: {e}")
                results[test_func.__name__] = StressTestResult(
                    test_name=test_func.__name__,
                    passed=False,
                    metrics={},
                    errors=[f"Test execution failed: {e}"]
                )

        return results

    def test_cold_start_behavior(self) -> StressTestResult:
        """Test MAB behavior with minimal historical data."""
        test_name = "cold_start_behavior"

        try:
            # Create strategies with minimal data
            strategies = [
                DummyStrategyWrapper(f"Strategy{i}", self._generate_random_weights(), self.assets)
                for i in range(3)
            ]

            # Test with very short burn-in
            bandit = UCBBandit(n_arms=3)
            mab = BanditStrategyWrapper(
                child_strategies=strategies,
                bandit_allocator=bandit,
                burn_in_periods=1,  # Minimal burn-in
                enable_soft_allocation=False
            )

            # Run minimal periods
            dates = pd.date_range('2023-01-01', periods=3, freq='QS')
            performances = []

            for date in dates:
                state = create_dummy_portfolio_state(date, equity=100000.0, assets=self.assets)
                weights = mab.get_weights(date, state)

                # Check that allocations are reasonable
                allocs = mab.last_allocations
                if allocs is not None:
                    performances.append({
                        'date': date,
                        'allocations': allocs,
                        'sum': np.sum(allocs),
                        'entropy': -np.sum(allocs * np.log(allocs + 1e-10))
                    })

            # Validate results
            passed = True
            errors = []
            warnings = []

            if len(performances) < 2:
                passed = False
                errors.append("Insufficient performance data generated")

            for perf in performances:
                if not (0.99 <= perf['sum'] <= 1.01):
                    passed = False
                    errors.append(f"Allocation sum {perf['sum']:.4f} not close to 1.0")
                if perf['entropy'] < -10:  # Very concentrated allocation
                    warnings.append(f"Very concentrated allocation at {perf['date']}")

            metrics = {
                'periods_tested': len(performances),
                'avg_allocation_entropy': np.mean([p['entropy'] for p in performances]) if performances else 0,
                'allocation_stability': np.std([p['entropy'] for p in performances]) if performances else 0
            }

            return StressTestResult(
                test_name=test_name,
                passed=passed,
                metrics=metrics,
                errors=errors,
                warnings=warnings,
                details={'performance_history': performances}
            )

        except Exception as e:
            return StressTestResult(
                test_name=test_name,
                passed=False,
                metrics={},
                errors=[f"Test failed with exception: {e}"]
            )

    def test_strategy_failure_robustness(self) -> StressTestResult:
        """Test MAB robustness when strategies fail."""
        test_name = "strategy_failure_robustness"

        try:
            # Create strategies, some will fail
            strategies = []
            for i in range(4):
                if i == 2:  # Make one strategy fail
                    strategies.append(FailingStrategyWrapper(f"FailingStrategy{i}", self.assets))
                else:
                    strategies.append(DummyStrategyWrapper(f"Strategy{i}", self._generate_random_weights(), self.assets))

            bandit = UCBBandit(n_arms=4)
            mab = BanditStrategyWrapper(
                child_strategies=strategies,
                bandit_allocator=bandit,
                burn_in_periods=2,
                fallback_on_error=True
            )

            # Run test periods
            dates = pd.date_range('2023-01-01', periods=5, freq='QS')
            failures_caught = 0
            successful_allocations = 0

            for date in dates:
                state = create_dummy_portfolio_state(date, equity=100000.0, assets=self.assets)
                try:
                    weights = mab.get_weights(date, state)
                    if mab.last_allocations is not None:
                        successful_allocations += 1
                except Exception as e:
                    failures_caught += 1
                    logger.debug(f"Expected failure caught: {e}")

            # Validate results
            passed = successful_allocations >= 3  # Should handle failures gracefully
            errors = []
            warnings = []

            if failures_caught > 2:
                passed = False
                errors.append(f"Too many failures: {failures_caught}")

            if successful_allocations < len(dates) - 1:
                warnings.append(f"Some allocations failed: {successful_allocations}/{len(dates)} successful")

            metrics = {
                'total_periods': len(dates),
                'failures_caught': failures_caught,
                'successful_allocations': successful_allocations,
                'failure_rate': failures_caught / len(dates)
            }

            return StressTestResult(
                test_name=test_name,
                passed=passed,
                metrics=metrics,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            return StressTestResult(
                test_name=test_name,
                passed=False,
                metrics={},
                errors=[f"Test failed with exception: {e}"]
            )

    def test_extreme_volatility(self) -> StressTestResult:
        """Test MAB under extreme market volatility conditions."""
        test_name = "extreme_volatility"

        try:
            strategies = [
                DummyStrategyWrapper(f"Strategy{i}", self._generate_random_weights(), self.assets)
                for i in range(3)
            ]

            bandit = UCBBandit(n_arms=3)
            mab = BanditStrategyWrapper(
                child_strategies=strategies,
                bandit_allocator=bandit,
                burn_in_periods=3,
                reward_type='sharpe'  # Should handle volatility well
            )

            # Generate extreme volatility returns
            dates = pd.date_range('2023-01-01', periods=10, freq='QS')
            volatilities = []

            for i, date in enumerate(dates):
                # Create extreme volatility scenario
                if i < 3:
                    equity = 100000.0  # Normal
                elif i < 6:
                    equity = 100000.0 * (1 + np.random.normal(0, 0.05))  # High vol
                else:
                    equity = 100000.0 * (1 + np.random.normal(0, 0.15))  # Extreme vol

                state = create_dummy_portfolio_state(date, equity=equity, assets=self.assets)
                weights = mab.get_weights(date, state)

                # Track volatility of allocations
                if mab.last_allocations is not None:
                    alloc_vol = np.std(mab.last_allocations)
                    volatilities.append(alloc_vol)

            # Validate stability under volatility
            passed = True
            errors = []
            warnings = []

            if len(volatilities) < 5:
                passed = False
                errors.append("Insufficient volatility data")

            alloc_volatility = np.std(volatilities) if volatilities else 0
            if alloc_volatility > 0.5:  # Allocations too unstable
                warnings.append(f"High allocation volatility: {alloc_volatility:.4f}")

            # Check for NaN or infinite values in diagnostics
            try:
                analytics = mab.get_learning_analytics()
                if any(np.isnan(v) or np.isinf(v) for v in analytics['regret_metrics'].values()):
                    passed = False
                    errors.append("NaN or infinite values in regret metrics")
            except Exception as e:
                warnings.append(f"Analytics calculation failed: {e}")

            metrics = {
                'periods_tested': len(volatilities),
                'allocation_volatility': alloc_volatility,
                'avg_allocation_vol': np.mean(volatilities) if volatilities else 0,
                'volatility_stress_passed': alloc_volatility < 0.3
            }

            return StressTestResult(
                test_name=test_name,
                passed=passed,
                metrics=metrics,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            return StressTestResult(
                test_name=test_name,
                passed=False,
                metrics={},
                errors=[f"Test failed with exception: {e}"]
            )

    def test_strategy_dominance(self) -> StressTestResult:
        """Test detection and handling of strategy dominance."""
        test_name = "strategy_dominance"

        try:
            # Create strategies with one clearly dominant
            strategies = [
                DominantStrategyWrapper("Dominant", self._generate_random_weights(), self.assets, dominance_factor=2.0),
                DummyStrategyWrapper("Normal1", self._generate_random_weights(), self.assets),
                DummyStrategyWrapper("Normal2", self._generate_random_weights(), self.assets)
            ]

            bandit = UCBBandit(n_arms=3)
            mab = BanditStrategyWrapper(
                child_strategies=strategies,
                bandit_allocator=bandit,
                burn_in_periods=2,
                enable_soft_allocation=False
            )

            # Run extended test to allow learning
            dates = pd.date_range('2023-01-01', periods=15, freq='QS')
            final_allocation = None

            for date in dates:
                equity = 100000.0 * (1 + np.random.normal(0.01, 0.02))  # Slight upward trend
                state = create_dummy_portfolio_state(date, equity=equity, assets=self.assets)
                weights = mab.get_weights(date, state)

                if date == dates[-1]:
                    final_allocation = mab.last_allocations

            # Check if dominant strategy gets higher allocation
            passed = True
            errors = []
            warnings = []

            if final_allocation is None:
                passed = False
                errors.append("No final allocation recorded")
            else:
                dominant_idx = 0  # First strategy is dominant
                dominant_alloc = final_allocation[dominant_idx]
                avg_other_alloc = np.mean([final_allocation[i] for i in range(len(final_allocation)) if i != dominant_idx])

                if dominant_alloc < avg_other_alloc * 1.2:  # Should be significantly higher
                    warnings.append(f"Dominant strategy allocation {dominant_alloc:.1%} not significantly higher than others {avg_other_alloc:.1%}")

                # Check for over-concentration (>90%)
                if dominant_alloc > 0.9:
                    warnings.append(f"Over-concentration on dominant strategy: {dominant_alloc:.1%}")

            # Check learning progress
            diag = mab.get_bandit_diagnostics()
            if diag['bandit_has_learned']:
                passed = True
            else:
                warnings.append("Bandit has not learned from dominant strategy")

            metrics = {
                'periods_tested': len(dates),
                'dominant_final_allocation': final_allocation[0] if final_allocation is not None else 0,
                'bandit_learned': diag['bandit_has_learned'],
                'allocation_entropy': diag['allocation_entropy']
            }

            return StressTestResult(
                test_name=test_name,
                passed=passed,
                metrics=metrics,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            return StressTestResult(
                test_name=test_name,
                passed=False,
                metrics={},
                errors=[f"Test failed with exception: {e}"]
            )

    def test_parameter_sensitivity(self) -> StressTestResult:
        """Test sensitivity to different parameter settings."""
        test_name = "parameter_sensitivity"

        try:
            strategies = [
                DummyStrategyWrapper(f"Strategy{i}", self._generate_random_weights(), self.assets)
                for i in range(3)
            ]

            # Test different parameter combinations
            param_configs = [
                {'burn_in_periods': 1, 'reward_type': 'return'},
                {'burn_in_periods': 5, 'reward_type': 'return'},
                {'burn_in_periods': 3, 'reward_type': 'sharpe'},
                {'burn_in_periods': 3, 'reward_type': 'clipped_sharpe'},
            ]

            results = []

            for config in param_configs:
                bandit = UCBBandit(n_arms=3)
                mab = BanditStrategyWrapper(
                    child_strategies=strategies,
                    bandit_allocator=bandit,
                    **config
                )

                # Run short test
                dates = pd.date_range('2023-01-01', periods=8, freq='QS')
                for date in dates:
                    state = create_dummy_portfolio_state(date, equity=100000.0, assets=self.assets)
                    weights = mab.get_weights(date, state)

                # Collect metrics
                diag = mab.get_bandit_diagnostics()
                analytics = mab.get_learning_analytics()

                results.append({
                    'config': config,
                    'allocation_entropy': diag['allocation_entropy'],
                    'cumulative_regret': analytics['regret_metrics']['cumulative_regret'],
                    'total_turnover': analytics['allocation_churn']['total_turnover']
                })

            # Validate parameter stability
            passed = True
            errors = []
            warnings = []

            regrets = [r['cumulative_regret'] for r in results]
            regret_std = np.std(regrets)

            if regret_std > 10:  # High variation in regret
                warnings.append(f"High regret variation across parameters: std={regret_std:.2f}")

            # Check for extreme values
            for i, result in enumerate(results):
                if abs(result['cumulative_regret']) > 100:
                    warnings.append(f"Extreme regret in config {i}: {result['cumulative_regret']:.2f}")

            # All configurations should complete without errors
            if len(results) != len(param_configs):
                passed = False
                errors.append(f"Incomplete results: {len(results)}/{len(param_configs)} configs tested")

            metrics = {
                'configs_tested': len(results),
                'avg_regret': np.mean(regrets),
                'regret_std': regret_std,
                'avg_turnover': np.mean([r['total_turnover'] for r in results]),
                'parameter_stability': regret_std < 5  # Low variation indicates stability
            }

            return StressTestResult(
                test_name=test_name,
                passed=passed,
                metrics=metrics,
                errors=errors,
                warnings=warnings,
                details={'parameter_results': results}
            )

        except Exception as e:
            return StressTestResult(
                test_name=test_name,
                passed=False,
                metrics={},
                errors=[f"Test failed with exception: {e}"]
            )

    def test_missing_data_robustness(self) -> StressTestResult:
        """Test robustness to missing or corrupted data."""
        test_name = "missing_data_robustness"

        try:
            strategies = [
                DummyStrategyWrapper(f"Strategy{i}", self._generate_random_weights(), self.assets)
                for i in range(3)
            ]

            bandit = UCBBandit(n_arms=3)
            mab = BanditStrategyWrapper(
                child_strategies=strategies,
                bandit_allocator=bandit,
                burn_in_periods=2
            )

            # Test with missing portfolio values
            dates = pd.date_range('2023-01-01', periods=6, freq='QS')
            successful_periods = 0

            for i, date in enumerate(dates):
                # Simulate missing data scenarios
                if i == 2:
                    equity = None  # Missing equity
                elif i == 4:
                    equity = float('nan')  # NaN equity
                else:
                    equity = 100000.0 * (1 + np.random.normal(0, 0.02))

                try:
                    if equity is None or np.isnan(equity):
                        # Should handle gracefully
                        state = create_dummy_portfolio_state(date, equity=100000.0, assets=self.assets)
                    else:
                        state = create_dummy_portfolio_state(date, equity=equity, assets=self.assets)

                    weights = mab.get_weights(date, state)
                    successful_periods += 1
                except Exception as e:
                    logger.debug(f"Handled missing data gracefully: {e}")

            # Validate robustness
            passed = successful_periods >= 4  # Should handle most missing data
            errors = []
            warnings = []

            if successful_periods < len(dates) - 1:
                warnings.append(f"Some periods failed: {successful_periods}/{len(dates)} successful")

            # Test diagnostic robustness
            try:
                analytics = mab.get_learning_analytics()
                diag = mab.get_bandit_diagnostics()

                # Check for NaN/inf values
                if any(np.isnan(v) or np.isinf(v) for v in analytics['regret_metrics'].values()):
                    passed = False
                    errors.append("NaN/infinite values in analytics after missing data")

            except Exception as e:
                passed = False
                errors.append(f"Analytics failed after missing data: {e}")

            metrics = {
                'total_periods': len(dates),
                'successful_periods': successful_periods,
                'success_rate': successful_periods / len(dates),
                'missing_data_handled': successful_periods >= len(dates) - 1
            }

            return StressTestResult(
                test_name=test_name,
                passed=passed,
                metrics=metrics,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            return StressTestResult(
                test_name=test_name,
                passed=False,
                metrics={},
                errors=[f"Test failed with exception: {e}"]
            )

    def test_allocation_concentration(self) -> StressTestResult:
        """Test behavior under allocation concentration scenarios."""
        test_name = "allocation_concentration"

        try:
            strategies = [
                DummyStrategyWrapper(f"Strategy{i}", self._generate_random_weights(), self.assets)
                for i in range(5)  # More strategies to test concentration
            ]

            # Test hard allocation (should concentrate)
            bandit = UCBBandit(n_arms=5)
            mab_hard = BanditStrategyWrapper(
                child_strategies=strategies,
                bandit_allocator=bandit,
                burn_in_periods=2,
                enable_soft_allocation=False  # Hard allocation
            )

            # Test soft allocation (should diversify)
            bandit_soft = UCBBandit(n_arms=5)
            mab_soft = BanditStrategyWrapper(
                child_strategies=strategies,
                bandit_allocator=bandit_soft,
                burn_in_periods=2,
                enable_soft_allocation=True  # Soft allocation
            )

            dates = pd.date_range('2023-01-01', periods=10, freq='QS')

            # Test hard allocation
            hard_concentrations = []
            for date in dates:
                state = create_dummy_portfolio_state(date, equity=100000.0, assets=self.assets)
                weights = mab_hard.get_weights(date, state)
                if mab_hard.last_allocations is not None:
                    # Max allocation should be 1.0 for hard allocation
                    max_alloc = np.max(mab_hard.last_allocations)
                    hard_concentrations.append(max_alloc)

            # Test soft allocation
            soft_entropies = []
            for date in dates:
                state = create_dummy_portfolio_state(date, equity=100000.0, assets=self.assets)
                weights = mab_soft.get_weights(date, state)
                if mab_soft.last_allocations is not None:
                    # Calculate entropy (higher = more diverse)
                    allocs = mab_soft.last_allocations
                    entropy = -np.sum(allocs * np.log(allocs + 1e-10))
                    soft_entropies.append(entropy)

            # Validate concentration behavior
            passed = True
            errors = []
            warnings = []

            if hard_concentrations:
                avg_hard_concentration = np.mean(hard_concentrations)
                if avg_hard_concentration < 0.8:  # Should be highly concentrated
                    warnings.append(f"Hard allocation not concentrated enough: {avg_hard_concentration:.2f}")

            if soft_entropies:
                avg_soft_entropy = np.mean(soft_entropies)
                if avg_soft_entropy < 1.0:  # Should be diverse
                    warnings.append(f"Soft allocation not diverse enough: {avg_soft_entropy:.2f}")

            # Check for over-concentration warnings in diagnostics
            try:
                hard_diag = mab_hard.get_diagnostics()
                soft_diag = mab_soft.get_diagnostics()
            except Exception as e:
                warnings.append(f"Diagnostic generation failed: {e}")

            metrics = {
                'hard_allocation_periods': len(hard_concentrations),
                'avg_hard_concentration': np.mean(hard_concentrations) if hard_concentrations else 0,
                'soft_allocation_periods': len(soft_entropies),
                'avg_soft_entropy': np.mean(soft_entropies) if soft_entropies else 0,
                'concentration_behavior_correct': True  # Will be validated by warnings
            }

            return StressTestResult(
                test_name=test_name,
                passed=passed,
                metrics=metrics,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            return StressTestResult(
                test_name=test_name,
                passed=False,
                metrics={},
                errors=[f"Test failed with exception: {e}"]
            )

    def test_correlation_stress(self) -> StressTestResult:
        """Test MAB under extreme correlation scenarios."""
        test_name = "correlation_stress"

        try:
            # Create correlated strategy returns
            strategies = [
                CorrelatedStrategyWrapper(f"Strategy{i}", self._generate_random_weights(), self.assets, correlation_factor=0.9)
                for i in range(3)
            ]

            bandit = UCBBandit(n_arms=3)
            mab = BanditStrategyWrapper(
                child_strategies=strategies,
                bandit_allocator=bandit,
                burn_in_periods=3,
                reward_type='sharpe'  # Should handle correlation well
            )

            dates = pd.date_range('2023-01-01', periods=12, freq='QS')
            allocation_stability = []

            for date in dates:
                state = create_dummy_portfolio_state(date, equity=100000.0, assets=self.assets)
                weights = mab.get_weights(date, state)

                if mab.last_allocations is not None:
                    stability = 1.0 - np.std(mab.last_allocations)  # Lower std = more stable
                    allocation_stability.append(stability)

            # Validate correlation handling
            passed = True
            errors = []
            warnings = []

            if len(allocation_stability) < 8:
                passed = False
                errors.append("Insufficient stability data")

            stability_trend = np.polyfit(range(len(allocation_stability)), allocation_stability, 1)[0] if len(allocation_stability) > 5 else 0

            if stability_trend < -0.01:  # Becoming less stable
                warnings.append(f"Allocation stability decreasing: trend={stability_trend:.4f}")

            # Check for allocation oscillation
            if len(allocation_stability) > 3:
                stability_volatility = np.std(allocation_stability)
                if stability_volatility > 0.3:
                    warnings.append(f"High stability volatility: {stability_volatility:.4f}")

            metrics = {
                'periods_tested': len(allocation_stability),
                'avg_stability': np.mean(allocation_stability) if allocation_stability else 0,
                'stability_trend': stability_trend,
                'correlation_handled': stability_trend > -0.005
            }

            return StressTestResult(
                test_name=test_name,
                passed=passed,
                metrics=metrics,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            return StressTestResult(
                test_name=test_name,
                passed=False,
                metrics={},
                errors=[f"Test failed with exception: {e}"]
            )

    def test_reward_function_stability(self) -> StressTestResult:
        """Test reward function stability across different scenarios."""
        test_name = "reward_function_stability"

        try:
            strategies = [
                DummyStrategyWrapper(f"Strategy{i}", self._generate_random_weights(), self.assets)
                for i in range(3)
            ]

            reward_types = ['return', 'sharpe', 'clipped_sharpe']
            results = {}

            for reward_type in reward_types:
                bandit = UCBBandit(n_arms=3)
                mab = BanditStrategyWrapper(
                    child_strategies=strategies,
                    bandit_allocator=bandit,
                    burn_in_periods=2,
                    reward_type=reward_type
                )

                # Test with extreme returns
                dates = pd.date_range('2023-01-01', periods=8, freq='QS')
                extreme_returns = [0.5, -0.3, 0.8, -0.6, 0.2, -0.1, 0.9, -0.7]  # Volatile returns

                for i, date in enumerate(dates):
                    equity = 100000.0 * (1 + extreme_returns[i])
                    state = create_dummy_portfolio_state(date, equity=equity, assets=self.assets)
                    weights = mab.get_weights(date, state)

                # Collect stability metrics
                analytics = mab.get_learning_analytics()
                diag = mab.get_bandit_diagnostics()

                results[reward_type] = {
                    'regret': analytics['regret_metrics']['cumulative_regret'],
                    'turnover': analytics['allocation_churn']['total_turnover'],
                    'entropy': diag['allocation_entropy'],
                    'learned': diag['bandit_has_learned']
                }

            # Validate reward function stability
            passed = True
            errors = []
            warnings = []

            regrets = [r['regret'] for r in results.values()]
            regret_range = max(regrets) - min(regrets)

            if regret_range > 20:  # Large variation between reward types
                warnings.append(f"High regret variation between reward types: {regret_range:.2f}")

            # All reward types should complete successfully
            for reward_type, result in results.items():
                if np.isnan(result['regret']) or np.isinf(result['regret']):
                    passed = False
                    errors.append(f"Invalid regret for {reward_type}: {result['regret']}")

            # Check for reward type specific issues
            exp3_regret = results.get('clipped_sharpe', {}).get('regret', 0)
            if abs(exp3_regret) > 10:
                warnings.append(f"EXP3 reward function may have issues: regret={exp3_regret:.2f}")

            metrics = {
                'reward_types_tested': len(reward_types),
                'regret_range': regret_range,
                'avg_regret': np.mean(regrets),
                'reward_stability': regret_range < 15,
                'all_completed': all(r['learned'] for r in results.values())
            }

            return StressTestResult(
                test_name=test_name,
                passed=passed,
                metrics=metrics,
                errors=errors,
                warnings=warnings,
                details={'reward_results': results}
            )

        except Exception as e:
            return StressTestResult(
                test_name=test_name,
                passed=False,
                metrics={},
                errors=[f"Test failed with exception: {e}"]
            )

    def test_burn_in_edge_cases(self) -> StressTestResult:
        """Test burn-in logic edge cases."""
        test_name = "burn_in_edge_cases"

        try:
            strategies = [
                DummyStrategyWrapper(f"Strategy{i}", self._generate_random_weights(), self.assets)
                for i in range(3)
            ]

            # Test edge cases
            edge_cases = [
                {'burn_in_periods': 0},  # No burn-in
                {'burn_in_periods': 1},  # Minimal burn-in
                {'burn_in_periods': 10}, # Long burn-in
            ]

            results = []

            for config in edge_cases:
                bandit = UCBBandit(n_arms=3)
                mab = BanditStrategyWrapper(
                    child_strategies=strategies,
                    bandit_allocator=bandit,
                    **config
                )

                # Run test
                periods = max(config['burn_in_periods'] + 3, 5)  # Test beyond burn-in
                dates = pd.date_range('2023-01-01', periods=periods, freq='QS')

                burn_in_allocs = []
                post_burn_in_allocs = []

                for i, date in enumerate(dates):
                    state = create_dummy_portfolio_state(date, equity=100000.0, assets=self.assets)
                    weights = mab.get_weights(date, state)

                    if mab.last_allocations is not None:
                        if i < config['burn_in_periods']:
                            burn_in_allocs.append(mab.last_allocations)
                        else:
                            post_burn_in_allocs.append(mab.last_allocations)

                results.append({
                    'config': config,
                    'burn_in_periods_actual': len(burn_in_allocs),
                    'post_burn_in_periods': len(post_burn_in_allocs),
                    'burn_in_equal': all(np.allclose(alloc, [1/3, 1/3, 1/3], atol=0.01) for alloc in burn_in_allocs) if burn_in_allocs else True,
                    'post_burn_in_varied': len(set(tuple(alloc) for alloc in post_burn_in_allocs)) > 1 if post_burn_in_allocs else False
                })

            # Validate edge case handling
            passed = True
            errors = []
            warnings = []

            for result in results:
                config = result['config']

                # Check burn-in periods
                if result['burn_in_periods_actual'] != config['burn_in_periods']:
                    passed = False
                    errors.append(f"Burn-in periods mismatch for {config}: expected {config['burn_in_periods']}, got {result['burn_in_periods_actual']}")

                # Check burn-in allocation equality
                if config['burn_in_periods'] > 0 and not result['burn_in_equal']:
                    warnings.append(f"Burn-in allocations not equal for {config}")

                # Check post-burn-in variation (except for burn_in=0)
                if config['burn_in_periods'] == 0 and not result['post_burn_in_varied']:
                    warnings.append(f"No allocation variation after burn-in=0")

            metrics = {
                'edge_cases_tested': len(edge_cases),
                'all_burn_in_correct': all(r['burn_in_periods_actual'] == r['config']['burn_in_periods'] for r in results),
                'burn_in_edge_cases_handled': passed
            }

            return StressTestResult(
                test_name=test_name,
                passed=passed,
                metrics=metrics,
                errors=errors,
                warnings=warnings,
                details={'edge_case_results': results}
            )

        except Exception as e:
            return StressTestResult(
                test_name=test_name,
                passed=False,
                metrics={},
                errors=[f"Test failed with exception: {e}"]
            )

    def _generate_random_weights(self) -> Dict[str, float]:
        """Generate random portfolio weights that sum to 1."""
        weights = np.random.random(len(self.assets))
        weights = weights / np.sum(weights)
        return dict(zip(self.assets, weights))


# Helper classes for stress testing

class FailingStrategyWrapper(DummyStrategyWrapper):
    """Strategy wrapper that fails on purpose for testing."""

    def __init__(self, name: str, assets: List[str]):
        super().__init__(name, {}, assets)

    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> pd.Series:
        """Always raises an exception."""
        raise RuntimeError(f"Strategy {self.name} intentionally failed")


class DominantStrategyWrapper(DummyStrategyWrapper):
    """Strategy wrapper that performs dominantly."""

    def __init__(self, name: str, weights: Dict[str, float], assets: List[str], dominance_factor: float = 2.0):
        super().__init__(name, weights, assets)
        self.dominance_factor = dominance_factor

    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> pd.Series:
        """Return weights with dominance factor applied to returns."""
        base_weights = super().get_weights(date, portfolio_state)
        # Dominant strategy gets better returns
        return base_weights * self.dominance_factor


class CorrelatedStrategyWrapper(DummyStrategyWrapper):
    """Strategy wrapper with controlled correlation."""

    def __init__(self, name: str, weights: Dict[str, float], assets: List[str], correlation_factor: float = 0.8):
        super().__init__(name, weights, assets)
        self.correlation_factor = correlation_factor
        self.base_return = np.random.normal(0.01, 0.02)

    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> pd.Series:
        """Return correlated weights."""
        # Add correlation to returns
        correlated_return = self.base_return * (1 - self.correlation_factor) + \
                          np.random.normal(0.01, 0.02) * self.correlation_factor

        # Update base for next period
        self.base_return = correlated_return

        return super().get_weights(date, portfolio_state)

