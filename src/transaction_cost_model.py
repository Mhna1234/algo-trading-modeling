"""
Transaction Cost Model Module

Abstract base class for transaction cost calculations.
Supports different cost models (linear, percentage, etc.).
"""

from abc import ABC, abstractmethod
from typing import Union
import pandas as pd


class TransactionCostModel(ABC):
    """
    Abstract base class for transaction cost models.
    
    Transaction costs include commissions, spreads, and market impact.
    Models can be asset-specific or global.
    """
    
    def __init__(self, base_cost_bps: float = 5.0):
        """
        Initialize with base cost in basis points.
        
        Parameters
        ----------
        base_cost_bps : float
            Base transaction cost in basis points (0.01% = 1 bps)
        """
        self.base_cost_bps = base_cost_bps
    
    @abstractmethod
    def calculate_cost(self, trade_amount: float, asset: str) -> float:
        """
        Calculate transaction cost for a trade.
        
        Parameters
        ----------
        trade_amount : float
            Dollar amount of trade (positive for buy, negative for sell)
        asset : str
            Asset ticker or 'CASH'
        
        Returns
        -------
        float
            Transaction cost in dollars
        """
        pass


class LinearTransactionCostModel(TransactionCostModel):
    """
    Simple linear cost model: cost = |trade_amount| * (base_cost_bps / 100)
    """
    
    def calculate_cost(self, trade_amount: float, asset: str) -> float:
        return abs(trade_amount) * (self.base_cost_bps / 100.0)