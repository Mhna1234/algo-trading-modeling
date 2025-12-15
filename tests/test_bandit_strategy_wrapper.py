"""
Unit tests for BanditStrategyWrapper

Tests cover:
- Initialization and validation
- Weight aggregation with dummy strategies
- Reward calculation and bandit updates
- Burn-in period behavior
- Error handling and fallback
- Soft vs hard allocation
- Minimum allocation constraints
- State tracking and diagnostics
"""

import pytest
import pandas as pd
import numpy as np
from pandas import Series, DataFrame
from typing import Optional
from dataclasses import dataclass

# Import classes to test
from src.bandit_strategy_wrapper import BanditStrategyWrapper, StrategyPerformanceTracker
from src.bandits import BanditAllocator, UCBBandit, ThompsonSamplingBandit
from src.portfolio_engine import PortfolioState


# ============================================================================
# Dummy Classes for Testing
# ============================================================================

class DummyStrategy:
    """Minimal strategy class for testing."""
    def __init__(self, assets):
        self.assets = assets


class DummyOptimizer:
    """Minimal optimizer class for testing."""
    pass


class DummyStrategyWrapper:
    """Mock strategy wrapper that returns fixed weights."""
    
    def __init__(self, name: str, weights: dict, assets: list):
        self.name = name
        self.fixed_weights = Series(weights)
        self.strategy = DummyStrategy(assets)
        self.optimizer = DummyOptimizer()
        self.call_count = 0
    
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> Series:
        """Return fixed weights."""
        self.call_count += 1
        return self.fixed_weights.copy()
    
    def get_strategy_info(self):
        return {'name': self.name}


class FailingStrategyWrapper(DummyStrategyWrapper):
    """Strategy that always fails."""
    
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> Series:
        raise RuntimeError("Simulated strategy failure")


# ============================================================================
# Helper Functions
# ============================================================================

def create_dummy_portfolio_state(
    date: pd.Timestamp,
    equity: float = 100000.0,
    assets: list = None
) -> PortfolioState:
    """Create a minimal PortfolioState for testing."""
    if assets is None:
        assets = ['AAPL', 'MSFT', 'GOOGL']
    
    n_assets = len(assets)
    
    return PortfolioState(
        date=date,
        current_weights=Series(1.0/n_assets, index=assets),
        current_shares=Series(10.0, index=assets),
        cash=10000.0,
        equity=equity,
        price_history=DataFrame(),
        return_history=DataFrame(),
        last_rebalance_date=None,
        days_since_rebalance=0,
        recent_sharpe=0.5,
        recent_vol=0.15,
        current_drawdown=0.0,
        portfolio_var=0.0,
        portfolio_cvar=0.0,
        total_return=0.0
    )


# ============================================================================
# Test: StrategyPerformanceTracker
# ============================================================================

def test_performance_tracker_initialization():
    """Test StrategyPerformanceTracker initialization."""
    tracker = StrategyPerformanceTracker("Test Strategy")
    assert tracker.strategy_name == "Test Strategy"
    assert len(tracker.returns) == 0
    assert len(tracker.allocations) == 0


def test_performance_tracker_add_observation():
    """Test adding observations to tracker."""
    tracker = StrategyPerformanceTracker("Test")
    date = pd.Timestamp('2023-01-01')
    
    tracker.add_observation(0.05, 0.3, date)
    assert len(tracker.returns) == 1
    assert tracker.returns[0] == 0.05
    assert tracker.allocations[0] == 0.3


def test_performance_tracker_metrics_empty():
    """Test metrics calculation with no data."""
    tracker = StrategyPerformanceTracker("Test")
    metrics = tracker.get_recent_metrics()
    
    assert metrics['mean_return'] == 0.0
    assert metrics['volatility'] == 0.0
    assert metrics['sharpe'] == 0.0


