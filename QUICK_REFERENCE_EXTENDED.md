# Quick Reference Guide - Extended Strategies

## Installation

```bash
# All dependencies already in requirements.txt
pip install -r requirements.txt
```

## Import Strategies

```python
# Import all extended strategies
from src.strategies_extended import (
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

# Or use factory function
from src.strategies_extended import create_extended_strategy

strategy = create_extended_strategy(
    'maximum_diversification',
    strategy_obj,
    optimizer,
    lookback=252
)
```

## Quick Examples

### Buy & Hold
```python
buy_hold = BuyAndHoldStrategy(strategy_obj, initial_method='equal')
result = portfolio.run_backtest(buy_hold, rebalance_freq='M')
```

### Quintile Momentum
```python
quintile = QuintileFactorStrategy(
    strategy_obj, optimizer,
    factor='momentum',
    target_quintile=5,  # Top 20%
    equal_weight_quintile=True
)
```

### Maximum Diversification
```python
mdp = MaximumDiversificationStrategy(
    strategy_obj,
    lookback=252,
    max_weight=0.3
)
```

### Time-Series Momentum
```python
ts_mom = TimeSeriesMomentumStrategy(
    strategy_obj, optimizer,
    lookback=126,
    volatility_scaling=True
)
```

### Markowitz MVO
```python
markowitz = MarkowitzMVOStrategy(
    strategy_obj, optimizer,
    risk_aversion=2.0,
    return_forecast_method='momentum'
)
```

## Strategy Comparison

| Strategy | When to Use | Complexity | Turnover |
|----------|-------------|------------|----------|
| Buy & Hold | Benchmarking | Very Low | Very Low |
| Quintile Factor | Factor investing | Low | Medium |
| GMRP | Max return | Low | High |
| MDP | Risk management | Medium | Low |
| MDCP | Correlation hedging | Medium | Low |
| TS Momentum | Trend following | Low | Medium |
| MA Crossover | Simple trends | Very Low | Low |
| Markowitz | Balanced approach | Medium | Medium |
| Linear Regression | ML prediction | Medium | Medium |

## Parameter Guidelines

### Lookback Windows
- **Short-term**: 20-60 days (tactical)
- **Medium-term**: 126 days (6 months, default)
- **Long-term**: 252 days (1 year)

### Risk Parameters
- **max_weight**: 0.2-0.5 (concentration control)
- **risk_aversion**: 0.5-5.0 (lower = more aggressive)

### Rebalancing Frequency
- **High turnover strategies**: Weekly ('W') or Bi-weekly ('2W')
- **Low turnover strategies**: Monthly ('M') or Quarterly ('Q')

## Running Examples

```bash
# Demo all extended strategies
python examples/demo_extended_strategies.py

# Run tests
pytest tests/test_strategies_extended.py -v

# With coverage
pytest tests/test_strategies_extended.py --cov=src.strategies_extended
```

## Common Issues

### Issue: Optimization fails
**Solution**: Strategies automatically fallback to equal weights

### Issue: Insufficient data
**Solution**: Reduce lookback window or ensure min 30 days of data

### Issue: Extreme weights
**Solution**: Reduce max_weight parameter (try 0.3 or lower)

## Documentation

- **Full docs**: `docs/STRATEGIES_EXTENDED.md`
- **Implementation summary**: `IMPLEMENTATION_SUMMARY_EXTENDED.md`
- **Core strategies**: `docs/STRATEGIES.md`

## Support

- Run examples: `python examples/demo_extended_strategies.py`
- Run tests: `pytest tests/test_strategies_extended.py -v`
- Check docs: `docs/STRATEGIES_EXTENDED.md`

---

**Version**: 2.1.0  
**Last Updated**: December 2, 2025
