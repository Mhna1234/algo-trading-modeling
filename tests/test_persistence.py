"""
Tests for persistence (serialization/deserialization) of bandit components.

Tests cover:
- Round-trip serialization for BanditAllocator subclasses
- Round-trip serialization for BanditStrategyWrapper
- JSON compatibility
- State restoration accuracy
- Edge cases (empty state, partial state, etc.)
"""

import pytest
import json
import numpy as np
import pandas as pd
from pandas import Series, DataFrame

from src.bandits import UCBBandit, ThompsonSamplingBandit
from src.bandit_strategy_wrapper import BanditStrategyWrapper, StrategyPerformanceTracker
from src.strategies import BaseStrategyWrapper


# ==============================================================================
# Test Fixtures
# ==============================================================================

class MockStrategy(BaseStrategyWrapper):
    """Mock strategy for testing."""
    
    def __init__(self, name: str, **kwargs):
        super().__init__(name=name, strategy=None, optimizer=None, **kwargs)
        self.call_count = 0
    
    def get_weights(self, date, portfolio_state):
        """Return fixed equal weights."""
        self.call_count += 1
        # Return equal weights for 5 assets
        return Series([0.2, 0.2, 0.2, 0.2, 0.2], index=['A', 'B', 'C', 'D', 'E'])


@pytest.fixture
def ucb_bandit():
    """Fresh UCB bandit."""
    return UCBBandit(n_arms=3, exploration_constant=1.5)


@pytest.fixture
def thompson_bandit():
    """Fresh Thompson Sampling bandit."""
    return ThompsonSamplingBandit(n_arms=3, random_seed=42)


@pytest.fixture
def mock_strategies():
    """List of mock child strategies."""
    return [
        MockStrategy(name="Strategy A"),
        MockStrategy(name="Strategy B"),
        MockStrategy(name="Strategy C"),
    ]


# ==============================================================================
# UCBBandit Serialization Tests
# ==============================================================================

class TestUCBBanditSerialization:
    """Test UCB bandit state persistence."""
    
    def test_initial_state_round_trip(self, ucb_bandit):
        """Test serialization of fresh bandit."""
        # Get initial state
        state = ucb_bandit.get_state()
        
        # Create new bandit and restore state
        new_bandit = UCBBandit(n_arms=3, exploration_constant=1.5)
        new_bandit.set_state(state)
        
        # Verify state matches
        assert new_bandit.n_arms == ucb_bandit.n_arms
        assert new_bandit.exploration_constant == ucb_bandit.exploration_constant
        assert new_bandit.counts == ucb_bandit.counts
        assert new_bandit.values == ucb_bandit.values
        assert new_bandit.total_selections == ucb_bandit.total_selections
    
    def test_trained_state_round_trip(self, ucb_bandit):
        """Test serialization after training."""
        # Train the bandit
        for t in range(20):
            arm = ucb_bandit.select_arm(t)
            reward = 0.1 * arm + 0.01 * t  # Arm 2 is best
            ucb_bandit.update(arm, reward)
        
        # Get state
        state = ucb_bandit.get_state()
        
        # Create new bandit and restore
        new_bandit = UCBBandit(n_arms=3, exploration_constant=1.5)
        new_bandit.set_state(state)
        
        # Verify all state matches
        assert new_bandit.counts == ucb_bandit.counts
        assert new_bandit.values == ucb_bandit.values
        assert new_bandit.total_selections == ucb_bandit.total_selections
        
        # Verify behavior matches (deterministic selection)
        for t in range(20, 25):
            arm_orig = ucb_bandit.select_arm(t)
            arm_new = new_bandit.select_arm(t)
            assert arm_orig == arm_new
    
    def test_json_serialization(self, ucb_bandit):
        """Test that state is JSON-serializable."""
        # Train bandit
        for t in range(10):
            arm = ucb_bandit.select_arm(t)
            ucb_bandit.update(arm, 0.1 * arm)
        
        # Get state and serialize to JSON
        state = ucb_bandit.get_state()
        json_str = json.dumps(state)
        
        # Deserialize and restore
        restored_state = json.loads(json_str)
        new_bandit = UCBBandit(n_arms=3, exploration_constant=1.5)
        new_bandit.set_state(restored_state)
        
        # Verify
        assert new_bandit.counts == ucb_bandit.counts
        assert new_bandit.values == ucb_bandit.values
    
    def test_invalid_state_raises_error(self, ucb_bandit):
        """Test that invalid state raises ValueError."""
        # Missing key
        with pytest.raises(ValueError, match="Missing required key"):
            ucb_bandit.set_state({'n_arms': 3})
        
        # Wrong n_arms
        with pytest.raises(ValueError, match="does not match"):
            ucb_bandit.set_state({
                'n_arms': 5,
                'exploration_constant': 1.5,
                'counts': [0] * 5,
                'values': [0.0] * 5,
                'total_selections': 0
            })
        
        # Wrong array length
        with pytest.raises(ValueError, match="does not match"):
            ucb_bandit.set_state({
                'n_arms': 3,
                'exploration_constant': 1.5,
                'counts': [0, 0],  # Too short
                'values': [0.0, 0.0, 0.0],
                'total_selections': 0
            })


