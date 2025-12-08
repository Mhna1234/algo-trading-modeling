# S3 Data Retrieval Guide

## Overview

This module retrieves historical OHLCV (Open, High, Low, Close, Volume) data from AWS S3 storage. Data is stored as monthly Parquet files in the `data-retrieval-output` bucket.

## Data Structure

**S3 Location:** `s3://data-retrieval-output/history-data/`

**File Format:** `history-data/YYYY-MM.parquet`
- Example: `history-data/2020-01.parquet`

**Schema per row:**
- `symbol` (string) - Ticker symbol
- `date` (date/datetime) - Trading date
- `open` (float) - Opening price
- `high` (float) - High price
- `low` (float) - Low price
- `close` (float) - Close price
- `volume` (float/numeric) - Trading volume

Each file contains approximately **10 years of daily OHLCV data** across all symbols for one month.

## Prerequisites

### 1. Install Dependencies

```powershell
# Install required packages
pip install boto3 pyarrow

# Or install all requirements
pip install -r requirements.txt
```

### 2. Configure AWS Credentials

You need AWS credentials with read access to the `data-retrieval-output` bucket. Configure them using one of these methods:

**Option A: AWS CLI (Recommended)**
```powershell
# Install AWS CLI if not already installed
# Download from: https://aws.amazon.com/cli/

# Configure credentials
aws configure
```

Enter your:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (e.g., us-east-1)
- Default output format (json)

**Option B: Environment Variables**
```powershell
$env:AWS_ACCESS_KEY_ID="your_access_key"
$env:AWS_SECRET_ACCESS_KEY="your_secret_key"
$env:AWS_DEFAULT_REGION="us-east-1"
```

**Option C: AWS Credentials File**

Create/edit `~\.aws\credentials`:
```
[default]
aws_access_key_id = your_access_key
aws_secret_access_key = your_secret_key
```

## Usage

### Command Line Interface

The main script is `scripts/load_s3_data.py`.

#### Load a Single Month

```powershell
# Load January 2020
python scripts/load_s3_data.py --year 2020 --month 1

# Output will be saved to: data/2020-01.csv
```

#### Load a Date Range

```powershell
# Load Q1 2020 (January through March)
python scripts/load_s3_data.py --start-year 2020 --start-month 1 --end-year 2020 --end-month 3

# Output: data/range_202001-202003.csv
```

```powershell
# Load entire year 2020
python scripts/load_s3_data.py --start-year 2020 --start-month 1 --end-year 2020 --end-month 12
```

#### Custom Output Path

```powershell
# Save to specific location
python scripts/load_s3_data.py --year 2020 --month 1 --output data/raw/jan2020.csv

# Save range to custom path
python scripts/load_s3_data.py --start-year 2020 --start-month 1 --end-year 2020 --end-month 6 --output data/raw/2020_h1.csv
```

### Python API

Use the module programmatically in your code:

```python
from src.data_retrieval import load_month, load_date_range, load_multiple_months, save_to_csv
from pathlib import Path

# Load a single month
df = load_month(2020, 1)
print(df.head())
print(f"Rows: {len(df)}, Symbols: {df['symbol'].nunique()}")

# Load multiple specific months
months = [(2020, 1), (2020, 2), (2020, 3)]
df = load_multiple_months(months)

# Load a continuous date range
df = load_date_range(2020, 1, 2020, 12)  # All of 2020

# Filter for specific symbols
df_filtered = df[df['symbol'].isin(['AAPL', 'GOOGL', 'MSFT'])]

# Save to CSV
save_to_csv(df_filtered, Path("data/processed/filtered_data.csv"))
```

## Examples

### Example 1: Load and Analyze Recent Data

```powershell
# Load last 3 months of 2020
python scripts/load_s3_data.py --start-year 2020 --start-month 10 --end-year 2020 --end-month 12 --output data/raw/2020_q4.csv
```

### Example 2: Load Multiple Years

```python
from src.data_retrieval import load_date_range
from pathlib import Path

# Load 2019-2020
df = load_date_range(2019, 1, 2020, 12)

print(f"Total rows: {len(df):,}")
print(f"Unique symbols: {df['symbol'].nunique()}")
print(f"Date range: {df['date'].min()} to {df['date'].max()}")

# Save
df.to_csv("data/raw/2019_2020_full.csv", index=False)
```

### Example 3: Integration with Existing Pipeline

```python
from src.data_retrieval import load_date_range
from src.data_loader import DataLoader

# Retrieve data from S3
df = load_date_range(2020, 1, 2020, 12)

# Save to expected location
df.to_csv("data/raw/raw_data_2020-01-01_2020-12-31.csv", index=False)

# Use with existing pipeline
loader = DataLoader()
data = loader.load_data(
    symbols=['AAPL', 'GOOGL', 'MSFT'],
    start_date='2020-01-01',
    end_date='2020-12-31',
    data_source='csv',
    csv_path='data/raw/raw_data_2020-01-01_2020-12-31.csv'
)
```

## Error Handling

### Common Errors

**1. NoCredentialsError**
```
AWS credentials not found. Configure credentials...
```
→ Configure AWS credentials (see Prerequisites)

**2. AccessDenied**
```
Access denied when reading S3 object...
```
→ Verify your IAM permissions for the bucket

**3. NoSuchKey**
```
S3 object not found: s3://data-retrieval-output/history-data/2020-01.parquet
```
→ Check if the month exists in S3 or verify the date

**4. Import boto3 could not be resolved**
```
pip install boto3 pyarrow
```

## Testing Your Setup

Run this quick test to verify everything works:

```python
from src.data_retrieval import load_month

try:
    df = load_month(2020, 1)
    print("✓ Successfully connected to S3")
    print(f"✓ Loaded {len(df):,} rows")
    print(f"✓ Columns: {list(df.columns)}")
    print("\nSample data:")
    print(df.head())
except Exception as e:
    print(f"✗ Error: {e}")
```

## Performance Notes

- Each month file is ~10 years of data across all symbols
- Loading a single month typically takes 5-30 seconds depending on network speed
- Loading multiple months will concatenate all data in memory
- For large date ranges, consider processing month-by-month to reduce memory usage
- Parquet format is highly compressed and efficient for transfer

## Troubleshooting

1. **Slow downloads**: Check your internet connection and AWS region configuration
2. **Memory issues**: Process months individually or filter symbols early
3. **Credential issues**: Run `aws sts get-caller-identity` to verify AWS access
4. **Import errors**: Ensure all dependencies are installed in the correct Python environment

## Module Reference

### Functions

**`load_month(year: int, month: int) -> pd.DataFrame`**
- Load a single month of data
- Raises: ValueError, RuntimeError, FileNotFoundError, PermissionError

**`load_multiple_months(year_months: List[Tuple[int, int]]) -> pd.DataFrame`**
- Load and concatenate specific months
- Example: `[(2020, 1), (2020, 3), (2020, 6)]`

**`load_date_range(start_year: int, start_month: int, end_year: int, end_month: int) -> pd.DataFrame`**
- Load all months in a continuous range (inclusive)

**`save_to_csv(df: pd.DataFrame, output_path: Path) -> None`**
- Save DataFrame to CSV with automatic directory creation
