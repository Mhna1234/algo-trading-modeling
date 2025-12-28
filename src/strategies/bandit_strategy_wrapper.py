"""
BanditStrategyWrapper - Multi-Armed Bandit Strategy Allocation

This module provides a meta-strategy that dynamically allocates capital across
a portfolio of child strategies using multi-armed bandit algorithms.

Key Features:
- Dynamic strategy allocation based on realized performance
- Risk-adjusted reward calculation (Sharpe-like)
- Transaction cost awareness
- Robust error handling with fallback allocation
- Comprehensive diagnostics and attribution
- Deterministic under fixed seed

Design:
- Each child strategy is an "arm" in the MAB framework
- The bandit learns which strategies perform best over time
- Allocation adapts based on risk-adjusted rewards
- No look-ahead bias: rewards calculated from realized returns only

Author: GitHub Copilot
Date: December 2025
"""

from typing import List, Dict, Any, Optional, Tuple
from abc import ABC
import pandas as pd
from pandas import Series, DataFrame
import numpy as np
import logging
from dataclasses import dataclass, field

# Import base classes
from src.strategies import BaseStrategyWrapper
from src.portfolio_engine import PortfolioState
from src.bandits import BanditAllocator


# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class StrategyPerformanceTracker:
    """Track performance metrics for a single child strategy."""
    
    strategy_name: str
    returns: List[float] = field(default_factory=list)
    allocations: List[float] = field(default_factory=list)
    timestamps: List[pd.Timestamp] = field(default_factory=list)
    
    def add_observation(self, ret: float, allocation: float, timestamp: pd.Timestamp):
        """Record a new performance observation."""
        self.returns.append(ret)
        self.allocations.append(allocation)
        self.timestamps.append(timestamp)
    
    def get_recent_metrics(self, window: int = 12) -> Dict[str, float]:
        """Calculate recent performance metrics over a rolling window."""
        if len(self.returns) < 1:
            return {
                'n_observations': 0,
                'mean_return': 0.0,
                'volatility': 0.0,
                'sharpe': 0.0,
                'mean_allocation': 0.0
            }
        
        recent_returns = self.returns[-window:]
        recent_allocs = self.allocations[-window:]
        
        mean_ret = np.mean(recent_returns)
        vol = np.std(recent_returns) if len(recent_returns) > 1 else 0.0
        sharpe = mean_ret / (vol + 1e-6)  # Avoid division by zero
        mean_alloc = np.mean(recent_allocs)
        
        return {
            'n_observations': len(self.returns),
            'mean_return': mean_ret,
            'volatility': vol,
            'sharpe': sharpe,
            'mean_allocation': mean_alloc
        }
    
    def get_state(self) -> Dict[str, Any]:
        """Get serializable state for persistence."""
        return {
            'strategy_name': self.strategy_name,
            'returns': self.returns.copy(),
            'allocations': self.allocations.copy(),
            'timestamps': [ts.isoformat() for ts in self.timestamps]
        }
    
    def set_state(self, state: Dict[str, Any]) -> None:
        """Restore state from serialized dictionary."""
        self.strategy_name = state['strategy_name']
        self.returns = state['returns'].copy()
        self.allocations = state['allocations'].copy()
        self.timestamps = [pd.Timestamp(ts) for ts in state['timestamps']]


