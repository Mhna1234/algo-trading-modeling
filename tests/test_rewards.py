"""
Unit tests for reward calculation module

Tests cover:
- Basic functionality of each reward type
- Clipping behavior
- Edge cases (zero vol, NaN, negative values)
- Boundary conditions
- Integration with compute_reward wrapper
"""

import pytest
import math
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rewards import (
    return_to_reward,
    sharpe_like_reward,
    drawdown_penalized_reward,
    multi_objective_reward,
    compute_reward
)


# ============================================================================
# Test: return_to_reward
# ============================================================================

class TestReturnToReward:
    """Tests for simple return-based reward."""
    
    def test_basic_positive_return(self):
        """Test normal positive return within bounds."""
        reward = return_to_reward(0.03)
        assert reward == 0.03
    
    def test_basic_negative_return(self):
        """Test normal negative return within bounds."""
        reward = return_to_reward(-0.02)
        assert reward == -0.02
    
    def test_zero_return(self):
        """Test zero return."""
        reward = return_to_reward(0.0)
        assert reward == 0.0
    
    def test_clipping_upper_bound(self):
        """Test clipping at upper bound."""
        reward = return_to_reward(0.10, clip=(-0.05, 0.05))
        assert reward == 0.05
    
    def test_clipping_lower_bound(self):
        """Test clipping at lower bound."""
        reward = return_to_reward(-0.10, clip=(-0.05, 0.05))
        assert reward == -0.05
    
    def test_exactly_at_upper_clip(self):
        """Test value exactly at upper clip."""
        reward = return_to_reward(0.05, clip=(-0.05, 0.05))
        assert reward == 0.05
    
    def test_exactly_at_lower_clip(self):
        """Test value exactly at lower clip."""
        reward = return_to_reward(-0.05, clip=(-0.05, 0.05))
        assert reward == -0.05
    
    def test_custom_clip_bounds(self):
        """Test with custom clip bounds."""
        reward = return_to_reward(0.15, clip=(-0.10, 0.20))
        assert reward == 0.15
        
        reward = return_to_reward(0.25, clip=(-0.10, 0.20))
        assert reward == 0.20
    
    def test_nan_handling(self):
        """Test NaN input returns 0."""
        reward = return_to_reward(float('nan'))
        assert reward == 0.0
    
    def test_extreme_positive_value(self):
        """Test extreme positive value gets clipped."""
        reward = return_to_reward(1.0, clip=(-0.05, 0.05))
        assert reward == 0.05
    
    def test_extreme_negative_value(self):
        """Test extreme negative value gets clipped."""
        reward = return_to_reward(-1.0, clip=(-0.05, 0.05))
        assert reward == -0.05


# ============================================================================
# Test: sharpe_like_reward
# ============================================================================

class TestSharpeLikeReward:
    """Tests for Sharpe-like risk-adjusted reward."""
    
    def test_basic_calculation(self):
        """Test basic Sharpe calculation."""
        # 2% return / 1% vol = 2.0 Sharpe
        reward = sharpe_like_reward(0.02, 0.01)
        assert reward == 2.0
    
    def test_higher_volatility_lowers_reward(self):
        """Test that higher vol reduces reward."""
        reward_low_vol = sharpe_like_reward(0.02, 0.01)
        reward_high_vol = sharpe_like_reward(0.02, 0.04)
        assert reward_low_vol > reward_high_vol
    
    def test_negative_return(self):
        """Test negative return gives negative reward."""
        reward = sharpe_like_reward(-0.02, 0.01)
        assert reward == -2.0
    
    def test_zero_return(self):
        """Test zero return gives zero reward."""
        reward = sharpe_like_reward(0.0, 0.01)
        assert reward == 0.0
    
    def test_zero_volatility_with_floor(self):
        """Test that zero vol uses floor to prevent division by zero."""
        reward = sharpe_like_reward(0.01, 0.0, vol_floor=1e-6)
        # Should use vol_floor, giving huge reward (clipped)
        assert reward == 2.0  # Clipped
    
    def test_very_small_volatility(self):
        """Test very small volatility doesn't break calculation."""
        reward = sharpe_like_reward(0.01, 1e-8, vol_floor=1e-6)
        # Should use vol_floor
        assert reward == 2.0  # Clipped
    
    def test_clipping_upper_bound(self):
        """Test clipping at upper Sharpe bound."""
        # 10% return / 1% vol = 10.0, clipped to 2.0
        reward = sharpe_like_reward(0.10, 0.01, clip=(-2.0, 2.0))
        assert reward == 2.0
    
    def test_clipping_lower_bound(self):
        """Test clipping at lower Sharpe bound."""
        # -10% return / 1% vol = -10.0, clipped to -2.0
        reward = sharpe_like_reward(-0.10, 0.01, clip=(-2.0, 2.0))
        assert reward == -2.0
    
    def test_nan_return(self):
        """Test NaN return returns 0."""
        reward = sharpe_like_reward(float('nan'), 0.01)
        assert reward == 0.0
    
    def test_nan_volatility(self):
        """Test NaN volatility returns 0."""
        reward = sharpe_like_reward(0.02, float('nan'))
        assert reward == 0.0
    
    def test_both_nan(self):
        """Test both NaN returns 0."""
        reward = sharpe_like_reward(float('nan'), float('nan'))
        assert reward == 0.0
    
    def test_negative_volatility(self):
        """Test negative volatility is handled (taken as absolute)."""
        reward = sharpe_like_reward(0.02, -0.01)
        assert reward == 2.0  # Should use abs(vol)
    
    def test_custom_clip_bounds(self):
        """Test with custom clip bounds."""
        reward = sharpe_like_reward(0.05, 0.01, clip=(-5.0, 5.0))
        assert reward == 5.0  # 5.0 Sharpe, within bounds
    
    def test_exactly_at_clip_boundary(self):
        """Test value exactly at clip boundary."""
        reward = sharpe_like_reward(0.02, 0.01, clip=(-2.0, 2.0))
        assert reward == 2.0


