"""
Portfolio Visualization Dashboard

This script creates comprehensive visualizations for portfolio analysis including:
- Performance metrics and equity curves
- Portfolio weight allocations over time
- Risk analytics (drawdowns, volatility)
- Rolling performance metrics
- Correlation analysis
- Signal strength visualization

Usage:
    python visualize_portfolio.py
"""

import sys
import os
import warnings
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import portfolio modules
from src.portfolio import Portfolio, PortfolioResult
from src.portfolio_manager import (
    PortfolioBacktester, ForecastManager, 
    ConfigManager
)
from src.utils import TradingConfig, setup_logging

# Suppress warnings
warnings.filterwarnings('ignore')

# Configure plotting style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Set up logging
setup_logging(level='INFO')


def create_sample_data(n_periods=500, n_assets=5):
    """Create sample data for visualization demo."""
    print(f"Creating sample data: {n_periods} periods, {n_assets} assets...")
    
    dates = pd.date_range(start='2020-01-01', periods=n_periods, freq='D')
    assets = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'SPY'][:n_assets]
    
    # Generate correlated returns with drift
    np.random.seed(42)
    mean_returns = np.array([0.0008, 0.0007, 0.0006, 0.0009, 0.0005])[:n_assets]
    cov_matrix = np.array([
        [0.0004, 0.0001, 0.0002, 0.0001, 0.0002],
        [0.0001, 0.0003, 0.0001, 0.0002, 0.0001],
        [0.0002, 0.0001, 0.0005, 0.0002, 0.0002],
        [0.0001, 0.0002, 0.0002, 0.0006, 0.0001],
        [0.0002, 0.0001, 0.0002, 0.0001, 0.0003]
    ])[:n_assets, :n_assets]
    
    returns = np.random.multivariate_normal(mean_returns, cov_matrix, size=n_periods)
    
    # Create prices from returns
    prices = pd.DataFrame(index=dates, columns=assets)
    prices.iloc[0] = [100.0] * n_assets
    
    for i in range(1, n_periods):
        prices.iloc[i] = prices.iloc[i-1] * (1 + returns[i])
    
    # Create signals (momentum-based)
    returns_df = pd.DataFrame(returns, index=dates, columns=assets)
    signals = returns_df.rolling(window=20).mean() * 5
    
    print(f"✓ Sample data created")
    return prices, signals, returns_df


