"""Unit tests for data_retrieval module."""

import pytest
from unittest.mock import MagicMock, patch
from src.data_retrieval import get_latest_available_month, load_latest_month


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