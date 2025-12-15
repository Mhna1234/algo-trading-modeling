"""
Multi-Armed Bandit algorithms for strategy allocation.

This module provides bandit algorithms for dynamic strategy selection
without dependencies on market data or pandas.
"""

from src.bandits.base import BanditAllocator
from src.bandits.ucb import UCBBandit

__all__ = [
    'BanditAllocator',
    'UCBBandit',
]
