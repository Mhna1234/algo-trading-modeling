"""
Demo Results Aggregator
=======================

Professional aggregation, persistence, and visualization of demo results.
Designed to support S3 upload and dynamic dashboard consumption.

Key Features:
- Structured CSV export (nav, returns, drawdown, sharpe, weights)
- Professional matplotlib visualizations
- No hardcoded strategy names
- Clean separation of computation and visualization

Usage:
    aggregator = DemoResultsAggregator()
    
    # Record data during demo
    for strategy_name, result in results:
        aggregator.record_strategy(
            strategy_name=strategy_name,
            equity_curve=result.equity_curve,
            portfolio_history=result.portfolio_history  # Optional
        )
    
    # Generate outputs
    output_dir = aggregator.export_csv(base_dir='results')
    aggregator.plot_summary(output_dir=output_dir)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class DemoResultsAggregator:
    """
    Aggregates, persists, and visualizes demo results.
    
    Stores all metrics in structured format suitable for:
    - S3 upload
    - Dashboard consumption
    - Reproducible analysis
    
    Attributes
    ----------
    nav_data : Dict[str, pd.Series]
        NAV curves by strategy
    returns_data : Dict[str, pd.Series]
        Returns series by strategy
    weights_history : List[Dict]
        Portfolio weight history over time
    window_size : int
        Rolling window for Sharpe ratio
    """
    
    def __init__(self, rolling_window: int = 60):
        """
        Initialize aggregator.
        
        Parameters
        ----------
        rolling_window : int
            Window size for rolling metrics (default 60 days)
        """
        self.nav_data: Dict[str, pd.Series] = {}
        self.returns_data: Dict[str, pd.Series] = {}
        self.weights_history: List[Dict] = []
        self.weights_final: Dict[str, Dict[str, float]] = {}
        self.window_size = rolling_window
        
        # Cached computed metrics
        self._drawdown_data: Optional[Dict[str, pd.Series]] = None
        self._rolling_sharpe_data: Optional[Dict[str, pd.Series]] = None
    
    def record_strategy(
        self,
        strategy_name: str,
        equity_curve: pd.Series,
        portfolio_history: Optional[pd.DataFrame] = None
    ):
        """
        Record results for a single strategy.
        
        Parameters
        ----------
        strategy_name : str
            Name of the strategy
        equity_curve : pd.Series
            NAV time series (indexed by date)
        portfolio_history : pd.DataFrame, optional
            Portfolio weights over time (columns = assets, index = dates)
        """
        # Normalize NAV to start at 1.0
        nav_normalized = equity_curve / equity_curve.iloc[0]
        self.nav_data[strategy_name] = nav_normalized
        
        # Compute returns
        returns = equity_curve.pct_change().dropna()
        self.returns_data[strategy_name] = returns
        
        # Store weights history
        if portfolio_history is not None and len(portfolio_history) > 0:
            for date_idx in portfolio_history.index:
                weights = portfolio_history.loc[date_idx]
                # Filter out zero/negligible weights
                weights_dict = {
                    asset: float(weight) 
                    for asset, weight in weights.items() 
                    if abs(weight) > 1e-6
                }
                
                self.weights_history.append({
                    'date': date_idx,
                    'strategy': strategy_name,
                    'weights': weights_dict
                })
            
            # Store final weights
            final_weights = portfolio_history.iloc[-1]
            self.weights_final[strategy_name] = {
                asset: float(weight)
                for asset, weight in final_weights.items()
                if abs(weight) > 1e-6
            }
        
        # Clear cached metrics
        self._drawdown_data = None
        self._rolling_sharpe_data = None
        
        logger.debug(f"Recorded strategy: {strategy_name}")
    
    def compute_drawdown(self) -> Dict[str, pd.Series]:
        """
        Compute drawdown curves for all strategies.
        
        Returns
        -------
        Dict[str, pd.Series]
            Drawdown series by strategy
        """
        if self._drawdown_data is not None:
            return self._drawdown_data
        
        drawdown_data = {}
        
        for strategy_name, nav in self.nav_data.items():
            cummax = nav.cummax()
            drawdown = (nav - cummax) / cummax
            drawdown_data[strategy_name] = drawdown
        
        self._drawdown_data = drawdown_data
        return drawdown_data
    
    def compute_rolling_sharpe(
        self, 
        annualization_factor: float = 252.0,
        risk_free_rate: float = 0.02
    ) -> Dict[str, pd.Series]:
        """
        Compute rolling Sharpe ratio for all strategies.
        
        Parameters
        ----------
        annualization_factor : float
            Factor to annualize returns (default 252 for daily data)
        risk_free_rate : float
            Annual risk-free rate (default 2%)
        
        Returns
        -------
        Dict[str, pd.Series]
            Rolling Sharpe series by strategy
        """
        if self._rolling_sharpe_data is not None:
            return self._rolling_sharpe_data
        
        rolling_sharpe_data = {}
        
        for strategy_name, returns in self.returns_data.items():
            # Rolling mean and std
            rolling_mean = returns.rolling(window=self.window_size).mean()
            rolling_std = returns.rolling(window=self.window_size).std()
            
            # Annualized Sharpe: sqrt(gamma) * (mu - rf) / sigma
            gamma = annualization_factor
            rf_daily = risk_free_rate / gamma
            
            rolling_sharpe = np.sqrt(gamma) * (rolling_mean - rf_daily) / rolling_std
            
            # Handle NaN and inf values
            rolling_sharpe = rolling_sharpe.replace([np.inf, -np.inf], np.nan)
            
            rolling_sharpe_data[strategy_name] = rolling_sharpe
        
        self._rolling_sharpe_data = rolling_sharpe_data
        return rolling_sharpe_data
    
    def export_csv(self, base_dir: str = 'results') -> Path:
        """
        Export all data to structured CSV files.
        
        Overwrites existing results in:
        results/
            nav.csv
            returns.csv
            drawdown.csv
            sharpe.csv
            weights_final.csv
            weights_history.csv
        
        Parameters
        ----------
        base_dir : str
            Base directory for results (default 'results')
        
        Returns
        -------
        Path
            Path to created output directory
        """
        # Use fixed directory (no timestamp)
        output_dir = Path(base_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Exporting results to: {output_dir}")
        
        # 1. Export NAV
        nav_df = pd.DataFrame(self.nav_data)
        nav_long = nav_df.reset_index().melt(
            id_vars='index',
            var_name='strategy',
            value_name='nav'
        ).rename(columns={'index': 'date'})
        nav_long.to_csv(output_dir / 'nav.csv', index=False)
        logger.debug("  ✓ nav.csv")
        
        # 2. Export Returns
        returns_df = pd.DataFrame(self.returns_data)
        returns_long = returns_df.reset_index().melt(
            id_vars='index',
            var_name='strategy',
            value_name='return'
        ).rename(columns={'index': 'date'})
        returns_long.to_csv(output_dir / 'returns.csv', index=False)
        logger.debug("  ✓ returns.csv")
        
        # 3. Export Drawdown
        drawdown_data = self.compute_drawdown()
        drawdown_df = pd.DataFrame(drawdown_data)
        drawdown_long = drawdown_df.reset_index().melt(
            id_vars='index',
            var_name='strategy',
            value_name='drawdown'
        ).rename(columns={'index': 'date'})
        drawdown_long.to_csv(output_dir / 'drawdown.csv', index=False)
        logger.debug("  ✓ drawdown.csv")
        
        # 4. Export Rolling Sharpe
        sharpe_data = self.compute_rolling_sharpe()
        sharpe_df = pd.DataFrame(sharpe_data)
        sharpe_long = sharpe_df.reset_index().melt(
            id_vars='index',
            var_name='strategy',
            value_name='rolling_sharpe'
        ).rename(columns={'index': 'date'})
        sharpe_long.to_csv(output_dir / 'sharpe.csv', index=False)
        logger.debug("  ✓ sharpe.csv")
        
        # 5. Export Final Weights
        if self.weights_final:
            final_weights_records = []
            for strategy_name, weights_dict in self.weights_final.items():
                for asset, weight in weights_dict.items():
                    final_weights_records.append({
                        'strategy': strategy_name,
                        'asset': asset,
                        'weight': weight
                    })
            
            final_weights_df = pd.DataFrame(final_weights_records)
            final_weights_df = final_weights_df.sort_values(
                ['strategy', 'weight'], 
                ascending=[True, False]
            )
            final_weights_df.to_csv(output_dir / 'weights_final.csv', index=False)
            logger.debug("  ✓ weights_final.csv")
        
        # 6. Export Weights History
        if self.weights_history:
            weights_history_records = []
            for record in self.weights_history:
                date = record['date']
                strategy = record['strategy']
                weights = record['weights']
                
                for asset, weight in weights.items():
                    weights_history_records.append({
                        'date': date,
                        'strategy': strategy,
                        'asset': asset,
                        'weight': weight
                    })
            
            weights_history_df = pd.DataFrame(weights_history_records)
            weights_history_df = weights_history_df.sort_values(['date', 'strategy', 'asset'])
            weights_history_df.to_csv(output_dir / 'weights_history.csv', index=False)
            logger.debug("  ✓ weights_history.csv")
        
        logger.info(f"✓ All data exported to: {output_dir}")
        return output_dir
    
    def plot_summary(
        self,
        output_dir: Optional[Path] = None,
        log_scale: bool = False,
        figsize: Tuple[int, int] = (20, 24),
        dpi: int = 300
    ):
        """
        Generate professional summary plots.
        
        Creates 5 subplots:
        1. NAV curves
        2. Drawdown curves
        3. Returns curves (cumulative)
        4. Rolling Sharpe ratio
        5. Final portfolio weights
        
        Parameters
        ----------
        output_dir : Path, optional
            Directory to save plots (if None, uses current directory)
        log_scale : bool
            Use log scale for NAV plot (default False)
        figsize : tuple
            Figure size (width, height)
        dpi : int
            Resolution for saved figure
        """
        if output_dir is None:
            output_dir = Path('.')
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create color map (consistent across plots)
        strategies = list(self.nav_data.keys())
        colors = plt.cm.tab20(np.linspace(0, 1, len(strategies)))
        color_map = dict(zip(strategies, colors))
        
        # Create figure with 5 subplots
        fig, axes = plt.subplots(5, 1, figsize=figsize)
        fig.suptitle(
            'Portfolio Strategy Performance Summary',
            fontsize=18,
            fontweight='bold',
            y=0.995
        )
        
        # ========== 1. NAV Curves ==========
        ax1 = axes[0]
        for strategy_name, nav in self.nav_data.items():
            ax1.plot(
                nav.index,
                nav.values,
                label=strategy_name,
                color=color_map[strategy_name],
                linewidth=2,
                alpha=0.8
            )
        
        ax1.set_title('1. Net Asset Value (NAV) - Normalized to 1.0', 
                      fontsize=14, fontweight='bold', pad=10)
        ax1.set_xlabel('Date', fontsize=11)
        ax1.set_ylabel('NAV', fontsize=11)
        if log_scale:
            ax1.set_yscale('log')
        ax1.legend(loc='best', fontsize=9, ncol=2, framealpha=0.9)
        ax1.grid(True, alpha=0.3, linestyle='--')
        
        # ========== 2. Drawdown Curves ==========
        ax2 = axes[1]
        drawdown_data = self.compute_drawdown()
        
        max_dd_values = {}
        for strategy_name, drawdown in drawdown_data.items():
            ax2.plot(
                drawdown.index,
                drawdown.values * 100,  # Convert to percentage
                label=strategy_name,
                color=color_map[strategy_name],
                linewidth=2,
                alpha=0.8
            )
            max_dd_values[strategy_name] = drawdown.min() * 100
        
        ax2.set_title('2. Drawdown - Distance from Peak', 
                      fontsize=14, fontweight='bold', pad=10)
        ax2.set_xlabel('Date', fontsize=11)
        ax2.set_ylabel('Drawdown (%)', fontsize=11)
        ax2.legend(loc='best', fontsize=9, ncol=2, framealpha=0.9)
        ax2.grid(True, alpha=0.3, linestyle='--')
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.8, alpha=0.5)
        
        # Add max drawdown annotations
        y_min = min(max_dd_values.values())
        ax2.text(
            0.02, 0.02,
            f"Max DD: {', '.join([f'{k}: {v:.1f}%' for k, v in sorted(max_dd_values.items(), key=lambda x: x[1])[:3]])}",
            transform=ax2.transAxes,
            fontsize=9,
            verticalalignment='bottom',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        )
        
        # ========== 3. Cumulative Returns ==========
        ax3 = axes[2]
        for strategy_name, returns in self.returns_data.items():
            cumulative_returns = (1 + returns).cumprod()
            ax3.plot(
                cumulative_returns.index,
                cumulative_returns.values,
                label=strategy_name,
                color=color_map[strategy_name],
                linewidth=2,
                alpha=0.8
            )
        
        ax3.set_title('3. Cumulative Returns - Compounded Growth', 
                      fontsize=14, fontweight='bold', pad=10)
        ax3.set_xlabel('Date', fontsize=11)
        ax3.set_ylabel('Cumulative Return Factor', fontsize=11)
        ax3.legend(loc='best', fontsize=9, ncol=2, framealpha=0.9)
        ax3.grid(True, alpha=0.3, linestyle='--')
        ax3.axhline(y=1, color='black', linestyle='--', linewidth=0.8, alpha=0.5)
        
        # ========== 4. Rolling Sharpe Ratio ==========
        ax4 = axes[3]
        sharpe_data = self.compute_rolling_sharpe()
        
        for strategy_name, sharpe in sharpe_data.items():
            # Only plot after sufficient data
            valid_sharpe = sharpe.dropna()
            if len(valid_sharpe) > 0:
                ax4.plot(
                    valid_sharpe.index,
                    valid_sharpe.values,
                    label=strategy_name,
                    color=color_map[strategy_name],
                    linewidth=2,
                    alpha=0.8
                )
        
        ax4.set_title(f'4. Rolling Sharpe Ratio - {self.window_size}-Day Window', 
                      fontsize=14, fontweight='bold', pad=10)
        ax4.set_xlabel('Date', fontsize=11)
        ax4.set_ylabel('Sharpe Ratio', fontsize=11)
        ax4.legend(loc='best', fontsize=9, ncol=2, framealpha=0.9)
        ax4.grid(True, alpha=0.3, linestyle='--')
        ax4.axhline(y=0, color='black', linestyle='--', linewidth=0.8, alpha=0.5)
        ax4.axhline(y=1, color='green', linestyle=':', linewidth=0.8, alpha=0.3)
        
        # ========== 5. Final Portfolio Weights - ALL STRATEGIES ==========
        # Remove the 5th subplot and create a new figure for weights
        ax5 = axes[4]
        ax5.axis('off')  # Hide the 5th subplot
        
        # Add text to indicate separate figure
        ax5.text(0.5, 0.5, 
                'Portfolio weights displayed in separate figure\n(weights_plot.png)',
                ha='center', va='center', fontsize=12,
                transform=ax5.transAxes,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        
        # Save figure
        output_file = output_dir / 'summary_plots.png'
        plt.savefig(output_file, dpi=dpi, bbox_inches='tight')
        logger.info(f"✓ Summary plots saved to: {output_file}")
        
        plt.close(fig)
        
        # Create separate figure for portfolio weights (all strategies)
        if self.weights_final:
            self._plot_all_weights(output_dir, color_map, dpi)
    
    def _plot_all_weights(
        self,
        output_dir: Path,
        color_map: Dict[str, any],
        dpi: int = 300
    ):
        """
        Create separate figure showing portfolio weights for ALL strategies.
        
        Parameters
        ----------
        output_dir : Path
            Directory to save plot
        color_map : Dict
            Color mapping for strategies
        dpi : int
            Resolution for saved figure
        """
        n_strategies = len(self.weights_final)
        
        # Calculate grid layout (try to make it roughly square)
        n_cols = min(3, n_strategies)  # Max 3 columns
        n_rows = int(np.ceil(n_strategies / n_cols))
        
        # Create figure with subplots
        fig, axes = plt.subplots(
            n_rows, n_cols,
            figsize=(6 * n_cols, 5 * n_rows)
        )
        fig.suptitle(
            'Final Portfolio Weights - All Strategies',
            fontsize=16,
            fontweight='bold',
            y=0.995
        )
        
        # Flatten axes for easier iteration
        if n_strategies == 1:
            axes = [axes]
        elif n_rows == 1:
            axes = list(axes)
        else:
            axes = axes.flatten()
        
        # Plot each strategy
        for idx, (strategy_name, weights) in enumerate(self.weights_final.items()):
            ax = axes[idx]
            
            # Sort by absolute weight (descending)
            sorted_weights = sorted(weights.items(), key=lambda x: abs(x[1]), reverse=True)
            
            # Filter out CASH and very small weights
            sorted_weights = [(asset, weight) for asset, weight in sorted_weights 
                             if asset != 'CASH' and abs(weight) > 1e-4]
            
            if sorted_weights:
                assets = [item[0] for item in sorted_weights]
                values = [item[1] * 100 for item in sorted_weights]  # Convert to percentage
                
                # Color bars: green for positive, red for negative
                colors_bar = ['green' if v > 0 else 'red' for v in values]
                
                # Horizontal bar chart
                bars = ax.barh(assets, values, color=colors_bar, alpha=0.7, edgecolor='black', linewidth=0.5)
                
                # Add value labels on bars
                for i, (bar, val) in enumerate(zip(bars, values)):
                    if abs(val) > 0.5:  # Only label if > 0.5%
                        ax.text(
                            val + (1 if val > 0 else -1),
                            i,
                            f'{val:.1f}%',
                            va='center',
                            ha='left' if val > 0 else 'right',
                            fontsize=8
                        )
                
                ax.set_title(strategy_name, fontsize=11, fontweight='bold', pad=8)
                ax.set_xlabel('Weight (%)', fontsize=9)
                ax.grid(True, alpha=0.3, axis='x', linestyle='--')
                ax.axvline(x=0, color='black', linestyle='-', linewidth=1)
                
                # Set x-axis limits with some padding
                max_abs = max(abs(v) for v in values)
                ax.set_xlim(-max_abs * 1.15, max_abs * 1.15)
            else:
                ax.text(0.5, 0.5, 'No weights data',
                       ha='center', va='center',
                       transform=ax.transAxes, fontsize=10)
                ax.set_title(strategy_name, fontsize=11, fontweight='bold', pad=8)
        
        # Hide unused subplots
        for idx in range(n_strategies, len(axes)):
            axes[idx].axis('off')
        
        plt.tight_layout()
        
        # Save figure
        output_file = output_dir / 'weights_plot.png'
        plt.savefig(output_file, dpi=dpi, bbox_inches='tight')
        logger.info(f"✓ Weights plot saved to: {output_file}")
        
        plt.close(fig)
    
    def get_summary_stats(self) -> pd.DataFrame:
        """
        Compute summary statistics table.
        
        Returns
        -------
        pd.DataFrame
            Summary statistics by strategy
        """
        stats = []
        
        drawdown_data = self.compute_drawdown()
        sharpe_data = self.compute_rolling_sharpe()
        
        for strategy_name in self.nav_data.keys():
            nav = self.nav_data[strategy_name]
            returns = self.returns_data[strategy_name]
            
            # Total return
            total_return = (nav.iloc[-1] - 1) * 100
            
            # CAGR
            n_years = len(nav) / 252
            cagr = ((nav.iloc[-1]) ** (1 / n_years) - 1) * 100 if n_years > 0 else 0
            
            # Volatility (annualized)
            vol = returns.std() * np.sqrt(252) * 100
            
            # Sharpe (final)
            sharpe_series = sharpe_data[strategy_name].dropna()
            final_sharpe = sharpe_series.iloc[-1] if len(sharpe_series) > 0 else np.nan
            
            # Max drawdown
            max_dd = drawdown_data[strategy_name].min() * 100
            
            stats.append({
                'Strategy': strategy_name,
                'Total Return (%)': total_return,
                'CAGR (%)': cagr,
                'Volatility (%)': vol,
                'Sharpe Ratio': final_sharpe,
                'Max Drawdown (%)': max_dd
            })
        
        return pd.DataFrame(stats)
