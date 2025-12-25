"""Unit tests for data_retrieval module."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.data_retrieval import (
    get_latest_available_month, 
    load_latest_month,
    parse_date_range_from_filename,
    get_local_data_date_range,
    get_missing_date_range,
    load_missing_data,
    update_processed_data
)


class TestGetLatestAvailableMonth:
    """Test get_latest_available_month function."""

    @patch('boto3.client')
    def test_successful_retrieval(self, mock_boto3_client):
        """Test successful retrieval of latest month."""
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3

        # Mock list_objects_v2 response
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'history-data/2020-01.parquet'},
                {'Key': 'history-data/2020-02.parquet'},
                {'Key': 'history-data/2020-03.parquet'},
                {'Key': 'history-data/2021-01.parquet'},
            ]
        }

        year, month = get_latest_available_month()

        assert year == 2021
        assert month == 1
        mock_s3.list_objects_v2.assert_called_once_with(
            Bucket="data-retrieval-output",
            Prefix="history-data/"
        )

    @patch('boto3.client')
    def test_no_contents(self, mock_boto3_client):
        """Test when no objects are found."""
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        mock_s3.list_objects_v2.return_value = {}

        with pytest.raises(FileNotFoundError, match="No history-data files found"):
            get_latest_available_month()

    @patch('boto3.client')
    def test_no_valid_files(self, mock_boto3_client):
        """Test when objects exist but no valid parquet files."""
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'history-data/README.txt'},
                {'Key': 'other-folder/file.txt'},
            ]
        }

        with pytest.raises(FileNotFoundError, match="No valid history-data files found"):
            get_latest_available_month()

    @patch('boto3.client')
    def test_malformed_keys(self, mock_boto3_client):
        """Test handling of malformed keys."""
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'history-data/2020-01.parquet'},
                {'Key': 'history-data/invalid-date.parquet'},
                {'Key': 'history-data/2020-13.parquet'},  # Invalid month
            ]
        }

        year, month = get_latest_available_month()

        assert year == 2020
        assert month == 1

    @patch('boto3.client')
    def test_no_credentials(self, mock_boto3_client):
        """Test NoCredentialsError handling."""
        from botocore.exceptions import NoCredentialsError
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        mock_s3.list_objects_v2.side_effect = NoCredentialsError()

        with pytest.raises(RuntimeError, match="AWS credentials not found"):
            get_latest_available_month()

    @patch('boto3.client')
    def test_access_denied(self, mock_boto3_client):
        """Test AccessDenied error handling."""
        from botocore.exceptions import ClientError
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        error = ClientError({'Error': {'Code': 'AccessDenied'}}, 'ListObjectsV2')
        mock_s3.list_objects_v2.side_effect = error

        with pytest.raises(PermissionError, match="Access denied when listing S3 objects"):
            get_latest_available_month()


class TestLoadLatestMonth:
    """Test load_latest_month function."""

    @patch('src.data_retrieval.get_latest_available_month')
    @patch('src.data_retrieval.load_month')
    def test_successful_load(self, mock_load_month, mock_get_latest):
        """Test successful loading of latest month."""
        import pandas as pd

        mock_get_latest.return_value = (2021, 1)
        mock_df = pd.DataFrame({'symbol': ['AAPL'], 'date': ['2021-01-01']})
        mock_load_month.return_value = mock_df

        result = load_latest_month()

        assert result.equals(mock_df)
        mock_get_latest.assert_called_once()
        mock_load_month.assert_called_once_with(2021, 1)


class TestParseDateRangeFromFilename:
    """Test parse_date_range_from_filename function."""

    def test_valid_filename(self):
        """Test parsing valid filename."""
        result = parse_date_range_from_filename("data_2015-11_2025-11.csv")
        assert result == (2015, 11, 2025, 11)

    def test_valid_filename_with_prefix(self):
        """Test parsing filename with prefix."""
        result = parse_date_range_from_filename("full_data_2020-01_2023-12.csv")
        assert result == (2020, 1, 2023, 12)

    def test_invalid_filename_no_dates(self):
        """Test parsing filename without date pattern."""
        with pytest.raises(ValueError, match="Could not parse date range"):
            parse_date_range_from_filename("data.csv")

    def test_invalid_month(self):
        """Test parsing filename with invalid month."""
        with pytest.raises(ValueError, match="Invalid month 13"):
            parse_date_range_from_filename("data_2020-13_2021-01.csv")


class TestGetLocalDataDateRange:
    """Test get_local_data_date_range function."""

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.glob')
    def test_successful_parsing(self, mock_glob, mock_exists):
        """Test successful parsing of local data range."""
        mock_exists.return_value = True
        
        # Mock file paths
        mock_file1 = MagicMock()
        mock_file1.name = "full_data_2015-11_2020-12.csv"
        mock_file2 = MagicMock()
        mock_file2.name = "price_data_2021-01_2025-11.csv"
        
        mock_glob.return_value = [mock_file1, mock_file2]

        result = get_local_data_date_range()
        assert result == (2015, 11, 2025, 11)  # earliest start, latest end

    @patch('pathlib.Path.exists')
    def test_directory_not_found(self, mock_exists):
        """Test when data directory doesn't exist."""
        mock_exists.return_value = False
        
        with pytest.raises(FileNotFoundError, match="Data directory not found"):
            get_local_data_date_range()

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.glob')
    def test_no_csv_files(self, mock_glob, mock_exists):
        """Test when no CSV files exist."""
        mock_exists.return_value = True
        mock_glob.return_value = []
        
        with pytest.raises(FileNotFoundError, match="No CSV files found"):
            get_local_data_date_range()

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.glob')
    def test_no_valid_files(self, mock_glob, mock_exists):
        """Test when CSV files exist but don't match pattern."""
        mock_exists.return_value = True
        
        mock_file = MagicMock()
        mock_file.name = "invalid_file.csv"
        mock_glob.return_value = [mock_file]
        
        with pytest.raises(FileNotFoundError, match="No files with valid date ranges found"):
            get_local_data_date_range()


