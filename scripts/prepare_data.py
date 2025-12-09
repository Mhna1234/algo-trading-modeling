"""
Data Preparation Script for Algo Trading Project
=================================================

This script downloads historical OHLCV data from S3 (Nov 2015 - Nov 2025)
and processes it once so that all demo scripts can use the pre-loaded data.

Usage:
    python scripts/prepare_data.py

This will:
1. Download raw data from S3 for the full date range (2015-11 to 2025-11)
2. Process the data (clean, add features, etc.)
3. Save both raw and processed data to disk
4. Generate data summary statistics

The processed data will be used by all demo scripts to avoid redundant
downloading and processing.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from dotenv import load_dotenv
from src.data_retrieval import load_date_range, save_to_csv
from src.data_loader import DataLoader

# Load environment variables from .env file
load_dotenv()


def print_section(title: str):
    """Print formatted section header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def download_s3_data(start_year: int, start_month: int, 
                     end_year: int, end_month: int,
                     output_dir: Path) -> pd.DataFrame:
    """
    Download raw data from S3.
    
    Args:
        start_year: Starting year (e.g., 2015)
        start_month: Starting month (1-12)
        end_year: Ending year (e.g., 2025)
        end_month: Ending month (1-12)
        output_dir: Directory to save raw data
        
    Returns:
        DataFrame with raw OHLCV data
    """
    print_section("DOWNLOADING DATA FROM S3")
    print(f"Date range: {start_year:04d}-{start_month:02d} to {end_year:04d}-{end_month:02d}")
    print(f"Output directory: {output_dir}")
    
    # Download data
    print("\nDownloading...")
    df = load_date_range(start_year, start_month, end_year, end_month)
    
    # Display summary
    print(f"\n✓ Downloaded {len(df):,} rows")
    if 'symbol' in df.columns:
        print(f"✓ Found {df['symbol'].nunique():,} unique symbols")
    if 'date' in df.columns:
        print(f"✓ Date range: {df['date'].min()} to {df['date'].max()}")
    
    # Save raw data
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_file = output_dir / f"raw_data_{start_year}-{start_month:02d}_{end_year}-{end_month:02d}.csv"
    save_to_csv(df, raw_file)
    
    return df


def reshape_to_multiindex_format(df: pd.DataFrame, tickers: list = None) -> pd.DataFrame:
    """
    Reshape S3 data from long format to wide MultiIndex format.
    
    S3 format (long): Each row is one ticker-date observation
        columns = [symbol, date, open, high, low, close, volume]
    
    MultiIndex format (wide): Each row is one date, columns are hierarchical
        columns = MultiIndex[(ticker1, 'open'), (ticker1, 'high'), ..., (ticker2, 'open'), ...]
        index = date
    
    This reshape is required because DataLoader expects wide format with MultiIndex columns.
    
    Args:
        df: Raw DataFrame from S3 in long format
        tickers: Optional list of tickers to filter. If None, use top 20 by volume
        
    Returns:
        DataFrame in wide MultiIndex format
    """
    print_section("RESHAPING DATA TO MULTIINDEX FORMAT")
    
    # Ensure date column is datetime
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    
    # Select tickers if specified, otherwise use top tickers by volume
    if tickers is None:
        # Calculate average volume per ticker
        avg_volumes = df.groupby('symbol')['volume'].mean().sort_values(ascending=False)
        tickers = avg_volumes.head(20).index.tolist()
        print(f"Using top 20 tickers by volume: {', '.join(tickers[:10])}...")
    else:
        print(f"Using specified tickers: {', '.join(tickers)}")
    
    # Filter to selected tickers
    df = df[df['symbol'].isin(tickers)].copy()
    
    # Pivot to create MultiIndex columns
    result_dfs = {}
    for ticker in tickers:
        ticker_data = df[df['symbol'] == ticker].set_index('date')[['open', 'high', 'low', 'close', 'volume']]
        ticker_data.columns = pd.MultiIndex.from_product([[ticker], ticker_data.columns])
        result_dfs[ticker] = ticker_data
    
    # Concatenate all tickers
    result = pd.concat(result_dfs.values(), axis=1)
    
    # Reorder columns
    result = result.reindex(columns=tickers, level=0)
    
    print(f"✓ Reshaped to MultiIndex format (wide)")
    print(f"✓ Shape: {result.shape}")
    print(f"✓ Tickers: {len(tickers)}")
    print(f"✓ Date range: {result.index.min()} to {result.index.max()}")
    
    return result


