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
    
    def __init__(self, checkpoint_dir: Path, max_checkpoints: int = 7):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.max_checkpoints = max_checkpoints
        
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
            "version": "1.0"
        }
        
        # Save to JSON
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f, indent=2, default=str)
            
        logger.info(f"Saved checkpoint: {checkpoint_path}")
        
        # Auto-cleanup old checkpoints
        self._cleanup_old_checkpoints()
        
        return str(checkpoint_path)
    
    def load_checkpoint(self, checkpoint_name: str) -> PortfolioResult:
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
            
        logger.info(f"Loaded checkpoint: {checkpoint_path}")
        
        # Convert back to PortfolioResult
        return self._dict_to_portfolio_result(checkpoint_data)
    
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
                # Convert string keys back to Timestamps for Series
                data[key] = Series({pd.Timestamp(k): v for k, v in value.items()})
            elif key in ['weights_history', 'trades_history', 'rolling_metrics', 
                        'position_pnl', 'benchmark_comparison']:
                if value:
                    # Convert string index back to Timestamps for DataFrame
                    df_data = {pd.Timestamp(idx): row_data for idx, row_data in value.items()}
                    data[key] = DataFrame.from_dict(df_data, orient='index')
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
                old_checkpoint.unlink()
                logger.info(f"Removed old checkpoint: {old_checkpoint}")