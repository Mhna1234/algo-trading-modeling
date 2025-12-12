# Implementation Suggestions for Backtesting Logical Process

## Executive Summary

This document provides **actionable implementation suggestions** for integrating the [Backtesting Logical Process](BACKTESTING_LOGICAL_PROCESS.md) into the existing codebase. It analyzes current implementation, identifies gaps, and provides concrete code suggestions.

---

## Current Implementation Analysis

### What Exists ✅

#### 1. **Portfolio Engine** (`src/portfolio_engine.py`)

**Current Capabilities**:
- ✅ Position tracking with shares and weights
- ✅ Transaction cost calculation (commission + slippage)
- ✅ Daily portfolio return simulation
- ✅ Comprehensive metrics (Sharpe, Max DD, etc.)
- ✅ Rebalancing at arbitrary frequencies (D/W/M/Q)

**Key Methods**:
```python
PortfolioEngine._execute_rebalance(date, target_weights)
    - Calculates turnover
    - Applies transaction costs
    - Updates positions
```

**Gap**: NO soft rebalancing (always trades to target)

#### 2. **Strategy Wrappers** (`src/strategy_wrapper.py`)

**Current Capabilities**:
- ✅ 12 benchmark strategies implemented
- ✅ BaseStrategyWrapper interface
- ✅ Weight generation from signals
- ✅ Position limits (min/max weights)

**Example Strategies**:
- BuyAndHoldStrategy
- EqualWeightStrategy
- QuintileFactorStrategy
- MomentumStrategy
- RiskParityStrategy
- etc.

**Gap**: No exposure to soft rebalancing logic

#### 3. **Backtesting Methods** (`src/backtesting_methods.py`)

**Current Capabilities**:
- ✅ Walk-forward analysis
- ✅ Cross-validation
- ✅ Monte Carlo simulation
- ✅ Vanilla backtest

**Gap**: Not using soft rebalancing

#### 4. **Demos** (`examples/demo_12_strategies_fast.py`)

**Current Capabilities**:
- ✅ Runs all 12 strategies
- ✅ Compares performance
- ✅ Generates leaderboard

**Configuration**:
```python
# Current demo uses:
- Period: Last 6 months
- Rebalancing: Weekly (W)
- Initial capital: $100,000
```

**Gap**: Not using quarterly rebalancing or soft logic

---

## Gap Analysis

### Critical Missing Features

| Feature | Required | Current Status | Priority |
|---------|----------|----------------|----------|
| **Soft Rebalancing** | ✅ | ❌ Not implemented | 🔴 HIGH |
| **Quarterly Rebalancing** | ✅ | ✅ Supported (Q) | ✅ Done |
| **Drift Threshold Check** | ✅ | ❌ Not implemented | 🔴 HIGH |
| **10-Year Backtest** | ✅ | ⚠️ Possible but not default | 🟡 MEDIUM |
| **40 Quarters Loop** | ✅ | ⚠️ Implicit in Q freq | ✅ Done |
| **Weight Drift Tracking** | ✅ | ⚠️ Partial (turnover) | 🟡 MEDIUM |

---

## Implementation Suggestions

### Option 1: Minimal Changes (Recommended)

**Add Soft Rebalancing to PortfolioEngine**

#### Location: `src/portfolio_engine.py`

**Step 1**: Add drift threshold parameter to `__init__`:

```python
class PortfolioEngine:
    def __init__(
        self,
        prices: DataFrame,
        initial_capital: float = 1_000_000.0,
        transaction_cost_bps: float = 5.0,
        slippage_bps: float = 1.0,
        drift_threshold: float = 0.05,  # NEW: 5% drift threshold
        enable_soft_rebalance: bool = False,  # NEW: Toggle soft rebalancing
        benchmark_tickers: Optional[List[str]] = None,
        cash_symbol: str = 'CASH',
    ):
        # ... existing code ...
        self.drift_threshold = drift_threshold
        self.enable_soft_rebalance = enable_soft_rebalance
```

**Step 2**: Modify `_execute_rebalance` method:

