"""
Main Algorithmic Trading Pipeline

This is the main entry point for the algorithmic trading system.
It orchestrates the entire pipeline from data loading to strategy evaluation:

1. Data Loading & Preprocessing
2. Feature Engineering & Technical Indicators
3. Time Series Forecasting (ARIMA + GARCH)
4. Signal Generation
5. Portfolio Optimization
6. Backtesting & Evaluation
7. Results Visualization & Reporting

Usage:
    python main.py [--config config.yaml] [--tickers AAPL MSFT SPY] [--start 2020-01-01] [--end 2024-01-01]
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from datetime import datetime
import warnings
import pandas as pd
import numpy as np

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import all our modules
from src.data_loader import load_data
from src.feature_engineering import make_features
from src.forecasting import ARIMAGARCHForecaster
from src.signal_generator import SignalGenerator
from src.optimizer import PortfolioOptimizer
from src.backtester import Backtester, BacktestResults
from src.evaluator import PerformanceEvaluator
from src.utils import TradingConfig, setup_logging, timing_decorator, rebalance_dates

# Import new Portfolio system
from src.portfolio import Portfolio
from src.portfolio_adapter import (
    BacktesterAdapter, ForecastPortfolioAdapter, 
    SignalPortfolioAdapter, ConfigurationAdapter, AdapterResult
)

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)


class AlgorithmicTradingPipeline:
    """
    Complete algorithmic trading pipeline that integrates all components.
    
    This class orchestrates the entire workflow from data loading to 
    strategy evaluation and reporting.
    """
    
    def __init__(self, config: TradingConfig):
        """
        Initialize the trading pipeline with configuration.
        
        Args:
            config: TradingConfig object with all parameters
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.forecaster = ARIMAGARCHForecaster(
            arima_order=config.arima_order,
            garch_order=config.garch_order,
            auto_order=config.auto_order_selection
        )
        
        self.signal_generator = SignalGenerator(
            signal_threshold=config.signal_threshold,
            volatility_scaling=config.volatility_scaling,
            signal_smoothing=config.signal_smoothing,
            smoothing_window=config.smoothing_window
        )
        
        self.optimizer = PortfolioOptimizer(
            risk_free_rate=config.risk_free_rate,
            max_weight=config.max_weight,
            min_weight=config.min_weight,
            transaction_cost=config.transaction_cost,
            turnover_limit=config.turnover_limit
        )
        
        # Initialize backtesting system (choose between old and new)
        if config.use_portfolio_class:
            self.backtester = BacktesterAdapter(config=config)
            logger.info("Using new Portfolio class for backtesting")
        else:
            self.backtester = Backtester(
                config=config,
                initial_capital=config.initial_capital,
                transaction_cost=config.transaction_cost,
                rebalance_frequency=config.rebalance_frequency,
                benchmark_ticker=config.benchmark
            )
            logger.info("Using legacy Backtester class")
        
        self.evaluator = PerformanceEvaluator(
            risk_free_rate=config.risk_free_rate
        )
        
        # Storage for pipeline results
        self.data = {}
        self.features = {}
        self.forecasts = {}
        self.signals = {}
        self.weights = {}
        self.backtest_results = None
        
    @timing_decorator
    def load_and_prepare_data(self) -> None:
        """Load and preprocess market data."""
        self.logger.info(f"Loading data for {self.config.tickers}")
        self.logger.info(f"Date range: {self.config.start_date} to {self.config.end_date}")
        
        # Load price data
        full_data, price_data = load_data(
            tickers=self.config.tickers,
            start=self.config.start_date,
            end=self.config.end_date
        )
        
        self.data['full_data'] = full_data
        self.data['price_data'] = price_data
        
        # Load benchmark data if different from assets
        if self.config.benchmark not in self.config.tickers:
            try:
                _, benchmark_data = load_data(
                    tickers=[self.config.benchmark],
                    start=self.config.start_date,
                    end=self.config.end_date
                )
                self.data['benchmark_data'] = benchmark_data
            except Exception as e:
                self.logger.warning(f"Could not load benchmark {self.config.benchmark}: {e}")
                self.data['benchmark_data'] = None
        else:
            self.data['benchmark_data'] = price_data[[self.config.benchmark]]
        
        self.logger.info(f"Loaded data: {price_data.shape[0]} days, {price_data.shape[1]} assets")
    
    @timing_decorator
    def engineer_features(self) -> None:
        """Compute technical indicators and features."""
        self.logger.info("Computing technical indicators and features")
        
        # Generate all features
        self.features = make_features(
            prices=self.data['price_data'],
            include_returns=True,
            include_ma=True,
            include_volatility=True,
            include_rsi=True,
            include_macd=True,
            include_bb=True,
            include_stats=True,
            include_momentum=True
        )
        
        feature_count = len([k for k, v in self.features.items() if hasattr(v, 'shape')])
        self.logger.info(f"Generated {feature_count} feature sets")
    
    @timing_decorator 
    def generate_forecasts(self) -> None:
        """Generate return and volatility forecasts using ARIMA+GARCH."""
        self.logger.info("Generating ARIMA+GARCH forecasts")
        
        # Use returns for forecasting
        returns_data = self.features['returns']
        
        # Generate forecasts
        mean_forecasts, vol_forecasts = self.forecaster.forecast_portfolio(
            returns=returns_data,
            steps=self.config.forecast_horizon
        )
        
        self.forecasts['mean'] = mean_forecasts
        self.forecasts['volatility'] = vol_forecasts
        
        self.logger.info(f"Generated forecasts for {len(mean_forecasts.columns)} assets")
    
    @timing_decorator
    def generate_trading_signals(self) -> None:
        """Generate trading signals from forecasts and technical indicators."""
        self.logger.info("Generating trading signals")
        
        # Prepare data for signal generation
        signal_data = {
            'prices': self.data['price_data'],
            'returns': self.features['returns'],
            'volatility': self.features['volatility'],
            'mean_forecast': self.forecasts['mean'],
            'vol_forecast': self.forecasts['volatility']
        }
        
        # Generate combined signals
        strategies = ['ma_crossover', 'macd', 'rsi', 'forecast']
        strategy_weights = {
            'ma_crossover': 0.25,
            'macd': 0.25, 
            'rsi': 0.25,
            'forecast': 0.25
        }
        
        self.signals['combined'] = self.signal_generator.generate_signals(
            data=signal_data,
            strategies=strategies,
            strategy_weights=strategy_weights
        )
        
        signal_count = (self.signals['combined'] != 0).sum().sum()
        self.logger.info(f"Generated {signal_count} non-zero signals")
    
    @timing_decorator
    def optimize_portfolio(self) -> None:
        """Optimize portfolio weights using forecasts and signals."""
        self.logger.info("Optimizing portfolio weights")
        
        if self.config.use_portfolio_class:
            # Use new Portfolio class optimization
            self._optimize_with_portfolio_class()
        else:
            # Use legacy optimization method
            self._optimize_with_legacy_method()
    
    def _optimize_with_portfolio_class(self) -> None:
        """Optimize using new Portfolio class and adapters."""
        self.logger.info("Using Portfolio class for optimization")
        
        # Initialize Portfolio instance
        portfolio_params = ConfigurationAdapter.trading_config_to_portfolio_params(self.config)
        portfolio = Portfolio(self.data['price_data'], **portfolio_params)
        
        # Create forecast adapter
        forecast_adapter = ForecastPortfolioAdapter(portfolio, self.config)
        
        # Generate weights using forecasts
        schedule_map = {
            'daily': 'D',
            'weekly': 'W',
            'monthly': 'M',
            'quarterly': 'Q'
        }
        schedule = schedule_map.get(self.config.rebalance_frequency, 'M')
        
        try:
            # Generate weights using forecaster
            weights_df = forecast_adapter.generate_weights_from_forecasts(
                forecaster=self.forecaster,
                schedule=schedule
            )
            
            # If we have signals, create combined approach
            if hasattr(self, 'signals') and 'combined' in self.signals:
                self.logger.info("Combining forecast and signal-based weights")
                
                # Create signal adapter
                signal_adapter = SignalPortfolioAdapter(portfolio, self.config)
                signal_weights = signal_adapter.generate_weights_from_signals(
                    signals_data=self.signals['combined'],
                    schedule=schedule
                )
                
                # Combine forecasts and signals (50/50 blend)
                weights_df = 0.5 * weights_df + 0.5 * signal_weights
                
                # Renormalize to ensure weights sum to 1
                weights_df = weights_df.div(weights_df.sum(axis=1), axis=0).fillna(0)
            
            self.weights['optimized'] = weights_df
            self.logger.info(f"Generated Portfolio class weights for {len(weights_df)} periods")
            
        except Exception as e:
            self.logger.error(f"Portfolio class optimization failed: {e}")
            # Fallback to legacy method
            self.logger.info("Falling back to legacy optimization method")
            self._optimize_with_legacy_method()
    
    def _optimize_with_legacy_method(self) -> None:
        """Legacy optimization method (original implementation)."""
        self.logger.info("Using legacy optimization method")
        
        # Get rebalancing dates
        rebal_dates = rebalance_dates(
            start_date=self.config.start_date,
            end_date=self.config.end_date,
            frequency=self.config.rebalance_frequency
        )
        
        # Filter rebalancing dates to match our data
        price_dates = self.data['price_data'].index
        rebal_dates = [d for d in rebal_dates if d in price_dates]
        
        # Initialize weights DataFrame
        weights_df = pd.DataFrame(
            index=price_dates,
            columns=self.data['price_data'].columns,
            dtype=float
        )
        
        # Get covariance matrix
        cov_matrix = self.features['cov']
        previous_weights = None
        
        # Optimize for each rebalancing period
        for i, rebal_date in enumerate(rebal_dates):
            if rebal_date not in price_dates:
                continue
                
            try:
                # Get forecast for this date (use latest available)
                forecast_idx = min(len(self.forecasts['mean']) - 1, 0)
                mean_forecast = self.forecasts['mean'].iloc[forecast_idx]
                
                # Optimize portfolio
                optimal_weights = self.optimizer.optimize_portfolio_forecasted(
                    mean_forecast=mean_forecast,
                    cov_matrix=cov_matrix,
                    method=self.config.optimization_method,
                    previous_weights=previous_weights
                )
                
                # Forward fill weights until next rebalancing date
                next_rebal_idx = i + 1
                if next_rebal_idx < len(rebal_dates):
                    end_date = rebal_dates[next_rebal_idx]
                    date_range = price_dates[(price_dates >= rebal_date) & (price_dates < end_date)]
                else:
                    date_range = price_dates[price_dates >= rebal_date]
                
                for date in date_range:
                    weights_df.loc[date] = optimal_weights
                
                previous_weights = optimal_weights
                
            except Exception as e:
                self.logger.warning(f"Portfolio optimization failed for {rebal_date}: {e}")
                # Use equal weights as fallback
                equal_weights = np.ones(len(self.data['price_data'].columns)) / len(self.data['price_data'].columns)
                
                # Forward fill until next rebalancing
                next_rebal_idx = i + 1
                if next_rebal_idx < len(rebal_dates):
                    end_date = rebal_dates[next_rebal_idx]
                    date_range = price_dates[(price_dates >= rebal_date) & (price_dates < end_date)]
                else:
                    date_range = price_dates[price_dates >= rebal_date]
                
                for date in date_range:
                    weights_df.loc[date] = equal_weights
        
        # Handle any remaining NaN values
        weights_df = weights_df.fillna(method='ffill').fillna(1/len(self.data['price_data'].columns))
        
        self.weights['optimized'] = weights_df
        
        rebal_count = len(rebal_dates)
        self.logger.info(f"Optimized portfolio weights for {rebal_count} rebalancing periods")
    
    @timing_decorator
    def run_backtest(self) -> None:
        """Run backtest simulation."""
        self.logger.info("Running backtest simulation")
        
        # Run the backtest
        self.backtest_results = self.backtester.run_backtest(
            price_data=self.data['price_data'],
            weight_data=self.weights['optimized'],
            benchmark_data=self.data['benchmark_data'],
            signals_data=self.signals.get('combined')
        )
        
        self.logger.info("Backtest completed successfully")
        
        # Log performance summary
        if hasattr(self.backtest_results, 'summary'):
            summary = self.backtest_results.summary()
            self.logger.info(f"Backtest Summary - Return: {summary.get('Total Return', 0):.2%}, "
                           f"Sharpe: {summary.get('Sharpe Ratio', 0):.3f}, "
                           f"Max DD: {summary.get('Max Drawdown', 0):.2%}")
    
    @timing_decorator
    def evaluate_performance(self) -> None:
        """Evaluate strategy performance and generate report."""
        self.logger.info("Evaluating strategy performance")
        
        if self.backtest_results is None:
            raise ValueError("Must run backtest before evaluation")
        
        # Generate comprehensive performance report
        report = self.evaluator.generate_report(
            returns=self.backtest_results.portfolio_returns,
            benchmark_returns=self.backtest_results.benchmark_returns,
            strategy_name="ARIMA-GARCH Algorithmic Strategy"
        )
        
        print(report)
        
        # Save detailed results
        results_summary = self.backtest_results.summary()
        
        self.logger.info("Performance evaluation completed")
        return results_summary
    
    def plot_results(self, save_plots: bool = True) -> None:
        """Generate and display result plots."""
        self.logger.info("Generating result plots")
        
        if self.backtest_results is None:
            raise ValueError("Must run backtest before plotting")
        
        try:
            # Use backtester's plotting method if available
            if hasattr(self.backtester, 'plot_results'):
                save_path = "backtest_results.png" if save_plots else None
                self.backtester.plot_results(save_path=save_path)
            else:
                # Create basic plot for Portfolio class results
                self._plot_portfolio_results(save_plots)
                
            self.logger.info("Plots generated successfully")
            
        except Exception as e:
            self.logger.warning(f"Plotting failed: {e}")
            self.logger.info("Skipping plot generation")
    
    def _plot_portfolio_results(self, save_plots: bool = True) -> None:
        """Create basic plots for Portfolio class results."""
        import matplotlib.pyplot as plt
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Portfolio NAV
        nav = self.backtest_results.portfolio_nav
        axes[0, 0].plot(nav.index, nav.values, label='Portfolio', linewidth=2)
        
        if hasattr(self.backtest_results, 'benchmark_nav') and len(self.backtest_results.benchmark_nav) > 0:
            bench_nav = self.backtest_results.benchmark_nav
            axes[0, 0].plot(bench_nav.index, bench_nav.values, 
                           label='Benchmark', linewidth=1, alpha=0.7)
        
        axes[0, 0].set_title('Portfolio Value Over Time')
        axes[0, 0].set_ylabel('Portfolio Value ($)')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # Returns distribution
        returns = self.backtest_results.portfolio_returns
        axes[0, 1].hist(returns, bins=50, alpha=0.7, edgecolor='black')
        axes[0, 1].set_title('Returns Distribution')
        axes[0, 1].set_xlabel('Daily Returns')
        axes[0, 1].set_ylabel('Frequency')
        axes[0, 1].grid(True, alpha=0.3)
        
        # Drawdown
        cumulative = nav / nav.iloc[0]
        rolling_max = cumulative.expanding().max()
        drawdown = (cumulative - rolling_max) / rolling_max
        axes[1, 0].fill_between(drawdown.index, drawdown.values, 0, alpha=0.7, color='red')
        axes[1, 0].set_title('Portfolio Drawdown')
        axes[1, 0].set_ylabel('Drawdown')
        axes[1, 0].grid(True, alpha=0.3)
        
        # Portfolio weights (if not too many assets)
        weights = self.backtest_results.portfolio_weights
        if len(weights.columns) <= 10:
            weights.plot(kind='area', stacked=True, ax=axes[1, 1], alpha=0.7)
            axes[1, 1].set_title('Portfolio Weights Over Time')
            axes[1, 1].set_ylabel('Weight')
            axes[1, 1].legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        else:
            total_exposure = weights.sum(axis=1)
            axes[1, 1].plot(total_exposure.index, total_exposure.values)
            axes[1, 1].set_title('Total Portfolio Exposure')
            axes[1, 1].set_ylabel('Total Weight')
        
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_plots:
            plt.savefig('portfolio_backtest_results.png', dpi=300, bbox_inches='tight')
        
        plt.show()
    
    @timing_decorator
    def run_full_pipeline(self) -> BacktestResults:
        """
        Run the complete algorithmic trading pipeline.
        
        Returns:
            BacktestResults object with comprehensive performance metrics
        """
        self.logger.info("Starting full algorithmic trading pipeline")
        
        try:
            # Execute pipeline steps
            self.load_and_prepare_data()
            self.engineer_features()
            self.generate_forecasts()
            self.generate_trading_signals()
            self.optimize_portfolio()
            self.run_backtest()
            results_summary = self.evaluate_performance()
            self.plot_results()
            
            self.logger.info("Full pipeline completed successfully")
            return self.backtest_results
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            raise


