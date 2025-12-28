import numpy as np
from typing import Dict, Any
from .base import BanditAllocator


class EpsilonGreedy(BanditAllocator):
    """
    ε-Greedy Multi-Armed Bandit algorithm.
    
    With probability ε, explores by selecting a random arm.
    With probability 1-ε, exploits by selecting the arm with the highest
    average reward observed so far.
    
    Parameters
    ----------
    n_arms : int
        Number of arms (strategies) available for selection
    epsilon : float
        Exploration probability (0 <= epsilon <= 1).
        Higher values increase exploration.
        
    Attributes
    ----------
    visits : np.ndarray
        Count of times each arm has been selected
    satisfaction : np.ndarray
        Sum of rewards received for each arm
        
    Examples
    --------
    >>> bandit = EpsilonGreedy(n_arms=5, epsilon=0.1)
    >>> arm = bandit.select_arm(t=1)
    >>> bandit.update(arm=arm, reward=0.15)
    """
    
    def __init__(self, n_arms: int, epsilon: float):
        """
        Initialize the ε-Greedy bandit.
        
        Parameters
        ----------
        n_arms : int
            Number of arms available for selection
        epsilon : float
            Exploration probability
            
        Raises
        ------
        ValueError
            If epsilon is not in [0, 1]
        """
        super().__init__(n_arms)
        if not 0 <= epsilon <= 1:
            raise ValueError(f"epsilon must be in [0, 1], got {epsilon}")
        self.epsilon = epsilon
        self.visits = np.zeros(n_arms)
        self.satisfaction = np.zeros(n_arms)
    
    def select_arm(self, t: int) -> int:
        """
        Select an arm using ε-Greedy strategy.
        
        Parameters
        ----------
        t : int
            Current time step (unused in ε-Greedy)
            
        Returns
        -------
        int
            Index of selected arm
        """
        if np.random.random() < self.epsilon:
            return np.random.choice(self.n_arms)
        else:
            # Compute average rewards, avoiding division by zero
            avg_rewards = self.satisfaction / (self.visits + 1e-5)
            return np.argmax(avg_rewards)
    
    def update(self, arm: int, reward: float) -> None:
        """
        Update statistics after observing reward for selected arm.
        
        Parameters
        ----------
        arm : int
            Index of arm that was selected
        reward : float
            Observed reward
        """
        if not 0 <= arm < self.n_arms:
            raise ValueError(f"arm must be in [0, {self.n_arms-1}], got {arm}")
        self.visits[arm] += 1
        self.satisfaction[arm] += reward
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get current state for serialization.
        
        Returns
        -------
        dict
            State dictionary
        """
        state = super().get_state()
        state.update({
            'epsilon': self.epsilon,
            'visits': self.visits.tolist(),
            'satisfaction': self.satisfaction.tolist()
        })
        return state
    
    def set_state(self, state: Dict[str, Any]) -> None:
        """
        Restore state from dictionary.
        
        Parameters
        ----------
        state : dict
            State dictionary from get_state()
        """
        super().set_state(state)
        if state.get('epsilon') != self.epsilon:
            raise ValueError(
                f"State epsilon={state.get('epsilon')} does not match "
                f"current epsilon={self.epsilon}"
            )
        self.visits = np.array(state['visits'])
        self.satisfaction = np.array(state['satisfaction'])
    
    def reset(self) -> None:
        """
        Reset bandit to initial state.
        """
        self.visits = np.zeros(self.n_arms)
        self.satisfaction = np.zeros(self.n_arms)