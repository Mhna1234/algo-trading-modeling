# Migration Guide - Extended Strategies Integration

## Overview

This guide helps you integrate the new extended strategies (`strategies_extended.py`) into your existing algo-trading project.

## What's New

### Extended Strategies Module
- **New File**: `src/strategies_extended.py`
- **Strategies Added**: 9 new strategies
- **Total Strategies**: 20 (11 existing + 9 new)

### New Strategies Available
1. Buy & Hold
2. Quintile Factor Portfolios
3. GMRP (Global Maximum Return)
4. Maximum Diversification (MDP)
5. Maximum Decorrelation (MDCP)
6. Time-Series Momentum
7. Moving Average Crossover
8. Markowitz Mean-Variance
9. Linear Regression Prediction

## Migration Steps

### Step 1: No Breaking Changes ✅

**Good news**: All existing code continues to work! The extended strategies are **additive only**.

```python
# Your existing code still works exactly as before
from src.strategy_wrapper import EqualWeightStrategy, MomentumStrategy

equal_weight = EqualWeightStrategy(strategy)
momentum = MomentumStrategy(strategy, optimizer)

# Existing backtests run unchanged
result = portfolio.run_backtest(momentum, rebalance_freq='M')
```

### Step 2: Import Extended Strategies

```python
# Option 1: Import specific strategies
from src.strategies_extended import (
    MaximumDiversificationStrategy,
    MarkowitzMVOStrategy
)

# Option 2: Use factory function
from src.strategies_extended import create_extended_strategy

mdp = create_extended_strategy(
    'maximum_diversification',
    strategy_obj,
    optimizer,
    lookback=252
)
```

### Step 3: Use Alongside Existing Strategies

```python
# Combine core and extended strategies seamlessly
from src.strategy_wrapper import MomentumStrategy, EqualWeightStrategy
from src.strategies_extended import MaximumDiversificationStrategy

strategies = {
    'Equal Weight': EqualWeightStrategy(strategy),
    'Momentum': MomentumStrategy(strategy, optimizer),
    'Max Diversification': MaximumDiversificationStrategy(strategy)
}

# Run backtests for all
results = {}
for name, strat in strategies.items():
    results[name] = portfolio.run_backtest(strat, rebalance_freq='M')
```

## Compatibility Matrix

| Component | Compatibility | Notes |
|-----------|---------------|-------|
| PortfolioEngine | ✅ Full | All extended strategies work seamlessly |
| PortfolioOptimizer | ✅ Full | Can be used by strategies that need optimization |
| Strategy | ✅ Full | All strategies use the same Strategy object |
| Data Loader | ✅ Full | No changes needed |
| Evaluator | ✅ Full | Metrics calculation works the same |
| Backtester (legacy) | ✅ Compatible | Via adapter layer |

## API Consistency

All strategies (core + extended) follow the same interface:

```python
class AnyStrategy(BaseStrategyWrapper):
    def __init__(self, strategy, optimizer=None, **params):
        super().__init__(name, strategy, optimizer, **params)
    
    def get_weights(self, date, portfolio_state) -> pd.Series:
        # Returns weights that sum to 1.0
        return weights
    
    def get_strategy_info(self) -> Dict[str, Any]:
        # Returns strategy metadata
        return info
```

## Example: Adding Extended Strategies to Existing Demo

### Before (Existing Code)
```python
# examples/my_demo.py
from src.strategy_wrapper import EqualWeightStrategy, MomentumStrategy

strategies = {
    'Equal': EqualWeightStrategy(strategy),
    'Momentum': MomentumStrategy(strategy, optimizer)
}

for name, strat in strategies.items():
    result = portfolio.run_backtest(strat)
    print(f"{name}: {result['sharpe_ratio']:.2f}")
```

