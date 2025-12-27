# Risk-Free Asset Integration

## Overview

The risk-free asset integration allows the MAB (Multi-Armed Bandit) system to dynamically allocate capital between risky strategies and risk-free cash, enabling true portfolio optimization that can choose to be fully invested, partially invested, or entirely in cash.

## Architecture

### Two Key Components

#### 1. RiskFreeAsset Class
- **Purpose**: Manages risk-free rates and calculates daily returns
- **Features**:
  - FRED API integration for real-time Treasury rates
  - Local caching with weekend interpolation
  - Fallback rates for historical data
  - Daily compounding calculations
- **Not a strategy**: Pure rate management utility

#### 2. RiskFreeStrategyWrapper Class
- **Purpose**: Makes risk-free asset compatible with MAB framework
- **Inherits from**: `BaseStrategyWrapper` (same as all trading strategies)
- **Role**: Acts as an "arm" in the bandit allocation system

## How It Works

### In the MAB Framework
The bandit algorithm allocates capital across multiple **strategies** (arms). The risk-free asset is treated as just another strategy option:

```python
# Risk-free asset as one of the allocation choices
strategies = [
    MomentumStrategy(...),
    MeanReversionStrategy(...),
    RiskFreeStrategyWrapper(risk_free_asset)  # Cash option
]

bandit = BanditStrategyWrapper(strategies, UCBBandit(n_arms=3))
```

### Decision Making
The bandit learns to answer: *"Should I allocate to Momentum, Mean Reversion, or just hold cash?"*

- **High conviction periods**: Allocates heavily to best-performing strategies
- **Low conviction periods**: Allocates to risk-free asset (cash)
- **Risk-off periods**: May go 100% to cash

### Reward Calculation
- **Strategy rewards**: Risk-adjusted returns (Sharpe ratio)
- **Risk-free reward**: Current risk-free rate
- **Opportunity cost**: Automatically factored into strategy rewards

## Benefits

1. **Dynamic Risk Management**: System can reduce exposure during uncertain periods
2. **True Benchmark**: Compares strategies against risk-free alternative
3. **Portfolio Optimization**: Optimal mix of risky and risk-free assets
4. **Adaptive Allocation**: Learns when to be aggressive vs defensive

## Usage Example

```python
from src.risk_free_asset import RiskFreeAsset, RiskFreeStrategyWrapper
from src.bandits import UCBBandit
from src.strategies import BanditStrategyWrapper

# Create risk-free asset manager
rfa = RiskFreeAsset(rate_source='fred', maturity='3M')

# Wrap as strategy for MAB
cash_strategy = RiskFreeStrategyWrapper(rfa, "Risk-Free Cash")

# Include in bandit allocation
bandit_wrapper = BanditStrategyWrapper(
    child_strategies=[momentum, mean_rev, cash_strategy],
    bandit_allocator=UCBBandit(n_arms=3)
)
```

## Integration Points

- **Daily Trading Engine**: Automatically includes risk-free option
- **Portfolio Engine**: Handles cash allocation seamlessly
- **Checkpoint Manager**: Persists risk-free rate state
- **Data Pipeline**: Updates rates alongside market data

## Key Design Principles

1. **Separation of Concerns**: Rate management vs strategy interface
2. **MAB Compatibility**: Risk-free asset as just another arm
3. **Opportunity Cost**: Built into reward calculations
4. **Caching**: Efficient rate retrieval and storage
5. **Fallback Handling**: Robust operation without API access</content>
<parameter name="filePath">c:\Users\mhna2\projects\algo_trading_project\algo-trading-modeling\docs\RISK_FREE_ASSET_INTEGRATION.md