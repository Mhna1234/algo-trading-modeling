# portfolio_optimization.py
# =========================================================
# A lightweight, dependency-free (no SciPy) portfolio optimization toolkit
# that treats cash as an explicit asset and maximizes the Sharpe ratio.
#
# Features
# --------
# - Cash is modeled as asset 0 with expected return = risk-free rate (Rf) and zero volatility/covariance.
# - Computes portfolio return, volatility, and Sharpe ratio (annualized).
# - Random search + projected gradient ascent optimizer that enforces:
#     * Sum of weights = 1
#     * Long-only (weights >= 0) by default, or allow_short=True for limited shorting
# - Utility to annualize returns/cov based on data frequency (daily/weekly/monthly).
# - Helper to scale risk via cash weight analytically when using a pure "risky sleeve".
#
# Notes
# -----
# - This module avoids SciPy to maximize portability in simple environments.
# - The optimizer uses a robust heuristic (multi-start projected gradient) that works well in practice
#   for moderate asset counts (n <= ~100). For larger universes, consider adding a more advanced solver.

from dataclasses import dataclass
from typing import Optional, Tuple, Dict
import numpy as np
import pandas as pd

# -----------------------------
# Data containers
# -----------------------------

@dataclass
class PortfolioInputs:
    mu_annual: np.ndarray          # shape (n_assets,), expected annual returns (including cash at idx 0)
    cov_annual: np.ndarray         # shape (n_assets, n_assets), annualized covariance (cash row/col should be 0)
    rf_annual: float               # risk-free rate (annualized)
    asset_names: Optional[list] = None  # optional labels (len n_assets, cash should be first)


@dataclass
class PortfolioResult:
    weights: np.ndarray
    exp_return: float
    volatility: float
    sharpe: float
    diagnostics: Dict


# -----------------------------
# Core math
# -----------------------------

def _project_simplex(v: np.ndarray) -> np.ndarray:
    """
    Project a vector v onto the probability simplex {w: w_i >= 0, sum w_i = 1}.
    Implements the algorithm from Duchi et al. (2008).
    """
    n = v.size
    if n == 0:
        return v
    u = np.sort(v)[::-1]
    cssv = np.cumsum(u)
    rho = np.where(u > (cssv - 1) / np.arange(1, n + 1))[0]
    if rho.size == 0:
        w = np.zeros_like(v)
        w[0] = 1.0
        return w
    rho = rho[-1]
    theta = (cssv[rho] - 1) / (rho + 1.0)
    w = np.maximum(v - theta, 0)
    return w


def _normalize_sum_to_one(w: np.ndarray) -> np.ndarray:
    s = np.sum(w)
    if s == 0:
        return np.ones_like(w) / w.size
    return w / s


def portfolio_stats(weights: np.ndarray, mu_annual: np.ndarray, cov_annual: np.ndarray, rf_annual: float) -> Tuple[float, float, float]:
    """
    Compute (expected_return, volatility, sharpe) for a given weight vector.
    Sharpe is computed as (E[R] - Rf) / sigma.
    """
    exp_ret = float(np.dot(weights, mu_annual))
    var = float(weights @ cov_annual @ weights)
    vol = np.sqrt(max(var, 0.0))
    if vol <= 1e-12:
        sharpe = 0.0 if exp_ret <= rf_annual else float('inf')
    else:
        sharpe = (exp_ret - rf_annual) / vol
    return exp_ret, vol, sharpe


def add_cash_asset(mu_annual_risky: np.ndarray, cov_annual_risky: np.ndarray, rf_annual: float, risky_names: Optional[list]=None) -> PortfolioInputs:
    """
    Prepend a 'cash' asset (index 0) to the risky assets.
    - mu_annual_risky: shape (n,)
    - cov_annual_risky: shape (n,n)
    Returns PortfolioInputs with shapes (n+1) and (n+1,n+1).
    """
    n = mu_annual_risky.size
    mu = np.concatenate([[rf_annual], mu_annual_risky])
    cov = np.zeros((n+1, n+1))
    cov[1:,1:] = cov_annual_risky  # cash has zero covariances/variance

    names = ["Cash"] + (risky_names if risky_names is not None else [f"Asset_{i+1}" for i in range(n)])
    return PortfolioInputs(mu_annual=mu, cov_annual=cov, rf_annual=rf_annual, asset_names=names)


# -----------------------------
# Optimizer (no SciPy)
# -----------------------------

