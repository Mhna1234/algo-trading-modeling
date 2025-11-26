"""
Quick test script to verify GMVP strategy implementation
"""
import numpy as np
import pandas as pd
from src.strategy import Strategy
from src.optimizer import PortfolioOptimizer
from src.strategy_wrapper import GlobalMinimumVarianceStrategy
from src.portfolio_engine import PortfolioState

print("="*80)
print("TESTING GMVP STRATEGY")
print("="*80)
print()

# Create synthetic price data
print("1. Creating synthetic price data...")
dates = pd.bdate_range('2020-01-01', '2023-12-31')
n_assets = 5
tickers = [f'ASSET_{i+1}' for i in range(n_assets)]

np.random.seed(42)
drifts = np.linspace(0.05, 0.15, n_assets) / 252
vols = np.linspace(0.15, 0.30, n_assets) / np.sqrt(252)

returns_data = pd.DataFrame(
    np.random.normal(loc=drifts, scale=vols, size=(len(dates), n_assets)),
    index=dates,
    columns=tickers
)

prices = 100 * (1 + returns_data).cumprod()
print(f"   ✓ Created {len(tickers)} assets with {len(prices)} price points")
print()

# Initialize strategy and optimizer
print("2. Initializing Strategy and Optimizer...")
strategy = Strategy(prices)
optimizer = PortfolioOptimizer(risk_free_rate=0.02)
print("   ✓ Strategy and Optimizer initialized")
print()

# Create GMVP strategy
print("3. Creating GMVP Strategy...")
gmvp_strategy = GlobalMinimumVarianceStrategy(
    strategy, 
    optimizer,
    lookback=252,
    use_integer_rebalance=False,
    max_weight=0.4
)
print(f"   ✓ GMVP Strategy created: {gmvp_strategy.name}")
print(f"   Parameters: {gmvp_strategy.params}")
print()

# Test weight generation
print("4. Testing weight generation...")
test_date = prices.index[300]  # Use a date after sufficient history

# Create a minimal PortfolioState for testing
portfolio_state = PortfolioState(
    date=test_date,
    current_weights=pd.Series(0.0, index=tickers),
    current_shares=pd.Series(0.0, index=tickers),
    cash=1_000_000,
    equity=1_000_000,
    price_history=prices.loc[:test_date],
    return_history=returns_data.loc[:test_date]
)

try:
    weights = gmvp_strategy.get_weights(test_date, portfolio_state)
    print(f"   ✓ Weights generated successfully!")
    print(f"\n   Generated weights:")
    for asset, weight in weights.items():
        print(f"      {asset}: {weight:.4f}")
    print(f"\n   Total weight sum: {weights.sum():.4f}")
    print(f"   Max weight: {weights.max():.4f}")
    print(f"   Min weight: {weights.min():.4f}")
    print()
    
    # Verify constraints
    print("5. Verifying constraints...")
    checks = []
    
    # Check sum to 1
    if abs(weights.sum() - 1.0) < 0.01:
        print("   ✓ Weights sum to approximately 1.0")
        checks.append(True)
    else:
        print(f"   ✗ Weights sum to {weights.sum():.4f} (should be 1.0)")
        checks.append(False)
    
    # Check non-negative
    if (weights >= 0).all():
        print("   ✓ All weights are non-negative")
        checks.append(True)
    else:
        print("   ✗ Some weights are negative")
        checks.append(False)
    
    # Check max weight constraint
    max_weight_param = gmvp_strategy.params['max_weight']
    if weights.max() <= max_weight_param + 0.01:
        print(f"   ✓ Max weight constraint satisfied ({weights.max():.4f} <= {max_weight_param})")
        checks.append(True)
    else:
        print(f"   ✗ Max weight constraint violated ({weights.max():.4f} > {max_weight_param})")
        checks.append(False)
    
    print()
    
    if all(checks):
        print("="*80)
        print("✓ ALL TESTS PASSED!")
        print("="*80)
    else:
        print("="*80)
        print("✗ SOME TESTS FAILED")
        print("="*80)
        
except Exception as e:
    print(f"   ✗ Error generating weights: {e}")
    import traceback
    traceback.print_exc()
    print()
    print("="*80)
    print("✗ TEST FAILED")
    print("="*80)

print()
print("GMVP Strategy Test Complete!")
print()
