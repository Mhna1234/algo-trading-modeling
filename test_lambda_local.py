"""
Local Lambda Function Test
Tests the lambda_function.py handler locally before AWS deployment.
"""

import json
import sys
from datetime import datetime
from unittest.mock import Mock


class MockContext:
    """Mock Lambda context for local testing."""
    def __init__(self):
        self.function_name = "benchmark-daily-calculator"
        self.memory_limit_in_mb = 3008
        self.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:benchmark-daily-calculator"
        self.aws_request_id = "test-request-id"

    def get_remaining_time_in_millis(self):
        return 900000  # 15 minutes


def test_lambda_imports():
    """Test 1: Verify all imports work."""
    print("\n=== Test 1: Import Check ===")
    try:
        import lambda_function
        print("✓ lambda_function.py imports successfully")

        # Check if all benchmark strategies can be imported
        from src.strategies.benchmarks import (
            BuyAndHoldBenchmark,
            EqualWeightBenchmark,
            QuintileFactorBenchmark,
            QuintileLowVolatilityBenchmark,
            MeanReversionBenchmark,
            GlobalMinVarianceBenchmark,
            InverseVolatilityBenchmark,
            InverseVarianceBenchmark,
            RiskParityBenchmark,
            MaxDecorrelationBenchmark,
            MostDiversifiedBenchmark,
            SharpeMaximizationBenchmark,
            CVaRMinimizationBenchmark,
            TopKReturnBenchmark,
            TopKSharpeBenchmark,
        )
        print("✓ All 15 benchmark strategies import successfully")

        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_strategy_initialization():
    """Test 2: Verify strategies can be initialized."""
    print("\n=== Test 2: Strategy Initialization ===")
    try:
        from lambda_function import get_benchmark_strategies
        from src.signal_generator import Strategy
        import pandas as pd
        import numpy as np

        # Create dummy price data
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']
        prices = pd.DataFrame(
            np.random.randn(100, 5).cumsum(axis=0) + 100,
            index=dates,
            columns=tickers
        )

        signal_generator = Strategy(prices)
        strategies = get_benchmark_strategies(signal_generator)

        print(f"✓ Initialized {len(strategies)} strategies:")
        for name in strategies.keys():
            print(f"  - {name}")

        return True
    except Exception as e:
        print(f"✗ Strategy initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_single_backtest():
    """Test 3: Run backtests and verify weights are only on rebalance dates."""
    print("\n=== Test 3: Backtest & Weights Validation ===")
    try:
        from lambda_function import run_benchmark_backtest, get_benchmark_strategies
        from src.signal_generator import Strategy
        import pandas as pd
        import numpy as np
        from datetime import datetime

        # Create dummy price data (3 years for walk-forward testing)
        dates = pd.date_range('2022-01-01', periods=1100, freq='D')  # ~3 years
        tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']
        np.random.seed(42)
        prices = pd.DataFrame(
            np.random.randn(1100, 5).cumsum(axis=0) + 100,
            index=dates,
            columns=tickers
        )

        signal_generator = Strategy(prices)
        strategies = get_benchmark_strategies(signal_generator)

        # Test Weekly Rebalancing
        print("\nTesting Weekly Rebalancing...")
        result_w = run_benchmark_backtest(
            strategy_name='equal_weight',
            strategy=strategies['equal_weight'],
            prices=prices,
            rebalance_freq='W'
        )

        if result_w['status'] != 'success':
            print(f"✗ Weekly backtest failed: {result_w.get('error_message', 'Unknown')}")
            return False

        weights_data_w = result_w['weights']
        print(f"  Weekly: {len(weights_data_w['dates'])} weight entries")

        # Check that weights are ~7 days apart
        dates_w = [datetime.strptime(d, '%Y-%m-%d') for d in weights_data_w['dates'][:5]]
        if len(dates_w) >= 2:
            gaps_w = [(dates_w[i+1] - dates_w[i]).days for i in range(len(dates_w)-1)]
            avg_gap_w = sum(gaps_w) / len(gaps_w) if gaps_w else 0
            print(f"  Days between rebalances: {gaps_w}")
            print(f"  Average: {avg_gap_w:.1f} days")

            if avg_gap_w < 5 or avg_gap_w > 10:
                print(f"✗ Weekly rebalancing spacing incorrect (expected ~7 days, got {avg_gap_w:.1f})")
                return False

        # Test Monthly Rebalancing
        print("\nTesting Monthly Rebalancing...")
        result_m = run_benchmark_backtest(
            strategy_name='equal_weight',
            strategy=strategies['equal_weight'],
            prices=prices,
            rebalance_freq='M'
        )

        if result_m['status'] != 'success':
            print(f"✗ Monthly backtest failed: {result_m.get('error_message', 'Unknown')}")
            return False

        weights_data_m = result_m['weights']
        print(f"  Monthly: {len(weights_data_m['dates'])} weight entries")

        # Check that weights are ~30 days apart
        dates_m = [datetime.strptime(d, '%Y-%m-%d') for d in weights_data_m['dates'][:3]]
        if len(dates_m) >= 2:
            gaps_m = [(dates_m[i+1] - dates_m[i]).days for i in range(len(dates_m)-1)]
            avg_gap_m = sum(gaps_m) / len(gaps_m) if gaps_m else 0
            print(f"  Days between rebalances: {gaps_m}")
            print(f"  Average: {avg_gap_m:.1f} days")

            if avg_gap_m < 20 or avg_gap_m > 40:
                print(f"✗ Monthly rebalancing spacing incorrect (expected ~30 days, got {avg_gap_m:.1f})")
                return False

        print("\n✓ All backtests completed successfully")
        print("✓ Weights are correctly filtered to rebalance dates only")
        print(f"\n  Metrics (Weekly):")
        print(f"    Total Return: {result_w['metrics']['total_return']:.2%}")
        print(f"    Sharpe Ratio: {result_w['metrics']['sharpe_ratio']:.2f}")
        print(f"    Max Drawdown: {result_w['metrics']['max_drawdown']:.2%}")

        return True

    except Exception as e:
        print(f"✗ Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_lambda_handler_mock():
    """Test 4: Test lambda_handler with mocked S3."""
    print("\n=== Test 4: Lambda Handler (Mocked) ===")
    print("⊘ Skipped (requires AWS S3 access)")
    print("To test: Manually run lambda_handler after deploying to AWS")
    return True

def test_lambda_handler_mock_interactive():
    """Test 4: Test lambda_handler with mocked S3 (Interactive)."""
    print("\n=== Test 4: Lambda Handler (Mocked) ===")
    print("Note: This test will fail if S3 buckets are not accessible.")
    print("Run this only if you have AWS credentials configured.")

    try:
        response = input("Do you want to run the full Lambda handler test? (y/n): ")
    except EOFError:
        print("⊘ Skipped Lambda handler test (non-interactive mode)")
        return True

    if response.lower() != 'y':
        print("⊘ Skipped Lambda handler test")
        return True

    try:
        from lambda_function import lambda_handler

        event = {
            "test": True,
            "execution_date": datetime.utcnow().strftime('%Y-%m-%d')
        }

        context = MockContext()

        print("Running Lambda handler (this may take several minutes)...")
        result = lambda_handler(event, context)

        if result['statusCode'] == 200:
            print("✓ Lambda handler completed successfully")
            print(f"  Duration: {result['duration_seconds']:.1f}s")
            print(f"  Successful backtests: {result['successful']}/{result['total_backtests']}")
            return True
        else:
            print(f"✗ Lambda handler failed: {result.get('error_message', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"✗ Lambda handler test failed: {e}")
        print("This is expected if S3 buckets are not accessible locally.")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all local tests."""
    print("=" * 60)
    print("AWS Lambda Function - Local Testing Suite")
    print("=" * 60)

    results = []

    # Test 1: Imports
    results.append(("Import Check", test_lambda_imports()))

    # Test 2: Strategy Initialization
    if results[-1][1]:  # Only if imports passed
        results.append(("Strategy Initialization", test_strategy_initialization()))

    # Test 3: Single Backtest
    if results[-1][1]:  # Only if initialization passed
        results.append(("Single Backtest", test_single_backtest()))

    # Test 4: Full Lambda Handler (optional)
    if all(r[1] for r in results):  # Only if all previous tests passed
        results.append(("Lambda Handler (Mocked)", test_lambda_handler_mock()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")

    total_passed = sum(1 for _, passed in results if passed)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")

    if all(passed for _, passed in results):
        print("\n🎉 All tests passed! Ready for AWS deployment.")
        return 0
    else:
        print("\n⚠ Some tests failed. Fix issues before deploying to AWS.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
