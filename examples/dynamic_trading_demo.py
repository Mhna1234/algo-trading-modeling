"""
Dynamic Trading Demo - Unified Real-Time Trading Platform
==========================================================

This demo provides a unified interface for different trading modes:
- BACKTEST: Traditional batch backtesting (existing functionality)
- SIMULATION: Historical date replay with state persistence
- LIVE: Real-time trading with daily updates (future)

The demo integrates checkpoint management for seamless transitions between modes
and maintains all existing functionality while adding real-time capabilities.

Configuration:
- Strategies: 12 benchmark + MAB allocation
- Data: Full historical period (2015-2024)
- Rebalancing: Monthly (configurable)
- Initial capital: $100,000
- Transaction costs: 0.1%
- Checkpointing: Enabled for simulation/live modes

Output:
- All results stored in results/ folder
- NAV curves, metrics, and checkpoint files
- Comprehensive logging and status reports

Author: Dynamic Trading Demo
Date: December 2025
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union
import logging
import argparse

# Import project modules
from src.data_loader import load_preprocessed_data
from src.portfolio_engine import PortfolioEngine, PortfolioResult
from src.signal_generator import Strategy
from src.optimizer import PortfolioOptimizer
from src.demo_results_aggregator import DemoResultsAggregator
from src.strategies import (
    BuyAndHoldStrategy,
    EqualWeightStrategy,
    QuintileFactorStrategy,
    QuintileLowVolatilityStrategy,
    MeanReversionStrategy,
    GlobalMinimumVarianceStrategy,
    InverseVolatilityStrategy,
    RiskParityStrategy,
    MaximumDiversificationStrategy,
    MaximumDecorrelationStrategy,
    SharpeMaximizationStrategy,
    CVaRMinimizationStrategy
)
from src.strategies.bandit_strategy_wrapper import BanditStrategyWrapper
from src.bandits.ucb import UCBBandit
from src.bandits.thompson import ThompsonSamplingBandit
from src.bandits.exp3 import EXP3Bandit
from src.checkpoint_manager import CheckpointManager
from src.daily_trading_engine import DailyTradingEngine
from src.config_loader import load_trading_config, TradingConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('results/dynamic_trading_demo.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Set plot style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)

# ============================================================================
# CONFIGURATION
# ============================================================================

def load_config(mode: str = 'simulation') -> TradingConfig:
    """
    Load configuration from YAML file.
    
    Args:
        mode: Override the mode from config file
        
    Returns:
        TradingConfig: Configuration object
    """
    config = load_trading_config()
    config.mode = mode  # Allow command line override
    return config

# ============================================================================
# UNIFIED TRADING DEMO CLASS
# ============================================================================

class DynamicTradingDemo:
    """
    Unified trading demo supporting multiple execution modes.

    This class provides a single interface for:
    - Traditional backtesting
    - Historical simulation with checkpoints
    - Real-time trading (future)
    """

    def __init__(self, config: TradingConfig):
        self.config = config
        self.checkpoint_manager = CheckpointManager(self.config.checkpoint_dir)
        self.results_dir = Path(self.config.results_dir)
        self.results_dir.mkdir(exist_ok=True)

        # Initialize components
        self.portfolio_engine = None
        self.strategies = []
        self.bandit = None
        self.results_aggregator = DemoResultsAggregator()

        logger.info(f"Initialized Dynamic Trading Demo in {config.mode} mode")

    def load_data(self) -> pd.DataFrame:
        """Load and prepare market data."""
        logger.info("Loading preprocessed data...")
        full_data, price_data = load_preprocessed_data()

        # Filter date range
        price_data = price_data.loc[self.config.start_date:self.config.end_date]

        logger.info(f"Loaded data: {len(price_data)} periods, {len(price_data.columns)} assets")
        return price_data

    def setup_strategies(self, data: pd.DataFrame):
        """Initialize trading strategies."""
        logger.info("Setting up trading strategies...")

        # Create signal generator
        signal_gen = Strategy(data)

        # Create optimizer
        optimizer = PortfolioOptimizer()

        # Initialize individual strategies
        strategy_classes = [
            BuyAndHoldStrategy,
            EqualWeightStrategy,
            QuintileFactorStrategy,
            QuintileLowVolatilityStrategy,
            MeanReversionStrategy,
            GlobalMinimumVarianceStrategy,
            InverseVolatilityStrategy,
            RiskParityStrategy,
            MaximumDiversificationStrategy,
            MaximumDecorrelationStrategy,
            SharpeMaximizationStrategy,
            CVaRMinimizationStrategy
        ]

        self.strategies = []
        for strategy_class in strategy_classes:
            strategy = strategy_class(signal_gen, optimizer)
            self.strategies.append(strategy)

        logger.info(f"Initialized {len(self.strategies)} strategies")

        # Setup bandit wrapper if enabled
        if self.config.use_bandit_wrapper:
            # Get bandit class based on type
            bandit_classes = {
                'ucb': UCBBandit,
                'thompson': ThompsonSamplingBandit,
                'exp3': EXP3Bandit
            }
            bandit_class = bandit_classes.get(self.config.bandit_type, UCBBandit)
            self.bandit = bandit_class(n_arms=len(self.strategies))

            # Create bandit strategy wrapper
            self.bandit_strategy = BanditStrategyWrapper(
                child_strategies=self.strategies,
                bandit_allocator=self.bandit,
                burn_in_periods=self.config.burn_in_periods
            )
            logger.info(f"Enabled {self.config.bandit_type.upper()} bandit wrapper")

    def run_backtest_mode(self, data: pd.DataFrame) -> PortfolioResult:
        """Run traditional batch backtest."""
        logger.info("Running backtest mode...")

        # Use bandit strategy if enabled, otherwise equal weight
        if self.config.use_bandit_wrapper:
            strategy = self.bandit_strategy
        else:
            # Create equal weight strategy for comparison
            strategy = EqualWeightStrategy(Strategy(data), PortfolioOptimizer())

        # Initialize portfolio engine
        self.portfolio_engine = PortfolioEngine(
            prices=data,
            initial_capital=self.config.initial_capital,
            transaction_cost_bps=self.config.transaction_cost_bps
        )

        # Run backtest
        result = self.portfolio_engine.run_backtest(
            strategy_wrapper=strategy,
            start_date=self.config.start_date,
            end_date=self.config.end_date,
            rebalance_freq=self.config.rebalance_frequency
        )

        logger.info("Backtest completed successfully")
        return result

    def run_simulation_mode(self, data: pd.DataFrame) -> PortfolioResult:
        """Run historical simulation with daily replay and checkpoints."""
        logger.info("Running simulation mode...")

        # Reset any existing checkpoints for clean simulation
        import shutil
        if self.checkpoint_manager.checkpoint_dir.exists():
            shutil.rmtree(self.checkpoint_manager.checkpoint_dir)
        self.checkpoint_manager.checkpoint_dir.mkdir(exist_ok=True)

        # Initialize daily trading engine
        engine = DailyTradingEngine(
            data_dir='data',
            checkpoint_dir=str(self.config.checkpoint_dir),
            strategy_config={
                'bandit_type': self.config.bandit_type,
                'burn_in_periods': self.config.burn_in_periods
            }
        )

        # First, initialize from a backtest to get starting point
        logger.info("Initializing simulation from backtest...")
        backtest_result = self.run_backtest_mode(data)
        engine.initialize_from_backtest(backtest_result, self.bandit)

        # Get all trading dates after backtest end
        backtest_end_date = backtest_result.equity_curve.index[-1]
        remaining_dates = data.index[data.index > backtest_end_date]

        if len(remaining_dates) == 0:
            logger.info("No additional dates to simulate")
            return backtest_result

        logger.info(f"Simulating {len(remaining_dates)} additional trading periods")

        # Run simulation period by period
        for i, current_date in enumerate(remaining_dates):
            logger.info(f"Processing period {i+1}/{len(remaining_dates)}: {current_date}")

            try:
                # Execute daily update
                result = engine.run_daily_update(self.bandit)

                if result is None:
                    logger.info(f"No update needed for {current_date}")
                    continue

                # Optional: pause for simulation speed control
                if self.config.simulation_speed > 0:
                    time.sleep(self.config.simulation_speed)

            except Exception as e:
                logger.error(f"Error processing {current_date}: {e}")
                continue

        # Load final result from checkpoint
        checkpoint_files = list(self.checkpoint_manager.checkpoint_dir.glob("checkpoint_*.json"))
        if checkpoint_files:
            latest_checkpoint = max(checkpoint_files, key=lambda x: x.stat().st_mtime)
            checkpoint_name = latest_checkpoint.stem
            final_result, _ = self.checkpoint_manager.load_checkpoint_with_bandit(checkpoint_name)
        else:
            final_result = backtest_result

        logger.info("Simulation completed successfully")
        return final_result

    def run_live_mode(self, data: pd.DataFrame) -> PortfolioResult:
        """Run real-time trading mode using DailyTradingEngine."""
        logger.info("Running live trading mode...")

        # Initialize daily trading engine
        engine = DailyTradingEngine(
            data_dir='data',
            checkpoint_dir=str(self.config.checkpoint_dir),
            strategy_config={
                'bandit_type': self.config.bandit_type,
                'burn_in_periods': self.config.burn_in_periods
            }
        )

        # Attempt to run daily update
        result = engine.run_daily_update(self.bandit)

        if result is None:
            logger.warning("No live update performed - check for new data or initialize from backtest/simulation first")
            # Fall back to loading latest checkpoint
            checkpoint_files = list(self.checkpoint_manager.checkpoint_dir.glob("checkpoint_*.json"))
            if checkpoint_files:
                latest_checkpoint = max(checkpoint_files, key=lambda x: x.stat().st_mtime)
                checkpoint_name = latest_checkpoint.stem
                checkpoint_result, _ = self.checkpoint_manager.load_checkpoint_with_bandit(checkpoint_name)
                logger.info("Loaded latest checkpoint as fallback")
                return checkpoint_result
            else:
                logger.error("No checkpoint available - run backtest or simulation first")
                raise ValueError("Live mode requires existing checkpoint from backtest or simulation")

        logger.info("Live trading update completed")
        return result

    def run(self) -> PortfolioResult:
        """Main execution method."""
        start_time = time.time()

        # Load data
        data = self.load_data()

        # Setup strategies
        self.setup_strategies(data)

        # Execute based on mode
        if self.config.mode == 'backtest':
            result = self.run_backtest_mode(data)
        elif self.config.mode == 'simulation':
            result = self.run_simulation_mode(data)
        elif self.config.mode == 'live':
            result = self.run_live_mode(data)
        else:
            raise ValueError(f"Unknown mode: {self.config.mode}")

        # Generate reports
        self.generate_reports(result)

        elapsed = time.time() - start_time
        logger.info(".2f")

        return result

    def generate_reports(self, result: PortfolioResult):
        """Generate comprehensive reports and visualizations."""
        logger.info("Generating reports...")

        # Save results to CSV
        result.equity_curve.to_csv(self.results_dir / 'dynamic_trading_equity_curve.csv')
        if hasattr(result, 'weights_history') and not result.weights_history.empty:
            result.weights_history.to_csv(self.results_dir / 'dynamic_trading_weights.csv')

        # Generate performance summary from result
        summary_data = {
            'total_return': result.summary_metrics.get('total_return', 0),
            'sharpe_ratio': result.summary_metrics.get('sharpe_ratio', 0),
            'max_drawdown': result.summary_metrics.get('max_drawdown', 0),
            'volatility': result.summary_metrics.get('volatility', 0),
            'final_value': result.equity_curve.iloc[-1]
        }
        summary = pd.DataFrame([summary_data])
        summary.to_csv(self.results_dir / 'dynamic_trading_summary.csv')

        # Create visualizations
        self.create_plots(result)

        logger.info(f"Reports saved to {self.results_dir}")

    def create_plots(self, result: PortfolioResult):
        """Create performance visualization plots."""
        # Equity curve
        plt.figure(figsize=(12, 6))
        result.equity_curve.plot()
        plt.title('Dynamic Trading Demo - Portfolio Equity Curve')
        plt.ylabel('Portfolio Value ($)')
        plt.savefig(self.results_dir / 'dynamic_trading_equity_curve.png')
        plt.close()

        # Strategy weights over time (if available)
        if not result.weights_history.empty:
            plt.figure(figsize=(12, 8))
            result.weights_history.plot.area(alpha=0.7)
            plt.title('Dynamic Trading Demo - Strategy Weights Over Time')
            plt.ylabel('Weight')
            plt.savefig(self.results_dir / 'dynamic_trading_weights.png')
            plt.close()

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main entry point with command line argument parsing."""
    parser = argparse.ArgumentParser(description='Dynamic Trading Demo')
    parser.add_argument('--mode', choices=['backtest', 'simulation', 'live'],
                       help='Execution mode (overrides config file)')
    parser.add_argument('--bandit', choices=['ucb', 'thompson', 'exp3'],
                       help='Bandit algorithm type (overrides config file)')
    parser.add_argument('--no-bandit', action='store_true',
                       help='Disable bandit wrapper (use equal weight)')
    parser.add_argument('--config', default='config/trading_config.yaml',
                       help='Path to configuration file')

    args = parser.parse_args()

    # Load configuration from YAML
    try:
        config = load_trading_config(args.config)
        logger.info(f"Loaded configuration from {args.config}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return

    # Apply command line overrides
    if args.mode:
        config.mode = args.mode
    if args.bandit:
        config.bandit_type = args.bandit
    if args.no_bandit:
        config.use_bandit_wrapper = False

    logger.info(f"Running in {config.mode} mode with {config.bandit_type} bandit")

    # Initialize and run demo
    demo = DynamicTradingDemo(config)
    result = demo.run()

    # Print final summary
    print("\n" + "="*60)
    print("DYNAMIC TRADING DEMO COMPLETED")
    print("="*60)
    print(f"Mode: {config.mode.upper()}")
    print(f"Final Portfolio Value: ${result.equity_curve.iloc[-1]:,.2f}")
    print(f"Total Return: {result.summary_metrics['total_return']:.2%}")
    print(f"Sharpe Ratio: {result.summary_metrics['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {result.summary_metrics['max_drawdown']:.2%}")
    print(f"Results saved to: {config.results_dir}")
    print("="*60)

if __name__ == "__main__":
    main()