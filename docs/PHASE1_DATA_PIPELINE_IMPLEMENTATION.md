# Real-Time Trading Data Pipeline - Phase 1 Implementation

## Overview

Phase 1 of the real-time trading implementation adds comprehensive data pipeline enhancements for incremental updates, gap detection, and data validation. This enables the system to automatically detect missing data, fetch only what's needed from S3, and maintain data integrity.

## New Functions Added

### Data Retrieval Functions (`src/data_retrieval.py`)

#### `get_latest_available_month() -> Tuple[int, int]`
Gets the latest available month of data in S3.

**Returns:**
- Tuple of (year, month) for the most recent available data

**Raises:**
- `RuntimeError`: If AWS credentials are missing
- `FileNotFoundError`: If no history-data files exist

**Example:**
```python
from src.data_retrieval import get_latest_available_month

try:
    year, month = get_latest_available_month()
    print(f"Latest data available: {year:04d}-{month:02d}")
except RuntimeError as e:
    print(f"Credential error: {e}")
```

#### `load_latest_month() -> pd.DataFrame`
Loads the most recent month of OHLCV data available in S3.

**Returns:**
- DataFrame with columns: symbol, date, open, high, low, close, volume

**Example:**
```python
from src.data_retrieval import load_latest_month

df = load_latest_month()
print(f"Loaded {len(df)} rows for {df['symbol'].nunique()} symbols")
```

#### `parse_date_range_from_filename(filename: str) -> Tuple[int, int, int, int]`
Parses year-month range from a filename like 'data_2015-11_2025-11.csv'.

**Parameters:**
- `filename`: Filename containing date range

**Returns:**
- Tuple of (start_year, start_month, end_year, end_month)

**Raises:**
- `ValueError`: If filename doesn't contain valid date range

**Example:**
```python
from src.data_retrieval import parse_date_range_from_filename

start_year, start_month, end_year, end_month = parse_date_range_from_filename("data_2015-11_2025-11.csv")
print(f"Data range: {start_year}-{start_month:02d} to {end_year}-{end_month:02d}")
```

#### `get_local_data_date_range(data_dir: Path = Path("data/processed")) -> Tuple[int, int, int, int]`
Gets the date range of locally stored data by parsing filenames.

**Parameters:**
- `data_dir`: Directory containing processed data files (default: "data/processed")

**Returns:**
- Tuple of (start_year, start_month, end_year, end_month)

**Raises:**
- `FileNotFoundError`: If no valid data files found

**Example:**
```python
from src.data_retrieval import get_local_data_date_range
from pathlib import Path

start_year, start_month, end_year, end_month = get_local_data_date_range()
print(f"Local data covers: {start_year}-{start_month:02d} to {end_year}-{end_month:02d}")
```

#### `get_missing_date_range(data_dir: Path = Path("data/processed")) -> List[Tuple[int, int]]`
Calculates the date range missing from local data up to current month.

**Parameters:**
- `data_dir`: Directory containing processed data files

**Returns:**
- List of (year, month) tuples for months that need to be fetched

**Example:**
```python
from src.data_retrieval import get_missing_date_range

missing_months = get_missing_date_range()
if missing_months:
    print(f"Missing {len(missing_months)} months: {missing_months}")
else:
    print("Data is up to date")
```

#### `load_missing_data(data_dir: Path = Path("data/processed")) -> pd.DataFrame`
Loads all missing data from last local update to current month.

**Parameters:**
- `data_dir`: Directory containing processed data files

**Returns:**
- DataFrame with all missing months concatenated

**Example:**
```python
from src.data_retrieval import load_missing_data

try:
    df = load_missing_data()
    print(f"Fetched {len(df)} rows of missing data")
except FileNotFoundError:
    print("No missing data to fetch")
```

#### `update_processed_data(data_dir: Path = Path("data")) -> None`
Updates processed datasets with any missing data from S3.

This function orchestrates the entire incremental update process:
1. Determines what data is missing locally
2. Fetches missing data from S3
3. Appends it to existing processed datasets

**Parameters:**
- `data_dir`: Base data directory (should contain processed/ subdirectory)

**Example:**
```python
from src.data_retrieval import update_processed_data

# Update processed data with any missing months
update_processed_data()
print("Processed data updated successfully")
```

### Data Loader Functions (`src/data_loader.py`)

#### `convert_s3_to_multiindex(s3_data: pd.DataFrame) -> pd.DataFrame`
Converts S3 data format to MultiIndex format used by processed data.

**Parameters:**
- `s3_data`: DataFrame from S3 with columns [symbol, date, open, high, low, close, volume]

**Returns:**
- DataFrame with MultiIndex columns in processed format

**Example:**
```python
from src.data_loader import DataLoader

loader = DataLoader()
s3_df = load_missing_data()  # Get S3 data
processed_df = loader.convert_s3_to_multiindex(s3_df)
print(f"Converted to MultiIndex format with shape: {processed_df.shape}")
```

#### `detect_data_gaps(data: pd.DataFrame, log_gaps: bool = True) -> Dict`
Detects gaps in trading data and categorizes them as expected or unexpected.

**Parameters:**
- `data`: DataFrame with datetime index
- `log_gaps`: Whether to log gap information (default: True)

**Returns:**
- Dictionary with gap statistics:
  - `total_gaps`: Total number of missing dates
  - `expected_gaps`: Gaps due to weekends/holidays
  - `unexpected_gaps`: Gaps on business days
  - `expected_gap_dates`: List of expected gap dates
  - `unexpected_gap_dates`: List of unexpected gap dates
  - `data_completeness`: Percentage of dates present

