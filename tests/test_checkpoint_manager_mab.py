"""Unit tests for MAB state persistence in checkpoint_manager module."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from pandas import Series, DataFrame

from src.checkpoint_manager import CheckpointManager
from src.portfolio_engine import PortfolioResult
from src.bandits import UCBBandit, ThompsonSamplingBandit


@pytest.fixture
def sample_portfolio_result():
    """Create a sample PortfolioResult for testing."""
    dates = pd.date_range('2020-01-01', periods=50, freq='D')
    assets = ['AAPL', 'MSFT', 'GOOGL', 'CASH']
    
    equity_curve = Series([1_000_000 + i * 1000 for i in range(50)], index=dates)
    returns_series = Series([0.01] * 50, index=dates)
    drawdown_series = Series([0.0] * 50, index=dates)
    turnover_history = Series([0.05] * 50, index=dates)
    transaction_costs = Series([100] * 50, index=dates)
    slippage_costs = Series([50] * 50, index=dates)
    cash_history = Series([100_000] * 50, index=dates)
    
    weights_history = DataFrame({
        'AAPL': [0.25] * 50,
        'MSFT': [0.25] * 50,
        'GOOGL': [0.25] * 50,
        'CASH': [0.25] * 50
    }, index=dates)
    
    trades_history = DataFrame({
        'AAPL': [0.0] * 50,
        'MSFT': [0.0] * 50,
        'GOOGL': [0.0] * 50,
        'CASH': [0.0] * 50
    }, index=dates)
    
    rolling_metrics = DataFrame({
        'sharpe_ratio': [1.5] * 50,
        'volatility': [0.15] * 50,
        'max_drawdown': [-0.1] * 50
    }, index=dates)
    
    position_pnl = DataFrame({
        'AAPL': [100] * 50,
        'MSFT': [150] * 50,
        'GOOGL': [200] * 50,
        'CASH': [0] * 50
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


class TestMABStatePersistence:
    """Test MAB state persistence functionality."""

    def test_serialize_ucb_bandit(self, temp_checkpoint_dir):
        """Test serialization of UCB bandit state."""
        manager = CheckpointManager(temp_checkpoint_dir)
        
        # Create and train a UCB bandit
        bandit = UCBBandit(n_arms=3, exploration_constant=1.5)
        
        # Simulate some learning
        bandit.update(0, 0.1)
        bandit.update(1, 0.2)
        bandit.update(2, 0.15)
        bandit.select_arm(3)  # This increments total_selections
        
        # Serialize state
        state = manager._serialize_bandit_state(bandit)
        
        # Verify state contains expected keys
        assert "counts" in state
        assert "values" in state
        assert "total_selections" in state
        assert "exploration_constant" in state
        
        # Verify values
        assert state["exploration_constant"] == 1.5
        assert state["total_selections"] == 3  # From the 3 update calls
        assert len(state["counts"]) == 3
        assert len(state["values"]) == 3

    def test_serialize_thompson_bandit(self, temp_checkpoint_dir):
        """Test serialization of Thompson sampling bandit state."""
        manager = CheckpointManager(temp_checkpoint_dir)
        
        # Create and train a Thompson bandit
        bandit = ThompsonSamplingBandit(n_arms=3, random_seed=42, prior_mean=0.05)
        
        # Simulate some learning
        bandit.update(0, 0.1)
        bandit.update(1, 0.2)
        bandit.update(2, 0.15)
        
        # Serialize state
        state = manager._serialize_bandit_state(bandit)
        
        # Verify state contains expected keys
        expected_keys = ["counts", "sums", "sum_squares", "prior_mean", 
                        "prior_variance", "variance_scale", "random_seed"]
        for key in expected_keys:
            assert key in state
        
        # Verify values
        assert state["prior_mean"] == 0.05
        assert state["random_seed"] == 42
        assert len(state["counts"]) == 3

    def test_deserialize_ucb_bandit(self, temp_checkpoint_dir):
        """Test deserialization of UCB bandit state."""
        manager = CheckpointManager(temp_checkpoint_dir)
        
        # Create original bandit
        original_bandit = UCBBandit(n_arms=3, exploration_constant=2.0)
        original_bandit.update(0, 0.1)
        original_bandit.update(1, 0.2)
        original_bandit.update(2, 0.15)
        
        # Serialize and then deserialize into new bandit
        state = manager._serialize_bandit_state(original_bandit)
        new_bandit = UCBBandit(n_arms=3)  # Different exploration constant
        manager._deserialize_bandit_state(new_bandit, state)
        
        # Verify state was restored
        assert new_bandit.exploration_constant == 2.0
        assert new_bandit.counts == [1, 1, 1]
        assert new_bandit.values == [0.1, 0.2, 0.15]
        assert new_bandit.total_selections == 3

    def test_deserialize_thompson_bandit(self, temp_checkpoint_dir):
        """Test deserialization of Thompson sampling bandit state."""
        manager = CheckpointManager(temp_checkpoint_dir)
        
        # Create original bandit
        original_bandit = ThompsonSamplingBandit(n_arms=3, random_seed=123, prior_mean=0.1)
        original_bandit.update(0, 0.1)
        original_bandit.update(1, 0.2)
        
        # Serialize and deserialize
        state = manager._serialize_bandit_state(original_bandit)
        new_bandit = ThompsonSamplingBandit(n_arms=3)  # No random seed
        manager._deserialize_bandit_state(new_bandit, state)
        
        # Verify state was restored
        assert new_bandit.prior_mean == 0.1
        assert new_bandit._random_seed == 123
        assert new_bandit.counts == [1, 1, 0]
        assert new_bandit.sums == [0.1, 0.2, 0.0]

    def test_save_load_checkpoint_with_bandit(self, temp_checkpoint_dir, sample_portfolio_result):
        """Test saving and loading checkpoint with bandit state."""
        manager = CheckpointManager(temp_checkpoint_dir)
        
        # Create and train bandit
        bandit = UCBBandit(n_arms=4, exploration_constant=1.5)
        bandit.update(0, 0.1)
        bandit.update(1, 0.2)
        bandit.update(2, 0.15)
        bandit.update(3, 0.05)
        
        # Save checkpoint with bandit
        checkpoint_path = manager.save_checkpoint_with_bandit(sample_portfolio_result, bandit, "test_bandit")
        
        # Verify files exist
        json_file = temp_checkpoint_dir / "test_bandit.json"
        assert json_file.exists()
        
        # Load checkpoint with new bandit
        new_bandit = UCBBandit(n_arms=4)  # Fresh bandit
        loaded_result = manager.load_checkpoint_with_bandit("test_bandit", new_bandit)
        
        # Verify portfolio result was loaded
        assert isinstance(loaded_result, PortfolioResult)
        assert loaded_result.strategy_name == "Test Strategy"
        
        # Verify bandit state was restored
        assert new_bandit.exploration_constant == 1.5
        assert new_bandit.counts == [1, 1, 1, 1]
        assert new_bandit.values == [0.1, 0.2, 0.15, 0.05]

    def test_bandit_type_validation(self, temp_checkpoint_dir, sample_portfolio_result):
        """Test that bandit type mismatches are handled gracefully."""
        manager = CheckpointManager(temp_checkpoint_dir)
        
        # Save with UCB bandit
        ucb_bandit = UCBBandit(n_arms=3)
        manager.save_checkpoint_with_bandit(sample_portfolio_result, ucb_bandit, "type_test")
        
        # Try to load with Thompson bandit (type mismatch)
        thompson_bandit = ThompsonSamplingBandit(n_arms=3)
        loaded_result = manager.load_checkpoint_with_bandit("type_test", thompson_bandit)
        
        # Should still load portfolio result but bandit state should not be restored
        assert isinstance(loaded_result, PortfolioResult)
        # Thompson bandit should remain unchanged (default state)
        assert thompson_bandit.counts == [0, 0, 0]

    def test_unsupported_bandit_type(self, temp_checkpoint_dir):
        """Test that unsupported bandit types raise appropriate errors."""
        manager = CheckpointManager(temp_checkpoint_dir)
        
        # Create a mock bandit with unsupported type
        class UnsupportedBandit:
            pass
        
        unsupported_bandit = UnsupportedBandit()
        
        with pytest.raises(ValueError, match="Unsupported bandit type for serialization"):
            manager._serialize_bandit_state(unsupported_bandit)
        
        with pytest.raises(ValueError, match="Unsupported bandit type for deserialization"):
            manager._deserialize_bandit_state(unsupported_bandit, {})

    def test_load_checkpoint_without_bandit(self, temp_checkpoint_dir, sample_portfolio_result):
        """Test loading checkpoint without providing bandit (should work normally)."""
        manager = CheckpointManager(temp_checkpoint_dir)
        
        # Save normal checkpoint
        manager.save_checkpoint(sample_portfolio_result, "no_bandit")
        
        # Load without bandit parameter
        loaded_result = manager.load_checkpoint_with_bandit("no_bandit")
        
        # Should work normally
        assert isinstance(loaded_result, PortfolioResult)
        assert loaded_result.strategy_name == "Test Strategy"