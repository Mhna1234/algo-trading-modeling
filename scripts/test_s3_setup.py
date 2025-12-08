"""Test script to verify S3 data retrieval setup."""

import os
import sys
from pathlib import Path

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded credentials from {env_path}")
    else:
        print(f"No .env file found at {env_path}")
        print("Checking for system AWS credentials...")
except ImportError:
    print("python-dotenv not installed, checking system AWS credentials...")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

def test_aws_connection():
    """Test AWS credentials and connection."""
    import boto3
    from botocore.exceptions import NoCredentialsError, PartialCredentialsError
    
    print("\n=== Testing AWS Connection ===")
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print("✓ AWS credentials are configured!")
        print(f"  Account: {identity['Account']}")
        print(f"  User ARN: {identity['Arn']}")
        return True
    except NoCredentialsError:
        print("✗ No AWS credentials found!")
        print("\nTo configure credentials:")
        print("  1. Copy .env.example to .env")
        print("  2. Add your AWS credentials to .env")
        print("  3. Or run: aws configure")
        return False
    except PartialCredentialsError:
        print("✗ Incomplete AWS credentials!")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_s3_bucket_access():
    """Test access to the S3 bucket."""
    import boto3
    from botocore.exceptions import ClientError
    
    print("\n=== Testing S3 Bucket Access ===")
    try:
        s3 = boto3.client('s3')
        # Try to list objects with a prefix to verify bucket access
        response = s3.list_objects_v2(
            Bucket='data-retrieval-output',
            Prefix='history-data/',
            MaxKeys=5
        )
        
        if 'Contents' in response:
            print("✓ S3 bucket 'data-retrieval-output' is accessible!")
            print(f"  Found {len(response.get('Contents', []))} sample files")
            print("\n  Sample files:")
            for obj in response.get('Contents', [])[:5]:
                key = obj['Key']
                size_mb = obj['Size'] / (1024 * 1024)
                print(f"    - {key} ({size_mb:.2f} MB)")
            return True
        else:
            print("✗ No files found in bucket")
            return False
            
    except ClientError as exc:
        error_code = exc.response.get('Error', {}).get('Code')
        if error_code == 'NoSuchBucket':
            print("✗ Bucket 'data-retrieval-output' not found!")
        elif error_code == 'AccessDenied':
            print("✗ Access denied to bucket!")
            print("  Verify your IAM permissions.")
        else:
            print(f"✗ Error: {exc}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_load_sample_month():
    """Test loading a sample month of data."""
    from data_retrieval import load_month
    
    print("\n=== Testing Data Load ===")
    print("Attempting to load January 2020...")
    
    try:
        df = load_month(2020, 1)
        print(f"✓ Successfully loaded data!")
        print(f"  Rows: {len(df):,}")
        print(f"  Columns: {list(df.columns)}")
        if 'symbol' in df.columns:
            print(f"  Unique symbols: {df['symbol'].nunique():,}")
        if 'date' in df.columns:
            print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
        
        print("\n  Sample data:")
        print(df.head())
        return True
        
    except FileNotFoundError as e:
        print(f"✗ File not found: {e}")
        print("  The requested month may not exist in S3")
        return False
    except Exception as e:
        print(f"✗ Error loading data: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("S3 Data Retrieval Setup Test")
    print("=" * 60)
    
    # Test imports
    print("\n=== Testing Dependencies ===")
    try:
        import boto3
        import pyarrow
        import pandas as pd
        print(f"✓ boto3 version: {boto3.__version__}")
        print(f"✓ pyarrow version: {pyarrow.__version__}")
        print(f"✓ pandas version: {pd.__version__}")
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("\nInstall with: pip install boto3 pyarrow pandas")
        return 1
    
    # Test AWS connection
    if not test_aws_connection():
        print("\n" + "=" * 60)
        print("Setup incomplete. Configure AWS credentials first.")
        print("=" * 60)
        return 1
    
    # Test S3 access
    if not test_s3_bucket_access():
        print("\n" + "=" * 60)
        print("Cannot access S3 bucket. Check permissions.")
        print("=" * 60)
        return 1
    
    # Test data loading
    if not test_load_sample_month():
        print("\n" + "=" * 60)
        print("Data loading failed. Check error messages above.")
        print("=" * 60)
        return 1
    
    # All tests passed
    print("\n" + "=" * 60)
    print("✓ All tests passed! Setup is complete.")
    print("=" * 60)
    print("\nYou can now use:")
    print("  python scripts/load_s3_data.py --year 2020 --month 1")
    print("\nOr in Python:")
    print("  from src.data_retrieval import load_month")
    print("  df = load_month(2020, 1)")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