```python
def _execute_rebalance(self, date: pd.Timestamp, target_weights: Series):
    """
    Execute rebalancing trades with costs and slippage.
    
    With soft rebalancing enabled, only trades assets where weight
    drift exceeds threshold.
    """
    # Get current prices
    current_prices = self._prices.loc[date]
    
    # Normalize target weights
    target_weights = target_weights.clip(lower=0)
    target_weights_sum = target_weights.sum()
    
    if target_weights_sum > 1.0:
        target_weights = target_weights / target_weights_sum
    
    # SOFT REBALANCING LOGIC (NEW)
    if self.enable_soft_rebalance:
        target_weights = self._apply_soft_rebalancing(target_weights)
    
    # ... rest of existing rebalancing logic ...
```

**Step 3**: Add new method `_apply_soft_rebalancing`:

```python
def _apply_soft_rebalancing(self, target_weights: Series) -> Series:
    """
    Apply soft rebalancing: only trade if drift > threshold.
    
    Parameters
    ----------
    target_weights : pd.Series
        Ideal target weights from strategy
        
    Returns
    -------
    pd.Series
        Adjusted weights (may equal current weights if no trade needed)
    """
    adjusted_weights = target_weights.copy()
    
    # Get current asset weights (excluding CASH)
    current_asset_weights = self._current_weights.drop(self.cash_symbol, errors='ignore')
    
    # For each asset in target weights
    for asset in target_weights.index:
        current_w = current_asset_weights.get(asset, 0.0)
        target_w = target_weights[asset]
        
        # Calculate drift
        drift = abs(target_w - current_w)
        
        # If drift below threshold, keep current weight (no trade)
        if drift <= self.drift_threshold:
            adjusted_weights[asset] = current_w
            
    return adjusted_weights
```

**Step 4**: Track drift metrics:

```python
def _execute_rebalance(self, date: pd.Timestamp, target_weights: Series):
    # ... existing code ...
    
    # NEW: Track drift before rebalancing
    if self.enable_soft_rebalance:
        current_asset_weights = self._current_weights.drop(self.cash_symbol, errors='ignore')
        
        drift_dict = {}
        trades_executed = 0
        
        for asset in target_weights.index:
            current_w = current_asset_weights.get(asset, 0.0)
            target_w = target_weights[asset]
            drift = abs(target_w - current_w)
            
            drift_dict[asset] = drift
            
            if drift > self.drift_threshold:
                trades_executed += 1
        
        # Store metrics
        self._soft_rebalance_stats[date] = {
            'assets_traded': trades_executed,
            'total_assets': len(target_weights),
            'max_drift': max(drift_dict.values()) if drift_dict else 0.0,
            'avg_drift': np.mean(list(drift_dict.values())) if drift_dict else 0.0
        }
```

---

### Option 2: Create Dedicated Soft Rebalancing Class

**New Module**: `src/soft_rebalancer.py`

