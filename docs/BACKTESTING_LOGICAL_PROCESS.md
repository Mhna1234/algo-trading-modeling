# Backtesting Logical Process

## Overview

This document outlines the **step-by-step logical process** for backtesting trading strategies with soft rebalancing, transaction costs, and comprehensive performance metrics. This is a **reference implementation guide** that defines the exact algorithmic flow for quarterly rebalancing over a 10-year period.

**Target Application**: Evaluating 12 benchmark strategies (policies 0-11) with realistic trading constraints.

---

## High-Level Algorithm

```
FOR each policy (0 to 11):
    
    Initialize:
    - portfolio_value = $100,000
    - current_positions = empty
    - current_weights = empty
    
    FOR each quarter (40 quarters over 10 years):
        
        1. GET SIGNALS
           - Retrieve policy's risk-adjusted returns for this date
           - Convert to target portfolio weights
           
        2. SOFT REBALANCING DECISION
           FOR each stock:
               weight_drift = |current_weight - target_weight|
               
               IF weight_drift > 5%:
                   → TRADE (buy/sell to reach target)
               ELSE:
                   → HOLD (no action)
        
        3. APPLY TRANSACTION COSTS
           FOR each trade:
               cost = trade_value × (0.001 + 0.0005)
               portfolio_value -= cost
        
        4. EXECUTE TRADES
           - Update positions to new levels
        
        5. HOLD FOR 3 MONTHS
           - Simulate daily returns based on market prices
           - Track daily portfolio value
           - Accumulate returns
        
        6. UPDATE STATE
           - Calculate new portfolio_value
           - Calculate new current_weights (positions drifted naturally)
    
    END quarter loop
    
    7. CALCULATE METRICS
       - Sharpe Ratio = mean(returns) / std(returns) × sqrt(252)
       - Max Drawdown = max(peak - trough) / peak
       - Win Rate = count(positive days) / total days
       - Profit Factor = sum(gains) / sum(losses)
       - Turnover Rate = average(quarterly turnover)
    
END policy loop

8. RANK POLICIES
   - Sort by Sharpe Ratio (primary)
   - Generate leaderboard
```

---

## Key Concepts to Implement

### 1. Soft Rebalancing Logic

**Concept**: Only trade when weight drift exceeds threshold to reduce transaction costs.

```python
current_weights = {"AAPL": 12%, "GOOGL": 8%, "MSFT": 18%}
target_weights =  {"AAPL": 10%, "GOOGL": 15%, "MSFT": 20%}

FOR each stock:
    drift = |current - target|
    
    IF drift > threshold (5%):
        trade_amount = (target - current) × portfolio_value
        execute_trade(trade_amount)
        apply_costs(trade_amount × 0.0015)
```

**Benefits**:
- Reduces unnecessary trading
- Lowers transaction costs
- Allows natural price drift
- More realistic trading simulation

**Parameters**:
- `drift_threshold`: Default 5% (0.05)
- Can be adjusted per strategy (e.g., 2% for active, 10% for passive)

---

### 2. Weight Conversion

**Process**: Convert risk-adjusted returns → portfolio weights

```python
FROM: Risk-adjusted returns
TO: Portfolio weights

Example:
AAPL: risk_adj_return = 0.0234
GOOGL: risk_adj_return = 0.0187
MSFT: risk_adj_return = -0.0052

Step 1: Filter positive only
    AAPL: 0.0234
    GOOGL: 0.0187
    (MSFT excluded - negative return)

Step 2: Normalize to sum to 1.0
    total = 0.0234 + 0.0187 = 0.0421
    AAPL: 0.0234 / 0.0421 = 0.556 (55.6%)
    GOOGL: 0.0187 / 0.0421 = 0.444 (44.4%)

Step 3: Apply limits (min 1%, max 20%)
    IF weight < 1%: set to 0% (too small)
    IF weight > 20%: clip to 20% (concentration limit)
    
    AAPL: 55.6% → 20.0% (clipped)
    GOOGL: 44.4% → 20.0% (clipped)

Step 4: Renormalize after clipping
    total = 20.0% + 20.0% = 40.0%
    AAPL: 20.0% / 40.0% = 50.0%
    GOOGL: 20.0% / 40.0% = 50.0%
    CASH: 0.0% (no cash in this example)
```

**Key Parameters**:
- `min_weight`: 0.01 (1%) - avoid dust positions
- `max_weight`: 0.20 (20%) - concentration limit
- `filter_negative`: True - only long positions

