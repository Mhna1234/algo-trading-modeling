
import pandas as pd
import numpy as np
import logging

def test_cleaning_logic():
    print("Loading debug_prices.csv...")
    try:
        prices = pd.read_csv('debug_prices.csv', index_col='date', parse_dates=True)
    except FileNotFoundError:
        print("debug_prices.csv not found. Please run debug_flat_equity.py first.")
        return

    print(f"Original shape: {prices.shape}")
    
    # Simulate Lambda Logic
    # 1. Drop delisted (all NaNs)
    prices = prices.dropna(axis=1, how='all')
    print(f"After dropna(axis=1, how='all'): {prices.shape}")

    # 2. Drop >10% missing
    missing_pct_per_stock = prices.isna().sum() / len(prices)
    stocks_with_sufficient_data = missing_pct_per_stock[missing_pct_per_stock < 0.10].index
    prices = prices[stocks_with_sufficient_data]
    print(f"After filtering <10% missing: {prices.shape}")
    
    # 3. FFill limit 5
    prices = prices.ffill(limit=5)
    print(f"After ffill(limit=5): {prices.shape}")
    
    # 4. Drop rows with ANY NaNs
    prices_dropped = prices.dropna(how='any')
    print(f"After dropna(how='any'): {prices_dropped.shape}")
    
    if len(prices_dropped) < 200:
        print("CRITICAL: Massive data loss detected matching user observation!")
    else:
        print("Logic seems safe. Data loss is minimal.")

if __name__ == "__main__":
    test_cleaning_logic()
