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
- Visualization generation (optional)
"""

import sys
import os
import warnings
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns

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

# Configure plotting style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Set up logging
setup_logging(level='INFO')
logger = logging.getLogger(__name__)


def create_test_data(n_periods=500, n_assets=4):
    """Create synthetic test data for testing."""
    print("Creating synthetic test data...")
    
    # Generate dates using business days for better alignment with monthly rebalancing
    dates = pd.date_range(start='2020-01-01', periods=n_periods, freq='B')
    
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


def test_visualizations():
    """Test visualization generation."""
    print("\n" + "="*50)
    print("Testing Visualization Generation")
    print("="*50)
    
    try:
        # Set fixed seed for reproducible visualizations
        np.random.seed(123)
        
        # Create test data
        prices, signals, returns = create_test_data(n_periods=250, n_assets=3)
        
        # Initialize Portfolio and run backtest
        portfolio = Portfolio(
            prices=prices,
            rf=0.02/252,
            trading_cost_bps=10.0,
            slippage_bps=2.0
        )
        
        # Create equal weight strategy
        equal_weight_rule = portfolio.equal_weight_rule()
        target_weights = portfolio.build_target_weights_from_rule(
            rule=equal_weight_rule,
            schedule='W'
        )
        
        # Run backtest
        result = portfolio.rebalance(
            target_weights=target_weights,
            initial_equity=100000
        )
        
        print("✓ Backtest completed for visualization")
        
        # Create visualizations
        print("Generating visualizations...")
        
        # 1. Equity curve
        fig1, ax1 = plt.subplots(figsize=(12, 6))
        equity = result.equity_curve
        ax1.plot(equity.index, equity.values, linewidth=2, color='#2E86AB', label='Portfolio')
        ax1.set_title('Portfolio Equity Curve', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Portfolio Value ($)', fontsize=11)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        plt.tight_layout()
        plt.savefig('visualizations/test_equity_curve.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ Equity curve saved: visualizations/test_equity_curve.png")
        
        # 2. Portfolio weights
        fig2, ax2 = plt.subplots(figsize=(12, 6))
        weights_plot = result.weights.drop(columns=['CASH'], errors='ignore')
        if len(weights_plot.columns) > 0:
            weights_plot.plot(kind='area', stacked=True, ax=ax2, alpha=0.7)
            ax2.set_title('Portfolio Weight Allocation', fontsize=14, fontweight='bold')
            ax2.set_ylabel('Weight', fontsize=11)
            ax2.set_ylim([0, 1])
            ax2.legend(loc='center left', bbox_to_anchor=(1, 0.5))
            ax2.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('visualizations/test_portfolio_weights.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ Portfolio weights saved: visualizations/test_portfolio_weights.png")
        
        # 3. Drawdown chart
        fig3, ax3 = plt.subplots(figsize=(12, 6))
        cumulative = equity / equity.iloc[0]
        rolling_max = cumulative.expanding().max()
        drawdown = (cumulative - rolling_max) / rolling_max
        ax3.fill_between(drawdown.index, drawdown.values, 0, alpha=0.7, color='red')
        ax3.plot(drawdown.index, drawdown.values, linewidth=1, color='darkred')
        ax3.set_title('Portfolio Drawdown', fontsize=14, fontweight='bold')
        ax3.set_ylabel('Drawdown', fontsize=11)
        ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))
        ax3.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('visualizations/test_drawdown.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ Drawdown chart saved: visualizations/test_drawdown.png")
        
        # 4. Returns distribution
        fig4, ax4 = plt.subplots(figsize=(12, 6))
        portfolio_returns = equity.pct_change().dropna()
        ax4.hist(portfolio_returns, bins=30, alpha=0.7, color='#2E86AB', edgecolor='black')
        ax4.axvline(portfolio_returns.mean(), color='red', linestyle='--', 
                   linewidth=2, label=f'Mean: {portfolio_returns.mean():.4f}')
        ax4.set_title('Daily Returns Distribution', fontsize=14, fontweight='bold')
        ax4.set_xlabel('Daily Return', fontsize=11)
        ax4.set_ylabel('Frequency', fontsize=11)
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('visualizations/test_returns_distribution.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ Returns distribution saved: visualizations/test_returns_distribution.png")
        
        # 5. Performance summary
        fig5, ax5 = plt.subplots(figsize=(10, 6))
        ax5.axis('off')
        perf_text = f"""
PORTFOLIO PERFORMANCE SUMMARY
{'='*50}

