"""
Data Loading and Preprocessing Module

This module handles downloading and cleaning financial market data using yfinance.
It provides functionality to:
- Download OHLCV data for multiple tickers
- Clean missing values and align dates
- Add risk-free rate data
- Save/load processed data

Mathematical Background:
- Adjusted close prices account for splits and dividends: P_adj = P_close * adjustment_factor
- Risk-free rate approximation: R_f ≈ 0.04 / 252 (4% annual rate daily)
"""

import pandas as pd
import numpy as np
import yfinance as yf
from typing import List, Optional, Tuple, Dict
import warnings
from pathlib import Path
import logging
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataLoader:
    """
    A comprehensive data loader for financial market data.
    
    This class provides methods to download, clean, and preprocess market data
    for algorithmic trading applications.
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize DataLoader with data directory.
        
        Args:
            data_dir: Directory to store raw and processed data
        """
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        
        # Create directories if they don't exist
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        self.risk_free_rate = 0.04 / 252  # 4% annual rate, daily
        
    def download_data(self, 
                     tickers: List[str], 
                     start_date: str, 
                     end_date: str,
                     save_raw: bool = True) -> pd.DataFrame:
        """
        Download OHLCV data for multiple tickers using yfinance.
        
        Args:
            tickers: List of ticker symbols (e.g., ['AAPL', 'MSFT', 'SPY'])
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            save_raw: Whether to save raw data to disk
            
        Returns:
            DataFrame with MultiIndex columns (ticker, OHLCV)
        """
        logger.info(f"Downloading data for {tickers} from {start_date} to {end_date}")
        
        try:
            # Download data for all tickers
            data = yf.download(tickers, start=start_date, end=end_date, 
                             group_by='ticker', auto_adjust=True, 
                             prepost=True, threads=True)
            
            if len(tickers) == 1:
                # yfinance returns different structure for single ticker
                data = pd.concat([data], keys=[tickers[0]], axis=1)
                
            # Reorder columns to standard format
            data = data.reindex(columns=tickers, level=0)
            
            if save_raw:
                raw_file = self.raw_dir / f"raw_data_{start_date}_{end_date}.csv"
                data.to_csv(raw_file)
                logger.info(f"Raw data saved to {raw_file}")
                
            return data
            
        except Exception as e:
            logger.error(f"Error downloading data: {e}")
            raise
    
    def clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and preprocess the downloaded data.
        
        This method:
        - Handles missing values using forward fill
        - Removes weekends and holidays with no trading
        - Ensures all tickers have aligned dates
        
        Args:
            data: Raw OHLCV data with MultiIndex columns
            
        Returns:
            Cleaned DataFrame with aligned dates and filled missing values
        """
        logger.info("Cleaning and preprocessing data")
        
        # Get list of tickers from column MultiIndex
        tickers = data.columns.get_level_values(0).unique().tolist()
        
        # Remove rows where all tickers have NaN values
        data = data.dropna(how='all')
        
        # Forward fill missing values for each ticker
        for ticker in tickers:
            # Forward fill missing values
            data[ticker] = data[ticker].ffill()
            
            # Drop remaining NaN values at the beginning
            first_valid_idx = data[ticker].first_valid_index()
            if first_valid_idx is not None:
                data = data.loc[first_valid_idx:]
        
        # Remove any remaining rows with NaN values
        data = data.dropna()
        
        logger.info(f"Data cleaned. Shape: {data.shape}")
        return data
    
    def add_risk_free_rate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Add risk-free rate column to the dataset.
        
        The risk-free rate is approximated as a constant daily rate of 4% annual.
        In practice, this could be replaced with actual treasury bill rates.
        
        Mathematical formulation:
        R_f,daily = (1 + R_f,annual)^(1/252) - 1 ≈ R_f,annual / 252
        
        Args:
            data: DataFrame with market data
            
        Returns:
            DataFrame with additional 'RF' column for risk-free rate
        """
        # Add risk-free rate as a new column at the highest level
        risk_free_data = pd.DataFrame(
            index=data.index,
            data={'RF': self.risk_free_rate}
        )
        
        # Concatenate with existing data
        data_with_rf = pd.concat([data, risk_free_data], axis=1)
        
        logger.info(f"Added risk-free rate column (daily rate: {self.risk_free_rate:.6f})")
        return data_with_rf
    
    def get_adjusted_closes(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Extract adjusted close prices for all tickers.
        
        Args:
            data: OHLCV data with MultiIndex columns
            
        Returns:
            DataFrame with adjusted close prices for each ticker
        """
        # Check if data has MultiIndex columns
        if data.columns.nlevels == 1:
            # Data is already just prices, return as-is
            return data
            
        tickers = data.columns.get_level_values(0).unique().tolist()
        
        # Filter out 'RF' if it exists (it's not a ticker)
        tickers = [t for t in tickers if t != 'RF']
        
        closes = pd.DataFrame(index=data.index)
        
        for ticker in tickers:
            ticker_data = data[ticker]
            if isinstance(ticker_data, pd.DataFrame):
                # Case-insensitive column search
                columns_lower = {col.lower(): col for col in ticker_data.columns}

                if 'close' in columns_lower:
                    closes[ticker] = ticker_data[columns_lower['close']]
                elif 'adj close' in columns_lower:
                    closes[ticker] = ticker_data[columns_lower['adj close']]
                elif 'Close' in ticker_data.columns:
                    closes[ticker] = ticker_data['Close']
                elif 'Adj Close' in ticker_data.columns:
                    closes[ticker] = ticker_data['Adj Close']
            else:
                # Single series, assume it's the close price
                closes[ticker] = ticker_data
                
        return closes
    
    def load_data(self, 
                  tickers: List[str], 
                  start_date: str, 
                  end_date: str,
                  use_cache: bool = True) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Main method to load and process market data.
        
        This method orchestrates the entire data loading pipeline:
        1. Download raw data from yfinance
        2. Clean and preprocess the data
        3. Add risk-free rate
        4. Extract adjusted close prices
        
        Args:
            tickers: List of ticker symbols
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            use_cache: Whether to use cached processed data if available
            
        Returns:
            Tuple of (full_data, price_data):
            - full_data: Complete OHLCV data with risk-free rate
            - price_data: Adjusted close prices only
        """
        processed_file = self.processed_dir / f"processed_data_{start_date}_{end_date}.csv"
        price_file = self.processed_dir / f"price_data_{start_date}_{end_date}.csv"
        
        if use_cache and processed_file.exists() and price_file.exists():
            logger.info("Loading cached processed data")
            full_data = pd.read_csv(processed_file, index_col=0, parse_dates=True, header=[0,1])
            price_data = pd.read_csv(price_file, index_col=0, parse_dates=True)
            return full_data, price_data
        
        # Download and process data
        raw_data = self.download_data(tickers, start_date, end_date)
        clean_data = self.clean_data(raw_data)
        full_data = self.add_risk_free_rate(clean_data)
        price_data = self.get_adjusted_closes(full_data)
        
        # Save processed data
        full_data.to_csv(processed_file)
        price_data.to_csv(price_file)
        
        logger.info(f"Processed data saved to {processed_file}")
        logger.info(f"Price data saved to {price_file}")
        
        return full_data, price_data
    
    def get_data_summary(self, data: pd.DataFrame) -> Dict:
        """
        Generate a summary of the loaded data.
        
        Args:
            data: DataFrame to summarize
            
        Returns:
            Dictionary with data summary statistics
        """
        if data.columns.nlevels > 1:
            tickers = data.columns.get_level_values(0).unique().tolist()
            tickers = [t for t in tickers if t != 'RF']
        else:
            tickers = data.columns.tolist()
            tickers = [t for t in tickers if t != 'RF']
        
        summary = {
            'start_date': data.index.min().strftime('%Y-%m-%d'),
            'end_date': data.index.max().strftime('%Y-%m-%d'),
            'total_days': len(data),
            'tickers': tickers,
            'num_tickers': len(tickers),
            'missing_values': data.isnull().sum().sum(),
            'data_shape': data.shape
        }
        
        return summary

    def convert_s3_to_multiindex(self, s3_data: pd.DataFrame) -> pd.DataFrame:
        """
        Convert S3 data format to MultiIndex format used by processed data.
        
        S3 data format: symbol, date, open, high, low, close, volume (long format)
        Processed format: MultiIndex columns (ticker, OHLCV) with date index
        
        Args:
            s3_data: DataFrame from S3 with columns [symbol, date, open, high, low, close, volume]
            
        Returns:
            DataFrame with MultiIndex columns in processed format
        """
        logger.info("Converting S3 data to MultiIndex format")
        
        # Ensure date is datetime
        s3_data['date'] = pd.to_datetime(s3_data['date'])
        s3_data = s3_data.set_index('date')
        
        # Get unique symbols
        symbols = s3_data['symbol'].unique()
        
        # Create MultiIndex DataFrame
        multiindex_data = []
        columns = []
        
        for symbol in symbols:
            symbol_data = s3_data[s3_data['symbol'] == symbol].drop('symbol', axis=1)
            
            # Rename columns to match yfinance format (Close, Open, etc.)
            symbol_data = symbol_data.rename(columns={
                'open': 'Open',
                'high': 'High', 
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            })
            
            multiindex_data.append(symbol_data)
            columns.append(symbol)
        
        # Create MultiIndex DataFrame
        result = pd.concat(multiindex_data, keys=columns, axis=1)
        
        logger.info(f"Converted data for {len(symbols)} symbols")
        return result

    def append_s3_data_to_processed(self, s3_data: pd.DataFrame) -> None:
        """
        Append new S3 data to existing processed datasets.
        
        This method:
        1. Loads existing processed data
        2. Converts S3 data to compatible format
        3. Preprocesses the new data
        4. Appends to existing data
        5. Saves updated processed files
        
        Args:
            s3_data: New data from S3 in raw format
        """
        logger.info("Appending S3 data to processed datasets")
        
        # Load existing processed data
        try:
            existing_full, existing_price = load_preprocessed_data(str(self.data_dir))
            logger.info(f"Loaded existing processed data with {len(existing_price)} rows")
        except FileNotFoundError:
            logger.warning("No existing processed data found. This should not happen in incremental mode.")
            raise
        
        # Convert S3 data to MultiIndex format
        new_multiindex = self.convert_s3_to_multiindex(s3_data)
        
        # Clean and preprocess new data
        new_clean = self.clean_data(new_multiindex)
        new_full = self.add_risk_free_rate(new_clean)
        new_price = self.get_adjusted_closes(new_full)
        
        # Validate new data integrity
        if not self.validate_data_integrity(new_full):
            logger.warning("Data integrity issues detected in new S3 data, but proceeding with append")
        
        # Append to existing data
        # Use combine_first to handle overlapping dates (existing data takes precedence)
        updated_full = new_full.combine_first(existing_full)
        updated_price = new_price.combine_first(existing_price)
        
        # Sort by date
        updated_full = updated_full.sort_index()
        updated_price = updated_price.sort_index()
        
        # Get date range for filename
        start_date = updated_full.index.min().strftime('%Y-%m')
        end_date = updated_full.index.max().strftime('%Y-%m')
        
        # Save updated data
        full_file = self.processed_dir / f"full_data_{start_date}_{end_date}.csv"
        price_file = self.processed_dir / f"price_data_{start_date}_{end_date}.csv"
        
        updated_full.to_csv(full_file)
        updated_price.to_csv(price_file)
        
        logger.info(f"Updated processed data saved:")
        logger.info(f"  Full data: {full_file} ({len(updated_full)} rows)")
        logger.info(f"  Price data: {price_file} ({len(updated_price)} rows)")
        
        # Remove old files if they exist
        old_full_files = list(self.processed_dir.glob("full_data_*.csv"))
        old_price_files = list(self.processed_dir.glob("price_data_*.csv"))
        
        for old_file in old_full_files + old_price_files:
            if old_file != full_file and old_file != price_file:
                old_file.unlink()
                logger.info(f"Removed old file: {old_file}")

    def detect_data_gaps(self, data: pd.DataFrame, log_gaps: bool = True) -> Dict:
        """
        Detect gaps in trading data and categorize them as expected or unexpected.
        
        Expected gaps: Weekends and US federal holidays
        Unexpected gaps: Missing data on business days (potential data issues)
        
        Args:
            data: DataFrame with datetime index
            log_gaps: Whether to log gap information
            
        Returns:
            Dictionary with gap statistics and details
        """
        logger = logging.getLogger(__name__)
        
        if data.empty:
            return {'total_gaps': 0, 'expected_gaps': 0, 'unexpected_gaps': 0, 'gap_dates': []}
        
        # Get date range
        start_date = data.index.min()
        end_date = data.index.max()
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Create business day calendar (excluding weekends and US holidays)
        bday = CustomBusinessDay(calendar=USFederalHolidayCalendar())
        business_days = pd.date_range(start=start_date, end=end_date, freq=bday)
        
        # Find all missing dates
        existing_dates = set(data.index.date)
        all_dates = set(date_range.date)
        missing_dates = all_dates - existing_dates
        
        # Categorize gaps
        expected_gaps = []
        unexpected_gaps = []
        
        for missing_date in missing_dates:
            missing_datetime = pd.Timestamp(missing_date)
            
            # Check if it's a business day
            is_business_day = missing_datetime in business_days
            
            if is_business_day:
                unexpected_gaps.append(missing_date)
                if log_gaps:
                    logger.warning(f"Unexpected data gap on business day: {missing_date}")
            else:
                expected_gaps.append(missing_date)
                if log_gaps:
                    logger.info(f"Expected data gap (weekend/holiday): {missing_date}")
        
        gap_stats = {
            'total_gaps': len(missing_dates),
            'expected_gaps': len(expected_gaps),
            'unexpected_gaps': len(unexpected_gaps),
            'expected_gap_dates': expected_gaps,
            'unexpected_gap_dates': unexpected_gaps,
            'data_completeness': len(existing_dates) / len(date_range) if date_range.size > 0 else 0
        }
        
        if log_gaps:
            logger.info(f"Data gap analysis: {gap_stats['total_gaps']} total gaps "
                       f"({gap_stats['expected_gaps']} expected, {gap_stats['unexpected_gaps']} unexpected), "
                       f"completeness: {gap_stats['data_completeness']:.1%}")
        
        return gap_stats

    def validate_data_integrity(self, data: pd.DataFrame) -> bool:
        """
        Validate data integrity and log any issues.
        
        Checks for:
        - Data gaps (expected vs unexpected)
        - Price continuity (no extreme jumps)
        - Volume reasonableness
        
        Args:
            data: DataFrame to validate
            
        Returns:
            True if data passes all checks, False otherwise
        """
        logger = logging.getLogger(__name__)
        is_valid = True
        
        # Check for data gaps
        gap_stats = self.detect_data_gaps(data)
        
        # Check for price continuity (basic outlier detection)
        if data.columns.nlevels > 1:
            # MultiIndex columns - check Close prices
            for symbol in data.columns.get_level_values(0).unique():
                if symbol == 'RF':  # Skip risk-free rate
                    continue
                close_prices = data[(symbol, 'Close')] if ('Close') in data[symbol].columns else data[symbol]
                if hasattr(close_prices, 'pct_change'):
                    returns = close_prices.pct_change()
                    extreme_returns = returns.abs() > 0.5  # 50% daily change threshold
                    if extreme_returns.any():
                        extreme_dates = returns[extreme_returns].index.strftime('%Y-%m-%d').tolist()
                        logger.warning(f"Extreme price movements detected for {symbol} on: {extreme_dates}")
                        is_valid = False
        else:
            # Single level columns
            for col in data.columns:
                if col == 'RF':
                    continue
                if hasattr(data[col], 'pct_change'):
                    returns = data[col].pct_change()
                    extreme_returns = returns.abs() > 0.5
                    if extreme_returns.any():
                        extreme_dates = returns[extreme_returns].index.strftime('%Y-%m-%d').tolist()
                        logger.warning(f"Extreme price movements detected for {col} on: {extreme_dates}")
                        is_valid = False
        
        # Check for zero/negative prices
        if data.columns.nlevels > 1:
            for symbol in data.columns.get_level_values(0).unique():
                if symbol == 'RF':
                    continue
                close_col = (symbol, 'Close') if (symbol, 'Close') in data.columns else None
                if close_col and (data[close_col] <= 0).any():
                    bad_dates = data[data[close_col] <= 0].index.strftime('%Y-%m-%d').tolist()
                    logger.error(f"Invalid prices (≤0) detected for {symbol} on: {bad_dates}")
                    is_valid = False
        else:
            for col in data.columns:
                if col == 'RF':
                    continue
                if (data[col] <= 0).any():
                    bad_dates = data[data[col] <= 0].index.strftime('%Y-%m-%d').tolist()
                    logger.error(f"Invalid prices (≤0) detected for {col} on: {bad_dates}")
                    is_valid = False
        
        return is_valid


def load_data(tickers: List[str], 
              start: str, 
              end: str,
              data_dir: str = "data") -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Convenience function to load market data.
    
    Args:
        tickers: List of ticker symbols
        start: Start date in 'YYYY-MM-DD' format
        end: End date in 'YYYY-MM-DD' format
        data_dir: Directory for data storage
        
    Returns:
        Tuple of (full_data, price_data)
    """
    loader = DataLoader(data_dir)
    return loader.load_data(tickers, start, end)


def load_preprocessed_data(data_dir: str = "data",
                           start: Optional[str] = None,
                           end: Optional[str] = None,
                           update_if_available: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load pre-processed data from disk (prepared by scripts/prepare_data.py).
    
    This function loads the full dataset that was already downloaded from S3
    and processed. It's much faster than downloading data from yfinance.
    
    Args:
        data_dir: Directory containing processed data
        start: Optional start date to filter data (format: 'YYYY-MM-DD')
        end: Optional end date to filter data (format: 'YYYY-MM-DD')
        update_if_available: If True, check for and append new data from S3
        
    Returns:
        Tuple of (full_data, price_data)
        - full_data: Complete OHLCV data with risk-free rate
        - price_data: Adjusted close prices only
        
    Example:
        >>> # Load all pre-processed data
        >>> full_data, price_data = load_preprocessed_data()
        >>> 
        >>> # Load with automatic updates
        >>> full_data, price_data = load_preprocessed_data(update_if_available=True)
        >>> 
        >>> # Load specific date range
        >>> full_data, price_data = load_preprocessed_data(
        ...     start='2020-01-01', 
        ...     end='2023-12-31'
        ... )
    """
    data_path = Path(data_dir)
    processed_dir = data_path / "processed"
    
    # Look for the latest pre-processed files
    full_data_file = processed_dir / "full_data_2015-11_2025-11.csv"
    price_data_file = processed_dir / "price_data_2015-11_2025-11.csv"
    
    if not full_data_file.exists() or not price_data_file.exists():
        raise FileNotFoundError(
            f"Pre-processed data not found in {processed_dir}\n"
            "Please run: python scripts/prepare_data.py"
        )
    
    logger.info(f"Loading pre-processed data from {processed_dir}")
    
    # Load data
    try:
        # Load full data with MultiIndex columns
        full_data = pd.read_csv(full_data_file, index_col=0, parse_dates=True, header=[0, 1])
    except Exception:
        # Fallback: try loading without MultiIndex
        full_data = pd.read_csv(full_data_file, index_col=0, parse_dates=True)
    
    # Load price data
    price_data = pd.read_csv(price_data_file, index_col=0, parse_dates=True)
    
    # Check for and append new data if requested
    if update_if_available:
        logger.info("Checking for new data to append...")
        try:
            from .data_retrieval import update_processed_data
            updated_full, updated_price = update_processed_data(data_dir)
            if updated_full is not None and updated_price is not None:
                logger.info("New data found and appended to processed datasets")
                full_data = updated_full
                price_data = updated_price
            else:
                logger.info("No new data available")
        except Exception as e:
            logger.warning(f"Failed to check for updates: {e}")
            logger.info("Continuing with existing data")
    
    # Filter by date range if specified
    if start is not None:
        start_date = pd.to_datetime(start)
        full_data = full_data[full_data.index >= start_date]
        price_data = price_data[price_data.index >= start_date]
    
    if end is not None:
        end_date = pd.to_datetime(end)
        full_data = full_data[full_data.index <= end_date]
        price_data = price_data[price_data.index <= end_date]
    
    logger.info(f"Loaded {len(price_data)} rows with {len(price_data.columns)} tickers")
    if start or end:
        logger.info(f"Filtered to date range: {price_data.index.min()} to {price_data.index.max()}")
    
    return full_data, price_data


if __name__ == "__main__":
    # Example usage
    tickers = ['AAPL', 'MSFT', 'SPY', 'QQQ']
    start_date = '2020-01-01'
    end_date = '2024-01-01'
    
    # Load data
    full_data, price_data = load_data(tickers, start_date, end_date)
    
    # Create loader instance for summary
    loader = DataLoader()
    summary = loader.get_data_summary(price_data)
    
    print("Data Summary:")
    for key, value in summary.items():
        print(f"{key}: {value}")
    
    print(f"\nPrice data shape: {price_data.shape}")
    print(f"Price data head:\n{price_data.head()}")