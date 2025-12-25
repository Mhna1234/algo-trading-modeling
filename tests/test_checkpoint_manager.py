"""Unit tests for checkpoint_manager module."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

import pandas as pd
from pandas import Series, DataFrame

from src.checkpoint_manager import CheckpointManager
from src.portfolio_engine import PortfolioResult


@pytest.fixture
def sample_portfolio_result():
    """Create a sample PortfolioResult for testing."""
    # Create sample data
    dates = pd.date_range('2020-01-01', periods=100, freq='D')
    assets = ['AAPL', 'MSFT', 'GOOGL', 'CASH']
    
    equity_curve = Series([1_000_000 + i * 1000 for i in range(100)], index=dates)
    returns_series = Series([0.01] * 100, index=dates)
    drawdown_series = Series([0.0] * 100, index=dates)
    turnover_history = Series([0.05] * 100, index=dates)
    transaction_costs = Series([100] * 100, index=dates)
    slippage_costs = Series([50] * 100, index=dates)
    cash_history = Series([100_000] * 100, index=dates)
    
    weights_history = DataFrame({
        'AAPL': [0.25] * 100,
        'MSFT': [0.25] * 100,
        'GOOGL': [0.25] * 100,
        'CASH': [0.25] * 100
    }, index=dates)
    
    trades_history = DataFrame({
        'AAPL': [0.0] * 100,
        'MSFT': [0.0] * 100,
        'GOOGL': [0.0] * 100,
        'CASH': [0.0] * 100
    }, index=dates)
    
    rolling_metrics = DataFrame({
        'sharpe_ratio': [1.5] * 100,
        'volatility': [0.15] * 100,
        'max_drawdown': [-0.1] * 100
    }, index=dates)
    
    position_pnl = DataFrame({
        'AAPL': [100] * 100,
        'MSFT': [150] * 100,
        'GOOGL': [200] * 100,
        'CASH': [0] * 100
    }, index=dates)
    
    summary_metrics = {
        'total_return': 0.5,
        'sharpe_ratio': 1.2,
        'max_drawdown': -0.15,
        'volatility': 0.18
    }
    
    return PortfolioResult(
        equity_curve=equity_curve,
        weights_history=weights_history,
        trades_history=trades_history,
        returns_series=returns_series,
        summary_metrics=summary_metrics,
        rolling_metrics=rolling_metrics,
        drawdown_series=drawdown_series,
        position_pnl=position_pnl,
        turnover_history=turnover_history,
        transaction_costs=transaction_costs,
        slippage_costs=slippage_costs,
        cash_history=cash_history,
        strategy_name="Test Strategy"
    )


@pytest.fixture
def temp_checkpoint_dir():
    """Create a temporary directory for checkpoint testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


