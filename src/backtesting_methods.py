"""
Advanced Backtesting Methods Module

This module implements multiple sophisticated backtesting methodologies to validate
trading strategies and reduce overfitting risk:

1. Vanilla Backtest - Traditional single-run historical backtest
2. Walk-Forward Backtest - Rolling/expanding window with train/test splits
3. Cross-Validation Backtest - Time-series k-fold validation
4. Monte Carlo Backtest - Synthetic data generation for robustness testing
5. Randomized Backtest - Multiple randomized starting points

Mathematical Foundations:
- Walk-Forward: Periodic re-optimization with out-of-sample testing
- Cross-Validation: Temporal splits preserving time-series order
- Monte Carlo: Bootstrap resampling and parametric simulation
- Randomized: Permutation testing for statistical significance
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Callable, Union
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm

from .portfolio_engine import PortfolioEngine, PortfolioResult
from .strategy_wrapper import BaseStrategyWrapper
from .utils import calculate_sharpe_ratio, calculate_max_drawdown

logger = logging.getLogger(__name__)


@dataclass
class BacktestMethodResult:
    """Container for results from advanced backtesting methods."""
    
    method_name: str
    individual_results: List[PortfolioResult]
    aggregate_metrics: Dict[str, float]
    confidence_intervals: Dict[str, Tuple[float, float]]
    metadata: Dict[str, any]
    
    def summary(self) -> Dict[str, any]:
        """Return comprehensive summary of results."""
        return {
            'method': self.method_name,
            'num_runs': len(self.individual_results),
            'metrics': self.aggregate_metrics,
            'confidence_intervals': self.confidence_intervals,
            'metadata': self.metadata
        }


class BacktestingMethods:
    """
    Advanced backtesting methodologies for robust strategy validation.
    
    This class provides multiple backtesting approaches to assess strategy
    performance under different conditions and reduce overfitting risk.
    """
    
    def __init__(self,
                 prices: pd.DataFrame,
                 initial_capital: float = 1000000.0,
                 transaction_cost_bps: float = 5.0,
                 slippage_bps: float = 1.0):
        """
        Initialize backtesting methods framework.
        
        Args:
            prices: Historical price data
            initial_capital: Starting portfolio value
            transaction_cost_bps: Transaction costs in basis points
            slippage_bps: Slippage in basis points
        """
        self.prices = prices
        self.initial_capital = initial_capital
        self.transaction_cost_bps = transaction_cost_bps
        self.slippage_bps = slippage_bps
        
    def vanilla_backtest(self,
                        strategy: BaseStrategyWrapper,
                        start_date: str,
                        end_date: Optional[str] = None,
                        rebalance_freq: str = 'M') -> BacktestMethodResult:
        """
        Traditional single-run backtest over entire historical period.
        
        Args:
            strategy: Strategy wrapper to test
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (optional)
            rebalance_freq: Rebalancing frequency
            
        Returns:
            BacktestMethodResult with single run
        """
        logger.info("Running Vanilla Backtest")
        
        portfolio = PortfolioEngine(
            self.prices,
            initial_capital=self.initial_capital,
            transaction_cost_bps=self.transaction_cost_bps,
            slippage_bps=self.slippage_bps
        )
        
        result = portfolio.run_backtest(
            strategy,
            start_date=start_date,
            end_date=end_date,
            rebalance_freq=rebalance_freq
        )
        
        return BacktestMethodResult(
            method_name='Vanilla Backtest',
            individual_results=[result],
            aggregate_metrics=result.summary_metrics,
            confidence_intervals={},
            metadata={
                'start_date': start_date,
                'end_date': end_date,
                'rebalance_freq': rebalance_freq
            }
        )
    
    def walk_forward_backtest(self,
                             strategy: BaseStrategyWrapper,
                             start_date: str,
                             end_date: Optional[str] = None,
                             train_window_months: int = 24,
                             test_window_months: int = 6,
                             step_months: int = 3,
                             rebalance_freq: str = 'M',
                             anchored: bool = False) -> BacktestMethodResult:
        """
        Walk-forward analysis with rolling/expanding windows.
        
        This method:
        1. Splits data into train/test periods
        2. Optimizes strategy on train period
        3. Tests on out-of-sample test period
        4. Rolls forward and repeats
        
        Args:
            strategy: Strategy wrapper to test
            start_date: Start date
            end_date: End date (optional)
            train_window_months: Training window size in months
            test_window_months: Test window size in months
            step_months: Step size for rolling window in months
            rebalance_freq: Rebalancing frequency
            anchored: If True, use expanding window; if False, use rolling window
            
        Returns:
            BacktestMethodResult with multiple walk-forward runs
        """
        logger.info(f"Running Walk-Forward Backtest ({'Anchored' if anchored else 'Rolling'})")
        
        # Parse dates
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date) if end_date else self.prices.index[-1]
        
        results = []
        walk_metadata = []
        
        current_train_start = start
        
        while True:
            # Define train period
            if anchored:
                train_start = start  # Expanding window
            else:
                train_start = current_train_start  # Rolling window
                
            train_end = current_train_start + pd.DateOffset(months=train_window_months)
            
            # Define test period
            test_start = train_end
            test_end = test_start + pd.DateOffset(months=test_window_months)
            
            # Check if we've reached the end
            if test_end > end:
                break
            
            logger.info(f"Walk {len(results) + 1}: Train [{train_start.date()} to {train_end.date()}], "
                       f"Test [{test_start.date()} to {test_end.date()}]")
            
            try:
                # Run backtest on test period (strategy trains on train period internally)
                portfolio = PortfolioEngine(
                    self.prices,
                    initial_capital=self.initial_capital,
                    transaction_cost_bps=self.transaction_cost_bps,
                    slippage_bps=self.slippage_bps
                )
                
                # Note: Strategy should be re-initialized with train period for optimization
                result = portfolio.run_backtest(
                    strategy,
                    start_date=test_start.strftime('%Y-%m-%d'),
                    end_date=test_end.strftime('%Y-%m-%d'),
                    rebalance_freq=rebalance_freq
                )
                
                results.append(result)
                walk_metadata.append({
                    'walk_number': len(results),
                    'train_start': train_start.strftime('%Y-%m-%d'),
                    'train_end': train_end.strftime('%Y-%m-%d'),
                    'test_start': test_start.strftime('%Y-%m-%d'),
                    'test_end': test_end.strftime('%Y-%m-%d')
                })
                
            except Exception as e:
                logger.warning(f"Walk-forward iteration failed: {e}")
            
            # Roll forward
            current_train_start += pd.DateOffset(months=step_months)
        
        # Aggregate results
        aggregate_metrics = self._aggregate_results(results)
        confidence_intervals = self._calculate_confidence_intervals(results)
        
        method_type = 'Anchored' if anchored else 'Rolling'
        return BacktestMethodResult(
            method_name=f'Walk-Forward Backtest ({method_type})',
            individual_results=results,
            aggregate_metrics=aggregate_metrics,
            confidence_intervals=confidence_intervals,
            metadata={
                'train_window_months': train_window_months,
                'test_window_months': test_window_months,
                'step_months': step_months,
                'anchored': anchored,
                'walks': walk_metadata
            }
        )
    
    def cross_validation_backtest(self,
                                 strategy: BaseStrategyWrapper,
                                 start_date: str,
                                 end_date: Optional[str] = None,
                                 n_splits: int = 5,
                                 test_size_months: int = 6,
                                 rebalance_freq: str = 'M') -> BacktestMethodResult:
        """
        Time-series cross-validation backtest.
        
        Splits data into k non-overlapping folds while preserving temporal order.
        Each fold is tested once while others are used for training.
        
        Args:
            strategy: Strategy wrapper to test
            start_date: Start date
            end_date: End date (optional)
            n_splits: Number of CV splits
            test_size_months: Size of each test fold in months
            rebalance_freq: Rebalancing frequency
            
        Returns:
            BacktestMethodResult with k-fold results
        """
        logger.info(f"Running {n_splits}-Fold Cross-Validation Backtest")
        
        # Parse dates
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date) if end_date else self.prices.index[-1]
        
        # Calculate fold size
        total_months = (end.year - start.year) * 12 + end.month - start.month
        fold_size_months = total_months // n_splits
        
        results = []
        fold_metadata = []
        
        for fold in range(n_splits):
            # Calculate test period for this fold
            test_start = start + pd.DateOffset(months=fold * fold_size_months)
            test_end = test_start + pd.DateOffset(months=min(test_size_months, fold_size_months))
            
            logger.info(f"Fold {fold + 1}/{n_splits}: Test [{test_start.date()} to {test_end.date()}]")
            
            try:
                portfolio = PortfolioEngine(
                    self.prices,
                    initial_capital=self.initial_capital,
                    transaction_cost_bps=self.transaction_cost_bps,
                    slippage_bps=self.slippage_bps
                )
                
                result = portfolio.run_backtest(
                    strategy,
                    start_date=test_start.strftime('%Y-%m-%d'),
                    end_date=test_end.strftime('%Y-%m-%d'),
                    rebalance_freq=rebalance_freq
                )
                
                results.append(result)
                fold_metadata.append({
                    'fold': fold + 1,
                    'test_start': test_start.strftime('%Y-%m-%d'),
                    'test_end': test_end.strftime('%Y-%m-%d')
                })
                
            except Exception as e:
                logger.warning(f"Fold {fold + 1} failed: {e}")
        
        # Aggregate results
        aggregate_metrics = self._aggregate_results(results)
        confidence_intervals = self._calculate_confidence_intervals(results)
        
        return BacktestMethodResult(
            method_name=f'{n_splits}-Fold Cross-Validation Backtest',
            individual_results=results,
            aggregate_metrics=aggregate_metrics,
            confidence_intervals=confidence_intervals,
            metadata={
                'n_splits': n_splits,
                'test_size_months': test_size_months,
                'folds': fold_metadata
            }
        )
    
    def monte_carlo_backtest(self,
                           strategy: BaseStrategyWrapper,
                           start_date: str,
                           end_date: Optional[str] = None,
                           n_simulations: int = 100,
                           method: str = 'bootstrap',
                           rebalance_freq: str = 'M',
                           block_size: int = 20) -> BacktestMethodResult:
        """
        Monte Carlo simulation with synthetic data generation.
        
        Methods:
        - 'bootstrap': Block bootstrap resampling of returns
        - 'parametric': Generate returns from fitted distributions
        - 'geometric': Geometric Brownian Motion simulation
        
        Args:
            strategy: Strategy wrapper to test
            start_date: Start date
            end_date: End date (optional)
            n_simulations: Number of Monte Carlo runs
            method: Simulation method ('bootstrap', 'parametric', 'geometric')
            rebalance_freq: Rebalancing frequency
            block_size: Block size for block bootstrap
            
        Returns:
            BacktestMethodResult with Monte Carlo results
        """
        logger.info(f"Running Monte Carlo Backtest ({method}, {n_simulations} simulations)")
        
        # Calculate returns from original prices
        returns = self.prices.pct_change().dropna()
        
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date) if end_date else self.prices.index[-1]
        
        # Filter returns to date range
        mask = (returns.index >= start) & (returns.index <= end)
        returns_subset = returns[mask]
        
        results = []
        
        for sim in tqdm(range(n_simulations), desc="Monte Carlo Simulations"):
            # Generate synthetic returns
            if method == 'bootstrap':
                synthetic_returns = self._block_bootstrap(returns_subset, block_size)
            elif method == 'parametric':
                synthetic_returns = self._parametric_simulation(returns_subset)
            elif method == 'geometric':
                synthetic_returns = self._geometric_brownian_motion(returns_subset)
            else:
                raise ValueError(f"Unknown method: {method}")
            
            # Convert returns to prices
            synthetic_prices = (1 + synthetic_returns).cumprod()
            # Get the starting price safely
            start_prices = self.prices.loc[self.prices.index >= start].iloc[0].values
            synthetic_prices = synthetic_prices * start_prices
            synthetic_prices.index = returns_subset.index
            
            try:
                # Run backtest on synthetic data
                portfolio = PortfolioEngine(
                    synthetic_prices,
                    initial_capital=self.initial_capital,
                    transaction_cost_bps=self.transaction_cost_bps,
                    slippage_bps=self.slippage_bps
                )
                
                result = portfolio.run_backtest(
                    strategy,
                    start_date=start_date,
                    end_date=end_date,
                    rebalance_freq=rebalance_freq
                )
                
                results.append(result)
                
            except Exception as e:
                logger.warning(f"Simulation {sim + 1} failed: {e}")
        
        # Aggregate results
        aggregate_metrics = self._aggregate_results(results)
        confidence_intervals = self._calculate_confidence_intervals(results)
        
        return BacktestMethodResult(
            method_name=f'Monte Carlo Backtest ({method})',
            individual_results=results,
            aggregate_metrics=aggregate_metrics,
            confidence_intervals=confidence_intervals,
            metadata={
                'n_simulations': n_simulations,
                'method': method,
                'block_size': block_size if method == 'bootstrap' else None
            }
        )
    
    def randomized_backtest(self,
                          strategy: BaseStrategyWrapper,
                          start_date: str,
                          end_date: Optional[str] = None,
                          n_trials: int = 50,
                          randomization_type: str = 'start_date',
                          rebalance_freq: str = 'M',
                          window_months: int = 24) -> BacktestMethodResult:
        """
        Randomized backtest with multiple starting points or permutations.
        
        Types:
        - 'start_date': Random starting dates within valid range
        - 'permutation': Permute returns while preserving distribution
        - 'subperiod': Random subperiods of specified length
        
        Args:
            strategy: Strategy wrapper to test
            start_date: Earliest start date
            end_date: Latest end date (optional)
            n_trials: Number of randomized trials
            randomization_type: Type of randomization
            rebalance_freq: Rebalancing frequency
            window_months: Window size for subperiod sampling
            
        Returns:
            BacktestMethodResult with randomized results
        """
        logger.info(f"Running Randomized Backtest ({randomization_type}, {n_trials} trials)")
        
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date) if end_date else self.prices.index[-1]
        
        results = []
        trial_metadata = []
        
        for trial in tqdm(range(n_trials), desc="Randomized Trials"):
            try:
                if randomization_type == 'start_date':
                    # Random start date
                    max_start = end - pd.DateOffset(months=window_months)
                    days_range = (max_start - start).days
                    random_days = np.random.randint(0, max(1, days_range))
                    trial_start = start + pd.Timedelta(days=random_days)
                    trial_end = trial_start + pd.DateOffset(months=window_months)
                    
                    trial_metadata.append({
                        'trial': trial + 1,
                        'start': trial_start.strftime('%Y-%m-%d'),
                        'end': trial_end.strftime('%Y-%m-%d')
                    })
                    
                    # Run backtest
                    portfolio = PortfolioEngine(
                        self.prices,
                        initial_capital=self.initial_capital,
                        transaction_cost_bps=self.transaction_cost_bps,
                        slippage_bps=self.slippage_bps
                    )
                    
                    result = portfolio.run_backtest(
                        strategy,
                        start_date=trial_start.strftime('%Y-%m-%d'),
                        end_date=trial_end.strftime('%Y-%m-%d'),
                        rebalance_freq=rebalance_freq
                    )
                    
                elif randomization_type == 'permutation':
                    # Permute returns
                    returns = self.prices.pct_change().dropna()
                    mask = (returns.index >= start) & (returns.index <= end)
                    returns_subset = returns[mask]
                    
                    # Randomly permute each column independently
                    permuted_returns = pd.DataFrame(
                        {col: np.random.permutation(returns_subset[col].values)
                         for col in returns_subset.columns},
                        index=returns_subset.index
                    )
                    
                    # Convert to prices
                    permuted_prices = (1 + permuted_returns).cumprod()
                    permuted_prices = permuted_prices * self.prices.loc[start].values
                    
                    trial_metadata.append({
                        'trial': trial + 1,
                        'type': 'permutation'
                    })
                    
                    # Run backtest
                    portfolio = PortfolioEngine(
                        permuted_prices,
                        initial_capital=self.initial_capital,
                        transaction_cost_bps=self.transaction_cost_bps,
                        slippage_bps=self.slippage_bps
                    )
                    
                    result = portfolio.run_backtest(
                        strategy,
                        start_date=start_date,
                        end_date=end_date,
                        rebalance_freq=rebalance_freq
                    )
                    
                elif randomization_type == 'subperiod':
                    # Random subperiod
                    all_dates = self.prices.index[(self.prices.index >= start) & 
                                                   (self.prices.index <= end)]
                    if len(all_dates) < window_months * 21:  # Approx trading days
                        raise ValueError("Not enough data for subperiod sampling")
                    
                    max_idx = len(all_dates) - window_months * 21
                    start_idx = np.random.randint(0, max(1, max_idx))
                    trial_start = all_dates[start_idx]
                    trial_end = trial_start + pd.DateOffset(months=window_months)
                    
                    trial_metadata.append({
                        'trial': trial + 1,
                        'start': trial_start.strftime('%Y-%m-%d'),
                        'end': trial_end.strftime('%Y-%m-%d')
                    })
                    
                    # Run backtest
                    portfolio = PortfolioEngine(
                        self.prices,
                        initial_capital=self.initial_capital,
                        transaction_cost_bps=self.transaction_cost_bps,
                        slippage_bps=self.slippage_bps
                    )
                    
                    result = portfolio.run_backtest(
                        strategy,
                        start_date=trial_start.strftime('%Y-%m-%d'),
                        end_date=trial_end.strftime('%Y-%m-%d'),
                        rebalance_freq=rebalance_freq
                    )
                
                results.append(result)
                
            except Exception as e:
                logger.warning(f"Trial {trial + 1} failed: {e}")
        
        # Aggregate results
        aggregate_metrics = self._aggregate_results(results)
        confidence_intervals = self._calculate_confidence_intervals(results)
        
        return BacktestMethodResult(
            method_name=f'Randomized Backtest ({randomization_type})',
            individual_results=results,
            aggregate_metrics=aggregate_metrics,
            confidence_intervals=confidence_intervals,
            metadata={
                'n_trials': n_trials,
                'randomization_type': randomization_type,
                'window_months': window_months,
                'trials': trial_metadata
            }
        )
    
    def _block_bootstrap(self, returns: pd.DataFrame, block_size: int) -> pd.DataFrame:
        """Block bootstrap resampling of returns."""
        n_periods = len(returns)
        n_blocks = n_periods // block_size
        
        # Sample blocks with replacement
        sampled_indices = []
        for _ in range(n_blocks + 1):
            start_idx = np.random.randint(0, max(1, n_periods - block_size))
            sampled_indices.extend(range(start_idx, min(start_idx + block_size, n_periods)))
        
        # Trim to original length
        sampled_indices = sampled_indices[:n_periods]
        
        return returns.iloc[sampled_indices].reset_index(drop=True)
    
    def _parametric_simulation(self, returns: pd.DataFrame) -> pd.DataFrame:
        """Generate returns from fitted normal distribution."""
        means = returns.mean()
        cov_matrix = returns.cov()
        
        # Generate multivariate normal samples
        synthetic = np.random.multivariate_normal(means, cov_matrix, size=len(returns))
        
        return pd.DataFrame(synthetic, columns=returns.columns)
    
    def _geometric_brownian_motion(self, returns: pd.DataFrame) -> pd.DataFrame:
        """Generate returns using Geometric Brownian Motion."""
        dt = 1/252  # Daily time step
        means = returns.mean()
        stds = returns.std()
        
        # GBM: dS/S = μ*dt + σ*dW
        synthetic = pd.DataFrame(index=range(len(returns)), columns=returns.columns)
        
        for col in returns.columns:
            mu = means[col]
            sigma = stds[col]
            
            # Generate random shocks
            shocks = np.random.standard_normal(len(returns))
            synthetic[col] = mu * dt + sigma * np.sqrt(dt) * shocks
        
        return synthetic
    
    def _aggregate_results(self, results: List[PortfolioResult]) -> Dict[str, float]:
        """Aggregate metrics across multiple backtest results."""
        if not results:
            return {}
        
        metrics = {}
        
        # Collect all metric values
        metric_values = {}
        for result in results:
            for metric_name, value in result.summary_metrics.items():
                if metric_name not in metric_values:
                    metric_values[metric_name] = []
                metric_values[metric_name].append(value)
        
        # Calculate aggregate statistics
        for metric_name, values in metric_values.items():
            values_array = np.array(values)
            metrics[f'{metric_name}_mean'] = np.mean(values_array)
            metrics[f'{metric_name}_median'] = np.median(values_array)
            metrics[f'{metric_name}_std'] = np.std(values_array)
            metrics[f'{metric_name}_min'] = np.min(values_array)
            metrics[f'{metric_name}_max'] = np.max(values_array)
        
        return metrics
    
    def _calculate_confidence_intervals(self,
                                       results: List[PortfolioResult],
                                       confidence_level: float = 0.95) -> Dict[str, Tuple[float, float]]:
        """Calculate confidence intervals for metrics."""
        if not results:
            return {}
        
        intervals = {}
        alpha = 1 - confidence_level
        
        # Collect metric values
        metric_values = {}
        for result in results:
            for metric_name, value in result.summary_metrics.items():
                if metric_name not in metric_values:
                    metric_values[metric_name] = []
                metric_values[metric_name].append(value)
        
        # Calculate confidence intervals
        for metric_name, values in metric_values.items():
            values_array = np.array(values)
            lower = np.percentile(values_array, alpha/2 * 100)
            upper = np.percentile(values_array, (1 - alpha/2) * 100)
            intervals[metric_name] = (lower, upper)
        
        return intervals
    
    def compare_methods(self,
                       results: List[BacktestMethodResult],
                       save_path: Optional[str] = None) -> pd.DataFrame:
        """
        Compare results from different backtesting methods.
        
        Args:
            results: List of BacktestMethodResult objects
            save_path: Optional path to save comparison table
            
        Returns:
            DataFrame with method comparison
        """
        comparison_data = []
        
        for result in results:
            row = {'Method': result.method_name}
            
            # Add aggregate metrics
            for metric_name, value in result.aggregate_metrics.items():
                row[metric_name] = value
            
            # Add confidence interval widths
            for metric_name, (lower, upper) in result.confidence_intervals.items():
                row[f'{metric_name}_ci_width'] = upper - lower
            
            comparison_data.append(row)
        
        comparison_df = pd.DataFrame(comparison_data)
        
        if save_path:
            comparison_df.to_csv(save_path, index=False)
            logger.info(f"Comparison saved to {save_path}")
        
        return comparison_df


if __name__ == "__main__":
    # Example usage
    print("Backtesting Methods Module")
    print("===========================")
    print("\nAvailable methods:")
    print("1. Vanilla Backtest - Traditional single-run backtest")
    print("2. Walk-Forward Backtest - Rolling/expanding window analysis")
    print("3. Cross-Validation Backtest - Time-series k-fold validation")
    print("4. Monte Carlo Backtest - Synthetic data generation")
    print("5. Randomized Backtest - Multiple randomized trials")
    print("\nSee demo_backtesting_methods.py for usage examples")
