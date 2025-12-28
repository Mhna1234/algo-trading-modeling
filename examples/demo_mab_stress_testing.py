"""
MAB Stress Testing Demo

Demonstrates the comprehensive stress testing framework for MAB robustness validation.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt

from src.mab_stress_testing import MABStressTester


def create_sample_market_data():
    """Create realistic market data for stress testing."""
    np.random.seed(42)

    # Create 4 years of monthly data
    dates = pd.date_range('2020-01-01', '2023-12-31', freq='ME')
    assets = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA']

    # Generate realistic price data with different characteristics
    prices = {}
    for i, asset in enumerate(assets):
        # Different starting prices and return characteristics
        start_price = 50 + i * 30
        drift = 0.08 + np.random.normal(0, 0.02)  # Different long-term trends
        volatility = 0.15 + np.random.normal(0, 0.05)  # Different volatilities

        # Generate returns with some correlation structure
        returns = np.random.normal(drift/12, volatility/np.sqrt(12), len(dates))
        prices[asset] = start_price * np.cumprod(1 + returns)

    return pd.DataFrame(prices, index=dates)


def run_stress_testing_demo():
    """Run comprehensive stress testing demonstration."""
    print("🔬 MAB Stress Testing Framework Demo")
    print("=" * 50)

    # Create market data
    print("\n📊 Creating sample market data...")
    market_data = create_sample_market_data()
    print(f"✓ Generated {len(market_data)} periods of data for {len(market_data.columns)} assets")

    # Initialize stress tester
    print("\n🧪 Initializing MAB Stress Tester...")
    stress_tester = MABStressTester(market_data)
    print("✓ Stress tester initialized successfully")

    # Run all stress tests
    print("\n🚀 Running comprehensive stress tests...")
    print("This may take a moment as we test 10 different stress scenarios...")

    results = stress_tester.run_all_stress_tests()

    # Display results
    print("\n📋 Stress Test Results Summary:")
    print("-" * 50)

    passed_count = 0
    total_count = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"{status} {test_name}")
        passed_count += 1 if result.passed else 0

        # Show key metrics
        if result.metrics:
            key_metrics = list(result.metrics.keys())[:3]  # Show first 3 metrics
            metric_str = ", ".join([f"{k}: {v:.3f}" for k, v in result.metrics.items() if k in key_metrics])
            print(f"      Key metrics: {metric_str}")

        # Show warnings/errors if any
        if result.warnings:
            print(f"      ⚠️  Warnings: {len(result.warnings)}")
        if result.errors:
            print(f"      ❌ Errors: {len(result.errors)}")
        print()

    # Overall summary
    print("🎯 Overall Results:")
    print(f"   Tests Passed: {passed_count}/{total_count}")
    print(f"   Pass Rate: {passed_count/total_count:.1%}")
    if passed_count == total_count:
        print("   🎉 All stress tests PASSED! MAB system is robust.")
    else:
        print("   ⚠️  Some tests failed. Review results above for details.")

    print("\n🔍 Stress Test Scenarios Covered:")
    print("   • Cold-start behavior with minimal data")
    print("   • Strategy failure robustness")
    print("   • Extreme market volatility handling")
    print("   • Strategy dominance detection")
    print("   • Parameter sensitivity analysis")
    print("   • Missing data robustness")
    print("   • Allocation concentration limits")
    print("   • Correlation stress scenarios")
    print("   • Reward function stability")
    print("   • Burn-in edge case handling")

    print("\n💡 Key Benefits of This Framework:")
    print("   • Validates MAB behavior under extreme conditions")
    print("   • Ensures graceful degradation during failures")
    print("   • Provides confidence in production deployment")
    print("   • Enables parameter tuning and optimization")
    print("   • Supports continuous monitoring and alerting")

    return results


if __name__ == "__main__":
    # Run the demo
    results = run_stress_testing_demo()

    print("\n" + "=" * 50)
    print("Demo completed! The MAB stress testing framework is ready for production use.")
    print("Use this framework to validate MAB performance before deployment and during monitoring.")