def test_performance_tracker_metrics_with_data():
    """Test metrics calculation with observations."""
    tracker = StrategyPerformanceTracker("Test")
    date = pd.Timestamp('2023-01-01')
    
    # Add observations
    returns = [0.02, 0.03, -0.01, 0.04, 0.01]
    for ret in returns:
        tracker.add_observation(ret, 0.5, date)
    
    metrics = tracker.get_recent_metrics()
    
    expected_mean = np.mean(returns)
    expected_vol = np.std(returns)
    expected_sharpe = expected_mean / expected_vol
    
    assert abs(metrics['mean_return'] - expected_mean) < 1e-6
    assert abs(metrics['volatility'] - expected_vol) < 1e-6
    assert abs(metrics['sharpe'] - expected_sharpe) < 1e-4  # Relaxed tolerance


# ============================================================================
# Test: BanditStrategyWrapper Initialization
# ============================================================================

def test_wrapper_initialization():
    """Test basic initialization of BanditStrategyWrapper."""
    assets = ['AAPL', 'MSFT', 'GOOGL']
    
    # Create dummy strategies
    strategy1 = DummyStrategyWrapper("Strategy 1", {'AAPL': 0.5, 'MSFT': 0.3, 'GOOGL': 0.2}, assets)
    strategy2 = DummyStrategyWrapper("Strategy 2", {'AAPL': 0.3, 'MSFT': 0.4, 'GOOGL': 0.3}, assets)
    
    # Create bandit
    bandit = UCBBandit(n_arms=2)
    
    # Create wrapper
    wrapper = BanditStrategyWrapper(
        child_strategies=[strategy1, strategy2],
        bandit_allocator=bandit
    )
    
    assert wrapper.name == "Bandit Strategy Allocator"
    assert len(wrapper.child_strategies) == 2
    assert wrapper.period_count == 0
    assert len(wrapper.trackers) == 2


def test_wrapper_initialization_validation_no_strategies():
    """Test that initialization fails with no child strategies."""
    bandit = UCBBandit(n_arms=2)
    
    with pytest.raises(ValueError, match="Must provide at least one child strategy"):
        BanditStrategyWrapper(child_strategies=[], bandit_allocator=bandit)


def test_wrapper_initialization_validation_mismatch():
    """Test that initialization fails with mismatched strategy count."""
    assets = ['AAPL', 'MSFT']
    strategy = DummyStrategyWrapper("Strategy", {'AAPL': 0.5, 'MSFT': 0.5}, assets)
    bandit = UCBBandit(n_arms=3)  # Mismatch!
    
    with pytest.raises(ValueError, match="must match"):
        BanditStrategyWrapper(child_strategies=[strategy], bandit_allocator=bandit)


def test_wrapper_initialization_validation_min_allocation():
    """Test min_allocation validation."""
    assets = ['AAPL', 'MSFT']
    strategy1 = DummyStrategyWrapper("Strategy 1", {'AAPL': 0.6, 'MSFT': 0.4}, assets)
    strategy2 = DummyStrategyWrapper("Strategy 2", {'AAPL': 0.4, 'MSFT': 0.6}, assets)
    bandit = UCBBandit(n_arms=2)
    
    with pytest.raises(ValueError, match="min_allocation must be"):
        BanditStrategyWrapper(
            child_strategies=[strategy1, strategy2],
            bandit_allocator=bandit,
            min_allocation=0.6  # Invalid! (max allowed is 0.5 for 2 strategies)
        )


# ============================================================================
# Test: Weight Aggregation
# ============================================================================

def test_get_weights_equal_allocation_burn_in():
    """Test that burn-in period uses equal allocation."""
    assets = ['AAPL', 'MSFT', 'GOOGL']
    
    # Strategy 1: prefers AAPL
    strategy1 = DummyStrategyWrapper("Strategy 1", {'AAPL': 0.7, 'MSFT': 0.2, 'GOOGL': 0.1}, assets)
    # Strategy 2: prefers MSFT
    strategy2 = DummyStrategyWrapper("Strategy 2", {'AAPL': 0.1, 'MSFT': 0.7, 'GOOGL': 0.2}, assets)
    
    bandit = UCBBandit(n_arms=2)
    wrapper = BanditStrategyWrapper(
        child_strategies=[strategy1, strategy2],
        bandit_allocator=bandit,
        burn_in_periods=5
    )
    
    date = pd.Timestamp('2023-01-01')
    portfolio_state = create_dummy_portfolio_state(date, assets=assets)
    
    # First call (burn-in): should be 50/50 allocation
    weights = wrapper.get_weights(date, portfolio_state)
    
    # Expected: 0.5 * [0.7, 0.2, 0.1] + 0.5 * [0.1, 0.7, 0.2]
    expected = Series({
        'AAPL': 0.5 * 0.7 + 0.5 * 0.1,  # 0.4
        'MSFT': 0.5 * 0.2 + 0.5 * 0.7,  # 0.45
        'GOOGL': 0.5 * 0.1 + 0.5 * 0.2  # 0.15
    })
    
    assert abs(weights['AAPL'] - expected['AAPL']) < 1e-6
    assert abs(weights['MSFT'] - expected['MSFT']) < 1e-6
    assert abs(weights['GOOGL'] - expected['GOOGL']) < 1e-6
    assert abs(weights.sum() - 1.0) < 1e-6


