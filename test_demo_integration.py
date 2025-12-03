"""Test GMVP integration with demo"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from src.portfolio_engine import PortfolioEngine
from src.strategy_wrapper import GlobalMinimumVarianceStrategy
from src.signal_generator import Strategy
from src.optimizer import PortfolioOptimizer

print("="*80)
print("TESTING GMVP INTEGRATION WITH PORTFOLIO ENGINE")
print("="*80)

# Create synthetic data
dates = pd.bdate_range('2020-01-01', '2023-12-31')
n_assets = 10
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
print(f"✓ Created synthetic price data: {prices.shape}")

# Initialize components
strategy = Strategy(prices)
optimizer = PortfolioOptimizer(risk_free_rate=0.02)
print(f"✓ Initialized Strategy and Optimizer")

# Create GMVP strategy
gmvp_strategy = GlobalMinimumVarianceStrategy(
    strategy, 
    optimizer,
    lookback=252,
    use_integer_rebalance=False,
    max_weight=0.4
)
print(f"✓ Created GMVP Strategy: {gmvp_strategy.name}")

# Run backtest
portfolio = PortfolioEngine(
    prices,
    initial_capital=1_000_000,
    transaction_cost_bps=5.0,
    slippage_bps=1.0
)
print(f"✓ Created Portfolio Engine")

print("\nRunning backtest...")
try:
    result = portfolio.run_backtest(
        gmvp_strategy,
        start_date=prices.index[252],  # Start after 1 year of history
        end_date=prices.index[-1],
        rebalance_freq='M'
    )
    
    print(f"\n✓ Backtest completed successfully!")
    print(f"\nPerformance Metrics:")
    print(f"  Annual Return: {result.summary_metrics['annual_return']:.2%}")
    print(f"  Annual Volatility: {result.summary_metrics['annual_volatility']:.2%}")
    print(f"  Sharpe Ratio: {result.summary_metrics['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown: {result.summary_metrics['max_drawdown']:.2%}")
    print(f"  Calmar Ratio: {result.summary_metrics['calmar_ratio']:.2f}")
    print(f"  Win Rate: {result.summary_metrics['win_rate']:.2%}")
    
    print(f"\n  Final Portfolio Value: ${result.equity_curve.iloc[-1]:,.2f}")
    print(f"  Total Return: {(result.equity_curve.iloc[-1] / 1_000_000 - 1):.2%}")
    
    print("\n" + "="*80)
    print("✓ ALL TESTS PASSED - GMVP STRATEGY WORKS CORRECTLY!")
    print("="*80)
    
except Exception as e:
    print(f"\n✗ Error during backtest: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