```python
"""
Soft Rebalancing Module

Implements intelligent rebalancing logic that only trades when necessary,
reducing transaction costs while maintaining portfolio alignment.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class RebalanceDecision:
    """Decision about whether to rebalance each asset."""
    
    asset: str
    current_weight: float
    target_weight: float
    drift: float
    should_trade: bool
    trade_amount: float  # In dollars
    

class SoftRebalancer:
    """
    Soft rebalancing logic for portfolio management.
    
    Only executes trades when weight drift exceeds threshold,
    reducing unnecessary transactions and costs.
    """
    
    def __init__(self, drift_threshold: float = 0.05):
        """
        Initialize soft rebalancer.
        
        Parameters
        ----------
        drift_threshold : float
            Minimum weight drift to trigger rebalancing (default 5%)
        """
        self.drift_threshold = drift_threshold
        self.decisions_history = []
        
    def decide_trades(
        self,
        current_weights: pd.Series,
        target_weights: pd.Series,
        portfolio_value: float
    ) -> Tuple[pd.Series, List[RebalanceDecision]]:
        """
        Decide which assets to trade based on drift threshold.
        
        Parameters
        ----------
        current_weights : pd.Series
            Current portfolio weights
        target_weights : pd.Series
            Desired target weights
        portfolio_value : float
            Total portfolio value
            
        Returns
        -------
        adjusted_weights : pd.Series
            Final weights after soft rebalancing decision
        decisions : List[RebalanceDecision]
            Detailed decisions for each asset
        """
        adjusted_weights = target_weights.copy()
        decisions = []
        
        # Ensure all assets are considered
        all_assets = set(current_weights.index) | set(target_weights.index)
        
        for asset in all_assets:
            current_w = current_weights.get(asset, 0.0)
            target_w = target_weights.get(asset, 0.0)
            
            drift = abs(target_w - current_w)
            should_trade = drift > self.drift_threshold
            
            if should_trade:
                final_weight = target_w
                trade_amount = (target_w - current_w) * portfolio_value
            else:
                final_weight = current_w  # Keep current
                trade_amount = 0.0
                
            adjusted_weights[asset] = final_weight
            
            decisions.append(RebalanceDecision(
                asset=asset,
                current_weight=current_w,
                target_weight=target_w,
                drift=drift,
                should_trade=should_trade,
                trade_amount=trade_amount
            ))
        
        self.decisions_history.append(decisions)
        
        return adjusted_weights, decisions
    
    def get_statistics(self) -> Dict[str, float]:
        """Get summary statistics about rebalancing decisions."""
        if not self.decisions_history:
            return {}
        
        total_decisions = sum(len(d) for d in self.decisions_history)
        total_trades = sum(
            sum(1 for dec in decisions if dec.should_trade)
            for decisions in self.decisions_history
        )
        
        return {
            'total_rebalance_events': len(self.decisions_history),
            'total_assets_considered': total_decisions,
            'total_trades_executed': total_trades,
            'trade_rate': total_trades / total_decisions if total_decisions > 0 else 0,
            'avg_trades_per_rebalance': total_trades / len(self.decisions_history)
        }
```

**Integration**:

```python
# In PortfolioEngine.__init__
from .soft_rebalancer import SoftRebalancer

self.soft_rebalancer = SoftRebalancer(drift_threshold=0.05)

# In _execute_rebalance
if self.enable_soft_rebalance:
    adjusted_weights, decisions = self.soft_rebalancer.decide_trades(
        current_weights=self._current_weights.drop(self.cash_symbol, errors='ignore'),
        target_weights=target_weights,
        portfolio_value=self._current_equity
    )
    target_weights = adjusted_weights
```

---

### Option 3: Strategy-Level Control

**Alternative**: Let strategies decide when to rebalance.

**Modify BaseStrategyWrapper**:

```python
class BaseStrategyWrapper:
    """Base class for all strategy wrappers."""
    
    def should_rebalance(self, state: PortfolioState) -> bool:
        """
        Decide if rebalancing should occur at this date.
        
        Default: Always rebalance on scheduled dates.
        Override in subclass for custom logic (e.g., soft rebalancing).
        
        Parameters
        ----------
        state : PortfolioState
            Current portfolio state
            
        Returns
        -------
        bool
            True if should rebalance, False to skip
        """
        return True  # Default: always rebalance
    
    def get_weights(self, state: PortfolioState) -> pd.Series:
        """Generate target weights (abstract method)."""
        raise NotImplementedError
```

**Soft Rebalancing Strategy Mixin**:

```python
class SoftRebalancingMixin:
    """Mixin to add soft rebalancing logic to any strategy."""
    
    def __init__(self, *args, drift_threshold: float = 0.05, **kwargs):
        super().__init__(*args, **kwargs)
        self.drift_threshold = drift_threshold
        
    def should_rebalance(self, state: PortfolioState) -> bool:
        """Only rebalance if any asset drift exceeds threshold."""
        
        # Get target weights (without rebalancing)
        target_weights = self.get_weights(state)
        
        # Calculate drifts
        current_weights = state.current_weights.drop('CASH', errors='ignore')
        
        for asset in target_weights.index:
            current_w = current_weights.get(asset, 0.0)
            target_w = target_weights[asset]
            drift = abs(target_w - current_w)
            
            if drift > self.drift_threshold:
                return True  # At least one asset needs rebalancing
                
        return False  # No rebalancing needed


# Usage
class SoftMomentumStrategy(SoftRebalancingMixin, MomentumStrategy):
    """Momentum strategy with soft rebalancing."""
    pass
```

---

## Recommended Implementation Plan

### Phase 1: Add Soft Rebalancing to PortfolioEngine ✅

