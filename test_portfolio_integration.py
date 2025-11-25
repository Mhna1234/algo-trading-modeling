"""
Portfolio Integration Test Script

This script tests the integration of the new Portfolio class with the existing
algorithmic trading system to ensure everything works correctly.

Test Coverage:
- Portfolio class initialization and basic functionality
- Configuration adapter functionality
- Forecast adapter integration
- Signal adapter integration
- Backtester adapter compatibility
- End-to-end pipeline execution
"""

import sys
import os
import warnings
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import modules for testing
try:
    from src.portfolio import Portfolio, PortfolioResult
    from src.portfolio_manager import (
        PortfolioBacktester, ForecastManager, 
        SignalManager, ConfigManager
    )
    from src.utils import TradingConfig, setup_logging
    print("✓ Successfully imported Portfolio integration modules")
except ImportError as e:
    print(f"✗ Failed to import modules: {e}")
    sys.exit(1)

# Suppress warnings
warnings.filterwarnings('ignore')

# Set up logging
setup_logging(level='INFO')
logger = logging.getLogger(__name__)


def create_test_data(n_periods=500, n_assets=4):
    """Create synthetic test data for testing."""
    print("Creating synthetic test data...")
    
    # Generate dates
    dates = pd.date_range(start='2020-01-01', periods=n_periods, freq='D')
    
    # Asset names
    assets = ['AAPL', 'MSFT', 'SPY', 'QQQ'][:n_assets]
    
    # Generate correlated returns
    np.random.seed(42)
    returns = np.random.multivariate_normal(
        mean=[0.0005, 0.0004, 0.0003, 0.0006][:n_assets],
        cov=np.array([
            [0.0004, 0.0001, 0.0002, 0.0001],
            [0.0001, 0.0003, 0.0001, 0.0002],
            [0.0002, 0.0001, 0.0002, 0.0001],
            [0.0001, 0.0002, 0.0001, 0.0005]
        ])[:n_assets, :n_assets],
        size=n_periods
    )
    
    # Create price data from returns
    prices = pd.DataFrame(index=dates, columns=assets)
    prices.iloc[0] = [100.0] * n_assets  # Starting prices
    
    for i in range(1, n_periods):
        prices.iloc[i] = prices.iloc[i-1] * (1 + returns[i])
    
    # Create some trading signals
    returns_df = pd.DataFrame(returns, index=dates, columns=assets)
    signals = returns_df.rolling(window=20).mean() * 10  # Simple momentum signals
    
    return prices, signals, returns_df


