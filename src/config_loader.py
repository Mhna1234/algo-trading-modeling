"""
Configuration Loader Module

This module provides functionality to load and validate configuration from YAML files.
Supports environment variable substitution and configuration validation.

Author: Configuration Loader
Date: December 2025
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
import logging
import pandas as pd

# Make dotenv optional (not available in Lambda)
try:
    from dotenv import load_dotenv
except ImportError:
    # Provide no-op fallback (Lambda uses environment variables directly)
    def load_dotenv(*args, **kwargs):
        pass

logger = logging.getLogger(__name__)


@dataclass
class TradingConfig:
    """Complete trading configuration loaded from YAML."""

    # Execution mode
    mode: str = "simulation"

    # Core trading parameters
    initial_capital: float = 100000.0
    transaction_cost_bps: float = 10.0
    slippage_bps: float = 1.0
    rebalance_frequency: str = "M"
    enable_soft_rebalance: bool = True
    drift_threshold: float = 0.05

    # Data configuration
    start_date: str = "2015-01-01"
    end_date: str = "2024-12-31"
    update_if_available: bool = True
    data_dir: str = "data"
    processed_dir: str = "data/processed"
    raw_dir: str = "data/raw"

    # Strategy configuration
    use_bandit_wrapper: bool = True
    include_risk_free: bool = True
    strategy_params: Dict[str, Any] = field(default_factory=dict)

    # Bandit configuration
    bandit_type: str = "ucb"
    exploration_constant: float = 2.0
    gamma: float = 0.07
    burn_in_periods: int = 12
    reward_type: str = "sharpe"
    reward_lookback: int = 12
    min_allocation: float = 0.05
    enable_soft_allocation: bool = True
    random_seed: int = 42

    # Risk-free configuration
    risk_free_rate_source: str = "fred"
    risk_free_maturity: str = "3M"
    risk_free_initial_rate: float = 0.04
    risk_free_api_key_env: str = "FRED_API_KEY"
    risk_free_update_freq: str = "D"

    # Checkpoint configuration
    checkpoint_enabled: bool = True
    checkpoint_dir: str = "checkpoints"
    max_checkpoints: int = 7
    use_parquet: bool = True

    # Output configuration
    results_dir: str = "results"
    save_plots: bool = True
    save_metrics: bool = True
    log_level: str = "INFO"
    log_file: str = "results/dynamic_trading_demo.log"

    # Simulation settings
    simulation_speed: float = 1.0
    pause_between_steps: float = 0.1

    # Live trading settings
    data_update_interval: int = 3600
    max_retry_attempts: int = 3
    retry_delay: int = 60
    health_check_interval: int = 300

    # AWS configuration
    aws_bucket: str = "data-retrieval-output"
    aws_region: str = "us-east-1"
    aws_access_key_env: str = "AWS_ACCESS_KEY_ID"
    aws_secret_key_env: str = "AWS_SECRET_ACCESS_KEY"

    # API keys (populated from environment)
    api_keys: Dict[str, str] = field(default_factory=dict)

    # Performance monitoring
    enable_profiling: bool = False
    memory_threshold_mb: int = 2048
    cpu_threshold_percent: int = 50
    log_performance_metrics: bool = True

    # Development settings
    enable_debug_mode: bool = False
    skip_data_validation: bool = False
    use_cached_data: bool = True


class ConfigLoader:
    """
    Loads and validates configuration from YAML files with environment variable support.
    """

    def __init__(self, config_path: Union[str, Path]):
        """
        Initialize config loader.

        Args:
            config_path: Path to YAML configuration file
        """
        # Load environment variables from .env file
        load_dotenv()
        
        self.config_path = Path(config_path)
        self.raw_config = {}

    def load_config(self) -> TradingConfig:
        """
        Load and validate configuration from YAML file.

        Returns:
            TradingConfig: Validated configuration object

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If configuration is invalid
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        # Load YAML
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.raw_config = yaml.safe_load(f)

        # Process environment variables
        self._process_environment_variables()

        # Validate configuration
        self._validate_config()

        # Convert to TradingConfig
        return self._create_trading_config()

    def _process_environment_variables(self) -> None:
        """
        Process environment variable substitutions in configuration.
        Supports ${VAR_NAME} and ${VAR_NAME:default_value} syntax.
        """
        def process_value(value: Any) -> Any:
            if isinstance(value, str):
                # Handle ${VAR_NAME} and ${VAR_NAME:default} patterns
                import re
                pattern = r'\$\{([^}]+)\}'

                def replace_var(match):
                    var_expr = match.group(1)
                    if ':' in var_expr:
                        var_name, default_value = var_expr.split(':', 1)
                    else:
                        var_name, default_value = var_expr, ''

                    env_value = os.getenv(var_name.strip())
                    if env_value is not None:
                        return env_value
                    elif default_value:
                        return default_value.strip()
                    else:
                        logger.warning(f"Environment variable {var_name} not found and no default provided")
                        return f"${{{var_expr}}}"  # Return as-is if not found

                return re.sub(pattern, replace_var, value)
            elif isinstance(value, dict):
                return {k: process_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [process_value(item) for item in value]
            else:
                return value

        self.raw_config = process_value(self.raw_config)

    def _validate_config(self) -> None:
        """
        Comprehensive validation of configuration parameters.
        Raises ValueError for invalid configurations.
        """
        config = self.raw_config
        
        # Validate execution mode
        valid_modes = ['backtest', 'simulation', 'live']
        mode = config.get('execution', {}).get('mode', 'simulation')
        if mode not in valid_modes:
            raise ValueError(f"Invalid execution mode '{mode}'. Must be one of: {valid_modes}")
        
        # Validate bandit configuration
        bandit = config.get('bandit', {})
        valid_bandit_types = ['ucb', 'thompson', 'exp3']
        if bandit.get('type', 'ucb') not in valid_bandit_types:
            raise ValueError(f"Invalid bandit type '{bandit.get('type')}'. Must be one of: {valid_bandit_types}")
        
        valid_reward_types = ['sharpe', 'return', 'clipped_sharpe']
        if bandit.get('reward_type', 'sharpe') not in valid_reward_types:
            raise ValueError(f"Invalid reward type '{bandit.get('reward_type')}'. Must be one of: {valid_reward_types}")
        
        # Validate date formats
        data = config.get('data', {})
        start_date = data.get('start_date', '2015-01-01')
        end_date = data.get('end_date', '2024-12-31')
        
        try:
            pd.to_datetime(start_date)
            pd.to_datetime(end_date)
        except ValueError as e:
            raise ValueError(f"Invalid date format. Start date: '{start_date}', End date: '{end_date}'. Error: {e}")
        
        if pd.to_datetime(start_date) >= pd.to_datetime(end_date):
            raise ValueError(f"Start date '{start_date}' must be before end date '{end_date}'")
        
        # Validate trading parameters
        trading = config.get('trading', {})
        if trading.get('initial_capital', 100000.0) <= 0:
            raise ValueError("Initial capital must be positive")
        
        transaction_cost = trading.get('transaction_cost_bps', 10.0)
        if not (0 <= transaction_cost <= 1000):  # Max 10% transaction cost
            raise ValueError(f"Transaction cost BPS must be between 0 and 1000, got {transaction_cost}")
        
        slippage = trading.get('slippage_bps', 1.0)
        if not (0 <= slippage <= 500):  # Max 5% slippage
            raise ValueError(f"Slippage BPS must be between 0 and 500, got {slippage}")
        
        # Validate rebalance frequency
        valid_frequencies = ['D', 'W', 'M', 'Q', 'Y']
        rebalance_freq = trading.get('rebalance_frequency', 'M')
        if rebalance_freq not in valid_frequencies:
            raise ValueError(f"Invalid rebalance frequency '{rebalance_freq}'. Must be one of: {valid_frequencies}")
        
        # Validate bandit parameters
        exploration_const = bandit.get('exploration_constant', 2.0)
        if exploration_const <= 0:
            raise ValueError("Exploration constant must be positive")
        
        gamma = bandit.get('gamma', 0.07)
        if not (0 < gamma < 1):
            raise ValueError(f"Gamma must be between 0 and 1, got {gamma}")
        
        burn_in = bandit.get('burn_in_periods', 12)
        if burn_in < 0:
            raise ValueError("Burn-in periods must be non-negative")
        
        reward_lookback = bandit.get('reward_lookback', 12)
        if reward_lookback <= 0:
            raise ValueError("Reward lookback must be positive")
        
        min_allocation = bandit.get('min_allocation', 0.05)
        if not (0 <= min_allocation <= 1):
            raise ValueError(f"Minimum allocation must be between 0 and 1, got {min_allocation}")
        
        # Validate risk-free parameters
        risk_free = config.get('risk_free', {})
        valid_sources = ['fred', 'config', 'fallback']
        if risk_free.get('rate_source', 'fred') not in valid_sources:
            raise ValueError(f"Invalid risk-free rate source '{risk_free.get('rate_source')}'. Must be one of: {valid_sources}")
        
        valid_maturities = ['1M', '3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y']
        maturity = risk_free.get('maturity', '3M')
        if maturity not in valid_maturities:
            raise ValueError(f"Invalid maturity '{maturity}'. Must be one of: {valid_maturities}")
        
        initial_rate = risk_free.get('initial_rate', 0.04)
        if not (0 <= initial_rate <= 0.5):  # Max 50% rate
            raise ValueError(f"Initial risk-free rate must be between 0 and 0.5, got {initial_rate}")
        
        # Validate checkpoint parameters
        checkpoint = config.get('checkpoint', {})
        max_checkpoints = checkpoint.get('max_checkpoints', 7)
        if max_checkpoints < 1:
            raise ValueError("Max checkpoints must be at least 1")
        
        # Validate live trading parameters
        live = config.get('live', {})
        update_interval = live.get('data_update_interval', 3600)
        if update_interval < 60:  # Min 1 minute
            raise ValueError("Data update interval must be at least 60 seconds")
        
        max_retries = live.get('max_retry_attempts', 3)
        if max_retries < 0:
            raise ValueError("Max retry attempts must be non-negative")
        
        retry_delay = live.get('retry_delay', 60)
        if retry_delay < 1:
            raise ValueError("Retry delay must be at least 1 second")
        
        health_interval = live.get('health_check_interval', 300)
        if health_interval < 30:  # Min 30 seconds
            raise ValueError("Health check interval must be at least 30 seconds")
        
        # Validate monitoring parameters
        monitoring = config.get('monitoring', {})
        memory_threshold = monitoring.get('memory_threshold_mb', 2048)
        if memory_threshold <= 0:
            raise ValueError("Memory threshold must be positive")
        
        cpu_threshold = monitoring.get('cpu_threshold_percent', 50)
        if not (0 <= cpu_threshold <= 100):
            raise ValueError(f"CPU threshold must be between 0 and 100, got {cpu_threshold}")
        
        logger.info("Configuration validation passed")

    def _get_nested_value(self, config: Dict, *keys: str) -> Any:
        """Get nested dictionary value safely."""
        current = config
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current

    def _create_trading_config(self) -> TradingConfig:
        """
        Convert raw config dict to TradingConfig dataclass.

        Returns:
            TradingConfig: Configuration object
        """
        config = self.raw_config

        # Extract nested values with defaults
        execution = config.get('execution', {})
        trading = config.get('trading', {})
        data = config.get('data', {})
        strategies = config.get('strategies', {})
        bandit = config.get('bandit', {})
        risk_free = config.get('risk_free', {})
        checkpoint = config.get('checkpoint', {})
        output = config.get('output', {})
        simulation = config.get('simulation', {})
        live = config.get('live', {})
        monitoring = config.get('monitoring', {})
        development = config.get('development', {})

        return TradingConfig(
            # Execution
            mode=execution.get('mode', 'simulation'),

            # Trading
            initial_capital=trading.get('initial_capital', 100000.0),
            transaction_cost_bps=trading.get('transaction_cost_bps', 10.0),
            slippage_bps=trading.get('slippage_bps', 1.0),
            rebalance_frequency=trading.get('rebalance_frequency', 'M'),
            enable_soft_rebalance=trading.get('enable_soft_rebalance', True),
            drift_threshold=trading.get('drift_threshold', 0.05),

            # Data
            start_date=data.get('start_date', '2015-01-01'),
            end_date=data.get('end_date', '2024-12-31'),
            update_if_available=data.get('update_if_available', True),
            data_dir=data.get('data_dir', 'data'),
            processed_dir=data.get('processed_dir', 'data/processed'),
            raw_dir=data.get('raw_dir', 'data/raw'),

            # Strategies
            use_bandit_wrapper=strategies.get('use_bandit_wrapper', True),
            include_risk_free=strategies.get('include_risk_free', True),
            strategy_params=strategies,

            # Bandit
            bandit_type=bandit.get('type', 'ucb'),
            exploration_constant=bandit.get('exploration_constant', 2.0),
            gamma=bandit.get('gamma', 0.07),
            burn_in_periods=bandit.get('burn_in_periods', 12),
            reward_type=bandit.get('reward_type', 'sharpe'),
            reward_lookback=bandit.get('reward_lookback', 12),
            min_allocation=bandit.get('min_allocation', 0.05),
            enable_soft_allocation=bandit.get('enable_soft_allocation', True),
            random_seed=bandit.get('random_seed', 42),

            # Risk-free
            risk_free_rate_source=risk_free.get('rate_source', 'fred'),
            risk_free_maturity=risk_free.get('maturity', '3M'),
            risk_free_initial_rate=risk_free.get('initial_rate', 0.04),
            risk_free_api_key_env=risk_free.get('api_key_env_var', 'FRED_API_KEY'),
            risk_free_update_freq=risk_free.get('update_frequency', 'D'),

            # Checkpoint
            checkpoint_enabled=checkpoint.get('enabled', True),
            checkpoint_dir=checkpoint.get('directory', 'checkpoints'),
            max_checkpoints=checkpoint.get('max_checkpoints', 7),
            use_parquet=checkpoint.get('use_parquet', True),

            # Output
            results_dir=output.get('results_dir', 'results'),
            save_plots=output.get('save_plots', True),
            save_metrics=output.get('save_metrics', True),
            log_level=output.get('log_level', 'INFO'),
            log_file=output.get('log_file', 'results/dynamic_trading_demo.log'),

            # Simulation
            simulation_speed=simulation.get('speed', 1.0),
            pause_between_steps=simulation.get('pause_between_steps', 0.1),

            # Live
            data_update_interval=live.get('data_update_interval', 3600),
            max_retry_attempts=live.get('max_retry_attempts', 3),
            retry_delay=live.get('retry_delay', 60),
            health_check_interval=live.get('health_check_interval', 300),

            # AWS
            aws_bucket=config.get('aws', {}).get('bucket', 'data-retrieval-output'),
            aws_region=config.get('aws', {}).get('region', 'us-east-1'),
            aws_access_key_env=config.get('aws', {}).get('access_key_env_var', 'AWS_ACCESS_KEY_ID'),
            aws_secret_key_env=config.get('aws', {}).get('secret_key_env_var', 'AWS_SECRET_ACCESS_KEY'),

            # API keys
            api_keys=config.get('api_keys', {}),

            # Monitoring
            enable_profiling=monitoring.get('enable_profiling', False),
            memory_threshold_mb=monitoring.get('memory_threshold_mb', 2048),
            cpu_threshold_percent=monitoring.get('cpu_threshold_percent', 50),
            log_performance_metrics=monitoring.get('log_performance_metrics', True),

            # Development
            enable_debug_mode=development.get('enable_debug_mode', False),
            skip_data_validation=development.get('skip_data_validation', False),
            use_cached_data=development.get('use_cached_data', True)
        )


def load_trading_config(config_path: Union[str, Path] = "config/trading_config.yaml") -> TradingConfig:
    """
    Convenience function to load trading configuration.

    Args:
        config_path: Path to configuration file

    Returns:
        TradingConfig: Loaded and validated configuration
    """
    loader = ConfigLoader(config_path)
    return loader.load_config()


# Test the configuration loader
if __name__ == "__main__":
    try:
        config = load_trading_config()
        print("Configuration loaded successfully!")
        print(f"Mode: {config.mode}")
        print(f"Initial capital: ${config.initial_capital:,.0f}")
        print(f"Bandit type: {config.bandit_type}")
        print(f"Risk-free source: {config.risk_free_rate_source}")
    except Exception as e:
        print(f"Error loading configuration: {e}")