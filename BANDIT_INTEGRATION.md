# Bandit Wrapper Integration Guide

## Overview

The BanditStrategyWrapper has been integrated into the main demo scripts with full backwards compatibility. The integration uses a feature flag approach that allows users to enable bandit-based strategy selection without affecting existing benchmark outputs.

## Files Modified

1. **examples/demo_12_strategies_full.py**
   - Added bandit wrapper imports
   - Added `USE_BANDIT_WRAPPER` feature flag
   - Added `BANDIT_CONFIG` configuration dict
   - Added `print_bandit_summary()` function for detailed reporting
   - Modified backtest execution to support bandit wrapper path

2. **examples/demo_benchmark_strategies.py**
   - Added bandit wrapper imports
   - Added `USE_BANDIT_WRAPPER` feature flag
   - Added `BANDIT_CONFIG` configuration dict
   - Added `print_bandit_summary()` function for detailed reporting
   - Modified backtest execution to support bandit wrapper path

## Feature Flag Configuration

```python
USE_BANDIT_WRAPPER = False  # Set to True to enable bandit-based strategy selection

BANDIT_CONFIG = {
    'algorithm': 'ucb',  # 'ucb' or 'thompson'
    'exploration_constant': 2.0,  # For UCB algorithm
    'burn_in_periods': 10,  # Equal allocation during burn-in
    'reward_type': 'sharpe',  # 'return', 'sharpe', or 'sortino'
    'enable_soft_allocation': True,  # Use soft allocation (probabilistic)
    'random_seed': 42  # For reproducibility (Thompson Sampling)
}
```

## Usage

### Running with Individual Strategies (Default)

```bash
python examples/demo_12_strategies_full.py
python examples/demo_benchmark_strategies.py
```

Runs all strategies individually and compares performance (existing behavior).

### Running with Bandit Wrapper

1. Edit the demo file and set `USE_BANDIT_WRAPPER = True`
2. Configure `BANDIT_CONFIG` as desired
3. Run the demo:

```bash
python examples/demo_12_strategies_full.py
```

## Output Format

When bandit wrapper is enabled, the output includes:

### 1. Current Strategy Allocations α(t)
Shows the final allocation to each strategy with visual bar chart:
```
Strategy A                               45.3% ████████████████████████
Strategy B                               32.1% ████████████████
Strategy C                               22.6% ███████████
```

### 2. Arm Performance Summary
Detailed statistics for each strategy:
- **Selections**: Number of times strategy was selected
- **Mean Reward**: Average reward received
- **Selection %**: Percentage of total selections

Example:
```
Strategy                                  Selections    Mean Reward   Selection %
--------------------------------------------------------------------------------
Equal Weight                                      45         0.0234        31.0%
Momentum                                          38         0.0189        26.2%
GMVP                                              32         0.0156        22.1%
```

### 3. Allocation Statistics
- Total rebalancing periods
- Burn-in periods completed
- Allocation concentration (Herfindahl index)
  - 1.0 = fully concentrated on one strategy
  - 1/n = equally distributed across n strategies

### 4. Turnover Impact (if available)
- Average monthly turnover
- Estimated transaction costs

## Backwards Compatibility

- When `USE_BANDIT_WRAPPER = False`, the demos run exactly as before
- All existing outputs, plots, and metrics are preserved
- No changes to existing benchmark comparison logic
- Feature can be toggled without code changes (just config)

## Configuration Options

### Algorithm Selection
- **UCB (Upper Confidence Bound)**
  - Deterministic
  - Exploration controlled by `exploration_constant`
  - Good for balanced exploration/exploitation
  
- **Thompson Sampling**
  - Bayesian/probabilistic
  - Naturally balances exploration/exploitation
  - Requires `random_seed` for reproducibility

### Reward Types
- **return**: Raw returns (simple, fast)
- **sharpe**: Risk-adjusted returns (Sharpe ratio)
- **sortino**: Downside risk-adjusted returns

### Allocation Modes
- **Soft allocation** (True): Probabilistic selection based on bandit probabilities
- **Hard allocation** (False): Winner-take-all allocation

## Implementation Notes

1. **Monthly Rebalancing**: When bandit wrapper is enabled, rebalancing defaults to monthly ('M') instead of daily to reduce transaction costs

2. **Transaction Costs**: Bandit wrapper backtest uses 0.1% (10 bps) transaction costs to accurately reflect turnover impact

3. **Burn-in Period**: During burn-in, all strategies receive equal allocation (1/n) to gather initial performance data

4. **State Persistence**: The bandit wrapper maintains full state that can be serialized/deserialized (see `src/bandit_strategy_wrapper.py` for `get_state()`/`set_state()` methods)

## Example Output

```
================================================================================
BANDIT WRAPPER PERFORMANCE SUMMARY
================================================================================

1. Current Strategy Allocations α(t):
--------------------------------------------------------------------------------
  Equal Weight                             38.5% ███████████████████
  Momentum                                 24.3% ████████████
  GMVP                                     18.2% █████████
  Inverse Volatility                       12.1% ██████
  Mean Reversion                            6.9% ███

2. Arm Performance Summary:
--------------------------------------------------------------------------------
Strategy                                  Selections    Mean Reward   Selection %
--------------------------------------------------------------------------------
  Equal Weight                                      52         0.0245        35.9%
  Momentum                                          38         0.0198        26.2%
  GMVP                                              29         0.0167        20.0%
  Inverse Volatility                                18         0.0134        12.4%
  Mean Reversion                                     8         0.0089         5.5%

3. Allocation Statistics:
--------------------------------------------------------------------------------
Total rebalancing periods: 108
Burn-in periods completed: 10
Current allocation concentration (HHI): 0.289
  (1.0 = fully concentrated, 0.200 = equally distributed)
================================================================================
```

## Testing

To verify the integration:

1. Run demos with `USE_BANDIT_WRAPPER = False` - should work as before
2. Run demos with `USE_BANDIT_WRAPPER = True` - should show bandit summary
3. Check that metrics DataFrame is correctly populated in both modes
4. Verify plots are generated correctly in both modes

## Future Enhancements

- Add allocation history plots showing α(t) over time
- Include turnover analysis in bandit summary
- Add regime-specific reporting (if regime detection is used)
- Export bandit diagnostics to CSV/JSON for further analysis
