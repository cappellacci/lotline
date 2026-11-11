"""The ADU flag undercount k by permit source (D-074 step 1, D-075 step 2, D-078).

A source's counted ADU permits are multiplied by its k: k = true ADU permits / counted ADU permits.
For a field flag k >= 1 (roll-confirmed ADUs the flag missed). For a parser source k = precision / recall
from its own hand check (D-081), which is below 1 when the parser's false positives outnumber its misses.
k scales counted ADU permits only (fit inputs, the D-070 observed floor, the `historical_floor` check and
tests A-C), never eligible lots. The table lives in `config/params/adu.yaml` (`adu_flag_undercount`) and is
loaded by `lotline.config.load_undercount`.

**Each row's distribution.** A split lognormal: the median is `value`, and `low` and `high` sit at the
two-sided `interval`'s quantiles, so ln k = ln value + z * s with s = ln(value / low) / z_q below the median
and ln(high / value) / z_q above it (z_q the standard-normal quantile of (1 + interval) / 2, 1.645 for 90%).

**The prior for an unmeasured field-flag source** (D-078 §1): centre exp(mean ln k) over the measured field
rows, range from the prior's `low` (1.0) to the largest measured field `high`, at the prior's interval.
By hand with Raleigh 1.07 (1.02-1.21), Austin 1.13 (1.09-1.18), Portland 1.06 (1.05-1.07):
centre = exp((ln 1.07 + ln 1.13 + ln 1.06) / 3) = 1.0862, range 1.0-1.21.

**Draws** (D-078 §5). In each simulation draw every field row (measured or prior) uses one shared z, because
they share one detection method; every measured parser row draws its own z. Floor rows, no-k rows and
parser rows without a hand check stay at k = 1 in every draw.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist

import numpy as np
import pandas as pd

from lotline.config import UndercountTable, load_undercount


@dataclass(frozen=True)
class Row:
    """A table row with its k distribution resolved (prior rows filled in; k = 1 rows have low = high = 1)."""

    source: str
    place: str
    kind: str
    value: float
    low: float
    high: float
    interval: float | None
    first_year: int | None
    last_year: int | None
    from_prior: bool
    floor: bool
    low_recall: bool

    @property
    def fixed(self) -> bool:
        return self.interval is None

    @property
    def shared(self) -> bool:
        """Drawn with the one shared field-flag z (D-078 §5)."""
        return self.kind == "field"

    def covers(self, year: int) -> bool:
        return (self.first_year is None or year >= self.first_year) and (
            self.last_year is None or year <= self.last_year
        )

    def quantile(self, z):
        """k at standard-normal z (split lognormal: median `value`, `low`/`high` at the interval's ends)."""
        z = np.asarray(z, dtype=float)
        if self.fixed:
            return np.full(z.shape, self.value)
        zq = NormalDist().inv_cdf((1.0 + self.interval) / 2.0)
        s_lo = math.log(self.value / self.low) / zq
        s_hi = math.log(self.high / self.value) / zq
        return self.value * np.exp(np.where(z < 0, z * s_lo, z * s_hi))


def prior(table: UndercountTable) -> tuple[float, float, float, float]:
    """(centre, low, high, interval) of the prior for unmeasured field-flag sources (D-078 §1)."""
    measured = [r for r in table.rows if r.kind == "field" and r.measured]
    if not measured:
        raise ValueError("the undercount prior needs at least one measured field-flag row")
    centre = math.exp(sum(math.log(r.value) for r in measured) / len(measured))
    high = max(r.high for r in measured)
    return centre, table.prior.low, high, table.prior.interval


def resolve(table: UndercountTable | None = None) -> list[Row]:
    """Every table row with its distribution: own k, the prior, or k = 1."""
    table = load_undercount() if table is None else table
    centre, p_low, p_high, p_int = prior(table)
    out = []
    for r in table.rows:
        if r.measured:
            v, lo, hi, iv = r.value, r.low, r.high, r.interval
        elif r.prior:
            v, lo, hi, iv = centre, p_low, p_high, p_int
        else:  # floor, none, or a parser without a hand check
            v, lo, hi, iv = 1.0, 1.0, 1.0, None
        out.append(
            Row(
                r.source,
                r.place,
                r.kind,
                v,
                lo,
                hi,
                iv,
                r.first_year,
                r.last_year,
                r.prior,
                r.floor,
                r.low_recall,
            )
        )
    return out


class Factors:
    """k per (source, year) in one draw: `rows` with one k each; a source-year no row covers is 1."""

    def __init__(self, rows: list[Row], k):
        self.rows = rows
        self.k = np.asarray(k, dtype=float)

    def index(self, source: str, year: int) -> int:
        """Position of the row covering (source, year), or -1 (k = 1)."""
        for i, r in enumerate(self.rows):
            if r.source == source and r.covers(int(year)):
                return i
        return -1

    def get(self, source: str, year: int) -> float:
        i = self.index(source, year)
        return 1.0 if i < 0 else float(self.k[i])

    def column(self, sources, years) -> np.ndarray:
        """k for each (source, year) pair."""
        cache: dict = {}
        out = np.empty(len(sources))
        for j, key in enumerate(zip(sources, years, strict=True)):
            if key not in cache:
                cache[key] = self.get(key[0], key[1])
            out[j] = cache[key]
        return out


def central(table: UndercountTable | None = None) -> Factors:
    """Each row at its median k (z = 0)."""
    rows = resolve(table)
    return Factors(rows, [r.value for r in rows])


def draw_matrix(rows: list[Row], n: int, rng: np.random.Generator) -> np.ndarray:
    """k per draw and row (n x rows): one shared z for every field row, an own z per other drawn row."""
    shared = rng.standard_normal(n)
    own = rng.standard_normal((n, len(rows)))
    out = np.empty((n, len(rows)))
    for i, r in enumerate(rows):
        out[:, i] = r.quantile(shared if r.shared else own[:, i])
    return out


def draws(n: int, seed: int, table: UndercountTable | None = None) -> list[Factors]:
    """`n` draws of the table's k (D-078 §5), from their own random stream."""
    rows = resolve(table)
    k = draw_matrix(rows, n, np.random.default_rng(seed))
    return [Factors(rows, k[d]) for d in range(n)]


def scale(by_source: pd.DataFrame, factors: Factors | None, count: str = "adu") -> pd.DataFrame:
    """`by_source` (columns source, issue_year, `count`) with `count` multiplied by each row's k and the raw
    count kept as `counted` and the row as `k_row` (-1: no row, k = 1). Unchanged when `factors` is None."""
    if factors is None:
        return by_source
    idx = [factors.index(s, y) for s, y in zip(by_source["source"], by_source["issue_year"], strict=True)]
    k = np.array([1.0 if i < 0 else factors.k[i] for i in idx], dtype=float)
    return by_source.assign(counted=by_source[count], k_row=idx, **{count: by_source[count] * k})


TABLE = "table"  # a builder's default: the table's central k (`central()`); None turns the correction off


def factors_arg(arg) -> Factors | None:
    """A builder's `undercount` argument: TABLE -> `central()`, None -> no correction, Factors as given."""
    return central() if isinstance(arg, str) and arg == TABLE else arg
