# Ledger Search Lab

`search_lab.py` runs reproducible method comparisons for the current
`n^4`-smooth one-shot certificate format.  It writes ignored artifacts under
`search_runs/` so experiments can be compared without editing challenge files.

## Generate Targets

```bash
python3 search_lab.py targets --start 52 --end 80
```

This writes:

```text
search_runs/targets.csv
```

with `exponent,p,gap,bitlength,n2,n4,bound`.

## Run A Method

```bash
python3 search_lab.py run \
  --method two_sided_factor \
  --exponent 60 \
  --curves 10 \
  --seed 20260701
```

Available methods:

- `baseline_gp`: one-sided search with upstream `smoothpart`.
- `factor_smoothpart`: one-sided search with PARI `factor(N, B)` smoothpart.
- `two_sided_gp`: tests curve and twist orders after one `ellcard`, using upstream `smoothpart`.
- `two_sided_factor`: tests curve and twist orders after one `ellcard`, using `factor(N, B)` smoothpart.

Each run appends curve-level and run-finished events to:

```text
search_runs/ledger.jsonl
```

Verified certificates are written to:

```text
search_runs/certs/
```

## Calibrate Methods

```bash
python3 search_lab.py calibrate --curves-52 20 --curves-60 10 --seed 20260701
```

Calibration uses the same PARI seed for every method at a given exponent so the
early sampled curves line up across methods.  This makes per-curve timing and
smooth-bit comparisons meaningful.

## Summarize The Ledger

```bash
python3 search_lab.py summary
```

This writes:

```text
search_runs/summary.csv
```

with method/exponent totals, hit counts, best smooth bits, median seconds per
curve, and certificates per CPU-hour.

## Launch A Parallel Sweep

Use `sweep` after calibration selects a method:

```bash
python3 search_lab.py sweep \
  --methods two_sided_factor \
  --exponents 53 \
  --workers 10 \
  --jobs 10 \
  --curves-per-worker 25 \
  --seed-start 2026075300 \
  --stop-after-hits 1
```

Each worker runs an independent seed shard.  Shards are written to:

```text
search_runs/shards/
```

and merged into:

```text
search_runs/ledger.jsonl
```

When `--stop-after-hits N` is set, the sweep stops launching new shards and
terminates remaining workers after completed shards contain `N` verified hits.
Partial worker shards are still merged, so the ledger records the work already
done before termination.

Worker logs are kept under:

```text
search_runs/logs/
```

For selective pressure between a winner and a challenger, split the jobs:

```bash
python3 search_lab.py sweep \
  --methods two_sided_factor factor_smoothpart \
  --exponents 53,60,70,80 \
  --workers 10 \
  --jobs 10 \
  --curves-per-worker 10 \
  --seed-start 2026077000
```

## Smoke Tests

```bash
python3 search_lab.py run --method two_sided_factor --prime 101 --curves 5 --seed 1
python3 search_lab.py sweep --methods two_sided_factor --exponents 52 --workers 2 --jobs 2 --curves-per-worker 1 --seed-start 2026070199
python3 voneshot.py --test
python3 - <<'PY'
from voneshot import verify
with open("challenge.csv", encoding="utf-8") as f:
    for line in f:
        vals = [int(x) for x in line.replace(",", " ").split()]
        assert verify(vals[0], vals[1], vals[2], vals[3], vals[4:])
print("challenge.csv ok")
PY
```