Equity Metrics:
  Initial Capital:    ${100000:,.2f}
  Final Equity:       ${equity.iloc[-1]:,.2f}
  Total Return:       {((equity.iloc[-1]/100000)-1)*100:.2f}%
  
Risk-Adjusted Returns:
  Annual Return:      {result.perf['ann_return']*100:.2f}%
  Annual Volatility:  {result.perf['ann_vol']*100:.2f}%
  Sharpe Ratio:       {result.perf['sharpe']:.3f}
  Sortino Ratio:      {result.perf['sortino']:.3f}
  
Risk Metrics:
  Max Drawdown:       {result.perf['max_drawdown']*100:.2f}%
  Calmar Ratio:       {result.perf['calmar']:.3f}
  CAGR:               {result.perf['cagr']*100:.2f}%
  
Trading Activity:
  Total Trades:       {len(result.trades[result.trades.abs().sum(axis=1) > 0])}
  Avg Daily Turnover: {result.trades.abs().sum(axis=1).mean():.4f}
        """
        ax5.text(0.1, 0.5, perf_text, transform=ax5.transAxes, 
                fontsize=11, verticalalignment='center', family='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
        plt.tight_layout()
        plt.savefig('visualizations/test_performance_summary.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ Performance summary saved: visualizations/test_performance_summary.png")
        
        print(f"\n✓ Successfully generated 5 visualization files")
        print(f"  Performance: Return={result.perf['ann_return']*100:.2f}%, Sharpe={result.perf['sharpe']:.3f}")
        
        return True
        
    except Exception as e:
        print(f"✗ Visualization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_strategy_comparison():
    """Test and compare multiple trading strategies."""
    print("\n" + "="*50)
    print("Testing Strategy Comparison")
    print("="*50)
    
    try:
        # Set fixed seed for reproducible comparison
        np.random.seed(456)
        
        # Create test data with more periods for better comparison
        prices, signals, returns = create_test_data(n_periods=750, n_assets=4)
        
        # Initialize Portfolio
        portfolio = Portfolio(
            prices=prices,
            rf=0.02/252,
            trading_cost_bps=10.0,
            slippage_bps=2.0
        )
        
        print("✓ Portfolio initialized for strategy comparison")
        
        # Define strategies to compare
        strategies = {}
        
        # 1. Equal Weight Strategy
        equal_weight_rule = portfolio.equal_weight_rule()
        equal_weights = portfolio.build_target_weights_from_rule(
            rule=equal_weight_rule,
            schedule=None,  # Rebalance every period for clear comparison
            lookback=60
        )
        strategies['Equal Weight'] = equal_weights
        
        # 2. Momentum Strategy (Top 2 assets)
        momentum_rule = portfolio.momentum_rule(top_k=2)
        momentum_weights = portfolio.build_target_weights_from_rule(
            rule=momentum_rule,
            schedule=None,
            lookback=60
        )
        strategies['Momentum (Top-2)'] = momentum_weights
        
        # 3. Momentum Strategy (Top 3 assets)
        momentum_rule_3 = portfolio.momentum_rule(top_k=3)
        momentum_weights_3 = portfolio.build_target_weights_from_rule(
            rule=momentum_rule_3,
            schedule=None,
            lookback=60
        )
        strategies['Momentum (Top-3)'] = momentum_weights_3
        
        # 4. Tangency (Max Sharpe) Strategy - lookback 60
        tangency_rule_60 = lambda date, mu: portfolio.tangency_weights(
            lookback=60, ridge=1e-4, date=date
        )
        tangency_weights_60 = portfolio.build_target_weights_from_rule(
            rule=tangency_rule_60,
            schedule=None,
            lookback=60
        )
        strategies['Tangency (60d)'] = tangency_weights_60
        
        # 5. Tangency (Max Sharpe) Strategy - lookback 120
        tangency_rule_120 = lambda date, mu: portfolio.tangency_weights(
            lookback=120, ridge=1e-4, date=date
        )
        tangency_weights_120 = portfolio.build_target_weights_from_rule(
            rule=tangency_rule_120,
            schedule=None,
            lookback=120
        )
        strategies['Tangency (120d)'] = tangency_weights_120
        
        # 6. Target Return MVO (Low Risk) - 5% annual
        mvo_low_rule = lambda date, mu: portfolio.target_return_mvo(
            target_return=0.05/252, lookback=120, ridge=1e-4, date=date
        )
        mvo_low_weights = portfolio.build_target_weights_from_rule(
            rule=mvo_low_rule,
            schedule=None,
            lookback=120
        )
        strategies['MVO (5% target)'] = mvo_low_weights
        
        # 7. Target Return MVO (High Risk) - 15% annual
        mvo_high_rule = lambda date, mu: portfolio.target_return_mvo(
            target_return=0.15/252, lookback=120, ridge=1e-4, date=date
        )
        mvo_high_weights = portfolio.build_target_weights_from_rule(
            rule=mvo_high_rule,
            schedule=None,
            lookback=120
        )
        strategies['MVO (15% target)'] = mvo_high_weights
        
        print(f"✓ Defined {len(strategies)} strategies for comparison")
        
        # Run backtests for all strategies
        results = {}
        
        for strategy_name, target_weights in strategies.items():
            result = portfolio.rebalance(
                target_weights=target_weights,
                initial_equity=100000
            )
            results[strategy_name] = result
        
        print(f"✓ Completed backtests for all {len(strategies)} strategies")
        
        # Create comparison table
        print("\n" + "="*90)
        print("STRATEGY PERFORMANCE COMPARISON")
        print("="*90)
        print(f"{'Strategy':<25} {'Return':>10} {'Ann Ret':>10} {'Sharpe':>10} {'Sortino':>10} {'MaxDD':>10} {'Calmar':>10}")
        print("-"*90)
        
        comparison_data = []
        for strategy_name, result in results.items():
            perf = result.perf
            total_ret = ((result.equity_curve.iloc[-1] / 100000) - 1) * 100
            
            print(f"{strategy_name:<25} {total_ret:>9.2f}% {perf['ann_return']*100:>9.2f}% "
                  f"{perf['sharpe']:>10.3f} {perf['sortino']:>10.3f} "
                  f"{perf['max_drawdown']*100:>9.2f}% {perf['calmar']:>10.3f}")
            
            comparison_data.append({
                'strategy': strategy_name,
                'total_return': total_ret,
                'ann_return': perf['ann_return'] * 100,
                'sharpe': perf['sharpe'],
                'sortino': perf['sortino'],
                'max_dd': perf['max_drawdown'] * 100,
                'calmar': perf['calmar']
            })
        
        print("="*90)
        
        # Find best performers
        best_return = max(comparison_data, key=lambda x: x['total_return'])
        best_sharpe = max(comparison_data, key=lambda x: x['sharpe'])
        best_sortino = max(comparison_data, key=lambda x: x['sortino'])
        lowest_dd = min(comparison_data, key=lambda x: abs(x['max_dd']))
        
        print(f"\n🏆 Best Total Return:    {best_return['strategy']} ({best_return['total_return']:.2f}%)")
        print(f"🏆 Best Sharpe Ratio:    {best_sharpe['strategy']} ({best_sharpe['sharpe']:.3f})")
        print(f"🏆 Best Sortino Ratio:   {best_sortino['strategy']} ({best_sortino['sortino']:.3f})")
        print(f"🏆 Lowest Max Drawdown:  {lowest_dd['strategy']} ({lowest_dd['max_dd']:.2f}%)")
        
        # Create comparison visualization
        print("\nGenerating strategy comparison charts...")
        
        # 1. Equity curves comparison
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # Top-left: All equity curves
        ax1 = axes[0, 0]
        colors = plt.cm.tab10(np.linspace(0, 1, len(strategies)))
        for idx, (strategy_name, result) in enumerate(results.items()):
            equity = result.equity_curve
            ax1.plot(equity.index, equity.values, linewidth=2, 
                    label=strategy_name, color=colors[idx], alpha=0.8)
        ax1.set_title('Strategy Equity Curves', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Portfolio Value ($)', fontsize=11)
        ax1.legend(loc='best', fontsize=9)
        ax1.grid(True, alpha=0.3)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        # Top-right: Sharpe ratios
        ax2 = axes[0, 1]
        strategy_names = [d['strategy'] for d in comparison_data]
        sharpe_ratios = [d['sharpe'] for d in comparison_data]
        bars = ax2.barh(strategy_names, sharpe_ratios, color=colors, alpha=0.7)
        ax2.set_title('Sharpe Ratio Comparison', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Sharpe Ratio', fontsize=11)
        ax2.grid(True, alpha=0.3, axis='x')
        for bar, val in zip(bars, sharpe_ratios):
            ax2.text(val + 0.02, bar.get_y() + bar.get_height()/2, 
                    f'{val:.3f}', va='center', fontsize=9)
        
        # Bottom-left: Returns vs Risk
        ax3 = axes[1, 0]
        ann_returns = [d['ann_return'] for d in comparison_data]
        max_dds = [abs(d['max_dd']) for d in comparison_data]
        ax3.scatter(max_dds, ann_returns, s=200, c=colors, alpha=0.7)
        for idx, name in enumerate(strategy_names):
            ax3.annotate(name, (max_dds[idx], ann_returns[idx]), 
                        fontsize=8, ha='center', va='bottom')
        ax3.set_title('Return vs Risk', fontsize=14, fontweight='bold')
        ax3.set_xlabel('Max Drawdown (%)', fontsize=11)
        ax3.set_ylabel('Annual Return (%)', fontsize=11)
        ax3.grid(True, alpha=0.3)
        
        # Bottom-right: Total returns
        ax4 = axes[1, 1]
        total_returns = [d['total_return'] for d in comparison_data]
        bars = ax4.barh(strategy_names, total_returns, color=colors, alpha=0.7)
        ax4.set_title('Total Return Comparison', fontsize=14, fontweight='bold')
        ax4.set_xlabel('Total Return (%)', fontsize=11)
        ax4.grid(True, alpha=0.3, axis='x')
        for bar, val in zip(bars, total_returns):
            ax4.text(val + 0.05, bar.get_y() + bar.get_height()/2, 
                    f'{val:.2f}%', va='center', fontsize=9)
        
        plt.tight_layout()
        plt.savefig('visualizations/test_strategy_comparison.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ Strategy comparison chart saved: visualizations/test_strategy_comparison.png")
        
        # 2. Drawdown comparison
        fig, ax = plt.subplots(figsize=(14, 8))
        for idx, (strategy_name, result) in enumerate(results.items()):
            equity = result.equity_curve
            cumulative = equity / equity.iloc[0]
            rolling_max = cumulative.expanding().max()
            drawdown = (cumulative - rolling_max) / rolling_max
            ax.plot(drawdown.index, drawdown.values * 100, linewidth=2, 
                   label=strategy_name, color=colors[idx], alpha=0.7)
        ax.set_title('Strategy Drawdown Comparison', fontsize=14, fontweight='bold')
        ax.set_ylabel('Drawdown (%)', fontsize=11)
        ax.legend(loc='best', fontsize=9)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('visualizations/test_strategy_drawdowns.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ Drawdown comparison chart saved: visualizations/test_strategy_drawdowns.png")
        
        print(f"\n✓ Strategy comparison test completed successfully")
        print(f"  Compared {len(strategies)} strategies over {len(prices)} periods")
        print(f"  Data range: {prices.index[0].date()} to {prices.index[-1].date()}")
        
        return True
        
    except Exception as e:
        print(f"✗ Strategy comparison test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests(include_visualizations=True):
    """Run all integration tests.
    
    Args:
        include_visualizations: Whether to generate visualization tests (default: True)
    """
    print("Starting Portfolio Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Portfolio Class", test_portfolio_class),
        ("Configuration Adapter", test_configuration_adapter),
        ("Forecast Adapter", test_forecast_manager),
        ("Signal Adapter", test_signal_manager),
        ("Backtester Adapter", test_backtester),
        ("End-to-End Pipeline", test_end_to_end_pipeline),
        ("Strategy Comparison", test_strategy_comparison)
    ]
    
    # Add visualization test if requested
    if include_visualizations:
        tests.append(("Visualization Generation", test_visualizations))
    
    results = []
    for test_name, test_func in tests:
        print(f"\nRunning {test_name} test...")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
            import traceback
            traceback.print_exc()
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
    
    if include_visualizations and passed == total:
        print("\n📊 Visualization files generated in visualizations/ folder:")
        print("  • test_equity_curve.png")
        print("  • test_portfolio_weights.png")
        print("  • test_drawdown.png")
        print("  • test_returns_distribution.png")
        print("  • test_performance_summary.png")
        print("  • test_strategy_comparison.png")
        print("  • test_strategy_drawdowns.png")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Portfolio integration is ready to use.")
        return True
    else:
        print(f"\n⚠️  {total - passed} tests failed. Please review and fix issues.")
        return False


if __name__ == "__main__":
    # Check for command line argument to skip visualizations
    import argparse
    parser = argparse.ArgumentParser(description='Run portfolio integration tests')
    parser.add_argument('--no-viz', action='store_true', 
                       help='Skip visualization generation')
    args = parser.parse_args()
    
    success = run_all_tests(include_visualizations=not args.no_viz)
    sys.exit(0 if success else 1)