---

### 3. Transaction Cost Formula

**Complete Cost Model**:

```python
total_cost = |trade_value| × (commission_rate + slippage_rate)
           = |trade_value| × (0.001 + 0.0005)
           = |trade_value| × 0.0015
```

**Components**:

| Component | Value | Description |
|-----------|-------|-------------|
| Commission | 0.001 (0.1%) | Broker fees |
| Slippage | 0.0005 (0.05%) | Market impact |
| **Total** | **0.0015 (0.15%)** | **Combined cost** |

**Application**:
- Applied to **absolute value** of trades (buys + sells)
- Deducted from portfolio value immediately
- Tracked separately for reporting

**Example**:
```python
portfolio_value = $100,000
target_trade = $15,000 (buy)
cost = $15,000 × 0.0015 = $22.50
net_portfolio_value = $100,000 - $22.50 = $99,977.50
```

---

### 4. Performance Tracking

**During Holding Period** (Daily Simulation):

```python
FOR each trading day:
    daily_return = Σ(position_return × weight)
    cumulative_value = cumulative_value × (1 + daily_return)
```

**After Backtest** (Metrics Calculation):

```python
returns_series = [r1, r2, r3, ..., rN]

# Core Metrics
Sharpe = sqrt(252) × mean(returns) / std(returns)
Max_DD = min(all drawdowns from peaks)
Win_Rate = count(returns > 0) / N
Profit_Factor = sum(positive returns) / |sum(negative returns)|

# Risk Metrics
VaR_95 = percentile(returns, 5)
CVaR_95 = mean(returns where returns < VaR_95)
Sortino = sqrt(252) × mean(returns) / downside_deviation
```

**Metrics Definitions**:

| Metric | Formula | Description |
|--------|---------|-------------|
| **Sharpe Ratio** | $\frac{\sqrt{252} \cdot \mu}{\sigma}$ | Risk-adjusted return (annualized) |
| **Max Drawdown** | $\max\left(\frac{\text{Peak} - \text{Trough}}{\text{Peak}}\right)$ | Worst peak-to-trough decline |
| **Win Rate** | $\frac{\text{# Positive Days}}{\text{Total Days}}$ | Percentage of profitable days |
| **Profit Factor** | $\frac{\sum \text{Gains}}{\sum |\text{Losses}|}$ | Ratio of gains to losses |
| **Turnover** | $\frac{1}{T}\sum_{t=1}^{T} \sum_{i=1}^{N} |w_{i,t} - w_{i,t-1}|$ | Average portfolio churn |
| **Calmar Ratio** | $\frac{\text{Annual Return}}{\text{Max Drawdown}}$ | Return per unit of downside risk |
| **Sortino Ratio** | $\frac{\sqrt{252} \cdot \mu}{\text{Downside Dev}}$ | Risk-adjusted using downside vol |

---

## Detailed Step-by-Step Process

### Step 1: Initialize Portfolio

```python
# Portfolio State
portfolio_value = 100000.0  # $100k
current_positions = {}       # {"AAPL": 100 shares, ...}
current_weights = {}         # {"AAPL": 0.15, ...}
cash = portfolio_value       # All cash initially

# History Tracking
equity_curve = []
weights_history = []
returns_history = []
transaction_costs_history = []
turnover_history = []
```

### Step 2: Quarterly Rebalancing Loop

```python
FOR quarter in range(40):  # 10 years × 4 quarters
    
    rebalance_date = start_date + quarter * 3_months
    
    # A. Get target weights from strategy
    target_weights = strategy.get_weights(
        date=rebalance_date,
        current_state=portfolio_state
    )
    
    # B. Soft rebalancing decision
    trades_to_execute = {}
    
    FOR asset in all_assets:
        current_w = current_weights.get(asset, 0.0)
        target_w = target_weights.get(asset, 0.0)
        drift = abs(current_w - target_w)
        
        IF drift > DRIFT_THRESHOLD:  # e.g., 0.05 (5%)
            trades_to_execute[asset] = target_w
    
    # C. Execute trades with costs
    total_turnover = 0.0
    total_costs = 0.0
    
    FOR asset, target_weight in trades_to_execute.items():
        current_weight = current_weights.get(asset, 0.0)
        
        # Calculate trade size
        trade_dollars = (target_weight - current_weight) * portfolio_value
        total_turnover += abs(trade_dollars)
        
        # Calculate costs
        cost = abs(trade_dollars) * TRANSACTION_COST_RATE
        total_costs += cost
        
        # Update positions
        current_weights[asset] = target_weight
    
    # Deduct costs from portfolio
    portfolio_value -= total_costs
    
    # D. Hold for 3 months (simulate daily returns)
    FOR day in range(63):  # ~63 trading days per quarter
        
        daily_portfolio_return = 0.0
        
        FOR asset, weight in current_weights.items():
            asset_return = market_returns[asset][day]
            daily_portfolio_return += weight * asset_return
        
        # Update portfolio value
        portfolio_value *= (1 + daily_portfolio_return)
        
        # Record
        equity_curve.append(portfolio_value)
        returns_history.append(daily_portfolio_return)
    
    # E. Update weights (natural drift from price changes)
    FOR asset in current_weights.keys():
        position_value = current_positions[asset] * current_price[asset]
        current_weights[asset] = position_value / portfolio_value
    
    # F. Record quarterly metrics
    turnover_history.append(total_turnover / portfolio_value)
    transaction_costs_history.append(total_costs)

END quarter loop
```

### Step 3: Calculate Final Metrics

```python
# Convert to pandas Series
returns = pd.Series(returns_history)
equity = pd.Series(equity_curve)

# Performance Metrics
total_return = (equity.iloc[-1] / equity.iloc[0]) - 1
annual_return = (1 + total_return) ** (252 / len(returns)) - 1

sharpe_ratio = np.sqrt(252) * returns.mean() / returns.std()

# Drawdown calculation
cummax = equity.cummax()
drawdown = (equity - cummax) / cummax
max_drawdown = drawdown.min()

# Win metrics
win_rate = (returns > 0).sum() / len(returns)
profit_factor = returns[returns > 0].sum() / abs(returns[returns < 0].sum())

# Cost metrics
avg_turnover = np.mean(turnover_history)
total_costs = sum(transaction_costs_history)

# Risk metrics
var_95 = returns.quantile(0.05)
cvar_95 = returns[returns < var_95].mean()

downside_returns = returns[returns < 0]
downside_std = downside_returns.std()
sortino_ratio = np.sqrt(252) * returns.mean() / downside_std

calmar_ratio = annual_return / abs(max_drawdown)
```

---

## Implementation Guidelines

### Recommended Architecture

```
BacktestEngine
├── initialize_portfolio()
├── quarterly_rebalance_loop()
│   ├── get_target_weights()
│   ├── soft_rebalancing_decision()
│   ├── execute_trades_with_costs()
│   ├── simulate_holding_period()
│   └── update_weights()
├── calculate_metrics()
└── generate_report()
```

### Key Parameters

```python
# Portfolio Configuration
INITIAL_CAPITAL = 100_000.0
N_QUARTERS = 40  # 10 years

# Rebalancing
REBALANCE_FREQ = 'Q'  # Quarterly
DRIFT_THRESHOLD = 0.05  # 5%

# Costs
COMMISSION_RATE = 0.001  # 0.1%
SLIPPAGE_RATE = 0.0005  # 0.05%
TOTAL_COST_RATE = 0.0015  # 0.15%

# Weight Constraints
MIN_WEIGHT = 0.01  # 1%
MAX_WEIGHT = 0.20  # 20%

# Metrics
ANNUAL_TRADING_DAYS = 252
DAYS_PER_QUARTER = 63
```

### Validation Checks

```python
# After each rebalance
assert sum(current_weights.values()) <= 1.0 + 1e-6  # Allow small float error
assert all(w >= 0 for w in current_weights.values())  # No shorts
assert portfolio_value > 0  # Not bankrupt

# After each day
assert len(returns_history) == len(equity_curve)

# After backtest
assert len(turnover_history) == N_QUARTERS
assert all(sharpe_ratio is not None for strategy in strategies)
```

---

## Example Output Format

### Per-Strategy Report

```
Strategy: Momentum Quintile (Policy #3)
========================================

Portfolio Metrics:
  Initial Capital:        $100,000.00
  Final Value:            $247,532.19
  Total Return:           147.53%
  Annualized Return:      9.52%
  
Performance Metrics:
  Sharpe Ratio:           1.47
  Max Drawdown:           -18.32%
  Calmar Ratio:           0.52
  Sortino Ratio:          2.13
  
Win Metrics:
  Win Rate:               54.3%
  Profit Factor:          1.82
  Best Day:               +4.21%
  Worst Day:              -3.87%
  
Trading Metrics:
  Avg Quarterly Turnover: 23.4%
  Total Transactions:     156
  Transaction Costs:      $3,421.50
  Cost as % of Return:    2.3%
  
Risk Metrics:
  Volatility (Annual):    15.2%
  VaR (95%):             -1.89%
  CVaR (95%):            -2.76%
  Downside Deviation:     10.8%
```

### Leaderboard

```
STRATEGY LEADERBOARD (Sorted by Sharpe Ratio)
==============================================

Rank | Strategy                    | Sharpe | Return | Max DD | Turnover
-----|----------------------------|--------|--------|--------|----------
  1  | Risk Parity                | 1.82   | 12.4%  | -12.1% | 18.3%
  2  | Maximum Diversification    | 1.73   | 11.2%  | -13.8% | 21.7%
  3  | Momentum Quintile          | 1.47   | 9.5%   | -18.3% | 23.4%
  4  | Low Volatility Quintile    | 1.41   | 8.7%   | -11.2% | 15.8%
  5  | Sharpe Maximization        | 1.38   | 10.1%  | -16.4% | 28.9%
  6  | Equal Weight               | 1.29   | 8.9%   | -19.7% | 12.1%
  7  | CVaR Minimization          | 1.24   | 7.8%   | -13.5% | 19.4%
  8  | Inverse Volatility         | 1.18   | 7.2%   | -14.8% | 16.2%
  9  | Global Min Variance        | 1.15   | 6.8%   | -12.7% | 14.5%
 10  | Maximum Decorrelation      | 1.09   | 7.5%   | -17.2% | 22.8%
 11  | Mean Reversion Quintile    | 0.94   | 6.1%   | -21.4% | 26.3%
 12  | Buy & Hold                 | 0.87   | 8.2%   | -24.8% | 0.0%
```

---

## Mathematical Formulations

### Portfolio Value Evolution

$$V_t = V_{t-1} \times (1 + R_{p,t}) - TC_t$$

Where:
- $V_t$ = Portfolio value at time $t$
- $R_{p,t}$ = Portfolio return at time $t$
- $TC_t$ = Transaction costs at time $t$

### Portfolio Return

$$R_{p,t} = \sum_{i=1}^{N} w_{i,t-1} \times R_{i,t}$$

Where:
- $w_{i,t-1}$ = Weight of asset $i$ at time $t-1$
- $R_{i,t}$ = Return of asset $i$ at time $t$

### Transaction Costs

$$TC_t = \kappa \times \sum_{i=1}^{N} |w_{i,t} - w_{i,t-1}| \times V_{t-1}$$

Where:
- $\kappa$ = Total cost rate (0.0015)
- $|w_{i,t} - w_{i,t-1}|$ = Absolute weight change

### Soft Rebalancing Trigger

$$\text{Trade}_{i,t} = 
\begin{cases}
w_{i,t}^{\text{target}} & \text{if } |w_{i,t}^{\text{current}} - w_{i,t}^{\text{target}}| > \tau \\
w_{i,t}^{\text{current}} & \text{otherwise}
\end{cases}$$

Where:
- $\tau$ = Drift threshold (default 0.05)

### Sharpe Ratio

$$\text{Sharpe} = \sqrt{252} \times \frac{\bar{R}}{\sigma_R}$$

### Maximum Drawdown

$$\text{MaxDD} = \max_{t \in [0,T]} \left( \frac{\max_{s \in [0,t]} V_s - V_t}{\max_{s \in [0,t]} V_s} \right)$$

---

## References

- Markowitz, H. (1952). "Portfolio Selection". *Journal of Finance*.
- Sharpe, W.F. (1966). "Mutual Fund Performance". *Journal of Business*.
- Jegadeesh & Titman (1993). "Returns to Buying Winners and Selling Losers". *Journal of Finance*.
- Carhart, M.M. (1997). "On Persistence in Mutual Fund Performance". *Journal of Finance*.

---

## Document Version

- **Version**: 1.0
- **Date**: December 12, 2025
- **Author**: Algo Trading Team
- **Status**: Reference Implementation Guide

---

## Next Steps

1. Review current implementation in `src/portfolio_engine.py`
2. Identify gaps between current code and this specification
3. Implement soft rebalancing logic
4. Add quarterly rebalancing support
5. Validate with 12 benchmark strategies
6. Generate comprehensive reports

---

*For implementation details, see [IMPLEMENTATION_SUGGESTIONS.md](IMPLEMENTATION_SUGGESTIONS.md)*
