# Aggregate Hasse-window certificate for 10^49 + 9

This directory is a focused review packet for the aggregate Hasse-window
certificate found for

```text
p = 10000000000000000000000000000000000000000000000009 = 10^49 + 9.
```

This is not an entry in the original one-shot challenge format.  The original
format is a single quadruple `p,A,x,m` with one point order above the one-shot
threshold.  This packet uses a generalized aggregate format:

```text
p,A1,x1,m1,A2,x2,m2,...
```

Each triple asserts an exact smooth point order on a Montgomery curve modulo
`p`.  Together, the Hasse-window residue constraints for these orders have
empty intersection for every possible divisor `q <= sqrt(p)`.

## Files

- `certificate_flat.txt`: minimized four-triple aggregate certificate.
- `search_aggregate_oneshot_10e49_seed20260816.json`: original search artifact
  with five accepted points; the smallest one is redundant in the minimized
  certificate.
- `search_aggregate_oneshot_10e20_seed20260816.json` and
  `search_aggregate_oneshot_10e30_seed20260816.json`: small-range calibration
  runs for the same aggregate method.
- `aggregate_hasse_numpy_10e49_s200k_r5_seed20260815.json`: lightweight
  geometric model panel at the same range.
- `research_overview.md`: short reviewer-facing map of explored search
  directions and negative results.
- `scaling_method.md`: note summarizing the method and scaling evidence.
- `verify_p49.py`: one-command verifier/summary wrapper for this packet.

The aggregate verifier/search/model scripts are included in this directory:

- `vaggregate.py`
- `aggregate_residue_intersection.py`
- `search_aggregate_oneshot.py`
- `aggregate_hasse_certificate_model.py`
- `aggregate_hasse_geometric_model.py`
- `aggregate_hasse_numpy_model.py`
- `smooth_tail_estimate.py`

They use the baseline repository helpers `voneshot.py` and
`cm_search_oneshot.py` from the root.

## Verification

From the repository root:

```bash
python3 aggregate_hasse_p49/verify_p49.py
```

Expected output ends with:

```text
vaggregate.verify = True
intersection_empty = True
```

## Search result

The actual search run used `aggregate_hasse_p49/search_aggregate_oneshot.py`
with seed `20260816`:

```text
curves tested       = 256
accepted points     = 5
elapsed wall time   = 97.23 seconds
one-shot threshold  = 81.387 bits
accepted order bits = 68.21, 45.09, 49.97, 48.80, 48.66
```

The minimized certificate uses the four largest useful orders:

```text
68.21, 49.97, 48.80, 48.66 bits
```

The deterministic Hasse-window intersection shrinks as follows:

```text
68.21-bit modulus -> 9268 intervals, 65924374288956540 candidate x
49.97-bit modulus -> 115 intervals, 424777077729111 candidate x
48.80-bit modulus -> 2 intervals, 1502961755758 candidate x
48.66-bit modulus -> 0 intervals, proof complete
```

Thus no single point order reaches the one-shot threshold, but the combined
constraints rule out every prime divisor `q <= sqrt(p)`.