def plot_equity_curves(portfolio_result, benchmark_prices=None, save_path='visualizations/equity_curves.png'):
    """Plot portfolio equity curve with benchmark comparison."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    
    # Equity curve
    equity = portfolio_result.equity_curve
    ax1.plot(equity.index, equity.values, linewidth=2, label='Portfolio', color='#2E86AB')
    
    if benchmark_prices is not None:
        benchmark_nav = (benchmark_prices.iloc[:, 0] / benchmark_prices.iloc[0, 0]) * 100000
        ax1.plot(benchmark_nav.index, benchmark_nav.values, 
                linewidth=1.5, label='Benchmark (SPY)', color='#A23B72', alpha=0.7)
    
    ax1.set_title('Portfolio Equity Curve', fontsize=16, fontweight='bold', pad=20)
    ax1.set_ylabel('Portfolio Value ($)', fontsize=12)
    ax1.legend(loc='upper left', fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    
    # Performance metrics text
    perf = portfolio_result.perf
    metrics_text = (f"Annual Return: {perf['ann_return']:.2%}\n"
                   f"Sharpe Ratio: {perf['sharpe']:.3f}\n"
                   f"Max Drawdown: {perf['max_drawdown']:.2%}\n"
                   f"Calmar Ratio: {perf['calmar']:.3f}")
    ax1.text(0.02, 0.95, metrics_text, transform=ax1.transAxes,
            fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # Returns distribution
    returns = equity.pct_change().dropna()
    ax2.hist(returns, bins=50, alpha=0.7, color='#2E86AB', edgecolor='black')
    ax2.axvline(returns.mean(), color='red', linestyle='--', 
               linewidth=2, label=f'Mean: {returns.mean():.4f}')
    ax2.axvline(returns.median(), color='green', linestyle='--', 
               linewidth=2, label=f'Median: {returns.median():.4f}')
    
    ax2.set_title('Daily Returns Distribution', fontsize=14, fontweight='bold', pad=15)
    ax2.set_xlabel('Daily Return', fontsize=12)
    ax2.set_ylabel('Frequency', fontsize=12)
    ax2.legend(loc='upper right', fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved equity curves to {save_path}")
    plt.show()


def plot_portfolio_weights(weights_df, save_path='visualizations/portfolio_weights.png'):
    """Plot portfolio weights allocation over time."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    
    # Remove cash column if present
    weights_plot = weights_df.drop(columns=['CASH'], errors='ignore')
    
    # Check if we have any data
    if weights_plot.empty or len(weights_plot) == 0:
        ax1.text(0.5, 0.5, 'No weight data available', 
                ha='center', va='center', fontsize=14)
        ax2.text(0.5, 0.5, 'No weight data available', 
                ha='center', va='center', fontsize=14)
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✓ Saved portfolio weights to {save_path}")
        plt.show()
        return
    
    # Ensure numeric data
    weights_plot = weights_plot.select_dtypes(include=[np.number])
    
    # Stacked area chart
    if len(weights_plot.columns) <= 10 and len(weights_plot) > 0:
        weights_plot.plot(kind='area', stacked=True, ax=ax1, alpha=0.7)
        ax1.set_title('Portfolio Weight Allocation Over Time', 
                     fontsize=16, fontweight='bold', pad=20)
        ax1.set_ylabel('Weight', fontsize=12)
        ax1.set_ylim([0, 1])
        ax1.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize=10)
        ax1.grid(True, alpha=0.3)
    else:
        # Too many assets, show concentration
        total_weights = weights_plot.sum(axis=1)
        ax1.plot(total_weights.index, total_weights.values, linewidth=2, color='#2E86AB')
        ax1.set_title('Total Portfolio Exposure', fontsize=16, fontweight='bold', pad=20)
        ax1.set_ylabel('Total Weight', fontsize=12)
        ax1.grid(True, alpha=0.3)
    
    # Average weights (bar chart)
    avg_weights = weights_plot.mean().sort_values(ascending=False)
    colors = sns.color_palette("husl", len(avg_weights))
    ax2.bar(range(len(avg_weights)), avg_weights.values, color=colors, edgecolor='black')
    ax2.set_xticks(range(len(avg_weights)))
    ax2.set_xticklabels(avg_weights.index, rotation=45, ha='right')
    ax2.set_title('Average Portfolio Weights', fontsize=14, fontweight='bold', pad=15)
    ax2.set_ylabel('Average Weight', fontsize=12)
    ax2.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for i, v in enumerate(avg_weights.values):
        ax2.text(i, v + 0.01, f'{v:.2%}', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved portfolio weights to {save_path}")
    plt.show()


def plot_risk_metrics(portfolio_result, save_path='visualizations/risk_metrics.png'):
    """Plot risk analytics including drawdowns and volatility."""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    equity = portfolio_result.equity_curve
    returns = equity.pct_change().dropna()
    
    # 1. Drawdown
    cumulative = equity / equity.iloc[0]
    rolling_max = cumulative.expanding().max()
    drawdown = (cumulative - rolling_max) / rolling_max
    
    ax1.fill_between(drawdown.index, drawdown.values, 0, 
                     alpha=0.7, color='red', label='Drawdown')
    ax1.plot(drawdown.index, drawdown.values, linewidth=1, color='darkred')
    ax1.set_title('Portfolio Drawdown', fontsize=14, fontweight='bold', pad=15)
    ax1.set_ylabel('Drawdown', fontsize=12)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))
    ax1.legend(loc='lower left', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # Add max drawdown line
    max_dd = drawdown.min()
    ax1.axhline(max_dd, color='darkred', linestyle='--', 
               linewidth=2, label=f'Max DD: {max_dd:.2%}')
    
    # 2. Rolling Volatility
    rolling_vol = returns.rolling(window=30).std() * np.sqrt(252)
    ax2.plot(rolling_vol.index, rolling_vol.values, linewidth=2, color='#F18F01')
    ax2.axhline(rolling_vol.mean(), color='blue', linestyle='--', 
               linewidth=2, label=f'Mean: {rolling_vol.mean():.2%}')
    ax2.set_title('Rolling 30-Day Volatility (Annualized)', 
                 fontsize=14, fontweight='bold', pad=15)
    ax2.set_ylabel('Volatility', fontsize=12)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))
    ax2.legend(loc='upper right', fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    # 3. Rolling Sharpe Ratio
    rolling_sharpe = (returns.rolling(window=60).mean() / 
                     returns.rolling(window=60).std() * np.sqrt(252))
    ax3.plot(rolling_sharpe.index, rolling_sharpe.values, linewidth=2, color='#06A77D')
    ax3.axhline(0, color='black', linestyle='-', linewidth=1, alpha=0.5)
    ax3.axhline(rolling_sharpe.mean(), color='red', linestyle='--', 
               linewidth=2, label=f'Mean: {rolling_sharpe.mean():.2f}')
    ax3.set_title('Rolling 60-Day Sharpe Ratio', fontsize=14, fontweight='bold', pad=15)
    ax3.set_ylabel('Sharpe Ratio', fontsize=12)
    ax3.legend(loc='upper right', fontsize=10)
    ax3.grid(True, alpha=0.3)
    
    # 4. Cumulative Returns
    cumulative_returns = (1 + returns).cumprod() - 1
    ax4.plot(cumulative_returns.index, cumulative_returns.values, 
            linewidth=2, color='#2E86AB')
    ax4.fill_between(cumulative_returns.index, 0, cumulative_returns.values, 
                     alpha=0.3, color='#2E86AB')
    ax4.set_title('Cumulative Returns', fontsize=14, fontweight='bold', pad=15)
    ax4.set_ylabel('Cumulative Return', fontsize=12)
    ax4.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved risk metrics to {save_path}")
    plt.show()


def plot_trading_activity(trades_df, save_path='visualizations/trading_activity.png'):
    """Plot trading activity and turnover."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    
    # Remove cash column
    trades_plot = trades_df.drop(columns=['CASH'], errors='ignore')
    
    # Daily turnover
    daily_turnover = trades_plot.abs().sum(axis=1)
    ax1.plot(daily_turnover.index, daily_turnover.values, linewidth=1, color='#2E86AB')
    ax1.fill_between(daily_turnover.index, 0, daily_turnover.values, 
                     alpha=0.5, color='#2E86AB')
    ax1.set_title('Daily Portfolio Turnover', fontsize=16, fontweight='bold', pad=20)
    ax1.set_ylabel('Turnover', fontsize=12)
    ax1.grid(True, alpha=0.3)
    
    # Cumulative trades
    cumulative_trades = trades_plot.abs().cumsum()
    if len(cumulative_trades.columns) <= 8:
        for col in cumulative_trades.columns:
            ax2.plot(cumulative_trades.index, cumulative_trades[col], 
                    linewidth=2, label=col, alpha=0.8)
        ax2.legend(loc='upper left', fontsize=10)
    else:
        total_cumulative = cumulative_trades.sum(axis=1)
        ax2.plot(total_cumulative.index, total_cumulative.values, 
                linewidth=2, color='#2E86AB')
    
    ax2.set_title('Cumulative Trading Activity', fontsize=14, fontweight='bold', pad=15)
    ax2.set_ylabel('Cumulative Trades', fontsize=12)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved trading activity to {save_path}")
    plt.show()


def plot_correlation_analysis(prices_df, save_path='visualizations/correlation_analysis.png'):
    """Plot correlation matrix and rolling correlations."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Calculate returns for correlation
    returns = prices_df.pct_change().dropna()
    
    # Correlation matrix heatmap
    corr_matrix = returns.corr()
    sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm', 
                center=0, square=True, ax=ax1, cbar_kws={'shrink': 0.8})
    ax1.set_title('Asset Correlation Matrix', fontsize=14, fontweight='bold', pad=15)
    
    # Rolling correlation (if we have at least 2 assets)
    if len(returns.columns) >= 2:
        asset1, asset2 = returns.columns[0], returns.columns[1]
        rolling_corr = returns[asset1].rolling(window=60).corr(returns[asset2])
        ax2.plot(rolling_corr.index, rolling_corr.values, linewidth=2, color='#2E86AB')
        ax2.axhline(rolling_corr.mean(), color='red', linestyle='--', 
                   linewidth=2, label=f'Mean: {rolling_corr.mean():.3f}')
        ax2.set_title(f'Rolling 60-Day Correlation\n{asset1} vs {asset2}', 
                     fontsize=14, fontweight='bold', pad=15)
        ax2.set_ylabel('Correlation', fontsize=12)
        ax2.set_ylim([-1, 1])
        ax2.legend(loc='upper right', fontsize=10)
        ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved correlation analysis to {save_path}")
    plt.show()


