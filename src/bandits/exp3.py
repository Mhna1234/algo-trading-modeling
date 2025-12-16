"""
EXP3 (Exponential-weight algorithm for Exploration and Exploitation).

Implements the EXP3 algorithm for adversarial and non-stationary environments.
Compatible with the BanditAllocator protocol.
"""

import math
import random
from typing import Dict, Any, List, Optional
from src.bandits.base import BanditAllocator

class EXP3Bandit(BanditAllocator):
    """
    EXP3 bandit algorithm.

    Maintains a probability distribution over arms and updates it
    multiplicatively based on observed rewards.

    Parameters
    ----------
    n_arms : int
        Number of arms
    gamma : float, default=0.07
        Exploration parameter in (0, 1]
    reward_clip : float, optional
        If provided, rewards are clipped to [-reward_clip, reward_clip]
    random_seed : Optional[int]
        Random seed for reproducibility
    reward_shift : Optional[float]
        If provided, all rewards are shifted by this value before scaling to [0, 1]
    reward_scale : Optional[float]
        If provided, all rewards are divided by this value after shifting
    """
    def __init__(
        self,
        n_arms: int,
        gamma: float = 0.07,
        reward_clip: Optional[float] = None,
        random_seed: Optional[int] = None,
        reward_shift: Optional[float] = None,
        reward_scale: Optional[float] = None,
    ):
        super().__init__(n_arms)
        if not (0 < gamma <= 1):
            raise ValueError(f"gamma must be in (0, 1], got {gamma}")
        self.gamma = gamma
        self.reward_clip = reward_clip
        self.reward_shift = reward_shift
        self.reward_scale = reward_scale
        self.weights: List[float] = [1.0] * n_arms
        self.probs: List[float] = [1.0 / n_arms] * n_arms
        self.random_state = random.Random(random_seed)
        self._random_seed = random_seed

    def _update_probabilities(self) -> None:
        total_weight = sum(self.weights)
        if total_weight <= 0:
            self.probs = [1.0 / self.n_arms] * self.n_arms
            return
        self.probs = [
            (1 - self.gamma) * (w / total_weight) + self.gamma / self.n_arms
            for w in self.weights
        ]

    def select_arm(self, t: int) -> int:
        self._update_probabilities()
        r = self.random_state.random()
        cumulative = 0.0
        for i, p in enumerate(self.probs):
            cumulative += p
            if r <= cumulative:
                return i
        return self.n_arms - 1

    def update(self, arm: int, reward: float) -> None:
        super().update(arm, reward)
        # Optionally clip reward
        if self.reward_clip is not None:
            reward = max(-self.reward_clip, min(self.reward_clip, reward))
        # Optionally shift and scale reward to [0, 1]
        reward_scaled = reward
        if self.reward_shift is not None:
            reward_scaled = reward_scaled + self.reward_shift
        if self.reward_scale is not None and self.reward_scale != 0:
            reward_scaled = reward_scaled / self.reward_scale
        # Ensure reward is in [0, 1]
        reward_scaled = max(0.0, min(1.0, reward_scaled))
        p = max(self.probs[arm], 1e-12)
        estimated_reward = reward_scaled / p
        growth_factor = math.exp((self.gamma * estimated_reward) / self.n_arms)
        self.weights[arm] *= growth_factor

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state.update({
            "gamma": self.gamma,
            "reward_clip": self.reward_clip,
            "reward_shift": self.reward_shift,
            "reward_scale": self.reward_scale,
            "weights": self.weights.copy(),
            "random_seed": self._random_seed,
        })
        return state

    def set_state(self, state: Dict[str, Any]) -> None:
        super().set_state(state)
        self.gamma = state["gamma"]
        self.reward_clip = state.get("reward_clip")
        self.reward_shift = state.get("reward_shift")
        self.reward_scale = state.get("reward_scale")
        self.weights = state["weights"].copy()
        self._random_seed = state.get("random_seed")
        if self._random_seed is not None:
            self.random_state = random.Random(self._random_seed)

    def reset(self) -> None:
        self.weights = [1.0] * self.n_arms
        self.probs = [1.0 / self.n_arms] * self.n_arms
        if self._random_seed is not None:
            self.random_state = random.Random(self._random_seed)
        else:
            self.random_state = random.Random()

    def __repr__(self) -> str:
        return (
            f"EXP3Bandit(n_arms={self.n_arms}, "
            f"gamma={self.gamma}, "
            f"reward_clip={self.reward_clip}, "
            f"reward_shift={self.reward_shift}, "
            f"reward_scale={self.reward_scale}, "
            f"random_seed={self._random_seed})"
        )
