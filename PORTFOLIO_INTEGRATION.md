# Portfolio Class Integration

The algorithmic trading system has been enhanced with a powerful new Portfolio class that provides advanced backtesting and optimization capabilities.

## New Features

### Portfolio Class (`src/portfolio.py`)
- **Comprehensive Backtesting**: Built-in transaction costs, slippage, and rebalancing logic
- **Multiple Optimization Methods**: Tangency portfolio, target return MVO, and risk parity
- **Flexible Rule System**: Easy creation of custom portfolio construction rules
- **Cash Management**: Explicit modeling of cash positions with risk-free returns
- **Performance Analytics**: Comprehensive risk and return metrics

### Integration Components (`src/portfolio_adapter.py`)
- **ForecastPortfolioAdapter**: Integrates ARIMA-GARCH forecasting with Portfolio optimization
- **SignalPortfolioAdapter**: Converts existing signals to Portfolio rules
- **BacktesterAdapter**: Provides backward compatibility with existing code
- **ConfigurationAdapter**: Handles parameter translation

## Usage

### Basic Portfolio Usage
```python
from src.portfolio import Portfolio
import pandas as pd

# Load price data
prices = pd.read_csv('prices.csv', index_col=0, parse_dates=True)

# Initialize Portfolio
portfolio = Portfolio(
    prices=prices,
    rf=0.02/252,  # 2% annual risk-free rate (daily)
    trading_cost_bps=10.0,  # 10 basis points trading costs
    slippage_bps=2.0  # 2 basis points slippage
)

# Create equal weight strategy
equal_weight_rule = portfolio.equal_weight_rule()
weights = portfolio.build_target_weights_from_rule(
    rule=equal_weight_rule,
    schedule='M'  # Monthly rebalancing
)

# Run backtest
result = portfolio.rebalance(weights, initial_equity=100000)
print(f"Annual Return: {result.perf['ann_return']:.2%}")
print(f"Sharpe Ratio: {result.perf['sharpe']:.3f}")
```

### Integration with Existing System

The new Portfolio class is fully integrated with the existing pipeline. By default, it replaces the old backtester:

```bash
# Use new Portfolio class (default)
python main.py --tickers AAPL MSFT SPY --start 2020-01-01 --end 2024-01-01

# Use legacy backtester
python main.py --use-legacy-backtester --tickers AAPL MSFT SPY
```

### Configuration

New configuration options in `TradingConfig`:

```python
config = TradingConfig()

# Portfolio-specific settings
config.use_portfolio_class = True  # Use new Portfolio class
config.slippage_bps = 2.0  # Slippage in basis points
config.cash_symbol = "CASH"  # Cash position symbol
config.long_only = True  # Enforce long-only constraint
config.leverage_cap = 1.0  # Maximum leverage
config.ridge_regularization = 1e-4  # Ridge parameter for optimization
```

## Benefits

### Reduced Dependencies
The Portfolio class eliminates the need for external optimization libraries:
- ❌ `cvxpy` (optional)
- ❌ `PyPortfolioOpt` (optional)
- ✅ Pure numpy/pandas implementation

### Enhanced Functionality
- More robust transaction cost modeling
- Better handling of cash positions
- Flexible optimization methods without external solvers
- Comprehensive performance analytics
- Rule-based portfolio construction

### Backward Compatibility
- Existing code continues to work unchanged
- Gradual migration path available
- Legacy backtester still available via command line flag

## Testing

Run the integration test suite:

```bash
python test_portfolio_integration.py
```

This will test:
- Portfolio class functionality
- Adapter compatibility
- End-to-end pipeline integration
- Performance calculations
- Configuration handling

## Migration Guide

### For Existing Users

1. **No Action Required**: The system defaults to using the new Portfolio class with full backward compatibility.

2. **To Use Legacy System**: Add `--use-legacy-backtester` flag or set `config.use_portfolio_class = False`.

3. **Custom Optimization**: Replace direct optimizer calls with Portfolio methods:
   ```python
   # Old way
   weights = optimizer.optimize_portfolio_forecasted(...)
   
   # New way
   weights = portfolio.tangency_weights(...)
   # or
   weights = portfolio.target_return_mvo(target_return=0.12, ...)
   ```

### For Advanced Users

Create custom portfolio rules:

```python
def custom_rule(date, past_returns):
    # Your custom logic here
    weights = calculate_custom_weights(past_returns)
    return pd.Series(weights, index=portfolio.assets)

# Use the rule
target_weights = portfolio.build_target_weights_from_rule(
    rule=custom_rule,
    schedule='W',  # Weekly rebalancing
    lookback=60
)
```

## Performance Comparison

The new Portfolio class typically provides:
- **Better Performance**: More efficient backtesting engine
- **More Accurate**: Proper transaction cost and slippage modeling
- **More Flexible**: Easy creation of custom strategies
- **Less Dependencies**: Reduced external package requirements

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

2. **Memory Usage**: For large datasets, the Portfolio class is more memory-efficient than the legacy system.

3. **Performance Differences**: Results may differ slightly due to more accurate cost modeling in the new system.

### Getting Help

1. Run the test suite to identify integration issues
2. Check the logs for detailed error messages
3. Use the legacy backtester as a fallback during transition
4. Review the adapter code for customization examples

## Future Enhancements

Planned improvements:
- Additional optimization methods (Black-Litterman, etc.)
- Real-time portfolio monitoring
- Enhanced risk management features
- Integration with live trading APIs
- Performance attribution analysis