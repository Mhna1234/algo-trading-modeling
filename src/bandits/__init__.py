"""
Multi-Armed Bandit algorithms for strategy allocation.

This module provides bandit algorithms for dynamic strategy selection
without dependencies on market data or pandas.
"""

from src.bandits.base import BanditAllocator

from src.bandits.ucb import UCBBandit
from src.bandits.thompson import ThompsonSamplingBandit
from src.bandits.exp3 import EXP3Bandit
from src.bandits.epsilon_greedy import EpsilonGreedy

__all__ = [
    'BanditAllocator',
    'UCBBandit',
    'ThompsonSamplingBandit',
    'EXP3Bandit',
    'EpsilonGreedy',
]