**Files to Modify**:
1. `src/portfolio_engine.py` - Add soft rebalancing logic
2. `src/utils.py` - Add drift_threshold to TradingConfig

**Changes**:
```python
# In utils.py
@dataclass
class TradingConfig:
    # ... existing fields ...
    drift_threshold: float = 0.05  # NEW
    enable_soft_rebalance: bool = False  # NEW
```

**Estimated Effort**: 2-3 hours

### Phase 2: Create 10-Year Quarterly Demo ✅

**New File**: `examples/demo_10year_quarterly.py`

```python
"""
Demo: 10-Year Quarterly Backtesting with Soft Rebalancing

Implements the full backtesting logical process:
- 10 years of data (2015-2025)
- Quarterly rebalancing (40 quarters)
- Soft rebalancing with 5% drift threshold
- All 12 benchmark strategies
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from datetime import datetime

from src.data_loader import load_preprocessed_data
from src.portfolio_engine import PortfolioEngine
from src.strategy_wrapper import (
    BuyAndHoldStrategy, EqualWeightStrategy,
    QuintileFactorStrategy, QuintileLowVolatilityStrategy,
    MeanReversionStrategy, GlobalMinimumVarianceStrategy,
    InverseVolatilityStrategy, RiskParityStrategy,
    MaximumDiversificationStrategy, MaximumDecorrelationStrategy,
    SharpeMaximizationStrategy, CVaRMinimizationStrategy
)


def main():
    print("=" * 60)
    print("10-YEAR QUARTERLY BACKTESTING (2015-2025)")
    print("=" * 60)
    
    # Load data
    print("\n[1/4] Loading 10 years of data...")
    prices = load_preprocessed_data(
        data_type='price',
        start_date='2015-01-01',
        end_date='2025-11-30'
    )
    
    # Configuration
    INITIAL_CAPITAL = 100_000.0
    REBALANCE_FREQ = 'Q'  # Quarterly
    DRIFT_THRESHOLD = 0.05  # 5%
    ENABLE_SOFT_REBALANCE = True
    
    print(f"\nConfiguration:")
    print(f"  Initial Capital: ${INITIAL_CAPITAL:,.0f}")
    print(f"  Period: {prices.index[0]} to {prices.index[-1]}")
    print(f"  Rebalance Frequency: Quarterly")
    print(f"  Soft Rebalancing: {ENABLE_SOFT_REBALANCE}")
    print(f"  Drift Threshold: {DRIFT_THRESHOLD * 100}%")
    
    # Initialize strategies
    print("\n[2/4] Initializing 12 strategies...")
    strategies = [
        BuyAndHoldStrategy(name="Buy & Hold"),
        EqualWeightStrategy(name="Equal Weight"),
        QuintileFactorStrategy(factor='momentum', name="Momentum Quintile"),
        QuintileLowVolatilityStrategy(name="Low Vol Quintile"),
        MeanReversionStrategy(name="Mean Reversion"),
        GlobalMinimumVarianceStrategy(name="Global Min Variance"),
        InverseVolatilityStrategy(name="Inverse Volatility"),
        RiskParityStrategy(name="Risk Parity"),
        MaximumDiversificationStrategy(name="Max Diversification"),
        MaximumDecorrelationStrategy(name="Max Decorrelation"),
        SharpeMaximizationStrategy(name="Sharpe Maximization"),
        CVaRMinimizationStrategy(name="CVaR Minimization")
    ]
    
    # Run backtests
    print("\n[3/4] Running backtests...")
    results = []
    
    for i, strategy in enumerate(strategies, 1):
        print(f"  [{i}/12] {strategy.name}...", end=" ")
        
        # Create portfolio engine with soft rebalancing
        portfolio = PortfolioEngine(
            prices=prices,
            initial_capital=INITIAL_CAPITAL,
            transaction_cost_bps=10.0,  # 0.1%
            slippage_bps=5.0,  # 0.05%
            drift_threshold=DRIFT_THRESHOLD,  # NEW
            enable_soft_rebalance=ENABLE_SOFT_REBALANCE  # NEW
        )
        
        # Run backtest
        result = portfolio.run_backtest(
            strategy_wrapper=strategy,
            start_date='2015-01-01',
            end_date='2025-11-30',
            rebalance_freq=REBALANCE_FREQ
        )
        
        results.append({
            'Strategy': strategy.name,
            'Sharpe': result.summary_metrics['sharpe_ratio'],
            'Return': result.summary_metrics['total_return'],
            'Max DD': result.summary_metrics['max_drawdown'],
            'Turnover': result.summary_metrics['avg_turnover']
        })
        
        print("✓")
    
    # Generate leaderboard
    print("\n[4/4] Generating leaderboard...")
    leaderboard = pd.DataFrame(results).sort_values('Sharpe', ascending=False)
    leaderboard['Rank'] = range(1, len(leaderboard) + 1)
    
    print("\n" + "=" * 80)
    print("STRATEGY LEADERBOARD (Sorted by Sharpe Ratio)")
    print("=" * 80)
    print(leaderboard.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    
    print("\n✓ Complete!")


if __name__ == "__main__":
    main()
```

