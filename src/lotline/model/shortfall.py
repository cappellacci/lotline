"""The shortfall view of housing need (Ben, 2026-11-19; analysis plan deviation of that date): the homes a
state still lacks after what it builds anyway, and how much of that the reforms would cover.

    need       = shortage today + household growth over the five years + homes lost over the five years
    homes lost = stock_loss_rate x housing stock x 5
    gap        = need - homes built anyway (the no-change forecast, all building sizes, five years)

Homes built anyway are gross permits from the baseline (results_baseline, size class `all`, the five-year
period), so homes lost are added to the need rather than netted out of the permits. Household growth is used
as projected, negative where a state's households are projected to fall (Ohio). The shortage and growth are
two kinds of need (D-057) that are added here on purpose: the shortage is the backlog, growth is the new
demand.

**Range.** The gap is one large uncertain number minus another, so its range is wide and is taken as bounds,
not percentiles: low = need at its low ends - built anyway at P90; high = need at its high ends - built anyway
at P10. A gap at or below zero means homes built anyway would cover the need at that end.

By hand: shortage 40,000 (40,000 to 160,000), growth 200,000, stock 5,000,000 at 0.3% (0.2% to 0.5%) a year,
built anyway 370,000 (240,000 to 520,000): lost 75,000 (50,000 to 125,000); need 315,000 (290,000 to 485,000);
gap -55,000, from -230,000 to 245,000.
"""

from __future__ import annotations

YEARS = 5


def homes_lost(stock: float, rate: float, years: int = YEARS) -> float:
    """Homes lost over the window: rate x stock x years. By hand: 5,000,000 x 0.003 x 5 = 75,000."""
    return float(stock) * float(rate) * years


def gap(
    shortage: tuple[float, float, float],
    growth: tuple[float, float, float],
    stock: float,
    rate: tuple[float, float, float],
    built: tuple[float, float, float],
) -> dict[str, float]:
    """Need, homes lost and the gap after homes built anyway, each (low, mid, high); built is (P10, P50, P90).

    Returns need_low/need/need_high, lost_low/lost/lost_high and gap_low/gap/gap_high (bounds, see module).
    """
    lost = [homes_lost(stock, r) for r in rate]
    need = [s + g + x for s, g, x in zip(shortage, growth, lost, strict=True)]
    b10, b50, b90 = built
    return {
        "lost_low": lost[0], "lost": lost[1], "lost_high": lost[2],
        "need_low": need[0], "need": need[1], "need_high": need[2],
        "gap_low": need[0] - b90, "gap": need[1] - b50, "gap_high": need[2] - b10,
    }  # fmt: skip
