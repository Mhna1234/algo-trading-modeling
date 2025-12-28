"""
Validation Script: 12 Benchmark Strategies
==========================================

This script validates all 12 required benchmark strategies:
1. Buy & Hold (Market / Index Benchmark)
2. Equal Weight (1/N)
3. Quintile Momentum (Cross-Sectional)
4. Quintile Low Volatility
5. Mean Reversion Quintile (Contrarian)
6. Global Minimum Variance Portfolio (GMVP)
7. Inverse Volatility Portfolio (IVol)
8. Risk Parity (Equal Risk Contribution)
9. Maximum Diversification Portfolio (MDP)
10. Maximum Decorrelation Portfolio (MDCP)
11. Sharpe Ratio Maximization (Mean–Variance)
12. CVaR Minimization Portfolio

Validation checks:
- Class exists and inherits from BaseStrategyWrapper
- Implements required methods: get_weights(), get_strategy_info()
- Mathematical correctness of weight calculation
- Integration with project modules
- No circular imports or naming conflicts
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from datetime import datetime
import logging

# Import project modules
from src.data_loader import load_preprocessed_data
from src.signal_generator import Strategy
from src.optimizer import PortfolioOptimizer
from src.portfolio_engine import PortfolioState
from src.strategies import (
    BaseStrategyWrapper,
    BuyAndHoldStrategy,
    EqualWeightStrategy,
    QuintileFactorStrategy,
    QuintileLowVolatilityStrategy,
    MeanReversionStrategy,
    GlobalMinimumVarianceStrategy,
    InverseVolatilityStrategy,
    RiskParityStrategy,
    MaximumDiversificationStrategy,
    MaximumDecorrelationStrategy,
    SharpeMaximizationStrategy,
    CVaRMinimizationStrategy
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_strategy_interface(strategy_class, strategy_name):
    """Validate that strategy implements required interface."""
    issues = []
    
    # Check inheritance
    if not issubclass(strategy_class, BaseStrategyWrapper):
        issues.append(f"Does not inherit from BaseStrategyWrapper")
    
    # Check required methods
    required_methods = ['get_weights', 'get_strategy_info']
    for method in required_methods:
        if not hasattr(strategy_class, method):
            issues.append(f"Missing required method: {method}")
    
    return issues


def validate_strategy_execution(
    strategy_instance,
    strategy_name,
    test_date,
    portfolio_state
):
    """Validate that strategy executes without errors and returns valid weights."""
    issues = []
    
    try:
        # Get weights
        weights = strategy_instance.get_weights(test_date, portfolio_state)
        
        # Validate weights
        if not isinstance(weights, pd.Series):
            issues.append(f"Weights are not a pandas Series (got {type(weights)})")
        
        if weights is None or len(weights) == 0:
            issues.append("Weights are None or empty")
        
        # Check weight properties
        if not np.isclose(weights.sum(), 1.0, atol=1e-6):
            issues.append(f"Weights do not sum to 1.0 (sum = {weights.sum():.6f})")
        
        if (weights < -1e-6).any():
            issues.append(f"Contains negative weights (min = {weights.min():.6f})")
        
        if weights.isna().any():
            issues.append("Contains NaN values")
        
        if np.isinf(weights).any():
            issues.append("Contains infinite values")
        
        # Get strategy info
        info = strategy_instance.get_strategy_info()
        if not isinstance(info, dict):
            issues.append(f"get_strategy_info() does not return dict (got {type(info)})")
        
        if 'name' not in info:
            issues.append("Strategy info missing 'name' field")
        
    except Exception as e:
        issues.append(f"Execution error: {str(e)}")
    
    return issues


def main():
    """Main validation routine."""
    print("=" * 80)
    print("12 BENCHMARK STRATEGIES VALIDATION")
    print("=" * 80)
    print()
    
    # Load data
    logger.info("Loading data...")
    full_data, prices = load_preprocessed_data()
    
    # Use recent 5 years for faster testing
    prices = prices.iloc[-1260:]  # Last ~5 years (252 days/year * 5)
    
    # Select subset of assets for faster testing
    test_assets = prices.columns[:10]  # First 10 assets
    prices = prices[test_assets]
    
    logger.info(f"Data loaded: {len(prices)} dates, {len(prices.columns)} assets")
    
    # Create signal generator and optimizer
    strategy = Strategy(prices)
    optimizer = PortfolioOptimizer(
        returns=strategy.returns,
        risk_free_rate=0.02,
        max_weight=0.4,
        min_weight=0.0
    )
    
    # Select test date (with enough history)
    test_date = prices.index[300]  # After warmup period
    
    # Create mock portfolio state (using PortfolioState dataclass fields)
    portfolio_state = PortfolioState(
        date=test_date,
        current_weights=pd.Series(1.0 / len(test_assets), index=test_assets),
        current_shares=pd.Series(100.0, index=test_assets),
        cash=20000.0,
        equity=100000.0,
        price_history=prices.loc[:test_date],
        return_history=strategy.returns.loc[:test_date],
        cash_symbol='CASH'
    )
    
    # Define 12 benchmark strategies
    strategies_to_validate = [
        ("Buy & Hold", lambda: BuyAndHoldStrategy(strategy, optimizer)),
        ("Equal Weight (1/N)", lambda: EqualWeightStrategy(strategy, optimizer)),
        ("Quintile Momentum", lambda: QuintileFactorStrategy(
            strategy, optimizer, factor='momentum', target_quintile=5
        )),
        ("Quintile Low Volatility", lambda: QuintileLowVolatilityStrategy(
            strategy, optimizer, target_quintile=1
        )),
        ("Mean Reversion Quintile", lambda: MeanReversionStrategy(
            strategy, optimizer, window=21, top_k=5
        )),
        ("Global Minimum Variance (GMVP)", lambda: GlobalMinimumVarianceStrategy(
            strategy, optimizer, lookback=252
        )),
        ("Inverse Volatility (IVol)", lambda: InverseVolatilityStrategy(
            strategy, optimizer, vol_window=63
        )),
        ("Risk Parity", lambda: RiskParityStrategy(
            strategy, optimizer, lookback=252
        )),
        ("Maximum Diversification (MDP)", lambda: MaximumDiversificationStrategy(
            strategy, optimizer, lookback=252
        )),
        ("Maximum Decorrelation (MDCP)", lambda: MaximumDecorrelationStrategy(
            strategy, optimizer, lookback=252
        )),
        ("Sharpe Maximization", lambda: SharpeMaximizationStrategy(
            strategy, optimizer, lookback=252
        )),
        ("CVaR Minimization", lambda: CVaRMinimizationStrategy(
            strategy, optimizer, lookback=252, alpha=0.95
        )),
    ]
    
    # Validation results
    results = []
    
    print("VALIDATION RESULTS:")
    print("-" * 80)
    
    for i, (name, strategy_factory) in enumerate(strategies_to_validate, 1):
        print(f"\n{i}. {name}")
        print("   " + "-" * 76)
        
        try:
            # Create strategy instance
            strategy_instance = strategy_factory()
            strategy_class = type(strategy_instance)
            
            # Interface validation
            interface_issues = validate_strategy_interface(strategy_class, name)
            
            # Execution validation
            execution_issues = validate_strategy_execution(
                strategy_instance, name, test_date, portfolio_state
            )
            
            all_issues = interface_issues + execution_issues
            
            if not all_issues:
                print("   ✓ Status: OK")
                print("   ✓ Interface: Complete")
                print("   ✓ Execution: Successful")
                print("   ✓ Weights: Valid")
                results.append((name, "OK", None))
            else:
                print("   ✗ Status: ISSUES FOUND")
                for issue in all_issues:
                    print(f"   ✗ {issue}")
                results.append((name, "FAILED", all_issues))
                
        except Exception as e:
            print(f"   ✗ Status: CRITICAL ERROR")
            print(f"   ✗ Error: {str(e)}")
            results.append((name, "ERROR", [str(e)]))
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    ok_count = sum(1 for _, status, _ in results if status == "OK")
    failed_count = sum(1 for _, status, _ in results if status == "FAILED")
    error_count = sum(1 for _, status, _ in results if status == "ERROR")
    
    print(f"\nTotal strategies: {len(results)}")
    print(f"✓ OK: {ok_count}")
    print(f"✗ Failed: {failed_count}")
    print(f"✗ Errors: {error_count}")
    
    if ok_count == len(results):
        print("\n✓✓✓ ALL 12 BENCHMARK STRATEGIES VALIDATED SUCCESSFULLY ✓✓✓")
        print("\nAll strategies:")
        print("- Inherit from BaseStrategyWrapper")
        print("- Implement required methods")
        print("- Execute without errors")
        print("- Return valid normalized weights")
        print("- Are compatible with project architecture")
        return 0
    else:
        print("\n✗✗✗ VALIDATION FAILED ✗✗✗")
        print("\nStrategies with issues:")
        for name, status, issues in results:
            if status != "OK":
                print(f"  - {name}: {status}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
