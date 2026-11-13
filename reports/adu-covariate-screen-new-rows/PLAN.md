# D-083 screen rerun on the accepted ADU rule rows (written before the run, 2026-11-13)

Ben asked on 2026-11-13 to accept PR #417's rows and rerun the D-083 place-factor screen on them ("Yes, do both").
This is a replication: the screen, factors, bars and thresholds are exactly D-083's (`config/params/adu_screen.yaml`).

What changes, and only this:
- **Rule rows:** `config/reforms/*.csv` as on branch `ws/adu-rules-config` (#417's 153 rows).
- **Form A multipliers:** m_o 1.0, m_x 0.7, Form A's maximum-likelihood fit on these rows (A′ in
  `reports/adu-version-c-2026-11/run/fits.csv`, branch `ws/adu-version-c`), in place of D-079's 1.0 and 0.4.
  Passed with `--m-owner 1.0 --m-other 0.7`.

Then the leave-one-place-out check (`--influence`) on whatever passes, as D-083 added it.

Read: do owner share (X1) and pre-1960 housing (X2) still pass all three bars, and does any other factor join them?
Nothing is adopted; adding a factor to the model needs its own method entry. St. Paul stays out; offline; no `--unblind`.