def test_portfolio_class():
    """Test basic Portfolio class functionality."""
    print("\n" + "="*50)
    print("Testing Portfolio Class")
    print("="*50)
    
    try:
        # Create test data
        prices, signals, returns = create_test_data()
        
        # Initialize Portfolio
        portfolio = Portfolio(
            prices=prices,
            rf=0.02/252,  # 2% annual risk-free rate
            trading_cost_bps=10.0,  # 10 bps trading costs
            slippage_bps=2.0  # 2 bps slippage
        )
        
        print(f"✓ Portfolio initialized with {len(portfolio.assets)} assets")
        print(f"✓ Returns data shape: {portfolio.returns.shape}")
        
        # Test optimization methods
        tangency_weights = portfolio.tangency_weights(lookback=60)
        print(f"✓ Tangency weights computed: sum={tangency_weights.sum():.3f}")
        
        target_return_weights = portfolio.target_return_mvo(
            target_return=0.10, lookback=60
        )
        print(f"✓ Target return MVO weights computed: sum={target_return_weights.sum():.3f}")
        
        # Test rule-based weight generation
        equal_weight_rule = portfolio.equal_weight_rule()
        momentum_rule = portfolio.momentum_rule(top_k=2)
        
        equal_weights = portfolio.build_target_weights_from_rule(
            rule=equal_weight_rule,
            schedule='M'
        )
        print(f"✓ Equal weight rule generated {equal_weights.shape[0]} periods")
        
        momentum_weights = portfolio.build_target_weights_from_rule(
            rule=momentum_rule,
            schedule='M'
        )
        print(f"✓ Momentum rule generated {momentum_weights.shape[0]} periods")
        
        # Test backtesting
        backtest_result = portfolio.rebalance(
            target_weights=equal_weights,
            initial_equity=100000
        )
        
        print(f"✓ Backtest completed successfully")
        print(f"  Final equity: ${backtest_result.equity_curve.iloc[-1]:,.2f}")
        print(f"  Annual return: {backtest_result.perf['ann_return']:.2%}")
        print(f"  Sharpe ratio: {backtest_result.perf['sharpe']:.3f}")
        print(f"  Max drawdown: {backtest_result.perf['max_drawdown']:.2%}")
        
        return True
        
    except Exception as e:
        print(f"✗ Portfolio class test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_configuration_adapter():
    """Test configuration adapter functionality."""
    print("\n" + "="*50)
    print("Testing Configuration Adapter")
    print("="*50)
    
    try:
        # Create test configuration
        config = TradingConfig()
        config.risk_free_rate = 0.03
        config.transaction_cost = 0.0015
        config.slippage_bps = 5.0
        config.long_only = True
        config.leverage_cap = 1.5
        
        # Test configuration conversion
        portfolio_params = ConfigManager.trading_config_to_portfolio_params(config)
        print(f"✓ Portfolio params: {portfolio_params}")
        
        optimization_params = ConfigManager.trading_config_to_optimization_params(config)
        print(f"✓ Optimization params: {optimization_params}")
        
        # Verify conversions
        assert abs(portfolio_params['rf'] - 0.03/252) < 1e-6, "Risk-free rate conversion failed"
        assert abs(portfolio_params['trading_cost_bps'] - 15.0) < 1e-6, "Trading cost conversion failed"
        assert portfolio_params['slippage_bps'] == 5.0, "Slippage pass-through failed"
        
        print("✓ All configuration conversions successful")
        return True
        
    except Exception as e:
        print(f"✗ Configuration adapter test failed: {e}")
        return False


def test_forecast_manager():
    """Test forecast adapter functionality."""
    print("\n" + "="*50)
    print("Testing Forecast Adapter")
    print("="*50)
    
    try:
        # Create test data
        prices, signals, returns = create_test_data()
        config = TradingConfig()
        
        # Initialize Portfolio and manager
        portfolio_params = ConfigManager.trading_config_to_portfolio_params(config)
        portfolio = Portfolio(prices, **portfolio_params)
        
        forecast_manager = ForecastManager(portfolio, config)
        print("✓ Forecast manager initialized")
        
        # Create mock forecaster
        class MockForecaster:
            def forecast_portfolio(self, returns, steps=1):
                # Return simple mean forecasts
                mean_forecast = returns.mean().to_frame().T
                vol_forecast = returns.std().to_frame().T
                return mean_forecast, vol_forecast
        
        mock_forecaster = MockForecaster()
        
        # Test rule creation
        forecast_rule = forecast_manager.create_forecast_rule(mock_forecaster)
        print("✓ Forecast rule created")
        
        # Test weight generation
        weights = forecast_manager.generate_weights_from_forecasts(
            forecaster=mock_forecaster,
            schedule='M'
        )
        
        print(f"✓ Forecast weights generated: {weights.shape}")
        print(f"  Weight sums range: {weights.sum(axis=1).min():.3f} to {weights.sum(axis=1).max():.3f}")
        
        return True
        
    except Exception as e:
        print(f"✗ Forecast adapter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_signal_manager():
    """Test signal adapter functionality."""
    print("\n" + "="*50)
    print("Testing Signal Adapter")
    print("="*50)
    
    try:
        # Create test data
        prices, signals, returns = create_test_data()
        config = TradingConfig()
        config.signal_threshold = 0.001
        
        # Initialize Portfolio and manager
        portfolio_params = ConfigManager.trading_config_to_portfolio_params(config)
        portfolio = Portfolio(prices, **portfolio_params)
        
        signal_manager = SignalManager(portfolio, config)
        print("✓ Signal manager initialized")
        
        # Test rule creation
        signal_rule = signal_manager.create_signal_rule(signals)
        print("✓ Signal rule created")
        
        # Test weight generation
        weights = signal_manager.generate_weights_from_signals(
            signals_data=signals,
            schedule='M'
        )
        
        print(f"✓ Signal weights generated: {weights.shape}")
        print(f"  Weight sums range: {weights.sum(axis=1).min():.3f} to {weights.sum(axis=1).max():.3f}")
        
        return True
        
    except Exception as e:
        print(f"✗ Signal adapter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backtester():
    """Test backtester adapter functionality."""
    print("\n" + "="*50)
    print("Testing Backtester Adapter")
    print("="*50)
    
    try:
        # Create test data
        prices, signals, returns = create_test_data()
        config = TradingConfig()
        config.initial_capital = 100000
        config.use_portfolio_class = True
        
        # Initialize adapter
        backtester = PortfolioBacktester(config)
        print("✓ Backtester adapter initialized")
        
        # Create target weights (equal weight)
        weights = pd.DataFrame(
            index=prices.index,
            columns=prices.columns,
            data=1/len(prices.columns)
        )
        
        # Run backtest
        results = backtester.run_backtest(
            price_data=prices,
            weight_data=weights,
            benchmark_data=prices[['SPY']],
            signals_data=signals
        )
        
        print("✓ Backtest completed via backtester")
        print(f"  Final equity: ${results.portfolio_nav.iloc[-1]:,.2f}")
        print(f"  Total return: {results.total_return:.2%}")
        print(f"  Sharpe ratio: {results.sharpe_ratio:.3f}")
        print(f"  Max drawdown: {results.max_drawdown:.2%}")
        
        # Test summary interface
        summary = results.summary()
        print(f"✓ Summary interface working: {len(summary)} metrics")
        
        return True
        
    except Exception as e:
        print(f"✗ Backtester adapter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_end_to_end_pipeline():
    """Test end-to-end pipeline with Portfolio class."""
    print("\n" + "="*50)
    print("Testing End-to-End Pipeline")
    print("="*50)
    
    try:
        # Create test data
        prices, signals, returns = create_test_data(n_periods=252, n_assets=3)
        
        # Create configuration
        config = TradingConfig()
        config.use_portfolio_class = True
        config.initial_capital = 100000
        config.rebalance_frequency = 'monthly'
        config.optimization_method = 'sharpe'
        
        print(f"✓ Configuration created: {config.optimization_method} method")
        
        # Initialize Portfolio system
        portfolio_params = ConfigManager.trading_config_to_portfolio_params(config)
        portfolio = Portfolio(prices, **portfolio_params)
        
        # Create managers
        forecast_manager = ForecastManager(portfolio, config)
        signal_manager = SignalManager(portfolio, config)
        backtester = PortfolioBacktester(config)
        
        print("✓ All managers initialized")
        
        # Mock forecaster
        class SimpleForecaster:
            def forecast_portfolio(self, returns, steps=1):
                mean_forecast = returns.mean().to_frame().T
                vol_forecast = returns.std().to_frame().T
                return mean_forecast, vol_forecast
        
        forecaster = SimpleForecaster()
        
        # Generate weights using forecasts
        forecast_weights = forecast_manager.generate_weights_from_forecasts(
            forecaster=forecaster,
            schedule='M'
        )
        
        # Generate weights using signals
        signal_weights = signal_manager.generate_weights_from_signals(
            signals_data=signals,
            schedule='M'
        )
        
        print("✓ Weights generated from both forecasts and signals")
        
        # Combine weights (50/50)
        combined_weights = 0.5 * forecast_weights + 0.5 * signal_weights
        combined_weights = combined_weights.div(combined_weights.sum(axis=1), axis=0)
        
        # Run backtest
        results = backtester.run_backtest(
            price_data=prices,
            weight_data=combined_weights,
            benchmark_data=prices[['SPY']],
            signals_data=signals
        )
        
        print("✓ End-to-end pipeline completed successfully")
        print(f"  Strategy performance:")
        print(f"    Final value: ${results.portfolio_nav.iloc[-1]:,.2f}")
        print(f"    Total return: {results.total_return:.2%}")
        print(f"    Annual return: {results.annualized_return:.2%}")
        print(f"    Sharpe ratio: {results.sharpe_ratio:.3f}")
        print(f"    Max drawdown: {results.max_drawdown:.2%}")
        print(f"    Total trades: {results.total_trades}")
        
        return True
        
    except Exception as e:
        print(f"✗ End-to-end pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all integration tests."""
    print("Starting Portfolio Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Portfolio Class", test_portfolio_class),
        ("Configuration Adapter", test_configuration_adapter),
        ("Forecast Adapter", test_forecast_manager),
        ("Signal Adapter", test_signal_manager),
        ("Backtester Adapter", test_backtester),
        ("End-to-End Pipeline", test_end_to_end_pipeline)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\nRunning {test_name} test...")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{test_name:25} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Portfolio integration is ready to use.")
        return True
    else:
        print(f"\n⚠️  {total - passed} tests failed. Please review and fix issues.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
