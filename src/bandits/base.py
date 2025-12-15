"""
Base class and protocol for Multi-Armed Bandit algorithms.

This module defines the interface that all bandit algorithms must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BanditAllocator(ABC):
    """
    Abstract base class for Multi-Armed Bandit algorithms.
    
    A bandit allocator learns which arms (strategies) to select based on
    observed rewards, balancing exploration (trying uncertain arms) with
    exploitation (selecting proven arms).
    
    This class has ZERO dependencies on market data, pandas, or trading logic.
    It operates purely on arm indices and scalar rewards.
    
    Attributes
    ----------
    n_arms : int
        Number of arms (strategies) available for selection
        
    Examples
    --------
    >>> from src.bandits import UCBBandit
    >>> bandit = UCBBandit(n_arms=5)
    >>> arm = bandit.select_arm(t=1)  # Select an arm
    >>> bandit.update(arm=arm, reward=0.15)  # Update with observed reward
    """
    
    def __init__(self, n_arms: int):
        """
        Initialize the bandit allocator.
        
        Parameters
        ----------
        n_arms : int
            Number of arms available for selection. Must be >= 2.
            
        Raises
        ------
        ValueError
            If n_arms < 2
        """
        if n_arms < 2:
            raise ValueError(f"n_arms must be >= 2, got {n_arms}")
        self.n_arms = n_arms
    
    @abstractmethod
    def select_arm(self, t: int) -> int:
        """
        Select an arm to play at time step t.
        
        Parameters
        ----------
        t : int
            Current time step (number of selections made so far).
            Used for exploration bonus in some algorithms.
            
        Returns
        -------
        int
            Index of selected arm in range [0, n_arms-1]
            
        Notes
        -----
        This method should be deterministic for reproducibility in backtests.
        """
        pass
    
    @abstractmethod
    def update(self, arm: int, reward: float) -> None:
        """
        Update bandit statistics after observing reward for selected arm.
        
        Parameters
        ----------
        arm : int
            Index of arm that was selected, in range [0, n_arms-1]
        reward : float
            Observed reward (can be negative, positive, or zero).
            Typically a risk-adjusted return metric (e.g., Sharpe ratio).
            
        Raises
        ------
        ValueError
            If arm is out of bounds [0, n_arms-1]
            
        Notes
        -----
        This method should update internal statistics (means, counts, etc.)
        but should NOT perform any I/O or side effects beyond updating state.
        """
        if not 0 <= arm < self.n_arms:
            raise ValueError(f"arm must be in [0, {self.n_arms-1}], got {arm}")
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get current internal state for serialization/persistence.
        
        Returns
        -------
        dict
            Dictionary containing all state needed to restore the bandit.
            At minimum should include 'n_arms' and algorithm-specific statistics.
            
        Notes
        -----
        This enables saving bandit state between backtest runs or
        for deployment in production systems.
        """
        return {'n_arms': self.n_arms}
    
    def set_state(self, state: Dict[str, Any]) -> None:
        """
        Restore internal state from serialized dictionary.
        
        Parameters
        ----------
        state : dict
            Dictionary previously returned by get_state()
            
        Raises
        ------
        ValueError
            If state is invalid or incompatible with current instance
            
        Notes
        -----
        This enables loading bandit state from previous runs.
        """
        if state.get('n_arms') != self.n_arms:
            raise ValueError(
                f"State n_arms={state.get('n_arms')} does not match "
                f"current n_arms={self.n_arms}"
            )
    
    def reset(self) -> None:
        """
        Reset bandit to initial state (forget all observations).
        
        Useful for:
        - Starting a new backtest run
        - Testing with fresh state
        - Handling regime changes that invalidate past observations
        """
        pass  # Subclasses should implement if stateful
