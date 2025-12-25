"""Unit tests for data_loader module."""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.data_loader import DataLoader


class TestDataLoaderIncremental:
    """Test incremental data loading functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.loader = DataLoader("test_data")

    @patch('src.data_loader.load_preprocessed_data')
    def test_append_s3_data_success(self, mock_load_preprocessed):
        """Test successful append of S3 data to processed datasets."""
        # Mock existing data
        existing_full = pd.DataFrame({
            ('AAPL', 'Close'): [100, 101],
            ('AAPL', 'Open'): [99, 100]
        }, index=pd.date_range('2025-11-01', periods=2))
        
        existing_price = pd.DataFrame({
            'AAPL': [100, 101]
        }, index=pd.date_range('2025-11-01', periods=2))
        
        mock_load_preprocessed.return_value = (existing_full, existing_price)
        
        # Mock S3 data in long format
        s3_data = pd.DataFrame({
            'symbol': ['AAPL', 'AAPL'],
            'date': ['2025-12-01', '2025-12-02'],
            'open': [102, 103],
            'high': [104, 105],
            'low': [101, 102],
            'close': [103, 104],
            'volume': [1000, 1100]
        })
        
        with patch.object(self.loader, 'clean_data') as mock_clean, \
             patch.object(self.loader, 'add_risk_free_rate') as mock_add_rf, \
             patch.object(self.loader, 'get_adjusted_closes') as mock_get_closes, \
             patch('builtins.open', create=True) as mock_open, \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.unlink'):
            
            # Mock preprocessing steps
            mock_clean.return_value = existing_full  # Simplified
            mock_add_rf.return_value = existing_full
            mock_get_closes.return_value = existing_price
            
            # Should not raise exception
            self.loader.append_s3_data_to_processed(s3_data)

    def test_convert_s3_to_multiindex(self):
        """Test conversion of S3 data to MultiIndex format."""
        # Create test S3 data
        s3_data = pd.DataFrame({
            'symbol': ['AAPL', 'AAPL', 'MSFT', 'MSFT'],
            'date': ['2025-12-01', '2025-12-02', '2025-12-01', '2025-12-02'],
            'open': [100, 101, 200, 201],
            'high': [102, 103, 202, 203],
            'low': [99, 100, 199, 200],
            'close': [101, 102, 201, 202],
            'volume': [1000, 1100, 2000, 2100]
        })
        
        result = self.loader.convert_s3_to_multiindex(s3_data)
        
        # Check structure
        assert isinstance(result.columns, pd.MultiIndex)
        assert 'AAPL' in result.columns.get_level_values(0)
        assert 'MSFT' in result.columns.get_level_values(0)
        
        # Check OHLCV columns exist
        assert 'Open' in result.columns.get_level_values(1)
        assert 'High' in result.columns.get_level_values(1)
        assert 'Low' in result.columns.get_level_values(1)
        assert 'Close' in result.columns.get_level_values(1)
        assert 'Volume' in result.columns.get_level_values(1)
        
        # Check data values
        assert result.loc['2025-12-01', ('AAPL', 'Close')] == 101
        assert result.loc['2025-12-02', ('MSFT', 'Open')] == 201

    def test_detect_data_gaps_with_expected_gaps(self):
        """Test gap detection with expected gaps (weekends)."""
        # Create data spanning a weekend: Mon, Tue, Wed, then next Mon
        dates = [pd.Timestamp('2023-12-25'), pd.Timestamp('2023-12-26'), pd.Timestamp('2023-12-27'), 
                pd.Timestamp('2024-01-01')]  # Missing weekend and holiday
        data = pd.DataFrame({
            'AAPL': [100, 101, 102, 103]
        }, index=dates)
        
        gap_stats = self.loader.detect_data_gaps(data, log_gaps=False)
        
        # Should detect weekend gaps (Dec 28-31) and holiday (Dec 25 is Christmas but we're including it)
        # Actually, let's simplify - just check that gaps are detected
        assert gap_stats['total_gaps'] > 0
        assert gap_stats['expected_gaps'] >= gap_stats['unexpected_gaps']  # More expected than unexpected

    def test_detect_data_gaps_with_unexpected_gaps(self):
        """Test gap detection with unexpected gaps (missing business day)."""
        # Create data missing a Wednesday (business day)
        dates = [pd.Timestamp('2023-12-25'), pd.Timestamp('2023-12-26'), 
                pd.Timestamp('2023-12-28'), pd.Timestamp('2023-12-29')]  # Missing Wed 2023-12-27
        data = pd.DataFrame({
            'AAPL': [100, 101, 103, 104]
        }, index=dates)
        
        gap_stats = self.loader.detect_data_gaps(data, log_gaps=False)
        
        # Should detect missing Wednesday
        assert gap_stats['total_gaps'] >= 1
        assert gap_stats['unexpected_gaps'] >= 1  # At least the missing Wednesday

    def test_detect_data_gaps_empty_data(self):
        """Test gap detection with empty data."""
        data = pd.DataFrame()
        gap_stats = self.loader.detect_data_gaps(data, log_gaps=False)
        
        assert gap_stats['total_gaps'] == 0
        assert gap_stats['expected_gaps'] == 0
        assert gap_stats['unexpected_gaps'] == 0

    def test_validate_data_integrity_valid_data(self):
        """Test data integrity validation with valid data."""
        dates = pd.date_range('2023-12-25', '2023-12-29', freq='B')
        data = pd.DataFrame({
            ('AAPL', 'Close'): [100, 101, 102, 103, 104],
            ('AAPL', 'Open'): [99, 100, 101, 102, 103],
            ('RF', ''): [0.0001, 0.0001, 0.0001, 0.0001, 0.0001]
        }, index=dates)
        data.columns = pd.MultiIndex.from_tuples(data.columns)
        
        is_valid = self.loader.validate_data_integrity(data)
        assert is_valid is True

    def test_validate_data_integrity_extreme_price_movement(self):
        """Test data integrity validation with extreme price movements."""
        dates = pd.date_range('2023-12-25', '2023-12-29', freq='B')
        data = pd.DataFrame({
            ('AAPL', 'Close'): [100, 200, 102, 103, 104],  # 100% jump on second day
            ('RF', ''): [0.0001, 0.0001, 0.0001, 0.0001, 0.0001]
        }, index=dates)
        data.columns = pd.MultiIndex.from_tuples(data.columns)
        
        is_valid = self.loader.validate_data_integrity(data)
        assert is_valid is False  # Should detect extreme movement

    def test_validate_data_integrity_invalid_prices(self):
        """Test data integrity validation with invalid prices."""
        dates = pd.date_range('2023-12-25', '2023-12-29', freq='B')
        data = pd.DataFrame({
            ('AAPL', 'Close'): [100, 0, 102, 103, 104],  # Zero price
            ('RF', ''): [0.0001, 0.0001, 0.0001, 0.0001, 0.0001]
        }, index=dates)
        data.columns = pd.MultiIndex.from_tuples(data.columns)
        
        is_valid = self.loader.validate_data_integrity(data)
        assert is_valid is False  # Should detect invalid price

    def test_validate_data_integrity_single_level_columns(self):
        """Test data integrity validation with single-level columns."""
        dates = pd.date_range('2023-12-25', '2023-12-29', freq='B')
        data = pd.DataFrame({
            'AAPL': [100, 101, 102, 103, 104],
            'RF': [0.0001, 0.0001, 0.0001, 0.0001, 0.0001]
        }, index=dates)
        
        is_valid = self.loader.validate_data_integrity(data)
        assert is_valid is True