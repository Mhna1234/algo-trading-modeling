"""
Quick diagnostic to understand why the demo showed 0% returns.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from src.data_loader import load_preprocessed_data

print("=" * 80)
print("DIAGNOSTIC: Demo Results Investigation")
print("=" * 80)

# Load data exactly as the demo does
start_date = '2015-11-01'
end_date = '2024-12-31'

print(f"\n1. Loading data: {start_date} to {end_date}")
full_data, price_data = load_preprocessed_data(start=start_date, end=end_date)

print(f"   Shape: {price_data.shape}")
print(f"   Date range: {price_data.index.min()} to {price_data.index.max()}")
print(f"   Tickers: {list(price_data.columns[:5])}...")

# Check for actual price changes
print(f"\n2. Checking price changes:")
first_prices = price_data.iloc[0]
last_prices = price_data.iloc[-1]
returns = (last_prices / first_prices - 1) * 100

print(f"   First row (2015-11-30):")
print(f"      AAPL: ${first_prices['AAPL']:.2f}")
print(f"      MSFT: ${first_prices['MSFT']:.2f}")
print(f"\n   Last row:")
print(f"      AAPL: ${last_prices['AAPL']:.2f}")
print(f"      MSFT: ${last_prices['MSFT']:.2f}")
print(f"\n   Total returns:")
print(f"      AAPL: {returns['AAPL']:.1f}%")
print(f"      MSFT: {returns['MSFT']:.1f}%")

# Simulate simple buy and hold
print(f"\n3. Simulating Buy & Hold with $100,000:")
initial_capital = 100000
n_assets = len(price_data.columns)
equal_weights = 1.0 / n_assets

# Calculate portfolio value over time
portfolio_values = []
for idx in range(len(price_data)):
    current_prices = price_data.iloc[idx]
    relative_prices = current_prices / first_prices
    portfolio_value = initial_capital * (equal_weights * relative_prices).sum()
    portfolio_values.append(portfolio_value)

final_value = portfolio_values[-1]
portfolio_return = (final_value / initial_capital - 1) * 100

print(f"   Initial value: ${initial_capital:,.2f}")
print(f"   Final value: ${final_value:,.2f}")
print(f"   Total return: {portfolio_return:.2f}%")

# Check if data has actual variability
print(f"\n4. Data variability check:")
daily_returns = price_data.pct_change().dropna()
print(f"   Daily returns shape: {daily_returns.shape}")
print(f"   Mean daily return: {daily_returns.mean().mean():.6f}")
print(f"   Std daily return: {daily_returns.std().mean():.6f}")
print(f"   Any NaN values: {daily_returns.isna().any().any()}")
print(f"   All zeros: {(daily_returns == 0).all().all()}")

# Sample recent returns
print(f"\n5. Sample of recent daily returns (last 5 days, AAPL):")
print(daily_returns['AAPL'].tail())

print("\n" + "=" * 80)
print("CONCLUSION:")
print("=" * 80)
if portfolio_return > 1:
    print(f"✓ Data looks GOOD - portfolio should have {portfolio_return:.2f}% return")
    print("  Problem is likely in the backtesting engine or strategy implementation")
else:
    print(f"✗ Data looks BAD - portfolio only has {portfolio_return:.2f}% return")
    print("  Problem is in the data loading or filtering")
