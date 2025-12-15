"""
Minimal test to debug Equal Weight strategy returns
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_loader import load_preprocessed_data
from src.signal_generator import Strategy
from src.strategies import EqualWeightStrategy
from src.portfolio_engine import PortfolioEngine

# Load data
print("Loading data...")
_, prices = load_preprocessed_data(start='2015-11-30', end='2024-12-31')
print(f"Data: {prices.shape[0]} days, {prices.shape[1]} tickers")
print(f"Date range: {prices.index[0]} to {prices.index[-1]}")

# Check actual price changes
print(f"\nPrice changes:")
print(f"  AAPL: ${prices['AAPL'].iloc[0]:.2f} -> ${prices['AAPL'].iloc[-1]:.2f} ({(prices['AAPL'].iloc[-1]/prices['AAPL'].iloc[0]-1)*100:+.1f}%)")
print(f"  MSFT: ${prices['MSFT'].iloc[0]:.2f} -> ${prices['MSFT'].iloc[-1]:.2f} ({(prices['MSFT'].iloc[-1]/prices['MSFT'].iloc[0]-1)*100:+.1f}%)")

# Create strategy
print("\nCreating Equal Weight strategy...")
strategy = Strategy(prices)
equal_weight = EqualWeightStrategy(strategy)

# Run backtest
print("\nRunning backtest...")
engine = PortfolioEngine(
    prices=prices,
    initial_capital=100000,
    transaction_cost_bps=0.0,
    slippage_bps=0.0
)

result = engine.run_backtest(
    strategy_wrapper=equal_weight,
    rebalance_freq='M',  # Monthly to make it faster
    start_date='2015-11-30',
    end_date='2024-12-31'
)

# Check results
print(f"\nResults:")
print(f"  Initial value: $100,000.00")
print(f"  Final value: ${result.equity_curve.iloc[-1]:,.2f}")
print(f"  Total return: {(result.equity_curve.iloc[-1]/100000-1)*100:+.2f}%")
print(f"  Sharpe ratio: {result.summary_metrics.get('sharpe_ratio', 0):.2f}")

# Check if weights were applied
print(f"\nWeight check (first rebalance):")
first_weights = result.weights_history.iloc[0]
print(first_weights[first_weights > 0])

print(f"\nEquity curve sample:")
print(result.equity_curve.head(10))
print("...")
print(result.equity_curve.tail(10))