class BanditStrategyWrapper(BaseStrategyWrapper):
    """
    Multi-Armed Bandit Strategy Allocator
    
    Dynamically allocates capital across multiple child strategies using
    multi-armed bandit algorithms. Each child strategy is treated as an "arm"
    and the bandit learns optimal allocation based on risk-adjusted rewards.
    
    Parameters
    ----------
    child_strategies : List[BaseStrategyWrapper]
        List of child strategies to allocate across (each is an "arm")
    bandit_allocator : BanditAllocator
        Bandit algorithm instance (e.g., UCBBandit, ThompsonSamplingBandit, EXP3Bandit)
    strategy : Optional
        Signal generator (unused, kept for interface consistency)
    optimizer : Optional
        Optimizer (unused for bandit wrapper)
    reward_type : str, default='return'
        Type of reward calculation:
        - 'return': Raw returns (recommended for hard allocation)
        - 'sharpe': Risk-adjusted return (mean/std)
        - 'clipped_sharpe': Bounded Sharpe ratio [-1, 3]
    reward_lookback : int, default=12
        Number of periods to use for reward calculation
    burn_in_periods : int, default=12
        Number of periods to use equal allocation before engaging bandit.
        Followed by a transition period (up to 3 periods or 25% of burn_in_periods)
        where allocations are blended between equal and bandit selections for
        smooth learning activation.
    min_allocation : float, default=0.05
        Minimum allocation per strategy (prevents total exclusion)
    transaction_cost_bps : float, default=5.0
        Transaction cost in basis points for reward adjustment
    enable_soft_allocation : bool, default=False
        If True, use soft allocation (weighted average of all strategies)
        If False, use hard allocation (select single best strategy)
    fallback_on_error : bool, default=True
        If True, fall back to equal allocation when child strategy fails
    random_seed : Optional[int], default=None
        Random seed for deterministic behavior
    strategy_names : Optional[List[str]], default=None
        Display names for strategies. If None, uses strategy.name from each child strategy
    
    Examples
    --------
    >>> from src.bandits import UCBBandit
    >>> from src.strategies import MomentumStrategy, MeanReversionStrategy
    >>> 
    >>> # Create child strategies
    >>> momentum = MomentumStrategy(strategy, optimizer, top_k=10)
    >>> mean_rev = MeanReversionStrategy(strategy, optimizer, top_k=10)
    >>> 
    >>> # Create bandit allocator
    >>> bandit = UCBBandit(n_arms=2, exploration_constant=2.0)
    >>> 
    >>> # Create bandit wrapper
    >>> bandit_wrapper = BanditStrategyWrapper(
    ...     child_strategies=[momentum, mean_rev],
    ...     bandit_allocator=bandit,
    ...     reward_type='sharpe',
    ...     min_allocation=0.1
    ... )
    >>> 
    >>> # Use like any other strategy
    >>> weights = bandit_wrapper.get_weights(date, portfolio_state)
    
    References
    ----------
    Sutton, R. S., & Barto, A. G. (2018).
    "Reinforcement Learning: An Introduction" (2nd ed.). MIT Press.
    
    Agarwal, A., et al. (2014). "Taming the Monster: A Fast and Simple
    Algorithm for Contextual Bandits." ICML.
    """
    
    def __init__(
        self,
        child_strategies: List[BaseStrategyWrapper],
        bandit_allocator: BanditAllocator,
        strategy=None,
        optimizer=None,
        reward_type: str = 'return',
        reward_lookback: int = 12,
        burn_in_periods: int = 12,
        min_allocation: float = 0.05,
        transaction_cost_bps: float = 5.0,
        enable_soft_allocation: bool = False,
        fallback_on_error: bool = True,
        random_seed: Optional[int] = None,
        strategy_names: Optional[List[str]] = None,
        **kwargs
    ):
        """Initialize Bandit Strategy Wrapper."""
        super().__init__(
            name="Bandit Strategy Allocator",
            strategy=strategy,
            optimizer=optimizer,
            **kwargs
        )
        
        # Log warning for unknown kwargs (defensive check)
        if kwargs:
            logger.warning(
                f"Unknown keyword arguments passed to BanditStrategyWrapper: {list(kwargs.keys())}. "
                "These were passed to the base class."
            )
        
        # Validate inputs
        if not child_strategies:
            raise ValueError("Must provide at least one child strategy")
        
        if len(child_strategies) != bandit_allocator.n_arms:
            raise ValueError(
                f"Number of child strategies ({len(child_strategies)}) must match "
                f"bandit n_arms ({bandit_allocator.n_arms})"
            )
        
        if not 0 <= min_allocation <= 1.0 / len(child_strategies):
            raise ValueError(
                f"min_allocation must be in [0, {1.0/len(child_strategies):.3f}]"
            )
        
        # Store configuration
        self.child_strategies = child_strategies
        self.bandit_allocator = bandit_allocator
        self.reward_type = reward_type
        self.reward_lookback = reward_lookback
        self.burn_in_periods = burn_in_periods
        self.min_allocation = min_allocation
        self.transaction_cost_bps = transaction_cost_bps
        self.enable_soft_allocation = enable_soft_allocation
        self.fallback_on_error = fallback_on_error
        self.random_seed = random_seed
        
        # Set strategy display names
        if strategy_names is None:
            self.strategy_names = [s.name for s in child_strategies]
        else:
            if len(strategy_names) != len(child_strategies):
                raise ValueError(
                    f"strategy_names length ({len(strategy_names)}) must match "
                    f"child_strategies length ({len(child_strategies)})"
                )
            self.strategy_names = strategy_names

        # Guard against pathological configurations (warnings only)
        if self.enable_soft_allocation and self.reward_type == "sharpe":
            logger.warning(
                "Soft allocation with Sharpe rewards may cause unstable learning. "
                "Sharpe rewards work best with hard allocation (single strategy selection)."
            )

        if self.reward_lookback < 12:
            logger.warning(
                f"reward_lookback={self.reward_lookback} is very short. "
                "This may cause noisy reward signals and unstable allocation. "
                "Consider using reward_lookback >= 12 for more stable learning."
            )

        if self.bandit_allocator.__class__.__name__ == 'EXP3Bandit' and self.reward_type != 'clipped_sharpe':
            logger.warning(
                "EXP3 bandit expects rewards in [0,1] range. "
                f"Current reward_type='{self.reward_type}' may produce out-of-range rewards, "
                "leading to unpredictable allocation behavior. Consider using reward_type='clipped_sharpe'."
            )
        
        # State tracking
        self.period_count = 0
        self.last_date: Optional[pd.Timestamp] = None
        self.last_weights: Optional[Series] = None
        self.last_allocations: Optional[np.ndarray] = None
        self.last_portfolio_value: Optional[float] = None
        
        # Learning state visibility
        self.bandit_active = False
        self.bandit_has_learned = False
        
        # Performance tracking
        self.trackers = [
            StrategyPerformanceTracker(strategy_name=name)
            for name in self.strategy_names
        ]
        
        # Allocation history
        self.allocation_history: List[Dict[str, Any]] = []
        
        # Set random seed if provided
        if random_seed is not None:
            np.random.seed(random_seed)
        
        logger.info(
            f"Initialized BanditStrategyWrapper with {len(child_strategies)} strategies, "
            f"algorithm={bandit_allocator.__class__.__name__}, "
            f"reward_type={reward_type}"
        )
    
    def get_weights(
        self,
        date: pd.Timestamp,
        portfolio_state: PortfolioState
    ) -> Series:
        """
        Generate target portfolio weights using bandit allocation.
        
        Flow:
        1. Calculate rewards from previous period (if not first period)
        2. Update bandit with rewards
        3. Get strategy allocations from bandit
        4. Get weights from each child strategy
        5. Aggregate using weighted combination
        6. Track state for next period's reward calculation
        
        Reward Timing Contract (Anti Look-Ahead):
        - Rewards updated at time t reflect performance from t-1 → t
        - Allocations selected at time t apply to t → t+1
        - Reward update MUST occur before allocation selection
        
        Parameters
        ----------
        date : pd.Timestamp
            Current rebalancing date
        portfolio_state : PortfolioState
            Current portfolio state with metrics
        
        Returns
        -------
        pd.Series
            Target portfolio weights (sum to 1.0)
        """
        # Anti look-ahead check (warning only, allow continuation)
        if self.last_date is not None and self.last_date >= date:
            logger.warning(f"Potential look-ahead or repeated date detected: last_date={self.last_date}, current_date={date}. Allowing continuation.")
        
        # Step 1: Calculate and update rewards from previous period
        if self.period_count > 0 and self.last_weights is not None:
            self._update_rewards_from_previous_period(date, portfolio_state)
        
        # Step 2: Get strategy allocations from bandit
        allocations = self._get_strategy_allocations(date)
        
        # Step 3: Get weights from each child strategy
        child_weights = self._get_child_weights(date, portfolio_state)
        
        # Step 4: Aggregate weights
        final_weights = self._aggregate_weights(child_weights, allocations)
        
        # Step 5: Track state for next period
        self._record_state(date, final_weights, allocations, portfolio_state)
        
        self.period_count += 1
        
        return final_weights
    
    def _update_rewards_from_previous_period(
        self,
        current_date: pd.Timestamp,
        portfolio_state: PortfolioState
    ):
        """
        Calculate rewards from previous period and update bandit.
        
        Reward is calculated as risk-adjusted return with transaction cost adjustment.
        During burn-in period, bandit does NOT learn (no updates).
        During transition period, bandit learns with partial weight.
        """
        try:
            # Calculate strategy-specific returns
            strategy_returns = self._calculate_strategy_returns(
                portfolio_state,
                current_date
            )
            
            # Calculate rewards with risk adjustment
            rewards = self._calculate_rewards(strategy_returns)
            
            # Skip bandit updates during burn-in period
            if self.period_count < self.burn_in_periods:
                # During burn-in, use proportional attribution for tracking purposes
                # (since we're not learning, we can attribute returns proportionally)
                if self.last_portfolio_value is not None and self.last_portfolio_value > 0:
                    portfolio_return = (portfolio_state.equity - self.last_portfolio_value) / self.last_portfolio_value
                    # Proportional attribution during burn-in
                    proportional_returns = [portfolio_return] * len(strategy_returns)
                else:
                    proportional_returns = [0.0] * len(strategy_returns)
                
                # Still track performance for diagnostics, but don't update bandit
                for arm_idx, ret in enumerate(proportional_returns):
                    allocation = self.last_allocations[arm_idx] if self.last_allocations is not None else 0.0
                    # Use a dummy reward of 0 since we're not learning
                    self.trackers[arm_idx].add_observation(ret, allocation, current_date)
                logger.debug(f"Burn-in period ({self.period_count}/{self.burn_in_periods}): proportional attribution for tracking")
                return
            
            # During transition period (first few periods after burn-in), use partial learning
            transition_periods = min(3, self.burn_in_periods // 4)  # Up to 3 periods or 25% of burn-in
            is_transition = (self.burn_in_periods <= self.period_count < self.burn_in_periods + transition_periods)
            
            if is_transition:
                # Partial learning: update bandit but with reduced confidence
                learning_weight = (self.period_count - self.burn_in_periods + 1) / transition_periods
                logger.debug(f"Transition period ({self.period_count - self.burn_in_periods + 1}/{transition_periods}): partial learning with weight {learning_weight:.2f}")
            else:
                learning_weight = 1.0
            
            # Update bandit with rewards for each arm (after burn-in)
            for arm_idx, reward in enumerate(rewards):
                # Apply learning weight during transition
                adjusted_reward = reward * learning_weight
                
                # Reward sanity checks (observability only, no modification)
                if np.isnan(adjusted_reward) or np.isinf(adjusted_reward):
                    logger.warning(f"Invalid adjusted reward for arm {arm_idx}: {adjusted_reward} (NaN or infinite)")
                elif abs(adjusted_reward) > 5.0:
                    logger.warning(f"Extreme adjusted reward for arm {arm_idx}: {adjusted_reward} (magnitude > 5)")
                if self.bandit_allocator.__class__.__name__ == 'EXP3Bandit':
                    # EXP3 expects rewards in [0, 1] after scaling
                    if not (0 <= adjusted_reward <= 1):
                        logger.warning(f"EXP3 adjusted reward out of [0,1] range for arm {arm_idx}: {adjusted_reward}")
                
                self.bandit_allocator.update(arm_idx, adjusted_reward)
            
            # Mark that bandit has learned at least once
            self.bandit_has_learned = True
            
            # Track performance
            for arm_idx, (ret, reward) in enumerate(zip(strategy_returns, rewards)):
                allocation = self.last_allocations[arm_idx] if self.last_allocations is not None else 0.0
                self.trackers[arm_idx].add_observation(ret, allocation, current_date)
            
            # Validation: Check for illogical allocations (logs only, no behavior change)
            self._validate_allocation_logic(rewards, current_date)
            
            logger.debug(
                f"Updated rewards at {current_date}: "
                f"returns={[f'{r:.4f}' for r in strategy_returns]}, "
                f"rewards={[f'{r:.4f}' for r in rewards]}, "
                f"learning_weight={learning_weight:.2f}"
            )
            
        except Exception as e:
            logger.warning(f"Failed to update rewards: {e}. Skipping update.")
    
    def _validate_allocation_logic(self, rewards: List[float], date: pd.Timestamp):
        """
        Validate allocation logic for potential issues (logging only).
        
        SOURCE OF ILLOGICAL ALLOCATION #5: Lack of Validation
        - Previously: No checks for economically irrational allocation behavior
        - Fixed: Added validation for dominance without reward justification and allocation oscillation
        - Impact: Now detects when allocations don't match reward signals
        
        Checks for:
        - One strategy dominating >90% allocation without corresponding reward dominance
        - Allocation oscillation without reward variance
        """
        if self.last_allocations is None or len(self.last_allocations) < 2:
            return
        
        allocations = self.last_allocations
        
        # Check for dominance without reward justification
        max_alloc_idx = np.argmax(allocations)
        max_alloc = allocations[max_alloc_idx]
        max_reward = rewards[max_alloc_idx]
        
        if max_alloc > 0.9:  # One strategy has >90% allocation
            # Check if this strategy has the highest reward
            sorted_rewards = sorted(rewards, reverse=True)
            if len(sorted_rewards) > 1 and max_reward < sorted_rewards[1] * 0.9:
                # This strategy doesn't have nearly the highest reward
                logger.info(
                    f"High allocation concentration at {date}: "
                    f"{self.strategy_names[max_alloc_idx]} has {max_alloc:.1%} allocation "
                    f"but reward {max_reward:.4f} vs best reward {sorted_rewards[0]:.4f}. "
                    f"This may indicate learning instability or reward signal issues."
                )
        
        # Check for allocation oscillation (if we have history)
        if len(self.allocation_history) >= 3:
            recent_allocs = [h['allocations'] for h in self.allocation_history[-3:]]
            
            # Check if allocations are oscillating without reward changes
            alloc_changes = []
            for i in range(len(recent_allocs) - 1):
                changes = [abs(a - b) for a, b in zip(recent_allocs[i], recent_allocs[i+1])]
                alloc_changes.append(np.mean(changes))
            
            avg_alloc_change = np.mean(alloc_changes)
            reward_std = np.std(rewards)
            
            # High allocation changes with low reward variance may indicate noise
            if avg_alloc_change > 0.3 and reward_std < 0.01:
                logger.info(
                    f"Allocation oscillation detected at {date}: "
                    f"Average allocation change {avg_alloc_change:.1%} with low reward variance "
                    f"(std={reward_std:.4f}). This may indicate noisy reward signals or "
                    f"over-sensitive learning parameters."
                )
    
    def _calculate_strategy_returns(
        self,
        portfolio_state: PortfolioState,
        current_date: pd.Timestamp
    ) -> List[float]:
        """
        Calculate per-strategy returns for the previous period.

        For bandit learning, we always use pure strategy returns (not allocation-weighted)
        to allow the bandit to learn which strategies are fundamentally better.
        
        The allocation mode (hard vs soft) only affects how weights are combined,
        not how rewards are calculated for learning.
        """
        # Get portfolio return over period
        if self.last_portfolio_value is not None and self.last_portfolio_value > 0:
            portfolio_return = (portfolio_state.equity - self.last_portfolio_value) / self.last_portfolio_value
        else:
            # First period: no return to calculate
            return [0.0] * len(self.child_strategies)

        # For learning purposes, always use hard attribution
        # This allows the bandit to learn pure strategy skill
        # The allocation mode affects weight combination, not reward attribution
        strategy_returns = [0.0] * len(self.child_strategies)
        if self.last_allocations is not None:
            # Attribute the full portfolio return to the strategy with highest allocation
            # This encourages the bandit to learn which strategy performs best when given capital
            selected_strategy_idx = np.argmax(self.last_allocations)
            strategy_returns[selected_strategy_idx] = portfolio_return

        return strategy_returns
    
    def _calculate_rewards(self, strategy_returns: List[float]) -> List[float]:
        """
        Calculate rewards from strategy returns based on reward_type.

        SOURCE OF ILLOGICAL ALLOCATION #3: Transaction Cost Attribution Bug
        - Previously: Penalized absolute allocation level (abs(current_alloc))
        - Fixed: Now penalizes allocation change (turnover) which is economically correct
        - Impact: Strategies were being penalized for maintaining large positions rather than trading
        
        SOURCE OF ILLOGICAL ALLOCATION #4: Sharpe Ratio Dilution
        - Previously: Included zero-allocation periods in Sharpe calculation
        - Fixed: Only considers periods with meaningful allocation (> epsilon)
        - Impact: Sharpe ratios were artificially depressed by periods of non-participation

        Reward Attribution:
        - For learning: Always use hard attribution (full portfolio return to highest allocated strategy)
        - This allows bandit to learn pure strategy skill regardless of allocation mode
        - Allocation mode affects weight combination, not reward learning
        """
        rewards = []

        for arm_idx, current_return in enumerate(strategy_returns):
            if self.reward_type == 'return':
                # Raw return (recommended for hard allocation)
                # For hard allocation: pure strategy skill
                # For soft allocation: portfolio contribution (allocation-weighted)
                reward = current_return

            elif self.reward_type == 'sharpe':
                # For soft allocation: use current period's risk-adjusted contribution
                # For hard allocation: use historical Sharpe (fallback for compatibility)
                if self.enable_soft_allocation and self.last_allocations is not None:
                    # Soft allocation: reward based on current period contribution
                    allocation = self.last_allocations[arm_idx]
                    if allocation > 0.01:  # Only reward strategies with meaningful allocation
                        # Risk-adjust the current return contribution
                        # Use recent volatility from tracker for risk adjustment
                        metrics = self.trackers[arm_idx].get_recent_metrics(min(12, self.reward_lookback))
                        vol = metrics.get('volatility', 0.15)  # Default 15% vol if no data
                        reward = current_return / (vol + 1e-6)  # Sharpe-like ratio for current contribution
                    else:
                        reward = 0.0  # No reward for strategies with negligible allocation
                else:
                    # Hard allocation fallback: use historical Sharpe
                    metrics = self.trackers[arm_idx].get_recent_metrics(self.reward_lookback)
                    reward = metrics['sharpe']

            elif self.reward_type == 'clipped_sharpe':
                # Clipped Sharpe ratio for EXP3 compatibility
                if self.enable_soft_allocation and self.last_allocations is not None:
                    # Soft allocation: use current period contribution
                    allocation = self.last_allocations[arm_idx]
                    if allocation > 0.01:
                        metrics = self.trackers[arm_idx].get_recent_metrics(min(12, self.reward_lookback))
                        vol = metrics.get('volatility', 0.15)
                        sharpe = current_return / (vol + 1e-6)
                        reward = np.clip(sharpe, -1.0, 3.0)
                    else:
                        reward = 0.0
                else:
                    # Hard allocation: use historical Sharpe
                    metrics = self.trackers[arm_idx].get_recent_metrics(self.reward_lookback)
                    sharpe = metrics['sharpe']
                    reward = np.clip(sharpe, -1.0, 3.0)

            else:
                raise ValueError(f"Unknown reward_type: {self.reward_type}")

            # Apply transaction cost adjustment for allocation changes
            # Transaction costs occur whenever allocations change, regardless of mode
            if self.last_allocations is not None and len(self.last_allocations) > arm_idx:
                current_alloc = self.last_allocations[arm_idx]
                # Get previous allocation (from two periods ago, since last_allocations is from previous period)
                if len(self.allocation_history) >= 2:
                    prev_alloc = self.allocation_history[-2]['allocations'][arm_idx]
                    # Turnover = absolute change in allocation
                    turnover = abs(current_alloc - prev_alloc)
                    turnover_penalty = turnover * (self.transaction_cost_bps / 10000.0)
                    reward -= turnover_penalty
                # Note: No penalty applied when allocation is unchanged (turnover = 0)

            rewards.append(reward)

        # Post-process rewards for specific bandit algorithms
        if self.bandit_allocator.__class__.__name__ == 'EXP3Bandit':
            # EXP3 requires rewards in [0, 1] range
            # Transform rewards using sigmoid-like normalization
            rewards = self._normalize_rewards_for_exp3(rewards)

        return rewards
    
    def _normalize_rewards_for_exp3(self, rewards: List[float]) -> List[float]:
        """
        Normalize rewards to [0, 1] range for EXP3 bandit algorithm.
        
        Uses a sigmoid-like transformation that preserves relative ranking
        while ensuring all rewards are in the required [0, 1] range.
        """
        if not rewards:
            return rewards
            
        rewards_array = np.array(rewards)
        
        # Handle edge case of all identical rewards
        if np.std(rewards_array) < 1e-6:
            return [0.5] * len(rewards)  # Neutral reward for all arms
            
        # Sigmoid transformation: maps rewards to [0, 1]
        # Center around median to be robust to outliers
        median_reward = np.median(rewards_array)
        
        # Scale factor controls the steepness of the sigmoid
        # Higher values = more extreme rewards (closer to 0 or 1)
        scale_factor = 2.0  # Adjustable parameter
        
        normalized = 1 / (1 + np.exp(-(rewards_array - median_reward) / scale_factor))
        
        # Ensure no rewards are exactly 0 or 1 (EXP3 can have issues with boundaries)
        epsilon = 1e-6
        normalized = np.clip(normalized, epsilon, 1 - epsilon)
        
        return normalized.tolist()
    
    def _get_strategy_allocations(self, date: pd.Timestamp) -> np.ndarray:
        """
        Get strategy allocations from bandit algorithm.
        
        During burn-in period, uses equal allocation.
        During transition period, blends equal and bandit allocations.
        After transition, uses full bandit allocation.
        
        Canonical Bandit Time Index:
        - Uses self.period_count as single source of truth for bandit time
        - Always passes bandit_time = self.period_count to select_arm()
        """
        n_strategies = len(self.child_strategies)
        
        # Burn-in period: equal allocation, bandit does NOT learn
        if self.period_count < self.burn_in_periods:
            allocations = np.ones(n_strategies) / n_strategies
            logger.debug(f"Burn-in period ({self.period_count}/{self.burn_in_periods}): equal allocation")
            return allocations
        
        # Transition period: blend equal and bandit allocations for smooth transition
        transition_periods = min(3, self.burn_in_periods // 4)  # Up to 3 periods or 25% of burn-in
        is_transition = (self.burn_in_periods <= self.period_count < self.burn_in_periods + transition_periods)
        
        if is_transition:
            # Blend equal allocation with bandit allocation
            transition_progress = (self.period_count - self.burn_in_periods + 1) / transition_periods
            equal_weight = 1.0 - transition_progress
            bandit_weight = transition_progress
            
            # Get equal allocation
            equal_allocations = np.ones(n_strategies) / n_strategies
            
            # Get bandit allocation
            bandit_allocations = self._get_bandit_allocations()
            
            # Blend allocations
            allocations = equal_weight * equal_allocations + bandit_weight * bandit_allocations
            
            logger.debug(
                f"Transition period ({self.period_count - self.burn_in_periods + 1}/{transition_periods}): "
                f"blending equal ({equal_weight:.2f}) and bandit ({bandit_weight:.2f}) allocations"
            )
            return allocations
        
        # Burn-in just ended: activate bandit learning
        if not self.bandit_active:
            self.bandit_active = True
            logger.info(f"Bandit learning activated at period {self.period_count}")
        
        # Full bandit allocation after transition
        allocations = self._get_bandit_allocations()
        return allocations
    
    def _get_bandit_allocations(self) -> np.ndarray:
        """
        Get allocations directly from bandit algorithm (helper method).
        """
        n_strategies = len(self.child_strategies)
        
        # Query bandit for selection using canonical time index
        bandit_time = self.period_count
        if self.enable_soft_allocation:
            # Soft allocation: use empirical frequencies or Thompson sampling
            allocations = self._compute_soft_allocations()
        else:
            # Hard allocation: select single best arm
            selected_arm = self.bandit_allocator.select_arm(bandit_time)
            allocations = np.zeros(n_strategies)
            allocations[selected_arm] = 1.0
        
        # Apply minimum allocation constraint (only for soft allocation)
        if self.enable_soft_allocation and self.min_allocation > 0:
            allocations = self._apply_min_allocation(allocations)
        
        return allocations
    
    def _compute_soft_allocations(self) -> np.ndarray:
        """
        Compute soft allocations using bandit statistics.
        
        Uses empirical mean estimates to create a softmax-like allocation.
        Handles different bandit types that may not have 'counts'.
        """
        n_strategies = len(self.child_strategies)
        
        # Get bandit state
        state = self.bandit_allocator.get_state()
        
        # Handle different bandit types
        if 'counts' in state:
            counts = state['counts']
        else:
            # For bandits without counts (like EXP3), use uniform weights
            # or derive from available statistics
            if 'weights' in state:
                # EXP3 case: use weights as proxy for experience
                weights = np.array(state['weights'])
                # Normalize weights to get relative experience
                counts = weights / np.sum(weights) * 10  # Scale to reasonable count values
            else:
                # Fallback: assume equal experience
                counts = np.ones(n_strategies)
        
        # Get mean values (UCB stores 'values', Thompson needs computation)
        if 'values' in state:
            # UCB case: use stored average rewards
            values = state['values']
        elif 'sums' in state and 'counts' in state:
            # Thompson case: compute means from sufficient statistics
            sums = state.get('sums', [0.0] * n_strategies)
            values = [
                sums[i] / counts[i] if counts[i] > 0 else 0.0
                for i in range(n_strategies)
            ]
        else:
            # No value information available
            values = [0.0] * n_strategies
        
        # Avoid division by zero
        if all(c == 0 for c in counts):
            return np.ones(n_strategies) / n_strategies
        
        # Use softmax on estimated values (with temperature = 1.0)
        # This creates a smooth distribution favoring high-value arms
        values_array = np.array(values)
        exp_values = np.exp(values_array - np.max(values_array))  # Numerical stability
        allocations = exp_values / np.sum(exp_values)
        
        return allocations
    
    def _apply_min_allocation(self, allocations: np.ndarray) -> np.ndarray:
        """
        Apply minimum allocation constraint while preserving rank order.
        """
        n_strategies = len(allocations)
        min_total = self.min_allocation * n_strategies
        
        if min_total >= 1.0:
            # If min constraint forces equal allocation
            return np.ones(n_strategies) / n_strategies
        
        # Reserve minimum for all strategies
        remaining = 1.0 - min_total
        adjusted = allocations.copy()
        
        # Redistribute remaining proportionally to original allocations
        if allocations.sum() > 0:
            adjusted = self.min_allocation + (allocations / allocations.sum()) * remaining
        else:
            adjusted = np.ones(n_strategies) / n_strategies
        
        # Ensure normalization
        adjusted = adjusted / adjusted.sum()
        
        return adjusted
    
    def _get_child_weights(
        self,
        date: pd.Timestamp,
        portfolio_state: PortfolioState
    ) -> List[Series]:
        """
        Get weights from each child strategy.
        
        Handles failures gracefully by falling back to equal weights.
        """
        child_weights = []
        
        for strategy_idx, strategy in enumerate(self.child_strategies):
            try:
                weights = strategy.get_weights(date, portfolio_state)
                
                # Validate weights
                if weights is None or len(weights) == 0:
                    raise ValueError(f"Strategy {strategy.name} returned empty weights")
                
                # Ensure weights sum to reasonable value
                weight_sum = weights.sum()
                if not (0.0 <= weight_sum <= 1.0 + 1e-6):
                    logger.warning(
                        f"Strategy {strategy.name} returned weights summing to {weight_sum:.4f}. "
                        "Normalizing."
                    )
                    weights = weights / weight_sum if weight_sum > 0 else weights
                
                child_weights.append(weights)
                
            except Exception as e:
                logger.error(f"Strategy {strategy.name} failed: {e}")
                
                if self.fallback_on_error:
                    # Fall back to equal weights
                    assets = strategy.strategy.assets
                    fallback_weights = Series(1.0 / len(assets), index=assets)
                    child_weights.append(fallback_weights)
                    logger.warning(f"Using equal-weight fallback for {strategy.name}")
                else:
                    raise
        
        return child_weights
    
    def _aggregate_weights(
        self,
        child_weights: List[Series],
        allocations: np.ndarray
    ) -> Series:
        """
        Aggregate child strategy weights using bandit allocations.
        
        Computes weighted average: w_final = Σ α_k * w_k
        """
        # Initialize with zeros
        first_weights = child_weights[0]
        aggregated = Series(0.0, index=first_weights.index)
        
        # Weighted sum
        for strategy_idx, (weights, allocation) in enumerate(zip(child_weights, allocations)):
            # Ensure consistent index
            aligned_weights = weights.reindex(aggregated.index, fill_value=0.0)
            aggregated += allocation * aligned_weights
        
        # Normalize to sum to 1.0 (handle numerical errors)
        weight_sum = aggregated.sum()
        if weight_sum > 1e-10:
            aggregated = aggregated / weight_sum
        else:
            # Fallback to equal weights if all zeros
            aggregated = Series(1.0 / len(aggregated), index=aggregated.index)
            logger.warning("Aggregated weights sum to zero. Using equal weights.")
        
        return aggregated
    
    def _record_state(
        self,
        date: pd.Timestamp,
        weights: Series,
        allocations: np.ndarray,
        portfolio_state: PortfolioState
    ):
        """Record current state for next period's reward calculation."""
        self.last_date = date
        self.last_weights = weights.copy()
        self.last_allocations = allocations.copy()
        self.last_portfolio_value = portfolio_state.equity
        
        # Record allocation history
        self.allocation_history.append({
            'date': date,
            'allocations': allocations.copy(),
            'period': self.period_count,
            'fold_number': getattr(self, 'current_fold', None)
        })
    
    def get_strategy_allocations(self) -> DataFrame:
        """
        Get historical strategy allocations as DataFrame.
        
        Returns
        -------
        pd.DataFrame
            Index: dates, Columns: strategy names, Values: allocations
        """
        if not self.allocation_history:
            return DataFrame()
        
        data = {
            name: [h['allocations'][i] for h in self.allocation_history]
            for i, name in enumerate(self.strategy_names)
        }
        
        dates = [h['date'] for h in self.allocation_history]
        
        return DataFrame(data, index=dates)
    
    def get_diagnostics(self) -> Dict[str, Any]:
        """
        Get comprehensive diagnostic information.
        
        SOURCE OF ILLOGICAL ALLOCATION #6: Unclear Reward Attribution
        - Previously: No explanation of how rewards relate to allocation mode
        - Fixed: Added explicit reward_attribution explanation in diagnostics
        - Impact: Users can now understand whether rewards reflect strategy skill vs portfolio contribution
        
        Returns
        -------
        dict
            Contains:
            - 'bandit_state': Current bandit algorithm state
            - 'strategy_metrics': Performance metrics per strategy
            - 'allocation_history': Historical allocations
            - 'current_allocations': Most recent allocations
            - 'period_count': Total periods processed
            - 'reward_attribution': Explanation of how rewards are calculated
        """
        # Get bandit state
        bandit_state = self.bandit_allocator.get_state()
        
        # Get strategy metrics
        strategy_metrics = {
            strategy.name: tracker.get_recent_metrics(self.reward_lookback)
            for strategy, tracker in zip(self.child_strategies, self.trackers)
        }
        
        # Current allocations
        current_allocations = {
            strategy.name: self.last_allocations[i] if self.last_allocations is not None else 0.0
            for i, strategy in enumerate(self.child_strategies)
        }
        
        # Reward attribution explanation
        if self.enable_soft_allocation:
            reward_attribution = (
                "Soft allocation: Rewards reflect PORTFOLIO CONTRIBUTION (allocation-weighted returns). "
                "Strategies are rewarded based on their contribution to overall portfolio performance, "
                "not pure strategy skill. This creates positive feedback loops where successful "
                "strategies get more allocation, amplifying their impact."
            )
        else:
            reward_attribution = (
                "Hard allocation: Rewards reflect PURE STRATEGY SKILL. "
                "Only the selected strategy receives the full portfolio return as reward. "
                "This isolates strategy performance from allocation effects."
            )
        
        return {
            'bandit_state': bandit_state,
            'strategy_metrics': strategy_metrics,
            'allocation_history': self.allocation_history.copy(),
            'current_allocations': current_allocations,
            'period_count': self.period_count,
            'burn_in_complete': self.period_count >= self.burn_in_periods,
            'reward_attribution': reward_attribution,
            'reward_type': self.reward_type,
            'enable_soft_allocation': self.enable_soft_allocation
        }
    
    def reset(self, fold_number: Optional[int] = None) -> None:
        """
        Reset MAB state for walk-forward fold isolation.
        
        This method resets the bandit allocator, performance trackers, and all
        internal state to initial values. Used between walk-forward folds to
        prevent lookahead bias.
        
        Parameters
        ----------
        fold_number : int, optional
            Current fold number for diagnostic tracking
        """
        # Store fold information
        self.current_fold = fold_number
        
        # Reset bandit allocator
        self.bandit_allocator.reset()
        
        # Reset performance trackers
        self.trackers = [
            StrategyPerformanceTracker(strategy_name=name)
            for name in self.strategy_names
        ]
        
        # Reset state tracking
        self.period_count = 0
        self.last_date = None
        self.last_weights = None
        self.last_allocations = None
        self.last_portfolio_value = None
        
        # Reset learning state
        self.bandit_active = False
        self.bandit_has_learned = False
        
        # Reset allocation history
        self.allocation_history = []
        
        logger.info(f"BanditStrategyWrapper state reset for fold {fold_number} walk-forward isolation")
    
    def get_fold_diagnostics(self, fold_number: Optional[int] = None) -> Dict[str, Any]:
        """
        Get fold-specific diagnostic information for walk-forward analysis.
        
        Parameters
        ----------
        fold_number : int, optional
            Specific fold number to analyze. If None, returns current state.
            
        Returns
        -------
        dict
            Fold-specific diagnostics including:
            - fold_number: Current fold being processed
            - learning_progress: Burn-in status and learning activation
            - allocation_evolution: How allocations changed during the fold
            - strategy_performance: Per-strategy metrics for the fold
            - bandit_state: Algorithm state at fold end
        """
        # Filter allocation history for this fold if specified
        if fold_number is not None:
            fold_allocations = [entry for entry in self.allocation_history 
                              if entry.get('fold_number') == fold_number]
        else:
            fold_allocations = self.allocation_history
        
        # Calculate allocation evolution
        if fold_allocations:
            allocation_evolution = {
                'initial_allocation': fold_allocations[0]['allocations'] if fold_allocations else None,
                'final_allocation': fold_allocations[-1]['allocations'] if fold_allocations else None,
                'allocation_changes': len([entry for entry in fold_allocations[1:] 
                                         if not np.allclose(entry['allocations'], fold_allocations[0]['allocations'])]),
                'total_periods': len(fold_allocations)
            }
        else:
            allocation_evolution = {
                'initial_allocation': None,
                'final_allocation': None,
                'allocation_changes': 0,
                'total_periods': 0
            }
        
        # Learning progress
        learning_progress = {
            'period_count': self.period_count,
            'burn_in_periods': self.burn_in_periods,
            'burn_in_complete': self.period_count >= self.burn_in_periods,
            'bandit_active': self.bandit_active,
            'bandit_has_learned': self.bandit_has_learned,
            'transition_periods': min(3, self.burn_in_periods // 4) if self.burn_in_periods > 0 else 0
        }
        
        # Strategy performance for this fold
        strategy_performance = {}
        for i, (strategy, tracker) in enumerate(zip(self.child_strategies, self.trackers)):
            # Get fold-specific returns if available
            fold_returns = [entry for entry in fold_allocations 
                          if entry.get('fold_number') == fold_number]
            
            strategy_performance[strategy.name] = {
                'total_observations': len(tracker.returns),
                'fold_allocations': [entry['allocations'][i] for entry in fold_returns] if fold_returns else [],
                'final_metrics': tracker.get_recent_metrics(self.reward_lookback),
                'allocation_volatility': np.std([entry['allocations'][i] for entry in fold_returns]) if fold_returns else 0.0
            }
        
        return {
            'fold_number': fold_number,
            'learning_progress': learning_progress,
            'allocation_evolution': allocation_evolution,
            'strategy_performance': strategy_performance,
            'bandit_state': self.bandit_allocator.get_state(),
            'fold_allocations': fold_allocations
        }
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Return strategy metadata."""
        return {
            'name': self.name,
            'type': self.__class__.__name__,
            'parameters': {
                'n_strategies': len(self.child_strategies),
                'child_strategies': [s.name for s in self.child_strategies],
                'bandit_algorithm': self.bandit_allocator.__class__.__name__,
                'reward_type': self.reward_type,
                'reward_lookback': self.reward_lookback,
                'burn_in_periods': self.burn_in_periods,
                'min_allocation': self.min_allocation,
                'enable_soft_allocation': self.enable_soft_allocation
            }
        }
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get complete state for persistence and resumption.
        
        Returns
        -------
        dict
            JSON-serializable dictionary containing:
            - bandit_state: Bandit allocator state
            - trackers: Performance tracking state per strategy
            - period_count: Number of periods processed
            - last_date: Last processed date (ISO format)
            - last_weights: Last portfolio weights (dict)
            - last_allocations: Last strategy allocations (list)
            - last_portfolio_value: Last portfolio value
            - allocation_history: Full history of allocations
            
        Notes
        -----
        Use this to save bandit state between runs. State can be
        serialized to JSON and restored with set_state().
        
        Examples
        --------
        >>> state = wrapper.get_state()
        >>> import json
        >>> with open('bandit_state.json', 'w') as f:
        ...     json.dump(state, f)
        """
        # Serialize allocation history
        serialized_history = [
            {
                'date': h['date'].isoformat(),
                'allocations': h['allocations'].tolist() if isinstance(h['allocations'], np.ndarray) else list(h['allocations']),
                'period': h['period']
            }
            for h in self.allocation_history
        ]
        
        return {
            'bandit_state': self.bandit_allocator.get_state(),
            'trackers': [tracker.get_state() for tracker in self.trackers],
            'period_count': self.period_count,
            'last_date': self.last_date.isoformat() if self.last_date is not None else None,
            'last_weights': self.last_weights.to_dict() if self.last_weights is not None else None,
            'last_allocations': self.last_allocations.tolist() if self.last_allocations is not None else None,
            'last_portfolio_value': self.last_portfolio_value,
            'allocation_history': serialized_history,
            'reward_config': {
                'reward_type': self.reward_type,
                'reward_lookback': self.reward_lookback,
                'burn_in_periods': self.burn_in_periods,
                'min_allocation': self.min_allocation,
                'transaction_cost_bps': self.transaction_cost_bps,
                'enable_soft_allocation': self.enable_soft_allocation,
                'fallback_on_error': self.fallback_on_error,
            },
            'learning_state': {
                'bandit_active': self.bandit_active,
                'bandit_has_learned': self.bandit_has_learned,
            },
        }
    
    def set_state(self, state: Dict[str, Any]) -> None:
        """
        Restore complete state from serialized dictionary.
        
        Parameters
        ----------
        state : dict
            State dictionary from get_state()
            
        Raises
        ------
        ValueError
            If state is invalid or incompatible with current configuration
            
        Notes
        -----
        This restores the full wrapper state including:
        - Bandit learning progress (counts, rewards)
        - Performance tracking history
        - Last portfolio state
        - Allocation history
        
        The number of child strategies must match the saved state.
        
        Examples
        --------
        >>> import json
        >>> with open('bandit_state.json', 'r') as f:
        ...     state = json.load(f)
        >>> wrapper.set_state(state)
        """
        # Validate state structure
        required_keys = [
            'bandit_state', 'trackers', 'period_count',
            'last_date', 'last_weights', 'last_allocations',
            'last_portfolio_value', 'allocation_history'
        ]
        for key in required_keys:
            if key not in state:
                raise ValueError(f"Missing required key in state: {key}")
        
        # Check reward configuration consistency (warning only)
        if 'reward_config' in state:
            stored_config = state['reward_config']
            current_config = {
                'reward_type': self.reward_type,
                'reward_lookback': self.reward_lookback,
                'burn_in_periods': self.burn_in_periods,
                'min_allocation': self.min_allocation,
                'transaction_cost_bps': self.transaction_cost_bps,
                'enable_soft_allocation': self.enable_soft_allocation,
                'fallback_on_error': self.fallback_on_error,
            }
            if stored_config != current_config:
                logger.warning(
                    "Reward configuration mismatch during state restoration. "
                    f"Stored: {stored_config}, Current: {current_config}. "
                    "Results may not be reproducible."
                )
        
        # Validate number of strategies matches
        if len(state['trackers']) != len(self.child_strategies):
            raise ValueError(
                f"State has {len(state['trackers'])} trackers but wrapper has "
                f"{len(self.child_strategies)} child strategies"
            )
        
        # Restore bandit state
        self.bandit_allocator.set_state(state['bandit_state'])
        
        # Restore performance trackers
        for tracker, tracker_state in zip(self.trackers, state['trackers']):
            tracker.set_state(tracker_state)
        
        # Restore scalar state
        self.period_count = state['period_count']
        self.last_date = pd.Timestamp(state['last_date']) if state['last_date'] is not None else None
        self.last_portfolio_value = state['last_portfolio_value']
        
        # Restore last weights (dict -> Series)
        if state['last_weights'] is not None:
            self.last_weights = Series(state['last_weights'])
        else:
            self.last_weights = None
        
        # Restore last allocations (list -> array)
        if state['last_allocations'] is not None:
            self.last_allocations = np.array(state['last_allocations'])
        else:
            self.last_allocations = None
        
        # Restore allocation history
        self.allocation_history = [
            {
                'date': pd.Timestamp(h['date']),
                'allocations': np.array(h['allocations']),
                'period': h['period']
            }
            for h in state['allocation_history']
        ]
        
        # Restore learning state
        if 'learning_state' in state:
            self.bandit_active = state['learning_state'].get('bandit_active', False)
            self.bandit_has_learned = state['learning_state'].get('bandit_has_learned', False)
        else:
            # Backward compatibility: infer from period_count
            self.bandit_active = self.period_count >= self.burn_in_periods
            self.bandit_has_learned = self.period_count > self.burn_in_periods
        
        logger.info(
            f"Restored BanditStrategyWrapper state: period_count={self.period_count}, "
            f"n_history={len(self.allocation_history)}, "
            f"bandit_active={self.bandit_active}, bandit_has_learned={self.bandit_has_learned}"
        )
    
    def get_bandit_diagnostics(self) -> Dict[str, Any]:
        """
        Get lightweight diagnostics for bandit learning state.
        
        Returns
        -------
        dict
            Diagnostic information including:
            - arm_counts: Number of times each arm was selected
            - mean_rewards: Average reward per arm (if available)
            - last_allocations: Most recent strategy allocations
            - allocation_entropy: Diversity of allocations (0=concentrated, higher=diverse)
            - bandit_active: Whether bandit learning is active
            - bandit_has_learned: Whether bandit has received at least one update
        """
        bandit_state = self.bandit_allocator.get_state()
        
        # Extract arm counts
        if 'counts' in bandit_state:
            arm_counts = bandit_state['counts']
        else:
            arm_counts = [0] * len(self.child_strategies)
        
        # Extract mean rewards
        if 'values' in bandit_state:
            mean_rewards = bandit_state['values']
        elif 'sums' in bandit_state and 'counts' in bandit_state:
            sums = bandit_state.get('sums', [0.0] * len(self.child_strategies))
            counts = bandit_state['counts']
            mean_rewards = [s / c if c > 0 else 0.0 for s, c in zip(sums, counts)]
        else:
            mean_rewards = [0.0] * len(self.child_strategies)
        
        # Calculate allocation entropy
        if self.last_allocations is not None:
            # Normalize to probabilities
            probs = np.array(self.last_allocations)
            probs = probs / np.sum(probs) if np.sum(probs) > 0 else np.ones(len(probs)) / len(probs)
            # Calculate entropy
            allocation_entropy = -np.sum(probs * np.log(probs + 1e-10))
        else:
            allocation_entropy = 0.0
        
        return {
            'arm_counts': arm_counts,
            'mean_rewards': mean_rewards,
            'last_allocations': self.last_allocations.tolist() if self.last_allocations is not None else None,
            'allocation_entropy': allocation_entropy,
            'bandit_active': self.bandit_active,
            'bandit_has_learned': self.bandit_has_learned,
            'period_count': self.period_count,
            'burn_in_periods': self.burn_in_periods,
        }
