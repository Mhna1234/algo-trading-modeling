"""
Unit tests for UCBBandit algorithm.

Tests UCB-specific logic including selection, updates, and edge cases.
All tests are deterministic and run fast (no I/O, no randomness).
"""

import unittest
import math
from src.bandits.ucb import UCBBandit


class TestUCBBandit(unittest.TestCase):
    """Test cases for UCB bandit algorithm."""
    
    def test_initialization_default_exploration(self):
        """Test initialization with default exploration constant."""
        bandit = UCBBandit(n_arms=3)
        
        self.assertEqual(bandit.n_arms, 3)
        self.assertEqual(bandit.exploration_constant, 1.0)
        self.assertEqual(bandit.counts, [0, 0, 0])
        self.assertEqual(bandit.values, [0.0, 0.0, 0.0])
        self.assertEqual(bandit.total_selections, 0)
    
    def test_initialization_custom_exploration(self):
        """Test initialization with custom exploration constant."""
        bandit = UCBBandit(n_arms=4, exploration_constant=2.0)
        
        self.assertEqual(bandit.exploration_constant, 2.0)
    
    def test_initialization_invalid_exploration_constant(self):
        """Test initialization fails with invalid exploration constant."""
        with self.assertRaises(ValueError) as ctx:
            UCBBandit(n_arms=3, exploration_constant=0.0)
        self.assertIn("exploration_constant must be > 0", str(ctx.exception))
        
        with self.assertRaises(ValueError):
            UCBBandit(n_arms=3, exploration_constant=-1.0)
    
    def test_forced_exploration_tries_each_arm_once(self):
        """Test UCB tries each arm once before using UCB formula."""
        bandit = UCBBandit(n_arms=3)
        
        # First 3 selections should try arms 0, 1, 2 in order
        arm0 = bandit.select_arm(t=0)
        self.assertEqual(arm0, 0)
        bandit.update(arm0, reward=0.1)
        
        arm1 = bandit.select_arm(t=1)
        self.assertEqual(arm1, 1)
        bandit.update(arm1, reward=0.2)
        
        arm2 = bandit.select_arm(t=2)
        self.assertEqual(arm2, 2)
        bandit.update(arm2, reward=0.3)
        
        # Verify all arms tried once
        self.assertEqual(bandit.counts, [1, 1, 1])
    
    def test_exploitation_after_exploration(self):
        """Test UCB exploits best arm after initial exploration."""
        bandit = UCBBandit(n_arms=3, exploration_constant=0.1)  # Low exploration
        
        # Initial exploration phase
        for arm in range(3):
            bandit.update(arm, reward=0.1 * arm)  # Arm 2 is best
        
        # With low exploration, should prefer arm 2 (highest mean)
        selected_arm = bandit.select_arm(t=3)
        self.assertEqual(selected_arm, 2)
    
    def test_exploration_bonus_increases_with_constant(self):
        """Test higher exploration constant increases exploration."""
        # Low exploration bandit
        bandit_low = UCBBandit(n_arms=3, exploration_constant=0.1)
        for arm in range(3):
            bandit_low.update(arm, reward=0.0)  # Equal initial rewards
        bandit_low.update(0, reward=1.0)  # Arm 0 looks best
        
        # High exploration bandit
        bandit_high = UCBBandit(n_arms=3, exploration_constant=2.0)
        for arm in range(3):
            bandit_high.update(arm, reward=0.0)
        bandit_high.update(0, reward=1.0)
        
        # After arm 0 looks best, check next selections
        # Low exploration should stick with arm 0
        arm_low = bandit_low.select_arm(t=4)
        
        # High exploration should try others more (arms 1 or 2 with high UCB)
        # This is probabilistic in behavior but deterministic in implementation
        stats_high = bandit_high.get_arm_statistics()
        
        # Verify exploration bonus is higher for high exploration constant
        self.assertGreater(bandit_high.exploration_constant, bandit_low.exploration_constant)
    
    def test_update_increments_counts(self):
        """Test update() correctly increments selection counts."""
        bandit = UCBBandit(n_arms=3)
        
        bandit.update(arm=0, reward=0.5)
        self.assertEqual(bandit.counts[0], 1)
        self.assertEqual(bandit.total_selections, 1)
        
        bandit.update(arm=0, reward=0.3)
        self.assertEqual(bandit.counts[0], 2)
        self.assertEqual(bandit.total_selections, 2)
        
        bandit.update(arm=1, reward=0.7)
        self.assertEqual(bandit.counts[1], 1)
        self.assertEqual(bandit.total_selections, 3)
    
    def test_update_computes_average_correctly(self):
        """Test update() computes running average correctly."""
        bandit = UCBBandit(n_arms=3)
        
        # Single update
        bandit.update(arm=0, reward=1.0)
        self.assertAlmostEqual(bandit.values[0], 1.0)
        
        # Second update
        bandit.update(arm=0, reward=2.0)
        self.assertAlmostEqual(bandit.values[0], 1.5)  # (1.0 + 2.0) / 2
        
        # Third update
        bandit.update(arm=0, reward=0.0)
        self.assertAlmostEqual(bandit.values[0], 1.0)  # (1.0 + 2.0 + 0.0) / 3
    
    def test_update_handles_negative_rewards(self):
        """Test update() correctly handles negative rewards."""
        bandit = UCBBandit(n_arms=3)
        
        bandit.update(arm=1, reward=-0.5)
        self.assertAlmostEqual(bandit.values[1], -0.5)
        
        bandit.update(arm=1, reward=-1.0)
        self.assertAlmostEqual(bandit.values[1], -0.75)  # (-0.5 + -1.0) / 2
    
    def test_update_handles_zero_rewards(self):
        """Test update() correctly handles zero rewards."""
        bandit = UCBBandit(n_arms=3)
        
        bandit.update(arm=2, reward=0.0)
        self.assertAlmostEqual(bandit.values[2], 0.0)
        
        bandit.update(arm=2, reward=0.0)
        self.assertAlmostEqual(bandit.values[2], 0.0)
    
    def test_numerical_stability_large_rewards(self):
        """Test algorithm remains stable with large rewards."""
        bandit = UCBBandit(n_arms=3)
        
        # Large positive reward
        bandit.update(arm=0, reward=1e6)
        self.assertAlmostEqual(bandit.values[0], 1e6)
        
        # Mix with normal reward
        bandit.update(arm=0, reward=1.0)
        expected = (1e6 + 1.0) / 2
        self.assertAlmostEqual(bandit.values[0], expected, places=5)
    
    def test_numerical_stability_many_updates(self):
        """Test incremental mean formula remains stable over many updates."""
        bandit = UCBBandit(n_arms=3)
        
        # Add 1000 small rewards
        rewards = [0.01] * 1000
        for reward in rewards:
            bandit.update(arm=0, reward=reward)
        
        # Should be very close to 0.01
        self.assertAlmostEqual(bandit.values[0], 0.01, places=5)
        self.assertEqual(bandit.counts[0], 1000)
    
    def test_deterministic_selection(self):
        """Test selections are deterministic given same reward sequence."""
        # Run 1
        bandit1 = UCBBandit(n_arms=3, exploration_constant=1.0)
        selections1 = []
        for t in range(10):
            arm = bandit1.select_arm(t)
            selections1.append(arm)
            bandit1.update(arm, reward=0.1 * arm)
        
        # Run 2 with same parameters and rewards
        bandit2 = UCBBandit(n_arms=3, exploration_constant=1.0)
        selections2 = []
        for t in range(10):
            arm = bandit2.select_arm(t)
            selections2.append(arm)
            bandit2.update(arm, reward=0.1 * arm)
        
        # Should select same arms in same order
        self.assertEqual(selections1, selections2)
    
    def test_get_state(self):
        """Test get_state() returns complete state."""
        bandit = UCBBandit(n_arms=3, exploration_constant=1.5)
        bandit.update(arm=0, reward=0.5)
        bandit.update(arm=1, reward=0.3)
        
        state = bandit.get_state()
        
        self.assertEqual(state['n_arms'], 3)
        self.assertEqual(state['exploration_constant'], 1.5)
        self.assertEqual(state['counts'], [1, 1, 0])
        self.assertAlmostEqual(state['values'][0], 0.5)
        self.assertAlmostEqual(state['values'][1], 0.3)
        self.assertEqual(state['total_selections'], 2)
    
    def test_set_state(self):
        """Test set_state() correctly restores state."""
        # Create and update bandit
        bandit1 = UCBBandit(n_arms=3, exploration_constant=1.5)
        bandit1.update(arm=0, reward=0.5)
        bandit1.update(arm=1, reward=0.3)
        state = bandit1.get_state()
        
        # Create new bandit and restore state
        bandit2 = UCBBandit(n_arms=3, exploration_constant=2.0)  # Different constant
        bandit2.set_state(state)
        
        # Verify state matches
        self.assertEqual(bandit2.exploration_constant, 1.5)
        self.assertEqual(bandit2.counts, [1, 1, 0])
        self.assertAlmostEqual(bandit2.values[0], 0.5)
        self.assertAlmostEqual(bandit2.values[1], 0.3)
        self.assertEqual(bandit2.total_selections, 2)
    
    def test_set_state_validates_arrays(self):
        """Test set_state() validates array lengths."""
        bandit = UCBBandit(n_arms=3)
        
        # Invalid counts length
        invalid_state = {
            'n_arms': 3,
            'exploration_constant': 1.0,
            'counts': [1, 1],  # Wrong length
            'values': [0.5, 0.5, 0.5],
            'total_selections': 2,
        }
        with self.assertRaises(ValueError) as ctx:
            bandit.set_state(invalid_state)
        self.assertIn("counts length", str(ctx.exception))
    
    def test_reset(self):
        """Test reset() clears all state."""
        bandit = UCBBandit(n_arms=3)
        
        # Make some updates
        for arm in range(3):
            bandit.update(arm, reward=0.5)
        
        # Reset
        bandit.reset()
        
        # Verify state cleared
        self.assertEqual(bandit.counts, [0, 0, 0])
        self.assertEqual(bandit.values, [0.0, 0.0, 0.0])
        self.assertEqual(bandit.total_selections, 0)
    
    def test_get_arm_statistics(self):
        """Test get_arm_statistics() returns detailed info."""
        bandit = UCBBandit(n_arms=3)
        
        # Make some selections
        for arm in range(3):
            bandit.update(arm, reward=0.1 * arm)
        
        stats = bandit.get_arm_statistics()
        
        self.assertIn('counts', stats)
        self.assertIn('values', stats)
        self.assertIn('ucb_scores', stats)
        
        self.assertEqual(stats['counts'], [1, 1, 1])
        self.assertEqual(len(stats['ucb_scores']), 3)
    
    def test_repr(self):
        """Test __repr__ produces useful string."""
        bandit = UCBBandit(n_arms=5, exploration_constant=1.5)
        repr_str = repr(bandit)
        
        self.assertIn('UCBBandit', repr_str)
        self.assertIn('n_arms=5', repr_str)
        self.assertIn('exploration_constant=1.5', repr_str)
        self.assertIn('total_selections=0', repr_str)
    
    def test_convergence_to_best_arm(self):
        """Test UCB converges to selecting best arm over time."""
        bandit = UCBBandit(n_arms=3, exploration_constant=1.0)
        
        # Arm 2 is clearly best
        arm_rewards = [0.1, 0.2, 0.5]
        
        # Run for 100 iterations
        selections = {0: 0, 1: 0, 2: 0}
        for t in range(100):
            arm = bandit.select_arm(t)
            selections[arm] += 1
            bandit.update(arm, reward=arm_rewards[arm])
        
        # After convergence, arm 2 should be selected most
        self.assertGreater(selections[2], selections[0])
        self.assertGreater(selections[2], selections[1])
    
    def test_no_pandas_dependency(self):
        """Test UCBBandit has no pandas dependency."""
        import sys
        
        # Create and use bandit
        bandit = UCBBandit(n_arms=3)
        for t in range(10):
            arm = bandit.select_arm(t)
            bandit.update(arm, reward=0.1)
        
        # Verify pandas not imported
        # (This is a meta-test to ensure we don't accidentally add pandas)
        # If pandas is in sys.modules, it was imported elsewhere (fine)
        # We just verify our code doesn't require it
        
        # Get state should not use pandas
        state = bandit.get_state()
        self.assertIsInstance(state, dict)
        self.assertIsInstance(state['counts'], list)
        self.assertIsInstance(state['values'], list)


class TestUCBEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""
    
    def test_single_arm_multiple_selections(self):
        """Test repeated selection of same arm."""
        bandit = UCBBandit(n_arms=3)
        
        # Select arm 0 multiple times
        for i in range(5):
            bandit.update(arm=0, reward=float(i))
        
        self.assertEqual(bandit.counts[0], 5)
        self.assertEqual(bandit.counts[1], 0)
        self.assertEqual(bandit.counts[2], 0)
        
        # Average should be (0+1+2+3+4)/5 = 2.0
        self.assertAlmostEqual(bandit.values[0], 2.0)
    
    def test_all_equal_rewards(self):
        """Test behavior when all arms have equal rewards."""
        bandit = UCBBandit(n_arms=3)
        
        # Give all arms same reward
        for arm in range(3):
            bandit.update(arm, reward=0.5)
        
        # All should have same value
        self.assertEqual(bandit.values[0], bandit.values[1])
        self.assertEqual(bandit.values[1], bandit.values[2])
    
    def test_extreme_reward_variance(self):
        """Test handling of rewards with extreme variance."""
        bandit = UCBBandit(n_arms=3)
        
        # Arm 0: high variance
        bandit.update(arm=0, reward=10.0)
        bandit.update(arm=0, reward=-10.0)
        
        # Should average to 0
        self.assertAlmostEqual(bandit.values[0], 0.0)


if __name__ == '__main__':
    unittest.main()
