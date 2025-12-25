"""
Checkpoint Manager - State Persistence for Real-Time Trading

This module provides checkpointing functionality for the real-time trading system:
- Saves and loads PortfolioResult instances to/from disk
- Uses JSON serialization for portfolio state and metadata
- Supports versioning and metadata tracking
- Enables rollback and state recovery

Author: Checkpoint Manager Team
Date: December 2025
"""

from __future__ import annotations
import json
import logging
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pandas import DataFrame, Series

from .portfolio_engine import PortfolioResult

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Manages saving and loading of portfolio checkpoints for state persistence.
    
    Checkpoints allow the system to:
    - Resume trading from the last saved state
    - Rollback to previous states in case of errors
    - Maintain historical portfolio snapshots
    
    Parameters
    ----------
    checkpoint_dir : Path
        Directory to store checkpoint files
    max_checkpoints : int, default=7
        Maximum number of checkpoints to keep (auto-cleanup)
    """
    
    def __init__(self, checkpoint_dir: Path, max_checkpoints: int = 7, use_parquet: bool = True):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.max_checkpoints = max_checkpoints
        self.use_parquet = use_parquet
        
    def save_checkpoint(self, portfolio_result: PortfolioResult, 
                       checkpoint_name: Optional[str] = None) -> str:
        """
        Save a PortfolioResult as a checkpoint.
        
        Parameters
        ----------
        portfolio_result : PortfolioResult
            The portfolio result to save
        checkpoint_name : str, optional
            Custom name for the checkpoint (default: timestamp-based)
            
        Returns
        -------
        str
            Path to the saved checkpoint file
        """
        if checkpoint_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            checkpoint_name = f"checkpoint_{timestamp}"
            
        checkpoint_path = self.checkpoint_dir / f"{checkpoint_name}.json"
        
        # Convert PortfolioResult to serializable dict
        checkpoint_data = self._portfolio_result_to_dict(portfolio_result)
        
        # Add metadata
        checkpoint_data["_metadata"] = {
            "checkpoint_name": checkpoint_name,
            "created_at": datetime.now().isoformat(),
            "portfolio_result_type": "PortfolioResult",
            "version": "1.0",
            "storage_format": "json"  # Default to JSON
        }
        
        # Optionally save time series to Parquet for better compression
        if self.use_parquet:
            parquet_path = checkpoint_path.with_suffix('.parquet')
            self._save_timeseries_to_parquet(portfolio_result, parquet_path)
            
            # Update metadata and strip time series from JSON
            checkpoint_data["_metadata"]["storage_format"] = "parquet"
            checkpoint_data["_metadata"]["parquet_file"] = str(parquet_path.name)
            checkpoint_data = self._strip_timeseries_from_dict(checkpoint_data)
        
        # Save metadata to JSON
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f, indent=2, default=str)
            
        logger.info(f"Saved checkpoint: {checkpoint_path}")
        
        # Auto-cleanup old checkpoints
        self._cleanup_old_checkpoints()
        
        return str(checkpoint_path)
    
    def save_checkpoint_with_bandit(self, portfolio_result: PortfolioResult, 
                                   bandit_allocator, checkpoint_name: Optional[str] = None) -> str:
        """
        Save a PortfolioResult checkpoint including MAB state.
        
        Parameters
        ----------
        portfolio_result : PortfolioResult
            The portfolio result to save
        bandit_allocator : BanditAllocator
            The bandit algorithm whose state to save
        checkpoint_name : str, optional
            Custom name for the checkpoint (default: timestamp-based)
            
        Returns
        -------
        str
            Path to the saved checkpoint file
        """
        if checkpoint_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            checkpoint_name = f"checkpoint_{timestamp}"
            
        checkpoint_path = self.checkpoint_dir / f"{checkpoint_name}.json"
        
        # Convert PortfolioResult to serializable dict
        checkpoint_data = self._portfolio_result_to_dict(portfolio_result)
        
        # Add metadata
        checkpoint_data["_metadata"] = {
            "checkpoint_name": checkpoint_name,
            "created_at": datetime.now().isoformat(),
            "portfolio_result_type": "PortfolioResult",
            "version": "1.0",
            "storage_format": "json"  # Default to JSON
        }
        
        # Add bandit state to metadata
        bandit_state = self._serialize_bandit_state(bandit_allocator)
        checkpoint_data["_metadata"]["bandit_state"] = bandit_state
        checkpoint_data["_metadata"]["bandit_type"] = type(bandit_allocator).__name__
        
        # Optionally save time series to Parquet for better compression
        if self.use_parquet:
            parquet_path = checkpoint_path.with_suffix('.parquet')
            self._save_timeseries_to_parquet(portfolio_result, parquet_path)
            
            # Update metadata and strip time series from JSON
            checkpoint_data["_metadata"]["storage_format"] = "parquet"
            checkpoint_data["_metadata"]["parquet_file"] = str(parquet_path.name)
            checkpoint_data = self._strip_timeseries_from_dict(checkpoint_data)
        
        # Save metadata to JSON
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f, indent=2, default=str)
            
        logger.info(f"Saved checkpoint with bandit state: {checkpoint_path}")
        
        # Auto-cleanup old checkpoints
        self._cleanup_old_checkpoints()
        
        return str(checkpoint_path)
    
    def load_checkpoint_with_bandit(self, checkpoint_name: str, bandit_allocator=None):
        """
        Load a PortfolioResult checkpoint and optionally restore bandit state.
        
        Parameters
        ----------
        checkpoint_name : str
            Name of the checkpoint to load (without .json extension)
        bandit_allocator : BanditAllocator, optional
            The bandit algorithm to restore state to
            
        Returns
        -------
        PortfolioResult
            The loaded portfolio result
        """
        checkpoint_path = self.checkpoint_dir / f"{checkpoint_name}.json"
        
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
            
        with open(checkpoint_path, 'r') as f:
            checkpoint_data = json.load(f)
            
        # Validate metadata
        metadata = checkpoint_data.pop("_metadata", {})
        if metadata.get("portfolio_result_type") != "PortfolioResult":
            raise ValueError(f"Invalid checkpoint type: {metadata.get('portfolio_result_type')}")
        
        # Load time series from Parquet if available
        if self.use_parquet and metadata.get("storage_format") == "parquet":
            parquet_filename = metadata.get("parquet_file")
            if parquet_filename:
                parquet_path = self.checkpoint_dir / parquet_filename
                if parquet_path.exists():
                    timeseries_data = self._load_timeseries_from_parquet(parquet_path)
                    # Merge Parquet data back into checkpoint_data
                    checkpoint_data.update(timeseries_data)
                else:
                    logger.warning(f"Parquet file not found: {parquet_path}")
        
        # Restore bandit state if available and requested
        if bandit_allocator and "bandit_state" in metadata:
            expected_type = metadata.get("bandit_type")
            if type(bandit_allocator).__name__ == expected_type:
                self._deserialize_bandit_state(bandit_allocator, metadata["bandit_state"])
                logger.info(f"Restored bandit state for {expected_type}")
            else:
                logger.warning(f"Bandit type mismatch: expected {expected_type}, got {type(bandit_allocator).__name__}")
            
        logger.info(f"Loaded checkpoint: {checkpoint_path}")
        
        # Convert back to PortfolioResult
        # Filter out summary keys that may be present from Parquet stripping
        filtered_data = {k: v for k, v in checkpoint_data.items() if not k.endswith('_summary')}
        return self._dict_to_portfolio_result(filtered_data)
        """
        Load a PortfolioResult from a checkpoint.
        
        Parameters
        ----------
        checkpoint_name : str
            Name of the checkpoint to load (without .json extension)
            
        Returns
        -------
        PortfolioResult
            The loaded portfolio result
        """
        checkpoint_path = self.checkpoint_dir / f"{checkpoint_name}.json"
        
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
            
        with open(checkpoint_path, 'r') as f:
            checkpoint_data = json.load(f)
            
        # Validate metadata
        metadata = checkpoint_data.pop("_metadata", {})
        if metadata.get("portfolio_result_type") != "PortfolioResult":
            raise ValueError(f"Invalid checkpoint type: {metadata.get('portfolio_result_type')}")
        
        # Load time series from Parquet if available
        if self.use_parquet and metadata.get("storage_format") == "parquet":
            parquet_filename = metadata.get("parquet_file")
            if parquet_filename:
                parquet_path = self.checkpoint_dir / parquet_filename
                if parquet_path.exists():
                    timeseries_data = self._load_timeseries_from_parquet(parquet_path)
                    # Merge Parquet data back into checkpoint_data
                    checkpoint_data.update(timeseries_data)
                else:
                    logger.warning(f"Parquet file not found: {parquet_path}")
            
        logger.info(f"Loaded checkpoint: {checkpoint_path}")
        
        # Convert back to PortfolioResult
        # Filter out summary keys that may be present from Parquet stripping
        filtered_data = {k: v for k, v in checkpoint_data.items() if not k.endswith('_summary')}
        return self._dict_to_portfolio_result(filtered_data)
    
    def list_checkpoints(self) -> list[str]:
        """
        List all available checkpoint names.
        
        Returns
        -------
        list[str]
            List of checkpoint names (without .json extension)
        """
        checkpoint_files = list(self.checkpoint_dir.glob("*.json"))
        return [f.stem for f in checkpoint_files]
    
    def get_latest_checkpoint(self) -> Optional[str]:
        """
        Get the name of the most recent checkpoint.
        
        Returns
        -------
        str or None
            Name of latest checkpoint, or None if no checkpoints exist
        """
        checkpoints = self.list_checkpoints()
        if not checkpoints:
            return None
            
        # Sort by timestamp in filename (assuming format: checkpoint_YYYYMMDD_HHMMSS)
        checkpoints.sort(reverse=True)
        return checkpoints[0]
    
    def _save_timeseries_to_parquet(self, portfolio_result: PortfolioResult, parquet_path: Path):
        """Save time series data to Parquet format."""
        timeseries_data = {
            'equity_curve': portfolio_result.equity_curve,
            'weights_history': portfolio_result.weights_history,
            'returns_series': portfolio_result.returns_series,
            'rolling_metrics': portfolio_result.rolling_metrics,
            'position_pnl': portfolio_result.position_pnl,
            'drawdown_series': portfolio_result.drawdown_series,
            'turnover_history': portfolio_result.turnover_history,
            'transaction_costs': portfolio_result.transaction_costs,
            'slippage_costs': portfolio_result.slippage_costs,
            'cash_history': portfolio_result.cash_history,
            'trades_history': portfolio_result.trades_history
        }
        
        # Combine all time series into a single DataFrame for efficient storage
        combined_df = self._combine_timeseries_to_dataframe(timeseries_data)
        combined_df.to_parquet(parquet_path, engine='pyarrow', compression='snappy')
    
    def _combine_timeseries_to_dataframe(self, timeseries_data: Dict[str, Any]) -> DataFrame:
        """Combine all time series into a single DataFrame for Parquet storage."""
        # Start with equity_curve as the base (Series)
        base_series = timeseries_data['equity_curve']
        combined_data = {'equity_curve': base_series}
        
        # Add other Series
        series_keys = ['returns_series', 'drawdown_series', 'turnover_history', 
                      'transaction_costs', 'slippage_costs', 'cash_history']
        for key in series_keys:
            if key in timeseries_data:
                combined_data[key] = timeseries_data[key]
        
        # Convert Series to DataFrame
        df = DataFrame(combined_data)
        
        # Add DataFrames as additional columns (flatten them)
        dataframe_keys = ['weights_history', 'trades_history', 'rolling_metrics', 'position_pnl']
        for key in dataframe_keys:
            if key in timeseries_data and not timeseries_data[key].empty:
                # Flatten DataFrame columns into the main DataFrame
                for col in timeseries_data[key].columns:
                    df[f"{key}_{col}"] = timeseries_data[key][col]
        
        return df
    
    def _strip_timeseries_from_dict(self, checkpoint_data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove time series data from dict when using Parquet storage."""
        timeseries_keys = [
            'equity_curve', 'weights_history', 'returns_series', 'rolling_metrics',
            'position_pnl', 'drawdown_series', 'turnover_history', 'transaction_costs',
            'slippage_costs', 'cash_history', 'trades_history'
        ]
        
        for key in timeseries_keys:
            if key in checkpoint_data:
                # Keep only a summary for reference
                if hasattr(checkpoint_data[key], '__len__'):
                    checkpoint_data[f"{key}_summary"] = {
                        "length": len(checkpoint_data[key]),
                        "date_range": [str(checkpoint_data[key].index.min()), str(checkpoint_data[key].index.max())] if hasattr(checkpoint_data[key], 'index') else None
                    }
                del checkpoint_data[key]
        
        return checkpoint_data
    
    def _load_timeseries_from_parquet(self, parquet_path: Path) -> Dict[str, Any]:
        """Load time series data from Parquet file."""
        combined_df = pd.read_parquet(parquet_path, engine='pyarrow')
        return self._split_dataframe_to_timeseries(combined_df)
    
    def _split_dataframe_to_timeseries(self, combined_df: DataFrame) -> Dict[str, Any]:
        """Split combined DataFrame back into individual time series."""
        result = {}
        
        # Extract Series
        series_keys = ['equity_curve', 'returns_series', 'drawdown_series', 'turnover_history', 
                      'transaction_costs', 'slippage_costs', 'cash_history']
        for key in series_keys:
            if key in combined_df.columns:
                result[key] = combined_df[key]
        
        # Extract DataFrames
        dataframe_keys = ['weights_history', 'trades_history', 'rolling_metrics', 'position_pnl']
        for key in dataframe_keys:
            # Find columns that start with this key
            matching_cols = [col for col in combined_df.columns if col.startswith(f"{key}_")]
            if matching_cols:
                # Extract the original column names
                original_cols = [col.replace(f"{key}_", "") for col in matching_cols]
                df_data = combined_df[matching_cols]
                df_data.columns = original_cols
                result[key] = df_data
        
        return result
    
    def _portfolio_result_to_dict(self, portfolio_result: PortfolioResult) -> Dict[str, Any]:
        """Convert PortfolioResult to a JSON-serializable dictionary."""
        result_dict = asdict(portfolio_result)
        
        # Convert pandas objects to JSON-serializable format
        for key, value in result_dict.items():
            if isinstance(value, Series):
                # Convert Series to dict with string keys
                result_dict[key] = {str(k): v for k, v in value.items()}
            elif isinstance(value, DataFrame):
                # Convert DataFrame to dict with string index
                result_dict[key] = {str(idx): row.to_dict() for idx, row in value.iterrows()}
            elif isinstance(value, dict):
                # Handle nested dicts (like summary_metrics)
                result_dict[key] = value
                
        return result_dict
    
    def _dict_to_portfolio_result(self, data: Dict[str, Any]) -> PortfolioResult:
        """Convert dictionary back to PortfolioResult."""
        # Convert dicts back to pandas objects
        for key, value in data.items():
            if key in ['equity_curve', 'returns_series', 'drawdown_series', 
                      'turnover_history', 'transaction_costs', 'slippage_costs', 'cash_history']:
                if isinstance(value, dict):
                    # Convert string keys back to Timestamps for Series
                    data[key] = Series({pd.Timestamp(k): v for k, v in value.items()})
                # If it's already a Series (from Parquet), keep it as is
            elif key in ['weights_history', 'trades_history', 'rolling_metrics', 
                        'position_pnl', 'benchmark_comparison']:
                if isinstance(value, dict) and value:  # Check if it's a non-empty dict
                    # Convert string index back to Timestamps for DataFrame
                    df_data = {pd.Timestamp(idx): row_data for idx, row_data in value.items()}
                    data[key] = DataFrame.from_dict(df_data, orient='index')
                elif isinstance(value, DataFrame):
                    # Already a DataFrame (from Parquet), keep it as is
                    pass
                else:
                    data[key] = DataFrame()
            # summary_metrics remains as dict
            
        return PortfolioResult(**data)
    
    def _cleanup_old_checkpoints(self):
        """Remove old checkpoints to maintain max_checkpoints limit."""
        checkpoints = sorted(
            self.checkpoint_dir.glob("*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        if len(checkpoints) > self.max_checkpoints:
            for old_checkpoint in checkpoints[self.max_checkpoints:]:
                # Remove JSON file
                old_checkpoint.unlink()
                logger.info(f"Removed old checkpoint: {old_checkpoint}")
                
                # Also remove associated Parquet file if it exists
                parquet_file = old_checkpoint.with_suffix('.parquet')
                if parquet_file.exists():
                    parquet_file.unlink()
                    logger.info(f"Removed old parquet file: {parquet_file}")
    
    def _serialize_bandit_state(self, bandit) -> Dict[str, Any]:
        """Serialize bandit algorithm state for persistence."""
        bandit_type = type(bandit).__name__
        
        if bandit_type == "UCBBandit":
            return {
                "counts": bandit.counts,
                "values": bandit.values,
                "total_selections": bandit.total_selections,
                "exploration_constant": bandit.exploration_constant
            }
        elif bandit_type == "ThompsonSamplingBandit":
            return {
                "counts": bandit.counts,
                "sums": bandit.sums,
                "prior_mean": bandit.prior_mean,
                "prior_std": bandit.prior_std,
                "known_reward_std": bandit.known_reward_std,
                "random_seed": bandit._random_seed
            }
        elif bandit_type == "EXP3Bandit":
            return {
                "weights": bandit.weights,
                "gamma": bandit.gamma,
                "total_selections": bandit.total_selections
            }
        else:
            raise ValueError(f"Unsupported bandit type for serialization: {bandit_type}")
    
    def _deserialize_bandit_state(self, bandit, state: Dict[str, Any]):
        """Restore bandit algorithm state from serialized data."""
        bandit_type = type(bandit).__name__
        
        if bandit_type == "UCBBandit":
            bandit.counts = state["counts"]
            bandit.values = state["values"]
            bandit.total_selections = state["total_selections"]
            bandit.exploration_constant = state["exploration_constant"]
        elif bandit_type == "ThompsonSamplingBandit":
            import random
            bandit.counts = state["counts"]
            bandit.sums = state["sums"]
            bandit.prior_mean = state["prior_mean"]
            bandit.prior_std = state["prior_std"]
            bandit.known_reward_std = state["known_reward_std"]
            bandit._random_seed = state["random_seed"]
            bandit.random_state = random.Random(state["random_seed"])
        elif bandit_type == "EXP3Bandit":
            bandit.weights = state["weights"]
            bandit.gamma = state["gamma"]
            bandit.total_selections = state["total_selections"]
        else:
            raise ValueError(f"Unsupported bandit type for deserialization: {bandit_type}")