### After (With Extended Strategies)
```python
# examples/my_demo.py
from src.strategy_wrapper import EqualWeightStrategy, MomentumStrategy
from src.strategies_extended import (
    MaximumDiversificationStrategy,
    MarkowitzMVOStrategy
)

strategies = {
    'Equal': EqualWeightStrategy(strategy),
    'Momentum': MomentumStrategy(strategy, optimizer),
    'Max Diversification': MaximumDiversificationStrategy(strategy),  # NEW
    'Markowitz': MarkowitzMVOStrategy(strategy, optimizer)  # NEW
}

for name, strat in strategies.items():
    result = portfolio.run_backtest(strat)
    print(f"{name}: {result['sharpe_ratio']:.2f}")
```

## Common Use Cases

### Use Case 1: Benchmark Comparison
```python
# Compare active strategies against buy & hold
from src.strategies_extended import BuyAndHoldStrategy

benchmark = BuyAndHoldStrategy(strategy)
active_strategy = MomentumStrategy(strategy, optimizer)

benchmark_result = portfolio.run_backtest(benchmark)
active_result = portfolio.run_backtest(active_strategy)

excess_return = active_result['total_return'] - benchmark_result['total_return']
print(f"Excess Return: {excess_return:.2%}")
```

### Use Case 2: Risk-Focused Portfolio
```python
# Combine risk-minimization strategies
from src.strategy_wrapper import GlobalMinimumVarianceStrategy
from src.strategies_extended import (
    MaximumDiversificationStrategy,
    MaximumDecorrelationStrategy
)

risk_strategies = {
    'GMVP': GlobalMinimumVarianceStrategy(strategy),
    'MDP': MaximumDiversificationStrategy(strategy),
    'MDCP': MaximumDecorrelationStrategy(strategy)
}

# Compare risk metrics
for name, strat in risk_strategies.items():
    result = portfolio.run_backtest(strat)
    print(f"{name} Volatility: {result['volatility']:.2%}")
```

### Use Case 3: Factor Investing
```python
# Implement factor portfolios
from src.strategies_extended import QuintileFactorStrategy

factors = {
    'Momentum': QuintileFactorStrategy(
        strategy, optimizer,
        factor='momentum',
        target_quintile=5
    ),
    'Mean Reversion': QuintileFactorStrategy(
        strategy, optimizer,
        factor='mean_reversion',
        target_quintile=1  # Bottom quintile
    ),
    'Low Volatility': QuintileFactorStrategy(
        strategy, optimizer,
        factor='volatility',
        target_quintile=5  # Highest inverse vol
    )
}
```

### Use Case 4: ML-Based Strategies
```python
# Compare different ML approaches
from src.strategy_wrapper import MLRandomForestStrategy
from src.strategies_extended import LinearRegressionStrategy

ml_strategies = {
    'Random Forest': MLRandomForestStrategy(strategy, optimizer),
    'Linear Regression': LinearRegressionStrategy(
        strategy, optimizer,
        regularization='ridge',
        alpha=0.1
    )
}
```

## Performance Considerations

### Memory Usage
- **Impact**: Minimal (< 10 MB additional)
- **Reason**: Strategies share same data objects

### Computation Time
- **Fast Strategies**: Buy & Hold, GMRP (< 1ms)
- **Medium Strategies**: Quintile, TS Momentum (< 10ms)
- **Slow Strategies**: MDP, MDCP, Markowitz (< 100ms)
- **ML Strategies**: Linear Regression (< 1s)

### Optimization
All strategies use the same optimization backend, so no performance regression.

## Testing Your Integration

### Quick Test
```python
# test_integration.py
from src.signal_generator import Strategy
from src.strategies_extended import MaximumDiversificationStrategy
from src.data_loader import load_data

# Load data
prices = load_data(start_date='2020-01-01', end_date='2023-12-31')

# Create strategy
strategy_obj = Strategy(prices)
mdp = MaximumDiversificationStrategy(strategy_obj)

# Test weight generation
test_date = strategy_obj.dates[-100]
weights = mdp.get_weights(test_date, None)

# Verify
assert abs(weights.sum() - 1.0) < 1e-6, "Weights don't sum to 1"
assert all(weights >= 0), "Negative weights found"
print("✅ Integration test passed!")
```