def process_data(raw_data: pd.DataFrame, output_dir: Path, 
                 tickers: list = None) -> tuple:
    """
    Process raw data and save to disk.
    
    Args:
        raw_data: Raw DataFrame from S3
        output_dir: Directory to save processed data
        tickers: Optional list of tickers to use
        
    Returns:
        Tuple of (full_data, price_data)
    """
    print_section("PROCESSING DATA")
    
    # Reshape to MultiIndex format
    multiindex_data = reshape_to_multiindex_format(raw_data, tickers)
    
    # Create DataLoader instance
    loader = DataLoader()
    
    # Clean the data
    print("\nCleaning data...")
    cleaned_data = loader.clean_data(multiindex_data)
    print(f"✓ Data cleaned")
    
    # Extract price data
    print("Extracting price data...")
    price_data = loader.get_adjusted_closes(cleaned_data)
    print(f"✓ Price data extracted: {price_data.shape}")
    
    # Save processed data
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save full data (with all OHLCV columns)
    full_file = output_dir / "full_data_2015-11_2025-11.csv"
    cleaned_data.to_csv(full_file)
    print(f"✓ Saved full data to {full_file}")
    
    # Save price data (close prices only)
    price_file = output_dir / "price_data_2015-11_2025-11.csv"
    price_data.to_csv(price_file)
    print(f"✓ Saved price data to {price_file}")
    
    return cleaned_data, price_data


def generate_summary(price_data: pd.DataFrame):
    """Generate and display data summary."""
    print_section("DATA SUMMARY")
    
    loader = DataLoader()
    summary = loader.get_data_summary(price_data)
    
    for key, value in summary.items():
        print(f"{key}: {value}")
    
    print("\nFirst few rows of price data:")
    print(price_data.head())
    
    print("\nLast few rows of price data:")
    print(price_data.tail())


def main():
    """Main execution function."""
    print_section("ALGO TRADING DATA PREPARATION")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Configuration
    START_YEAR = 2015
    START_MONTH = 11
    END_YEAR = 2025
    END_MONTH = 11
    
    # Default tickers (top tech and market leaders)
    DEFAULT_TICKERS = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META',  # Tech giants
        'NVDA', 'TSLA', 'JPM', 'V', 'JNJ',        # Leaders in other sectors
        'WMT', 'PG', 'XOM', 'BAC', 'MA',          # Diversification
        'HD', 'KO', 'PFE', 'DIS', 'NFLX'          # More diversification
    ]
    
    data_dir = Path("data")
    raw_dir = data_dir / "raw"
    processed_dir = data_dir / "processed"
    
    try:
        # Step 1: Download raw data from S3
        raw_data = download_s3_data(
            START_YEAR, START_MONTH,
            END_YEAR, END_MONTH,
            raw_dir
        )
        
        # Step 2: Process and save data
        full_data, price_data = process_data(
            raw_data,
            processed_dir,
            tickers=DEFAULT_TICKERS
        )
        
        # Step 3: Generate summary
        generate_summary(price_data)
        
        print_section("COMPLETION")
        print("✓ Data preparation completed successfully!")
        print(f"✓ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nProcessed files:")
        print(f"  - {processed_dir / 'full_data_2015-11_2025-11.csv'}")
        print(f"  - {processed_dir / 'price_data_2015-11_2025-11.csv'}")
        print("\nYou can now run the demo scripts using this pre-processed data.")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
