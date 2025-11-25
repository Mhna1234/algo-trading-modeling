"""
Performance Evaluation Module

This module provides comprehensive performance evaluation and analysis tools
for algorithmic trading strategies. It includes:
- Risk-adjusted performance metrics
- Benchmark comparison analysis
- Risk attribution and decomposition
- Statistical significance testing
- Performance visualization and reporting

Mathematical Formulations:
- Sharpe Ratio: SR = (E[R] - R_f) / σ(R)
- Sortino Ratio: Sortino = (E[R] - R_f) / DD(R)
- Information Ratio: IR = E[R - R_b] / σ(R - R_b)
- Maximum Drawdown: MDD = max{(Peak_t - Trough_t) / Peak_t}
- Value at Risk: VaR_α = -quantile(R, α)
- Expected Shortfall: ES_α = -E[R | R ≤ VaR_α]
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
import warnings
import logging
from scipy import stats
from sklearn.metrics import mean_squared_error, mean_absolute_error
import matplotlib.pyplot as plt
import seaborn as sns

from .utils import (
    calculate_returns, annualize_returns, annualize_volatility,
    calculate_sharpe_ratio, calculate_max_drawdown, format_percentage
)

logger = logging.getLogger(__name__)

class PerformanceEvaluator:
    """
    Comprehensive performance evaluation and analysis.
    
    This class provides methods to evaluate trading strategy performance
    across multiple dimensions including returns, risk, and benchmark comparison.
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize PerformanceEvaluator.
        
        Args:
            risk_free_rate: Annual risk-free rate for calculations
        """
        self.risk_free_rate = risk_free_rate
        self.daily_rf = risk_free_rate / 252
        
    def basic_metrics(self, returns: pd.Series, 
                     benchmark_returns: Optional[pd.Series] = None) -> Dict[str, float]:
        """
        Calculate basic performance metrics.
        
        Args:
            returns: Strategy returns
            benchmark_returns: Optional benchmark returns
            
        Returns:
            Dictionary of basic performance metrics
        """
        metrics = {}
        
        # Return metrics
        metrics['Total Return'] = (1 + returns).prod() - 1
        metrics['Annualized Return'] = annualize_returns(returns)
        metrics['Volatility'] = annualize_volatility(returns)
        
        # Risk-adjusted metrics
        metrics['Sharpe Ratio'] = calculate_sharpe_ratio(returns, self.risk_free_rate)
        metrics['Max Drawdown'] = calculate_max_drawdown(returns)
        
        # Calmar ratio
        if metrics['Max Drawdown'] != 0:
            metrics['Calmar Ratio'] = metrics['Annualized Return'] / abs(metrics['Max Drawdown'])
        else:
            metrics['Calmar Ratio'] = np.nan
        
        # Additional return statistics
        metrics['Skewness'] = returns.skew()
        metrics['Kurtosis'] = returns.kurtosis()
        metrics['Win Rate'] = (returns > 0).mean()
        
        # Benchmark comparison if provided
        if benchmark_returns is not None:
            aligned_data = pd.concat([returns, benchmark_returns], axis=1).dropna()
            if len(aligned_data) > 0:
                strat_ret, bench_ret = aligned_data.iloc[:, 0], aligned_data.iloc[:, 1]
                
                metrics['Benchmark Return'] = annualize_returns(bench_ret)
                metrics['Benchmark Volatility'] = annualize_volatility(bench_ret)
                metrics['Benchmark Sharpe'] = calculate_sharpe_ratio(bench_ret, self.risk_free_rate)
                
                # Excess return metrics
                excess_returns = strat_ret - bench_ret
                metrics['Excess Return'] = annualize_returns(excess_returns)
                metrics['Tracking Error'] = annualize_volatility(excess_returns)
                
                if metrics['Tracking Error'] > 0:
                    metrics['Information Ratio'] = metrics['Excess Return'] / metrics['Tracking Error']
                else:
                    metrics['Information Ratio'] = np.nan
                
                # Beta and Alpha
                if bench_ret.var() > 0:
                    metrics['Beta'] = strat_ret.cov(bench_ret) / bench_ret.var()
                    metrics['Alpha'] = (metrics['Annualized Return'] - self.risk_free_rate) - \
                                     metrics['Beta'] * (metrics['Benchmark Return'] - self.risk_free_rate)
                else:
                    metrics['Beta'] = np.nan
                    metrics['Alpha'] = np.nan
        
        return metrics
    
    def risk_metrics(self, returns: pd.Series) -> Dict[str, float]:
        """
        Calculate comprehensive risk metrics.
        
        Args:
            returns: Strategy returns
            
        Returns:
            Dictionary of risk metrics
        """
        metrics = {}
        
        # Value at Risk (VaR)
        metrics['VaR 95%'] = returns.quantile(0.05)
        metrics['VaR 99%'] = returns.quantile(0.01)
        
        # Expected Shortfall (Conditional VaR)
        var_95 = metrics['VaR 95%']
        var_99 = metrics['VaR 99%']
        
        tail_returns_95 = returns[returns <= var_95]
        tail_returns_99 = returns[returns <= var_99]
        
        metrics['CVaR 95%'] = tail_returns_95.mean() if len(tail_returns_95) > 0 else np.nan
        metrics['CVaR 99%'] = tail_returns_99.mean() if len(tail_returns_99) > 0 else np.nan
        
        # Downside deviation and Sortino ratio
        downside_returns = returns[returns < self.daily_rf]
        if len(downside_returns) > 0:
            metrics['Downside Deviation'] = annualize_volatility(downside_returns)
            metrics['Sortino Ratio'] = (annualize_returns(returns) - self.risk_free_rate) / \
                                     metrics['Downside Deviation']
        else:
            metrics['Downside Deviation'] = 0.0
            metrics['Sortino Ratio'] = np.nan
        
        # Maximum consecutive losses
        consecutive_losses = 0
        max_consecutive_losses = 0
        
        for ret in returns:
            if ret < 0:
                consecutive_losses += 1
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
            else:
                consecutive_losses = 0
        
        metrics['Max Consecutive Losses'] = max_consecutive_losses
        
        # Ulcer Index (alternative drawdown measure)
        nav = (1 + returns).cumprod()
        running_max = nav.expanding().max()
        drawdown_pct = (nav - running_max) / running_max
        metrics['Ulcer Index'] = np.sqrt((drawdown_pct ** 2).mean())
        
        return metrics
    
    def rolling_performance(self, returns: pd.Series,
                          window: int = 252,
                          benchmark_returns: Optional[pd.Series] = None) -> pd.DataFrame:
        """
        Calculate rolling performance metrics.
        
        Args:
            returns: Strategy returns
            window: Rolling window size (default: 252 trading days = 1 year)
            benchmark_returns: Optional benchmark returns
            
        Returns:
            DataFrame with rolling metrics
        """
        rolling_metrics = pd.DataFrame(index=returns.index)
        
        # Rolling return metrics
        rolling_metrics['Rolling Return'] = returns.rolling(window).apply(
            lambda x: (1 + x).prod() - 1, raw=False)
        rolling_metrics['Rolling Volatility'] = returns.rolling(window).std() * np.sqrt(252)
        rolling_metrics['Rolling Sharpe'] = (
            returns.rolling(window).mean() - self.daily_rf
        ) / returns.rolling(window).std() * np.sqrt(252)
        
        # Rolling max drawdown
        nav = (1 + returns).cumprod()
        rolling_max = nav.rolling(window).max()
        rolling_drawdown = (nav - rolling_max) / rolling_max
        rolling_metrics['Rolling Max Drawdown'] = rolling_drawdown.rolling(window).min()
        
        # Rolling VaR
        rolling_metrics['Rolling VaR 95%'] = returns.rolling(window).quantile(0.05)
        
        # Rolling win rate
        rolling_metrics['Rolling Win Rate'] = (returns > 0).rolling(window).mean()
        
        # Benchmark comparison if provided
        if benchmark_returns is not None:
            excess_returns = returns - benchmark_returns
            rolling_metrics['Rolling Excess Return'] = excess_returns.rolling(window).apply(
                lambda x: (1 + x).prod() - 1, raw=False)
            rolling_metrics['Rolling Information Ratio'] = (
                excess_returns.rolling(window).mean() / 
                excess_returns.rolling(window).std() * np.sqrt(252)
            )
        
        return rolling_metrics
    
    def drawdown_analysis(self, returns: pd.Series) -> Dict[str, Union[float, pd.Series]]:
        """
        Perform detailed drawdown analysis.
        
        Args:
            returns: Strategy returns
            
        Returns:
            Dictionary with drawdown statistics and time series
        """
        nav = (1 + returns).cumprod()
        running_max = nav.expanding().max()
        drawdown = (nav - running_max) / running_max
        
        # Find drawdown periods
        is_drawdown = drawdown < 0
        drawdown_periods = []
        
        in_drawdown = False
        start_date = None
        
        for date, is_dd in is_drawdown.items():
            if is_dd and not in_drawdown:
                # Start of drawdown
                in_drawdown = True
                start_date = date
            elif not is_dd and in_drawdown:
                # End of drawdown
                in_drawdown = False
                end_date = date
                period_drawdown = drawdown[start_date:end_date]
                max_dd_in_period = period_drawdown.min()
                duration = len(period_drawdown)
                
                drawdown_periods.append({
                    'start': start_date,
                    'end': end_date,
                    'duration': duration,
                    'max_drawdown': max_dd_in_period
                })
        
        # Handle case where we're still in drawdown at the end
        if in_drawdown:
            end_date = returns.index[-1]
            period_drawdown = drawdown[start_date:end_date]
            max_dd_in_period = period_drawdown.min()
            duration = len(period_drawdown)
            
            drawdown_periods.append({
                'start': start_date,
                'end': end_date,
                'duration': duration,
                'max_drawdown': max_dd_in_period
            })
        
        # Summary statistics
        if drawdown_periods:
            max_drawdown_period = min(drawdown_periods, key=lambda x: x['max_drawdown'])
            longest_drawdown_period = max(drawdown_periods, key=lambda x: x['duration'])
            avg_drawdown = np.mean([p['max_drawdown'] for p in drawdown_periods])
            avg_duration = np.mean([p['duration'] for p in drawdown_periods])
        else:
            max_drawdown_period = None
            longest_drawdown_period = None
            avg_drawdown = 0
            avg_duration = 0
        
        return {
            'drawdown_series': drawdown,
            'max_drawdown': drawdown.min(),
            'max_drawdown_period': max_drawdown_period,
            'longest_drawdown_period': longest_drawdown_period,
            'num_drawdown_periods': len(drawdown_periods),
            'avg_drawdown': avg_drawdown,
            'avg_drawdown_duration': avg_duration,
            'all_periods': drawdown_periods
        }
    
    def monte_carlo_analysis(self, returns: pd.Series,
                           num_simulations: int = 1000,
                           simulation_length: Optional[int] = None) -> Dict[str, Union[float, np.ndarray]]:
        """
        Perform Monte Carlo analysis of strategy performance.
        
        Args:
            returns: Historical strategy returns
            num_simulations: Number of Monte Carlo simulations
            simulation_length: Length of each simulation (default: same as input)
            
        Returns:
            Dictionary with Monte Carlo results
        """
        if simulation_length is None:
            simulation_length = len(returns)
        
        # Fit distribution to returns (assuming normal for simplicity)
        mean_return = returns.mean()
        std_return = returns.std()
        
        # Run simulations
        simulated_final_returns = []
        simulated_max_drawdowns = []
        simulated_sharpe_ratios = []
        
        for _ in range(num_simulations):
            # Generate random returns
            sim_returns = np.random.normal(mean_return, std_return, simulation_length)
            sim_returns = pd.Series(sim_returns)
            
            # Calculate metrics for this simulation
            final_return = (1 + sim_returns).prod() - 1
            max_dd = calculate_max_drawdown(sim_returns)
            sharpe = calculate_sharpe_ratio(sim_returns, self.risk_free_rate)
            
            simulated_final_returns.append(final_return)
            simulated_max_drawdowns.append(max_dd)
            simulated_sharpe_ratios.append(sharpe)
        
        # Actual strategy performance
        actual_final_return = (1 + returns).prod() - 1
        actual_max_dd = calculate_max_drawdown(returns)
        actual_sharpe = calculate_sharpe_ratio(returns, self.risk_free_rate)
        
        # Calculate percentiles
        return_percentile = stats.percentileofscore(simulated_final_returns, actual_final_return)
        dd_percentile = stats.percentileofscore(simulated_max_drawdowns, actual_max_dd)
        sharpe_percentile = stats.percentileofscore(simulated_sharpe_ratios, actual_sharpe)
        
        return {
            'simulated_returns': np.array(simulated_final_returns),
            'simulated_max_drawdowns': np.array(simulated_max_drawdowns),
            'simulated_sharpe_ratios': np.array(simulated_sharpe_ratios),
            'return_percentile': return_percentile,
            'max_dd_percentile': dd_percentile,
            'sharpe_percentile': sharpe_percentile,
            'mean_simulated_return': np.mean(simulated_final_returns),
            'std_simulated_return': np.std(simulated_final_returns)
        }
    
    def statistical_significance(self, returns: pd.Series,
                                benchmark_returns: pd.Series,
                                confidence_level: float = 0.95) -> Dict[str, float]:
        """
        Test statistical significance of outperformance vs benchmark.
        
        Args:
            returns: Strategy returns
            benchmark_returns: Benchmark returns
            confidence_level: Confidence level for tests
            
        Returns:
            Dictionary with statistical test results
        """
        # Align returns
        aligned_data = pd.concat([returns, benchmark_returns], axis=1).dropna()
        if len(aligned_data) < 30:
            logger.warning("Insufficient data for reliable statistical tests")
        
        strat_returns = aligned_data.iloc[:, 0]
        bench_returns = aligned_data.iloc[:, 1]
        excess_returns = strat_returns - bench_returns
        
        # T-test for mean excess return
        t_stat, t_p_value = stats.ttest_1samp(excess_returns, 0)
        
        # Information ratio t-test
        if excess_returns.std() > 0:
            ir_t_stat = excess_returns.mean() / (excess_returns.std() / np.sqrt(len(excess_returns)))
        else:
            ir_t_stat = np.nan
        
        # Sharpe ratio significance test
        strat_sharpe = calculate_sharpe_ratio(strat_returns, self.risk_free_rate)
        bench_sharpe = calculate_sharpe_ratio(bench_returns, self.risk_free_rate)
        
        # Approximate test for Sharpe ratio difference
        n = len(strat_returns)
        if n > 30:
            sharpe_diff = strat_sharpe - bench_sharpe
            sharpe_se = np.sqrt((1 + 0.5 * strat_sharpe**2) / n)
            sharpe_t_stat = sharpe_diff / sharpe_se
            sharpe_p_value = 2 * (1 - stats.t.cdf(abs(sharpe_t_stat), n - 1))
        else:
            sharpe_t_stat = np.nan
            sharpe_p_value = np.nan
        
        return {
            'excess_return_t_stat': t_stat,
            'excess_return_p_value': t_p_value,
            'excess_return_significant': t_p_value < (1 - confidence_level),
            'information_ratio_t_stat': ir_t_stat,
            'sharpe_diff_t_stat': sharpe_t_stat,
            'sharpe_diff_p_value': sharpe_p_value,
            'sharpe_diff_significant': sharpe_p_value < (1 - confidence_level) if not np.isnan(sharpe_p_value) else False
        }
    
    def generate_report(self, returns: pd.Series,
                       benchmark_returns: Optional[pd.Series] = None,
                       strategy_name: str = "Strategy") -> str:
        """
        Generate a comprehensive performance report.
        
        Args:
            returns: Strategy returns
            benchmark_returns: Optional benchmark returns
            strategy_name: Name of the strategy
            
        Returns:
            Formatted performance report as string
        """
        report = f"\n{'='*60}\n"
        report += f"PERFORMANCE REPORT: {strategy_name}\n"
        report += f"{'='*60}\n\n"
        
        # Basic metrics
        basic = self.basic_metrics(returns, benchmark_returns)
        report += "BASIC PERFORMANCE METRICS\n"
        report += "-" * 30 + "\n"
        
        for key, value in basic.items():
            if isinstance(value, float):
                if 'Return' in key or 'Alpha' in key:
                    report += f"{key:.<25} {format_percentage(value)}\n"
                elif 'Ratio' in key or 'Beta' in key:
                    report += f"{key:.<25} {value:.3f}\n"
                elif 'Rate' in key:
                    report += f"{key:.<25} {format_percentage(value)}\n"
                else:
                    report += f"{key:.<25} {value:.4f}\n"
        
        # Risk metrics
        risk = self.risk_metrics(returns)
        report += f"\nRISK METRICS\n"
        report += "-" * 30 + "\n"
        
        for key, value in risk.items():
            if isinstance(value, float) and not np.isnan(value):
                if 'Return' in key or 'VaR' in key or 'CVaR' in key or 'Deviation' in key:
                    report += f"{key:.<25} {format_percentage(value)}\n"
                elif 'Ratio' in key:
                    report += f"{key:.<25} {value:.3f}\n"
                else:
                    report += f"{key:.<25} {value:.2f}\n"
        
        # Drawdown analysis
        dd_analysis = self.drawdown_analysis(returns)
        report += f"\nDRAWDOWN ANALYSIS\n"
        report += "-" * 30 + "\n"
        report += f"Maximum Drawdown........... {format_percentage(dd_analysis['max_drawdown'])}\n"
        report += f"Number of DD Periods....... {dd_analysis['num_drawdown_periods']}\n"
        report += f"Average Drawdown........... {format_percentage(dd_analysis['avg_drawdown'])}\n"
        report += f"Average DD Duration........ {dd_analysis['avg_drawdown_duration']:.1f} days\n"
        
        if dd_analysis['max_drawdown_period']:
            max_dd_period = dd_analysis['max_drawdown_period']
            report += f"Worst Drawdown Period...... {max_dd_period['start'].strftime('%Y-%m-%d')} to {max_dd_period['end'].strftime('%Y-%m-%d')}\n"
        
        # Statistical significance if benchmark provided
        if benchmark_returns is not None:
            sig_tests = self.statistical_significance(returns, benchmark_returns)
            report += f"\nSTATISTICAL SIGNIFICANCE\n"
            report += "-" * 30 + "\n"
            report += f"Excess Return T-stat....... {sig_tests['excess_return_t_stat']:.3f}\n"
            report += f"Excess Return P-value...... {sig_tests['excess_return_p_value']:.4f}\n"
            report += f"Outperformance Significant. {'Yes' if sig_tests['excess_return_significant'] else 'No'}\n"
        
        report += f"\n{'='*60}\n"
        
        return report


def evaluate_performance(returns: pd.Series,
                        benchmark_returns: Optional[pd.Series] = None,
                        risk_free_rate: float = 0.02) -> Dict[str, Union[float, Dict]]:
    """
    Convenience function to evaluate strategy performance.
    
    Args:
        returns: Strategy returns
        benchmark_returns: Optional benchmark returns
        risk_free_rate: Risk-free rate for calculations
        
    Returns:
        Dictionary with performance metrics
    """
    evaluator = PerformanceEvaluator(risk_free_rate)
    
    results = {
        'basic_metrics': evaluator.basic_metrics(returns, benchmark_returns),
        'risk_metrics': evaluator.risk_metrics(returns),
        'drawdown_analysis': evaluator.drawdown_analysis(returns)
    }
    
    if benchmark_returns is not None:
        results['statistical_significance'] = evaluator.statistical_significance(
            returns, benchmark_returns)
    
    return results


if __name__ == "__main__":
    # Example usage
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Generate sample strategy returns
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', '2023-12-31', freq='D')
    
    # Strategy returns (slightly outperforming market)
    strategy_returns = pd.Series(
        np.random.normal(0.0008, 0.015, len(dates)),  # 20% annual return, 24% vol
        index=dates,
        name='Strategy'
    )
    
    # Benchmark returns (market-like)
    benchmark_returns = pd.Series(
        np.random.normal(0.0004, 0.012, len(dates)),  # 10% annual return, 19% vol
        index=dates,
        name='Benchmark'
    )
    
    # Initialize evaluator
    evaluator = PerformanceEvaluator(risk_free_rate=0.02)
    
    try:
        print("Performance Evaluation Example")
        print("=" * 50)
        
        # Basic metrics
        basic_metrics = evaluator.basic_metrics(strategy_returns, benchmark_returns)
        print("\nBasic Metrics:")
        for key, value in basic_metrics.items():
            if isinstance(value, float):
                if 'Return' in key:
                    print(f"  {key}: {format_percentage(value)}")
                elif 'Ratio' in key:
                    print(f"  {key}: {value:.3f}")
                else:
                    print(f"  {key}: {value:.4f}")
        
        # Risk metrics
        risk_metrics = evaluator.risk_metrics(strategy_returns)
        print(f"\nRisk Metrics:")
        print(f"  VaR 95%: {format_percentage(risk_metrics['VaR 95%'])}")
        print(f"  CVaR 95%: {format_percentage(risk_metrics['CVaR 95%'])}")
        print(f"  Sortino Ratio: {risk_metrics['Sortino Ratio']:.3f}")
        
        # Drawdown analysis
        dd_analysis = evaluator.drawdown_analysis(strategy_returns)
        print(f"\nDrawdown Analysis:")
        print(f"  Max Drawdown: {format_percentage(dd_analysis['max_drawdown'])}")
        print(f"  Number of DD Periods: {dd_analysis['num_drawdown_periods']}")
        
        # Statistical significance
        sig_tests = evaluator.statistical_significance(strategy_returns, benchmark_returns)
        print(f"\nStatistical Significance:")
        print(f"  Excess Return T-stat: {sig_tests['excess_return_t_stat']:.3f}")
        print(f"  Outperformance Significant: {'Yes' if sig_tests['excess_return_significant'] else 'No'}")
        
        # Generate full report
        report = evaluator.generate_report(strategy_returns, benchmark_returns, "Example Strategy")
        print(report)
        
    except Exception as e:
        print(f"Error in example: {e}")
        import traceback
        traceback.print_exc()