# ==============================================================================
# ThompsonSamplingBandit Serialization Tests
# ==============================================================================

class TestThompsonBanditSerialization:
    """Test Thompson Sampling bandit state persistence."""
    
    def test_initial_state_round_trip(self, thompson_bandit):
        """Test serialization of fresh bandit."""
        state = thompson_bandit.get_state()
        
        new_bandit = ThompsonSamplingBandit(
            n_arms=3,
            prior_mean=0.0,
            prior_variance=1.0,
            variance_scale=1.0,
            random_seed=42
        )
        new_bandit.set_state(state)
        
        # Verify state
        assert new_bandit.n_arms == thompson_bandit.n_arms
        assert new_bandit.counts == thompson_bandit.counts
        assert new_bandit.sums == thompson_bandit.sums
        assert new_bandit.sum_squares == thompson_bandit.sum_squares
    
    def test_trained_state_round_trip(self, thompson_bandit):
        """Test serialization after training."""
        # Train the bandit
        for t in range(30):
            arm = thompson_bandit.select_arm(t)
            reward = 0.15 * arm + 0.005 * t
            thompson_bandit.update(arm, reward)
        
        # Get state
        state = thompson_bandit.get_state()
        
        # Restore to new bandit
        new_bandit = ThompsonSamplingBandit(
            n_arms=3,
            prior_mean=0.0,
            prior_variance=1.0,
            variance_scale=1.0,
            random_seed=42  # Same seed for deterministic behavior
        )
        new_bandit.set_state(state)
        
        # Verify statistics match
        assert new_bandit.counts == thompson_bandit.counts
        assert new_bandit.sums == thompson_bandit.sums
        assert new_bandit.sum_squares == thompson_bandit.sum_squares
        
        # Verify posterior statistics match
        orig_stats = thompson_bandit.get_arm_statistics()
        new_stats = new_bandit.get_arm_statistics()
        
        for key in ['counts', 'means', 'variances']:
            assert orig_stats[key] == new_stats[key]
    
    def test_json_serialization(self, thompson_bandit):
        """Test JSON serialization."""
        # Train
        for t in range(15):
            arm = thompson_bandit.select_arm(t)
            thompson_bandit.update(arm, 0.1 * arm)
        
        # Serialize to JSON
        state = thompson_bandit.get_state()
        json_str = json.dumps(state)
        restored_state = json.loads(json_str)
        
        # Restore
        new_bandit = ThompsonSamplingBandit(n_arms=3, random_seed=42)
        new_bandit.set_state(restored_state)
        
        # Verify
        assert new_bandit.counts == thompson_bandit.counts
        assert new_bandit.sums == thompson_bandit.sums


# ==============================================================================
# StrategyPerformanceTracker Serialization Tests
# ==============================================================================

class TestTrackerSerialization:
    """Test StrategyPerformanceTracker persistence."""
    
    def test_empty_tracker_round_trip(self):
        """Test serialization of tracker with no observations."""
        tracker = StrategyPerformanceTracker(strategy_name="TestStrategy")
        
        state = tracker.get_state()
        new_tracker = StrategyPerformanceTracker(strategy_name="Temp")
        new_tracker.set_state(state)
        
        assert new_tracker.strategy_name == "TestStrategy"
        assert len(new_tracker.returns) == 0
        assert len(new_tracker.allocations) == 0
        assert len(new_tracker.timestamps) == 0
    
    def test_populated_tracker_round_trip(self):
        """Test serialization with observations."""
        tracker = StrategyPerformanceTracker(strategy_name="TestStrategy")
        
        # Add observations
        dates = pd.date_range('2023-01-01', periods=5, freq='D')
        for i, date in enumerate(dates):
            tracker.add_observation(
                ret=0.01 * i,
                allocation=0.2 * i,
                timestamp=date
            )
        
        # Serialize
        state = tracker.get_state()
        
        # Verify JSON-serializable
        json_str = json.dumps(state)
        restored_state = json.loads(json_str)
        
        # Restore
        new_tracker = StrategyPerformanceTracker(strategy_name="Temp")
        new_tracker.set_state(restored_state)
        
        # Verify
        assert new_tracker.strategy_name == "TestStrategy"
        assert new_tracker.returns == tracker.returns
        assert new_tracker.allocations == tracker.allocations
        assert new_tracker.timestamps == tracker.timestamps


