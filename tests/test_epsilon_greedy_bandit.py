"""
Unit tests for EpsilonGreedy bandit algorithm.

Tests ε-Greedy specific logic including selection, updates, and edge cases.
"""

import unittest
import numpy as np
from src.bandits.epsilon_greedy import EpsilonGreedy


class TestEpsilonGreedy(unittest.TestCase):
    """Test cases for EpsilonGreedy bandit algorithm."""
    
    def test_initialization_valid(self):
        """Test initialization with valid parameters."""
        bandit = EpsilonGreedy(n_arms=3, epsilon=0.1)
        
        self.assertEqual(bandit.n_arms, 3)
        self.assertEqual(bandit.epsilon, 0.1)
        np.testing.assert_array_equal(bandit.visits, [0, 0, 0])
        np.testing.assert_array_equal(bandit.satisfaction, [0.0, 0.0, 0.0])
    
    def test_initialization_invalid_epsilon(self):
        """Test initialization fails with invalid epsilon."""
        with self.assertRaises(ValueError) as ctx:
            EpsilonGreedy(n_arms=3, epsilon=-0.1)
        self.assertIn("epsilon must be in [0, 1]", str(ctx.exception))
        
        with self.assertRaises(ValueError):
            EpsilonGreedy(n_arms=3, epsilon=1.5)
    
    def test_pure_exploitation_epsilon_zero(self):
        """Test with epsilon=0 (pure exploitation)."""
        bandit = EpsilonGreedy(n_arms=3, epsilon=0.0)
        
        # All arms have same average initially (0), should pick first (argmax of [0,0,0])
        arm = bandit.select_arm(t=1)
        self.assertEqual(arm, 0)
        
        # Update arm 1 with higher reward
        bandit.update(arm=1, reward=1.0)
        
        # Should now pick arm 1
        arm = bandit.select_arm(t=2)
        self.assertEqual(arm, 1)
        
        # Update arm 2 with even higher reward
        bandit.update(arm=2, reward=2.0)
        
        # Should pick arm 2
        arm = bandit.select_arm(t=3)
        self.assertEqual(arm, 2)
    
    def test_pure_exploration_epsilon_one(self):
        """Test with epsilon=1 (pure exploration)."""
        bandit = EpsilonGreedy(n_arms=3, epsilon=1.0)
        
        # Set seed for reproducibility
        np.random.seed(42)
        
        # Should select randomly
        arms_selected = []
        for _ in range(10):
            arm = bandit.select_arm(t=1)
            arms_selected.append(arm)
            bandit.update(arm, reward=0.1)
        
        # Should have selected different arms (not always the same)
        self.assertGreater(len(set(arms_selected)), 1)
    
    def test_mixed_strategy(self):
        """Test mixed exploration/exploitation."""
        bandit = EpsilonGreedy(n_arms=2, epsilon=0.5)
        
        # Give arm 1 a big advantage
        bandit.update(arm=1, reward=1.0)
        
        # Run many selections to see behavior
        selections = []
        np.random.seed(123)
        for i in range(100):
            arm = bandit.select_arm(t=i+1)
            selections.append(arm)
            # Small reward to maintain advantage
            bandit.update(arm, reward=0.1 if arm == 1 else 0.0)
        
        # Should select arm 1 more often due to higher average
        arm1_count = sum(1 for arm in selections if arm == 1)
        self.assertGreater(arm1_count, 40)  # More than 40% of the time
    
    def test_update_validation(self):
        """Test update method validates arm index."""
        bandit = EpsilonGreedy(n_arms=3, epsilon=0.1)
        
        # Valid update
        bandit.update(arm=0, reward=0.5)
        
        # Invalid arm index
        with self.assertRaises(ValueError) as ctx:
            bandit.update(arm=3, reward=0.5)
        self.assertIn("arm must be in [0, 2]", str(ctx.exception))
        
        with self.assertRaises(ValueError):
            bandit.update(arm=-1, reward=0.5)
    
    def test_get_state(self):
        """Test state serialization."""
        bandit = EpsilonGreedy(n_arms=3, epsilon=0.2)
        bandit.update(arm=0, reward=1.0)
        bandit.update(arm=1, reward=2.0)
        
        state = bandit.get_state()
        
        expected_keys = {'n_arms', 'epsilon', 'visits', 'satisfaction'}
        self.assertEqual(set(state.keys()), expected_keys)
        self.assertEqual(state['n_arms'], 3)
        self.assertEqual(state['epsilon'], 0.2)
        self.assertEqual(state['visits'], [1, 1, 0])
        self.assertEqual(state['satisfaction'], [1.0, 2.0, 0.0])
    
    def test_set_state(self):
        """Test state restoration."""
        bandit1 = EpsilonGreedy(n_arms=3, epsilon=0.2)
        bandit1.update(arm=0, reward=1.0)
        bandit1.update(arm=1, reward=2.0)
        
        state = bandit1.get_state()
        
        bandit2 = EpsilonGreedy(n_arms=3, epsilon=0.2)
        bandit2.set_state(state)
        
        np.testing.assert_array_equal(bandit2.visits, [1, 1, 0])
        np.testing.assert_array_equal(bandit2.satisfaction, [1.0, 2.0, 0.0])
    
    def test_set_state_validation(self):
        """Test set_state validates state."""
        bandit = EpsilonGreedy(n_arms=3, epsilon=0.2)
        
        # Wrong n_arms
        invalid_state = {'n_arms': 4, 'epsilon': 0.2, 'visits': [0,0,0], 'satisfaction': [0,0,0]}
        with self.assertRaises(ValueError) as ctx:
            bandit.set_state(invalid_state)
        self.assertIn("n_arms=4 does not match current n_arms=3", str(ctx.exception))
        
        # Wrong epsilon
        invalid_state = {'n_arms': 3, 'epsilon': 0.3, 'visits': [0,0,0], 'satisfaction': [0,0,0]}
        with self.assertRaises(ValueError) as ctx:
            bandit.set_state(invalid_state)
        self.assertIn("epsilon=0.3 does not match current epsilon=0.2", str(ctx.exception))
    
    def test_reset(self):
        """Test reset functionality."""
        bandit = EpsilonGreedy(n_arms=3, epsilon=0.1)
        bandit.update(arm=0, reward=1.0)
        bandit.update(arm=1, reward=2.0)
        
        # Verify state is not zero
        self.assertFalse(np.all(bandit.visits == 0))
        self.assertFalse(np.all(bandit.satisfaction == 0))
        
        bandit.reset()
        
        # Should be back to initial state
        np.testing.assert_array_equal(bandit.visits, [0, 0, 0])
        np.testing.assert_array_equal(bandit.satisfaction, [0.0, 0.0, 0.0])


if __name__ == '__main__':
    unittest.main()