def main():
    """Main entry point for the algorithmic trading system."""
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Algorithmic Trading System')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--tickers', nargs='+', default=['AAPL', 'MSFT', 'SPY', 'QQQ', 'IWM'],
                       help='List of ticker symbols')
    parser.add_argument('--start', type=str, default='2020-01-01',
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default='2024-01-01',
                       help='End date (YYYY-MM-DD)')
    parser.add_argument('--benchmark', type=str, default='SPY',
                       help='Benchmark ticker')
    parser.add_argument('--method', type=str, default='sharpe',
                       choices=['sharpe', 'mean_variance', 'risk_parity'],
                       help='Portfolio optimization method')
    parser.add_argument('--rebalance', type=str, default='monthly',
                       choices=['daily', 'weekly', 'monthly', 'quarterly'],
                       help='Rebalancing frequency')
    parser.add_argument('--log-level', type=str, default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    parser.add_argument('--no-plots', action='store_true',
                       help='Skip generating plots')
    parser.add_argument('--use-legacy-backtester', action='store_true',
                       help='Use legacy backtester instead of new Portfolio class')
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(level=args.log_level, log_file='trading_pipeline.log')
    logger = logging.getLogger(__name__)
    
    try:
        # Load or create configuration
        if args.config and os.path.exists(args.config):
            logger.info(f"Loading configuration from {args.config}")
            config = TradingConfig.load(args.config)
        else:
            logger.info("Using default configuration with command line overrides")
            config = TradingConfig()
        
        # Override config with command line arguments
        config.tickers = args.tickers
        config.start_date = args.start
        config.end_date = args.end
        config.benchmark = args.benchmark
        config.optimization_method = args.method
        config.rebalance_frequency = args.rebalance
        config.use_portfolio_class = not args.use_legacy_backtester
        
        logger.info(f"Configuration: {len(config.tickers)} assets, {config.start_date} to {config.end_date}")
        logger.info(f"Optimization: {config.optimization_method}, Rebalance: {config.rebalance_frequency}")
        
        # Initialize and run pipeline
        pipeline = AlgorithmicTradingPipeline(config)
        results = pipeline.run_full_pipeline()
        
        # Print summary
        print("\n" + "="*60)
        print("PIPELINE EXECUTION SUMMARY")
        print("="*60)
        print(f"Strategy completed successfully!")
        print(f"Total Return: {results.total_return:.2%}")
        print(f"Annualized Return: {results.annualized_return:.2%}")
        print(f"Sharpe Ratio: {results.sharpe_ratio:.3f}")
        print(f"Max Drawdown: {results.max_drawdown:.2%}")
        print(f"Benchmark Return: {results.benchmark_total_return:.2%}")
        print(f"Excess Return: {results.excess_return:.2%}")
        print("="*60)
        
        # Save configuration for future reference
        config.save('last_run_config.yaml')
        logger.info("Configuration saved to last_run_config.yaml")
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()