class TestCheckpointManager:
    """Test CheckpointManager class."""

    def test_init_creates_directory(self, temp_checkpoint_dir):
        """Test that __init__ creates the checkpoint directory."""
        manager = CheckpointManager(temp_checkpoint_dir / "checkpoints")
        assert (temp_checkpoint_dir / "checkpoints").exists()
        assert manager.max_checkpoints == 7

    def test_save_checkpoint_auto_name(self, temp_checkpoint_dir, sample_portfolio_result):
        """Test saving checkpoint with auto-generated name."""
        manager = CheckpointManager(temp_checkpoint_dir)
        
        with patch('src.checkpoint_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 25, 10, 30, 45)
            path = manager.save_checkpoint(sample_portfolio_result)
            
        expected_name = "checkpoint_20251225_103045"
        expected_path = str(temp_checkpoint_dir / f"{expected_name}.json")
        assert path == expected_path
        
        # Verify file was created
        assert (temp_checkpoint_dir / f"{expected_name}.json").exists()

    def test_save_checkpoint_custom_name(self, temp_checkpoint_dir, sample_portfolio_result):
        """Test saving checkpoint with custom name."""
        manager = CheckpointManager(temp_checkpoint_dir)
        custom_name = "test_checkpoint"
        
        path = manager.save_checkpoint(sample_portfolio_result, custom_name)
        expected_path = str(temp_checkpoint_dir / f"{custom_name}.json")
        assert path == expected_path
        assert (temp_checkpoint_dir / f"{custom_name}.json").exists()

    def test_load_checkpoint(self, temp_checkpoint_dir, sample_portfolio_result):
        """Test loading a checkpoint."""
        manager = CheckpointManager(temp_checkpoint_dir)
        checkpoint_name = "test_load"
        
        # Save first
        manager.save_checkpoint(sample_portfolio_result, checkpoint_name)
        
        # Load back
        loaded_result = manager.load_checkpoint(checkpoint_name)
        
        # Verify it's a PortfolioResult
        assert isinstance(loaded_result, PortfolioResult)
        assert loaded_result.strategy_name == "Test Strategy"
        assert len(loaded_result.equity_curve) == 100
        assert loaded_result.summary_metrics['total_return'] == 0.5

    def test_load_checkpoint_not_found(self, temp_checkpoint_dir):
        """Test loading non-existent checkpoint raises error."""
        manager = CheckpointManager(temp_checkpoint_dir)
        
        with pytest.raises(FileNotFoundError, match="Checkpoint not found"):
            manager.load_checkpoint("nonexistent")

    def test_list_checkpoints(self, temp_checkpoint_dir, sample_portfolio_result):
        """Test listing checkpoints."""
        manager = CheckpointManager(temp_checkpoint_dir)
        
        # Initially empty
        assert manager.list_checkpoints() == []
        
        # Add some checkpoints
        manager.save_checkpoint(sample_portfolio_result, "checkpoint1")
        manager.save_checkpoint(sample_portfolio_result, "checkpoint2")
        
        checkpoints = manager.list_checkpoints()
        assert len(checkpoints) == 2
        assert "checkpoint1" in checkpoints
        assert "checkpoint2" in checkpoints

    def test_get_latest_checkpoint(self, temp_checkpoint_dir, sample_portfolio_result):
        """Test getting latest checkpoint."""
        manager = CheckpointManager(temp_checkpoint_dir)
        
        # No checkpoints
        assert manager.get_latest_checkpoint() is None
        
        # Add checkpoints with timestamps
        with patch('src.checkpoint_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 25, 10, 0, 0)
            manager.save_checkpoint(sample_portfolio_result, "checkpoint_20251225_100000")
            
            mock_datetime.now.return_value = datetime(2025, 12, 25, 11, 0, 0)
            manager.save_checkpoint(sample_portfolio_result, "checkpoint_20251225_110000")
            
            mock_datetime.now.return_value = datetime(2025, 12, 25, 9, 0, 0)
            manager.save_checkpoint(sample_portfolio_result, "checkpoint_20251225_090000")
        
        latest = manager.get_latest_checkpoint()
        assert latest == "checkpoint_20251225_110000"

    def test_checkpoint_metadata(self, temp_checkpoint_dir, sample_portfolio_result):
        """Test that metadata is correctly saved and validated."""
        manager = CheckpointManager(temp_checkpoint_dir)
        checkpoint_name = "metadata_test"
        
        manager.save_checkpoint(sample_portfolio_result, checkpoint_name)
        
        # Read the JSON file directly to check metadata
        checkpoint_file = temp_checkpoint_dir / f"{checkpoint_name}.json"
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
        
        assert "_metadata" in data
        metadata = data["_metadata"]
        assert metadata["checkpoint_name"] == checkpoint_name
        assert metadata["portfolio_result_type"] == "PortfolioResult"
        assert metadata["version"] == "1.0"
        assert "created_at" in metadata

    def test_invalid_checkpoint_type(self, temp_checkpoint_dir):
        """Test loading checkpoint with invalid type raises error."""
        manager = CheckpointManager(temp_checkpoint_dir)
        checkpoint_file = temp_checkpoint_dir / "invalid.json"
        
        # Create invalid checkpoint
        invalid_data = {
            "_metadata": {
                "portfolio_result_type": "InvalidType",
                "version": "1.0"
            }
        }
        
        with open(checkpoint_file, 'w') as f:
            json.dump(invalid_data, f)
        
        with pytest.raises(ValueError, match="Invalid checkpoint type"):
            manager.load_checkpoint("invalid")

    def test_cleanup_old_checkpoints(self, temp_checkpoint_dir, sample_portfolio_result):
        """Test automatic cleanup of old checkpoints."""
        manager = CheckpointManager(temp_checkpoint_dir, max_checkpoints=2)
        
        # Create 3 checkpoints
        manager.save_checkpoint(sample_portfolio_result, "checkpoint1")
        manager.save_checkpoint(sample_portfolio_result, "checkpoint2") 
        manager.save_checkpoint(sample_portfolio_result, "checkpoint3")
        
        # Should only have 2 checkpoints left
        checkpoints = manager.list_checkpoints()
        assert len(checkpoints) == 2
        assert "checkpoint1" not in checkpoints  # Oldest should be removed

    def test_portfolio_result_conversion(self, sample_portfolio_result):
        """Test conversion between PortfolioResult and dict."""
        manager = CheckpointManager(Path("/tmp"))
        
        # Convert to dict
        result_dict = manager._portfolio_result_to_dict(sample_portfolio_result)
        
        # Convert back
        restored_result = manager._dict_to_portfolio_result(result_dict)
        
        # Verify key attributes
        assert isinstance(restored_result.equity_curve, Series)
        assert isinstance(restored_result.weights_history, DataFrame)
        assert restored_result.summary_metrics == sample_portfolio_result.summary_metrics
        assert len(restored_result.equity_curve) == len(sample_portfolio_result.equity_curve)