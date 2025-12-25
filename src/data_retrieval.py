"""Module for retrieving historical OHLCV data from S3."""

import re
import sys
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import List, Tuple

import boto3
import pandas as pd
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from dateutil.relativedelta import relativedelta


def load_month(year: int, month: int) -> pd.DataFrame:
    """Download a single month of OHLCV data from S3 and return as a DataFrame.
    
    Args:
        year: 4-digit year (e.g., 2020)
        month: Month number (1-12)
        
    Returns:
        DataFrame with columns: symbol, date, open, high, low, close, volume
        
    Raises:
        ValueError: If month is not in range 1-12
        RuntimeError: If AWS credentials are missing or incomplete
        FileNotFoundError: If the S3 object doesn't exist
        PermissionError: If access to S3 is denied
    """
    if not 1 <= month <= 12:
        raise ValueError("month must be in 1-12")

    key = f"history-data/{year:04d}-{month:02d}.parquet"
    s3 = boto3.client("s3")

    try:
        obj = s3.get_object(Bucket="data-retrieval-output", Key=key)
    except NoCredentialsError as exc:
        raise RuntimeError(
            "AWS credentials not found. Configure credentials (e.g., AWS CLI, env vars, or IAM role)."
        ) from exc
    except PartialCredentialsError as exc:
        raise RuntimeError("Incomplete AWS credentials. Check your AWS configuration.") from exc
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code == "NoSuchKey":
            raise FileNotFoundError(f"S3 object not found: s3://data-retrieval-output/{key}") from exc
        if error_code == "AccessDenied":
            raise PermissionError("Access denied when reading S3 object. Confirm IAM permissions.") from exc
        raise

    return pd.read_parquet(BytesIO(obj["Body"].read()))


def load_multiple_months(year_months: List[Tuple[int, int]]) -> pd.DataFrame:
    """Load and concatenate multiple months of OHLCV data.
    
    Args:
        year_months: List of (year, month) tuples
        
    Returns:
        Concatenated DataFrame with all months
        
    Example:
        >>> data = load_multiple_months([(2020, 1), (2020, 2), (2020, 3)])
    """
    dfs = []
    for year, month in year_months:
        print(f"Loading {year:04d}-{month:02d}...", file=sys.stderr)
        df = load_month(year, month)
        dfs.append(df)
    
    return pd.concat(dfs, ignore_index=True)


def load_date_range(start_year: int, start_month: int, end_year: int, end_month: int) -> pd.DataFrame:
    """Load all months in a date range.
    
    Args:
        start_year: Starting year
        start_month: Starting month (1-12)
        end_year: Ending year
        end_month: Ending month (1-12)
        
    Returns:
        DataFrame containing all data in the range (inclusive)
    """
    year_months = []
    current_year, current_month = start_year, start_month
    
    while (current_year, current_month) <= (end_year, end_month):
        year_months.append((current_year, current_month))
        current_month += 1
        if current_month > 12:
            current_month = 1
            current_year += 1
    
    return load_multiple_months(year_months)


