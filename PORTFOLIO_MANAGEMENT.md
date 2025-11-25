# Portfolio Management System

**Last Updated:** November 2025

The algorithmic trading system features a comprehensive portfolio management system that integrates forecasting, signals, and backtesting into a unified, production-ready framework.

## New Features

### Portfolio Class (`src/portfolio.py`)
- **Comprehensive Backtesting**: Built-in transaction costs, slippage, and rebalancing logic
- **Multiple Optimization Methods**: Tangency portfolio, target return MVO, and risk parity
- **Flexible Rule System**: Easy creation of custom portfolio construction rules
- **Cash Management**: Explicit modeling of cash positions with risk-free returns
- **Performance Analytics**: Comprehensive risk and return metrics (Sharpe, Sortino, Calmar, CAGR)
- **Pure Python Implementation**: No external optimization library dependencies required
- **Efficient Computation**: Optimized for large-scale backtesting

### Integration Components (`src/portfolio_manager.py`)
- **ConfigManager**: Central configuration management system
- **ForecastManager**: Integrates ARIMA-GARCH forecasting with portfolio optimization
- **SignalManager**: Converts trading signals to portfolio weights
- **PortfolioBacktester**: Production-ready backtesting with full analytics
- **Seamless Integration**: Drop-in replacement maintaining backward compatibility

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

The new portfolio management system is fully integrated with the existing pipeline:

```python
from src.portfolio_manager import PortfolioBacktester, ForecastManager, ConfigManager
from src.portfolio import Portfolio
from src.utils import TradingConfig

# Configuration
config = TradingConfig()
config.tickers = ['AAPL', 'MSFT', 'SPY']
config.use_portfolio_class = True  # Use new system (default)

# Run with new system
backtester = PortfolioBacktester(config)
results = backtester.run_backtest(price_data, weight_data, benchmark_data)
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

## Visualization Tools

The system includes comprehensive visualization capabilities:

```bash
# Run portfolio visualization dashboard
python visualize_portfolio.py
```

This creates:
- **Equity Curves**: Portfolio performance vs benchmark with annotations
- **Weight Allocation**: Stacked area charts and average weights
- **Risk Analytics**: Drawdowns, rolling volatility, rolling Sharpe ratio
- **Trading Activity**: Turnover and cumulative trading analysis
- **Correlation Analysis**: Asset correlation matrices and rolling correlations
- **Monthly Returns Heatmap**: Year-month performance visualization

All visualizations are saved as high-resolution PNG files (300 DPI).

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
- Optimization methods
- Rebalancing logic

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
    """
    Custom portfolio construction rule.
    
    Args:
        date: Current rebalancing date
        past_returns: DataFrame of historical returns (lookback period)
    
    Returns:
        pd.Series: Target weights for each asset
    """
    # Example: Inverse volatility weighting
    volatility = past_returns.std()
    inv_vol = 1 / volatility
    weights = inv_vol / inv_vol.sum()
    
    return pd.Series(weights, index=portfolio.assets)

# Use the rule
target_weights = portfolio.build_target_weights_from_rule(
    rule=custom_rule,
    schedule='W',  # Weekly rebalancing
    lookback=60
)
```

### Advanced Optimization Techniques

```python
# 1. Tangency portfolio (maximum Sharpe ratio)
tangency_weights = portfolio.tangency_weights(
    mu=expected_returns,
    Sigma=cov_matrix,
    ridge=1e-4  # Regularization for numerical stability
)

# 2. Target return optimization
target_weights = portfolio.target_return_mvo(
    target_return=0.12,  # 12% target annual return
    mu=expected_returns,
    Sigma=cov_matrix,
    ridge=1e-4
)

# 3. Risk parity (equal risk contribution)
risk_parity_weights = portfolio.risk_parity_weights(
    Sigma=cov_matrix,
    ridge=1e-4
)
```

### Best Practices

1. **Cost Modeling**: Always include realistic transaction costs (10-20 bps typical)
2. **Rebalancing Frequency**: Monthly or quarterly for most strategies (reduces turnover)
3. **Regularization**: Use ridge parameter (~1e-4) for numerical stability
4. **Lookback Periods**: 60-252 days for covariance estimation depending on strategy
5. **Cash Allocation**: Enable cash positions for more realistic backtests
6. **Slippage**: Include 2-5 bps slippage for realistic execution modeling

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