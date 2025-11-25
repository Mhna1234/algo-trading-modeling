"""
Unit Tests for Portfolio Engine

Run with: python -m pytest tests/test_portfolio_engine.py -v
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from src.portfolio_engine import PortfolioEngine, PortfolioState, PortfolioResult
from src.strategy_wrapper import EqualWeightStrategy, MomentumStrategy
from src.strategy import Strategy
from src.optimizer import PortfolioOptimizer


@pytest.fixture
def sample_prices():
    """Generate sample price data for testing."""
    dates = pd.bdate_range('2020-01-01', '2022-12-31')
    n_assets = 5
    tickers = [f'ASSET_{i+1}' for i in range(n_assets)]
    
    np.random.seed(42)
    returns = pd.DataFrame(
        np.random.normal(0.0005, 0.015, (len(dates), n_assets)),
        index=dates,
        columns=tickers
    )
    
    prices = 100 * (1 + returns).cumprod()
    return prices


@pytest.fixture
def portfolio_engine(sample_prices):
    """Create portfolio engine instance."""
    return PortfolioEngine(
        prices=sample_prices,
        initial_capital=1_000_000,
        transaction_cost_bps=5.0,
        slippage_bps=1.0
    )


@pytest.fixture
def strategy_and_optimizer(sample_prices):
    """Create strategy and optimizer instances."""
    strategy = Strategy(sample_prices)
    optimizer = PortfolioOptimizer(strategy.get_return_matrix())
    return strategy, optimizer


class TestPortfolioEngine:
    """Test cases for PortfolioEngine class."""
    
    def test_initialization(self, portfolio_engine, sample_prices):
        """Test portfolio engine initialization."""
        assert portfolio_engine.initial_capital == 1_000_000
        assert portfolio_engine.transaction_cost_bps == 5.0
        assert portfolio_engine.slippage_bps == 1.0
        assert len(portfolio_engine.assets) == len(sample_prices.columns)
    
    def test_get_rebalance_dates(self, portfolio_engine, sample_prices):
        """Test rebalance date generation."""
        start = sample_prices.index[0]
        end = sample_prices.index[-1]
        
        # Monthly rebalancing
        monthly_dates = portfolio_engine._get_rebalance_dates(start, end, 'M')
        assert len(monthly_dates) > 0
        assert len(monthly_dates) < len(sample_prices)
        
        # Daily rebalancing
        daily_dates = portfolio_engine._get_rebalance_dates(start, end, 'D')
        assert len(daily_dates) == len(sample_prices.loc[start:end])
    
    def test_equal_weight_backtest(self, portfolio_engine, strategy_and_optimizer):
        """Test backtest with equal weight strategy."""
        strategy, optimizer = strategy_and_optimizer
        
        equal_weight = EqualWeightStrategy(strategy)
        
        result = portfolio_engine.run_backtest(
            strategy_wrapper=equal_weight,
            start_date='2021-01-01',
            end_date='2022-12-31',
            rebalance_freq='M'
        )
        
        # Check result type
        assert isinstance(result, PortfolioResult)
        
        # Check data exists
        assert len(result.equity_curve) > 0
        assert len(result.weights_history) > 0
        assert len(result.returns_series) > 0
        
        # Check metrics
        assert 'annual_return' in result.summary_metrics
        assert 'sharpe_ratio' in result.summary_metrics
        assert 'max_drawdown' in result.summary_metrics
        
        # Check equity curve is sensible
        assert result.equity_curve.iloc[0] > 0
        assert result.equity_curve.iloc[-1] > 0
    
    def test_portfolio_state(self, portfolio_engine, sample_prices):
        """Test portfolio state building."""
        date = sample_prices.index[300]
        
        # Initialize some state
        portfolio_engine._current_equity = 1_100_000
        portfolio_engine._current_cash = 100_000
        portfolio_engine._last_rebalance_date = sample_prices.index[250]
        
        state = portfolio_engine._build_portfolio_state(date)
        
        assert isinstance(state, PortfolioState)
        assert state.date == date
        assert state.equity == 1_100_000
        assert state.cash == 100_000
        assert len(state.price_history) <= 300
    
    def test_metrics_calculation(self, portfolio_engine, strategy_and_optimizer):
        """Test metrics calculation."""
        strategy, optimizer = strategy_and_optimizer
        equal_weight = EqualWeightStrategy(strategy)
        
        result = portfolio_engine.run_backtest(
            equal_weight, '2021-01-01', '2022-12-31', 'M'
        )
        
        metrics = result.summary_metrics
        
        # Check all required metrics exist
        required_metrics = [
            'total_return', 'annual_return', 'annual_volatility',
            'sharpe_ratio', 'sortino_ratio', 'max_drawdown',
            'calmar_ratio', 'win_rate', 'profit_factor'
        ]
        
        for metric in required_metrics:
            assert metric in metrics
            assert not np.isnan(metrics[metric]) or metric in ['calmar_ratio', 'profit_factor']
    
    def test_dashboard_data_export(self, portfolio_engine, strategy_and_optimizer):
        """Test dashboard data export."""
        strategy, optimizer = strategy_and_optimizer
        equal_weight = EqualWeightStrategy(strategy)
        
        result = portfolio_engine.run_backtest(
            equal_weight, '2021-01-01', '2022-12-31', 'M'
        )
        
        dashboard_data = portfolio_engine.get_dashboard_data()
        
        # Check all required keys
        required_keys = [
            'equity_curve', 'weights_history', 'summary_metrics',
            'rolling_metrics', 'drawdown_series', 'returns_distribution',
            'turnover', 'costs', 'risk_metrics', 'trades', 'cash'
        ]
        
        for key in required_keys:
            assert key in dashboard_data


class TestStrategies:
    """Test cases for strategy wrappers."""
    
    def test_equal_weight_strategy(self, strategy_and_optimizer):
        """Test equal weight strategy."""
        strategy, _ = strategy_and_optimizer
        
        equal_weight = EqualWeightStrategy(strategy)
        
        # Create dummy portfolio state
        state = PortfolioState(
            date=strategy.prices.index[300],
            current_weights=pd.Series(0.2, index=strategy.assets + ['CASH']),
            current_shares=pd.Series(0, index=strategy.assets),
            cash=1_000_000,
            equity=1_000_000,
            price_history=strategy.prices.iloc[:300],
            return_history=strategy.returns.iloc[:300]
        )
        
        weights = equal_weight.get_weights(state.date, state)
        
        # Check weights
        assert len(weights) == len(strategy.assets)
        assert np.allclose(weights.sum(), 1.0)
        assert np.allclose(weights.values, 1.0 / len(strategy.assets))
    
    def test_momentum_strategy(self, strategy_and_optimizer):
        """Test momentum strategy."""
        strategy, optimizer = strategy_and_optimizer
        
        momentum = MomentumStrategy(
            strategy, optimizer,
            top_k=3, lookback=63
        )
        
        state = PortfolioState(
            date=strategy.prices.index[300],
            current_weights=pd.Series(0.2, index=strategy.assets + ['CASH']),
            current_shares=pd.Series(0, index=strategy.assets),
            cash=1_000_000,
            equity=1_000_000,
            price_history=strategy.prices.iloc[:300],
            return_history=strategy.returns.iloc[:300]
        )
        
        weights = momentum.get_weights(state.date, state)
        
        # Check weights
        assert len(weights) == len(strategy.assets)
        assert weights.sum() <= 1.01  # Allow small tolerance
        assert (weights >= 0).all()  # Long-only


class TestIntegration:
    """Integration tests."""
    
    def test_full_backtest_workflow(self, sample_prices):
        """Test complete workflow from data to results."""
        # Initialize
        strategy = Strategy(sample_prices)
        optimizer = PortfolioOptimizer(strategy.get_return_matrix())
        portfolio = PortfolioEngine(sample_prices, initial_capital=1_000_000)
        
        # Create strategy
        equal_weight = EqualWeightStrategy(strategy)
        
        # Run backtest
        result = portfolio.run_backtest(
            equal_weight,
            start_date='2021-01-01',
            end_date='2022-12-31',
            rebalance_freq='M'
        )
        
        # Verify complete result
        assert isinstance(result, PortfolioResult)
        assert result.equity_curve.iloc[-1] > 0
        assert len(result.summary_metrics) > 10
        
        # Verify can export dashboard data
        dashboard_data = portfolio.get_dashboard_data()
        assert isinstance(dashboard_data, dict)
        assert len(dashboard_data) > 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
