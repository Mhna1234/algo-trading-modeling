# MAB Risk-Free Asset & Rebalancing Architecture Plan

## Motivation

- Enhance portfolio realism and flexibility by introducing a configurable risk-free asset (cash/money-market).
- Enable explicit, modular control over rebalancing frequency at both global and per-strategy levels.
- Ensure transaction costs and opportunity costs (vs. risk-free) are consistently and transparently handled.
- Support robust, extensible architecture for future research and production deployment.

---

## Current-State Summary

- **Strategies**: Multiple portfolio strategies (heuristic, risk-based, optimized) implemented as arms.
- **MAB Layer**: Allocates capital across strategies; strategies act as arms.
- **Rewards**: May be risk-adjusted (Sharpe, volatility-penalized, transaction-cost aware).
- **Rebalancing**: Logic exists, but frequency control and separation of global/strategy-specific rebalancing may be limited.
- **Transaction Costs**: Accounted for in some reward calculations.
- **Cash/Risk-Free Asset**: No explicit risk-free asset; capital is assumed to be fully invested in risky strategies.

---

## Deep Code Review (Read-Only Findings)

- **Allocation Decisions**:  
  - Typically made in the MAB or portfolio engine layer (see src/portfolio_engine.py, src/backtester.py).
  - Allocations are distributed across strategies, often assuming full investment.
- **Rebalancing Triggers**:  
  - Rebalancing is likely triggered at fixed intervals (global), with some strategies possibly having internal logic.
  - No explicit abstraction for per-strategy rebalancing frequency.
- **Reward Computation**:  
  - Rewards are computed post-allocation, may include risk-adjustment and transaction costs.
  - Opportunity cost (vs. risk-free) is not explicitly modeled.
- **Fully Invested Assumptions**:  
  - Implicit throughout: capital is always allocated to risky strategies; no explicit cash buffer or risk-free asset.
- **Cash Concept**:  
  - No explicit cash or risk-free asset abstraction.
- **Rebalancing Frequency**:  
  - No clear, modular location for per-strategy rebalancing frequency; likely handled globally or ad hoc.

---

## Gap Analysis

- **Missing Abstractions**:
  - No risk-free asset or cash module/class.
  - No abstraction for rebalancing schedule (global vs. per-strategy).
  - Transaction cost logic may be scattered or tightly coupled to reward computation.
- **Tight Couplings**:
  - Allocation and rebalancing logic may be intertwined, making it hard to introduce two-stage rebalancing.
  - Assumption of full investment blocks easy integration of a risk-free asset.
- **Assumptions to Break**:
  - Fully invested capital: must allow for unallocated capital to flow to risk-free asset.
  - Static rebalancing: must support both global and per-strategy schedules.
  - Hard-coded rates: risk-free rate must be dynamic/configurable.

---

## Target Architecture (Conceptual)

### Key Modules & Responsibilities

- **PortfolioEngine**
  - Orchestrates allocation, rebalancing, and reward evaluation.
  - Holds references to all strategies, risk-free asset, and bandit allocator.

- **Strategy (Abstract)**
  - Interface for all trading strategies (arms).
  - Methods: `rebalance()`, `get_weight()`, `evaluate_reward()`, `get_rebalancing_frequency()`

- **RiskFreeAsset**
  - Represents cash/money-market.
  - Methods: `get_daily_return()`, `update_rate()`
  - Rate source: dynamic (FRED API), fallback to config.

- **BanditAllocator**
  - Decides capital allocation across arms (strategies + optionally risk-free).
  - Methods: `allocate(weights, rewards)`, `update(reward_feedback)`

- **TransactionCostModel**
  - Abstracts transaction cost logic.
  - Methods: `calculate_cost(trade_amount, asset)`

- **RebalancingScheduler**
  - Manages global and per-strategy rebalancing schedules.

#### Two-Stage Rebalancing

```
[Global Rebalancer] ---> [Bandit Allocator] ---> [Per-Strategy Rebalancer]
```

- Stage 1: Bandit decides allocations at global rebalancing points.
- Stage 2: Each strategy (and risk-free) runs its own rebalancing logic if due.

#### Risk-Free Asset Modeling

- **As an Arm**: Treated like any other strategy; bandit can allocate to it directly.
- **As Base Asset**: Residual capital flows to risk-free after bandit allocates to risky arms.

---

## Design Decisions & Trade-Offs

- **Risk-Free as Arm vs. Base Asset**
  - *Arm*: Unified allocation logic, bandit can learn to prefer cash in bad regimes, but may distort learning.
  - *Base Asset*: Bandit focuses on risky strategies; risk-free is a default, but less flexible.
  - **Recommendation**: Support both via configuration.

- **Rebalancing Control**
  - Explicit, modular control over both global and per-strategy rebalancing frequencies.
  - Rebalancing logic should be decoupled from allocation logic.

- **Transaction Costs**
  - Centralize transaction cost logic for consistency and extensibility.
  - Ensure all reward calculations account for both transaction and opportunity costs.

- **Risk-Free Rate Source**
  - Prefer dynamic retrieval (e.g., FRED API).
  - Fallback to user-configurable parameter.

---

## Phased Implementation Plan

### Phase 1: Abstraction & Decoupling

- Refactor to decouple allocation, rebalancing, and reward logic.
- Introduce abstract interfaces for Strategy, TransactionCostModel, and RebalancingScheduler.

### Phase 2: Risk-Free Asset Integration

- Implement RiskFreeAsset class.
- Add support for dynamic rate retrieval and config fallback.
- Refactor allocation logic to allow for unallocated capital.

### Phase 3: Rebalancing Enhancements

- Implement RebalancingScheduler for global and per-strategy control.
- Ensure two-stage rebalancing is supported.

### Phase 4: Transaction & Opportunity Cost Consistency

- Centralize transaction cost logic.
- Update reward attribution to include opportunity cost vs. risk-free.

### Phase 5: Configurability & Testing

- Add configuration options for risk-free modeling (arm vs. base asset), rates, and rebalancing schedules.
- Develop comprehensive tests for new abstractions and logic.

---

## Risks & Open Questions

- **Data Availability**: Dynamic risk-free rate retrieval may fail; robust fallback and error handling needed.
- **Bandit Learning**: Modeling risk-free as an arm may bias learning; requires empirical validation.
- **Legacy Code**: Existing tight couplings may complicate refactoring; incremental migration recommended.
- **Performance**: More granular rebalancing and cost modeling may impact backtest speed.
- **Opportunity Cost Attribution**: Requires careful design to avoid double-counting or misattribution.

---

## ASCII Diagram: Target Architecture

```
+-------------------+
|   PortfolioEngine |
+-------------------+
   |        |      |
   v        v      v
[Bandit] [RiskFree][Strategy*]
   |        |      |
   +--------+------+
            |
   [RebalancingScheduler]
            |
   [TransactionCostModel]
```

---

## Summary

This plan provides a modular, extensible path to integrating a risk-free asset, explicit rebalancing control, and robust transaction/opportunity cost handling into the MAB portfolio allocation framework. The approach balances flexibility, testability, and research needs, while highlighting key trade-offs and risks for future development.

---