class TestGetMissingDateRange:
    """Test get_missing_date_range function."""

    @patch('src.data_retrieval.get_local_data_date_range')
    @patch('src.data_retrieval.date')
    def test_missing_months(self, mock_date_class, mock_get_local):
        """Test calculating missing months."""
        from datetime import date
        
        # Mock local data ends at 2025-11
        mock_get_local.return_value = (2015, 11, 2025, 11)
        
        # Mock date.today() to return Dec 25, 2025
        mock_today = date(2025, 12, 25)
        mock_date_class.today.return_value = mock_today
        
        # Mock date() constructor to return actual date objects for comparisons
        original_date = date
        def mock_date_constructor(*args):
            if len(args) == 3:  # date(year, month, day)
                return original_date(*args)
            return MagicMock()
        mock_date_class.side_effect = mock_date_constructor
        
        result = get_missing_date_range()
        assert result == [(2025, 12)]  # Should fetch December 2025

    @patch('src.data_retrieval.get_local_data_date_range')
    @patch('src.data_retrieval.date')
    def test_no_missing_months(self, mock_date_class, mock_get_local):
        """Test when local data is up to current month."""
        from datetime import date
        
        # Mock local data ends at current month
        mock_get_local.return_value = (2015, 11, 2025, 12)
        
        # Mock date.today() to return Dec 25, 2025
        mock_today = date(2025, 12, 25)
        mock_date_class.today.return_value = mock_today
        
        # Mock date() constructor
        original_date = date
        def mock_date_constructor(*args):
            if len(args) == 3:
                return original_date(*args)
            return MagicMock()
        mock_date_class.side_effect = mock_date_constructor
        
        result = get_missing_date_range()
        assert result == []  # No missing months

    @patch('src.data_retrieval.get_local_data_date_range')
    def test_no_local_data(self, mock_get_local):
        """Test when no local data exists."""
        mock_get_local.side_effect = FileNotFoundError("No local data")
        
        with pytest.raises(FileNotFoundError, match="Cannot determine missing date range"):
            get_missing_date_range()