# ==============================================================================
# BanditStrategyWrapper Serialization Tests
# ==============================================================================

class TestWrapperSerialization:
    """Test BanditStrategyWrapper persistence."""
    
    def test_initial_wrapper_round_trip(self, mock_strategies):
        """Test serialization of fresh wrapper."""
        bandit = UCBBandit(n_arms=3, exploration_constant=1.0)
        wrapper = BanditStrategyWrapper(
            child_strategies=mock_strategies,
            bandit_allocator=bandit,
            reward_type='sharpe',
            burn_in_periods=5
        )
        
        # Get state
        state = wrapper.get_state()
        
        # Verify JSON-serializable
        json_str = json.dumps(state)
        restored_state = json.loads(json_str)
        
        # Create new wrapper and restore
        new_bandit = UCBBandit(n_arms=3, exploration_constant=1.0)
        new_wrapper = BanditStrategyWrapper(
            child_strategies=mock_strategies,
            bandit_allocator=new_bandit,
            reward_type='sharpe',
            burn_in_periods=5
        )
        new_wrapper.set_state(restored_state)
        
        # Verify
        assert new_wrapper.period_count == 0
        assert new_wrapper.last_date is None
        assert new_wrapper.last_weights is None
        assert new_wrapper.last_allocations is None
        assert len(new_wrapper.allocation_history) == 0
    
    def test_trained_wrapper_round_trip(self, mock_strategies):
        """Test serialization after some training."""
        from src.portfolio_engine import PortfolioState
        
        bandit = UCBBandit(n_arms=3, exploration_constant=1.0)
        wrapper = BanditStrategyWrapper(
            child_strategies=mock_strategies,
            bandit_allocator=bandit,
            reward_type='sharpe',
            burn_in_periods=3
        )
        
        # Simulate a few periods
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        tickers = ['A', 'B', 'C', 'D', 'E']
        for date in dates:
            portfolio_state = PortfolioState(
                date=date,
                equity=100000.0,
                cash=100000.0,
                current_weights=Series([0.2] * 5, index=tickers),
                current_shares=Series([0.0] * 5, index=tickers),
                price_history=DataFrame(index=dates[:len(dates)], columns=tickers),
                return_history=DataFrame(index=dates[:len(dates)], columns=tickers)
            )
            weights = wrapper.get_weights(date, portfolio_state)
        
        # Get state
        state = wrapper.get_state()
        
        # Verify JSON-serializable
        json_str = json.dumps(state)
        restored_state = json.loads(json_str)
        
        # Create new wrapper and restore
        new_bandit = UCBBandit(n_arms=3, exploration_constant=1.0)
        new_wrapper = BanditStrategyWrapper(
            child_strategies=mock_strategies,
            bandit_allocator=new_bandit,
            reward_type='sharpe',
            burn_in_periods=3
        )
        new_wrapper.set_state(restored_state)
        
        # Verify state restored correctly
        assert new_wrapper.period_count == wrapper.period_count
        assert new_wrapper.last_date == wrapper.last_date
        assert len(new_wrapper.allocation_history) == len(wrapper.allocation_history)
        
        # Verify bandit state restored
        assert new_wrapper.bandit_allocator.total_selections == wrapper.bandit_allocator.total_selections
        
        # Verify performance trackers restored
        for i in range(3):
            assert len(new_wrapper.trackers[i].returns) == len(wrapper.trackers[i].returns)
    
    def test_wrapper_state_keys(self, mock_strategies):
        """Test that all required keys present in state."""
        bandit = UCBBandit(n_arms=3)
        wrapper = BanditStrategyWrapper(
            child_strategies=mock_strategies,
            bandit_allocator=bandit
        )
        
        state = wrapper.get_state()
        
        # Check required keys
        required_keys = [
            'bandit_state',
            'trackers',
            'period_count',
            'last_date',
            'last_weights',
            'last_allocations',
            'last_portfolio_value',
            'allocation_history'
        ]
        
        for key in required_keys:
            assert key in state, f"Missing key: {key}"
    
    def test_invalid_wrapper_state(self, mock_strategies):
        """Test that invalid state raises errors."""
        bandit = UCBBandit(n_arms=3)
        wrapper = BanditStrategyWrapper(
            child_strategies=mock_strategies,
            bandit_allocator=bandit
        )
        
        # Missing key
        with pytest.raises(ValueError, match="Missing required key"):
            wrapper.set_state({'period_count': 0})
        
        # Wrong number of trackers
        state = wrapper.get_state()
        state['trackers'] = state['trackers'][:2]  # Remove one tracker
        
        with pytest.raises(ValueError, match="trackers but wrapper has"):
            wrapper.set_state(state)
    
    def test_allocation_history_serialization(self, mock_strategies):
        """Test that allocation history is properly serialized."""
        from src.portfolio_engine import PortfolioState
        
        bandit = UCBBandit(n_arms=3)
        wrapper = BanditStrategyWrapper(
            child_strategies=mock_strategies,
            bandit_allocator=bandit
        )
        
        # Run a few periods
        dates = pd.date_range('2023-01-01', periods=5, freq='D')
        tickers = ['A', 'B', 'C', 'D', 'E']
        for date in dates:
            portfolio_state = PortfolioState(
                date=date,
                equity=100000.0,
                cash=100000.0,
                current_weights=Series([0.2] * 5, index=tickers),
                current_shares=Series([0.0] * 5, index=tickers),
                price_history=DataFrame(index=dates[:len(dates)], columns=tickers),
                return_history=DataFrame(index=dates[:len(dates)], columns=tickers)
            )
            wrapper.get_weights(date, portfolio_state)
        
        # Get state and verify allocation_history is serializable
        state = wrapper.get_state()
        json_str = json.dumps(state)  # Should not raise
        
        # Restore and verify
        restored_state = json.loads(json_str)
        new_bandit = UCBBandit(n_arms=3)
        new_wrapper = BanditStrategyWrapper(
            child_strategies=mock_strategies,
            bandit_allocator=new_bandit
        )
        new_wrapper.set_state(restored_state)
        
        # Check allocation history length
        assert len(new_wrapper.allocation_history) == 5
        
        # Check each entry has correct structure
        for entry in new_wrapper.allocation_history:
            assert 'date' in entry
            assert 'allocations' in entry
            assert 'period' in entry
            assert isinstance(entry['date'], pd.Timestamp)
            assert isinstance(entry['allocations'], np.ndarray)


