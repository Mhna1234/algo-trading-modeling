"""
Local Lambda Partition Function Test
Tests the lambda_function_partition_X.py handlers locally before AWS deployment.
"""

import json
import sys
from datetime import datetime
from unittest.mock import Mock


class MockContext:
    """Mock Lambda context for local testing."""
    def __init__(self, partition_id):
        self.function_name = f"benchmark-calculator-partition-{partition_id}"
        self.memory_limit_in_mb = 3008
        self.invoked_function_arn = f"arn:aws:lambda:eu-north-1:123456789012:function:benchmark-calculator-partition-{partition_id}"
        self.aws_request_id = f"test-request-id-partition-{partition_id}"

    def get_remaining_time_in_millis(self):
        return 900000  # 15 minutes


def test_partition_imports(partition_id):
    """Test that partition Lambda function imports correctly."""
    print(f"\n=== Testing Partition {partition_id} Import ===")
    try:
        # Import the partition module
        import importlib
        module_name = f"lambda_function_partition_{partition_id}"
        module = importlib.import_module(module_name)
        print(f"✓ {module_name}.py imports successfully")
        return True, module
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False, None


def test_partition_handler(partition_id):
    """Test the Lambda handler for a partition."""
    print(f"\n=== Testing Partition {partition_id} Handler ===")
    print("Note: This test will attempt to access S3 buckets.")
    print("It may fail if data for current month is not available.")

    success, module = test_partition_imports(partition_id)
    if not success:
        return False

    try:
        # Get the lambda_handler from the imported module
        lambda_handler = module.lambda_handler

        event = {
            "test": True,
            "execution_date": datetime.now().strftime('%Y-%m-%d')
        }

        context = MockContext(partition_id)

        print(f"Running Partition {partition_id} Lambda handler (may take several minutes)...")
        result = lambda_handler(event, context)

        print(f"\nResponse from Partition {partition_id}:")
        print(f"  Status Code: {result['statusCode']}")
        print(f"  Partition ID: {result.get('partition_id', 'N/A')}")
        print(f"  Execution Date: {result.get('execution_date', 'N/A')}")
        print(f"  Duration: {result.get('duration_seconds', 0):.2f}s")

        if result['statusCode'] == 200:
            print(f"  Successful: {result.get('successful', 0)}/{result.get('total_backtests', 0)} backtests")
            print(f"  Failed: {result.get('failed', 0)}")
            print(f"  S3 Files Written: {result.get('s3_files_written', 0)}")
            print(f"✓ Partition {partition_id} completed successfully")
            return True
        else:
            print(f"✗ Partition {partition_id} failed:")
            print(f"  Error: {result.get('error_message', 'Unknown error')}")
            if 'error_traceback' in result:
                print(f"  Traceback:\n{result['error_traceback']}")
            return False

    except Exception as e:
        print(f"✗ Partition {partition_id} test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run tests for all partition Lambda functions."""
    print("=" * 60)
    print("AWS Lambda Partition Functions - Local Testing")
    print("=" * 60)

    partitions = [1, 2, 3]
    results = []

    for partition_id in partitions:
        result = test_partition_handler(partition_id)
        results.append((f"Partition {partition_id}", result))
        print()

    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")

    total_passed = sum(1 for _, passed in results if passed)
    print(f"\nTotal: {total_passed}/{len(results)} partitions passed")

    if all(passed for _, passed in results):
        print("\n🎉 All partitions passed! Ready for AWS deployment.")
        return 0
    else:
        print("\n⚠ Some partitions failed. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