def maximize_sharpe(inputs: PortfolioInputs,
                    allow_short: bool=False,
                    n_random_starts: int=5000,
                    n_gradient_steps: int=200,
                    step_size: float=0.05,
                    seed: Optional[int]=42) -> PortfolioResult:
    """
    Heuristic optimizer to maximize Sharpe ratio under constraints:
      - Sum of weights = 1
      - Long-only if allow_short=False (default). If allow_short=True, we allow limited shorting
        via an L2 projection to sum=1 and then clipping to a leverage cap.
    Strategy:
      1) Random search for multiple starting points (Dirichlet for long-only; Gaussian for short-allowed)
      2) For each start, projected gradient ascent on Sharpe ratio
    """
    rng = np.random.default_rng(seed)
    mu = inputs.mu_annual
    cov = inputs.cov_annual
    rf = inputs.rf_annual
    n = mu.size

    def sharpe_and_grad(w: np.ndarray):
        num = float(w @ mu - rf)
        Sigma_w = cov @ w
        denom_sq = float(w @ Sigma_w)
        denom = np.sqrt(max(denom_sq, 1e-16))
        if denom <= 1e-12:
            S = -1e9
            grad = np.zeros_like(w)
            exp_ret = float(w @ mu)
            vol = 0.0
            return S, grad, exp_ret, vol, num
        S = num / denom
        # ∇S = mu/denom - num*(Σ w)/denom^3
        grad = mu/denom - (num * Sigma_w) / (denom**3)
        exp_ret = float(w @ mu)
        vol = denom
        return S, grad, exp_ret, vol, num

    # Random initializations
    starts = []
    if allow_short:
        for _ in range(n_random_starts):
            w = rng.normal(0, 1, size=n)
            w = _normalize_sum_to_one(w)
            starts.append(w)
    else:
        alpha = np.ones(n)
        starts = rng.dirichlet(alpha, size=n_random_starts)

    best_w = None
    best_exp = None
    best_vol = None
    best_S = -1e18
    best_diag = None

    for idx, w0 in enumerate(starts):
        w = w0.copy()
        traj = []
        for t in range(n_gradient_steps):
            S, grad, exp_ret, vol, num = sharpe_and_grad(w)
            if allow_short:
                w = w + step_size * grad
                w = _normalize_sum_to_one(w)
                w = np.clip(w, -2.0, 2.0)
            else:
                w = w + step_size * grad
                w = _project_simplex(w)

            traj.append(S)
            if t > 20 and abs(traj[-1] - traj[-10]) < 1e-8:
                break

        exp_ret, vol, S = portfolio_stats(w, mu, cov, rf)
        if S > best_S:
            best_S = S
            best_w = w
            best_exp = exp_ret
            best_vol = vol
            best_diag = {"start_index": idx, "steps_taken": len(traj), "last_S": traj[-1] if len(traj) else None}

    return PortfolioResult(weights=best_w, exp_return=best_exp, volatility=best_vol, sharpe=best_S, diagnostics=best_diag)


# -----------------------------
# Utilities for preprocessing
# -----------------------------

def annualize_returns_and_cov(returns: pd.DataFrame, freq: str="daily") -> Tuple[np.ndarray, np.ndarray]:
    """
    Convert historical *simple* returns DataFrame into annualized mean vector and covariance matrix.
    - returns: DataFrame of shape (T, n), each column is an asset's simple return (e.g., pct_change())
    - freq: "daily", "weekly", or "monthly"
    Returns (mu_annual, cov_annual) as numpy arrays.
    """
    freq = freq.lower()
    if freq not in {"daily", "weekly", "monthly"}:
        raise ValueError("freq must be one of: daily, weekly, monthly")

    ann_fac = {"daily": 252, "weekly": 52, "monthly": 12}[freq]
    mu = returns.mean().to_numpy() * ann_fac
    cov = returns.cov().to_numpy() * ann_fac
    return mu, cov


def risky_to_full_inputs(returns: pd.DataFrame,
                         rf_annual: float,
                         freq: str="daily",
                         names: Optional[list]=None) -> PortfolioInputs:
    """
    Convenience: take risky asset *return series* and build PortfolioInputs with cash prepended.
    """
    mu_r, cov_r = annualize_returns_and_cov(returns, freq=freq)
    return add_cash_asset(mu_r, cov_r, rf_annual=rf_annual, risky_names=names)


# -----------------------------
# Cash scaling helper
# -----------------------------

def scale_vol_with_cash(risky_weights: np.ndarray, cov_risky_annual: np.ndarray, target_vol_annual: float):
    """
    Given a risky sleeve (weights sum to 1 across risky assets) with annual vol sigma_risky, compute
    the cash weight needed to achieve a lower target volatility using:
        sigma_p = (1 - w0) * sigma_risky  ->  w0 = 1 - sigma_p / sigma_risky
    Returns (cash_weight, risky_multiplier) where risky_multiplier = 1 - w0.
    """
    sigma_risky = np.sqrt(float(risky_weights @ cov_risky_annual @ risky_weights))
    if sigma_risky <= 1e-12:
        return 1.0, 0.0
    risky_mult = min(max(target_vol_annual / sigma_risky, 0.0), 1.0)
    w0 = 1.0 - risky_mult
    return w0, risky_mult


# -----------------------------
# Pretty printing
# -----------------------------

def summarize_result(result, asset_names: Optional[list]=None) -> str:
    names = asset_names if asset_names is not None else [f"Asset_{i}" for i in range(len(result.weights))]
    rows = ["Weights:"]
    for n, w in zip(names, result.weights):
        rows.append(f"  - {n:<15} {w: .4f}")
    rows += [
        f"\nExpected annual return: {result.exp_return:.4%}",
        f"Annual volatility:       {result.volatility:.4%}",
        f"Sharpe ratio:            {result.sharpe:.4f}",
        f"Diagnostics:             {result.diagnostics}"
    ]
    return "\n".join(rows)
