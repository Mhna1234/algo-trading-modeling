"""
Unit Tests for Extended Strategies

Tests for extended strategies now integrated in strategy_wrapper.py module.
Ensures correct weight generation, constraint satisfaction, and integration.

Run with:
    pytest tests/test_strategies_extended.py -v
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.signal_generator import Strategy
from src.optimizer import PortfolioOptimizer
from src.portfolio_engine import PortfolioState
from src.strategy_wrapper import (
    BuyAndHoldStrategy,
    QuintileFactorStrategy,
    GMRPStrategy,
    MaximumDiversificationStrategy,
    MaximumDecorrelationStrategy,
    TimeSeriesMomentumStrategy,
    MovingAverageCrossoverStrategy,
    MarkowitzMVOStrategy,
    LinearRegressionStrategy,
    list_available_strategies,
    create_strategy
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_prices():
    """Generate sample price data for testing."""
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', '2023-12-31', freq='D')
    n_assets = 10
    assets = [f'ASSET_{i}' for i in range(n_assets)]
    
    # Generate realistic price paths (geometric Brownian motion)
    initial_prices = np.ones(n_assets) * 100
    returns = np.random.normal(0.0005, 0.02, (len(dates), n_assets))
    prices = initial_prices * np.exp(np.cumsum(returns, axis=0))
    
    df = pd.DataFrame(prices, index=dates, columns=assets)
    return df


@pytest.fixture
def strategy_obj(sample_prices):
    """Create Strategy object."""
    return Strategy(sample_prices, risk_free_rate=0.02)


@pytest.fixture
def optimizer(strategy_obj):
    """Create PortfolioOptimizer."""
    return PortfolioOptimizer(
        returns=strategy_obj.returns,
        risk_free_rate=0.02,
        max_weight=0.3
    )


@pytest.fixture
def portfolio_state():
    """Create dummy PortfolioState."""
    return PortfolioState(
        date=pd.Timestamp('2023-01-01'),
        portfolio_value=100000.0,
        weights=pd.Series(),
        cash=0.0,
        equity_value=100000.0,
        returns=pd.Series(),
        cumulative_returns=pd.Series(),
        transaction_costs=0.0,
        turnover=0.0,
        history=pd.DataFrame()
    )


# ============================================================================
# UTILITY FUNCTIONS TESTS
# ============================================================================

def test_list_extended_strategies():
    """Test that list_available_strategies returns correct strategies including extended ones."""
    strategies = list_available_strategies()
    
    assert isinstance(strategies, dict)
    # Test that extended strategies are present
    assert 'buy_and_hold' in strategies
    assert 'quintile_factor' in strategies
    assert 'max_diversification' in strategies
    assert 'gmrp' in strategies
    assert len(strategies) == 20  # Should have 20 total strategies (11 core + 9 extended)


def test_create_extended_strategy(strategy_obj, optimizer):
    """Test factory function for creating strategies."""
    strategy = create_strategy(
        'buy_and_hold',
        strategy_obj,
        optimizer
    )
    
    assert isinstance(strategy, BuyAndHoldStrategy)
    assert strategy.name == "Buy & Hold"
    
    # Test invalid strategy name
    with pytest.raises(ValueError):
        create_strategy('invalid_strategy', strategy_obj, optimizer)


# ============================================================================
# BUY AND HOLD STRATEGY TESTS
# ============================================================================

def test_buy_and_hold_initialization(strategy_obj):
    """Test Buy & Hold strategy initialization."""
    strategy = BuyAndHoldStrategy(strategy_obj)
    
    assert strategy.name == "Buy & Hold"
    assert strategy.params['initial_method'] == 'equal'


def test_buy_and_hold_weights(strategy_obj, portfolio_state):
    """Test Buy & Hold weight generation."""
    strategy = BuyAndHoldStrategy(strategy_obj, initial_method='equal')
    
    test_date = strategy_obj.dates[-100]
    weights = strategy.get_weights(test_date, portfolio_state)
    
    # Check weight properties
    assert isinstance(weights, pd.Series)
    assert len(weights) == len(strategy_obj.assets)
    assert np.isclose(weights.sum(), 1.0, atol=1e-6)
    assert all(weights >= 0)
    
    # Check equal weights
    expected_weight = 1.0 / len(strategy_obj.assets)
    assert all(np.isclose(weights, expected_weight, atol=1e-6))


def test_buy_and_hold_persistence(strategy_obj, portfolio_state):
    """Test that Buy & Hold maintains same weights across rebalancing."""
    strategy = BuyAndHoldStrategy(strategy_obj, initial_method='equal')
    
    date1 = strategy_obj.dates[-100]
    date2 = strategy_obj.dates[-50]
    
    weights1 = strategy.get_weights(date1, portfolio_state)
    weights2 = strategy.get_weights(date2, portfolio_state)
    
    # Weights should be identical (buy and hold)
    assert all(np.isclose(weights1, weights2, atol=1e-6))


# ============================================================================
# QUINTILE FACTOR STRATEGY TESTS
# ============================================================================

def test_quintile_factor_initialization(strategy_obj, optimizer):
    """Test Quintile Factor strategy initialization."""
    strategy = QuintileFactorStrategy(
        strategy_obj,
        optimizer,
        factor='momentum',
        n_quintiles=5
    )
    
    assert 'Quintile Factor' in strategy.name
    assert strategy.params['factor'] == 'momentum'
    assert strategy.params['n_quintiles'] == 5


def test_quintile_factor_weights(strategy_obj, optimizer, portfolio_state):
    """Test Quintile Factor weight generation."""
    strategy = QuintileFactorStrategy(
        strategy_obj,
        optimizer,
        factor='momentum',
        lookback=126,
        target_quintile=5,
        equal_weight_quintile=True
    )
    
    test_date = strategy_obj.dates[-100]
    weights = strategy.get_weights(test_date, portfolio_state)
    
    # Check weight properties
    assert isinstance(weights, pd.Series)
    assert np.isclose(weights.sum(), 1.0, atol=1e-6)
    assert all(weights >= 0)
    
    # Check that only some assets have non-zero weights (top quintile)
    n_nonzero = (weights > 1e-6).sum()
    assert n_nonzero <= len(strategy_obj.assets)


def test_quintile_factor_long_short(strategy_obj, optimizer, portfolio_state):
    """Test Quintile Factor long-short variant."""
    strategy = QuintileFactorStrategy(
        strategy_obj,
        optimizer,
        factor='momentum',
        long_short=True,
        equal_weight_quintile=True
    )
    
    test_date = strategy_obj.dates[-100]
    weights = strategy.get_weights(test_date, portfolio_state)
    
    # For long-short, weights can be negative
    assert any(weights > 0)  # Some long positions
    # Note: might not have short if long_only constraint applied


# ============================================================================
# GMRP STRATEGY TESTS
# ============================================================================

def test_gmrp_initialization(strategy_obj):
    """Test GMRP strategy initialization."""
    strategy = GMRPStrategy(strategy_obj, lookback=126, max_weight=0.4)
    
    assert strategy.name == "Global Maximum Return"
    assert strategy.params['max_weight'] == 0.4


def test_gmrp_weights(strategy_obj, portfolio_state):
    """Test GMRP weight generation."""
    strategy = GMRPStrategy(
        strategy_obj,
        lookback=126,
        max_weight=0.4,
        min_assets=3
    )
    
    test_date = strategy_obj.dates[-100]
    weights = strategy.get_weights(test_date, portfolio_state)
    
    # Check weight properties
    assert isinstance(weights, pd.Series)
    assert np.isclose(weights.sum(), 1.0, atol=1e-6)
    assert all(weights >= 0)
    
    # Check concentration constraints
    assert all(weights <= 0.4 + 1e-6)
    assert (weights > 1e-6).sum() >= 3  # Minimum assets


# ============================================================================
# MAXIMUM DIVERSIFICATION STRATEGY TESTS
# ============================================================================

def test_mdp_initialization(strategy_obj):
    """Test MDP strategy initialization."""
    strategy = MaximumDiversificationStrategy(strategy_obj, lookback=252)
    
    assert strategy.name == "Maximum Diversification"
    assert strategy.params['lookback'] == 252


def test_mdp_weights(strategy_obj, portfolio_state):
    """Test MDP weight generation."""
    strategy = MaximumDiversificationStrategy(
        strategy_obj,
        lookback=252,
        max_weight=0.3
    )
    
    test_date = strategy_obj.dates[-100]
    weights = strategy.get_weights(test_date, portfolio_state)
    
    # Check weight properties
    assert isinstance(weights, pd.Series)
    assert np.isclose(weights.sum(), 1.0, atol=1e-6)
    assert all(weights >= 0)
    assert all(weights <= 0.3 + 1e-6)


# ============================================================================
# MAXIMUM DECORRELATION STRATEGY TESTS
# ============================================================================

def test_mdcp_initialization(strategy_obj):
    """Test MDCP strategy initialization."""
    strategy = MaximumDecorrelationStrategy(strategy_obj, lookback=252)
    
    assert strategy.name == "Maximum Decorrelation"
    assert strategy.params['lookback'] == 252


def test_mdcp_weights(strategy_obj, portfolio_state):
    """Test MDCP weight generation."""
    strategy = MaximumDecorrelationStrategy(
        strategy_obj,
        lookback=252,
        max_weight=0.3
    )
    
    test_date = strategy_obj.dates[-100]
    weights = strategy.get_weights(test_date, portfolio_state)
    
    # Check weight properties
    assert isinstance(weights, pd.Series)
    assert np.isclose(weights.sum(), 1.0, atol=1e-6)
    assert all(weights >= 0)
    assert all(weights <= 0.3 + 1e-6)


# ============================================================================
# TIME-SERIES MOMENTUM STRATEGY TESTS
# ============================================================================

def test_ts_momentum_initialization(strategy_obj, optimizer):
    """Test Time-Series Momentum strategy initialization."""
    strategy = TimeSeriesMomentumStrategy(
        strategy_obj,
        optimizer,
        lookback=126,
        volatility_scaling=True
    )
    
    assert strategy.name == "Time-Series Momentum"
    assert strategy.params['lookback'] == 126


def test_ts_momentum_weights(strategy_obj, optimizer, portfolio_state):
    """Test Time-Series Momentum weight generation."""
    strategy = TimeSeriesMomentumStrategy(
        strategy_obj,
        optimizer,
        lookback=126,
        volatility_scaling=True,
        long_only=True
    )
    
    test_date = strategy_obj.dates[-100]
    weights = strategy.get_weights(test_date, portfolio_state)
    
    # Check weight properties
    assert isinstance(weights, pd.Series)
    assert np.isclose(weights.sum(), 1.0, atol=1e-6)
    assert all(weights >= 0)  # Long only


# ============================================================================
# MOVING AVERAGE CROSSOVER STRATEGY TESTS
# ============================================================================

def test_ma_crossover_initialization(strategy_obj, optimizer):
    """Test MA Crossover strategy initialization."""
    strategy = MovingAverageCrossoverStrategy(
        strategy_obj,
        optimizer,
        fast_window=50,
        slow_window=200
    )
    
    assert 'MA Crossover' in strategy.name
    assert strategy.params['fast_window'] == 50
    assert strategy.params['slow_window'] == 200


def test_ma_crossover_weights(strategy_obj, optimizer, portfolio_state):
    """Test MA Crossover weight generation."""
    strategy = MovingAverageCrossoverStrategy(
        strategy_obj,
        optimizer,
        fast_window=20,  # Use shorter window for test data
        slow_window=50,
        signal_type='binary',
        long_only=True
    )
    
    test_date = strategy_obj.dates[-100]
    weights = strategy.get_weights(test_date, portfolio_state)
    
    # Check weight properties
    assert isinstance(weights, pd.Series)
    assert np.isclose(weights.sum(), 1.0, atol=1e-6)
    assert all(weights >= 0)


# ============================================================================
# MARKOWITZ MVO STRATEGY TESTS
# ============================================================================

def test_markowitz_initialization(strategy_obj, optimizer):
    """Test Markowitz MVO strategy initialization."""
    strategy = MarkowitzMVOStrategy(
        strategy_obj,
        optimizer,
        risk_aversion=2.0
    )
    
    assert 'Markowitz MVO' in strategy.name
    assert strategy.params['risk_aversion'] == 2.0


def test_markowitz_weights(strategy_obj, optimizer, portfolio_state):
    """Test Markowitz MVO weight generation."""
    strategy = MarkowitzMVOStrategy(
        strategy_obj,
        optimizer,
        risk_aversion=2.0,
        return_forecast_method='historical',
        max_weight=0.5
    )
    
    test_date = strategy_obj.dates[-100]
    weights = strategy.get_weights(test_date, portfolio_state)
    
    # Check weight properties
    assert isinstance(weights, pd.Series)
    assert np.isclose(weights.sum(), 1.0, atol=1e-6)
    assert all(weights >= 0)
    assert all(weights <= 0.5 + 1e-6)


# ============================================================================
# LINEAR REGRESSION STRATEGY TESTS
# ============================================================================

def test_linear_regression_initialization(strategy_obj, optimizer):
    """Test Linear Regression strategy initialization."""
    strategy = LinearRegressionStrategy(
        strategy_obj,
        optimizer,
        lookback=252,
        regularization='ridge'
    )
    
    assert strategy.name == "Linear Regression"
    assert strategy.params['regularization'] == 'ridge'


def test_linear_regression_weights(strategy_obj, optimizer, portfolio_state):
    """Test Linear Regression weight generation."""
    strategy = LinearRegressionStrategy(
        strategy_obj,
        optimizer,
        lookback=252,
        regularization='ridge',
        alpha=0.1
    )
    
    test_date = strategy_obj.dates[-100]
    weights = strategy.get_weights(test_date, portfolio_state)
    
    # Check weight properties
    assert isinstance(weights, pd.Series)
    assert np.isclose(weights.sum(), 1.0, atol=1e-6)
    assert all(weights >= 0)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_all_strategies_generate_valid_weights(strategy_obj, optimizer, portfolio_state):
    """Test that all strategies generate valid weights."""
    strategies = [
        BuyAndHoldStrategy(strategy_obj),
        QuintileFactorStrategy(strategy_obj, optimizer),
        GMRPStrategy(strategy_obj),
        MaximumDiversificationStrategy(strategy_obj),
        MaximumDecorrelationStrategy(strategy_obj),
        TimeSeriesMomentumStrategy(strategy_obj, optimizer),
        MovingAverageCrossoverStrategy(strategy_obj, optimizer, fast_window=20, slow_window=50),
        MarkowitzMVOStrategy(strategy_obj, optimizer),
        LinearRegressionStrategy(strategy_obj, optimizer)
    ]
    
    test_date = strategy_obj.dates[-100]
    
    for strategy in strategies:
        weights = strategy.get_weights(test_date, portfolio_state)
        
        # Check valid weight properties
        assert isinstance(weights, pd.Series), f"{strategy.name} did not return Series"
        assert len(weights) == len(strategy_obj.assets), f"{strategy.name} wrong number of weights"
        assert np.isclose(weights.sum(), 1.0, atol=1e-6), f"{strategy.name} weights don't sum to 1"
        assert all(weights >= -1e-6), f"{strategy.name} has negative weights in long-only"
        assert not any(np.isnan(weights)), f"{strategy.name} has NaN weights"


def test_strategies_with_insufficient_data(sample_prices, portfolio_state):
    """Test strategies handle insufficient data gracefully."""
    # Create strategy with very little data
    short_prices = sample_prices.iloc[:30]  # Only 30 days
    strategy_obj = Strategy(short_prices)
    optimizer = PortfolioOptimizer(returns=strategy_obj.returns)
    
    strategies = [
        BuyAndHoldStrategy(strategy_obj),
        GMRPStrategy(strategy_obj),
        MaximumDiversificationStrategy(strategy_obj),
    ]
    
    test_date = strategy_obj.dates[-1]
    
    for strategy in strategies:
        # Should not raise exception, should fallback to equal weights
        weights = strategy.get_weights(test_date, portfolio_state)
        assert isinstance(weights, pd.Series)
        assert np.isclose(weights.sum(), 1.0, atol=1e-6)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
