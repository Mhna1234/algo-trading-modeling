"""Command-line script to load OHLCV data from S3."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_retrieval import load_month, load_date_range, save_to_csv


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Load OHLCV data from S3 and save as CSV.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load a single month
  python scripts/load_s3_data.py --year 2020 --month 1
  
  # Load a date range
  python scripts/load_s3_data.py --start-year 2020 --start-month 1 --end-year 2020 --end-month 3
  
  # Specify custom output path
  python scripts/load_s3_data.py --year 2020 --month 1 --output data/raw/jan2020.csv
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--year", type=int, help="4-digit year for single month load")
    
    parser.add_argument("--month", type=int, help="Month number (1-12) for single month load")
    parser.add_argument("--start-year", type=int, help="Starting year for date range")
    parser.add_argument("--start-month", type=int, help="Starting month (1-12) for date range")
    parser.add_argument("--end-year", type=int, help="Ending year for date range")
    parser.add_argument("--end-month", type=int, help="Ending month (1-12) for date range")
    parser.add_argument("--output", "-o", type=str, help="Output CSV path (default: data/YYYY-MM.csv or data/range.csv)")
    
    args = parser.parse_args()

    # Validate arguments
    if args.year is not None:
        if args.month is None:
            parser.error("--month is required when --year is specified")
        if any([args.start_year, args.start_month, args.end_year, args.end_month]):
            parser.error("Cannot use --year/--month with date range arguments")
    else:
        required_range_args = [args.start_year, args.start_month, args.end_year, args.end_month]
        if not all(required_range_args):
            parser.error("All of --start-year, --start-month, --end-year, --end-month are required for date range")

    try:
        # Load data
        if args.year is not None:
            print(f"Loading {args.year:04d}-{args.month:02d}...")
            df = load_month(args.year, args.month)
            default_output = Path("data") / f"{args.year:04d}-{args.month:02d}.csv"
        else:
            print(f"Loading range {args.start_year:04d}-{args.start_month:02d} to {args.end_year:04d}-{args.end_month:02d}...")
            df = load_date_range(args.start_year, args.start_month, args.end_year, args.end_month)
            default_output = Path("data") / f"range_{args.start_year:04d}{args.start_month:02d}-{args.end_year:04d}{args.end_month:02d}.csv"
        
        # Determine output path
        output_path = Path(args.output) if args.output else default_output
        
        # Display sample and save
        print("\nFirst few rows:")
        print(df.head())
        print(f"\nTotal rows: {len(df):,}")
        if 'symbol' in df.columns:
            print(f"Unique symbols: {df['symbol'].nunique():,}")
        
        save_to_csv(df, output_path)
        return 0
        
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