**Estimated Effort**: 1-2 hours

### Phase 3: Add Drift Tracking Dashboard ✅

**Enhance PortfolioResult**:

```python
@dataclass
class PortfolioResult:
    # ... existing fields ...
    
    # NEW: Soft rebalancing metrics
    drift_history: Optional[pd.DataFrame] = None  # Date × Asset drift matrix
    rebalance_decisions: Optional[pd.DataFrame] = None  # Trade/Hold decisions
    soft_rebalance_stats: Optional[Dict] = None  # Summary stats
```

**Add visualization**:

```python
def plot_drift_analysis(result: PortfolioResult):
    """Plot weight drift over time and rebalancing decisions."""
    
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    
    # Plot 1: Maximum drift over time
    max_drift = result.drift_history.max(axis=1)
    axes[0].plot(max_drift, label='Max Drift')
    axes[0].axhline(y=0.05, color='r', linestyle='--', label='Threshold (5%)')
    axes[0].set_title('Maximum Weight Drift Over Time')
    axes[0].legend()
    
    # Plot 2: Number of trades per rebalance
    trades_per_rebalance = result.rebalance_decisions.sum(axis=1)
    axes[1].bar(trades_per_rebalance.index, trades_per_rebalance.values)
    axes[1].set_title('Assets Traded Per Rebalancing Event')
    
    # Plot 3: Cumulative transaction costs saved
    axes[2].plot(result.transaction_costs.cumsum(), label='With Soft Rebalancing')
    axes[2].set_title('Cumulative Transaction Costs')
    axes[2].legend()
    
    plt.tight_layout()
    plt.show()
```

**Estimated Effort**: 2-3 hours

---

## Testing Plan

### Unit Tests

```python
# tests/test_soft_rebalancing.py

import pytest
import pandas as pd
import numpy as np
from src.portfolio_engine import PortfolioEngine
from src.soft_rebalancer import SoftRebalancer


def test_soft_rebalancing_no_trade_when_below_threshold():
    """Test that no trade occurs when drift < threshold."""
    
    rebalancer = SoftRebalancer(drift_threshold=0.05)
    
    current_weights = pd.Series({'AAPL': 0.30, 'GOOGL': 0.30, 'MSFT': 0.40})
    target_weights = pd.Series({'AAPL': 0.32, 'GOOGL': 0.28, 'MSFT': 0.40})
    
    adjusted, decisions = rebalancer.decide_trades(
        current_weights, target_weights, portfolio_value=100000
    )
    
    # All drifts < 5%, so should keep current weights
    pd.testing.assert_series_equal(adjusted, current_weights)
    
    # No trades should be executed
    trades_count = sum(1 for d in decisions if d.should_trade)
    assert trades_count == 0


def test_soft_rebalancing_trade_when_above_threshold():
    """Test that trade occurs when drift > threshold."""
    
    rebalancer = SoftRebalancer(drift_threshold=0.05)
    
    current_weights = pd.Series({'AAPL': 0.30, 'GOOGL': 0.30, 'MSFT': 0.40})
    target_weights = pd.Series({'AAPL': 0.40, 'GOOGL': 0.30, 'MSFT': 0.30})
    # AAPL drift: |0.40 - 0.30| = 0.10 > 0.05 ✓ trade
    # GOOGL drift: |0.30 - 0.30| = 0.00 < 0.05 ✗ no trade
    # MSFT drift: |0.30 - 0.40| = 0.10 > 0.05 ✓ trade
    
    adjusted, decisions = rebalancer.decide_trades(
        current_weights, target_weights, portfolio_value=100000
    )
    
    # Should trade AAPL and MSFT, but not GOOGL
    assert adjusted['AAPL'] == 0.40  # Changed
    assert adjusted['GOOGL'] == 0.30  # Unchanged
    assert adjusted['MSFT'] == 0.30  # Changed
    
    trades_count = sum(1 for d in decisions if d.should_trade)
    assert trades_count == 2  # AAPL and MSFT


def test_quarterly_rebalancing():
    """Test that quarterly rebalancing generates correct dates."""
    
    prices = pd.DataFrame({
        'AAPL': np.random.randn(2520) + 100,  # ~10 years daily
        'GOOGL': np.random.randn(2520) + 100,
    }, index=pd.date_range('2015-01-01', periods=2520, freq='B'))
    
    portfolio = PortfolioEngine(prices, initial_capital=100000)
    
    dates = portfolio._get_rebalance_dates(
        start_date=pd.Timestamp('2015-01-01'),
        end_date=pd.Timestamp('2024-12-31'),
        freq='Q'
    )
    
    # Should be ~40 quarters in 10 years
    assert 38 <= len(dates) <= 42
    
    # Check that dates are quarter-end
    for date in dates:
        assert date.month in [3, 6, 9, 12] or date == dates[0] or date == dates[-1]
```