### Full Test Suite
```bash
# Run all tests including extended strategies
pytest tests/test_strategies_extended.py -v

# Run with coverage
pytest tests/test_strategies_extended.py --cov=src.strategies_extended
```

## Troubleshooting

### Issue: Import Error
```python
# Error: ModuleNotFoundError: No module named 'src.strategies_extended'

# Solution: Ensure file exists
import os
assert os.path.exists('src/strategies_extended.py')

# Or add to path
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
```

### Issue: Optimization Failures
```python
# Strategies automatically fallback to equal weights
# Check logs for warnings:
import logging
logging.basicConfig(level=logging.INFO)

# Run strategy
result = portfolio.run_backtest(strategy)
# Check logs for any "optimization failed" messages
```

### Issue: Incompatible Data
```python
# Ensure sufficient data
min_lookback = 252  # days
assert len(prices) >= min_lookback, f"Need at least {min_lookback} days"

# Ensure no NaN values
assert not prices.isna().any().any(), "NaN values in prices"
```

## Best Practices

### 1. Start Simple
```python
# Start with basic strategies
buy_hold = BuyAndHoldStrategy(strategy)
result = portfolio.run_backtest(buy_hold)

# Then add complexity
mdp = MaximumDiversificationStrategy(strategy)
```

### 2. Use Factory Functions
```python
# More maintainable
from src.strategies_extended import create_extended_strategy

strategy = create_extended_strategy(
    'maximum_diversification',
    strategy_obj,
    optimizer,
    lookback=252
)
```

### 3. Parameter Validation
```python
# Validate parameters before backtesting
lookback = 252
assert lookback <= len(prices), "Lookback too long"
assert lookback >= 20, "Lookback too short"

strategy = MaximumDiversificationStrategy(
    strategy_obj,
    lookback=lookback
)
```

### 4. Compare Against Benchmark
```python
# Always compare against buy & hold
benchmark = BuyAndHoldStrategy(strategy)
benchmark_result = portfolio.run_backtest(benchmark)

# Your strategy
active = YourStrategy(strategy)
active_result = portfolio.run_backtest(active)

# Information ratio
excess_return = active_result['total_return'] - benchmark_result['total_return']
tracking_error = np.std(active_result['returns'] - benchmark_result['returns'])
info_ratio = excess_return / tracking_error
```

## Documentation

- **Full Documentation**: `docs/STRATEGIES_EXTENDED.md`
- **Quick Reference**: `QUICK_REFERENCE_EXTENDED.md`
- **Examples**: `examples/demo_extended_strategies.py`
- **Tests**: `tests/test_strategies_extended.py`

## Support

### Getting Help
1. Check documentation: `docs/STRATEGIES_EXTENDED.md`
2. Run examples: `python examples/demo_extended_strategies.py`
3. Review tests: `tests/test_strategies_extended.py`
4. Check implementation: `IMPLEMENTATION_SUMMARY_EXTENDED.md`

### Reporting Issues
If you encounter issues:
1. Check if data is sufficient (min 30 days)
2. Verify parameters are reasonable
3. Run tests to ensure environment is correct
4. Check logs for warnings/errors

## Summary

✅ **Zero breaking changes** - all existing code works  
✅ **Seamless integration** - same API, same patterns  
✅ **Full compatibility** - works with all existing components  
✅ **Well-tested** - comprehensive test suite included  
✅ **Well-documented** - extensive docs and examples  

**You can start using extended strategies immediately!**

```python
# One line to get started
from src.strategies_extended import MaximumDiversificationStrategy
```

---

**Version**: 2.1.0  
**Date**: December 2, 2025  
**Status**: Production Ready ✅
