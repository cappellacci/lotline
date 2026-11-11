# config/validation

Hand-coded inputs for validation tests, each with a source. Nothing here is an outcome a test scores.

- `or_adu_history.csv`: published ADU permits before 2018 for V9's ADU targets (analysis plan D-052).
  The loader (`lotline.validation.v9.load_history`) refuses any year from 2018 on.
  - **Portland:** 2009, 2010 and 2016 are published in Ord. 189050's findings. 2011–2015 and 2017 aren't in
    any official source found yet.
  - **Bend:** no official yearly count was found for 2009–2017. The city site rate-limited fetches, and the 2016
    ADU amendment record (PZ-15-0849) wasn't reached. With no rows, Bend's own-history variant equals its
    transfer prediction.
- `adu_roll_counts.csv`: second homes gained between two parcel rolls, per jurisdiction, copied from the roll
  comparisons already on `main` (`reports/nc/wake-roll-adu-diff.md`, `reports/oh/franklin-roll-adu-diff.json`).
  Unlike the files above, this one **is** scored: it is the observed side of D-074 test B (the roll check),
  run by `scripts/dev/adu_joint_refit.py`. `sets_k` marks the city whose roll set a flag undercount k
  (Raleigh); test B leaves it out. `first_year`-`last_year` are the model years the roll window covers.
  These counts were published before D-079, so they are not a holdout.