### Integration Tests

```python
# tests/test_full_backtest_10years.py

def test_10year_quarterly_backtest():
    """Full integration test of 10-year quarterly backtest."""
    
    # Load real data
    prices = load_preprocessed_data(start_date='2015-01-01', end_date='2024-12-31')
    
    # Create strategy
    strategy = EqualWeightStrategy()
    
    # Run backtest with soft rebalancing
    portfolio = PortfolioEngine(
        prices,
        initial_capital=100000,
        drift_threshold=0.05,
        enable_soft_rebalance=True
    )
    
    result = portfolio.run_backtest(
        strategy_wrapper=strategy,
        start_date='2015-01-01',
        end_date='2024-12-31',
        rebalance_freq='Q'
    )
    
    # Validate results
    assert result.summary_metrics['total_return'] > 0  # Positive return
    assert -1 < result.summary_metrics['max_drawdown'] < 0  # Valid drawdown
    assert result.summary_metrics['sharpe_ratio'] > 0  # Positive Sharpe
    
    # Check that soft rebalancing reduced trades
    assert result.soft_rebalance_stats['trade_rate'] < 0.8  # < 80% of potential trades
```

---

## Performance Considerations

### Current Performance

Based on `demo_12_strategies_fast.py`:
- **6 months, weekly rebalancing**: < 10 seconds
- **Estimated for 10 years, quarterly**: ~30-60 seconds

### Optimization Tips

1. **Vectorize Drift Calculations**:
```python
# Instead of loop
drifts = (target_weights - current_weights).abs()
trades_needed = drifts[drifts > threshold]
```

2. **Cache Rolling Metrics**:
```python
# Calculate once per quarter, not per asset
@lru_cache(maxsize=128)
def get_rolling_vol(date):
    return returns.loc[:date].tail(252).std()
```

3. **Parallel Strategy Execution**:
```python
from concurrent.futures import ProcessPoolExecutor

with ProcessPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(run_backtest, strategy) for strategy in strategies]
    results = [f.result() for f in futures]
```

---

## Validation Checklist

Before deployment, verify:

- [ ] Soft rebalancing correctly identifies drift > threshold
- [ ] Transaction costs only apply to actual trades (not skipped assets)
- [ ] Weights always sum to 1.0 (±1e-6)
- [ ] No negative positions (unless shorts explicitly enabled)
- [ ] Quarterly rebalancing generates ~40 events over 10 years
- [ ] Metrics match expected formulas (Sharpe, Max DD, etc.)
- [ ] Cash is handled correctly in weight calculations
- [ ] Edge cases handled (all assets below threshold, all above, etc.)
- [ ] Performance is acceptable (< 2 minutes for full demo)
- [ ] Results are reproducible (same seed → same results)

---

## Example Usage

