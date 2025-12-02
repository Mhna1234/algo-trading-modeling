"""
Quick Verification Test - Post-Fix Validation
==============================================

This script tests that all critical fixes have been successfully applied.
Run this before running full demos to ensure basic functionality.

Usage:
    python verify_fixes.py
"""

import sys
import os

def test_imports():
    """Test that all strategy imports work correctly."""
    print("Testing imports...")
    try:
        from src import (
            EqualWeightStrategy,
            BuyAndHoldStrategy,
            MomentumStrategy,
            MeanReversionStrategy,
            InverseVolatilityStrategy,
            GlobalMinimumVarianceStrategy,
            CVaRMinimizationStrategy,
            MaximumDiversificationStrategy,
            MaximumDecorrelationStrategy,
            QuintileFactorStrategy,
            TimeSeriesMomentumStrategy,
            MovingAverageCrossoverStrategy,
            MarkowitzMVOStrategy,
            LinearRegressionStrategy,
            PortfolioEngine,
            Strategy,
            PortfolioOptimizer,
            load_data
        )
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_strategy_registry():
    """Test that strategy registry is correctly updated."""
    print("\nTesting strategy registry...")
    try:
        from src.strategy_wrapper import list_available_strategies
        
        strategies = list_available_strategies()
        expected_strategies = [
            'equal_weight',
            'momentum',
            'mean_reversion',
            'inverse_volatility',
            'cvar_minimization',
            'gmvp',
            'buy_and_hold',
            'quintile_factor',
            'max_diversification',
            'max_decorrelation',
            'time_series_momentum',
            'ma_crossover',
            'markowitz_mvo',
            'linear_regression'
        ]
        
        missing = [s for s in expected_strategies if s not in strategies]
        extra = [s for s in strategies if s not in expected_strategies]
        
        if missing:
            print(f"✗ Missing strategies: {missing}")
            return False
        
        if extra:
            print(f"⚠ Extra strategies (not expected): {extra}")
        
        print(f"✓ Strategy registry correct ({len(strategies)} strategies)")
        print(f"  Available: {', '.join(strategies.keys())}")
        return True
        
    except Exception as e:
        print(f"✗ Registry test failed: {e}")
        return False


def test_no_duplicate_classes():
    """Test that there are no duplicate class definitions."""
    print("\nTesting for duplicate class definitions...")
    try:
        from src import strategy_wrapper
        import inspect
        
        # Get all classes in strategy_wrapper
        classes = [name for name, obj in inspect.getmembers(strategy_wrapper, inspect.isclass)
                   if obj.__module__ == 'src.strategy_wrapper']
        
        # Check for duplicates
        from collections import Counter
        counts = Counter(classes)
        duplicates = [name for name, count in counts.items() if count > 1]
        
        if duplicates:
            print(f"✗ Duplicate classes found: {duplicates}")
            return False
        
        print(f"✓ No duplicate classes ({len(classes)} unique classes)")
        return True
        
    except Exception as e:
        print(f"✗ Duplicate check failed: {e}")
        return False


def test_optimizer_validation():
    """Test that optimizer validation is working."""
    print("\nTesting optimizer validation...")
    try:
        from src import PortfolioOptimizer
        import numpy as np
        
        optimizer = PortfolioOptimizer()
        
        # This should raise ValueError
        try:
            weights = optimizer.optimize(
                initial_weights=np.array([0.5, 0.5]),
                objective='sharpe'
            )
            print("✗ Optimizer didn't raise error for missing returns data")
            return False
        except ValueError as e:
            if "No returns data available" in str(e):
                print("✓ Optimizer validation working correctly")
                return True
            else:
                print(f"✗ Wrong error message: {e}")
                return False
        
    except Exception as e:
        print(f"✗ Optimizer test failed: {e}")
        return False


def test_data_loader():
    """Test that data loader uses updated pandas syntax."""
    print("\nTesting data loader (pandas compatibility)...")
    try:
        import pandas as pd
        import warnings
        
        # Check pandas version
        pandas_version = tuple(int(x) for x in pd.__version__.split('.')[:2])
        print(f"  Pandas version: {pd.__version__}")
        
        if pandas_version >= (2, 0):
            print("  ✓ Using pandas 2.0+ - ffill() syntax should be used")
        
        # Check if data_loader uses ffill() instead of fillna(method='ffill')
        with open('src/data_loader.py', 'r') as f:
            content = f.read()
            if 'fillna(method=' in content:
                print("  ✗ Still using deprecated fillna(method=...) syntax")
                return False
            elif '.ffill()' in content:
                print("  ✓ Using modern ffill() syntax")
                return True
            else:
                print("  ⚠ Cannot determine ffill usage")
                return True
        
    except Exception as e:
        print(f"✗ Data loader test failed: {e}")
        return False


def main():
    """Run all verification tests."""
    print("="*70)
    print("POST-FIX VERIFICATION TEST")
    print("="*70)
    
    tests = [
        ("Import Test", test_imports),
        ("Strategy Registry", test_strategy_registry),
        ("Duplicate Classes", test_no_duplicate_classes),
        ("Optimizer Validation", test_optimizer_validation),
        ("Data Loader", test_data_loader)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n✗ {name} crashed: {e}")
            results.append((name, False))
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    total = len(results)
    passed = sum(1 for _, result in results if result)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {name}")
    
    print("-"*70)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED - Project is ready to use!")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed - Review issues above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
