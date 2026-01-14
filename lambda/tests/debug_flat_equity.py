"""
Debug script to investigate "Flat Equity" issue.
PHASE 2: Deep Dive into Engine Execution.

Usage:
    python lambda/tests/debug_flat_equity.py
"""

import sys
import os
import pandas as pd
import numpy as np
import logging

# Adjust path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.signal_generator import Strategy
from src.strategies.benchmarks.buy_and_hold import BuyAndHoldBenchmark
from src.portfolio_engine import PortfolioEngine

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_debug():
    # 1. Load Data Locally
    csv_path = 'debug_prices.csv'
    if not os.path.exists(csv_path):
        logger.error(f"{csv_path} not found. Run Phase 1 first (fetch data).")
        return

    logger.info(f"Loading {csv_path}...")
    prices = pd.read_csv(csv_path, index_col='date', parse_dates=True)
    logger.info(f"Loaded prices: {prices.shape}")
    logger.info(f"Date Range: {prices.index[0]} to {prices.index[-1]}")
    
    # Fill NA just in case (engine might drop them)
    prices = prices.fillna(method='ffill').dropna(axis=1, how='all')
    
    # 2. Setup Strategy
    logger.info("Initializing Strategy...")
    signal_gen = Strategy(prices)
    strategy = BuyAndHoldBenchmark(signal_gen)
    
    # Check signal generator directly
    first_date = prices.index[0]
    logger.info(f"Checking signals for {first_date}...")
    try:
        # BuyAndHoldBenchmark wraps a Strategy (signal_generator). 
        # We should call generate_signals on the INNER strategy if we want to test it,
        # but BuyAndHold doesn't use dynamic signals (just assets list).
        pass

    except Exception as e:
        logger.error(f"Signal generation failed: {e}")
        import traceback
        traceback.print_exc()

    # 3. Setup Engine
    logger.info("Initializing Portfolio Engine...")
    portfolio = PortfolioEngine(
        prices=prices,
        initial_capital=1_000_000,
        transaction_cost_bps=10,
        rebalance_freq='M' 
    )
    
    # 4. Run Backtest with verbose inspection
    logger.info("Running Backtest...")
    
    try:
        # Run standard backtest
        result = portfolio.run_backtest(
            strategy_wrapper=strategy,
            start_date=prices.index[0],
            end_date=prices.index[-1],
            soft_rebalance=True
        )
        
        # Inspect Results
        if result:
            logger.info("Backtest finished.")
            logger.info(f"Trades History Length: {len(result.trades_history)}")
            
            if not result.trades_history.empty:
                logger.info(f"First Trade:\n{result.trades_history.iloc[0]}")
            else:
                logger.error("!!! NO TRADES RECORDED !!!")
                
            logger.info(f"Equity Start: {result.equity_curve.iloc[0]}")
            logger.info(f"Equity End:   {result.equity_curve.iloc[-1]}")
            logger.info(f"Equity Std:   {result.equity_curve.std()}")
            
            # Check weights history
            logger.info(f"Weights History: {result.weights_history.shape}")
            if not result.weights_history.empty:
                logger.info("Sample Weights (first row):")
                # print non-zero weights
                row = result.weights_history.iloc[0]
                print(row[row > 0].head())
        else:
            logger.error("Backtest returned None.")

    except Exception as e:
        logger.error(f"Backtest execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_debug()
