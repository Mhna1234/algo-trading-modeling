"""
Thompson Sampling bandit algorithm for continuous rewards.

Thompson Sampling uses Bayesian posterior sampling to balance exploration
and exploitation. It naturally explores uncertain arms (wide posterior)
while exploiting arms with high estimated rewards.
"""

import random
from typing import Dict, Any, List, Optional
from src.bandits.base import BanditAllocator


class ThompsonSamplingBandit(BanditAllocator):
    """
    Thompson Sampling bandit with Normal-Normal conjugate model for continuous rewards.
    
    This implementation uses the exact Bayesian Normal-Normal conjugate posterior:
    - Prior: N(prior_mean, prior_std²)
    - Likelihood: N(θ, reward_std²) with known reward_std
    - Posterior: N(μ_post, σ_post²) where:
      * μ_post = (prior_mean/prior_std² + sum(rewards)/reward_std²) / (1/prior_std² + n/reward_std²)
      * σ_post² = 1 / (1/prior_std² + n/reward_std²)
    
    The algorithm naturally balances exploration and exploitation:
    - Untried arms: use prior distribution
    - Well-tried arms: posterior narrows around true mean
    - Arms with good rewards: high posterior mean → frequently sampled
    
    Parameters
    ----------
    n_arms : int
        Number of arms available for selection
    prior_mean : float, default=0.0
        Prior belief about arm means (typically 0.0 for neutral prior)
    prior_std : float, default=1.0
        Prior standard deviation about arm means (higher = more exploration initially)
    known_reward_std : float, default=1.0
        Known standard deviation of rewards (must be > 0)
    random_seed : Optional[int], default=None
        Random seed for reproducibility. If None, results will be stochastic.
        
    Attributes
    ----------
    counts : List[int]
        Number of times each arm has been selected
    sums : List[float]
        Sum of rewards for each arm
    random_state : random.Random
        Random number generator
        
    Examples
    --------
    >>> bandit = ThompsonSamplingBandit(n_arms=3, known_reward_std=0.1, random_seed=42)
    >>> 
    >>> # Simulate rewards
    >>> for t in range(20):
    ...     arm = bandit.select_arm(t)
    ...     reward = 0.1 * arm + 0.01 * t  # Arm 2 is best
    ...     bandit.update(arm, reward)
    >>> 
    >>> # Check which arm is preferred
    >>> stats = bandit.get_arm_statistics()
    >>> best_arm = max(range(3), key=lambda i: stats['means'][i])
    >>> print(f"Best arm: {best_arm}")
    Best arm: 2
    
    Notes
    -----
    Thompson Sampling has excellent empirical performance and strong
    theoretical properties. It naturally explores uncertain options
    without requiring tuning of exploration parameters (unlike UCB).
    
    For reproducible backtests, set random_seed. For production use
    with real-time adaptation, leave random_seed=None.
    """
    
    def __init__(
        self,
        n_arms: int,
        prior_mean: float = 0.0,
        prior_std: float = 1.0,
        known_reward_std: float = 1.0,
        random_seed: Optional[int] = None
    ):
        """
        Initialize Thompson Sampling bandit.
        
        Parameters
        ----------
        n_arms : int
            Number of arms, must be >= 2
        prior_mean : float, default=0.0
            Prior belief about arm means
        prior_std : float, default=1.0
            Prior standard deviation, must be > 0
        known_reward_std : float, default=1.0
            Known reward standard deviation, must be > 0
        random_seed : Optional[int], default=None
            Random seed for reproducibility
            
        Raises
        ------
        ValueError
            If n_arms < 2, prior_std <= 0, or known_reward_std <= 0
        """
        super().__init__(n_arms)
        
        if prior_std <= 0:
            raise ValueError(f"prior_std must be > 0, got {prior_std}")
        if known_reward_std <= 0:
            raise ValueError(f"known_reward_std must be > 0, got {known_reward_std}")
        
        self.prior_mean = prior_mean
        self.prior_std = prior_std
        self.known_reward_std = known_reward_std
        
        # Statistics for each arm
        self.counts: List[int] = [0] * n_arms
        self.sums: List[float] = [0.0] * n_arms
        
        # Random number generator
        self.random_state = random.Random(random_seed)
        self._random_seed = random_seed
    
    def select_arm(self, t: int) -> int:
        """
        Select arm by sampling from posterior distributions.
        
        Parameters
        ----------
        t : int
            Current time step (not used in Thompson Sampling)
            
        Returns
        -------
        int
            Index of selected arm
            
        Notes
        -----
        Algorithm:
        1. For each arm k, compute posterior mean μ_k and variance σ²_k using Normal-Normal conjugate
        2. Sample θ_k ~ N(μ_k, σ²_k) from each posterior
        3. Select arm with highest sample: argmax_k θ_k
        
        Untried arms use prior distribution for sampling.
        """
        samples = []
        
        for arm in range(self.n_arms):
            if self.counts[arm] == 0:
                # Untried arm: sample from prior
                posterior_mean = self.prior_mean
                posterior_std = self.prior_std
            else:
                # Compute posterior parameters using Normal-Normal conjugate
                n = self.counts[arm]
                sum_rewards = self.sums[arm]
                prior_precision = 1 / (self.prior_std ** 2)
                reward_precision = 1 / (self.known_reward_std ** 2)
                posterior_precision = prior_precision + n * reward_precision
                posterior_mean = (self.prior_mean * prior_precision + sum_rewards * reward_precision) / posterior_precision
                posterior_std = (1 / posterior_precision) ** 0.5
            
            # Sample from posterior
            sample = self.random_state.gauss(posterior_mean, posterior_std)
            samples.append(sample)
        
        # Select arm with highest sample
        return int(max(range(self.n_arms), key=lambda i: samples[i]))
    
    def update(self, arm: int, reward: float) -> None:
        """
        Update posterior after observing reward for selected arm.
        
        Parameters
        ----------
        arm : int
            Index of arm that was selected
        reward : float
            Observed reward (continuous value)
            
        Raises
        ------
        ValueError
            If arm is out of bounds
            
        Notes
        -----
        Updates sufficient statistics:
        - count: n_k += 1
        - sum: sum_k += reward
        
        These statistics are used to compute posterior mean and variance.
        """
        super().update(arm, reward)  # Validates arm index
        
        # Update sufficient statistics
        self.counts[arm] += 1
        self.sums[arm] += reward
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get current state for serialization.
        
        Returns
        -------
        dict
            State dictionary containing:
            - n_arms: number of arms
            - prior_mean: prior mean parameter
            - prior_std: prior standard deviation parameter
            - known_reward_std: known reward standard deviation
            - random_seed: random seed (if set)
            - counts: selection counts per arm
            - sums: sum of rewards per arm
        """
        state = super().get_state()
        state.update({
            'prior_mean': self.prior_mean,
            'prior_std': self.prior_std,
            'known_reward_std': self.known_reward_std,
            'random_seed': self._random_seed,
            'counts': self.counts.copy(),
            'sums': self.sums.copy(),
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
        required_keys = [
            'prior_mean', 'prior_std', 'known_reward_std',
            'counts', 'sums'
        ]
        for key in required_keys:
            if key not in state:
                raise ValueError(f"Missing required key in state: {key}")
        
        # Validate array lengths
        if len(state['counts']) != self.n_arms:
            raise ValueError(
                f"counts length {len(state['counts'])} does not match n_arms={self.n_arms}"
            )
        if len(state['sums']) != self.n_arms:
            raise ValueError(
                f"sums length {len(state['sums'])} does not match n_arms={self.n_arms}"
            )
        
        # Restore state
        self.prior_mean = state['prior_mean']
        self.prior_std = state['prior_std']
        self.known_reward_std = state['known_reward_std']
        self._random_seed = state.get('random_seed')
        self.counts = state['counts'].copy()
        self.sums = state['sums'].copy()
        
        # Re-seed random state if seed was saved
        if self._random_seed is not None:
            self.random_state = random.Random(self._random_seed)
    
    def reset(self) -> None:
        """
        Reset bandit to initial state (forget all observations).
        
        Notes
        -----
        Resets all counters and statistics to zero, and re-seeds
        the random state if a seed was originally provided.
        """
        self.counts = [0] * self.n_arms
        self.sums = [0.0] * self.n_arms
        
        # Reset random state
        if self._random_seed is not None:
            self.random_state = random.Random(self._random_seed)
        else:
            self.random_state = random.Random()
    
    def get_arm_statistics(self) -> Dict[str, List[float]]:
        """
        Get detailed statistics for all arms.
        
        Returns
        -------
        dict
            Dictionary with keys:
            - 'counts': selection counts per arm
            - 'means': posterior mean per arm
            - 'variances': posterior variance per arm
            - 'std_devs': posterior standard deviation per arm
            
        Notes
        -----
        Useful for diagnostics and visualization of posterior beliefs.
        Untried arms show prior parameters.
        """
        means = []
        variances = []
        std_devs = []
        
        for arm in range(self.n_arms):
            if self.counts[arm] == 0:
                # Untried arm: use prior
                means.append(self.prior_mean)
                variances.append(self.prior_std ** 2)
                std_devs.append(self.prior_std)
            else:
                # Compute posterior parameters using Normal-Normal conjugate
                n = self.counts[arm]
                sum_rewards = self.sums[arm]
                prior_precision = 1 / (self.prior_std ** 2)
                reward_precision = 1 / (self.known_reward_std ** 2)
                posterior_precision = prior_precision + n * reward_precision
                posterior_mean = (self.prior_mean * prior_precision + sum_rewards * reward_precision) / posterior_precision
                posterior_var = 1 / posterior_precision
                
                means.append(posterior_mean)
                variances.append(posterior_var)
                std_devs.append(posterior_var ** 0.5)
        
        return {
            'counts': self.counts.copy(),
            'means': means,
            'variances': variances,
            'std_devs': std_devs,
        }
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"ThompsonSamplingBandit(n_arms={self.n_arms}, "
            f"prior_mean={self.prior_mean}, "
            f"prior_std={self.prior_std}, "
            f"known_reward_std={self.known_reward_std}, "
            f"random_seed={self._random_seed})"
        )
    
"""
# NOTE: The following implementation is experimental / optional.
# It is disabled because bayesianbandits is not a project dependency.
# The active and supported implementation is ThompsonSamplingBandit above.
from bayesianbandits import Arm, NormalBandit
from typing import Dict, Any
from src.bandits.base import BanditAllocator
import numpy as np


class BayesianThompsonSamplingBandit(BanditAllocator):

    Proper Bayesian Thompson Sampling using Normal–Normal model.


    def __init__(
        self,
        n_arms: int,
        prior_mean: float = 0.0,
        prior_std: float = 1.0,
        reward_std: float = 1.0,
        random_seed: int | None = None,
    ):
        super().__init__(n_arms)

        self.arms = [
            Arm.Normal(
                mu=prior_mean,
                sigma=prior_std,
                known_sigma=reward_std,
            )
            for _ in range(n_arms)
        ]

        self.bandit = NormalBandit(self.arms, seed=random_seed)

    def select_arm(self, t: int) -> int:
        return int(self.bandit.sample())

    def update(self, arm: int, reward: float) -> None:
        super().update(arm, reward)
        self.bandit.update(arm, reward)

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["arms"] = [arm.to_dict() for arm in self.arms]
        return state

    def set_state(self, state: Dict[str, Any]) -> None:
        super().set_state(state)
        for arm, arm_state in zip(self.arms, state["arms"]):
            arm.from_dict(arm_state)

    def reset(self) -> None:
        for arm in self.arms:
            arm.reset()

"""