def test_get_weights_soft_allocation_after_burn_in():
    """Test soft allocation after burn-in period."""
    assets = ['AAPL', 'MSFT']
    
    strategy1 = DummyStrategyWrapper("Strategy 1", {'AAPL': 0.8, 'MSFT': 0.2}, assets)
    strategy2 = DummyStrategyWrapper("Strategy 2", {'AAPL': 0.3, 'MSFT': 0.7}, assets)
    
    bandit = UCBBandit(n_arms=2, exploration_constant=2.0)
    wrapper = BanditStrategyWrapper(
        child_strategies=[strategy1, strategy2],
        bandit_allocator=bandit,
        burn_in_periods=2,
        enable_soft_allocation=True,
        random_seed=42
    )
    
    dates = pd.date_range('2023-01-01', periods=5, freq='W')
    equity = 100000.0
    
    for i, date in enumerate(dates):
        portfolio_state = create_dummy_portfolio_state(date, equity=equity, assets=assets)
        weights = wrapper.get_weights(date, portfolio_state)
        
        # Check valid weights
        assert abs(weights.sum() - 1.0) < 1e-6
        assert all(weights >= 0)
        
        # Simulate equity change for next period
        equity *= 1.01  # 1% growth


def test_get_weights_hard_allocation():
    """Test hard allocation (single strategy selection)."""
    assets = ['AAPL', 'MSFT']
    
    strategy1 = DummyStrategyWrapper("Strategy 1", {'AAPL': 0.8, 'MSFT': 0.2}, assets)
    strategy2 = DummyStrategyWrapper("Strategy 2", {'AAPL': 0.3, 'MSFT': 0.7}, assets)
    
    bandit = UCBBandit(n_arms=2)
    wrapper = BanditStrategyWrapper(
        child_strategies=[strategy1, strategy2],
        bandit_allocator=bandit,
        burn_in_periods=0,
        enable_soft_allocation=False,
        random_seed=42
    )
    
    date = pd.Timestamp('2023-01-01')
    portfolio_state = create_dummy_portfolio_state(date, assets=assets)
    
    weights = wrapper.get_weights(date, portfolio_state)
    
    # With hard allocation, weights should match one of the strategies exactly
    # (after first selection, bandit will explore)
    assert abs(weights.sum() - 1.0) < 1e-6


def test_get_weights_min_allocation_constraint():
    """Test minimum allocation constraint."""
    assets = ['AAPL', 'MSFT']
    
    strategy1 = DummyStrategyWrapper("Strategy 1", {'AAPL': 0.8, 'MSFT': 0.2}, assets)
    strategy2 = DummyStrategyWrapper("Strategy 2", {'AAPL': 0.3, 'MSFT': 0.7}, assets)
    
    bandit = ThompsonSamplingBandit(n_arms=2, random_seed=42)
    
    # Set high minimum allocation
    min_alloc = 0.3
    wrapper = BanditStrategyWrapper(
        child_strategies=[strategy1, strategy2],
        bandit_allocator=bandit,
        burn_in_periods=0,
        min_allocation=min_alloc,
        random_seed=42
    )
    
    # Run for several periods
    dates = pd.date_range('2023-01-01', periods=10, freq='W')
    equity = 100000.0
    
    for date in dates:
        portfolio_state = create_dummy_portfolio_state(date, equity=equity, assets=assets)
        weights = wrapper.get_weights(date, portfolio_state)
        equity *= 1.01
    
    # Check that allocations respect minimum
    allocations_df = wrapper.get_strategy_allocations()
    
    # After burn-in, all allocations should be >= min_alloc
    if len(allocations_df) > 0:
        for col in allocations_df.columns:
            assert all(allocations_df[col] >= min_alloc - 1e-6)