class TestLoadMissingData:
    """Test load_missing_data function."""

    @patch('src.data_retrieval.get_missing_date_range')
    @patch('src.data_retrieval.load_multiple_months')
    def test_successful_load(self, mock_load_multiple, mock_get_missing):
        """Test successful loading of missing data."""
        mock_get_missing.return_value = [(2025, 12)]
        mock_df = MagicMock()
        mock_load_multiple.return_value = mock_df

        result = load_missing_data()
        assert result == mock_df
        mock_load_multiple.assert_called_once_with([(2025, 12)])

    @patch('src.data_retrieval.get_missing_date_range')
    def test_no_missing_data(self, mock_get_missing):
        """Test when no missing data to fetch."""
        mock_get_missing.return_value = []
        
        with pytest.raises(FileNotFoundError, match="No missing data to fetch"):
            load_missing_data()


class TestUpdateProcessedData:
    """Test update_processed_data function."""

    @patch('src.data_retrieval.get_missing_date_range')
    def test_no_missing_data(self, mock_get_missing):
        """Test when no data needs to be updated."""
        mock_get_missing.return_value = []
        
        # Should not raise an exception, just return
        update_processed_data()

    @patch('src.data_retrieval.get_missing_date_range')
    def test_no_processed_data_found(self, mock_get_missing):
        """Test when no processed data exists."""
        mock_get_missing.side_effect = FileNotFoundError("No processed data")
        
        # Should not raise an exception, just return
        update_processed_data()

    @patch('src.data_retrieval.load_multiple_months')
    @patch('src.data_retrieval.get_missing_date_range')
    @patch('src.data_loader.DataLoader')
    def test_successful_update(self, mock_data_loader_class, mock_get_missing, mock_load_multiple):
        """Test successful data update."""
        # Mock missing months
        mock_get_missing.return_value = [(2025, 12)]
        
        # Mock new data
        mock_new_data = MagicMock()
        mock_load_multiple.return_value = mock_new_data
        
        # Mock DataLoader
        mock_loader = MagicMock()
        mock_data_loader_class.return_value = mock_loader
        
        update_processed_data()
        
        # Verify calls
        mock_get_missing.assert_called_once()
        mock_load_multiple.assert_called_once_with([(2025, 12)])
        mock_data_loader_class.assert_called_once_with("data")
        mock_loader.append_s3_data_to_processed.assert_called_once_with(mock_new_data)

    @patch('src.data_retrieval.load_multiple_months')
    @patch('src.data_retrieval.get_missing_date_range')
    def test_s3_fetch_error(self, mock_get_missing, mock_load_multiple):
        """Test handling of S3 fetch errors."""
        mock_get_missing.return_value = [(2025, 12)]
        mock_load_multiple.side_effect = Exception("S3 error")
        
        # Should not raise exception, just print error
        update_processed_data()

    @patch('src.data_retrieval.load_multiple_months')
    @patch('src.data_retrieval.get_missing_date_range')
    @patch('src.data_loader.DataLoader')
    def test_append_error(self, mock_data_loader_class, mock_get_missing, mock_load_multiple):
        """Test handling of append errors."""
        mock_get_missing.return_value = [(2025, 12)]
        mock_load_multiple.return_value = MagicMock()
        
        mock_loader = MagicMock()
        mock_loader.append_s3_data_to_processed.side_effect = Exception("Append error")
        mock_data_loader_class.return_value = mock_loader
        
        with pytest.raises(Exception, match="Append error"):
            update_processed_data()