def plot_monthly_returns_heatmap(portfolio_result, save_path='visualizations/monthly_returns.png'):
    """Plot monthly returns heatmap."""
    equity = portfolio_result.equity_curve
    returns = equity.pct_change().dropna()
    
    # Resample to monthly returns
    monthly_returns = returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
    
    # Create year-month pivot table
    monthly_returns_df = pd.DataFrame({
        'Year': monthly_returns.index.year,
        'Month': monthly_returns.index.month,
        'Return': monthly_returns.values
    })
    
    pivot_table = monthly_returns_df.pivot(index='Year', columns='Month', values='Return')
    
    fig, ax = plt.subplots(figsize=(14, 8))
    sns.heatmap(pivot_table * 100, annot=True, fmt='.2f', cmap='RdYlGn', 
                center=0, ax=ax, cbar_kws={'label': 'Return (%)'})
    ax.set_title('Monthly Returns Heatmap (%)', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Month', fontsize=12)
    ax.set_ylabel('Year', fontsize=12)
    
    # Set month labels
    month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    ax.set_xticklabels(month_labels)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved monthly returns heatmap to {save_path}")
    plt.show()


def create_comprehensive_dashboard():
    """Create comprehensive portfolio visualization dashboard."""
    print("="*60)
    print("PORTFOLIO VISUALIZATION DASHBOARD")
    print("="*60)
    
    # Create sample data
    prices, signals, returns = create_sample_data(n_periods=500, n_assets=5)
    
    # Initialize Portfolio
    print("\nInitializing Portfolio...")
    portfolio = Portfolio(
        prices=prices,
        rf=0.02/252,
        trading_cost_bps=10.0,
        slippage_bps=2.0
    )
    
    # Create signal-based strategy
    print("Generating portfolio weights...")
    signal_rule = portfolio.integrate_with_signals(signals, signal_threshold=0.0)
    target_weights = portfolio.build_target_weights_from_rule(
        rule=signal_rule,
        schedule='W',  # Weekly rebalancing
        lookback=60
    )
    
    # If no weights generated, use simple equal weight with specific dates
    if target_weights.empty or len(target_weights) == 0:
        print("Creating simple rebalancing strategy...")
        rebalance_dates = prices.index[::20]  # Every 20 days
        n_assets = len(prices.columns)
        target_weights = pd.DataFrame(
            1.0 / n_assets,
            index=rebalance_dates,
            columns=prices.columns
        )
    
    # Run backtest
    print("Running backtest...")
    result = portfolio.rebalance(
        target_weights=target_weights,
        initial_equity=100000
    )
    
    print("\n" + "="*60)
    print("PORTFOLIO PERFORMANCE SUMMARY")
    print("="*60)
    print(f"Initial Equity:    ${100000:,.2f}")
    print(f"Final Equity:      ${result.equity_curve.iloc[-1]:,.2f}")
    print(f"Total Return:      {((result.equity_curve.iloc[-1]/100000)-1)*100:.2f}%")
    print(f"Annual Return:     {result.perf['ann_return']*100:.2f}%")
    print(f"Annual Volatility: {result.perf['ann_vol']*100:.2f}%")
    print(f"Sharpe Ratio:      {result.perf['sharpe']:.3f}")
    print(f"Sortino Ratio:     {result.perf['sortino']:.3f}")
    print(f"Max Drawdown:      {result.perf['max_drawdown']*100:.2f}%")
    print(f"Calmar Ratio:      {result.perf['calmar']:.3f}")
    print(f"CAGR:              {result.perf['cagr']*100:.2f}%")
    print("="*60)
    
    # Create visualizations
    print("\nGenerating visualizations...")
    print("-" * 60)
    
    plot_equity_curves(result, benchmark_prices=prices[['SPY']])
    plot_portfolio_weights(result.weights)
    plot_risk_metrics(result)
    plot_trading_activity(result.trades)
    plot_correlation_analysis(prices)
    plot_monthly_returns_heatmap(result)
    
    print("\n" + "="*60)
    print("✓ ALL VISUALIZATIONS COMPLETED!")
    print("="*60)
    print("\nGenerated files:")
    print("  • equity_curves.png - Portfolio performance vs benchmark")
    print("  • portfolio_weights.png - Weight allocation over time")
    print("  • risk_metrics.png - Drawdown, volatility, and risk analysis")
    print("  • trading_activity.png - Trading turnover and activity")
    print("  • correlation_analysis.png - Asset correlation matrix")
    print("  • monthly_returns.png - Monthly returns heatmap")
    print("\n" + "="*60)


if __name__ == "__main__":
    create_comprehensive_dashboard()
