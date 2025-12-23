# MAB Risk-Free Asset & Rebalancing Architecture Plan

## Implementation Status Summary
**Status:** ✅ 4/5 Phases Complete (December 2025)  
**Risk-Free Asset:** Fully implemented with dynamic FRED API rates  
**Rebalancing:** Modular scheduler with global/per-strategy control  
**Transaction Costs:** Centralized modeling with opportunity cost  
**Testing:** ⚠️ Needs comprehensive test suite  

---

## Motivation

- Enhance portfolio realism and flexibility by introducing a configurable risk-free asset (cash/money-market).
- Enable explicit, modular control over rebalancing frequency at both global and per-strategy levels.
- Ensure transaction costs and opportunity costs (vs. risk-free) are consistently and transparently handled.
- Support robust, extensible architecture for future research and production deployment.

---

## Current-State Summary (Post-Implementation)

- **Strategies**: Multiple portfolio strategies (heuristic, risk-based, optimized) implemented as arms.
- **MAB Layer**: Allocates capital across strategies; strategies act as arms.
- **Rewards**: Risk-adjusted (Sharpe, volatility-penalized, transaction-cost aware) with opportunity cost vs. risk-free.
- **Rebalancing**: Modular control with RebalancingScheduler supporting global and per-strategy frequencies.
- **Transaction Costs**: Centralized in TransactionCostModel with consistent application.
- **Cash/Risk-Free Asset**: ✅ Fully implemented - RiskFreeAsset class with dynamic rates, can be used as arm or base asset.

---

## Deep Code Review (Post-Implementation Findings)

- **Allocation Decisions**:  
  - Made in PortfolioEngine with BanditAllocator integration
  - Support for both full investment and unallocated capital flowing to risk-free
- **Rebalancing Triggers**:  
  - ✅ RebalancingScheduler handles global and per-strategy rebalancing
  - Two-stage rebalancing: Global → Bandit allocation → Per-strategy rebalancing
- **Reward Computation**:  
  - ✅ Rewards include risk-adjustment, transaction costs, and opportunity cost vs. risk-free
  - Centralized in rewards.py with configurable risk-free rate
- **Fully Invested Assumptions**:  
  - ✅ Broken: PortfolioEngine supports unallocated capital
  - Risk-free can be used as base asset or as an arm
- **Cash Concept**:  
  - ✅ Implemented: RiskFreeAsset class with dynamic rate updates
- **Rebalancing Frequency**:  
  - ✅ Modular: RebalancingScheduler with per-strategy frequency support

---

## Gap Analysis (Post-Implementation)

**✅ All Major Gaps Filled:**
- **Missing Abstractions**:
  - ✅ RiskFreeAsset class implemented
  - ✅ RebalancingScheduler abstraction implemented
  - ✅ TransactionCostModel centralized
- **Tight Couplings**:
  - ✅ Allocation and rebalancing logic decoupled via scheduler
  - ✅ Two-stage rebalancing implemented
- **Assumptions Broken**:
  - ✅ Fully invested capital: unallocated capital flows to risk-free
  - ✅ Static rebalancing: global and per-strategy schedules supported
  - ✅ Hard-coded rates: dynamic/configurable risk-free rates

**Remaining Minor Gaps:**
- ⚠️ Comprehensive test coverage for new abstractions
- ⚠️ Empirical validation of risk-free as arm vs. base asset trade-offs

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

### Phase 1: Abstraction & Decoupling ✅ COMPLETED
**Status:** Implemented and integrated into PortfolioEngine  
**Completion Date:** December 2025

- ✅ Refactor to decouple allocation, rebalancing, and reward logic.
- ✅ Introduce abstract interfaces for Strategy, TransactionCostModel, and RebalancingScheduler.
- ✅ PortfolioEngine now accepts TransactionCostModel and RebalancingScheduler as parameters
- ✅ Concrete implementations: LinearTransactionCostModel, SimpleRebalancingScheduler

### Phase 2: Risk-Free Asset Integration ✅ COMPLETED
**Status:** Fully implemented with dynamic rates and demo  
**Completion Date:** December 2025

- ✅ Implement RiskFreeAsset class with FRED API integration
- ✅ Add support for dynamic rate retrieval and config fallback
- ✅ Refactor allocation logic to allow for unallocated capital
- ✅ RiskFreeStrategyWrapper for treating risk-free as an arm
- ✅ Demo script (demo_risk_free_integration.py) showing integration
- ✅ Comparison results available (demo_rfa_comparison.csv)

### Phase 3: Rebalancing Enhancements ✅ COMPLETED
**Status:** Two-stage rebalancing supported  
**Completion Date:** December 2025

- ✅ Implement RebalancingScheduler for global and per-strategy control
- ✅ SimpleRebalancingScheduler supports different frequencies (D, W, M, Q)
- ✅ Per-strategy rebalancing frequency configuration
- ✅ Two-stage rebalancing architecture: Global → Bandit → Per-Strategy

### Phase 4: Transaction & Opportunity Cost Consistency ✅ COMPLETED
**Status:** Centralized and opportunity cost included  
**Completion Date:** December 2025

- ✅ Centralize transaction cost logic in TransactionCostModel
- ✅ Update reward attribution to include opportunity cost vs. risk-free in rewards.py
- ✅ Sharpe ratio calculations account for risk-free rate
- ✅ Transaction costs applied consistently across rebalancing

### Phase 5: Configurability & Testing 🔄 PARTIALLY COMPLETED
**Status:** Configurable but testing incomplete  
**Current Status:** December 2025

- ✅ Add configuration options for risk-free modeling (arm vs. base asset), rates, and rebalancing schedules
- ✅ Risk-free rate sources: FRED API, config, fallback
- ✅ Rebalancing frequencies configurable per strategy
- ⚠️ Develop comprehensive tests for new abstractions and logic (NOT YET IMPLEMENTED)
- ⚠️ No dedicated test files for RiskFreeAsset, TransactionCostModel, RebalancingScheduler

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

**Implementation Status: 4/5 Phases Complete**  
This plan has been successfully implemented with all core functionality in place. The MAB portfolio allocation framework now supports risk-free assets, modular rebalancing control, and consistent transaction/opportunity cost handling. The architecture provides the flexibility and extensibility needed for research and production deployment.

**Key Achievements:**
- ✅ Complete risk-free asset integration with dynamic FRED API rates
- ✅ Modular rebalancing scheduler supporting global and per-strategy frequencies  
- ✅ Centralized transaction cost modeling
- ✅ Opportunity cost adjustments in reward calculations
- ✅ Two-stage rebalancing architecture implemented
- ✅ Demo scripts and comparison results available

**Remaining Work:**
- ⚠️ Comprehensive test suite for new abstractions (Phase 5 incomplete)

The approach successfully balances flexibility, testability, and research needs while addressing the identified trade-offs and risks.

---
