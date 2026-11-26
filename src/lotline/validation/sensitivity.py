"""Which uncertain inputs drive a result's range: first-order sensitivity shares from runs already made.

Every Lotline result is the spread of n model runs, each with its own draw of the uncertain inputs. For one
input X and the result Y, the first-order (Sobol) share is

    S_X = Var(E[Y | X]) / Var(Y),

the part of Y's variance that X explains on its own. It is estimated here from the n (X, Y) pairs the model
already produced ("given data"), with no new runs. Sort the runs by X, cut them into B equal-count bins, and
compare the spread of the bin means of Y with the spread of Y:

    Ŝ_X = Σ_b n_b (ȳ_b − ȳ)² / Σ_i (y_i − ȳ)².

Even an X that does nothing gives Ŝ_X ≈ (B − 1) / (n − 1) by chance, because bin means of noise still differ.
`first_order` subtracts that expected chance level and floors at 0. With n = 1,000 and B = 20 the chance level
is 0.019, so shares under about 3% are reported as noise.

Limits, said plainly where the shares are shown:
- Shares of correlated inputs overlap (each includes what it shares with the other), so they need not sum
  to 1.
- What no recorded input explains (place-to-place luck, which places' rules are drawn, interactions) is
  1 − (the sum of the shares), shown as "other".
- Total-order shares (an input's effect including its interactions) need new model runs and are not
  estimated here.

By hand (`test_first_order_by_hand`): eight runs, X = 1..8, Y = 0 for X ≤ 4 and 1 for X > 4, two bins. The
bin means are 0 and 1, the overall mean 0.5: between-bin sum 4 × 0.25 + 4 × 0.25 = 2, total sum 8 × 0.25 = 2,
so the raw share is 1. The chance level is (2 − 1) / (8 − 1) = 1/7, and (1 − 1/7) / (1 − 1/7) = 1.
"""

from __future__ import annotations

import numpy as np


def first_order(x, y, bins: int = 20) -> float:
    """Ŝ_X with the chance level removed: (raw − c) / (1 − c), c = (bins − 1) / (n − 1), floored at 0.

    A constant X explains nothing (0). Ties in X stay in one bin (bins are cut at X's quantiles, then runs
    with the same X share the lower bin), so a two-valued X gets at most two bins.
    """
    x, y = np.asarray(x, dtype=float).ravel(), np.asarray(y, dtype=float).ravel()
    keep = np.isfinite(x) & np.isfinite(y)
    x, y = x[keep], y[keep]
    n = x.size
    if n < 2 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return 0.0
    edges = np.unique(np.quantile(x, np.linspace(0, 1, bins + 1)))
    b = np.clip(np.searchsorted(edges, x, side="right") - 1, 0, len(edges) - 2)
    used = np.unique(b)
    total = float(((y - y.mean()) ** 2).sum())
    between = float(sum((b == k).sum() * (y[b == k].mean() - y.mean()) ** 2 for k in used))
    raw = between / total
    chance = (len(used) - 1) / (n - 1)
    return max(0.0, (raw - chance) / (1 - chance))


def drivers(inputs: dict[str, np.ndarray], y, bins: int = 20) -> dict[str, float]:
    """{input: first-order share} for every input that varies, plus "other" = 1 − sum of the shares
    (floored at 0)."""
    out = {k: first_order(v, y, bins) for k, v in inputs.items() if np.ptp(np.asarray(v, dtype=float)) > 0}
    out["other"] = max(0.0, 1.0 - sum(out.values()))
    return out
