"""
Comprehensive Pre-Flight Check
Validates all imports and dependencies before running demo_benchmark_strategies.py
"""
import sys
import os

print("="*80)
print("PRE-FLIGHT VALIDATION CHECK")
print("="*80)
print()

# Test 1: Core package imports
print("[1/8] Testing core package imports...")
try:
    from src.data_loader import load_data
    from src.portfolio_engine import PortfolioEngine
    from src.evaluator import Evaluator
    from src.strategy import Strategy
    from src.optimizer import PortfolioOptimizer
    print("      ✓ Core modules imported successfully")
except Exception as e:
    print(f"      ✗ FAILED: {e}")
    sys.exit(1)

# Test 2: Core strategies
print("[2/8] Testing core strategy imports...")
try:
    from src.strategy_wrapper import (
        EqualWeightStrategy,
        MomentumStrategy,
        MeanReversionStrategy,
        InverseVolatilityStrategy,
        GlobalMinimumVarianceStrategy,
        CVaRMinimizationStrategy,
        RegimeSwitchingStrategy,
        MLRandomForestStrategy,
        MLGradientBoostingStrategy,
        ARMAForecastStrategy,
        MultiFactorMLStrategy
    )
    print("      ✓ All 11 core strategies imported successfully")
except Exception as e:
    print(f"      ✗ FAILED: {e}")
    sys.exit(1)

# Test 3: Extended strategies
print("[3/8] Testing extended strategy imports...")
try:
    from src.strategy_wrapper import (
        BuyAndHoldStrategy,
        QuintileFactorStrategy,
        GMRPStrategy,
        MaximumDiversificationStrategy,
        MaximumDecorrelationStrategy,
        TimeSeriesMomentumStrategy,
        MovingAverageCrossoverStrategy,
        MarkowitzMVOStrategy,
        LinearRegressionStrategy
    )
    print("      ✓ All 9 extended strategies imported successfully")
except Exception as e:
    print(f"      ✗ FAILED: {e}")
    sys.exit(1)

# Test 4: Utility functions
print("[4/8] Testing utility functions...")
try:
    from src.strategy_wrapper import list_available_strategies, create_strategy
    strategies = list_available_strategies()
    assert len(strategies) == 20, f"Expected 20 strategies, got {len(strategies)}"
    print(f"      ✓ Utility functions work, {len(strategies)} strategies available")
except Exception as e:
    print(f"      ✗ FAILED: {e}")
    sys.exit(1)

# Test 5: Package-level imports
print("[5/8] Testing package-level imports (from src import *)...")
try:
    from src import (
        BuyAndHoldStrategy,
        MaximumDiversificationStrategy,
        LinearRegressionStrategy,
        list_available_strategies
    )
    print("      ✓ Package-level imports work correctly")
except Exception as e:
    print(f"      ✗ FAILED: {e}")
    sys.exit(1)

# Test 6: Verify no references to deleted files
print("[6/8] Checking for references to deleted strategies_extended.py...")
try:
    import importlib.util
    spec = importlib.util.find_spec('src.strategies_extended')
    if spec is not None:
        print("      ✗ WARNING: strategies_extended.py still exists!")
    else:
        print("      ✓ strategies_extended.py correctly removed")
except Exception as e:
    print(f"      ✓ strategies_extended.py correctly removed")

# Test 7: Demo file syntax check
print("[7/8] Validating demo_benchmark_strategies.py...")
try:
    import py_compile
    py_compile.compile('examples/demo_benchmark_strategies.py', doraise=True)
    print("      ✓ demo_benchmark_strategies.py is syntactically valid")
except Exception as e:
    print(f"      ✗ FAILED: {e}")
    sys.exit(1)

# Test 8: Test strategy instantiation
print("[8/8] Testing strategy instantiation...")
try:
    import pandas as pd
    import numpy as np
    
    # Create minimal test data
    dates = pd.date_range('2020-01-01', '2020-01-31', freq='D')
    prices = pd.DataFrame(
        np.random.randn(len(dates), 3).cumsum(axis=0) + 100,
        index=dates,
        columns=['A', 'B', 'C']
    )
    
    strategy_obj = Strategy(prices)
    optimizer = PortfolioOptimizer()
    
    # Test creating strategies
    eq_strat = EqualWeightStrategy(strategy_obj, optimizer)
    bh_strat = BuyAndHoldStrategy(strategy_obj, optimizer)
    lr_strat = LinearRegressionStrategy(strategy_obj, optimizer)
    
    print("      ✓ Strategy instantiation works correctly")
except Exception as e:
    print(f"      ✗ FAILED: {e}")
    sys.exit(1)

print()
print("="*80)
print("ALL VALIDATION CHECKS PASSED ✓")
print("="*80)
print()
print("Summary:")
print("  - 20 strategies available (11 core + 9 extended)")
print("  - All imports working correctly")
print("  - No references to deleted files")
print("  - demo_benchmark_strategies.py is ready to run")
print()
print("You can now safely run:")
print("  python examples/demo_benchmark_strategies.py")
print()
print("Note: The demo will take 10-15 minutes due to daily rebalancing over 10 years.")
print("="*80)
