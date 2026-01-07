# Data Loading and Processing in Examples

## Available Demos

The `examples/` folder contains the following production-ready demos:

1. **[comprehensive_benchmark_demo.py](../examples/comprehensive_benchmark_demo.py)** - Main benchmarking with 12 strategies + 4 MAB algorithms
2. **[dynamic_trading_demo.py](../examples/dynamic_trading_demo.py)** - Real-time/simulation trading platform with BACKTEST/SIMULATION/LIVE modes
3. **[mab_walk_forward_demo.py](../examples/mab_walk_forward_demo.py)** - MAB algorithms with walk-forward validation
4. **[demo_backtesting_methods.py](../examples/demo_backtesting_methods.py)** - All 5 backtesting methodologies
5. **[demo_soft_rebalancing.py](../examples/demo_soft_rebalancing.py)** - Soft vs hard rebalancing comparison
6. **[demo_rewards.py](../examples/demo_rewards.py)** - Reward calculation examples
7. **[demo_mab_stress_testing.py](../examples/demo_mab_stress_testing.py)** - MAB stress testing framework
8. **[benchmark_strategies_demo.py](../examples/benchmark_strategies_demo.py)** - Individual strategy testing

## Quick Start: Prepare Data for All Demos

**To prepare all data for the demo scripts, simply run:**

```sh
python scripts/prepare_data.py
```

This script will:
- Download the raw historical data from S3 (if needed)
- Process and clean the data
- Save the processed data in `data/processed/`
- Make the data ready for all demo scripts

**You only need to run this script once (or whenever you want to refresh the data).**

After running it, you can safely use any demo script in the `examples/` folder without additional data preparation.

This document explains how data is loaded and processed for the demo scripts in the `examples/` folder, and provides guidance to ensure safe and correct execution. The full pipeline is automated by `scripts/prepare_data.py`.

## 1. Data Loading

- **Primary Loader:**
  - The main data loading logic is implemented in [src/data_loader.py](../src/data_loader.py).
  - The function `load_preprocessed_data()` is the recommended way to load data for most demos. It loads pre-processed CSVs from `data/processed/`.
  - For raw S3 data retrieval, see [src/data_retrieval.py](../src/data_retrieval.py), but this is not required for standard demo runs.

- **How to Load Data Safely:**
  - Ensure the files `full_data_2015-11_2025-11.csv` and `price_data_2015-11_2025-11.csv` exist in `data/processed/`.
  - If not, run `python scripts/prepare_data.py` to generate them from raw or S3 data.
  - In your demo scripts, always use:
    ```python
    from src.data_loader import load_preprocessed_data
    full_data, price_data = load_preprocessed_data()
    ```

## 2. Data Processing

- **Processing Script:**
  - [scripts/prepare_data.py](../scripts/prepare_data.py) is responsible for preparing and saving the processed data files.
  - It uses logic from `src/data_loader.py` and/or `src/data_retrieval.py` to fetch, clean, and store the data.

- **Safe Processing Steps:**
  1. Run `python scripts/prepare_data.py` if you need to (see above).
  2. Do **not** modify the processed CSVs manually.
  3. Always use the loader functions in your demo scripts, not direct file reads.

## 3. Running Demos Safely

- **Before running any demo:**
  - Confirm that the processed data files exist and are up to date.
  - If you update raw data or want to refresh, rerun the preparation script.

- **Typical Demo Data Loading Pattern:**
  ```python
  from src.data_loader import load_preprocessed_data
  
  # Basic loading (recommended for most demos)
  full_data, price_data = load_preprocessed_data()
  
  # With automatic updates (checks S3 for new data)
  full_data, price_data = load_preprocessed_data(update_if_available=True)
  ```

- **Do not** use `src/data_retrieval.py` directly in demos unless you are customizing data acquisition.
- **Note**: The `update_if_available=True` parameter automatically fetches and integrates new S3 data if available.

## 4. Code Conflict Check

- The current codebase uses `load_preprocessed_data()` for safe, fast data loading in demos.
- There are no known conflicts between the loader and processing scripts as long as you:
  - Use the loader functions as described.
  - Do not bypass the processing step or modify processed files manually.
- If you encounter errors about missing data, always run the preparation script first.

---

**Summary:**
- Use `scripts/prepare_data.py` to generate processed data.
- Use `src/data_loader.py`'s `load_preprocessed_data()` in all demo scripts.
- Do not use `src/data_retrieval.py` in demos unless advanced customization is needed.
- Never edit processed CSVs by hand.
