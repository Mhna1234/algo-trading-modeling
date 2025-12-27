"""
Daily Trading Engine for Real-Time Portfolio Management

This module provides the core engine for daily trading operations:
- Load latest portfolio checkpoint
- Fetch and integrate new market data
- Execute trading decisions using MAB allocation
- Update portfolio metrics and save new checkpoint
- Handle weekends/holidays gracefully

The engine transforms the existing batch backtest system into a real-time
trading platform while maintaining all existing functionality.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, timedelta
import logging

from src.portfolio_engine import PortfolioEngine, PortfolioResult
from src.checkpoint_manager import CheckpointManager
from src.data_loader import load_preprocessed_data
from src.bandits.base import BanditAllocator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DailyTradingEngine:
    """
    Engine for daily trading operations with state persistence.

    This class orchestrates the daily trading cycle:
    1. Load latest checkpoint (portfolio state + MAB state)
    2. Check for and load new market data
    3. Execute trading decisions for new period
    4. Update portfolio and save new checkpoint

    The engine is designed to be idempotent - it can be run multiple times
    safely and will only process new data when available.
    """

    def __init__(self,
                 data_dir: str = "data",
                 checkpoint_dir: str = "checkpoints",
                 strategy_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the daily trading engine.

        Args:
            data_dir: Directory containing market data
            checkpoint_dir: Directory for checkpoint storage
            strategy_config: Configuration for trading strategies
        """
        self.data_dir = Path(data_dir)
        self.checkpoint_manager = CheckpointManager(checkpoint_dir)

        # Default strategy configuration
        self.strategy_config = strategy_config or {
            'rebalance_frequency': 'daily',
            'risk_free_rate': 0.04 / 252,  # 4% annual
            'transaction_cost': 0.001,     # 10 bps
            'max_weight': 0.2,             # Max 20% per asset
            'min_weight': -0.1,            # Max 10% short
        }

        logger.info("DailyTradingEngine initialized")
        logger.info(f"Data directory: {self.data_dir}")
        logger.info(f"Checkpoint directory: {checkpoint_dir}")

    def run_daily_update(self, bandit: BanditAllocator) -> Optional[PortfolioResult]:
        """
        Execute daily trading update cycle.

        Args:
            bandit: MAB algorithm for strategy allocation (will be updated with rewards)

        Returns:
            Updated PortfolioResult if new data was processed, None otherwise
        """
        logger.info("Starting daily trading update...")

        try:
            # Step 1: Load latest checkpoint
            checkpoint_result, loaded_bandit = self._load_latest_checkpoint(bandit)
            if checkpoint_result is None:
                logger.warning("No checkpoint found - initialize with historical backtest first")
                return None

            # Step 2: Check for new data
            new_data_available = self._check_for_new_data(checkpoint_result)
            if not new_data_available:
                logger.info("No new data available - skipping update")
                return None

            # Step 3: Load updated data
            full_data, price_data = self._load_updated_data()

            # Step 4: Determine trading period
            last_date = checkpoint_result.equity_curve.index[-1]
            new_end_date = price_data.index[-1]

            if last_date >= new_end_date:
                logger.info("No new trading days available")
                return None

            # Step 5: Execute trading for new period
            updated_result = self._execute_trading_period(
                checkpoint_result, loaded_bandit, full_data, price_data,
                last_date, new_end_date
            )

            # Step 6: Save new checkpoint
            self._save_checkpoint(updated_result, loaded_bandit)

            logger.info("Daily trading update completed successfully")
            return updated_result

        except Exception as e:
            logger.error(f"Daily trading update failed: {e}")
            raise

    def _load_latest_checkpoint(self, bandit_template: BanditAllocator) -> Tuple[Optional[PortfolioResult], Optional[BanditAllocator]]:
        """
        Load the most recent checkpoint.

        Returns:
            Tuple of (PortfolioResult, BanditAllocator) or (None, None) if no checkpoint
        """
        try:
            # Get latest checkpoint name
            checkpoint_files = list(self.checkpoint_manager.checkpoint_dir.glob("*.json"))
            if not checkpoint_files:
                return None, None

            latest_checkpoint = max(checkpoint_files, key=lambda x: x.stat().st_mtime)
            checkpoint_name = latest_checkpoint.stem  # Remove .json extension

            logger.info(f"Loading checkpoint: {checkpoint_name}")

            # Load checkpoint with bandit
            result, bandit = self.checkpoint_manager.load_checkpoint_with_bandit(checkpoint_name)

            logger.info(f"Checkpoint loaded - last date: {result.equity_curve.index[-1]}")
            return result, bandit

        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None, None

    def _check_for_new_data(self, checkpoint_result: PortfolioResult) -> bool:
        """
        Check if new data is available beyond the checkpoint date.

        Returns:
            True if new data should be processed
        """
        try:
            # Load data with update check
            _, price_data = load_preprocessed_data(
                data_dir=str(self.data_dir),
                update_if_available=True
            )

            last_checkpoint_date = checkpoint_result.equity_curve.index[-1]
            latest_data_date = price_data.index[-1]

            # Check if we have new trading days
            new_days = (price_data.index > last_checkpoint_date).sum()

            logger.info(f"Checkpoint date: {last_checkpoint_date}")
            logger.info(f"Latest data date: {latest_data_date}")
            logger.info(f"New trading days available: {new_days}")

            return new_days > 0

        except Exception as e:
            logger.error(f"Failed to check for new data: {e}")
            return False

    def _load_updated_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Load the most current market data.

        Returns:
            Tuple of (full_data, price_data)
        """
        logger.info("Checking for and loading updated market data...")

        # First update data from S3 if available
        try:
            from src.data_retrieval import update_processed_data
            update_processed_data(self.data_dir)
        except Exception as e:
            logger.warning(f"Failed to update data from S3: {e}")
            logger.info("Proceeding with existing local data")

        # Then load the (potentially updated) data
        full_data, price_data = load_preprocessed_data(
            data_dir=str(self.data_dir),
            update_if_available=False  # Data already updated above
        )
        return full_data, price_data

    def _execute_trading_period(self,
                               checkpoint_result: PortfolioResult,
                               bandit: BanditAllocator,
                               full_data: pd.DataFrame,
                               price_data: pd.DataFrame,
                               start_date: pd.Timestamp,
                               end_date: pd.Timestamp) -> PortfolioResult:
        """
        Execute trading for the new period using existing PortfolioEngine.

        This extends the existing backtest from the checkpoint date.
        """
        logger.info(f"Executing trading from {start_date} to {end_date}")

        # Filter data to new period
        period_full_data = full_data[(full_data.index > start_date) & (full_data.index <= end_date)]
        period_price_data = price_data[(price_data.index > start_date) & (price_data.index <= end_date)]

        if len(period_price_data) == 0:
            raise ValueError(f"No trading data found between {start_date} and {end_date}")

        # Create portfolio engine for the new period
        engine = PortfolioEngine(
            price_data=period_price_data,
            full_data=period_full_data,
            risk_free_rate=self.strategy_config['risk_free_rate'],
            transaction_cost=self.strategy_config['transaction_cost']
        )

        # Get child strategies and create bandit wrapper
        child_strategies = self._get_trading_strategies()
        from src.strategies.bandit_strategy_wrapper import BanditStrategyWrapper

        bandit_wrapper = BanditStrategyWrapper(
            child_strategies=child_strategies,
            bandit_allocator=bandit,
            reward_type='sharpe',
            reward_lookback=12,
            burn_in_periods=12,
            min_allocation=0.05,
            enable_soft_allocation=True
        )

        # Run the backtest for the new period using the bandit wrapper
        result = engine.run_backtest(
            strategy_wrapper=bandit_wrapper,
            start_date=last_date.strftime('%Y-%m-%d'),
            end_date=new_end_date.strftime('%Y-%m-%d'),
            initial_capital=checkpoint_result.equity_curve.iloc[-1],  # Start from last value
            soft_rebalance=True,
            drift_threshold=0.05
        )

        # Combine with checkpoint result
        combined_result = self._combine_results(checkpoint_result, result)

        return combined_result

    def _get_trading_strategies(self) -> List[Any]:
        """
        Get the trading strategies to use.

        Returns a list of BaseStrategyWrapper instances for the BanditStrategyWrapper.
        In a real implementation, these would be loaded from checkpoint or config.
        """
        # Import required classes
        from src.strategies import (
            BuyAndHoldStrategy, EqualWeightStrategy, QuintileFactorStrategy,
            QuintileLowVolatilityStrategy, MeanReversionStrategy,
            GlobalMinimumVarianceStrategy, InverseVolatilityStrategy
        )
        from src.signal_generator import SignalGenerator
        from src.optimizer import Optimizer

        # Create signal generator and optimizer
        # These would typically be loaded from config or checkpoint
        signal_generator = SignalGenerator()
        optimizer = Optimizer()

        # Create a basic set of strategies
        # In practice, these should match the strategies used in the original backtest
        strategies = [
            BuyAndHoldStrategy(signal_generator, optimizer),
            EqualWeightStrategy(signal_generator, optimizer),
            QuintileFactorStrategy(signal_generator, optimizer, lookback=63, target_quintile=5),
            QuintileLowVolatilityStrategy(signal_generator, optimizer, lookback=63, target_quintile=1),
            MeanReversionStrategy(signal_generator, optimizer, lookback=10),
            GlobalMinimumVarianceStrategy(signal_generator, optimizer, lookback=63, max_weight=0.5),
            InverseVolatilityStrategy(signal_generator, optimizer, lookback=21)
        ]

        return strategies

    def _combine_results(self,
                        checkpoint_result: PortfolioResult,
                        new_result: PortfolioResult) -> PortfolioResult:
        """
        Combine checkpoint result with new period result.

        This creates a continuous time series by appending the new results.
        """
        logger.info("Combining checkpoint and new results...")

        # Combine equity curves
        combined_equity = pd.concat([
            checkpoint_result.equity_curve,
            new_result.equity_curve
        ])

        # Combine returns
        combined_returns = pd.concat([
            checkpoint_result.returns_series,
            new_result.returns_series
        ])

        # Combine weights history
        combined_weights = pd.concat([
            checkpoint_result.weights_history,
            new_result.weights_history
        ])

        # Combine trades history
        combined_trades = pd.concat([
            checkpoint_result.trades_history,
            new_result.trades_history
        ])

        # Combine rolling metrics
        combined_rolling = pd.concat([
            checkpoint_result.rolling_metrics,
            new_result.rolling_metrics
        ])

        # Combine position P&L
        combined_pnl = pd.concat([
            checkpoint_result.position_pnl,
            new_result.position_pnl
        ])

        # Combine turnover
        combined_turnover = pd.concat([
            checkpoint_result.turnover_history,
            new_result.turnover_history
        ])

        # Combine transaction costs
        combined_txn_costs = pd.concat([
            checkpoint_result.transaction_costs,
            new_result.transaction_costs
        ])

        # Combine slippage costs
        combined_slippage = pd.concat([
            checkpoint_result.slippage_costs,
            new_result.slippage_costs
        ])

        # Combine cash history
        combined_cash = pd.concat([
            checkpoint_result.cash_history,
            new_result.cash_history
        ])

        # Update summary metrics (recalculate for combined period)
        combined_summary = self._recalculate_summary_metrics(combined_returns)

        # Create combined result
        combined_result = PortfolioResult(
            equity_curve=combined_equity,
            weights_history=combined_weights,
            trades_history=combined_trades,
            returns_series=combined_returns,
            summary_metrics=combined_summary,
            rolling_metrics=combined_rolling,
            drawdown_series=checkpoint_result.drawdown_series,  # Recalculate if needed
            position_pnl=combined_pnl,
            turnover_history=combined_turnover,
            transaction_costs=combined_txn_costs,
            slippage_costs=combined_slippage,
            cash_history=combined_cash,
            strategy_name=f"{checkpoint_result.strategy_name}_continued"
        )

        return combined_result

    def _recalculate_summary_metrics(self, returns: pd.Series) -> Dict[str, float]:
        """
        Recalculate summary metrics for combined returns series.
        """
        # Simple recalculation - in practice, use existing metrics calculation
        total_return = (1 + returns).prod() - 1
        sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        max_drawdown = (returns.cumsum() - returns.cumsum().cummax()).min()

        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'volatility': returns.std() * np.sqrt(252),
        }

    def _save_checkpoint(self, result: PortfolioResult, bandit: BanditAllocator) -> None:
        """
        Save current state as a new checkpoint.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_name = f"daily_update_{timestamp}"

        logger.info(f"Saving checkpoint: {checkpoint_name}")
        self.checkpoint_manager.save_checkpoint_with_bandit(result, bandit, checkpoint_name)

    def initialize_from_backtest(self,
                                backtest_result: PortfolioResult,
                                bandit: BanditAllocator,
                                checkpoint_name: str = "initial") -> None:
        """
        Initialize the daily trading system from a completed backtest.

        Args:
            backtest_result: Result from historical backtest
            bandit: Trained bandit algorithm
            checkpoint_name: Name for the initial checkpoint
        """
        logger.info(f"Initializing daily trading from backtest: {checkpoint_name}")
        self.checkpoint_manager.save_checkpoint_with_bandit(
            backtest_result, bandit, checkpoint_name
        )
        logger.info("Daily trading system initialized")

    def reset_system(self) -> None:
        """
        Reset the trading system to initial state by clearing all checkpoints.

        This removes all saved checkpoints and bandit state, allowing the system
        to be reinitialized from a fresh backtest.
        """
        logger.info("Resetting trading system - clearing all checkpoints...")

        try:
            # Remove all checkpoint files
            checkpoint_dir = self.checkpoint_manager.checkpoint_dir
            if checkpoint_dir.exists():
                for checkpoint_file in checkpoint_dir.glob("*.json"):
                    checkpoint_file.unlink()
                    logger.info(f"Removed checkpoint: {checkpoint_file}")

                for parquet_file in checkpoint_dir.glob("*.parquet"):
                    parquet_file.unlink()
                    logger.info(f"Removed parquet file: {parquet_file}")

            logger.info("System reset completed successfully")

        except Exception as e:
            logger.error(f"Failed to reset system: {e}")
            raise


# Example usage and testing functions
if __name__ == "__main__":
    # Example: Initialize from existing backtest
    engine = DailyTradingEngine()

    print("DailyTradingEngine created successfully")
    print("Ready for daily updates - load a checkpoint and bandit first")