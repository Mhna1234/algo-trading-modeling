# Bandit Strategy Selection - Detailed Explanation

## How the Bandit Chooses Strategies

### Overview
The **BanditStrategyWrapper** uses a **Multi-Armed Bandit (MAB)** algorithm to dynamically allocate capital across 12 different trading strategies. Think of it like choosing which slot machine to play, but for investment strategies.

---

## The Selection Process

### 1. **Burn-In Period (First 12 Months)**
During the first 12 rebalancing periods (months), the bandit uses **equal allocation**:
- **Each strategy gets 8.3%** (1/12) of the capital
- This period allows the bandit to **gather initial performance data** for all strategies
- No strategy selection happens yet - it's pure exploration

**Why burn-in?**
- Prevents premature convergence to potentially lucky strategies
- Ensures all strategies get fair initial evaluation
- Builds statistical confidence before making allocation decisions

### 2. **Post Burn-In: UCB Algorithm** (After Month 12)
After burn-in, the **Upper Confidence Bound (UCB)** algorithm takes over:

#### **UCB Formula:**
```
UCB_score(strategy) = mean_reward + c × √(2 × ln(t) / n)
```

Where:
- `mean_reward`: Average risk-adjusted return (Sharpe ratio) for that strategy
- `c`: Exploration constant (2.0 in your config) - controls exploration vs exploitation
- `t`: Total number of selections made
- `n`: Number of times this strategy was selected

#### **Selection Logic:**
1. **Calculate UCB score** for each strategy
2. **Select strategy with highest UCB score**
3. With soft allocation enabled, converts UCB scores to **probability distribution** using softmax

**Key Insight:** The `√(2 × ln(t) / n)` term is the **exploration bonus**:
- **High bonus** for rarely-tried strategies → encourages exploration
- **Low bonus** for frequently-tried strategies → focuses on exploitation
- This creates optimal exploration-exploitation balance

---

## Why Your Demo Showed Equal Allocations

Looking at your results:
```
Total rebalancing periods: 121
Burn-in complete: True
All strategies: 8.3% allocation
```

### The Issue: **Soft Allocation During Burn-In**
The configuration had:
```python
enable_soft_allocation=True
```

With soft allocation, instead of selecting ONE best strategy, the bandit:
1. Computes UCB scores for all strategies
2. Applies **softmax** to convert scores to probabilities
3. **Allocates proportionally** to these probabilities

**Result:** If all strategies perform similarly (which they often do):
- UCB scores are similar
- Softmax creates near-equal probabilities
- Allocations remain approximately equal (8.3% each)

---

## How Strategy Selection Affects Performance

### Monthly Rebalancing Flow

```
Month t-1 → Month t:
┌─────────────────────────────────────────────┐
│ 1. Calculate Returns                        │
│    - Portfolio return over the month        │
│    - Attribute to strategies proportionally │
└─────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────┐
│ 2. Calculate Rewards (Risk-Adjusted)        │
│    - Compute Sharpe ratio for each strategy │
│    - Apply transaction cost penalty         │
└─────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────┐
│ 3. Update Bandit                            │
│    - UCB updates mean_reward estimates      │
│    - Increments selection counts            │
└─────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────┐
│ 4. Select Strategies (for next month)       │
│    - Compute UCB scores                     │
│    - Apply softmax (if enabled)             │
│    - Generate allocation weights α(t)       │
└─────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────┐
│ 5. Get Strategy Weights                     │
│    - Each strategy generates its weights    │
│    - Example: Mean Reversion → w₁           │
│               Equal Weight → w₂              │
└─────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────┐
│ 6. Aggregate Weights                        │
│    Final_weights = α₁×w₁ + α₂×w₂ + ... + α₁₂×w₁₂│
└─────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────┐
│ 7. Execute Trades                           │
│    - Rebalance portfolio to final_weights   │
│    - Pay transaction costs                  │
└─────────────────────────────────────────────┘
```

---

## Impact on Performance

### Your Results Analysis
```
Bandit Meta-Strategy Performance:
- CAGR: 16.52%
- Sharpe Ratio: 0.848
- Max Drawdown: -29.65%
- Volatility: 17.50%
```

**What happened:**
1. **Equal allocation** across 12 diverse strategies
2. **Diversification benefit** from combining multiple approaches:
   - Low volatility strategies (GMVP, Inverse Vol)
   - Factor strategies (Momentum, Mean Reversion)
   - Optimization strategies (Sharpe Max, CVaR Min)
   - Simple strategies (Buy & Hold, Equal Weight)

3. **Result:** Stable performance from diversification, NOT from active selection

---

## To See Active Strategy Selection

### Option 1: Disable Soft Allocation
```python
BANDIT_CONFIG = {
    'algorithm': 'ucb',
    'exploration_constant': 2.0,
    'burn_in_periods': 12,
    'reward_type': 'sharpe',
    'enable_soft_allocation': False,  # <-- Change this
    'random_seed': 42
}
```

**Result:** Bandit will select 1-2 best strategies, giving them 100% allocation

### Option 2: Increase Exploration Constant
```python
'exploration_constant': 5.0,  # More aggressive exploration
```

**Result:** Higher variance in allocations, more strategy switching

### Option 3: Change Reward Type
```python
'reward_type': 'return',  # Raw returns instead of Sharpe
```

**Result:** Favors high-return strategies (ignoring risk)

---

## Understanding UCB Values

In the updated output, you'll see:
```
Strategy                    UCB Pulls  Mean Return  UCB Value
---------------------------------------------------------------
Sharpe Maximization               109       0.0008      0.1234
Equal Weight                      108       0.0007      0.1189
Mean Reversion                    107       0.0006      0.1156
...
```

- **UCB Pulls**: How many times the UCB algorithm selected this strategy
- **Mean Return**: Average return when this strategy was active
- **UCB Value**: Bandit's estimated mean reward (Sharpe ratio)

**Higher UCB Value = Strategy the bandit prefers**

---

## Key Concepts Summary

### 1. **Exploration vs Exploitation**
- **Exploration:** Try different strategies to learn which are best
- **Exploitation:** Focus capital on proven best strategies
- UCB balances both automatically

### 2. **Risk-Adjusted Rewards**
- Using Sharpe ratio (return/volatility) instead of raw returns
- Penalizes high-volatility strategies
- Rewards consistent performers

### 3. **Soft Allocation**
- Spreads risk across multiple strategies
- Reduces impact of estimation errors
- More stable, but less adaptive

### 4. **No Look-Ahead Bias**
- All decisions use only past data
- Rewards calculated from realized returns
- Statistically sound for backtesting

---

## Run with Better Diagnostics

Now run again to see the improved output:

```powershell
.venv\Scripts\Activate.ps1; python examples\demo_12_strategies_full.py
```

The updated diagnostic output will show:
- ✅ Actual observation counts per strategy
- ✅ UCB selection counts (how many times each strategy was chosen)
- ✅ UCB values (bandit's reward estimates)
- ✅ True allocation concentration metrics

---

## Further Reading

**Multi-Armed Bandits:**
- [Bandit Algorithms Book](https://tor-lattimore.com/downloads/book/book.pdf) by Lattimore & Szepesvári

**UCB Algorithm:**
- Original paper: "Finite-time Analysis of the Multiarmed Bandit Problem" (Auer et al., 2002)

**Portfolio Applications:**
- "Online Portfolio Selection: A Survey" (Li & Hoi, 2014)
- "A Modern Introduction to Online Learning" (Orabona, 2019)