def save_to_csv(df: pd.DataFrame, output_path: Path) -> None:
    """Save DataFrame to CSV file.
    
    Args:
        df: DataFrame to save
        output_path: Path where CSV should be saved
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Saved {len(df)} rows to {output_path}")


def get_latest_available_month() -> Tuple[int, int]:
    """Get the latest available month of data in S3.
    
    Returns:
        Tuple of (year, month) for the most recent available data
        
    Raises:
        RuntimeError: If AWS credentials are missing or no data files found
        FileNotFoundError: If no history-data files exist in the bucket
    """
    s3 = boto3.client("s3")
    
    try:
        # List objects in the history-data prefix
        response = s3.list_objects_v2(Bucket="data-retrieval-output", Prefix="history-data/")
        
        if 'Contents' not in response:
            raise FileNotFoundError("No history-data files found in S3 bucket")
        
        # Extract dates from keys like "history-data/2020-01.parquet"
        available_dates = []
        for obj in response['Contents']:
            key = obj['Key']
            if key.endswith('.parquet'):
                try:
                    date_str = key.split('/')[-1].replace('.parquet', '')  # "2020-01"
                    year, month = map(int, date_str.split('-'))
                    if 1 <= month <= 12:  # Validate month range
                        available_dates.append((year, month))
                except (ValueError, IndexError):
                    continue  # Skip malformed keys
        
        if not available_dates:
            raise FileNotFoundError("No valid history-data files found in S3 bucket")
        
        # Return the latest date
        return max(available_dates)
        
    except NoCredentialsError as exc:
        raise RuntimeError(
            "AWS credentials not found. Configure credentials (e.g., AWS CLI, env vars, or IAM role)."
        ) from exc
    except PartialCredentialsError as exc:
        raise RuntimeError("Incomplete AWS credentials. Check your AWS configuration.") from exc
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code == "AccessDenied":
            raise PermissionError("Access denied when listing S3 objects. Confirm IAM permissions.") from exc
        raise


def load_latest_month() -> pd.DataFrame:
    """Load the most recent month of OHLCV data available in S3.
    
    Returns:
        DataFrame with the latest available month's data
        
    Raises:
        Same exceptions as load_month() and get_latest_available_month()
    """
    year, month = get_latest_available_month()
    print(f"Loading latest available data: {year:04d}-{month:02d}", file=sys.stderr)
    return load_month(year, month)


def parse_date_range_from_filename(filename: str) -> Tuple[int, int, int, int]:
    """Parse year-month range from a filename like 'data_2015-11_2025-11.csv'.
    
    Args:
        filename: Filename containing date range
        
    Returns:
        Tuple of (start_year, start_month, end_year, end_month)
        
    Raises:
        ValueError: If filename doesn't contain valid date range
    """
    # Match pattern like: data_2015-11_2025-11.csv or full_data_2015-11_2025-11.csv
    pattern = r'_(\d{4})-(\d{2})_(\d{4})-(\d{2})\.csv$'
    match = re.search(pattern, filename)
    
    if not match:
        raise ValueError(f"Could not parse date range from filename: {filename}")
    
    start_year, start_month, end_year, end_month = map(int, match.groups())
    
    # Validate months
    for month in [start_month, end_month]:
        if not 1 <= month <= 12:
            raise ValueError(f"Invalid month {month} in filename: {filename}")
    
    return start_year, start_month, end_year, end_month


def get_local_data_date_range(data_dir: Path = Path("data/processed")) -> Tuple[int, int, int, int]:
    """Get the date range of locally stored data by parsing filenames.
    
    Args:
        data_dir: Directory containing processed data files
        
    Returns:
        Tuple of (start_year, start_month, end_year, end_month) representing
        the complete date range available locally
        
    Raises:
        FileNotFoundError: If no valid data files found
    """
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")
    
    # Find all CSV files with date ranges
    csv_files = list(data_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")
    
    date_ranges = []
    for file_path in csv_files:
        try:
            start_year, start_month, end_year, end_month = parse_date_range_from_filename(file_path.name)
            date_ranges.append((start_year, start_month, end_year, end_month))
        except ValueError:
            continue  # Skip files that don't match the pattern
    
    if not date_ranges:
        raise FileNotFoundError(f"No files with valid date ranges found in {data_dir}")
    
    # Find the overall date range (earliest start to latest end)
    min_start = min(date_ranges, key=lambda x: (x[0], x[1]))
    max_end = max(date_ranges, key=lambda x: (x[2], x[3]))
    
    return min_start[0], min_start[1], max_end[2], max_end[3]


def get_missing_date_range(data_dir: Path = Path("data/processed")) -> List[Tuple[int, int]]:
    """Calculate the date range missing from local data up to current month.
    
    Args:
        data_dir: Directory containing processed data files
        
    Returns:
        List of (year, month) tuples for months that need to be fetched
        
    Raises:
        FileNotFoundError: If local data date range cannot be determined
    """
    try:
        local_start_year, local_start_month, local_end_year, local_end_month = get_local_data_date_range(data_dir)
    except FileNotFoundError:
        # If no local data, we'll need to determine what to fetch (this might be handled differently)
        raise FileNotFoundError("Cannot determine missing date range: no local data found")
    
    # Get current date
    today = date.today()
    current_year = today.year
    current_month = today.month
    
    # Convert local end date to date object and add one month
    local_end_date = date(local_end_year, local_end_month, 1)
    next_month = local_end_date + relativedelta(months=1)
    
    missing_months = []
    current_date = next_month
    
    # Generate all months from local_end + 1 month to current month
    while current_date <= date(current_year, current_month, 1):
        missing_months.append((current_date.year, current_date.month))
        current_date += relativedelta(months=1)
    
    return missing_months


def load_missing_data(data_dir: Path = Path("data/processed")) -> pd.DataFrame:
    """Load all missing data from last local update to current month.
    
    Args:
        data_dir: Directory containing processed data files
        
    Returns:
        DataFrame with all missing months concatenated
        
    Raises:
        FileNotFoundError: If no missing data to fetch
    """
    missing_months = get_missing_date_range(data_dir)
    
    if not missing_months:
        raise FileNotFoundError("No missing data to fetch - local data is up to date")
    
    print(f"Found {len(missing_months)} missing months to fetch", file=sys.stderr)
    return load_multiple_months(missing_months)


def update_processed_data(data_dir: Path = Path("data")) -> None:
    """Update processed datasets with any missing data from S3.
    
    This function:
    1. Determines what data is missing locally
    2. Fetches missing data from S3
    3. Appends it to existing processed datasets
    
    Args:
        data_dir: Base data directory (should contain processed/ subdirectory)
    """
    from src.data_loader import DataLoader
    
    print("Checking for missing data...", file=sys.stderr)
    
    try:
        missing_months = get_missing_date_range(data_dir / "processed")
    except FileNotFoundError as e:
        print(f"No processed data found: {e}", file=sys.stderr)
        return
    
    if not missing_months:
        print("Local data is up to date - no missing months found", file=sys.stderr)
        return
    
    print(f"Fetching {len(missing_months)} missing months from S3...", file=sys.stderr)
    
    # Fetch missing data
    try:
        new_data = load_multiple_months(missing_months)
        print(f"Fetched {len(new_data)} rows of new data", file=sys.stderr)
    except Exception as e:
        print(f"Error fetching data from S3: {e}", file=sys.stderr)
        return
    
    # Append to processed data
    try:
        loader = DataLoader(str(data_dir))
        loader.append_s3_data_to_processed(new_data)
        print("Successfully updated processed datasets", file=sys.stderr)
    except Exception as e:
        print(f"Error updating processed data: {e}", file=sys.stderr)
        raise
