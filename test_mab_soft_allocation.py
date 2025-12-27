import pandas as pd
import numpy as np
from src.strategies.bandit_strategy_wrapper import BanditStrategyWrapper
from src.bandits import UCBBandit, ThompsonSamplingBandit, EXP3Bandit
from tests.test_bandit_strategy_wrapper import create_dummy_portfolio_state, DummyStrategyWrapper

# Create dummy strategies with DIFFERENT performance
assets = ['AAPL', 'MSFT', 'GOOGL']

class BiasedDummyStrategyWrapper(DummyStrategyWrapper):
    '''Dummy strategy that adds bias to returns'''
    def __init__(self, name, weights, assets, return_bias=0.0):
        super().__init__(name, weights, assets)
        self.return_bias = return_bias

    def get_weights(self, date, portfolio_state):
        weights = super().get_weights(date, portfolio_state)
        return weights

strategies = [
    BiasedDummyStrategyWrapper('Good Strategy', {'AAPL': 0.6, 'MSFT': 0.3, 'GOOGL': 0.1}, assets, return_bias=0.01),  # +1% bias
    BiasedDummyStrategyWrapper('Bad Strategy', {'AAPL': 0.1, 'MSFT': 0.1, 'GOOGL': 0.8}, assets, return_bias=-0.005),  # -0.5% bias
    BiasedDummyStrategyWrapper('Medium Strategy', {'AAPL': 0.4, 'MSFT': 0.4, 'GOOGL': 0.2}, assets, return_bias=0.0)   # neutral
]

print('Testing MAB algorithms with soft allocation and DIFFERENT strategy performance...')

# Test each algorithm with soft allocation
algorithms = [
    ('UCB', UCBBandit(n_arms=3)),
    ('Thompson', ThompsonSamplingBandit(n_arms=3)),
    ('EXP3', EXP3Bandit(n_arms=3))
]

for name, bandit in algorithms:
    print(f'\n=== {name} Bandit (Soft Allocation, Different Performance) ===')

    wrapper = BanditStrategyWrapper(
        child_strategies=strategies,
        bandit_allocator=bandit,
        burn_in_periods=2,
        enable_soft_allocation=True,
        reward_type='return'
    )

    # Simulate some periods with different portfolio returns
    dates = pd.date_range('2023-01-01', periods=8, freq='Q')

    for i, date in enumerate(dates):
        # Create portfolio state with varying returns
        base_return = 0.02 * i  # Base return increases over time
        # Add some noise
        portfolio_return = base_return + np.random.normal(0, 0.005)
        equity = 100000 * (1 + portfolio_return)

        state = create_dummy_portfolio_state(date, equity=equity, assets=assets)

        # Get weights
        weights = wrapper.get_weights(date, state)

        if i >= 2:  # After burn-in
            print(f'Period {i+1}: allocations={[f"{a:.2f}" for a in wrapper.last_allocations]}')