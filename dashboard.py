"""
Interactive Portfolio Dashboard - Streamlit Application
========================================================

Comprehensive visualization dashboard for algo-trading backtesting results.

Features:
- Strategy comparison charts
- Performance metrics table
- Cumulative returns and drawdown plots
- Rolling Sharpe ratio and volatility
- Correlation heatmaps
- Weight evolution over time
- Transaction costs analysis

Run with: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.data_loader import load_data
from src.portfolio_engine import PortfolioEngine
from src.strategy import Strategy
from src.optimizer import PortfolioOptimizer
from src.strategy_wrapper import (
    EqualWeightStrategy, BuyAndHoldStrategy, MomentumStrategy,
    MeanReversionStrategy, InverseVolatilityStrategy,
    GlobalMinimumVarianceStrategy, CVaRMinimizationStrategy,
    MaximumDiversificationStrategy, MaximumDecorrelationStrategy,
    QuintileFactorStrategy, TimeSeriesMomentumStrategy,
    MovingAverageCrossoverStrategy, MarkowitzMVOStrategy,
    LinearRegressionStrategy
)

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Algo Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .reportview-container {
        background: #f0f2f6;
    }
    .main .block-container {
        padding-top: 2rem;
    }
    h1 {
        color: #1f77b4;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 10px;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SIDEBAR CONFIGURATION
# ============================================================================

st.sidebar.title("⚙️ Dashboard Configuration")
st.sidebar.markdown("---")

# Data configuration
st.sidebar.subheader("📊 Data Settings")
default_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'JPM']
tickers_input = st.sidebar.text_input(
    "Tickers (comma-separated)",
    value=",".join(default_tickers)
)
tickers = [t.strip().upper() for t in tickers_input.split(",")]

start_date = st.sidebar.date_input(
    "Start Date",
    value=pd.to_datetime('2020-01-01')
)
end_date = st.sidebar.date_input(
    "End Date",
    value=pd.to_datetime('2023-12-31')
)

# Backtest configuration
st.sidebar.subheader("🔧 Backtest Settings")
initial_capital = st.sidebar.number_input(
    "Initial Capital ($)",
    min_value=10000,
    max_value=10000000,
    value=100000,
    step=10000
)

rebalance_freq = st.sidebar.selectbox(
    "Rebalance Frequency",
    options=['D', 'W', 'M', 'Q'],
    index=2,
    help="D=Daily, W=Weekly, M=Monthly, Q=Quarterly"
)

transaction_cost_bps = st.sidebar.slider(
    "Transaction Costs (bps)",
    min_value=0.0,
    max_value=50.0,
    value=10.0,
    step=1.0
)

# Strategy selection
st.sidebar.subheader("📈 Strategy Selection")
all_strategies = {
    'Equal Weight': True,
    'Buy & Hold': False,
    'Momentum': True,
    'Mean Reversion': False,
    'Inverse Volatility': True,
    'GMVP': True,
    'CVaR Minimization': True,
    'Max Diversification': False,
    'Max Decorrelation': False,
    'Time-Series Momentum': False,
    'MA Crossover': False,
    'Markowitz MVO': True,
    'Linear Regression': False,
    'ML Random Forest': False,
    'ML Gradient Boosting': False,
    'ARMA Forecast': False,
    'Multi-Factor ML': False,
    'GMRP': False,
    'Quintile Factor': False
}

selected_strategies = {}
for strat_name, default_val in all_strategies.items():
    selected_strategies[strat_name] = st.sidebar.checkbox(
        strat_name,
        value=default_val
    )

# ============================================================================
# CACHING DATA AND BACKTESTS
# ============================================================================

@st.cache_data
def load_market_data(tickers, start, end):
    """Load and cache market data."""
    try:
        full_data, prices = load_data(tickers, str(start), str(end))
        return prices
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

@st.cache_data
def run_backtest_cached(
    prices_df,
    strategy_name,
    initial_cap,
    rebal_freq,
    tc_bps
):
    """Run and cache backtest for a strategy."""
    try:
        # Convert prices_df back to DataFrame
        prices = pd.DataFrame(prices_df)
        
        # Create strategy and optimizer
        strategy = Strategy(prices)
        optimizer = PortfolioOptimizer()
        
        # Create strategy wrapper
        if strategy_name == 'Equal Weight':
            wrapper = EqualWeightStrategy(strategy, optimizer)
        elif strategy_name == 'Buy & Hold':
            wrapper = BuyAndHoldStrategy(strategy, optimizer)
        elif strategy_name == 'Momentum':
            wrapper = MomentumStrategy(strategy, optimizer, top_k=4, lookback=126)
        elif strategy_name == 'Mean Reversion':
            wrapper = MeanReversionStrategy(strategy, optimizer, window=21, top_k=4)
        elif strategy_name == 'Inverse Volatility':
            wrapper = InverseVolatilityStrategy(strategy, optimizer, vol_window=63)
        elif strategy_name == 'GMVP':
            wrapper = GlobalMinimumVarianceStrategy(strategy, optimizer, lookback=252)
        elif strategy_name == 'CVaR Minimization':
            wrapper = CVaRMinimizationStrategy(strategy, optimizer, alpha=0.95)
        elif strategy_name == 'Max Diversification':
            wrapper = MaximumDiversificationStrategy(strategy, optimizer, lookback=252)
        elif strategy_name == 'Max Decorrelation':
            wrapper = MaximumDecorrelationStrategy(strategy, optimizer, lookback=252)
        elif strategy_name == 'Time-Series Momentum':
            wrapper = TimeSeriesMomentumStrategy(strategy, optimizer, lookback=126)
        elif strategy_name == 'MA Crossover':
            wrapper = MovingAverageCrossoverStrategy(strategy, optimizer, fast_window=50, slow_window=200)
        elif strategy_name == 'Markowitz MVO':
            wrapper = MarkowitzMVOStrategy(strategy, optimizer, lookback=252, risk_aversion=1.0)
        elif strategy_name == 'Linear Regression':
            wrapper = LinearRegressionStrategy(strategy, optimizer, lookback=252)
        elif strategy_name == 'ML Random Forest':
            wrapper = MLRandomForestStrategy(strategy, optimizer, lookback=252, top_k=4)
        elif strategy_name == 'ML Gradient Boosting':
            wrapper = MLGradientBoostingStrategy(strategy, optimizer, lookback=252, top_k=4)
        elif strategy_name == 'ARMA Forecast':
            wrapper = ARMAForecastStrategy(strategy, optimizer, arma_order=(2,1), top_k=4)
        elif strategy_name == 'Multi-Factor ML':
            wrapper = MultiFactorMLStrategy(strategy, optimizer, lookback=252, top_k=4)
        elif strategy_name == 'GMRP':
            wrapper = GMRPStrategy(strategy, optimizer, lookback=126)
        elif strategy_name == 'Quintile Factor':
            wrapper = QuintileFactorStrategy(strategy, optimizer, factor='momentum')
        else:
            return None
        
        # Run backtest
        engine = PortfolioEngine(
            prices=prices,
            initial_capital=initial_cap,
            transaction_cost_bps=tc_bps,
            slippage_bps=0.0
        )
        
        result = engine.run_backtest(
            strategy_wrapper=wrapper,
            rebalance_freq=rebal_freq,
            start_date=str(prices.index[0].date()),
            end_date=str(prices.index[-1].date())
        )
        
        return result
        
    except Exception as e:
        st.warning(f"Strategy {strategy_name} failed: {e}")
        return None

# ============================================================================
# MAIN DASHBOARD
# ============================================================================

st.title("📈 Algorithmic Trading Portfolio Dashboard")
st.markdown("**Comprehensive Backtesting and Performance Analysis**")
st.markdown("---")

# Run button
if st.sidebar.button("▶️ Run Backtest", type="primary"):
    st.session_state.run_backtest = True
else:
    if 'run_backtest' not in st.session_state:
        st.session_state.run_backtest = False

if st.session_state.run_backtest:
    # Load data
    with st.spinner("📥 Loading market data..."):
        prices = load_market_data(tickers, start_date, end_date)
    
    if prices is None or prices.empty:
        st.error("Failed to load data. Please check tickers and date range.")
        st.stop()
    
    st.success(f"✅ Loaded {len(prices)} days of data for {len(tickers)} assets")
    
    # Run backtests
    strategies_to_run = [k for k, v in selected_strategies.items() if v]
    
    if not strategies_to_run:
        st.warning("⚠️ Please select at least one strategy")
        st.stop()
    
    st.markdown(f"### Running {len(strategies_to_run)} strategies...")
    
    results = {}
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, strat_name in enumerate(strategies_to_run):
        status_text.text(f"Running {strat_name}...")
        
        result = run_backtest_cached(
            prices.copy(),
            strat_name,
            initial_capital,
            rebalance_freq,
            transaction_cost_bps
        )
        
        if result is not None:
            results[strat_name] = result
        
        progress_bar.progress((idx + 1) / len(strategies_to_run))
    
    status_text.text("✅ All backtests complete!")
    progress_bar.empty()
    status_text.empty()
    
    if not results:
        st.error("❌ No strategies completed successfully")
        st.stop()
    
    # ========================================================================
    # METRICS DASHBOARD
    # ========================================================================
    
    st.markdown("## 📊 Performance Metrics")
    
    # Build metrics DataFrame
    metrics_data = []
    for name, result in results.items():
        metrics = result.summary_metrics.copy()
        metrics['Strategy'] = name
        metrics_data.append(metrics)
    
    metrics_df = pd.DataFrame(metrics_data).set_index('Strategy')
    
    # Display key metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    best_sharpe_strat = metrics_df['sharpe_ratio'].idxmax()
    best_return_strat = metrics_df['total_return'].idxmax()
    best_dd_strat = metrics_df['max_drawdown'].idxmax()  # Least negative = best
    
    with col1:
        st.metric("Best Sharpe", best_sharpe_strat, 
                 f"{metrics_df.loc[best_sharpe_strat, 'sharpe_ratio']:.2f}")
    with col2:
        st.metric("Best Return", best_return_strat,
                 f"{metrics_df.loc[best_return_strat, 'total_return']*100:.1f}%")
    with col3:
        st.metric("Best DD", best_dd_strat,
                 f"{metrics_df.loc[best_dd_strat, 'max_drawdown']*100:.1f}%")
    with col4:
        avg_sharpe = metrics_df['sharpe_ratio'].mean()
        st.metric("Avg Sharpe", f"{avg_sharpe:.2f}")
    with col5:
        avg_return = metrics_df['total_return'].mean()
        st.metric("Avg Return", f"{avg_return*100:.1f}%")
    
    # Full metrics table
    st.markdown("### 📋 Detailed Metrics")
    display_df = metrics_df[[
        'total_return', 'annual_return', 'annual_volatility',
        'sharpe_ratio', 'max_drawdown', 'calmar_ratio'
    ]].copy()
    
    display_df.columns = ['Total Return', 'Annual Return', 'Volatility',
                         'Sharpe', 'Max DD', 'Calmar']
    display_df['Total Return'] = display_df['Total Return'].apply(lambda x: f"{x*100:.2f}%")
    display_df['Annual Return'] = display_df['Annual Return'].apply(lambda x: f"{x*100:.2f}%")
    display_df['Volatility'] = display_df['Volatility'].apply(lambda x: f"{x*100:.2f}%")
    display_df['Sharpe'] = display_df['Sharpe'].apply(lambda x: f"{x:.3f}")
    display_df['Max DD'] = display_df['Max DD'].apply(lambda x: f"{x*100:.2f}%")
    display_df['Calmar'] = display_df['Calmar'].apply(lambda x: f"{x:.3f}")
    
    st.dataframe(display_df, use_container_width=True)
    
    # ========================================================================
    # VISUALIZATION SECTION
    # ========================================================================
    
    st.markdown("## 📈 Performance Visualizations")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Equity Curves", "Returns & Drawdown", "Risk Analysis",
        "Weights & Turnover", "Comparisons"
    ])
    
    # TAB 1: Equity Curves
    with tab1:
        st.markdown("### Cumulative Portfolio Value")
        
        fig = go.Figure()
        for name, result in results.items():
            fig.add_trace(go.Scatter(
                x=result.equity_curve.index,
                y=result.equity_curve.values,
                name=name,
                mode='lines',
                line=dict(width=2)
            ))
        
        fig.update_layout(
            title="Equity Curves - All Strategies",
            xaxis_title="Date",
            yaxis_title="Portfolio Value ($)",
            hovermode='x unified',
            height=600,
            template='plotly_white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # TAB 2: Returns & Drawdown
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Cumulative Returns (%)")
            fig_ret = go.Figure()
            for name, result in results.items():
                cum_ret = (result.equity_curve / initial_capital - 1) * 100
                fig_ret.add_trace(go.Scatter(
                    x=cum_ret.index,
                    y=cum_ret.values,
                    name=name,
                    mode='lines'
                ))
            
            fig_ret.update_layout(
                xaxis_title="Date",
                yaxis_title="Cumulative Return (%)",
                hovermode='x unified',
                height=400,
                template='plotly_white'
            )
            st.plotly_chart(fig_ret, use_container_width=True)
        
        with col2:
            st.markdown("### Drawdown (%)")
            fig_dd = go.Figure()
            for name, result in results.items():
                dd = result.drawdown_series * 100
                fig_dd.add_trace(go.Scatter(
                    x=dd.index,
                    y=dd.values,
                    name=name,
                    mode='lines',
                    fill='tozeroy'
                ))
            
            fig_dd.update_layout(
                xaxis_title="Date",
                yaxis_title="Drawdown (%)",
                hovermode='x unified',
                height=400,
                template='plotly_white'
            )
            st.plotly_chart(fig_dd, use_container_width=True)
    
    # TAB 3: Risk Analysis
    with tab3:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Risk-Return Scatter")
            scatter_data = []
            for name in results.keys():
                scatter_data.append({
                    'Strategy': name,
                    'Volatility': metrics_df.loc[name, 'annual_volatility'] * 100,
                    'Return': metrics_df.loc[name, 'annual_return'] * 100,
                    'Sharpe': metrics_df.loc[name, 'sharpe_ratio']
                })
            
            scatter_df = pd.DataFrame(scatter_data)
            fig_scatter = px.scatter(
                scatter_df,
                x='Volatility',
                y='Return',
                text='Strategy',
                size='Sharpe',
                color='Sharpe',
                color_continuous_scale='RdYlGn',
                title="Risk-Return Profile"
            )
            fig_scatter.update_traces(textposition='top center')
            fig_scatter.update_layout(height=500, template='plotly_white')
            st.plotly_chart(fig_scatter, use_container_width=True)
        
        with col2:
            st.markdown("### Sharpe Ratio Comparison")
            sharpe_data = metrics_df['sharpe_ratio'].sort_values()
            fig_sharpe = go.Figure(go.Bar(
                x=sharpe_data.values,
                y=sharpe_data.index,
                orientation='h',
                marker=dict(
                    color=sharpe_data.values,
                    colorscale='RdYlGn',
                    showscale=True
                )
            ))
            fig_sharpe.update_layout(
                title="Sharpe Ratio by Strategy",
                xaxis_title="Sharpe Ratio",
                yaxis_title="Strategy",
                height=500,
                template='plotly_white'
            )
            st.plotly_chart(fig_sharpe, use_container_width=True)
    
    # TAB 4: Weights & Turnover
    with tab4:
        # Select strategy to view weights
        selected_for_weights = st.selectbox(
            "Select strategy to view weights:",
            list(results.keys())
        )
        
        if selected_for_weights:
            result = results[selected_for_weights]
            
            st.markdown(f"### Portfolio Weights - {selected_for_weights}")
            
            # Prepare weights data (sample last 100 days)
            weights_df = result.weights_history.iloc[-min(100, len(result.weights_history)):]
            
            if 'CASH' in weights_df.columns:
                weights_df = weights_df.drop('CASH', axis=1)
            
            fig_weights = go.Figure()
            for col in weights_df.columns:
                fig_weights.add_trace(go.Scatter(
                    x=weights_df.index,
                    y=weights_df[col],
                    name=col,
                    mode='lines',
                    stackgroup='one',
                    fillcolor=None
                ))
            
            fig_weights.update_layout(
                title=f"Weight Evolution (Last {len(weights_df)} Days)",
                xaxis_title="Date",
                yaxis_title="Weight",
                hovermode='x unified',
                height=500,
                template='plotly_white'
            )
            st.plotly_chart(fig_weights, use_container_width=True)
            
            # Turnover
            st.markdown("### Turnover Analysis")
            turnover = result.turnover_history
            fig_turnover = go.Figure()
            fig_turnover.add_trace(go.Scatter(
                x=turnover.index,
                y=turnover.values * 100,
                mode='lines',
                fill='tozeroy',
                name='Turnover'
            ))
            fig_turnover.update_layout(
                title="Daily Turnover (%)",
                xaxis_title="Date",
                yaxis_title="Turnover (%)",
                height=400,
                template='plotly_white'
            )
            st.plotly_chart(fig_turnover, use_container_width=True)
    
    # TAB 5: Comparisons
    with tab5:
        st.markdown("### Strategy Comparison Heatmap")
        
        # Correlation of returns
        returns_matrix = pd.DataFrame({
            name: result.returns_series
            for name, result in results.items()
        })
        
        corr_matrix = returns_matrix.corr()
        
        fig_heatmap = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.index,
            colorscale='RdBu',
            zmid=0,
            text=corr_matrix.values,
            texttemplate='%{text:.2f}',
            textfont={"size": 10},
            colorbar=dict(title="Correlation")
        ))
        
        fig_heatmap.update_layout(
            title="Return Correlation Matrix",
            height=600,
            template='plotly_white'
        )
        
        st.plotly_chart(fig_heatmap, use_container_width=True)
        
        # Distribution comparison
        st.markdown("### Daily Returns Distribution")
        fig_dist = go.Figure()
        for name in results.keys():
            returns = results[name].returns_series * 100
            fig_dist.add_trace(go.Histogram(
                x=returns,
                name=name,
                opacity=0.7,
                nbinsx=50
            ))
        
        fig_dist.update_layout(
            title="Distribution of Daily Returns",
            xaxis_title="Daily Return (%)",
            yaxis_title="Frequency",
            barmode='overlay',
            height=500,
            template='plotly_white'
        )
        st.plotly_chart(fig_dist, use_container_width=True)
    
    # ========================================================================
    # DOWNLOAD RESULTS
    # ========================================================================
    
    st.markdown("## 💾 Export Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Export metrics
        csv_metrics = metrics_df.to_csv()
        st.download_button(
            label="📥 Download Metrics (CSV)",
            data=csv_metrics,
            file_name=f"backtest_metrics_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    with col2:
        # Export equity curves
        equity_df = pd.DataFrame({
            name: result.equity_curve
            for name, result in results.items()
        })
        csv_equity = equity_df.to_csv()
        st.download_button(
            label="📥 Download Equity Curves (CSV)",
            data=csv_equity,
            file_name=f"equity_curves_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

else:
    st.info("👈 Configure settings in the sidebar and click '▶️ Run Backtest' to start")
    st.markdown("""
    ### 🚀 Quick Start Guide
    
    1. **Select Tickers**: Enter comma-separated ticker symbols (e.g., AAPL,MSFT,GOOGL)
    2. **Set Date Range**: Choose start and end dates for backtesting
    3. **Configure Backtest**: Set initial capital, rebalance frequency, and transaction costs
    4. **Choose Strategies**: Select which strategies to compare
    5. **Run**: Click the "Run Backtest" button to start analysis
    
    ### 📊 Available Strategies
    
    - **Basic**: Equal Weight, Buy & Hold
    - **Factor-Based**: Momentum, Mean Reversion, Inverse Volatility
    - **Risk-Optimized**: GMVP, CVaR Minimization, Max Diversification
    - **Advanced**: Time-Series Momentum, MA Crossover, Markowitz MVO
    - **Machine Learning**: Random Forest, Gradient Boosting, ARMA, Multi-Factor ML
    - **Other**: GMRP, Quintile Factor, Max Decorrelation
    
    ### 💡 Tips
    
    - Start with fewer strategies for faster execution
    - Daily rebalancing is computationally intensive - use monthly for longer periods
    - Transaction costs significantly impact high-turnover strategies
    - Compare at least 5-10 strategies for meaningful insights
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>📈 Algorithmic Trading Dashboard v1.0 | Built with Streamlit & Plotly</p>
</div>
""", unsafe_allow_html=True)
