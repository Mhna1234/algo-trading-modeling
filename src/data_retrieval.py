"""Module for retrieving historical OHLCV data from S3."""

import sys
from io import BytesIO
from pathlib import Path
from typing import List, Tuple

import boto3
import pandas as pd
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError


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