# ============================================================================
# Test: drawdown_penalized_reward
# ============================================================================

class TestDrawdownPenalizedReward:
    """Tests for drawdown-penalized reward."""
    
    def test_basic_calculation(self):
        """Test basic drawdown penalty."""
        # 5% return - 1.0 * 2% DD = 3%
        reward = drawdown_penalized_reward(0.05, -0.02, lambda_dd=1.0)
        assert abs(reward - 0.03) < 1e-10
    
    def test_no_drawdown(self):
        """Test with zero drawdown (no penalty)."""
        reward = drawdown_penalized_reward(0.05, 0.0, lambda_dd=1.0)
        assert reward == 0.05
    
    def test_positive_drawdown_treated_as_zero(self):
        """Test positive drawdown is treated as zero."""
        reward = drawdown_penalized_reward(0.05, 0.01, lambda_dd=1.0)
        assert reward == 0.05  # No penalty
    
    def test_lambda_scaling(self):
        """Test lambda_dd scales the penalty."""
        reward_1x = drawdown_penalized_reward(0.05, -0.02, lambda_dd=1.0)
        reward_2x = drawdown_penalized_reward(0.05, -0.02, lambda_dd=2.0)
        
        assert abs(reward_1x - 0.03) < 1e-10
        assert abs(reward_2x - 0.01) < 1e-10
        assert reward_1x > reward_2x
    
    def test_zero_lambda(self):
        """Test lambda=0 gives no penalty."""
        reward = drawdown_penalized_reward(0.05, -0.10, lambda_dd=0.0)
        assert reward == 0.05
    
    def test_negative_return_with_drawdown(self):
        """Test negative return with drawdown."""
        # -3% return - 1.0 * 2% DD = -5%
        reward = drawdown_penalized_reward(-0.03, -0.02, lambda_dd=1.0)
        assert abs(reward - (-0.05)) < 1e-10
    
    def test_clipping_upper_bound(self):
        """Test clipping at upper bound."""
        reward = drawdown_penalized_reward(0.15, 0.0, lambda_dd=1.0, clip=(-0.10, 0.10))
        assert reward == 0.10
    
    def test_clipping_lower_bound(self):
        """Test clipping at lower bound."""
        reward = drawdown_penalized_reward(-0.05, -0.10, lambda_dd=1.0, clip=(-0.10, 0.10))
        assert reward == -0.10  # -0.05 - 0.10 = -0.15, clipped
    
    def test_nan_return(self):
        """Test NaN return returns 0."""
        reward = drawdown_penalized_reward(float('nan'), -0.02, lambda_dd=1.0)
        assert reward == 0.0
    
    def test_nan_drawdown(self):
        """Test NaN drawdown returns 0."""
        reward = drawdown_penalized_reward(0.05, float('nan'), lambda_dd=1.0)
        assert reward == 0.0
    
    def test_both_nan(self):
        """Test both NaN returns 0."""
        reward = drawdown_penalized_reward(float('nan'), float('nan'), lambda_dd=1.0)
        assert reward == 0.0
    
    def test_large_drawdown(self):
        """Test large drawdown penalty."""
        # 10% return - 1.0 * 20% DD = -10%
        reward = drawdown_penalized_reward(0.10, -0.20, lambda_dd=1.0)
        assert reward == -0.10


# ============================================================================
# Test: multi_objective_reward
# ============================================================================

class TestMultiObjectiveReward:
    """Tests for multi-objective reward."""
    
    def test_basic_calculation(self):
        """Test basic multi-objective calculation."""
        reward = multi_objective_reward(
            ret=0.02,
            vol=0.01,
            drawdown=-0.03,
            weight_return=0.3,
            weight_sharpe=0.4,
            weight_dd=0.3
        )
        # Should be combination of all three
        assert isinstance(reward, float)
        assert -1.0 <= reward <= 1.0  # Within default clip
    
    def test_nan_handling(self):
        """Test NaN in any input returns 0."""
        reward = multi_objective_reward(float('nan'), 0.01, -0.02)
        assert reward == 0.0
        
        reward = multi_objective_reward(0.02, float('nan'), -0.02)
        assert reward == 0.0
        
        reward = multi_objective_reward(0.02, 0.01, float('nan'))
        assert reward == 0.0
    
    def test_custom_weights(self):
        """Test with custom weights."""
        reward = multi_objective_reward(
            ret=0.05,
            vol=0.02,
            drawdown=-0.01,
            weight_return=1.0,
            weight_sharpe=0.0,
            weight_dd=0.0
        )
        # Should be close to raw return (with some Sharpe scaling)
        assert isinstance(reward, float)
    
    def test_clipping(self):
        """Test clipping works."""
        reward = multi_objective_reward(
            ret=0.50,
            vol=0.01,
            drawdown=0.0,
            clip=(-0.5, 0.5)
        )
        assert -0.5 <= reward <= 0.5