**Example:**
```python
from src.data_loader import DataLoader

loader = DataLoader()
full_data, price_data = loader.load_preprocessed_data()

gap_stats = loader.detect_data_gaps(price_data)
print(f"Data completeness: {gap_stats['data_completeness']:.1%}")
print(f"Expected gaps: {gap_stats['expected_gaps']}")
print(f"Unexpected gaps: {gap_stats['unexpected_gaps']}")
```

#### `validate_data_integrity(data: pd.DataFrame) -> bool`
Validates data integrity and logs any issues.

Checks for:
- Data gaps (expected vs unexpected)
- Price continuity (no extreme jumps > 50% daily change)
- Invalid prices (zero or negative)

**Parameters:**
- `data`: DataFrame to validate

**Returns:**
- `True` if data passes all checks, `False` otherwise

**Example:**
```python
from src.data_loader import DataLoader

loader = DataLoader()
full_data, price_data = loader.load_preprocessed_data()

is_valid = loader.validate_data_integrity(full_data)
if is_valid:
    print("Data integrity check passed")
else:
    print("Data integrity issues found (check logs)")
```

#### `append_s3_data_to_processed(s3_data: pd.DataFrame) -> None`
Appends new S3 data to existing processed datasets.

This method:
1. Loads existing processed data
2. Converts S3 data to compatible format
3. Preprocesses the new data
4. Validates data integrity
5. Appends to existing data
6. Saves updated processed files

**Parameters:**
- `s3_data`: New data from S3 in raw format

**Example:**
```python
from src.data_loader import DataLoader
from src.data_retrieval import load_missing_data

loader = DataLoader()

# Get missing data
missing_data = load_missing_data()

# Append to processed datasets
loader.append_s3_data_to_processed(missing_data)
print("Successfully appended new data to processed datasets")
```

## Usage Examples

### Complete Incremental Update Workflow

```python
from src.data_retrieval import update_processed_data

# One-liner to update all processed data
update_processed_data()
```

### Manual Step-by-Step Update

```python
from src.data_retrieval import (
    get_missing_date_range,
    load_multiple_months
)
from src.data_loader import DataLoader

# Check what data is missing
missing_months = get_missing_date_range()
print(f"Missing months: {missing_months}")

if missing_months:
    # Fetch missing data
    new_data = load_multiple_months(missing_months)
    print(f"Fetched {len(new_data)} rows")
    
    # Append to processed datasets
    loader = DataLoader()
    loader.append_s3_data_to_processed(new_data)
    print("Data successfully updated")
else:
    print("Data is already up to date")
```

### Data Quality Monitoring

```python
from src.data_loader import DataLoader

loader = DataLoader()
full_data, price_data = loader.load_preprocessed_data()

# Check for gaps
gap_stats = loader.detect_data_gaps(price_data)
print(f"Data completeness: {gap_stats['data_completeness']:.1%}")

# Validate integrity
is_valid = loader.validate_data_integrity(full_data)
print(f"Data integrity: {'✓' if is_valid else '✗'}")

if gap_stats['unexpected_gaps'] > 0:
    print(f"Warning: {gap_stats['unexpected_gaps']} unexpected gaps found")
    print(f"Dates: {gap_stats['unexpected_gap_dates'][:5]}...")  # Show first 5
```

### Checking Local Data Coverage

```python
from src.data_retrieval import get_local_data_date_range

try:
    start_year, start_month, end_year, end_month = get_local_data_date_range()
    print(f"Local data covers: {start_year}-{start_month:02d} to {end_year}-{end_month:02d}")
except FileNotFoundError:
    print("No processed data found locally")
```

## Integration with Existing Code

### Automatic Integration
The new functionality integrates seamlessly with existing code:

- `append_s3_data_to_processed()` automatically validates data integrity
- Gap detection runs during data validation
- All functions use existing error handling patterns
- No changes needed to existing demo scripts

### Enhanced DataLoader Usage
```python
from src.data_loader import DataLoader

loader = DataLoader()

# Existing functionality still works
full_data, price_data = loader.load_data(['AAPL', 'MSFT'], '2020-01-01', '2023-12-31')

# New functionality available
gap_stats = loader.detect_data_gaps(price_data)
is_valid = loader.validate_data_integrity(full_data)
```

## Error Handling

All functions include comprehensive error handling:

- **AWS Credentials**: `RuntimeError` with helpful messages
- **Missing Files**: `FileNotFoundError` for local or S3 data
- **Invalid Data**: `ValueError` for malformed filenames or data
- **Network Issues**: Appropriate exceptions from boto3

## Performance Notes

- **Gap Detection**: Efficient O(n) operation on data size
- **Data Validation**: Minimal overhead, suitable for daily runs
- **Incremental Updates**: Only processes missing months
- **Memory Usage**: Scales with data size, processes in chunks

## Testing

Comprehensive unit tests are available:

```bash
# Test data retrieval functions
pytest tests/test_data_retrieval.py -v

# Test data loader incremental functions
pytest tests/test_data_loader_incremental.py -v

# Run all tests
pytest tests/test_data_retrieval.py tests/test_data_loader_incremental.py
```

## Dependencies

The implementation uses existing dependencies plus:
- `pandas.tseries.holiday.USFederalHolidayCalendar`
- `pandas.tseries.offsets.CustomBusinessDay`

All dependencies are already included in `requirements.txt`.

## Next Steps

This completes Phase 1 of the real-time trading implementation. The system now supports:

- ✅ Automatic detection of missing data
- ✅ Incremental fetching from S3
- ✅ Data integrity validation
- ✅ Gap detection and logging
- ✅ Seamless integration with existing pipeline

Phase 2 will focus on state persistence and checkpoint management.