# ==============================================================================
# Edge Case Tests
# ==============================================================================

class TestEdgeCases:
    """Test edge cases for persistence."""
    
    def test_wrapper_with_zero_observations(self, mock_strategies):
        """Test wrapper that has never been called."""
        bandit = UCBBandit(n_arms=3)
        wrapper = BanditStrategyWrapper(
            child_strategies=mock_strategies,
            bandit_allocator=bandit
        )
        
        # Get state immediately
        state = wrapper.get_state()
        json_str = json.dumps(state)
        
        # Should be valid
        assert state['period_count'] == 0
        assert state['last_date'] is None
        assert state['allocation_history'] == []
    
    def test_wrapper_during_burn_in(self, mock_strategies):
        """Test wrapper during burn-in period."""
        from src.portfolio_engine import PortfolioState
        
        bandit = UCBBandit(n_arms=3)
        wrapper = BanditStrategyWrapper(
            child_strategies=mock_strategies,
            bandit_allocator=bandit,
            burn_in_periods=10
        )
        
        # Run partway through burn-in
        dates = pd.date_range('2023-01-01', periods=5, freq='D')
        tickers = ['A', 'B', 'C', 'D', 'E']
        for date in dates:
            portfolio_state = PortfolioState(
                date=date,
                equity=100000.0,
                cash=100000.0,
                current_weights=Series([0.2] * 5, index=tickers),
                current_shares=Series([0.0] * 5, index=tickers),
                price_history=DataFrame(index=dates[:len(dates)], columns=tickers),
                return_history=DataFrame(index=dates[:len(dates)], columns=tickers)
            )
            wrapper.get_weights(date, portfolio_state)
        
        # Serialize
        state = wrapper.get_state()
        json_str = json.dumps(state)
        
        # Restore
        new_bandit = UCBBandit(n_arms=3)
        new_wrapper = BanditStrategyWrapper(
            child_strategies=mock_strategies,
            bandit_allocator=new_bandit,
            burn_in_periods=10
        )
        new_wrapper.set_state(json.loads(json_str))
        
        # Verify still in burn-in
        assert new_wrapper.period_count == 5
        assert new_wrapper.period_count < new_wrapper.burn_in_periods
    
    def test_thompson_sampling_determinism_after_restore(self):
        """Test that Thompson Sampling behavior is deterministic after restore."""
        # Create bandit with seed
        bandit1 = ThompsonSamplingBandit(n_arms=3, random_seed=42)
        
        # Train it
        for t in range(20):
            arm = bandit1.select_arm(t)
            bandit1.update(arm, 0.1 * arm)
        
        # Save state
        state = bandit1.get_state()
        
        # Create new bandit with SAME seed and restore
        bandit2 = ThompsonSamplingBandit(n_arms=3, random_seed=42)
        bandit2.set_state(state)
        
        # Note: Selections will be stochastic due to random sampling,
        # but the posterior parameters should match exactly
        stats1 = bandit1.get_arm_statistics()
        stats2 = bandit2.get_arm_statistics()
        
        assert stats1['means'] == stats2['means']
        assert stats1['variances'] == stats2['variances']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