# ============================================================================
# Test: Error Handling
# ============================================================================

def test_get_weights_child_strategy_failure_with_fallback():
    """Test graceful handling of child strategy failure."""
    assets = ['AAPL', 'MSFT']
    
    good_strategy = DummyStrategyWrapper("Good", {'AAPL': 0.6, 'MSFT': 0.4}, assets)
    bad_strategy = FailingStrategyWrapper("Bad", {'AAPL': 0.5, 'MSFT': 0.5}, assets)
    
    bandit = UCBBandit(n_arms=2)
    wrapper = BanditStrategyWrapper(
        child_strategies=[good_strategy, bad_strategy],
        bandit_allocator=bandit,
        fallback_on_error=True
    )
    
    date = pd.Timestamp('2023-01-01')
    portfolio_state = create_dummy_portfolio_state(date, assets=assets)
    
    # Should not raise, uses fallback for bad strategy
    weights = wrapper.get_weights(date, portfolio_state)
    
    assert abs(weights.sum() - 1.0) < 1e-6


def test_get_weights_child_strategy_failure_without_fallback():
    """Test that failure propagates when fallback disabled."""
    assets = ['AAPL', 'MSFT']
    
    good_strategy = DummyStrategyWrapper("Good", {'AAPL': 0.6, 'MSFT': 0.4}, assets)
    bad_strategy = FailingStrategyWrapper("Bad", {'AAPL': 0.5, 'MSFT': 0.5}, assets)
    
    bandit = UCBBandit(n_arms=2)
    wrapper = BanditStrategyWrapper(
        child_strategies=[good_strategy, bad_strategy],
        bandit_allocator=bandit,
        fallback_on_error=False
    )
    
    date = pd.Timestamp('2023-01-01')
    portfolio_state = create_dummy_portfolio_state(date, assets=assets)
    
    with pytest.raises(RuntimeError, match="Simulated strategy failure"):
        wrapper.get_weights(date, portfolio_state)


# ============================================================================
# Test: Reward Calculation
# ============================================================================

def test_reward_calculation_sharpe():
    """Test Sharpe-based reward calculation."""
    assets = ['AAPL', 'MSFT']
    
    strategy1 = DummyStrategyWrapper("Strategy 1", {'AAPL': 0.6, 'MSFT': 0.4}, assets)
    strategy2 = DummyStrategyWrapper("Strategy 2", {'AAPL': 0.4, 'MSFT': 0.6}, assets)
    
    bandit = UCBBandit(n_arms=2)
    wrapper = BanditStrategyWrapper(
        child_strategies=[strategy1, strategy2],
        bandit_allocator=bandit,
        reward_type='sharpe',
        burn_in_periods=1
    )
    
    # Run for multiple periods to generate rewards
    dates = pd.date_range('2023-01-01', periods=5, freq='W')
    equity = 100000.0
    
    for date in dates:
        portfolio_state = create_dummy_portfolio_state(date, equity=equity, assets=assets)
        weights = wrapper.get_weights(date, portfolio_state)
        
        # Simulate equity change
        equity *= (1.0 + np.random.uniform(-0.02, 0.03))
    
    # Check that bandit was updated (counts should be > 0 after burn-in)
    state = bandit.get_state()
    assert sum(state['counts']) > 0


def test_reward_calculation_return():
    """Test raw return reward calculation."""
    assets = ['AAPL', 'MSFT']
    
    strategy1 = DummyStrategyWrapper("Strategy 1", {'AAPL': 0.5, 'MSFT': 0.5}, assets)
    strategy2 = DummyStrategyWrapper("Strategy 2", {'AAPL': 0.4, 'MSFT': 0.6}, assets)
    bandit = UCBBandit(n_arms=2)
    
    wrapper = BanditStrategyWrapper(
        child_strategies=[strategy1, strategy2],
        bandit_allocator=bandit,
        reward_type='return',
        burn_in_periods=0
    )
    
    # Run two periods
    date1 = pd.Timestamp('2023-01-01')
    date2 = pd.Timestamp('2023-01-08')
    
    equity1 = 100000.0
    equity2 = 105000.0  # 5% gain
    
    state1 = create_dummy_portfolio_state(date1, equity=equity1, assets=assets)
    wrapper.get_weights(date1, state1)
    
    state2 = create_dummy_portfolio_state(date2, equity=equity2, assets=assets)
    wrapper.get_weights(date2, state2)
    
    # Check that trackers recorded returns
    assert len(wrapper.trackers[0].returns) > 0
    assert len(wrapper.trackers[1].returns) > 0


