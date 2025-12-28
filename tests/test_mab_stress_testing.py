"""
Tests for MAB Stress Testing Framework

Comprehensive tests for the MAB stress testing functionality.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from src.mab_stress_testing import MABStressTester, StressTestResult
from src.strategies.bandit_strategy_wrapper import BanditStrategyWrapper
from src.bandits import UCBBandit


class TestMABStressTesting:
    """Test suite for MAB stress testing framework."""

    @pytest.fixture
    def sample_prices(self):
        """Create sample price data for testing."""
        dates = pd.date_range('2020-01-01', '2023-12-31', freq='M')
        assets = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']

        # Generate realistic price data
        np.random.seed(42)
        prices = {}
        for asset in assets:
            start_price = 100 + np.random.randint(50, 150)
            returns = np.random.normal(0.01, 0.03, len(dates))
            prices[asset] = start_price * np.cumprod(1 + returns)

        return pd.DataFrame(prices, index=dates)

    @pytest.fixture
    def stress_tester(self, sample_prices):
        """Create stress tester instance."""
        return MABStressTester(sample_prices)

    def test_stress_tester_initialization(self, stress_tester):
        """Test stress tester initialization."""
        assert stress_tester.assets == ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
        assert len(stress_tester.base_prices) > 0

    def test_run_all_stress_tests(self, stress_tester):
        """Test running all stress tests."""
        results = stress_tester.run_all_stress_tests()

        # Should have results for all test methods
        expected_tests = [
            'cold_start_behavior',
            'strategy_failure_robustness',
            'extreme_volatility',
            'strategy_dominance',
            'parameter_sensitivity',
            'missing_data_robustness',
            'allocation_concentration',
            'correlation_stress',
            'reward_function_stability',
            'burn_in_edge_cases'
        ]

        for test_name in expected_tests:
            assert test_name in results
            assert isinstance(results[test_name], StressTestResult)
            assert isinstance(results[test_name].passed, bool)
            assert isinstance(results[test_name].metrics, dict)

    def test_cold_start_behavior(self, stress_tester):
        """Test cold start behavior test."""
        result = stress_tester.test_cold_start_behavior()

        assert isinstance(result, StressTestResult)
        assert result.test_name == "cold_start_behavior"
        assert isinstance(result.passed, bool)
        assert 'periods_tested' in result.metrics
        assert 'avg_allocation_entropy' in result.metrics

    def test_strategy_failure_robustness(self, stress_tester):
        """Test strategy failure robustness test."""
        result = stress_tester.test_strategy_failure_robustness()

        assert isinstance(result, StressTestResult)
        assert result.test_name == "strategy_failure_robustness"
        assert isinstance(result.passed, bool)
        assert 'successful_allocations' in result.metrics
        assert 'failure_rate' in result.metrics

    def test_extreme_volatility(self, stress_tester):
        """Test extreme volatility test."""
        result = stress_tester.test_extreme_volatility()

        assert isinstance(result, StressTestResult)
        assert result.test_name == "extreme_volatility"
        assert isinstance(result.passed, bool)
        assert 'allocation_volatility' in result.metrics

    def test_strategy_dominance(self, stress_tester):
        """Test strategy dominance test."""
        result = stress_tester.test_strategy_dominance()

        assert isinstance(result, StressTestResult)
        assert result.test_name == "strategy_dominance"
        assert isinstance(result.passed, bool)
        assert 'dominant_final_allocation' in result.metrics

    def test_parameter_sensitivity(self, stress_tester):
        """Test parameter sensitivity test."""
        result = stress_tester.test_parameter_sensitivity()

        assert isinstance(result, StressTestResult)
        assert result.test_name == "parameter_sensitivity"
        assert isinstance(result.passed, bool)
        assert 'configs_tested' in result.metrics
        assert 'regret_std' in result.metrics

    def test_missing_data_robustness(self, stress_tester):
        """Test missing data robustness test."""
        result = stress_tester.test_missing_data_robustness()

        assert isinstance(result, StressTestResult)
        assert result.test_name == "missing_data_robustness"
        assert isinstance(result.passed, bool)
        assert 'success_rate' in result.metrics

    def test_allocation_concentration(self, stress_tester):
        """Test allocation concentration test."""
        result = stress_tester.test_allocation_concentration()

        assert isinstance(result, StressTestResult)
        assert result.test_name == "allocation_concentration"
        assert isinstance(result.passed, bool)
        assert 'avg_hard_concentration' in result.metrics
        assert 'avg_soft_entropy' in result.metrics

    def test_correlation_stress(self, stress_tester):
        """Test correlation stress test."""
        result = stress_tester.test_correlation_stress()

        assert isinstance(result, StressTestResult)
        assert result.test_name == "correlation_stress"
        assert isinstance(result.passed, bool)
        assert 'stability_trend' in result.metrics

    def test_reward_function_stability(self, stress_tester):
        """Test reward function stability test."""
        result = stress_tester.test_reward_function_stability()

        assert isinstance(result, StressTestResult)
        assert result.test_name == "reward_function_stability"
        assert isinstance(result.passed, bool)
        assert 'reward_types_tested' in result.metrics

    def test_burn_in_edge_cases(self, stress_tester):
        """Test burn-in edge cases test."""
        result = stress_tester.test_burn_in_edge_cases()

        assert isinstance(result, StressTestResult)
        assert result.test_name == "burn_in_edge_cases"
        assert isinstance(result.passed, bool)
        assert 'edge_cases_tested' in result.metrics

    def test_stress_test_result_structure(self):
        """Test StressTestResult data structure."""
        result = StressTestResult(
            test_name="test_example",
            passed=True,
            metrics={'metric1': 1.0, 'metric2': 2.0},
            errors=['error1'],
            warnings=['warning1'],
            details={'detail1': 'value1'}
        )

        assert result.test_name == "test_example"
        assert result.passed is True
        assert result.metrics == {'metric1': 1.0, 'metric2': 2.0}
        assert result.errors == ['error1']
        assert result.warnings == ['warning1']
        assert result.details == {'detail1': 'value1'}

    def test_stress_test_comprehensive_validation(self, stress_tester):
        """Test that stress tests perform comprehensive validation."""
        results = stress_tester.run_all_stress_tests()

        # All tests should have completed
        assert len(results) == 10

        # Check that tests include proper validation
        for test_name, result in results.items():
            # Each test should have metrics
            assert isinstance(result.metrics, dict)
            assert len(result.metrics) > 0

            # Errors and warnings should be lists
            assert isinstance(result.errors, list)
            assert isinstance(result.warnings, list)

            # Details should be a dict
            assert isinstance(result.details, dict)

    def test_stress_test_error_handling(self, stress_tester):
        """Test that stress tests handle errors gracefully."""
        # This test ensures that if any stress test fails,
        # it doesn't crash the entire test suite

        results = stress_tester.run_all_stress_tests()

        # All results should be StressTestResult objects
        for result in results.values():
            assert isinstance(result, StressTestResult)

        # At least some tests should pass (assuming implementation is correct)
        passed_tests = sum(1 for r in results.values() if r.passed)
        assert passed_tests >= 5  # At least half should pass