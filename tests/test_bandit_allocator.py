"""
Unit tests for BanditAllocator base class.

Tests the interface and validation logic without testing specific algorithms.
"""

import unittest
from src.bandits.base import BanditAllocator


class MockBandit(BanditAllocator):
    """Mock implementation for testing base class."""
    
    def __init__(self, n_arms: int):
        super().__init__(n_arms)
        self.selections = []
        self.updates = []
    
    def select_arm(self, t: int) -> int:
        """Always select arm 0."""
        return 0
    
    def update(self, arm: int, reward: float) -> None:
        """Record update."""
        super().update(arm, reward)  # Validates arm index
        self.updates.append((arm, reward))


class TestBanditAllocator(unittest.TestCase):
    """Test cases for BanditAllocator base class."""
    
    def test_initialization_valid(self):
        """Test successful initialization with valid n_arms."""
        bandit = MockBandit(n_arms=5)
        self.assertEqual(bandit.n_arms, 5)
    
    def test_initialization_minimum_arms(self):
        """Test initialization with minimum n_arms=2."""
        bandit = MockBandit(n_arms=2)
        self.assertEqual(bandit.n_arms, 2)
    
    def test_initialization_invalid_too_few_arms(self):
        """Test initialization fails with n_arms < 2."""
        with self.assertRaises(ValueError) as ctx:
            MockBandit(n_arms=1)
        self.assertIn("n_arms must be >= 2", str(ctx.exception))
    
    def test_initialization_invalid_zero_arms(self):
        """Test initialization fails with n_arms=0."""
        with self.assertRaises(ValueError):
            MockBandit(n_arms=0)
    
    def test_initialization_invalid_negative_arms(self):
        """Test initialization fails with negative n_arms."""
        with self.assertRaises(ValueError):
            MockBandit(n_arms=-5)
    
    def test_update_validates_arm_in_range(self):
        """Test update() validates arm is in valid range."""
        bandit = MockBandit(n_arms=3)
        
        # Valid arms should work
        bandit.update(arm=0, reward=0.5)
        bandit.update(arm=1, reward=-0.2)
        bandit.update(arm=2, reward=0.0)
        
        self.assertEqual(len(bandit.updates), 3)
    
    def test_update_rejects_arm_too_large(self):
        """Test update() rejects arm >= n_arms."""
        bandit = MockBandit(n_arms=3)
        
        with self.assertRaises(ValueError) as ctx:
            bandit.update(arm=3, reward=0.5)
        self.assertIn("arm must be in [0, 2]", str(ctx.exception))
    
    def test_update_rejects_negative_arm(self):
        """Test update() rejects negative arm index."""
        bandit = MockBandit(n_arms=3)
        
        with self.assertRaises(ValueError) as ctx:
            bandit.update(arm=-1, reward=0.5)
        self.assertIn("arm must be in [0, 2]", str(ctx.exception))
    
    def test_update_accepts_negative_rewards(self):
        """Test update() accepts negative rewards."""
        bandit = MockBandit(n_arms=3)
        bandit.update(arm=1, reward=-0.5)
        
        self.assertEqual(bandit.updates[-1], (1, -0.5))
    
    def test_update_accepts_zero_rewards(self):
        """Test update() accepts zero rewards."""
        bandit = MockBandit(n_arms=3)
        bandit.update(arm=1, reward=0.0)
        
        self.assertEqual(bandit.updates[-1], (1, 0.0))
    
    def test_get_state_returns_dict(self):
        """Test get_state() returns dictionary."""
        bandit = MockBandit(n_arms=5)
        state = bandit.get_state()
        
        self.assertIsInstance(state, dict)
        self.assertIn('n_arms', state)
        self.assertEqual(state['n_arms'], 5)
    
    def test_set_state_validates_n_arms(self):
        """Test set_state() validates n_arms matches."""
        bandit = MockBandit(n_arms=5)
        
        # Valid state should work
        valid_state = {'n_arms': 5}
        bandit.set_state(valid_state)
        
        # Mismatched n_arms should fail
        invalid_state = {'n_arms': 3}
        with self.assertRaises(ValueError) as ctx:
            bandit.set_state(invalid_state)
        self.assertIn("does not match", str(ctx.exception))
    
    def test_select_arm_returns_int(self):
        """Test select_arm() returns integer."""
        bandit = MockBandit(n_arms=3)
        arm = bandit.select_arm(t=0)
        
        self.assertIsInstance(arm, int)
    
    def test_select_arm_returns_valid_range(self):
        """Test select_arm() returns arm in valid range."""
        bandit = MockBandit(n_arms=5)
        
        for t in range(10):
            arm = bandit.select_arm(t)
            self.assertGreaterEqual(arm, 0)
            self.assertLess(arm, 5)
    
    def test_reset_exists(self):
        """Test reset() method exists and is callable."""
        bandit = MockBandit(n_arms=3)
        bandit.update(arm=1, reward=0.5)
        
        # Should not raise
        bandit.reset()


if __name__ == '__main__':
    unittest.main()
