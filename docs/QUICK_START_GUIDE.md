# Quick Start Guide for Developers

## Prerequisites
- **Python Version**: 3.11.9 or higher (required for compatibility with dependencies like `torch` and `stable-baselines3`).
- **System Requirements**: Windows/Linux/macOS with at least 8GB RAM (recommended 16GB for full backtests). Sufficient disk space for data (~5GB for processed datasets).
- **Dependencies**: pip for package management. Optional: AWS CLI for S3 access, Git for version control.

## Installation Steps
1. **Clone the Repository**:
   ```
   git clone https://github.com/Mhna1234/algo-trading-modeling.git
   cd algo-trading-modeling
   ```

2. **Set Up Virtual Environment**:
   ```
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS/Linux
   source .venv/bin/activate
   ```

3. **Install Dependencies**:
   ```
   pip install -r requirements.txt
   ```
   Key packages include `pandas`, `numpy`, `scikit-learn`, `boto3` (for S3), `pyarrow` (for Parquet), `yfinance`, and `plotly` for visualization.

4. **Configure Environment Variables** (Optional but Recommended for Full Functionality):
   - `FRED_API_KEY`: Obtain from Federal Reserve Economic Data (fred.stlouisfed.org) for risk-free rate integration.
   - `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`: For S3 data access (see `docs/S3_DATA_RETRIEVAL.md`).
   Set via system environment variables or shell.

5. **Set Up Configuration**:
   - Copy the example config: `cp config/trading_config.yaml.example config/trading_config.yaml`
   - Edit `config/trading_config.yaml` to set execution mode (`backtest`, `simulation`, or `live`), trading parameters (e.g., initial capital $100K, transaction costs 0.1%), and bandit settings (e.g., UCB algorithm).
   - The config file is gitignored for security; never commit sensitive data.

## Understanding the Project
- **Core Concept**: This is an algorithmic trading system with 12 benchmark strategies (momentum, mean reversion, etc.), multi-armed bandit (MAB) allocation for dynamic strategy selection, and **real-time capabilities via state persistence** (96% implemented as of December 2025).
- **Key Components**:
  - `src/portfolio_engine.py`: Core engine for portfolio management, rebalancing, and metrics calculation.
  - `src/strategies/`: 25 strategies, including benchmark ones and MAB wrappers.
  - `src/bandits/`: MAB implementations (UCB, Thompson Sampling, EXP3) for adaptive allocation.
  - `src/checkpoint_manager.py`: Handles state persistence for real-time trading (saves/loads portfolio snapshots).
  - `src/daily_trading_engine.py`: Orchestrates daily updates in live/simulation modes.
  - `examples/dynamic_trading_demo.py`: Unified demo for backtest, simulation, and live modes.
- **Data Flow**: Loads processed market data (CSV/Parquet), applies strategies, simulates trades with costs/slippage, calculates metrics (Sharpe ratio, drawdown), and persists state.
- **Execution Modes**:
  - **Backtest**: Batch processing of historical data.
  - **Simulation**: Historical replay with checkpoints (e.g., quarterly rebalancing over 2015-2024).
  - **Live**: Daily updates (requires S3/FRED access) - **implemented and ready for use**.

## Running Examples
1. **Basic Demo** (Full 10-year backtest with 12 strategies):
   ```
   python examples/demo_12_strategies_full.py
   ```
   Outputs comprehensive metrics and plots in `results/`.

2. **MAB Comparison Demo** (Compare different bandit algorithms):
   ```
   python examples/mab_comparison_demo.py
   ```
   Shows performance comparison between UCB, Thompson, and EXP3 bandits.

3. **Full System Demo** (Unified real-time platform):
   ```
   python examples/dynamic_trading_demo.py --mode simulation
   ```
   Runs simulation mode with checkpoints; check `results/dynamic_trading_api_data.json` for output (e.g., equity curve, Sharpe ratio ~0.82).

4. **Dashboard** (Visualization):
   ```
   streamlit run dashboard.py
   ```
   Opens interactive dashboard for results analysis.

5. **Testing**:
   ```
   pytest tests/
   ```
   Runs unit tests for core components.

## Troubleshooting
- **Data Issues**: Ensure `data/processed/` has CSV files; use `scripts/prepare_data.py` to preprocess raw data.
- **API Errors**: Verify environment variables; fallbacks exist for offline mode.
- **Performance**: Full backtests may take 5-10 minutes; use smaller date ranges for testing.
- **Real-Time Features**: Check `checkpoints/` directory for state persistence; simulation mode works without external APIs.
- **Configuration**: Validate `config/trading_config.yaml` syntax; use YAML linter if needed.
- **Documentation**: Read `README.md`, `docs/ARCHITECTURE.md`, `docs/REALTIME_TRADING_IMPLEMENTATION_PLAN.md`, and `src/MODULE_ORGANIZATION.md` for deep dives.

## Current Implementation Status (December 2025)
- ✅ **Data Pipeline**: Incremental loading, S3 integration, FRED API, gap detection
- ✅ **State Persistence**: CheckpointManager with JSON/Parquet storage, 7-day cleanup
- ✅ **Daily Trading Engine**: Real-time updates, MAB integration, error handling
- ✅ **Unified Demo**: BACKTEST/SIMULATION/LIVE modes with YAML configuration
- ✅ **Core Algorithm**: Complete backtesting with soft rebalancing, transaction costs, metrics
- ❌ **Automation**: FastAPI service and GitHub Actions (planned for Phase 5)

**Ready for Production**: The system supports real-time trading with 96% of planned features implemented. Use simulation mode for testing without external dependencies.