### Basic Usage

```python
from src.portfolio_engine import PortfolioEngine
from src.strategy_wrapper import EqualWeightStrategy

# Load data
prices = load_preprocessed_data('2015-01-01', '2025-11-30')

# Create strategy
strategy = EqualWeightStrategy()

# Create portfolio with soft rebalancing
portfolio = PortfolioEngine(
    prices,
    initial_capital=100000,
    drift_threshold=0.05,  # 5% drift threshold
    enable_soft_rebalance=True
)

# Run 10-year quarterly backtest
result = portfolio.run_backtest(
    strategy_wrapper=strategy,
    start_date='2015-01-01',
    end_date='2025-11-30',
    rebalance_freq='Q'
)

# Print results
print(f"Sharpe Ratio: {result.summary_metrics['sharpe_ratio']:.2f}")
print(f"Total Return: {result.summary_metrics['total_return']:.2%}")
print(f"Max Drawdown: {result.summary_metrics['max_drawdown']:.2%}")
print(f"Trades Executed: {result.soft_rebalance_stats['total_trades_executed']}")
print(f"Trade Rate: {result.soft_rebalance_stats['trade_rate']:.1%}")
```

### Advanced Usage: Compare Soft vs Hard Rebalancing

```python
# Run with soft rebalancing
portfolio_soft = PortfolioEngine(prices, enable_soft_rebalance=True, drift_threshold=0.05)
result_soft = portfolio_soft.run_backtest(strategy, '2015-01-01', '2025-11-30', 'Q')

# Run without soft rebalancing
portfolio_hard = PortfolioEngine(prices, enable_soft_rebalance=False)
result_hard = portfolio_hard.run_backtest(strategy, '2015-01-01', '2025-11-30', 'Q')

# Compare
comparison = pd.DataFrame({
    'Metric': ['Sharpe', 'Return', 'Max DD', 'Turnover', 'Costs'],
    'Soft Rebalance': [
        result_soft.summary_metrics['sharpe_ratio'],
        result_soft.summary_metrics['total_return'],
        result_soft.summary_metrics['max_drawdown'],
        result_soft.summary_metrics['avg_turnover'],
        result_soft.summary_metrics['total_transaction_costs']
    ],
    'Hard Rebalance': [
        result_hard.summary_metrics['sharpe_ratio'],
        result_hard.summary_metrics['total_return'],
        result_hard.summary_metrics['max_drawdown'],
        result_hard.summary_metrics['avg_turnover'],
        result_hard.summary_metrics['total_transaction_costs']
    ]
})

print(comparison)
```

---

## Next Steps

1. ✅ Review this document with the team
2. ⏳ Implement Option 1 (Minimal Changes) - **Start here**
3. ⏳ Create unit tests for soft rebalancing
4. ⏳ Build `demo_10year_quarterly.py`
5. ⏳ Run validation tests
6. ⏳ Compare soft vs hard rebalancing performance
7. ⏳ Document results and insights
8. ⏳ Deploy to production

---

## Questions & Answers

**Q: Should soft rebalancing be default?**
A: No, make it opt-in via `enable_soft_rebalance=True`. This maintains backward compatibility.

**Q: What drift threshold should we use?**
A: Start with 5% (0.05). Can be tuned per strategy:
- Active strategies: 2-3%
- Passive strategies: 5-10%

**Q: Does this slow down backtesting?**
A: Negligible impact. Drift calculation is O(n) where n = number of assets (~10-20).

**Q: Can we use soft rebalancing with daily rebalancing?**
A: Yes, but it's less impactful. Soft rebalancing shines with lower frequencies (weekly/monthly/quarterly).

**Q: How do we handle new assets entering the portfolio?**
A: New asset has current_weight = 0, so drift = target_weight. If target_weight > threshold, trade is executed.

---

## References

- Current Implementation: `src/portfolio_engine.py`
- Logical Process: [BACKTESTING_LOGICAL_PROCESS.md](BACKTESTING_LOGICAL_PROCESS.md)
- Strategies: `src/strategy_wrapper.py`
- Demos: `examples/demo_12_strategies_fast.py`

---

**Document Version**: 1.0  
**Date**: December 12, 2025  
**Status**: Implementation Guide  
**Priority**: HIGH

