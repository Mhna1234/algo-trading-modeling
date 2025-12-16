# Data Loading and Processing in Examples

This document explains how data is loaded and processed for the demo scripts in the `examples/` folder, and provides guidance to ensure safe and correct execution.

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
  full_data, price_data = load_preprocessed_data()
  ```

- **Do not** use `src/data_retrieval.py` directly in demos unless you are customizing data acquisition.

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
