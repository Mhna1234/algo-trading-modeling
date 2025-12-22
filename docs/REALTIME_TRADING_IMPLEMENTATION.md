
# Daily Online Decision-Making System Implementation Plan

## 1️⃣ Architectural Overview

**High-Level System Diagram:**

```
┌──────────────┐   ┌──────────────┐   ┌────────────────────┐   ┌──────────────┐
│  Scheduler   │──▶│ Orchestrator │──▶│ PortfolioEngine    │──▶│ Persistence  │
│ (cron/Cloud) │   │ (New Layer)  │   │ (Unchanged)        │   │ (Parquet/CSV)│
└──────────────┘   └──────────────┘   └────────────────────┘   └──────────────┘
        │                │                    │                      │
        │                ▼                    │                      │
        │        ┌────────────────────┐       │                      │
        │        │ TradingDayContext  │       │                      │
        │        └────────────────────┘       │                      │
        │                │                    │                      │
        │                ▼                    │                      │
        │        ┌────────────────────┐       │                      │
        │        │ DecisionArtifact   │       │                      │
        │        └────────────────────┘       │                      │
        │                │                    │                      │
        │                ▼                    │                      │
        │        ┌────────────────────┐       │                      │
        │        │ Daily Rebalance    │       │                      │
        │        │ Gate (Bandit)      │       │                      │
        │        └────────────────────┘       │                      │
        ▼
   FastAPI Control Plane (for monitoring, manual triggers, status)
```

**Separation of Concerns:**
- **Scheduling:** External (cron, cloud scheduler, or workflow tool)
- **Orchestration:** New layer, coordinates daily run, data validation, gating, and persistence
- **PortfolioEngine:** Remains deterministic, stateless, and strategy-agnostic
- **Persistence:** All outputs and metadata written to Parquet/CSV for auditability

---

## 2️⃣ New Core Concepts (Design Only)

### TradingDayContext
**Responsibilities:**
- Encapsulates all information for a single trading day (date, calendar status, data readiness, etc.)
- Provides interfaces for querying if today is a valid trading day (NYSE calendar)
- Holds references to S3 data locations and expected file paths

**Must Not:**
- Contain any business logic for portfolio decisions
- Interact directly with PortfolioEngine

### DecisionArtifact
**Responsibilities:**
- Canonical record of the daily decision (target weights, status, metadata, reason)
- Includes all inputs, outputs, and context needed for full reproducibility
- Written as a Parquet or CSV file with metadata (date, data version, decision status, etc.)

**Must Not:**
- Contain raw order instructions or broker integration
- Omit any required metadata for audit/replay

### Daily Rebalance Gate (Bandit-Driven)
**Responsibilities:**
- Applies bandit strategy to produce target weights for the day
- Applies gating logic: only rebalance if conditions are met (e.g., sufficient drift, valid data)
- Returns explicit status: REBALANCE, HOLD, or SKIP, with rationale

**Must Not:**
- Execute trades or interact with brokers
- Mutate PortfolioEngine state

---

## 3️⃣ Daily Decision Flow (Step-by-Step)

1. **Trigger:** Scheduler (cron/cloud) initiates run after 01:00, post S3 data upload
2. **Trading Day Detection:**
   - Use NYSE calendar to check if today is a valid trading day
   - If not, exit with status SKIP (reason: non-trading day)
3. **S3 Data Readiness Validation:**
   - Confirm required Parquet file (history-data/YYYY-MM.parquet) exists and is complete
   - If missing or incomplete, exit with status SKIP (reason: data unavailable)
4. **Data Slicing:**
   - Load only the relevant slice (up to and including today) from the monthly Parquet file
   - Ensure data is final and immutable for the day
5. **TradingDayContext Construction:**
   - Build context object with all relevant info (date, data paths, calendar status, etc.)
6. **Bandit Decision:**
   - Invoke bandit strategy to compute target weights for the day
   - No order generation; only weights
7. **Daily Rebalance Gate:**
   - Apply gating logic (e.g., drift, data validity)
   - If gating fails, set status HOLD or SKIP with reason
8. **PortfolioEngine Invocation:**
   - Run PortfolioEngine in one-day deterministic mode using today’s data and target weights
   - No state mutation, no clock/calendar logic inside engine
9. **DecisionArtifact Generation:**
   - Write canonical artifact (Parquet/CSV + metadata) for the day
   - Include all inputs, outputs, and rationale
10. **Persistence:**
    - Store artifact in reproducible, auditable location (e.g., decisions/YYYY-MM-DD.parquet)

---

## 4️⃣ FastAPI Control Plane Design

**Purpose:**
- Monitoring, manual triggers, and status queries only (not compute)

**Endpoints (Design Only):**
- `GET /status/{date}`: Retrieve status and metadata for a given trading day
- `POST /trigger/{date}`: Manually trigger a daily decision run for a specific date (idempotent)
- `GET /artifact/{date}`: Download the DecisionArtifact for a given date
- `GET /calendar/{date}`: Query if a date is a valid trading day

**Idempotency Rules:**
- All endpoints are idempotent: repeated calls for the same date yield the same result or error if not possible
- Manual triggers do not overwrite existing artifacts unless explicitly forced (e.g., with a `force=true` parameter)

**Inputs/Outputs:**
- Inputs: date, optional force flag
- Outputs: status, metadata, artifact location, error reason if applicable

**State Read/Written:**
- Reads: calendar, S3 data, existing artifacts
- Writes: new DecisionArtifact only if not already present (unless forced)

---

## 5️⃣ Interaction With PortfolioEngine

**What Stays Unchanged:**
- PortfolioEngine remains deterministic, stateless, and strategy-agnostic
- No clock, calendar, or S3 logic is added to the engine

**How Invoked in “One-Day Mode”:**
- Orchestrator calls PortfolioEngine with today’s data and target weights
- Engine computes results for that day only, no persistent state

**Rebalance vs Hold Expression:**
- If gating passes: engine is called with new target weights (REBALANCE)
- If gating fails: engine is called with previous weights (HOLD), or not called at all (SKIP)
- Decision status and rationale are always recorded in the artifact

**Backtest/Live Symmetry:**
- Identical invocation path for both backtest and live, ensuring reproducibility and auditability

---

## 6️⃣ Persistence & Reproducibility

**Daily Files Written:**
- `decisions/YYYY-MM-DD.parquet` (or .csv): DecisionArtifact for each trading day
- Includes: date, target weights, status (REBALANCE/HOLD/SKIP), rationale, data version, and all relevant metadata

**Metadata Required:**
- Trading date
- Data file version/hash
- Calendar status
- Bandit parameters and version
- Gating logic outcome and reason
- PortfolioEngine version
- Any warnings or errors encountered

**Reproducibility:**
- All artifacts contain sufficient metadata to replay the decision for any day
- No mutable state; all runs are idempotent and auditable

---

## 7️⃣ Explicit Non-Goals

- No broker or order management integration
- No intraday or high-frequency trading
- No stateful or persistent services inside PortfolioEngine
- No embedding of scheduling, calendar, or S3 logic in PortfolioEngine
- No direct execution of trades
- No real-time streaming or event-driven compute
- No business logic in FastAPI endpoints (control plane only)

---

**Document Version:** 2.0  
**Last Updated:** December 22, 2025  
**Status:** Implementation Plan – Ready for Engineering