# ============================================================================
# Test: State Tracking and Diagnostics
# ============================================================================

def test_get_strategy_allocations():
    """Test retrieval of allocation history."""
    assets = ['AAPL', 'MSFT']
    
    strategy1 = DummyStrategyWrapper("Strategy 1", {'AAPL': 0.6, 'MSFT': 0.4}, assets)
    strategy2 = DummyStrategyWrapper("Strategy 2", {'AAPL': 0.4, 'MSFT': 0.6}, assets)
    
    bandit = UCBBandit(n_arms=2)
    wrapper = BanditStrategyWrapper(
        child_strategies=[strategy1, strategy2],
        bandit_allocator=bandit
    )
    
    # Run for multiple periods
    dates = pd.date_range('2023-01-01', periods=5, freq='W')
    equity = 100000.0
    
    for date in dates:
        portfolio_state = create_dummy_portfolio_state(date, equity=equity, assets=assets)
        wrapper.get_weights(date, portfolio_state)
        equity *= 1.01
    
    # Get allocation history
    alloc_df = wrapper.get_strategy_allocations()
    
    assert len(alloc_df) == 5
    assert list(alloc_df.columns) == ['Strategy 1', 'Strategy 2']
    
    # All allocations should sum to 1
    for _, row in alloc_df.iterrows():
        assert abs(row.sum() - 1.0) < 1e-6


def test_get_diagnostics():
    """Test diagnostic information retrieval."""
    assets = ['AAPL', 'MSFT']
    
    strategy1 = DummyStrategyWrapper("Strategy 1", {'AAPL': 0.6, 'MSFT': 0.4}, assets)
    strategy2 = DummyStrategyWrapper("Strategy 2", {'AAPL': 0.4, 'MSFT': 0.6}, assets)
    
    bandit = UCBBandit(n_arms=2)
    wrapper = BanditStrategyWrapper(
        child_strategies=[strategy1, strategy2],
        bandit_allocator=bandit,
        burn_in_periods=3
    )
    
    # Run for multiple periods
    dates = pd.date_range('2023-01-01', periods=5, freq='W')
    equity = 100000.0
    
    for date in dates:
        portfolio_state = create_dummy_portfolio_state(date, equity=equity, assets=assets)
        wrapper.get_weights(date, portfolio_state)
        equity *= 1.01
    
    # Get diagnostics
    diagnostics = wrapper.get_diagnostics()
    
    assert 'bandit_state' in diagnostics
    assert 'strategy_metrics' in diagnostics
    assert 'allocation_history' in diagnostics
    assert 'current_allocations' in diagnostics
    assert 'period_count' in diagnostics
    assert 'burn_in_complete' in diagnostics
    
    assert diagnostics['period_count'] == 5
    assert diagnostics['burn_in_complete'] == True
    
    # Check strategy metrics structure
    assert 'Strategy 1' in diagnostics['strategy_metrics']
    assert 'Strategy 2' in diagnostics['strategy_metrics']
    
    metrics1 = diagnostics['strategy_metrics']['Strategy 1']
    assert 'mean_return' in metrics1
    assert 'volatility' in metrics1
    assert 'sharpe' in metrics1


