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
        Bandit algorithm instance (e.g., UCBBandit, ThompsonSamplingBandit)
    strategy : Optional
        Signal generator (unused, kept for interface consistency)
    optimizer : Optional
        Optimizer (unused for bandit wrapper)
    reward_type : str, default='sharpe'
        Type of reward calculation:
        - 'sharpe': Risk-adjusted return (mean/std)
        - 'return': Raw returns (not recommended)
        - 'clipped_sharpe': Bounded Sharpe ratio [-1, 3]
    reward_lookback : int, default=12
        Number of periods to use for reward calculation
    burn_in_periods : int, default=12
        Number of periods to use equal allocation before engaging bandit
    min_allocation : float, default=0.05
        Minimum allocation per strategy (prevents total exclusion)
    transaction_cost_bps : float, default=5.0
        Transaction cost in basis points for reward adjustment
    enable_soft_allocation : bool, default=True
        If True, use soft allocation (weighted average of all strategies)
        If False, use hard allocation (select single best strategy)
    fallback_on_error : bool, default=True
        If True, fall back to equal allocation when child strategy fails
    random_seed : Optional[int], default=None
        Random seed for deterministic behavior
    
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
    >>> bandit = UCBBandit(n_arms=2, exploration_factor=2.0)
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
        reward_type: str = 'sharpe',
        reward_lookback: int = 12,
        burn_in_periods: int = 12,
        min_allocation: float = 0.05,
        transaction_cost_bps: float = 5.0,
        enable_soft_allocation: bool = True,
        fallback_on_error: bool = True,
        random_seed: Optional[int] = None,
        **kwargs
    ):
        """Initialize Bandit Strategy Wrapper."""
        super().__init__(
            name="Bandit Strategy Allocator",
            strategy=strategy,
            optimizer=optimizer,
            **kwargs
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
        
        # State tracking
        self.period_count = 0
        self.last_date: Optional[pd.Timestamp] = None
        self.last_weights: Optional[Series] = None
        self.last_allocations: Optional[np.ndarray] = None
        self.last_portfolio_value: Optional[float] = None
        
        # Performance tracking
        self.trackers = [
            StrategyPerformanceTracker(strategy_name=s.name)
            for s in child_strategies
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
        """
        try:
            # Calculate strategy-specific returns
            strategy_returns = self._calculate_strategy_returns(
                portfolio_state,
                current_date
            )
            
            # Calculate rewards with risk adjustment
            rewards = self._calculate_rewards(strategy_returns)
            
            # Update bandit with rewards for each arm
            for arm_idx, reward in enumerate(rewards):
                self.bandit_allocator.update(arm_idx, reward)
            
            # Track performance
            for arm_idx, (ret, reward) in enumerate(zip(strategy_returns, rewards)):
                allocation = self.last_allocations[arm_idx] if self.last_allocations is not None else 0.0
                self.trackers[arm_idx].add_observation(ret, allocation, current_date)
            
            logger.debug(
                f"Updated rewards at {current_date}: "
                f"returns={[f'{r:.4f}' for r in strategy_returns]}, "
                f"rewards={[f'{r:.4f}' for r in rewards]}"
            )
            
        except Exception as e:
            logger.warning(f"Failed to update rewards: {e}. Skipping update.")
    
    def _calculate_strategy_returns(
        self,
        portfolio_state: PortfolioState,
        current_date: pd.Timestamp
    ) -> List[float]:
        """
        Calculate per-strategy returns for the previous period.
        
        This uses a simplified approach: calculate portfolio return and attribute
        it proportionally to each strategy based on its allocation.
        
        Note: This is an approximation. True attribution would require tracking
        separate sub-portfolios per strategy, which adds significant complexity.
        """
        # Get portfolio return over period
        if self.last_portfolio_value is not None and self.last_portfolio_value > 0:
            portfolio_return = (portfolio_state.equity - self.last_portfolio_value) / self.last_portfolio_value
        else:
            # First period: no return to calculate
            return [0.0] * len(self.child_strategies)
        
        # Attribute return to strategies proportional to their allocation
        # This is a simplification but maintains no-lookahead property
        strategy_returns = [
            portfolio_return * (self.last_allocations[i] if self.last_allocations is not None else 0.0)
            for i in range(len(self.child_strategies))
        ]
        
        return strategy_returns
    
    def _calculate_rewards(self, strategy_returns: List[float]) -> List[float]:
        """
        Calculate rewards from strategy returns based on reward_type.
        
        Applies risk adjustment and transaction cost penalty.
        """
        rewards = []
        
        for arm_idx, current_return in enumerate(strategy_returns):
            tracker = self.trackers[arm_idx]
            
            if self.reward_type == 'return':
                # Raw return (not recommended)
                reward = current_return
                
            elif self.reward_type == 'sharpe':
                # Risk-adjusted return (Sharpe-like)
                metrics = tracker.get_recent_metrics(self.reward_lookback)
                reward = metrics['sharpe']
                
            elif self.reward_type == 'clipped_sharpe':
                # Clipped Sharpe ratio
                metrics = tracker.get_recent_metrics(self.reward_lookback)
                sharpe = metrics['sharpe']
                reward = np.clip(sharpe, -1.0, 3.0)
                
            else:
                raise ValueError(f"Unknown reward_type: {self.reward_type}")
            
            # Apply transaction cost adjustment
            # Cost is proportional to turnover (allocation change)
            if self.last_allocations is not None:
                current_alloc = self.last_allocations[arm_idx]
                # Estimate turnover as allocation change
                # (This is simplified; true cost requires weight change tracking)
                turnover_penalty = abs(current_alloc) * (self.transaction_cost_bps / 10000.0)
                reward -= turnover_penalty
            
            rewards.append(reward)
        
        return rewards
    
    def _get_strategy_allocations(self, date: pd.Timestamp) -> np.ndarray:
        """
        Get strategy allocations from bandit algorithm.
        
        During burn-in period, uses equal allocation.
        After burn-in, queries bandit for allocation.
        """
        n_strategies = len(self.child_strategies)
        
        # Burn-in period: equal allocation
        if self.period_count < self.burn_in_periods:
            allocations = np.ones(n_strategies) / n_strategies
            logger.debug(f"Burn-in period ({self.period_count}/{self.burn_in_periods}): equal allocation")
            return allocations
        
        # Query bandit for selection
        if self.enable_soft_allocation:
            # Soft allocation: use empirical frequencies or Thompson sampling
            allocations = self._compute_soft_allocations()
        else:
            # Hard allocation: select single best arm
            selected_arm = self.bandit_allocator.select_arm(self.period_count)
            allocations = np.zeros(n_strategies)
            allocations[selected_arm] = 1.0
        
        # Apply minimum allocation constraint
        if self.min_allocation > 0:
            allocations = self._apply_min_allocation(allocations)
        
        return allocations
    
    def _compute_soft_allocations(self) -> np.ndarray:
        """
        Compute soft allocations using bandit statistics.
        
        Uses empirical mean estimates to create a softmax-like allocation.
        """
        n_strategies = len(self.child_strategies)
        
        # Get bandit state
        state = self.bandit_allocator.get_state()
        counts = state['counts']
        
        # Get mean values (UCB stores 'values', Thompson needs computation)
        if 'values' in state:
            # UCB case: use stored average rewards
            values = state['values']
        else:
            # Thompson case: compute means from sufficient statistics
            sums = state.get('sums', [0.0] * n_strategies)
            values = [
                sums[i] / counts[i] if counts[i] > 0 else 0.0
                for i in range(n_strategies)
            ]
        
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
            'period': self.period_count
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
            strategy.name: [h['allocations'][i] for h in self.allocation_history]
            for i, strategy in enumerate(self.child_strategies)
        }
        
        dates = [h['date'] for h in self.allocation_history]
        
        return DataFrame(data, index=dates)
    
    def get_diagnostics(self) -> Dict[str, Any]:
        """
        Get comprehensive diagnostic information.
        
        Returns
        -------
        dict
            Contains:
            - 'bandit_state': Current bandit algorithm state
            - 'strategy_metrics': Performance metrics per strategy
            - 'allocation_history': Historical allocations
            - 'current_allocations': Most recent allocations
            - 'period_count': Total periods processed
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
        
        return {
            'bandit_state': bandit_state,
            'strategy_metrics': strategy_metrics,
            'allocation_history': self.allocation_history.copy(),
            'current_allocations': current_allocations,
            'period_count': self.period_count,
            'burn_in_complete': self.period_count >= self.burn_in_periods
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
        
        logger.info(
            f"Restored BanditStrategyWrapper state: period_count={self.period_count}, "
            f"n_history={len(self.allocation_history)}"
        )
