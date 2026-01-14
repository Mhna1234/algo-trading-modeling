"""
S3 Output Verification Script for Algo Trading Strategies.

This script verifies the integrity and correctness of backtest results stored in S3.
It checks:
1. Existence of expected files (JSON, Timeseries CSV, Weights CSV).
2. Data validity (row counts, non-empty files).
3. Logic checks (e.g., Buy & Hold should have minimal rebalancing).

Results are printed to console AND saved to 'verification_report.txt' in the same directory.
"""

import boto3
import pandas as pd
import io
import os
import argparse
from datetime import datetime
import sys

# Configuration
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET', 'benchmarks-modelling-output')
OUTPUT_PREFIX = os.environ.get('OUTPUT_PREFIX', 'benchmarks-output')

# Strategies to check (can be expanded)
STRATEGIES_OF_INTEREST = ['buy_and_hold', 'equal_weight'] 

class GenericLogger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding='utf-8')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

def get_latest_execution_date(s3_client, bucket, prefix):
    """Find the most recent date folder in the history directory."""
    try:
        # List objects in history/ folder
        history_prefix = f"{prefix}/history/"
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=history_prefix, Delimiter='/')
        
        if 'CommonPrefixes' not in response:
            print(f"No history found in s3://{bucket}/{history_prefix}")
            return None
            
        # Extract dates from prefixes (format: .../history/YYYY-MM-DD/)
        dates = []
        for obj in response['CommonPrefixes']:
            folder_name = obj['Prefix'].rstrip('/').split('/')[-1]
            try:
                datetime.strptime(folder_name, '%Y-%m-%d')
                dates.append(folder_name)
            except ValueError:
                continue
                
        if not dates:
            print("No valid date folders found.")
            return None
            
        return sorted(dates)[-1]
        
    except Exception as e:
        print(f"Error finding latest date: {e}")
        return None

def verify_csv_length(df, min_rows=100):
    """Verify DataFrame has minimum number of rows."""
    if len(df) < min_rows:
        return False, f"Too few rows: {len(df)} < {min_rows}"
    return True, f"Rows: {len(df)}"

def verify_buy_and_hold_weights(df):
    """Verify Buy and Hold weights change very infrequently (ideally only once)."""
    # In a perfect Buy & Hold, we buy once. 
    # However, the system might record initial setup or slight adjustments if implemented that way.
    # We expect very few rows in the weights file (rebalance events).
    
    row_count = len(df)
    if row_count > 5: # Allow for some margin, but it shouldn't be daily/monthly for years
        return False, f"Too many rebalance events for Buy & Hold: {row_count} (Expected <= 5)"
    return True, f"Rebalance count: {row_count} (OK)"

def check_strategy_output(s3_client, date, strategy, freq):
    """Run checks for a specific strategy and frequency."""
    print(f"\nChecking {strategy} ({freq})...")
    issues = []
    
    # 1. Check Timeseries CSV
    ts_key = f"{OUTPUT_PREFIX}/timeseries/{strategy}/{freq}/{date}.csv"
    try:
        obj = s3_client.get_object(Bucket=OUTPUT_BUCKET, Key=ts_key)
        df_ts = pd.read_csv(obj['Body'])
        
        # Check integrity
        # Expecting ~2 years min (approx 252 * 2 = 504 rows)
        valid_len, msg = verify_csv_length(df_ts, min_rows=100) 
        if not valid_len:
            issues.append(f"Timeseries CSV: {msg}")
        else:
            print(f"  ✓ Timeseries data: {len(df_ts)} rows")
            
        # Check standard deviation of equity (should not be constant for valid market data)
        if df_ts['equity'].std() == 0:
            issues.append("Timeseries: Equity curve is constant (flatline).")
            
    except s3_client.exceptions.NoSuchKey:
        issues.append("Missing Timeseries CSV")
    except Exception as e:
        issues.append(f"Error reading Timeseries: {e}")

    # 2. Check Weights CSV
    w_key = f"{OUTPUT_PREFIX}/weights/{strategy}/{freq}/{date}.csv"
    try:
        obj = s3_client.get_object(Bucket=OUTPUT_BUCKET, Key=w_key)
        df_w = pd.read_csv(obj['Body'])
        
        print(f"  ✓ Weights data: {len(df_w)} rows")
        
        # Logic Checks
        if strategy == 'buy_and_hold':
            valid_bh, msg = verify_buy_and_hold_weights(df_w)
            if not valid_bh:
                issues.append(f"Logic Error (B&H): {msg}")
            else:
                print(f"  ✓ Buy & Hold Logic: {msg}")
                
        elif strategy == 'equal_weight' and freq == 'M':
            # Should have rebalanced roughly once per month
            if len(df_w) < 10:
                issues.append(f"Suspiciously low rebalance count for Monthly strategy: {len(df_w)}")
                
    except s3_client.exceptions.NoSuchKey:
        issues.append("Missing Weights CSV")
    except Exception as e:
        issues.append(f"Error reading Weights: {e}")

    # Report
    if not issues:
        print("  ✓ ALL CHECKS PASSED")
        return True
    else:
        for issue in issues:
            print(f"  ✗ {issue}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Verify S3 Backtest Outputs')
    parser.add_argument('--date', help='Specific date to check (YYYY-MM-DD)', default=None)
    args = parser.parse_args()

    # Setup file logging
    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'verification_report.txt')
    sys.stdout = GenericLogger(report_file)

    print("="*60)
    print(f"S3 VERIFICATION REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    print(f"Report saved to: {report_file}")

    s3 = boto3.client('s3')
    
    # 1. Determine Date
    check_date = args.date
    if not check_date:
        print(f"Looking for latest execution in s3://{OUTPUT_BUCKET}/{OUTPUT_PREFIX}...")
        check_date = get_latest_execution_date(s3, OUTPUT_BUCKET, OUTPUT_PREFIX)
        
    if not check_date:
        print("Could not determine date to check.")
        sys.exit(1)
        
    print(f"Verifying outputs for date: {check_date}")
    
    # 2. Run Checks
    checks = [
        ('buy_and_hold', 'M'),
        ('equal_weight', 'M'),
    ]
    
    success_count = 0
    fail_count = 0
    
    for strategy, freq in checks:
        if check_strategy_output(s3, check_date, strategy, freq):
            success_count += 1
        else:
            fail_count += 1
            
    print("\n" + "="*30)
    print(f"SUMMARY: {success_count} Passed, {fail_count} Failed")
    print("="*30)
    
    if fail_count > 0:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