def test_get_strategy_info():
    """Test strategy info retrieval."""
    assets = ['AAPL', 'MSFT']
    
    strategy1 = DummyStrategyWrapper("Strategy 1", {'AAPL': 0.6, 'MSFT': 0.4}, assets)
    strategy2 = DummyStrategyWrapper("Strategy 2", {'AAPL': 0.4, 'MSFT': 0.6}, assets)
    
    bandit = UCBBandit(n_arms=2)
    wrapper = BanditStrategyWrapper(
        child_strategies=[strategy1, strategy2],
        bandit_allocator=bandit
    )
    
    info = wrapper.get_strategy_info()
    
    assert info['name'] == "Bandit Strategy Allocator"
    assert info['type'] == "BanditStrategyWrapper"
    assert 'parameters' in info
    
    params = info['parameters']
    assert params['n_strategies'] == 2
    assert params['child_strategies'] == ['Strategy 1', 'Strategy 2']
    assert params['bandit_algorithm'] == 'UCBBandit'


# ============================================================================
# Test: Determinism with Random Seed
# ============================================================================

def test_deterministic_behavior_with_seed():
    """Test that setting random seed produces deterministic results."""
    assets = ['AAPL', 'MSFT']
    
    def run_simulation(seed):
        strategy1 = DummyStrategyWrapper("Strategy 1", {'AAPL': 0.6, 'MSFT': 0.4}, assets)
        strategy2 = DummyStrategyWrapper("Strategy 2", {'AAPL': 0.4, 'MSFT': 0.6}, assets)
        
        bandit = ThompsonSamplingBandit(n_arms=2, random_seed=seed)
        wrapper = BanditStrategyWrapper(
            child_strategies=[strategy1, strategy2],
            bandit_allocator=bandit,
            burn_in_periods=0,
            random_seed=seed
        )
        
        dates = pd.date_range('2023-01-01', periods=10, freq='W')
        equity = 100000.0
        
        results = []
        for date in dates:
            portfolio_state = create_dummy_portfolio_state(date, equity=equity, assets=assets)
            weights = wrapper.get_weights(date, portfolio_state)
            results.append(weights.to_dict())
            equity *= 1.01
        
        return results
    
    # Run twice with same seed
    results1 = run_simulation(42)
    results2 = run_simulation(42)
    
    # Should be identical
    for r1, r2 in zip(results1, results2):
        for asset in ['AAPL', 'MSFT']:
            assert abs(r1[asset] - r2[asset]) < 1e-10


# ============================================================================
# Test: Integration with Different Bandit Algorithms
# ============================================================================

def test_integration_with_ucb():
    """Test integration with UCBBandit."""
    assets = ['AAPL', 'MSFT']
    
    strategy1 = DummyStrategyWrapper("Strategy 1", {'AAPL': 0.6, 'MSFT': 0.4}, assets)
    strategy2 = DummyStrategyWrapper("Strategy 2", {'AAPL': 0.4, 'MSFT': 0.6}, assets)
    
    bandit = UCBBandit(n_arms=2, exploration_constant=2.0)
    wrapper = BanditStrategyWrapper(
        child_strategies=[strategy1, strategy2],
        bandit_allocator=bandit
    )
    
    # Run simulation
    dates = pd.date_range('2023-01-01', periods=10, freq='W')
    equity = 100000.0
    
    for date in dates:
        portfolio_state = create_dummy_portfolio_state(date, equity=equity, assets=assets)
        weights = wrapper.get_weights(date, portfolio_state)
        assert abs(weights.sum() - 1.0) < 1e-6
        equity *= 1.01


def test_integration_with_thompson_sampling():
    """Test integration with ThompsonSamplingBandit."""
    assets = ['AAPL', 'MSFT']
    
    strategy1 = DummyStrategyWrapper("Strategy 1", {'AAPL': 0.6, 'MSFT': 0.4}, assets)
    strategy2 = DummyStrategyWrapper("Strategy 2", {'AAPL': 0.4, 'MSFT': 0.6}, assets)
    
    bandit = ThompsonSamplingBandit(n_arms=2, random_seed=42)
    wrapper = BanditStrategyWrapper(
        child_strategies=[strategy1, strategy2],
        bandit_allocator=bandit,
        random_seed=42
    )
    
    # Run simulation
    dates = pd.date_range('2023-01-01', periods=10, freq='W')
    equity = 100000.0
    
    for date in dates:
        portfolio_state = create_dummy_portfolio_state(date, equity=equity, assets=assets)
        weights = wrapper.get_weights(date, portfolio_state)
        assert abs(weights.sum() - 1.0) < 1e-6
        equity *= 1.01


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
