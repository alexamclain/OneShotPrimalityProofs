# Research overview

This note is a short map of the search directions explored around the
one-shot primality challenge and the aggregate Hasse-window variant.  The
detailed technical trail is in `scaling_method.md`; this file is meant to help
a reviewer see what has already been tried.

## Baseline: random one-shot search

The baseline search samples Montgomery curves, asks PARI/SEA for the full
point count, and keeps a curve or twist when the smooth point order exceeds the
one-shot bound.  The random-order model explains why this works at the current
range but becomes expensive:

```text
10^47 target: expected random trials about 10^5.2
10^60 target: expected random trials about 10^6.7
10^80 target: expected random trials about 10^9.2
10^100 target: expected random trials about 10^11.8
```

The completed `10^48` one-shot certificate was found after 59,309 tested
curves.  That is consistent with the model: more engineering can push the
range somewhat, but the smooth-tail probability remains the central obstacle.

## Hindsight filters at 10^48

After the `10^48` certificate was known, several prefilter families were
benchmarked against the random stream.  The best ones were real engineering
wins but not scaling breakthroughs:

```text
streaming q0=11 mixed-profile prefilter: about 10.5x
streaming q0=3  mixed-profile prefilter: about  7.1x
best static mixed profiles:              about  5-6.5x
same-prime q-primary screens:            about  1.5-2.4x
```

These methods mostly would have found different promising curves, not the
exact winning curve.  The best extracted smooth parts in the prefilter panels
were still far below the one-shot threshold, so these are useful shortlist
layers rather than a new asymptotic source.

## Point-order calibration

One correctness caveat is that a smooth group order is not always a smooth
point order.  If

```text
E(F_p) ~= Z/n1Z x Z/n2Z
```

then a certificate point can have order at most `n2`, and small factors can be
lost into the first invariant.  A pessimistic max-split simulation at `10^48`
did not show a large effect: in 200,000 random Hasse-window orders, the usual
order-smooth tail and the corrected point-exponent tail both had one hit above
the verifier threshold.  This is important for verification and modeling, but
it did not reveal a hidden speedup.

## Partial SEA and SEA-prefix screening

A natural engineering idea is to stop treating SEA as a black box.  Instead of
recovering the whole trace for every curve, expose the trace residues as SEA
processes small auxiliary primes and score curve/twist smoothness directly.

Experiments with PARI debug output and local SEA patches showed that this is
the right implementation layer, but the simple prefix screen is too weak to
change the smooth-tail exponent.  At `10^48`, generic SEA recovers the full
trace after auxiliary primes only up to about `67`, which is less than 1% of
the primes allowed by the verifier's smoothness bound.  The known `10^48`
winner has 80.41 bits of extracted smooth point order, but only 21.78 bits are
visible at primes `<= 67`; most of its mass is in later primes such as `139`,
`991`, `7573`, `16759`, and `25523`.

Forcing SEA to look farther does expose more relevant factors, but it quickly
becomes slower than just finishing the point count.  Smoothness-aware early
abort remains a plausible engineering improvement, but the evidence says it
does not change the underlying rare-event probability.

## CM and order-first searches

The order-first CM route tries to choose a smooth divisor first and then find a
trace satisfying

```text
t == p + 1 mod M
t^2 + D v^2 = 4p
```

This is conceptually attractive because it attacks the trace distribution
instead of merely filtering random curves.  Small-discriminant experiments,
however, were negative at high range.  Scanning fundamental discriminants up
to `D <= 10^6` found no one-shot threshold crossings at `10^48` or `10^80`;
the best smooth-rich represented orders remained substantially below the
thresholds.

The entropy model explains the obstruction.  Forcing an `M0`-bit smooth
divisor generally requires discriminants of about `2*M0` bits just to expect a
trace.  At `10^80`, forcing an `M0` near the 133-bit one-shot bound points to
roughly a 264-bit discriminant, with class-number scale around 132 bits.  So
CM is not ruled out, but the missing primitive would have to construct or
navigate large-discriminant isogeny classes far below class-number cost.

## Congruence, torsion, and lift-profile probes

Many local-filter variants were explored: q-primary valuation screens, mixed
valuation profiles, forced torsion, q-adic towers, line/gate coupling, class
packet relations, residual medium-prime menus, and trace-residue gates.  The
common pattern was:

- they can create useful shortlist scores at `10^48`;
- ideal/free oracle versions sometimes look much better than costed versions;
- costed implementations lose much of the apparent advantage;
- the exact winning curve often has only modest valuation structure in the
  primes being screened;
- no local filter yet provides enough smoothness mass to replace the random
  tail.

This was valuable negative information: it suggests that a successful
cryptographic-range method needs either a real trace/order source or a new
certificate shape, not just another local scoring layer.

## Aggregate Hasse-window certificates

The main promising variant is the aggregate Hasse-window certificate.  Instead
of requiring one smooth point order above the one-shot threshold, it collects
several exact smooth point orders on different Montgomery curves.  For every
prime divisor `q | n`, each component gives

```text
m_i | #E_i(F_q)
|#E_i(F_q) - (q + 1)| <= 2 sqrt(q)
```

Thus `x = q + 1` must lie in a Hasse-width periodic interval modulo every
`m_i`.  The verifier intersects these constraints over
`3 <= x <= floor(sqrt(n)) + 1`; if the intersection is empty, then no small
prime divisor exists and `n` is prime.

This turns sub-threshold smooth orders into useful certificate components.  The
evidence so far:

```text
10^20 + 39: verified in 6 curves, 2 points
10^30 + 57: verified in 23 curves, 3 points
10^49 + 9:  verified in 256 curves, 5 accepted points, 97.23 seconds
```

The minimized `10^49 + 9` certificate uses four orders:

```text
68.21, 49.97, 48.80, 48.66 bits
```

all below the 81.39-bit one-shot threshold.  The deterministic intersection
counts shrink from 9268 intervals, to 115, to 2, to empty.  This is therefore
not a disguised one-shot certificate; the proof strength comes from combining
Hasse-window constraints across curves.

The model is also encouraging.  A random Hasse-window simulation at `10^48`
found aggregate hits in 20/20 runs within 20,000 SEA-count samples, with median
hit around 1,106 counts, while one-shot hits occurred in only 1/20 runs.  A
vectorized geometric model at `10^80` found aggregate hits in 20/20 runs within
1,000,000 samples, with median hit around 90,843 samples and no one-shot hits
in the same streams.

## Current caveats

The aggregate method should be presented as a separate generalized certificate
variant, not as satisfying the original one-quadruple challenge format.  The
current verifier is a prototype and currently materializes interval lists, so a
high-range implementation needs a memory-stable emptiness proof or a
CRT/lattice-style certificate for the intersection step.  The model should
also be rerun with extracted point exponents rather than full component smooth
parts, and the actual search needs more profiling at and above the `10^49`
range.

The short version is: engineering filters can buy constant factors, easy CM
and simple SEA-prefix screens do not appear to change the exponent, and the
aggregate Hasse-window certificate is the one route found so far that changes
the search landscape by giving partial smooth-order wins a way to accumulate.