# ============================================================================
# Test: compute_reward wrapper
# ============================================================================

class TestComputeReward:
    """Tests for compute_reward convenience wrapper."""
    
    def test_return_type(self):
        """Test 'return' reward type."""
        reward = compute_reward(0.03, reward_type='return')
        assert reward == 0.03
    
    def test_sharpe_type(self):
        """Test 'sharpe' reward type."""
        reward = compute_reward(0.02, vol=0.01, reward_type='sharpe')
        assert reward == 2.0
    
    def test_sharpe_type_missing_vol(self):
        """Test sharpe type fails without volatility."""
        with pytest.raises(ValueError, match="volatility required"):
            compute_reward(0.02, reward_type='sharpe')
    
    def test_drawdown_type(self):
        """Test 'drawdown' reward type."""
        reward = compute_reward(0.05, drawdown=-0.02, reward_type='drawdown')
        assert abs(reward - 0.03) < 1e-10
    
    def test_drawdown_type_missing_dd(self):
        """Test drawdown type fails without drawdown."""
        with pytest.raises(ValueError, match="drawdown required"):
            compute_reward(0.05, reward_type='drawdown')
    
    def test_multi_type(self):
        """Test 'multi' reward type."""
        reward = compute_reward(
            0.02,
            vol=0.01,
            drawdown=-0.03,
            reward_type='multi'
        )
        assert isinstance(reward, float)
    
    def test_multi_type_missing_inputs(self):
        """Test multi type fails without vol or drawdown."""
        with pytest.raises(ValueError, match="volatility and drawdown required"):
            compute_reward(0.02, reward_type='multi')
    
    def test_unknown_type(self):
        """Test unknown reward type raises error."""
        with pytest.raises(ValueError, match="Unknown reward_type"):
            compute_reward(0.02, reward_type='invalid')


# ============================================================================
# Test: Edge Cases and Numerical Stability
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and numerical stability."""
    
    def test_very_large_return(self):
        """Test very large return is handled."""
        reward = return_to_reward(10.0)
        assert reward == 0.05  # Clipped
    
    def test_very_small_return(self):
        """Test very small return is handled."""
        reward = return_to_reward(1e-10)
        assert abs(reward - 1e-10) < 1e-15
    
    def test_sharpe_with_matching_return_vol(self):
        """Test Sharpe when return equals volatility."""
        reward = sharpe_like_reward(0.01, 0.01)
        assert reward == 1.0
    
    def test_drawdown_equals_return(self):
        """Test when drawdown magnitude equals return."""
        reward = drawdown_penalized_reward(0.05, -0.05, lambda_dd=1.0)
        assert reward == 0.0
    
    def test_multiple_consecutive_calls(self):
        """Test function is stateless (multiple calls give same result)."""
        r1 = sharpe_like_reward(0.02, 0.01)
        r2 = sharpe_like_reward(0.02, 0.01)
        assert r1 == r2
    
    def test_infinity_handling_sharpe(self):
        """Test infinity in Sharpe calculation."""
        reward = sharpe_like_reward(float('inf'), 0.01)
        assert reward == 2.0  # Clipped
        
        # Negative infinity
        reward = sharpe_like_reward(float('-inf'), 0.01)
        assert reward == -2.0  # Clipped
    
    def test_all_zeros(self):
        """Test with all zero inputs."""
        reward = multi_objective_reward(0.0, 0.0, 0.0)
        assert isinstance(reward, float)


# ============================================================================
# Test: Comparison and Ordering
# ============================================================================

class TestComparisonAndOrdering:
    """Tests that rewards maintain proper ordering."""
    
    def test_higher_return_gives_higher_reward(self):
        """Test ordering is preserved for returns."""
        r1 = return_to_reward(0.02)
        r2 = return_to_reward(0.04)
        assert r2 > r1
    
    def test_higher_sharpe_gives_higher_reward(self):
        """Test ordering for Sharpe ratios."""
        s1 = sharpe_like_reward(0.02, 0.02)  # Sharpe = 1.0
        s2 = sharpe_like_reward(0.04, 0.02)  # Sharpe = 2.0
        assert s2 > s1
    
    def test_lower_drawdown_gives_higher_reward(self):
        """Test that lower drawdown gives higher reward."""
        d1 = drawdown_penalized_reward(0.05, -0.10, lambda_dd=1.0)
        d2 = drawdown_penalized_reward(0.05, -0.02, lambda_dd=1.0)
        assert d2 > d1  # Less drawdown = higher reward


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
