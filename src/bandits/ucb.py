"""
Upper Confidence Bound (UCB1) bandit algorithm implementation.

UCB1 is a deterministic algorithm that balances exploration and exploitation
by computing upper confidence bounds for each arm's expected reward.
"""

import math
from typing import Dict, Any, List
from src.bandits.base import BanditAllocator


class UCBBandit(BanditAllocator):
    """
    Upper Confidence Bound (UCB1) bandit algorithm.
    
    UCB1 selects arms by computing an upper confidence bound for each arm:
    
        UCB_k = mean_k + c * sqrt(2 * ln(t) / n_k)
    
    Where:
    - mean_k: average reward for arm k
    - c: exploration constant (default 1.0)
    - t: total number of selections
    - n_k: number of times arm k was selected
    
    The algorithm is:
    - Deterministic (reproducible backtests)
    - Forces exploration of untried arms (they get infinite UCB)
    - Numerically stable (handles edge cases gracefully)
    - Has strong theoretical regret bounds
    
    Parameters
    ----------
    n_arms : int
        Number of arms available for selection
    exploration_constant : float, default=1.0
        Exploration bonus multiplier. Higher values encourage more exploration.
        Typical range: [0.5, 2.0]
        - 0.5: More exploitation (prefer proven arms)
        - 1.0: Balanced (recommended default)
        - 2.0: More exploration (try uncertain arms)
        
    Attributes
    ----------
    counts : List[int]
        Number of times each arm has been selected
    values : List[float]
        Average reward for each arm
    total_selections : int
        Total number of selections made
        
    Examples
    --------
    >>> bandit = UCBBandit(n_arms=3, exploration_constant=1.0)
    >>> 
    >>> # First 3 selections try each arm once
    >>> for t in range(3):
    ...     arm = bandit.select_arm(t)
    ...     print(f"Selected arm {arm}")
    ...     bandit.update(arm, reward=0.1 * (arm + 1))
    Selected arm 0
    Selected arm 1
    Selected arm 2
    >>> 
    >>> # After exploration, selects best arm (highest UCB)
    >>> arm = bandit.select_arm(3)
    >>> print(f"Best arm: {arm}")
    Best arm: 2
    """
    
    def __init__(self, n_arms: int, exploration_constant: float = 1.0):
        """
        Initialize UCB bandit.
        
        Parameters
        ----------
        n_arms : int
            Number of arms, must be >= 2
        exploration_constant : float, default=1.0
            Exploration bonus multiplier, must be > 0
            
        Raises
        ------
        ValueError
            If n_arms < 2 or exploration_constant <= 0
        """
        super().__init__(n_arms)
        
        if exploration_constant <= 0:
            raise ValueError(
                f"exploration_constant must be > 0, got {exploration_constant}"
            )
        
        self.exploration_constant = exploration_constant
        self.counts: List[int] = [0] * n_arms
        self.values: List[float] = [0.0] * n_arms
        self.total_selections: int = 0
    
    def select_arm(self, t: int) -> int:
        """
        Select arm with highest upper confidence bound.
        
        Parameters
        ----------
        t : int
            Current time step (used for exploration bonus calculation)
            
        Returns
        -------
        int
            Index of selected arm
            
        Notes
        -----
        - Untried arms (count=0) are selected first (infinite UCB)
        - After all arms tried once, selects arm with highest UCB score
        - Deterministic: same sequence of rewards produces same selections
        """
        # Force exploration: try each arm once before using UCB formula
        for arm in range(self.n_arms):
            if self.counts[arm] == 0:
                return arm
        
        # All arms tried at least once, compute UCB scores
        ucb_scores = [self._compute_ucb(arm, t) for arm in range(self.n_arms)]
        
        # Select arm with highest UCB (ties broken by lowest index)
        return int(max(range(self.n_arms), key=lambda i: ucb_scores[i]))
    
    def _compute_ucb(self, arm: int, t: int) -> float:
        """
        Compute Upper Confidence Bound for an arm.
        
        Parameters
        ----------
        arm : int
            Arm index
        t : int
            Current time step
            
        Returns
        -------
        float
            UCB score for the arm
            
        Notes
        -----
        Formula: mean + c * sqrt(2 * ln(t+1) / count)
        
        Uses t+1 to avoid log(0) when t=0. This is numerically stable.
        """
        if self.counts[arm] == 0:
            return float('inf')  # Untried arms have infinite UCB
        
        # Exploitation term: average reward
        exploitation = self.values[arm]
        
        # Exploration term: uncertainty bonus
        # Use t+1 to avoid log(0), and max(1, count) for stability
        exploration_bonus = self.exploration_constant * math.sqrt(
            2.0 * math.log(t + 1) / max(1, self.counts[arm])
        )
        
        return exploitation + exploration_bonus
    
    def update(self, arm: int, reward: float) -> None:
        """
        Update statistics for selected arm after observing reward.
        
        Parameters
        ----------
        arm : int
            Index of arm that was selected
        reward : float
            Observed reward (can be negative, positive, or zero)
            
        Raises
        ------
        ValueError
            If arm is out of bounds
            
        Notes
        -----
        Updates are numerically stable using incremental mean formula:
        
            new_mean = old_mean + (reward - old_mean) / new_count
        
        This avoids overflow and maintains precision.
        """
        super().update(arm, reward)  # Validates arm index
        
        # Increment selection count
        self.counts[arm] += 1
        self.total_selections += 1
        
        # Update average reward using stable incremental formula
        # new_mean = old_mean + (reward - old_mean) / count
        n = self.counts[arm]
        old_value = self.values[arm]
        self.values[arm] = old_value + (reward - old_value) / n
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get current state for serialization.
        
        Returns
        -------
        dict
            State dictionary containing:
            - n_arms: number of arms
            - exploration_constant: exploration parameter
            - counts: selection counts per arm
            - values: average rewards per arm
            - total_selections: total selections made
        """
        state = super().get_state()
        state.update({
            'exploration_constant': self.exploration_constant,
            'counts': self.counts.copy(),
            'values': self.values.copy(),
            'total_selections': self.total_selections,
        })
        return state
    
    def set_state(self, state: Dict[str, Any]) -> None:
        """
        Restore state from serialized dictionary.
        
        Parameters
        ----------
        state : dict
            State dictionary from get_state()
            
        Raises
        ------
        ValueError
            If state is invalid or incompatible
        """
        super().set_state(state)
        
        # Validate state structure
        required_keys = ['exploration_constant', 'counts', 'values', 'total_selections']
        for key in required_keys:
            if key not in state:
                raise ValueError(f"Missing required key in state: {key}")
        
        # Validate array lengths
        if len(state['counts']) != self.n_arms:
            raise ValueError(
                f"counts length {len(state['counts'])} does not match n_arms={self.n_arms}"
            )
        if len(state['values']) != self.n_arms:
            raise ValueError(
                f"values length {len(state['values'])} does not match n_arms={self.n_arms}"
            )
        
        # Restore state
        self.exploration_constant = state['exploration_constant']
        self.counts = state['counts'].copy()
        self.values = state['values'].copy()
        self.total_selections = state['total_selections']
    
    def reset(self) -> None:
        """
        Reset bandit to initial state (forget all observations).
        
        Notes
        -----
        Resets all counters and values to zero, as if the bandit
        was just initialized.
        """
        self.counts = [0] * self.n_arms
        self.values = [0.0] * self.n_arms
        self.total_selections = 0
    
    def get_arm_statistics(self) -> Dict[str, List[float]]:
        """
        Get detailed statistics for all arms.
        
        Returns
        -------
        dict
            Dictionary with keys:
            - 'counts': selection counts per arm
            - 'values': average rewards per arm
            - 'ucb_scores': current UCB scores (at t=total_selections)
            
        Notes
        -----
        Useful for diagnostics and visualization of bandit behavior.
        """
        t = self.total_selections
        ucb_scores = [self._compute_ucb(arm, t) for arm in range(self.n_arms)]
        
        return {
            'counts': self.counts.copy(),
            'values': self.values.copy(),
            'ucb_scores': ucb_scores,
        }
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"UCBBandit(n_arms={self.n_arms}, "
            f"exploration_constant={self.exploration_constant}, "
            f"total_selections={self.total_selections})"
        )
