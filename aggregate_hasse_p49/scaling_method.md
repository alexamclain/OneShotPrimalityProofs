# Scaling method notes

## Current bottleneck

The present random search samples a Montgomery parameter `A`, asks PARI for an
exact point count, then keeps the curve or its twist when the group order has
an `n^2`-smooth factor above the one-shot lower bound.  This is robust, but it
spends a full SEA point count on almost every curve.

For the challenge targets this is more information than the certificate needs.
The verifier only needs a point whose exact order `m` is:

- greater than `sqrt(p) + 1 + sqrt(4 sqrt(p))`, and
- smooth over primes `<= n^2`, where `n = bit_length(p)`.

It does not need the full group order.

## Random-order barrier

The first question for any proposed speedup is whether it changes the success
probability or only the cost per random curve.  Modeling `#E(F_p)` as a random
integer near `p`, the `n^2`-smooth part has mean only about 14-16 bits in the
current challenge range.  The one-shot lower bound is about half the bitlength
of `p`.

The saddlepoint estimator in `aggregate_hasse_p49/smooth_tail_estimate.py`
gives:

```text
10^47 target: random-trial expectation about 10^5.2 curves
10^60 target: random-trial expectation about 10^6.7 curves
10^80 target: random-trial expectation about 10^9.2 curves
10^100 target: random-trial expectation about 10^11.8 curves
```

A parallel random run did eventually find the `10^48` certificate after 59,309
tested curves:

```text
p = 1000000000000000000000000000000000000000000000193
A = 756629692972229602491961804298556859655820911395
x = 918593905186155312035948211710330034366751932565
m = 1606109062327986974770608
bits(m) = 80.4098
m = 2^4 * 3 * 31 * 41 * 59 * 139 * 991 * 7573 * 16759 * 25523
```

`voneshot.py` verified this certificate.  This is consistent with the random-tail
model: `10^48` is reachable by grinding, while the same strategy still scales
poorly toward `10^80`.

There is one important extraction calibration: a smooth group order is not
always the same thing as a smooth point order.  For
`E(F_p) ~= Z/n1Z x Z/n2Z`, the verifier can use at most the exponent `n2`, and
`n1 | p - 1` can split off some small smooth factors.  The known `10^48`
certificate has full component order
`1000000000000000000000000696074418908822187692192`, whose `n^2`-smooth part is
`81.41` bits, but PARI gives group invariants equivalent to
`Z/2Z x Z/(N/2)Z`, so the actual point order loses one factor of `2` and is
`80.41` bits.

A pessimistic max-split model in `point_exponent_tail_model.py` removes every
smooth factor that could legally sit in the first invariant.  On 200k random
Hasse-window orders at `10^48`, the usual order-smooth tail and this max-split
exponent tail both had `1` hit above the `79.73`-bit verifier threshold, with
average loss only `0.336` bits:

```text
artifact: artifacts/point_exponent_tail_model_10e48_s200000_seed20260812.json
order hits = 1 / 200000
max-split exponent hits = 1 / 200000
lost order-tail hits = 0
known component smooth bits = 81.410
known actual point-order bits = 80.410
```

So the point-exponent distinction is a real correctness caveat and may make
order-smooth tail estimates slightly optimistic, but it does not reveal a
larger hidden source of wins.  It pushes us back toward constructing the marked
point/order directly, or toward a sourceable way to force many trace residues.

## Hindsight speedup audit for 10^48

Now that the `10^48` certificate is known, `hindsight_10e48_speedups.py`
normalizes the explored methods against two baselines:

```text
actual random curves to known certificate = 59,309
two-sided random model expectation        = 10^5.015 ~= 103,548 curve counts
artifact: artifacts/hindsight_10e48_speedups.json
```

The answer is yes, several methods would probably have sped up the `10^48`
range in expectation, but mostly by finding a different certificate, not by
homing in on the exact winning curve:

```text
streaming q0=11 mixed-profile prefilter: 1.019 log10 ~= 10.5x
streaming q0=3  mixed-profile prefilter: 0.851 log10 ~=  7.1x
best static mixed profile, q0=11:        0.811 log10 ~=  6.5x
best static mixed profile, q0=3:         0.760 log10 ~=  5.7x
same-prime q-primary q=3 screen:         0.384 log10 ~=  2.4x
same-prime q-primary q=5 screen:         0.333 log10 ~=  2.2x
same-prime q-primary q=7 screen:         0.173 log10 ~=  1.5x
```

Interpreted against the actual `59,309`-curve run, the strongest streaming
profile model corresponds to roughly `5,700-8,400` random-curve equivalents.
That is a real engineering win.  It is not a mathematical scaling breakthrough:
the best rows in those profile-prefilter panels still reached only
`42.77-47.73` extracted smooth bits, far below the `79.73`-bit verifier
threshold.

For the exact winning curve, the story is more sobering.  Its component order
has small valuations:

```text
2^5 * 3 * 31 * 41 * 59 * 139 * 991 * ...
```

It has no factor `11`, so the q0=11 prefilter would not have found this
particular curve.  It has only one factor of `3`, so the high-depth q=3
q-primary screens would not have selected it either.  The SEA-prefix replay does
see the winner, but late: its visible product is only `4.17` bits through 8
records, `7.54` bits at 10 records, `12.90` bits at 12 records, and `18.78`
bits at 16 records.  In the known-plus-random80 replay it enters the top-10
only after enough SEA work that the gain is at most modest.

The methods that did not help are just as important:

- small-D/easy CM had zero threshold crossings through `D <= 10^6`;
- trace-CRT/source constructions still miss the break-even source budget by a
  large class-number gap;
- point-exponent modeling is a correctness calibration, with no speedup;
- costed medium-prime menus after a profile were worse than profile-only, even
  though ideal/free oracle menus looked much better.

So the practical recommendation for another `10^48`-scale run would be:
use a q0=3/q0=11 mixed-profile prefilter and only then pay full SEA on a
shortlist.  The mathematical recommendation is unchanged: a scalable method
still needs a real source for coupled trace/eigenline conditions, not just a
better local scoring layer.

## Candidate: aggregate Hasse-window certificates

There is one new route that is qualitatively different from the local filters
above.  The current verifier asks for one smooth point order `m` larger than
the largest possible elliptic-curve group order over any prime
`q <= sqrt(n)`.  That forces `m ~= n^(1/2)`.

An aggregate variant would collect several exact smooth point orders
`m_1, ..., m_r` on different curves over `Z/n`.  If `q | n`, then each reduced
curve satisfies

```text
#E_i(F_q) = k_i m_i
|#E_i(F_q) - (q + 1)| <= 2 sqrt(q).
```

So `q + 1` must lie in a Hasse-width window modulo every `m_i`.  Let
`W ~= 4 n^(1/4)` bound the number of allowed residues per order and let
`M = lcm(m_i)`.  The random-density estimate for surviving small divisors is

```text
expected survivors ~= sqrt(n) * W^r / M
surplus bits        = log2(M) - r log2(W)
target surplus      = log2(sqrt(n)).
```

The lcm/window inequality is only a density heuristic, not the certificate
itself.  The deterministic proof is the actual integer interval intersection:
intersect the windows for `x = q + 1` over
`3 <= x <= floor(sqrt(n)) + 1`; if the intersection is empty, then no
`q <= sqrt(n)` can divide `n`.  This verifier is now implemented in
`aggregate_hasse_p49/aggregate_residue_intersection.py` and wired into
`aggregate_hasse_p49/vaggregate.py`.  The
interval enumerator is deliberately capped, because unlucky or over-broad
cryptographic-size intersections can otherwise materialize millions of Python
intervals; an interval explosion is treated as a failed proof attempt, not as a
reason to keep allocating memory.

The exact-Hasse simulation in
`aggregate_hasse_p49/aggregate_hasse_certificate_model.py` uses random
Hasse-window orders and greedily adds a component only when its new lcm bits
beat the `log2(W)` tax.  At `10^48`:

```text
artifact: artifacts/aggregate_hasse_cert_model_10e48_s20000_r20_seed20260813.json
20/20 aggregate hits within 20,000 SEA counts
median aggregate hit = 1,106 SEA counts
min / max = 184 / 2,147
median components = 14
one-shot hits in same streams = 1/20
```

A vectorized geometric-valuation model in
`aggregate_hasse_p49/aggregate_hasse_numpy_model.py`
matches the `10^48` scale and gives the first encouraging `10^80` estimate:

```text
artifact: artifacts/aggregate_hasse_numpy_10e80_s1e6_r20_seed20260815.json
20/20 aggregate hits within 1,000,000 sampled SEA counts
median aggregate hit = 90,843 SEA counts
min / max = 23,828 / 148,682
median components = 25
median best individual smooth component = 94.65 bits
one-shot hits in same streams = 0/20
```

Compared with the two-sided one-shot model at `10^80`
(`10^8.926` curve/twist trials), this is a `~10^4` rare-event improvement in
the model.  The accepted components are not certificate-sized individually;
they are moderate `70-110` bit smooth pieces whose lcm accumulates faster than
the Hasse-window tax.

Actual end-to-end searches now confirm that this is more than a scoring model:

```text
artifact: aggregate_hasse_p49/search_aggregate_oneshot_10e20_seed20260816.json
10^20 + 39: verified in 6 curves, 2 points
order bits = 30.50, 22.56
one-shot bound = 33.22 bits

artifact: aggregate_hasse_p49/search_aggregate_oneshot_10e30_seed20260816.json
10^30 + 57: verified in 23 curves, 3 points, 8.28 seconds
order bits = 32.54, 31.97, 43.19
one-shot bound = 49.83 bits

artifact: aggregate_hasse_p49/search_aggregate_oneshot_10e49_seed20260816.json
10^49 + 9: verified in 256 curves, 5 accepted points, 97.23 seconds
order bits = 68.21, 45.09, 49.97, 48.80, 48.66
one-shot bound = 81.39 bits
```

The `10^49` certificate minimizes to four points: sorted by order size, the
deterministic interval counts go

```text
68.21 bits -> 9268 intervals, 65924374288956540 candidate x
49.97 bits -> 115 intervals, 424777077729111 candidate x
48.80 bits -> 2 intervals, 1502961755758 candidate x
48.66 bits -> 0 intervals, proof complete
```

The four-point minimized certificate verifies independently with
`aggregate_hasse_p49/vaggregate.py`.
Every point order is far below the `81.39`-bit one-shot threshold, so this is a
genuine aggregate certificate rather than a disguised one-shot success.

The next decisive tasks are therefore:

- replace the interval-list verifier with a memory-stable emptiness certificate
  or a lattice/CRT-style intersection proof for the high range;
- rerun the model with extracted point exponents rather than full component
  smooth parts, to price non-cyclic group loss;
- run actual aggregate searches at and above the `10^48`/`10^49` range with
  profiling, so the model's SEA-count gains can be compared with real wall time.

This explains why pure random-curve search can plausibly reach a little beyond
the current range with enough engineering, but should not be expected to reach
cryptographic sizes comfortably.

For comparison, generic SEA trace reconstruction only needs an auxiliary-prime
product larger than roughly `4 sqrt(p)`.  At the `10^80` target this is about
135 bits of auxiliary-prime product, while testing divisibility by every prime
up to `n^2` means considering 7007 primes.  This is the catch in a naive
partial-SEA screen: it can save some rejected point counts, but by itself it
does not change the rare-event probability.

## Order-first CM congruence search, now demoted

One natural way to change scaling is to choose the smooth divisor first, then
construct a curve whose Frobenius trace realizes it.  The experiments and
entropy model below now demote the small-discriminant version of this idea, but
the framing is still useful because it explains what a successful trace-first
method would have to overcome.

Let `M` be an `n^2`-smooth integer above the one-shot lower bound.  We want a
trace `t` and a manageable CM discriminant `-d` such that

```text
t^2 + d v^2 = 4p
t == p + 1 (mod M)
```

Then `M | p + 1 - t`, so a curve with Frobenius trace `t` has group order
divisible by the desired smooth integer by construction.  The existing
`sc_try_order` and `voneshot.verify` code can then extract and verify a point
certificate from the constructed curve.

This reframes the search as a norm-congruence problem in an imaginary
quadratic order:

```text
Norm(pi) = p
pi == 1 (mod M)
Norm(1 - pi) = p + 1 - t
```

The hard part is keeping `d` small enough that CM construction is practical.
For a fixed prescribed `M` near `sqrt(p)`, the Hasse interval contains only a
constant number of compatible traces, and their squarefree discriminants are
usually huge.  The next search should therefore be hybrid rather than all-or
nothing:

- force a sizeable smooth divisor `M0`, smaller than the final bound;
- search CM traces satisfying `t == p + 1 (mod M0)`;
- use the random residual cofactor to provide the remaining smooth part;
- tune `M0` to balance trace density, discriminant size, and residual
  smoothness probability.

This is the mathematical path that can genuinely beat random curves if it can
find a useful balance.  It uses the freedom of one-shot certificates: the
smooth divisor need not be a power of two and need not equal the entire group
order.

### CM congruence implementation sketch

Start with a diagnostic search rather than full curve construction:

```python
def cm_norm_congruence_candidates(p, B, bound, forced_bits, max_d):
    for M0 in smooth_numbers_with_bits(B, forced_bits):
        for d in small_fundamental_discriminants(max_d):
            # Solve the norm congruence modulo M0:
            #   t == p + 1 mod M0
            #   t^2 + d*v^2 == 4p
            # Lift compatible residues into the Hasse interval.
            for t, v in cornacchia_with_trace_congruence(p, d, M0):
                N = p + 1 - t
                s = smooth_part(N, B)
                if s > bound:
                    yield d, t, N, s
```

The first measurable milestone is not a certificate; it is finding traces where
`s > bound` while `d` is small enough for class-polynomial construction.  If
that happens at high exponents, the existing `cm_search_oneshot.py` extraction
path can be reused.

`cm_congruence_sieve.py` implements this diagnostic.  Two early checks are
important:

- On the `10^8` target it rediscovers known low-discriminant traces such as
  `D=-71`, `D=-247`, and `D=-991` when powers of two are included as forced
  divisors.  This validates the trace/order congruence.
- On the `10^20 + 39` target, giving it the known smooth divisor
  `4211767679201901` immediately recovers the existing `D=-1923` trace.

The first random high-range sample was negative:

```text
10^47 target, forced_bits=60:76, 200 M0 samples, 40097 traces:
no recognized D <= 10^16 using the limited square-prime screen

10^48 target, forced_bits=60:72, 60 M0 samples, 118132 traces:
no recognized D <= 10^6 using the limited square-prime screen

10^48 target, forced_bits=60:72, 50 M0 samples, 144702 traces:
no recognized D <= 10^6 using the limited square-prime screen
```

This does not rule out the congruence route, because the limited screen can
miss large conductor factors.  It does show that naive random `M0` sampling is
not enough; the next variant should choose `M0` and the residual `r` with a
square-sieving objective, or solve congruences modulo candidate discriminants
before invoking exact `core`.

`cm_square_sieve.py` implements the square-sieving variant.  For fixed `M0`, it
solves

```text
(p + 1 - M0*r)^2 == 4p (mod q^2)
```

for many small primes `q`, combines the resulting `r` classes by CRT, and only
then checks the CM core of `4p - t^2`.  This gives a useful prefilter:

```text
10^8 target, forced_bits=8:14:
  53 square-sieved residuals found D=-991 successes.

10^20 target, forced_bits=24:34:
  1823 square-sieved residuals plus exact core found a success with D=-109238694.

10^47 target, forced_bits=54:70:
  48708 square-sieved residuals found no recognized D <= 10^16 in limited mode.
  Exact core at this size was too slow for broad scans without a stronger prefilter.

10^48 target, forced_bits=52:64:
  73332 square-sieved residuals found no recognized D <= 10^12 in limited mode.

10^48 target, forced_bits=48:64:
  20463 square-sieved residuals found no recognized D <= 10^12 in limited mode.
```

This clarifies the main obstruction.  If `Q` is the product of forced square
primes, then the expected number of residuals left after the CRT conditions is
roughly

```text
(4 sqrt(p) / M0) * product_q (2 / q^2).
```

But making the discriminant at most `Dmax` typically requires
`Q` on the order of `sqrt(p / Dmax)`.  At high `p`, once `M0` is already large
enough to help with the smooth-order requirement, the Hasse window does not
have enough entropy left to force a conductor large enough for small-D CM.
This makes order-first CM useful as a diagnostic and maybe for medium sizes,
but unlikely to be the final cryptographic-range method by itself.

`cm_entropy_tradeoff.py` makes the same obstruction independent of the square
sieve implementation.  With `N = M0*r = p + 1 - t`, the Hasse interval gives
about `4 sqrt(p)/M0` residual choices.  To have CM discriminant at most `Dmax`,
we need `4p - t^2 = D*v^2` with `D <= Dmax`, so the square root of the forced
square part is on the order of `sqrt(p/Dmax)`.  A random integer is divisible
by a square with root at least `V` with probability about `1/V`, giving

```text
expected small-D traces ~= 4 sqrt(Dmax) / M0.
```

So the price of forcing an `M0`-bit smooth divisor is a discriminant of about
`2*M0 - 4` bits just to expect one trace.  At the `10^48` target:

```text
M0 bits  required D bits for E~=1  class-number scale
40       76                         38
60       116                        58
80       156                        78
```

The known successful `10^48` curve lands exactly on this boundary: its
`core(4p - t^2)` is a 156-bit discriminant, far outside practical CM
construction.  At `10^80`, forcing an `M0` near the 133-bit one-shot bound
requires about a 264-bit discriminant for even one expected trace, with
class-number scale around 132 bits.  This rules out small-discriminant
order-first CM as the cryptographic-range escape route; a successful
trace-first method would need a way to construct large-discriminant isogeny
classes without class-polynomial cost, or a different high-genus/torsion-tower
representation of the certificate point.

`smooth_trace_class_probe.py` tests the same obstruction from the opposite
direction: first choose smooth-rich Hasse orders, then measure the CM class
size hidden behind their traces.  At `10^48`, a 30k random-order sample plus
the known certificate and the exact `10^48` order gave:

```text
artifact: artifacts/smooth_trace_class_probe_10e48_s30000_known.json

exact order N=10^48:
  trace = gap + 1 = 194
  smooth bits = 159.45
  D bits = 150
  class-number scale ~= 74.73 bits

known 10^48 certificate order:
  smooth bits = 81.41
  D bits = 156
  class-number scale ~= 77.63 bits

best random smooth-rich sample:
  smooth bits = 84.30
  D bits = 162
  class-number scale ~= 80.69 bits
```

`smooth_order_discriminant_correlation.py` tightens this by keeping a uniform
reservoir and the top smooth orders from the same random Hasse-order stream,
then computing exact CM cores only for the retained rows:

```text
artifact: artifacts/smooth_order_discriminant_correlation_10e48_s200000_r2000_top500_known_seed20260807.json

10^48, 200k random Hasse orders:
  stream successes = 2/200000

uniform reservoir, 2000 rows:
  smooth median = 12.49 bits
  D median = 160 bits
  class-number median ~= 79.69 bits

top smooth, 500 rows:
  smooth median = 56.56 bits
  D median = 159 bits
  class-number median ~= 79.40 bits

one-shot successes:
  smooth bits = 80.10 and 80.86
  D bits = 160 and 162
  class-number scale ~= 79.72 and 80.71 bits

explicit rows:
  exact order N=10^48: smooth = 159.45 bits, D = 150 bits, class ~= 74.73 bits
  known certificate:    smooth =  81.41 bits, D = 156 bits, class ~= 77.63 bits

reservoir correlations:
  Pearson(smooth, D bits) ~= -0.075
  Spearman(smooth, D bits) ~= -0.089
```

So smooth-rich Hasse orders are essentially class-generic in this sample.  The
top smooth tail does not expose a hidden low-discriminant population; the only
meaningfully lower class-scale rows are the explicit dream order and the known
certificate, and even those are still around `75-78` class bits at `10^48`.

This is the trace-first paradox in its cleanest form.  The challenge primes
have a perfect-looking target trace: if `p = 10^e + gap`, then
`t = gap + 1` gives `#E = 10^e = 2^e 5^e`.  The verifier would love that
order, but constructing the isogeny class is still a large-discriminant CM
problem:

```text
artifact: artifacts/dream_trace_discriminant_scaling.json

10^48:  D bits = 150, class-number scale ~=  74.73 bits
10^60:  D bits = 200, class-number scale ~=  99.66 bits
10^80:  D bits = 251, class-number scale ~= 125.29 bits
10^100: D bits = 333, class-number scale ~= 166.10 bits
```

So the trace/order-first branch is not dead mathematically, but its required
missing primitive is now precise: construct a large-discriminant isogeny class
or an equivalent marked torsion point at far below class-number cost.  Without
that primitive, choosing smoother orders first just moves the hard work from
smooth-tail search into CM class construction.

## Secondary method: smoothness-aware partial SEA

Use SEA as a residue oracle instead of as a full point-counting black box.

For each random Montgomery curve `E_A`, run only the small-prime part of SEA for
auxiliary primes `l <= n^2`.  Each Elkies step gives the trace modulo `l`.
Then:

- if `t == p + 1 (mod l)`, multiply the curve-side accumulator by `l`;
- if `t == -(p + 1) (mod l)`, multiply the twist-side accumulator by `l`;
- include prime powers by lifting or by repeated local order checks when cheap;
- stop the partial count as soon as either accumulator exceeds the one-shot
  lower bound;
- only then call the existing exact `ellcard`/`sc_try_order` path to extract
  and verify a certificate.

This changes the search from:

```text
full SEA on every sampled curve
```

to:

```text
partial SEA screen on every sampled curve
full SEA only on curves already known to have enough small-order divisibility
```

The mathematical advantage is that the screen computes exactly the information
the one-shot certificate cares about: small prime divisibility of `#E(F_p)` and
of the twist order.  It avoids reconstructing the entire trace modulo a product
larger than `4 sqrt(p)` unless the curve is already promising.

PARI's [`ellsea` documentation][pari-ellsea] confirms that its SEA
implementation already has early-abort logic keyed to small prime divisors of
the order.  That is the right layer to fork or reimplement: expose the
per-auxiliary-prime trace residues instead of returning only the final order.

`sea_abort_factor_probe.py` tests a no-fork version of this idea.  With
`default(debug,1)`, PARI prints the prime that caused an `ellsea(E,tors)` early
abort:

```text
Aborting: #E(Fq) divisible by 41
```

The probe captures that line, multiplies the aborting prime into `tors` when it
is still within the `n^2` smoothness bound, and repeats.  For twist-side
candidates it feeds SEA the actual quadratic-twist model
`[0, A*d, 0, d^2, 0]`, so the abort prime belongs to the selected component.

At `10^48`, starting from only the forced `4*13` torsion on the top `M=13`
forced-component candidates:

```text
source candidates = 80
max SEA-abort steps = 3
elapsed time = 28.30s
full orders returned = 49
best exposed torsion score = 20.19 bits
correlation with known smooth component bits = 0.30
best 57.96-bit smooth row SEA-prefix rank = 24

source candidates = 120
max SEA-abort steps = 4
elapsed time including top-40 extraction = 84.23s
full orders returned during probe = 111
best exposed torsion score = 23.37 bits
best extracted point order after top-40 extraction = 57.96 bits
best 57.96-bit smooth row SEA-prefix rank = 17
correlation on the 80 previously counted rows = 0.38
```

This is a better partial-SEA signal than first-depth Kummer gates for medium
primes: it sees factors like `43`, `59`, `61`, and `67` without `Z_q`
polynomials.  But it is not yet a search breakthrough.  In this pool the
stock `ellsea` API often returns the full order after only a few admitted abort
primes, so the probe drifts back into point counting.  The actionable lesson is
to expose SEA residues directly rather than scrape the abort interface: stop
after each auxiliary prime with the current smoothness score, instead of
letting `ellsea` decide whether it already has enough information to finish.

`ellsea(E, -tors)` is also useful diagnostically: the negative `tors` flag asks
PARI to abort when either the curve or its quadratic twist has a disallowed
prime divisor.  The debug output distinguishes the side:

```text
Aborting: #E_twist(Fq) divisible by 13
```

`sea_dual_abort_scout.py` uses that side label to keep separate curve/twist
prefix products for ordinary random Montgomery curves.  On `10^48`:

```text
samples = 80
max SEA-abort steps = 4
elapsed time = 44.33s
full orders returned = 63
best exposed prefix = 15.88 bits
best exact smooth side among full orders = 39.95 bits
best extracted point order = 39.95 bits
correlation(prefix bits, exact smooth bits) = 0.245
```

This confirms that the negative-`tors` interface can scout both certificate
sides in one call, but the prefix score is too weak and the API again falls
back to full SEA too often.  It is evidence for a source-level partial-SEA
primitive, not for further debug-output scraping.

Inspecting PARI `2.17.3` source identifies the exact patch point:

```text
src/basemath/ellsea.c
  find_trace(...) returns trace residues modulo ell^k or Atkin candidates.
  Fq_ellcard_SEA(...) tests
      card_mod_ell = q + 1 - t_mod_ellkt
      tcard_mod_ell = q + 1 + t_mod_ellkt
    immediately before the current smallfact abort.
```

The temporary patch saved as
`artifacts/patches/pari-2.17.3-ellsea-prefix-debug.patch` adds one debug line
at that location.  A `10^48` smoke test in
`artifacts/sea_prefix_debug_smoke_10e48.txt` shows the desired record:

```text
Elkies mod 5 prefix_trace=4 mod=25 curve_div=1 twist_div=0
Aborting: #E(Fq) divisible by 5
```

This is stronger than the Python debug scraper: the prefix line exposes the
trace modulo `ell^k` (`25` here), and therefore can carry q-adic information
already computed by SEA.  The q-adic tower probes above were computing the same
kind of Smith data by solving local preimage equations; a patched SEA prefix
can get it from the trace path directly for Elkies primes.

The stronger temporary patch
`artifacts/patches/pari-2.17.3-ellsea-prefix-records.patch` prints prefix
records even when `ellsea(E,0)` is allowed to finish.  This lets us replay the
SEA stream as if a future primitive had stopped after a fixed number of
auxiliary primes.  `sea_prefix_gp_scout.py` parses those records and scores the
visible curve/twist smooth product from the trace residues.

Two `10^48` replays are now recorded:

```text
forced M=13 candidate pool, top 40:
  records per curve = 17-18
  best exact smooth side = 57.96 bits
  prefix-count correlations:
    4 records:  0.113
    6 records:  0.210
    8 records:  0.166
    10 records: 0.068
    12 records: 0.027
  the best 57.96-bit row ranked 5, 5, 10, 16, 18 respectively.

random curves, 80 samples:
  records per curve = 17-22
  best exact smooth side = 67.20 bits
  prefix-count correlations:
    4 records:  0.162
    6 records:  0.158
    8 records:  0.192
    10 records: 0.225
    12 records: 0.205
  the best 67.20-bit row ranked 24, 28, 8, 10, 13 respectively.
```

This is a valuable negative constraint.  SEA prefix residues are the right
implementation layer, but ranking by the already-visible small-prime product is
still weak: the rare high smooth tails often arrive from primes not yet seen in
the prefix.  A scalable partial-SEA screen therefore needs either a stronger
conditional smoothness model using both positive and negative residue
information, or a construction that changes the trace distribution itself.  The
simple conditional model below rules out the first version of that hope:
simply exposing the first dozen SEA primes is not the asymptotic escape.

The random-order model explains why.  After processing a fixed prefix of SEA
auxiliary primes, the known contribution is a product `S0`.  For unprocessed
primes `q`, the event `q | #E` is still approximately independent with
probability `1/q`, so the expected unseen smooth tail is almost the same for
all curves with the same prefix budget.  Ranking by the conditional expectation
therefore mostly collapses back to ranking by `S0`.  This can reject curves
with very small visible `S0`, but it cannot reliably identify the rare rows
whose remaining smooth tail contains medium primes such as `151`, `307`,
`3307`, `7591`, or other late arrivals.  To beat the tail rather than merely
observe it, the search has to bias the trace/order itself.

`sea_horizon_model.py` makes this sharper.  The public SEA prefix can only see
order factors that occur before SEA has enough auxiliary-prime product to
recover the full trace.  At that point `ellsea` can return the order without
ever querying larger smoothness-bound primes.

```text
artifact: artifacts/sea_horizon_model_10e48_10e100_known_order.json
extended caps: artifacts/sea_horizon_model_caps_known_order.json

10^48:
  smoothness bound B = 25600
  SEA full-trace auxiliary max = 67
  primes <= 67 are only 0.67% of primes <= B
  visible-only tail log10 = -14.60
  full smooth-tail log10 = -5.32

10^80:
  smoothness bound B = 70756
  SEA full-trace auxiliary max = 107
  primes <= 107 are only 0.40% of primes <= B
  visible-only tail log10 = -25.43
  full smooth-tail log10 = -9.23
```

The known `10^48` winner has 80.41 bits in its extracted smooth order, but only
21.78 of those bits are at primes `<= 67`.  A prefix-only SEA screen therefore
cannot rank that winner early; most of the certificate mass is outside the SEA
auxiliary horizon.

Even an idealized targeted-SEA cap below the usual modular-equation boundary
would still miss most of the winner:

```text
known 10^48 winner, visible factor bits:
  q <= 67:     21.78 bits
  q <= 139:    28.90 bits
  q <= 499:    28.90 bits
  q <= 991:    38.85 bits
  q <= 25600:  80.41 bits

random-tail model at 10^48:
  cap 139: tail log10 = -12.56
  cap 499: tail log10 =  -9.75
  cap 991: tail log10 =  -8.60
  full B:  tail log10 =  -5.32
```

So exposing all factors up to `499` would still be roughly four orders of
magnitude too selective relative to the real one-shot smoothness event.  The
first major winner factor beyond `139` is `991`, and the remaining mass comes
from `7573`, `16759`, and `25523`.

A source-level experiment confirms the interpretation.  The temporary patch
`artifacts/patches/pari-2.17.3-ellsea-min-ell-debug.patch` adds an environment
variable `SEA_MIN_ELL` that prevents `ellsea` from returning the full order
until the auxiliary loop has processed at least that prime.  On the known
winner, with torsion already allowing `3*31*41*59`, stock SEA returns the full
order at auxiliary prime `61`.  With `SEA_MIN_ELL=139`, the same run continues
through the intermediate SEA primes and aborts at

```text
SEA_PREFIX ell=139 kind=single mod=139 trace=16 curve_div=1 twist_div=0
Aborting: #E(Fq) divisible by 139
```

This is a useful proof of access to targeted medium-prime divisibility, but not
yet a search method: the run took about `4.7s` for one curve, versus about
`0.35s` for the stock full-order return after the small-prime horizon.  Pushing
the auxiliary horizon upward one prime at a time is therefore worse than full
point counting unless we can jump directly to selected smoothness primes or
reuse the targeted SEA work across many candidates.

The cost gets worse when no new factor appears.  With torsion already allowing
`3*31*41*59*139`, the patched loop returns the full order with these timings:

```text
stock SEA horizon: 0.49s, returns after auxiliary prime 61
SEA_MIN_ELL=139:   4.79s, returns after processing 139
SEA_MIN_ELL=211:  20.92s, returns after processing 211
```

The local PARI build also has no external `seadata` files for `491`, `499`, or
`991`, so a direct `ellmodulareqn(q)` query at those levels fails in this
environment.  Targeted SEA is therefore demoted as a standalone search method:
it is the correct source of information when available, but the mathematically
important factors are too late and too expensive to scan one by one.

`sea_prefix_conditional_scorer.py` makes this failure mode explicit.  It reads
the prefix artifacts, treats single-trace records as exact q-adic information
up to the SEA modulus, lets saturated q-adic records keep a residual geometric
tail, and scores each side by the saddlepoint probability that the unseen
smooth part can still clear the one-shot bound.  On the same `10^48` artifacts:

```text
forced M=13 top 40:
  conditional rank of the best 57.96-bit row matches visible-product rank
  counts 4,6,8,10,12,16: 5,5,10,16,18,18
  conditional correlations are slightly below visible-product correlations

random 80:
  conditional rank of the best 67.20-bit row:
    4 records: 28
    6 records: 32
    8 records: 8
    10 records: 10
    12 records: 13
    16 records: 18
    20 records: 21
```

The known successful `10^48` certificate is the sharpest sanity check.  Running
its curve through the patched SEA prefix stream gives full curve smoothness
`81.41` bits, but the visible prefix sees only:

```text
records 4,6,8:  4.17 bits
records 10:     7.54 bits
records 12:    12.90 bits
records 16:    18.78 bits
```

Inserted into the random 80-curve panel, the known winner ranks only around the
middle before ten records, then rises to rank 5 by 12 records and rank 2-3 by
16 records.  That is useful as an engineering screen, but it is already close
to full SEA at this size: the CRT product of the first 16 auxiliary primes is
about `64.82` bits, while full trace recovery needs 19 primes and `82.70` bits.
The winning factors are mostly late medium primes (`139`, `991`, `7573`,
`16759`, `25523`), so a prefix screen can observe part of the luck only after
doing much of the work.  It does not change the smooth-tail exponent.

A direct `known winner + random80` replay makes the retention boundary exact.
The conditional scorer, which accounts for residual smooth-tail probability
after the visible SEA prefix, ranks the winning curve as follows:

```text
prefix records:       4   6   8  10  12  16  20
conditional rank:    46  48  52  29   5   3   3
visible-score rank:  46  48  52  26   5   2   2
```

So the known `10^48` success would not survive a top-10 early screen until 12
SEA records.  Smooth-tail-aware conditioning does not rescue the early prefix;
it mostly reproduces the visible score, with correlations only around
`0.11-0.13` through 8 records and about `0.32` by 16 records.

A purpose-built `ellsea_prefix(E, maxell, maxbits)` should expose records like

```text
(ell, kind, modulus, trace_candidates, curve_divisible, twist_divisible)
```

after each SEA auxiliary prime, and return before the CRT product exceeds the
Hasse bound.  That is enough to score curve and twist smoothness directly,
including Atkin ambiguity, without solving Kummer division polynomials and
without forcing the full trace.

A better version is smoothness-aware early abort: after each SEA residue, keep
the set of possible traces in the Hasse interval and ask whether any compatible
order can still have a large enough `n^2`-smooth part.  If not, reject the curve
without completing the point count.  This can reduce the cost of random search,
but it should be treated as the engineering track because it leaves the
random-order tail unchanged.

`sea_prefix_rejection_feasibility.py` tests that early-abort idea on the
`known winner + random80` prefix artifact.  The current debug records do not
store full Atkin candidate trace sets, so this is a feasibility replay rather
than a correctness-safe oracle: it combines the exact CRT width from single
trace records with the same conditional smooth-tail model above, and asks how
many Hasse-compatible smooth witnesses should still remain.

```text
artifact: artifacts/sea_prefix_rejection_feasibility_known_plus_random80_10e48.json

prefix records:                    4      6      8     10     12     16     20
median single-trace CRT bits:    10.98  15.07  19.32  24.16  29.13  41.99  44.90
median compatible traces log10:  21.30  20.07  18.79  17.33  15.83  11.96  11.09
median expected witnesses log10: 16.11  14.84  13.79  12.16  10.55   6.80   5.74
minimum expected witnesses log10:13.31  10.93   8.23   6.71   3.49   1.54   0.70
rows below one expected witness:     0      0      0      0      0      0      0
```

That demotes correctness-safe prefix rejection with the current record stream:
even after all stored prefix records, the single-trace CRT leaves every sampled
row with more than one expected Hasse-compatible smooth witness, and the median
still has about `10^5.7`.  A real safe-abort implementation would need much
richer Atkin candidate data or many more SEA residues, which pushes it back
toward full point counting at `10^48`.

## Why this is likely better than pure CM scanning

The CM trace-first route is attractive because it chooses the trace before
constructing a curve.  However, the cheap small-discriminant version has weak
high-range evidence so far.

Measured with `cm_trace_sieve.py --max-discriminant 50000`:

```text
10^47 target: 15195 fundamental discriminants, 258 represented, 0 smooth-rich orders
10^60 target: 15195 fundamental discriminants,  78 represented, 0 smooth-rich orders
10^80 target: 15195 fundamental discriminants, 364 represented, 0 smooth-rich orders
```

Pushing the same easy-CM scan to `D <= 10^6` gives stronger negative evidence
and records the best sub-threshold rows:

```text
artifacts/cm_trace_sieve_10e48_D1e6_top20.json
10^48:
  fundamental discriminants checked = 303968
  represented traces/orders = 677 / 1354
  smooth-rich orders above threshold = 0
  best represented order = 65 smooth bits
  one-shot threshold = 79.73 bits

artifacts/cm_trace_sieve_10e80_D1e6_top20.json
10^80:
  fundamental discriminants checked = 303968
  represented traces/orders = 1628 / 3260
  smooth-rich orders above threshold = 0
  best represented order = 86 smooth bits
  one-shot threshold = 132.88 bits
```

So the easy-CM family is not just missing exact certificates; its best observed
smooth parts are still about `15` bits short at `10^48` and `47` bits short at
`10^80`.  The small-discriminant branch therefore remains a diagnostic and
low-range constructor, not the scaling method.

The existing `cm_search_oneshot.py` did find smooth-rich small-discriminant
traces for the `10^20 + 39` target, but most were unusable for Montgomery
certificates.  Odd traces are impossible for this certificate shape, and even
traces can still fail the Montgomery normalization when the rational 2-torsion
is not divisible in the required way.

This does not rule out CM.  It means the promising CM version would need a
stronger construction, such as searching traces with a prescribed smooth
divisor and controlled squarefree discriminant.  That becomes a different
Diophantine search, not just a larger `max_discriminant`.

### Partial-SEA implementation sketch

Add a new search driver around a partial SEA primitive:

```python
def small_order_divisors(A, p, B, bound):
    curve_part = 1
    twist_part = 1
    residues = []
    for ell in primes_up_to(B):
        if ell == p:
            continue
        trace_mod_ell = sea_trace_mod_ell(A, p, ell)
        residues.append((ell, trace_mod_ell))
        if (p + 1 - trace_mod_ell) % ell == 0:
            curve_part *= ell
        if (p + 1 + trace_mod_ell) % ell == 0:
            twist_part *= ell
        if curve_part > bound or twist_part > bound:
            return curve_part, twist_part, residues
    return curve_part, twist_part, residues
```

The first prototype can ignore Atkin primes and prime powers.  That only makes
the screen conservative: it may miss good curves, but any curve it accepts has
real small-prime divisibility evidence.  Once this works, add Atkin handling
and `l^e` lifting to recover the success probability lost by the conservative
prototype.

The extraction phase should remain unchanged initially:

1. A partial-SEA screen accepts `A`.
2. Call `ellcard` once for that accepted curve.
3. Reuse `sc_try_order` for the curve and twist.
4. Reuse `voneshot.verify` as the final authority.

That keeps correctness anchored in the current verifier while testing whether
the partial-SEA screen improves the time-to-candidate curve.

## Promising novelty track: direct torsion construction

A more radical approach is to construct a curve and point of smooth order
directly, rather than constructing the curve from a trace.  The certificate
only needs one point of known order above the one-shot lower bound, essentially
`sqrt(p)`; it does not need `#E(F_p)`.

The right mathematical object is a tower of modular curves

```text
X_1(mq) -> X_1(m)
```

for small primes `q <= n^2`.  Each lift corresponds to finding a `q`-division
preimage of the current marked point, thereby multiplying the certified point
order by `q`.  A practical search would:

- start from a low-level Montgomery or Tate normal form with a marked point;
- choose a smooth target `m` just above the one-shot lower bound;
- climb a tower of small-prime preimage equations, with backtracking when a
  chosen branch has no `F_p` lift;
- output the final Montgomery `A`, point `x0`, and constructed order `m`;
- rely on `voneshot.verify` as the final proof, so the construction need only
  be heuristic.

This is the first approach in the portfolio that changes both hard parts at
once: it avoids random smooth-order tails and avoids small-discriminant CM.
The risk is modular-curve complexity: expanded equations for `X_1(m)` are
hopeless when `m` is large.  The possible win is to keep the construction as a
tower of small-degree covers, solving only small `q`-division/preimage problems
at each step.  That is the next branch to prototype.

`two_power_lift.py` is the first such prototype for the 2-power tower.  It uses
the Montgomery x-only doubling formula

```text
x(2P) = (x^2 - 1)^2 / (4*x*(x^2 + A*x + 1))
```

and repeatedly solves the halving quartic over `F_p`.

Results:

```text
p=101:
  found verified certificate 101 62 26 32.

10^8 target:
  found verified certificate
  100000007 9025243 90888275 131072
  after 4656 initial order-8 states.

10^20 + 39 target:
  5000 initial order-8 states reached only 2^14;
  the required Pomerance order is 2^34.
```

This shows the direct torsion equations are correct and can construct
certificates, but the naive local lift samples the thin set below
`X_1(2^k)` too blindly.  This matches the external
[Pomerance-triple challenge][danger3] data: the `10^20 + 39` Pomerance triple
required about `1.2e9` candidates, and the `10^21 + 117` triple about `5.3e10`
candidates in an optimized low-level search.  In other words, plain 2-power
construction is the known grinding track, not yet the asymptotic escape.

The next direct-torsion idea should be meet-in-the-middle on the tower:

- represent a length-`a` lower tower from the order-4 point as compact states
  `(A, x_mid)` or as hashes of the induced rational constraints;
- represent a length-`b` upper tower by reverse halving constraints;
- match at the midpoint so the cost behaves like roughly `2^(k/2)` tower
  states instead of `2^k` candidates;
- keep the final verifier unchanged.

If this can be made algebraic without materializing huge modular-curve
polynomials, it is the first path with a plausible asymptotic improvement over
the existing Pomerance search while still producing the same tiny certificate.

`mixed_prime_lift.py` tests the same direct-torsion idea with several small
prime covers.  It supports `q=2` and odd primes up to a conservative prototype
bound; `q=2` uses the halving quartic, while odd `q` uses the x-only Montgomery
ladder equation `x([q]R)=x(P)`.

Results:

```text
p=101, q in {2,3,5}:
  found verified certificate 101 38 6 108.

10^8 target, q in {2,3}:
  found verified certificate
  100000007 60592281 37641787 18432
  after 141 random curves.

10^8 target, q in {2,3,5}:
  found verified certificate
  100000007 80784765 4993461 50000000
  after 182 random curves.

10^12 target, q in {2,3,5}:
  300 random curves reached only order 5184, below the 1002001 bound.

10^20 + 39 target, q in {2,3,5}:
  200 random curves reached only order 9720, far below the 10000200001 bound.
```

This is the strongest positive signal so far for the generalized one-shot
setting: mixed small-prime torsion can produce much larger orders than a pure
2-power tower at small sizes.  But it also shows that random curve starts still
inherit a severe tail at larger sizes.  The next version should not sample `A`
uniformly; it should search over smooth target words such as

```text
2^a * 3^b * 5^c * ...
```

and use dynamic programming/meet-in-the-middle on compact tower states
`(A, x, m)` to bias the construction toward order growth.  In practical terms,
the branch to pursue is a **multi-prime torsion tower search** with:

- a priority queue scored by `log(m)` per root-solving cost;
- cached q-division polynomials for small `q`;
- beam search across both curve parameter `A` and marked point `x`;
- occasional exact `voneshot.verify` checks once `m` crosses the bound.

`word_guided_lift.py` adds the first bit of targeting.  It chooses the first
lift prime `q`, samples a preimage coordinate `x`, and solves

```text
x([q]R) = 1
```

for the Montgomery parameter `A`; after that it either follows a fixed word or
runs a free beam search over small primes.

Results:

```text
p=101, word=3,3,3:
  found verified certificate 101 39 37 108.

10^8 target, word=5 then free {2,3,5} tail:
  found verified certificate
  100000007 88816434 41019708 45000
  after 158 first-lift states.

10^10 target, word=5 then free {2,3,5} tail:
  found verified certificate
  10000000019 7650937785 7223815917 1687500
  after 312 first-lift states.

10^12 target, word=5 then free {2,3,5} tail:
  514 first-lift states reached order 162000, below the 1002001 bound.

10^20 + 39 target, word=5 then free {2,3,5} tail:
  276 first-lift states reached order 23040, far below the 10000200001 bound.
```

This is a real improvement over uniform random `A`: the guided first lift
extends the verified range of the direct-torsion prototype to `10^10`, and it
improves the `10^12` best order from `5184` to `162000` in comparable small
experiments.  The remaining bottleneck is tail selection.  A scalable version
should prioritize states by observed lift availability and target order growth,
not just keep the largest current `m`.

An explicit one-step lookahead scorer was also tested in `word_guided_lift.py`.
It ranks free-tail states by current `log2(m)` plus a bonus for valid next
lifts.  The result is mixed:

```text
10^8 target, lookahead tail:
  found verified certificate
  100000007 51259818 52789802 13500
  after 43 first-lift states.

10^10 target, order-ranked tail:
  found verified certificate
  10000000019 6036997842 7053962278 103680
  after 60 first-lift states, about 4.3s.

10^10 target, lookahead tail:
  found verified certificate
  10000000019 2814286688 4907837002 172800
  after 216 first-lift states, about 37.8s.

10^12 target, lookahead tail:
  stopped after 250 first-lift states with best order 9600,
  worse than the order-ranked best of 162000.
```

So liftability matters, but exact one-step lookahead is too expensive and too
noisy.  The next refinement should cache q-preimage availability and use a
cheap structural score, rather than recomputing exact future lifts for every
candidate state.

`word_guided_lift.py` now has that first cached scorer.  It reuses child
expansions while ranking candidates by current order plus one-step lift
availability.  Results with first lift `5` and free tail `{2,3,5}`:

```text
10^8 target, cached lookahead:
  found verified certificate
  100000007 1434612 91580792 77760
  after 45 first-lift states.
  cache: root_hits=0/10680, child_hits=4407/7967.

10^10 target, cached lookahead:
  found verified certificate
  10000000019 7154753448 2727166052 39062500
  after 21 first-lift states.
  cache: root_hits=0/7743, child_hits=1732/4313.

10^12 target, cached lookahead:
  532 first-lift states reached order 512000,
  below the 1002001 bound.
  cache: root_hits=0/73542, child_hits=35793/60307.
```

The cache result is informative.  Repeated exact root solves are not the main
reuse opportunity (`root_hits=0` in these runs), but child expansion decisions
repeat often enough to cut scoring cost.  That means ordinary memoization is a
useful instrument, not the mathematical escape hatch.

The more interesting result came from opening the tower to `q=7`.  Using `7` as
the first guided lift was not good:

```text
10^8 target, first lift 7, tail {3,5,7}:
  found verified certificate
  100000007 68672321 57596856 26460
  after 17 first-lift states.

10^10 target, first lift 7, tail {3,5,7}:
  160 first-lift states reached only order 37044,
  below the 100633 bound.
```

But using `7` opportunistically in the tail after a first lift by `5` was much
better:

```text
10^10 target, first lift 5, tail {2,3,5,7}:
  found verified certificate
  10000000019 8997773839 4878957936 1984500
  after 190 first-lift states.

10^12 target, first lift 5, tail {2,3,5,7}:
  found verified certificate
  1000000000039 185004666010 584281974706 1296540
  after 36 first-lift states.

10^14 target, first lift 5, tail {2,3,5,7}:
  interrupted after 300 first-lift states at best order 1134000,
  below the 10006325 bound.
```

This is the strongest evidence so far for the "many ways to win" view.  Higher
prime covers are not uniformly better, but they can be valuable when admitted
as optional branches.  The next novelty branch should therefore not optimize a
single fixed word.  It should treat the tower as an adaptive search problem:

- choose the next prime by predicted liftability, not by a static order;
- estimate each state's local lift distribution before exact root solving;
- keep a portfolio of target words so an expensive `q=7` or `q=11` step is used
  only when the local tree makes it unusually cheap;
- use the SEA interpretation as a guide: forcing trace eigenvalue `1` modulo
  small primes is exactly the rational-torsion condition, so this direct tower
  is the non-black-box version of a smoothness-aware SEA search.

### Guidance from the Danger2026 research corpus

The external [Danger2026 research notes][danger2026-research] sharpen the
boundary between practical speedups and actual scaling improvements.

For p23, the ["true sub-sqrt scaling frontier"][danger2026-p23-frontier]
states the key criterion:
fixed prescribed torsion levels give useful constant factors, while true
scaling requires growing torsion or trace information that can be extracted
for less than its generic modular-curve cost.  It also records the generic
barrier:

```text
density gain from X_1(N) prescribed torsion ~= N
generic X_1(N) fiber/gonality burden ~= N^2
```

That matches the local experiments here: sampling more preimages is not enough
unless the tower has special structure.

`torsion_tower_cost_model.py` quantifies the same point for the Montgomery
selected-component forcing surface.  For an odd prime `q`, solving
`Z_q(A,x)=0` for `A` at fixed `x` has degree `(q^2 - 1)/4`; independent
squarefree torsion-point conditions therefore build a fiber product whose
generic degree grows like `M^2`, while the density gain is only `M`.

At `10^48`, using the consecutive odd primes until the forced product crosses
the one-shot threshold gives:

```text
forced squarefree M bits = 81.70
generic fiber-product degree bits = 127.10
degree minus density gain = 45.40 bits
```

At `10^80` the gap is worse:

```text
forced squarefree M bits = 133.14
generic fiber-product degree bits = 213.98
degree minus density gain = 80.84 bits
```

So the "many independent chosen torsion witnesses sharing the same A" idea is
not a hidden shortcut; generically it is just `X_1(M)` in fiber-product
clothing.

The mixed-prime predictor below exposes a second squarefree regime that is not
captured by the raw `X_1` point model.  After a guided first lift, an odd
mixed-prime gate `q != q0` does not need a chosen q-torsion point; it only needs
the selected component to have a rational q-torsion line with Frobenius
eigenvalue `1`.  Modeling that as a line/eigenvalue condition of degree about
`q+1`, rather than a point condition of degree about `q^2`, gives:

```text
10^48:
  forced squarefree M bits = 81.70
  line/eigenvalue degree bits = 83.35
  degree minus density gain = 1.65 bits

10^80:
  forced squarefree M bits = 133.14
  line/eigenvalue degree bits = 134.92
  degree minus density gain = 1.78 bits
```

This is the first squarefree route whose coarse degree model is not immediately
worse than random smooth-tail search.  The hard part shifts from finding more
preimage roots to finding a sourceable line/eigenvalue modular coordinate for
many q at once.

`line_forcing_tradeoff.py` checks the obvious generic strategy:

```text
force a fixed squarefree line/eigenvalue product M,
then rely on the remaining random smooth tail.
```

This does not beat random search, because it loses the entropy from all the
other ways a smooth tail can occur:

```text
artifacts/line_forcing_tradeoff_10e48.json
random expected work log10 = 5.316
best forced-prefix strategy:
  force q=3 only
  expected work log10 = 5.869
  overhead vs random = 0.553

artifacts/line_forcing_tradeoff_10e80.json
random expected work log10 = 9.227
best forced-prefix strategy:
  force q=3 only
  expected work log10 = 9.779
  overhead vs random = 0.552
```

Representative one-prime checks at `10^48` make the same point: forcing `31`
is `1.11` log10 worse than random, forcing `991` is `2.17` log10 worse, and
forcing `25523` is `3.21` log10 worse.  Thus generic line-product forcing is
not the method.  The useful possibility is narrower: find a special
low-genus/recurrence/divisor-class source that couples many line conditions
without paying for a fixed product one prime at a time.

A corrected conditioned-tail variant keeps forced primes available for natural
higher q-adic valuation after the first forced hit.  This helps only slightly:

```text
artifact: artifacts/line_forcing_tradeoff_10e48_conditioned_geometric.json
random expected work log10 = 5.316
best forced-prefix strategy:
  force q=3 only
  expected work log10 = 5.783
  overhead vs random = 0.467
```

The conclusion is unchanged.  Medium and large one-prime line gates are still
worse than random at `10^48`: forcing `31` is `1.09` log10 worse, forcing `991`
is `2.17` log10 worse, and forcing `25523` is `3.21` log10 worse even under
the conditioned-tail model.

`source_break_even_model.py` makes the missing source requirement explicit.
Because the smooth-tail event has many ways to occur, forcing one fixed
residue product `M` only improves the residual tail like roughly `M^theta`, not
like `M`.  Therefore a sourceable family that imposes those residues must cost
less than `M^theta` to beat random search.  A merely density-neutral `X_0` or
line/eigenvalue source is still too expensive.

```text
artifact: artifacts/source_break_even_10e48.json
maximum break-even alpha ~= 0.284
generic line/eigenvalue alpha ~= 1.02-1.26
generic X_1 point alpha eventually ~= 1.55

artifact: artifacts/source_break_even_10e80.json
maximum break-even alpha ~= 0.306
generic line/eigenvalue alpha ~= 1.01-1.26
generic X_1 point alpha eventually ~= 1.61
```

Those artifacts are one-sided smooth-tail baselines.  The actual `oneshot.gp`
search pays for one SEA count and then tests both the curve order and the twist
order.  `two_sided_tail_baseline.py` models this paired Hasse trace
`p+1 +/- t`:

```text
artifact: artifacts/two_sided_tail_baseline_10e48_s200000_10e80_20260811.json

10^48 model:
  one-sided expected work = 10^5.316
  curve/twist union expected work ~= 10^5.015

10^48 sample, 200k random traces:
  curve hits = 1
  twist hits = 3
  either-side hits = 4
  both-side hits = 0
  smooth-bit correlation ~= 0.020

10^80 model:
  one-sided expected work = 10^9.227
  curve/twist union expected work ~= 10^8.926
```

Using the two-sided baseline makes the source budget stricter by one bit:

```text
artifact: artifacts/source_break_even_10e48_two_sided.json
maximum break-even alpha ~= 0.239

artifact: artifacts/source_break_even_10e80_two_sided.json
maximum break-even alpha ~= 0.263
```

Here `alpha` means source cost about `M^alpha` for forced residue product `M`.
At `10^80`, forcing enough consecutive odd primes to cross the one-shot bound
uses about `133` forced bits, but the entire random smooth-tail work budget is
only about `29.65` bits against the two-sided baseline.  So a scalable residue
source must be genuinely sub-density, not just an optimized implementation of
the generic modular surface.

The most natural normalized source is trace-CRT selection: force

```text
t ==  p + 1 (mod M)   or   t == -p - 1 (mod M)
```

so that the curve or twist component order is divisible by `M`, then use the
remaining Hasse-interval freedom to choose a trace with small CM
discriminant.  `trace_crt_break_even_model.py` compares that idea to the
same smooth-tail break-even budget.

The entropy is unforgiving.  Among traces in one residue class, the expected
number whose fundamental discriminant has `|D| <= Dmax` is about
`4*sqrt(Dmax)/M`; allowing both curve/twist signs only doubles this.  Since
class construction has scale about `sqrt(D)`, expecting even one constructible
trace needs class-number scale about `log2(M)-3` bits, while the smooth-tail
budget saved by forcing `M` is much smaller.

```text
artifact: artifacts/trace_crt_break_even_10e48.json
crossing prefix through q=67:
  forced residue bits = 81.70
  smooth-tail break-even source budget = 17.66 bits
  class scale needed for one compatible trace ~= 78.70 bits
  expected compatible traces at the break-even budget = 2^-61.04

artifact: artifacts/trace_crt_break_even_10e80.json
crossing prefix through q=101:
  forced residue bits = 133.14
  smooth-tail break-even source budget = 30.65 bits
  class scale needed for one compatible trace ~= 130.14 bits
  expected compatible traces at the break-even budget = 2^-99.49
```

So trace-CRT residue selection does not evade the CM barrier.  It is exactly
the right quotient-level formulation of the mixed-prime gates, but it still
requires a large-discriminant isogeny-class constructor far below class-number
cost.  Without that extra primitive, the Hasse-trace freedom is too small to
turn residue forcing into a scalable source.

`trace_square_entropy_model.py` adds the other trace-first lever: force square
factors in `4p - t^2` so the fundamental CM discriminant is smaller.  For an
odd square-root conductor `f` made from `k` primes, the square congruences give
about `2^k` trace branches modulo `f^2`, but cost `f^2` in trace density.  The
expected number of traces satisfying the order residue, the square congruences,
and a class scale `C` is roughly

```text
2^(sign_entropy + k + C - log2(M) - log2(f)).
```

So the class scale needed to expect one compatible trace is

```text
C ~= log2(M) + log2(f) - k - sign_entropy.
```

Each odd square-prime `q` therefore changes the required class scale by
`log2(q) - 1` bits.  Square-sieving lowers the discriminant of a particular
surviving trace, but it makes such traces rarer faster than it lowers the
expected construction scale.

```text
artifact: artifacts/trace_square_entropy_10e48_v2.json

order-residue crossing:
  forced_bits = 81.700
  break-even source budget = 17.660 bits

k=0 square primes:
  required class scale = 78.700 bits
  class-scale gap = 61.041 bits

k=1 square prime:
  square-root bits = 6.150
  branch bits = 1.000
  required class scale = 83.850 bits
  class-scale gap = 66.190 bits

artifact: artifacts/trace_square_entropy_10e80_v2.json

order-residue crossing:
  forced_bits = 133.139
  break-even source budget = 30.650 bits

k=0 square primes:
  required class scale = 130.139 bits
  class-scale gap = 99.489 bits

k=1 square prime:
  square-root bits = 6.768
  branch bits = 1.000
  required class scale = 135.907 bits
  class-scale gap = 105.257 bits
```

This explains the square-sieve experiments: they are useful for finding small
guard examples and for verifying the CM obstruction, but square forcing is not
the missing source.  It spends trace entropy at a net loss of about
`log2(q)-1` class-scale bits per odd square prime.  A scalable trace-first
method would need a genuinely different large-discriminant class constructor,
not just more conductor CRT conditions.

`line_hit_correlation.py` then asks whether the ordinary guided first-lift
surface already supplies such coupling.  It samples first-lift states at
`10^48`, computes the mixed-prime line hits up to `31`, and compares the best
observed line product with an independent Monte Carlo model using the same
per-prime hit rates.

```text
artifact: artifacts/line_hit_correlation_10e48_q0_3_s100_q31.json
q0=3, 96 states, q in {5,7,11,13,17,19,23,29,31}
  best observed line product = 11.85 bits
  independent median = 12.84 bits
  independent p95 = 17.17 bits
  observed percentile = 0.286

artifact: artifacts/line_hit_correlation_10e48_q0_11_s100_q31.json
q0=11, 99 states, q in {3,5,7,13,17,19,23,29,31}
  best observed line product = 11.06 bits
  independent median = 12.62 bits
  independent p95 = 16.65 bits
  observed percentile = 0.235

artifact: artifacts/line_hit_correlation_10e48_q0_5_s100_q31.json
q0=5, 95 states, q in {3,7,11,13,17,19,23,29,31}
  best observed line product = 12.10 bits
  independent median = 12.71 bits
  independent p95 = 16.87 bits
  independent p99 = 18.73 bits
  observed percentile = 0.416
```

So the naive first-lift surface does not itself create a helpful high-tail
correlation among mixed q-line conditions.  This demotes "sample first-lift A
then score many line hits" as a scaling method.  A successful version must
actively construct or exploit a coupled source; it cannot rely on accidental
correlation in the guided first-lift distribution.

A widened `q0=5` run through gate primes up to `43` gave a high but still
ordinary sample:

```text
artifact: artifacts/line_hit_correlation_10e48_q0_5_s140_q43.json
q0=5, 136 states, q in {3,7,11,13,17,19,23,29,31,37,41,43}
  best observed line product = 20.42 bits
  independent median = 15.83 bits
  independent p95 = 20.78 bits
  independent p99 = 23.16 bits
  observed percentile = 0.941
```

This is not a knockout negative result for every possible normalized cover, but
it is not the kind of extreme outlier a sourceable coupling should produce.

There is one useful constant-factor variant of the same idea.  Instead of
forcing a fixed line product, use a menu prefilter: compute several cheap
selected-component q-line gates, keep rows whose observed hit product is above
a threshold, and call full SEA only on that accepted band.  This keeps the
"many ways to win" entropy that fixed-M forcing loses.

`line_prefilter_economics.py` models that strategy from the observed
`line_hit_correlation.py` artifacts.  It uses the measured q-oracle time per
candidate, assumes a 2.6s full-SEA cost at `10^48`, and estimates the residual
smooth tail from each row's observed hit product.

```text
artifact: artifacts/line_prefilter_economics_10e48.json

q0=3, q<=31:
  best threshold = 3.46 product bits
  accepted = 37/96
  average accepted product = 6.17 bits
  modeled speedup vs random full SEA = 0.288 log10 ~= 1.94x

q0=5, q<=31:
  best threshold = 3.46 product bits
  accepted = 37/95
  average accepted product = 5.98 bits
  modeled speedup vs random full SEA = 0.278 log10 ~= 1.90x

q0=11, q<=31:
  best threshold = 3.70 product bits
  accepted = 44/99
  average accepted product = 5.90 bits
  modeled speedup vs random full SEA = 0.300 log10 ~= 2.00x

q0=5, q<=43:
  best threshold = 2.81 product bits
  accepted = 80/136
  average accepted product = 6.26 bits
  modeled speedup vs random full SEA = 0.208 log10 ~= 1.61x
```

The broader menu is therefore a legitimate engineering support layer: it can
cut full-SEA work by about a factor of two at this size.  But the optimum
threshold is deliberately broad, accepting roughly 40-60% of candidates, and
the gain stays in constant-factor territory.  It does not supply the missing
sub-density source for many trace residues.

The same model shows why q-primary structure is special.  To reach the
`10^48` bound using one prime alone would require approximately:

```text
q=2: 78 extra levels
q=3: 49 extra levels
q=5: 33 extra levels
q=7: 27 extra levels
```

Generic `q^2` branching would cost about twice the target bitlength in each
case, but a Smith-line oracle would cost roughly the target bitlength.  Thus
there are now two plausible non-black-box surfaces: mixed squarefree
line/eigenvalue products, and same-prime q-primary Smith lines.  Both require
normalized Frobenius/Kummer data rather than raw division-polynomial branching.

The [p25 practical-search lane][danger2026-p25-practical] and
[p26 GPU report][danger2026-p26-gpu] show that the fixed `X_1(16)`
nonsplit/halving route is an excellent practical search surface.  It solved
`10^25 + 13` after about `4.63e11` accepted-trial accounting and solved
`10^26 + 67` on GPU after about `1.40e11` `X_1(16)` curves.  But the p26
report is explicit that this is a fixed-prime practical result, not an
asymptotic shortcut.

The [p27 frontier][danger2026-p27-frontier] is the most relevant source for a
mathematical route.  It identifies the selected halving tower obstruction as
the sequence

```text
d_j = x_j^2 + A*x_j + 1
chi(d_j) = chi(x_j)
```

on nonsplit Montgomery rows.  Equivalently, after a successful halving step
with `x' + 1/x' = u`, the next gate is

```text
chi(x') = chi(u + 2) = chi(u - 2).
```

Fixed prefix tests of these characters are constant-factor filters; the p27
recurrence and GPU precheck probes show they do not beat square-root scaling
when tested independently.  The p27 "D_plus" trace/norm stratum is likewise an
exact two-gate prefix, not a late-depth law by itself.  The surviving p27
moonshot is more precise: extract the normalized
[A-line/Kummer/divisor classes][danger2026-p27-a-level] for the later selected
gates and find a recurrence, coboundary, low-genus source, or Prym/theta
relation coupling many gates at once.

This changes the interpretation of the adaptive mixed-prime scheduler.  It is
a diagnostic, not the method.  A first adaptive version in `word_guided_lift.py`
probes individual `(state, q)` pairs and records per-prime yield:

```text
10^12 target, first lift 5, adaptive tail {2,3,5,7}:
  218 first-lift states reached only order 52500,
  below the 1002001 bound.
  q2:p7555/h2607/v6396/2.191s
  q3:p7464/h1075/v4029/4.527s
  q5:p6940/h517/v2585/12.906s
  q7:p3426/h210/v1290/9.755s

10^14 target, first lift 5, adaptive tail {2,3,5,7}:
  269 first-lift states reached only order 126000,
  below the 10006325 bound.
  q2:p8788/h3586/v8306/3.493s
  q3:p8737/h1816/v4333/5.067s
  q5:p7208/h405/v2025/14.224s
  q7:p5192/h252/v1542/16.621s

10^10 target, risk-seeking adaptive tail {2,3,5,7,11}:
  found verified certificate
  10000000019 1267012399 8863864806 220500
  after 8 first-lift states.
  q11:p382/h0/v0/3.813s
```

The adaptive rule is too myopic: it mostly rediscovers cheap local liftability,
while the rare high-order branches that matter are not predicted before
root-solving.  The `q=11` probe is also a useful warning: larger covers can be
pure cost with no valid children in small samples.

The next mathematical method should therefore be:

1. Treat each successful lift gate as a Kummer character, not merely as a root
   search.
2. Build finite-field fixtures for the post-first-lift states grouped by a
   low-dimensional invariant such as `A`, a Kummer-line coordinate, or a
   quotient analogous to the p27 A/B/K coordinates.
3. Test whether successive liftability bits descend to whole fibers and
   whether their branch classes are related by pullback, translate, coboundary,
   or recurrence.
4. Promote only a sourceable class relation that controls many gates at once;
   demote fixed-prefix filters, adaptive per-prime bandits, and visible
   low-degree character scans when they show independent half-loss.

This is still "dig into SEA" in the relevant sense: the direct-torsion tower is
the certificate-side version of forcing Frobenius eigenvalue `1` modulo small
primes.  The promising non-black-box problem is to find the hidden Kummer/class
relations among those local conditions, not to compute more SEA residues or
more division-polynomial roots independently.

### First class-descent probe for the mixed-prime tower

`lift_class_probe.py` is the first diagnostic aimed at that Kummer/class
problem.  It enumerates or samples the guided first-lift surface

```text
x([q0]R) = 1
```

and then tests later liftability bits using the same exact-order checks as the
certificate prototypes.  For each next prime `q`, it records whether the bit is
constant on fibers of the Montgomery parameter `A`, and whether the bit is a
visible low-degree character `chi(f(A))`.

For first lift `q0=5`, small-field enumeration gives a strong descent signal:

```text
F_607, full first-lift enumeration:
  q=2: A_groups=156, A_mixed=0, valid_rate=0.384615
  q=3: A_groups=156, A_mixed=0, valid_rate=0.423077
  q=5: A_groups=156, A_mixed=0, valid_rate=0.423077
  q=7: A_groups=156, A_mixed=0, valid_rate=0.057692
  no monic degree <= 2 A-polynomial character hits.

F_863, full first-lift enumeration:
  q=2: A_groups=213, A_mixed=0, valid_rate=0.319249
  q=3: A_groups=213, A_mixed=0, valid_rate=0.563380
  q=5: A_groups=213, A_mixed=0, valid_rate=0.126761
  q=7: A_groups=213, A_mixed=0, valid_rate=0.436620
  no monic degree <= 2 A-polynomial character hits.

F_991, full first-lift enumeration:
  q=2: A_groups=186, A_mixed=0, valid_rate=0.390244
  q=3: A_groups=186, A_mixed=0, valid_rate=0.268293
  q=5: A_groups=186, A_mixed=12, valid_rate=0.243902
  q=7: A_groups=186, A_mixed=0, valid_rate=0.048780
  no monic degree <= 2 A-polynomial character hits.

F_1231, full first-lift enumeration:
  q=2: A_groups=247, A_mixed=0, valid_rate=0.416667
  q=3: A_groups=247, A_mixed=0, valid_rate=0.480769
  q=5: A_groups=247, A_mixed=0, valid_rate=0.173077
  q=7: A_groups=247, A_mixed=0, valid_rate=0.096154
  no monic degree <= 1 A-polynomial character hits.

10^12 target sample, 234 first-lift states:
  q=2: valid_rate=0.410256
  q=3: valid_rate=0.388889
  q=5: valid_rate=0.213675
  q=7: valid_rate=0.179487
  duplicate A fibers are essentially absent, so this checks rate sanity rather
  than descent.
```

The key positive result is not the valid rate.  It is that most tested
liftability bits are constant on `A` fibers even though each `A` has multiple
first-lift points above it.  This is analogous to the p27 discovery that later
selected halving gates descend to A-line/Kummer classes.  It suggests the
mixed-prime tower has a smaller class surface than the raw `(A,x)` preimage
tree.

The key negative result is equally important: the descended bits are not
explained by cheap visible low-degree characters of `A`.  Also, the `F_991`
`q=5` bit has mixed `A` fibers, so the correct invariant is not always bare
`A`; the normalized class may require a cover coordinate, orientation, or a
quotient coordinate analogous to the p27 B/K/A-line bridge.

Adding quotient summaries makes the class target sharper.  The Montgomery
`j`-invariant depends on `A^2`, so testing both `{A,-A}` and `j(A)` asks
whether the bit lives on the signed `A` cover or descends to the twist quotient.
For the `q0=5` first-lift fixtures:

```text
F_607:
  q=2: A_mixed=0, j_mixed=19
  q=3: A_mixed=0, j_mixed=0
  q=5: A_mixed=0, j_mixed=0
  q=7: A_mixed=0, j_mixed=0

F_863:
  q=2: A_mixed=0, j_mixed=16
  q=3: A_mixed=0, j_mixed=0
  q=5: A_mixed=0, j_mixed=0
  q=7: A_mixed=0, j_mixed=0

F_991:
  q=2: A_mixed=0,  j_mixed=28
  q=3: A_mixed=0,  j_mixed=0
  q=5: A_mixed=12, j_mixed=8
  q=7: A_mixed=0,  j_mixed=0

F_1231:
  q=2: A_mixed=0, j_mixed=32
  q=3: A_mixed=0, j_mixed=0
  q=5: A_mixed=0, j_mixed=0
  q=7: A_mixed=0, j_mixed=0
```

This says the `q=2` gate is naturally a signed-`A` class, not a `j`-class,
while the odd gates often descend to the twist quotient.  The `F_991, q=5`
exception is also structured: every mixed `A` fiber has 24 first-lift rows
with a 20/4 split.  That is consistent with a same-prime tower coordinate
inside the 5-division fiber, rather than random row noise.

The low-degree visibility test was then extended from bare `A` to all three
obvious quotient coordinates: `A`, `{A,-A}`, and `j(A)`.  For first lift
`q0=5`, the two gates that cleanly descend to `j` in every guard field still
have no monic degree <= 2 quadratic-character representation on any of those
coordinates:

```text
Command shape:
  python3 lift_class_probe.py --prime p --first-prime 5 --enumerate \
    --samples N --gate-primes 3,7 --poly-degree 2 \
    --poly-variables A,pmA,j

F_607:
  q=3: A/pmA/j scanned 369056 each, hits none
  q=7: A/pmA/j scanned 369056 each, hits none

F_863:
  q=3: A/pmA/j scanned 745632 each, hits none
  q=7: A/pmA/j scanned 745632 each, hits none

F_991:
  q=3: A/pmA/j scanned 983072 each, hits none
  q=7: A/pmA/j scanned 983072 each, hits none

F_1231:
  q=3: A/pmA/j scanned 1516592 each, hits none
  q=7: A/pmA/j scanned 1516592 each, hits none
```

This rules out the easiest version of the quotient idea: the descended odd
gate bits are not simply `chi(f(A))`, `chi(f({A,-A}))`, or `chi(f(j))` for a
monic polynomial `f` of degree at most 2.  The result is negative but useful:
the class is visible as a quotient-level bit, yet not as an obvious low-degree
branch divisor in the standard coordinates.  That is exactly the regime where
the p27-style Kummer extraction, divisor normalization, or cover-coordinate
search is the right next experiment.

Extending the immediate-gate probe to `q=11` and `q=13` shows the same pattern
beyond the tiny primes.  In small guard fields with first lift `q0=5`, every
nontrivial `q=11`/`q=13` gate tested is constant on `A` fibers and on the
`j(A)` quotient, while degree-2 visible character scans still find no
nontrivial formula.  All-negative gates produce trivial polynomial "hits" and
are ignored as class evidence.

```text
artifacts/lift_class_q607_q0_5_q3_q7_q11_q13.json
  q=11: valid_rate=0.0000, A_mixed=0, j_mixed=0  (all-negative)
  q=13: valid_rate=0.0000, A_mixed=0, j_mixed=0  (all-negative)

artifacts/lift_class_q863_q0_5_q3_q7_q11_q13.json
  q=11: valid_rate=0.2254, A_mixed=0, j_mixed=0, degree<=2 hits none

artifacts/lift_class_q991_q0_5_q3_q7_q11_q13.json
  q=13: valid_rate=0.1220, A_mixed=0, j_mixed=0, degree<=2 hits none

artifacts/lift_class_q1231_q0_5_q3_q7_q11_q13.json
  q=13: valid_rate=0.0385, A_mixed=0, j_mixed=0, degree<=2 hits none
```

On the actual `10^48` target, a 254-state first-lift sample gives nontrivial
immediate rates for these larger gates:

```text
artifact: artifacts/lift_class_10e48_q0_5_q3_q7_q11_q13_s260.json
q=3:  valid_rate=0.5394
q=7:  valid_rate=0.1417
q=11: valid_rate=0.0866
q=13: valid_rate=0.0669
```

This is the useful positive signal for the direct-torsion branch: medium gates
are not too rare to matter, and the finite-field fixtures say they live on a
small quotient surface.  The negative signal is just as sharp: paying for each
gate as an independent root search still loses, so the only promotable version
is a normalized class/correspondence that sources several of these quotient
bits together.

`gate_coupling_summary.py` then checks the next required property: do the
descended quotient bits actually cluster, or are they fresh independent gates?
The small-field packet with degree-2 product scans is:

```text
artifacts/class_packet_q0_5_q3_q7_q11_q13_rel_degree2.json
artifacts/gate_coupling_q0_5_q3_q7_q11_q13_smallfields.json
```

It finds no stable nontrivial degree-2 product character.  Some guard fields
show strong special behavior, but it is not stable: for example `F_863` has
positive `q=3`/`q=7` clustering, while other fields have disjoint or
all-negative medium gates.

A larger `10^48` sample makes the practical read clearer:

```text
artifact: artifacts/lift_class_10e48_q0_5_q3_q7_q11_q13_s900.json
initial states = 934
q=3:  valid_rate=0.5107
q=7:  valid_rate=0.1777
q=11: valid_rate=0.0910
q=13: valid_rate=0.0814

artifact: artifacts/gate_coupling_10e48_q0_5_q3_q7_q11_q13_s900.json
q=3 x q=7:   ++ = 82, expected = 84.78, enrichment = 0.97, phi = -0.016
q=3 x q=11:  ++ = 54, expected = 43.41, enrichment = 1.24, phi =  0.079
q=7 x q=11:  ++ = 18, expected = 15.11, enrichment = 1.19, phi =  0.028
q=11 x q=13: ++ = 11, expected =  6.92, enrichment = 1.59, phi =  0.056
```

The `q=11`/`q=13` pair has a small positive bias, but the mutual information is
only about `0.002` bits.  This is far below the kind of reusable relation that
would change scaling.  The immediate quotient classes are therefore good
coordinates for a future Kummer/divisor-class extraction, but ordinary pairwise
clustering of those classes is not the method.

`exact_gate_vector_field.py` removes the first-lift sampling layer entirely on
small guard fields.  It enumerates every nonsingular Montgomery parameter `A`,
computes the selected curve/twist component order, records the complete
selected-component gate vector, and compares the best observed product with two
null models:

- independent Bernoulli gates with the same marginal rates;
- random integers in the same Hasse/order interval, which is the correct null
  for tiny guard fields where some CRT products are impossible because the
  order interval is too short.

```text
artifact: artifacts/exact_gate_vector_p10007_q3_11_interval.json

p = 10007
gates = 3,5,7,11
states = 10005
best observed product = 231 = 3*7*11 = 7.852 bits
random-order interval median/p95/p99 = 8.589 / 8.589 / 8.589 bits
observed interval percentile = 0.0000

largest pairwise mutual information:
  q=7 x q=11: mi_bits = 0.00139, enrichment = 1.299, phi = 0.045
```

```text
artifact: artifacts/exact_gate_vector_p5003_q3_11_interval.json

p = 5003
gates = 3,5,7,11
states = 5001
best observed product = 105 = 3*5*7 = 6.714 bits
random-order interval median/p95/p99 = 8.589 / 8.589 / 8.589 bits
observed interval percentile = 0.0000

largest positive pairwise bias:
  q=7 x q=11: mi_bits = 0.00585, enrichment = 1.648, phi = 0.096
```

These exact quotient-family checks show no hidden high-product tail.  Some
pairwise biases exist in small fields, but they are tiny in information terms
and do not lift the multi-gate product above a random-order Hasse-interval
baseline.  This strengthens the negative conclusion: the raw Montgomery
selected-component trace family does not visibly couple the residue gates we
need.  A successful source has to be a new normalized cover/class construction,
not merely "use the whole A-family more exactly."

`exact_gate_recurrence_screen.py` tests the first theorem-shaped recurrence
family on the same all-A artifacts.  It asks whether selected gate classes are
related by

```text
gate_q2(phi(A)) = +/- gate_q1(A)
```

where `phi` is a Dickson/Chebyshev self-map of the A-line branch set
`{-2,2,infinity}`, conjugated on both sides by the six S3 branch symmetries.
This is the local analogue of the p27 A/B-line recurrence screens.

```text
artifact: artifacts/exact_gate_recurrence_DicksonS3_p5003_p10007_q3_11_degree12_top80.json

p=5003, gates={3,5,7,11}, maps tested=432:
  exact nontrivial high-coverage relations = 30
  all exact relations are q=3 -> q=3, degree=1 S3 symmetries
  no exact cross-prime relation and no exact degree>1 Dickson relation
  best non-exact high-coverage row:
    q=11 -> q=11, degree=1 S3, accuracy=0.9056, mismatches=472

p=10007, gates={3,5,7,11}, maps tested=432:
  exact nontrivial high-coverage relations = 30
  all exact relations are q=3 -> q=3, degree=1 S3 symmetries
  no exact cross-prime relation and no exact degree>1 Dickson relation
  best non-exact high-coverage row:
    q=11 -> q=11, degree=1 S3, accuracy=0.9076, mismatches=924
```

The stable q=3 S3 invariance is a useful sanity check on the branch-set
coordinate, but it does not grow a smooth product or couple different primes.
The negative part is the important scaling result: the obvious
postcritically-finite A-line recurrences do not provide the missing
multi-gate source.

`gate_product_tail.py` checks the higher-order version of the same hope: maybe
pairwise products are weak, but the best multi-gate source states still have an
unusually large product.  On the same `10^48` sample:

```text
artifact: artifacts/gate_product_tail_10e48_q0_5_q3_q7_q11_q13_s900.json
best observed product = 7 * 11 * 13 = 1001 = 9.967 bits
best observed independent percentile = 0.535
independent median = 9.967 bits
independent p95 = 11.552 bits
independent p99 = 11.552 bits
```

The observed best state is therefore exactly ordinary under the independent
marginal model; an independent sample of this size often finds the same
three-gate product and sometimes finds all four gates.  This demotes raw
higher-order clustering.  Any remaining direct-torsion scaling method must
extract or construct a normalized class relation, not merely exploit accidental
multi-gate tails in first-lift samples.

`trace_residue_gate_probe.py` identifies what these quotient classes are.  For
mixed gates `q != q0`, the gate is positive exactly when the selected
curve/twist component order is `0 mod q`.  If
`t = p + 1 - #E_A(F_p)`, this is the trace-residue condition:

```text
selected curve: t ==  p + 1 (mod q)
selected twist: t == -p - 1 (mod q)
```

The checker compares the liftability fixture signs with exact point counts:

```text
artifacts/trace_residue_gate_q863_q0_5_q3_q7_q11_q13.json
  q=3,7,11,13: mismatches = 0 over 213 A-fibers

artifacts/trace_residue_gate_q991_q0_5_q3_q7_q11_q13.json
  q=3,7,11,13: mismatches = 0 over 186 A-fibers

artifacts/trace_residue_gate_10e48_q0_5_q3_q7_q11_q13_s900_f40.json
  q=3,7,11,13: mismatches = 0 over 40 point-counted 10^48 A-fibers
```

This explains why the quotient bits descend cleanly yet behave independently:
they are ordinary Frobenius trace congruences pulled back to the first-lift
surface.  A successful normalized class method must therefore do something
stronger than predict these bits one at a time.  It must construct a low-cost
source on which many trace residues are forced or algebraically linked.  In
SEA language, the missing primitive is not "compute another q-gate"; it is
"produce many selected-side `Frob = 1` eigenvalue conditions for less than the
product of their individual modular costs."

A pilot with first lift `q0=3` gives the same broad rule but warns against
overfitting the quotient:

```text
F_607, q0=3:
  q=2: A_mixed=0, j_mixed=28
  q=3: A_mixed=9, j_mixed=6
  q=5: A_mixed=0, j_mixed=0
  q=7: A_mixed=0, j_mixed=0

F_863, q0=3:
  q=2: A_mixed=0, j_mixed=25
  q=3: A_mixed=0, j_mixed=0
  q=5: A_mixed=0, j_mixed=89
  q=7: A_mixed=0, j_mixed=62
```

`class_packet.py` now condenses the raw fixtures into reusable class packets:
quotient sign classes, mixed fibers, pairwise gate products, and optional
cover-row `x` character scans.  The compact artifacts are:

```text
artifacts/class_packet_q0_5.json
artifacts/class_packet_q0_5.tsv
artifacts/class_packet_q0_3.json
artifacts/class_packet_q0_3.tsv
artifacts/class_packet_q991_mixed_x.json
artifacts/class_packet_q0_3_mixed_x.json
```

The packet evidence separates two phenomena that looked similar in the raw
quotient tables:

```text
q=2 quotient failure:
  For q0=5 and p in {607,863,991,1231}, every mixed j-fiber of the q=2 gate is
  split exactly by chi(A+2).  Counts:
    F_607:  19/19 mixed j-fibers exact
    F_863:  16/16 mixed j-fibers exact
    F_991:  28/28 mixed j-fibers exact
    F_1231: 32/32 mixed j-fibers exact

  For q0=3:
    F_607: 28/28 mixed j-fibers exact
    F_863: 25/25 mixed j-fibers exact

  Interpretation: q=2 is not a hidden j-class.  It is the visible signed-A
  cover, with the expected y-coordinate obstruction at the marked x=1 point.

same-prime / odd-cover failures:
  F_991, q0=5, q=5:
    A_mixed=12; best mixed-row feature is -chi(x), 240/288 = 0.833.
    No simple feature separates all mixed fibers.
    No monic degree <= 2 character chi(f(x)) on mixed rows:
      scanned 983072 candidates, hits none.

  F_607, q0=3, q=3:
    A_mixed=9; best mixed-row feature is -chi(x), score 0.75.
    No monic degree <= 2 character chi(f(x)) on mixed rows:
      scanned 369056 candidates, hits none.

  F_863, q0=3, q=5 and q=7:
    The pmA failures are signed-A cover failures: chi(A) separates every mixed
    pmA fiber for q=5 (58/58) and q=7 (31/31).
    The j failures include further identifications: chi(A) explains only
    58/89 q=5 mixed j-fibers and 31/62 q=7 mixed j-fibers.
    No monic degree <= 2 character chi(f(x)) on mixed rows:
      scanned 745632 candidates for each mixed quotient, hits none.
```

Pairwise gate-product packets do not yet show a stable small basis of classes.
Degree-2 product scans are now recorded:

```text
artifacts/class_packet_q0_5_rel_degree2.json
artifacts/class_packet_q0_5_rel_degree2.tsv
artifacts/class_packet_q0_3_rel_degree2.json
artifacts/class_packet_q0_3_rel_degree2.tsv
```

Across all tested `A`, `{A,-A}`, and `j` quotient products, there are no
nontrivial stable degree-2 character hits.  The only product hits are the
tautological/constant cases where two resolved gate classes agree on an entire
guard field, such as `q=3` and `q=5` on `F_607, q0=5`, or `q=5` and `q=7` on
the resolved `F_863, q0=3` `pmA`/`j` classes.  These do not survive the other
guard fields, so they are probably field-specific coincidences unless a later
normalization explains them.

`rational_branch_support_probe.py` strengthens that negative result.  Instead
of asking for one monic polynomial, it asks whether a resolved quotient class is
any product of up to four rational branch factors:

```text
sign(z) = +/- chi((z-a1)(z-a2)...(z-ak)),  k <= 4
```

The exact meet-in-the-middle screen was run on

```text
q0=5, p in {607,863,991,1231}, q in {2,3,5,7}
q0=3, p in {607,863},          q in {2,3,5,7}
quotients z in {A, pmA, j}
```

It tested 70 nontrivial quotient screens and found zero hits:

```text
artifact: artifacts/rational_branch_support_q0_3_q0_5_degree4.json
q0=5 fixtures: 48/48 screens tested, 0 hits
q0=3 fixtures: 22/24 screens tested, 0 hits
```

Thus the resolved A/pmA/j gate classes are not low-degree rational branch
divisors in the obvious coordinates.  This still leaves non-rational branch
support, higher degree, and normalized cover coordinates open, but it closes the
nearest cheap A-line source law.

The p27 research handoff suggests one obvious normalized cover coordinate to
try before going to full Kummer extraction: the signed sheet above the marked
`x=1` point.  In this Montgomery setting the selected-side coordinate is

```text
B1^2 = A + 2                         if A+2 is square,
B1^2 = (A + 2) / nonsquare           otherwise,
```

with `B1` taken modulo sign.  Adding `B1` as a quotient to the exact rational
branch screen gives the same answer:

```text
artifact: artifacts/rational_branch_support_B1_q0_5_q3_7_11_13_degree4.json
q0=5, p in {607,863,991,1231}, q in {3,7,11,13}: 0 hits

artifact: artifacts/rational_branch_support_B1_q0_3_q5_7_degree4.json
q0=3, p in {607,863}, q in {5,7}: 0 hits
```

So the nearest p27-style sheet shortcut is also closed here: mixed selected
component gates are not products of up to four rational branch factors on the
marked-point `B1` line.  This does not kill higher-degree or non-rational
Kummer classes, but it says the source is not hiding in the first normalized
double cover.

`mixed_row_branch_support_probe.py` applies the same degree-4 rational support
test inside mixed quotient fibers, using the row coordinate `x`.  This targets
the same-prime and signed-cover exceptions that do not descend cleanly to a
resolved quotient class.  On the same guard fixtures it found zero hits:

```text
artifact: artifacts/mixed_row_branch_support_x_q0_3_q0_5_degree4.json

same-prime cases:
  F_991, q0=5, q=5:
    mixed A/pmA/j row screens, 288 rows each, 0 hits
  F_607, q0=3, q=3:
    mixed A/pmA/j row screens, 72 rows each, 0 hits

signed-cover and residual mixed cases:
  q=2 mixed pmA/j screens over p in {607,863,991,1231}, 0 hits
  F_863, q0=3, q in {5,7} mixed pmA/j screens, 0 hits
```

So the hidden row-level selector is not a product of a few rational factors in
raw `x` either.  The remaining plausible route is an actual normalized
fiber/Kummer coordinate, not another low-degree raw-coordinate character scan.

### Same-prime fiber extraction

`torsion_fiber_probe.py` turns the same-prime mixed fibers into actual group
coordinates.  For odd first lift `q0`, let `P` be the point with `x(P)=1` on
the curve or twist component selected by `chi(A+2)`, and choose
`B=[u]P` with `u*q0 = 1 mod 4`, so that `[q0]B=P`.  Each first-lift root can
then be oriented and written as

```text
R = B + T,  T in E[q0].
```

The second same-prime lift bit is not an arbitrary character of `x`.  It is the
linear group condition

```text
B + T in q0 * G,
```

where `G` is the relevant curve/twist group over `F_p`.  On the observed mixed
fibers this condition cuts out a one-dimensional `F_q0` line in the recovered
`q0`-torsion fiber.

For the two same-prime mixed cases found earlier:

```text
F_991, q0=5, q=5:
  12/12 mixed A-fibers are exact 5-torsion lines.
  Each has rows=24, plus=4, minus=20.
  The selected curve/twist component has order 1000 = 2^3 * 5^3.

F_607, q0=3, q=3:
  9/9 mixed A-fibers are exact 3-torsion lines.
  Each has rows=8, plus=2, minus=6.
  The selected curve/twist component has order 648 = 2^3 * 3^4.
```

All-fiber passes make the rule more explicit.  For `q0=5, q=5`:

```text
F_607:
  90 fibers: rows=4,  plus=0, v5(component)=1
  66 fibers: rows=4,  plus=4, v5(component)=2

F_863:
  186 fibers: rows=4, plus=0, v5(component)=1
  27 fibers:  rows=4, plus=4, v5(component)=2

F_991:
  126 fibers: rows=4,  plus=0, v5(component)=1
  48 fibers:  rows=4,  plus=4, v5(component)=3
  12 fibers:  rows=24, plus=4, v5(component)=3, positive rows are a line

F_1231:
  180 fibers: rows=4,  plus=0, v5(component)=1
  54 fibers:  rows=4,  plus=4, v5(component)=2
  13 fibers:  rows=24, plus=0, v5(component)=2
```

For `q0=3, q=3`:

```text
F_607:
  139 fibers: rows=2, plus=0, v3(component)=1
  48 fibers:  rows=2, plus=2, v3(component)=2
  18 fibers:  rows=2, plus=2, v3(component)=4
  15 fibers:  rows=8, plus=0, v3(component)=2
  9 fibers:   rows=8, plus=2, v3(component)=4, positive rows are a line

F_863:
  312 fibers: rows=2, plus=0, v3(component)=1
  54 fibers:  rows=2, plus=2, v3(component)=2
  63 fibers:  rows=2, plus=2, v3(component)=3
```

This is the first genuinely mathematical simplification of the mixed-prime
tower.  The hidden same-prime bit is the `q0`-primary Smith/Frobenius
obstruction, not a low-degree visible character.  In SEA language, after
`Frob = 1 mod q0` on the rational torsion line or plane, the next lift is
controlled by the kernel of the mod-`q0` linear map represented by
`(Frob - 1) / q0` on `E[q0]` (or by the equivalent `q0`-primary group
structure).  That is sourceable: compute or constrain this line directly,
instead of treating the `q0^2 - 1` first-lift rows as independent branches.

`same_prime_group_predictor.py` validates the operational form of this rule.
For each same-prime gate it predicts a row as positive iff the oriented
first-lift point `R` lies in `qG`, where `G` is the selected curve/twist group:

```text
predict liftable(R)  <=>  R in qG.
```

In the small guard fields the script enumerates `G` directly.  This is not the
intended large-scale algorithm; it is a verification harness for the eventual
SEA replacement.  The cryptographic-sized version should compute the same data
from the Smith normal form of `Frob - 1` on the `q`-adic Tate module, or
equivalently from the rational `q`-primary group structure of the selected
component.

`same_prime_line_packet.py` packages the same invariant without choosing an
arbitrary basis of `E[q]`.  For each rational q-torsion line it records the
monic polynomial whose roots are the Kummer `x(T)` coordinates of the nonzero
points on that line.  For q=3 this line polynomial is linear; for q=5 it is
quadratic.  The selected line is `qG cap E[q]` when that intersection is
one-dimensional.

On the mixed same-prime fibers:

```text
artifact: artifacts/same_prime_line_packet_mixed_q0_3_q0_5.json

F_991, q0=5, q=5:
  12 mixed fibers, all selected line polynomials match the positive rows.
  example selected coefficients: (884,552), (926,756), (11,536)

F_607, q0=3, q=3:
  9 mixed fibers, all selected line polynomials match the positive rows.
  example selected coefficients: (247), (393), (221)
```

The all-fiber packet confirms this basis-free line exactly captures the
Smith-type buckets already seen in group coordinates:

```text
artifact: artifacts/same_prime_line_packet_all_q0_3_q0_5.json

q0=5:
  F_607:  156 fibers, selected_lines=66,  matches=156, mismatches=0
  F_863:  213 fibers, selected_lines=27,  matches=213, mismatches=0
  F_991:  186 fibers, selected_lines=60,  matches=186, mismatches=0
  F_1231: 247 fibers, selected_lines=54,  matches=247, mismatches=0

q0=3:
  F_607: 229 fibers, selected_lines=75,  matches=229, mismatches=0
  F_863: 429 fibers, selected_lines=117, matches=429, mismatches=0
```

`line_selector_relation_probe.py` then asks whether the selected line is cut
out by a low-degree equation in these normalized line-polynomial coordinates.
For each fixture it forms rows `(A, coeffs...)`, searches total degree <= 4
polynomials vanishing on all selected lines, and checks whether any such
polynomial avoids every unselected line.  The result is negative in the useful
way:

```text
artifact: artifacts/line_selector_relation_q0_3_q0_5_degree4.json

q0=5 fixtures:
  monomials=35, nullity=11, structural=11, separator=False

q0=3 fixtures:
  monomials=15, nullity=1, structural=1, separator=False
```

The nullspace consists only of structural relations shared by all rational
q-torsion lines, i.e. the line-coordinate version of the q-division equation.
It does not separate `qG cap E[q]`.  Thus the normalized line packet gives the
right intrinsic object, but the selector still requires Frobenius/Smith data or
a deeper Kummer relation; it is not exposed by a small raw polynomial relation
among `A` and the line coefficients.

`scalar_selector_collision_probe.py` checks the complementary question: could a
partial-SEA trace or full point count determine the selected line without
matrix/eigenline data?  It groups selected-line packets by scalar invariants
such as component order, selected trace modulo `q^k`, q-adic valuation, and
`A mod q`.  Collisions are immediate:

```text
artifact: artifacts/scalar_selector_collision_q0_3_q0_5.json

component_order key:
  F_607,  q0=5: 66 selected lines under the same component order 600
  F_863,  q0=5: 27 selected lines under the same component order 900
  F_991,  q0=5: 60 selected lines under the same component order 1000
  F_607,  q0=3: 75 selected lines across only 3 component orders
  F_863,  q0=3: 117 selected lines across only 3 component orders

trace_mod_q4 key:
  same collision counts as component_order in the fixed-field guards.

order_and_A_mod_q key:
  still collides in every fixture; e.g. F_991, q0=5 has
  60 selected lines in 5 groups, max 15 distinct lines in one group.
```

Therefore scalar SEA output can say whether a q-divisible line exists and how
deep the selected component is, but it cannot choose the line.  For repeated
same-prime lifting, the useful primitive must expose Frobenius action on the
q-torsion line/plane, not merely the trace.

The PARI source inspection points to the exact hook.  In `ellsea.c`,
`find_trace_Elkies_power` first computes an Elkies kernel polynomial:

```text
tmp = find_isogenous(...)
kpoly = gel(tmp, 3)
```

and then lifts the Frobenius eigenvalue:

```text
lambda = find_eigen_value_power(..., kpoly, ...)
```

but the public trace path immediately collapses that information to the scalar

```text
trace = lambda + p/lambda mod ell^k
```

before returning.  A same-prime Smith primitive should instead return records
of the form

```text
(ell, k, kpoly, lambda mod ell^k)
```

or, for the rational `lambda = 1 mod ell` case, the reduced kernel of
`(Frob - 1)/ell` on `E[ell]`.  That is the missing data needed to continue the
q-primary chain without enumerating all first-lift branches or doing a full
point count.

The resulting algorithmic target is concrete:

```text
For each rational q-torsion line L:
  SEA gives a kernel polynomial h_L and Frobenius eigenvalue lambda_L.
  If lambda_L == 1 mod q^2, then L is contained in qG and is the next
  same-prime lift line.
  More generally, v_q(lambda_L - 1) is the depth available on that line.
```

For a full rational `E[q]` fiber there are `q+1` lines; the current root-based
probe finds the good one by testing preimages branch by branch.  The SEA-Smith
version would get the same line from eigenvalue lifts, turning a repeated
`q^2`-branch local search into a small list of line records with valuations.
This is the first branch that plausibly changes the same-prime tower from
sampling roots to following q-adic Frobenius data.

`qadic_line_tower_probe.py` checks the same target from the group side on the
small guard fields.  For each rational q-torsion line `L` it computes

```text
depth(L) = max e >= 1 such that L subset q^(e-1)G
```

by direct enumeration, then compares the lines with `depth >= 2` against the
actual positive same-prime rows.  This is the group-side analogue of
`v_q(lambda_L - 1)`.

```text
artifact: artifacts/qadic_line_tower_q0_3_q0_5.json

q0=5:
  F_607:  fibers=156, mismatched_positive_depth_fibers=0
  F_863:  fibers=213, mismatched_positive_depth_fibers=0
  F_991:  fibers=186, mismatched_positive_depth_fibers=0
  F_1231: fibers=247, mismatched_positive_depth_fibers=0

q0=3:
  F_607: fibers=229, mismatched_positive_depth_fibers=0
  F_863: fibers=429, mismatched_positive_depth_fibers=0
```

The deeper buckets also show up line-by-line: for example `F_991, q0=5` has
selected lines of depths 2 and 3, and `F_607, q0=3` has selected lines of
depths 2, 3, and 4.  This strengthens the SEA hook target: the missing
primitive is not just "does q divide the component order?", but the eigenline
valuation attached to each rational torsion line.

The predictor is exact on the current same-prime guard fixtures:

```text
q0=5, q=5, p in {607,863,991,1231}:
  fibers=802, rows=3708, mismatches=0
  predicted_plus=actual_plus=828

q0=3, q=3, p in {607,863}:
  fibers=658, rows=1460, mismatches=0
  predicted_plus=actual_plus=384
```

The bucketed Smith-style quantity is `|qG ∩ E[q]|`, written below as
`qdiv_Eq`.  It explains both one-dimensional and two-dimensional first-lift
fibers:

```text
qdiv_Eq=1:
  no q-divisible q-torsion direction, so no same-prime lift rows.

qdiv_Eq=q:
  one q-divisible direction, so either all rows lift on a rational torsion
  line, or exactly one line lifts inside a full E[q] fiber.

Observed buckets:
  q0=5:
    rows=4,  plus=0, vq=1, qdiv_Eq=1:  582 fibers
    rows=4,  plus=4, vq=2, qdiv_Eq=5:  147 fibers
    rows=4,  plus=4, vq=3, qdiv_Eq=5:   48 fibers
    rows=24, plus=0, vq=2, qdiv_Eq=1:   13 fibers
    rows=24, plus=4, vq=3, qdiv_Eq=5:   12 fibers

  q0=3:
    rows=2, plus=0, vq=1, qdiv_Eq=1: 451 fibers
    rows=2, plus=2, vq=2, qdiv_Eq=3: 102 fibers
    rows=2, plus=2, vq=3, qdiv_Eq=3:  63 fibers
    rows=2, plus=2, vq=4, qdiv_Eq=3:  18 fibers
    rows=8, plus=0, vq=2, qdiv_Eq=1:  15 fibers
    rows=8, plus=2, vq=4, qdiv_Eq=3:   9 fibers
```

This gives a concrete scalable strategy for repeated same-prime lifting:

1. Use the first lift only to move onto a component where `Frob` has eigenvalue
   `1 mod q`.
2. Compute the `q`-primary Smith data of `Frob - 1` rather than enumerating
   every `q`-preimage.
3. Continue only along the affine kernel/coset `R in qG`.  In a full `E[q]`
   fiber this replaces `q^2 - 1` row trials by a single `F_q` line; in the
   common rational-line case it decides the whole fiber at once.

The first cryptographic-sized smoke test was run at the `10^48` target

```text
p = 1000000000000000000000000000000000000000000000193.
```

`same_prime_valuation_probe.py` sampled guided first-lift states and compared
the same-prime root check against a valuation predictor.  The large-field probe
does not enumerate `G`; it only uses PARI point counting to compute the selected
curve/twist component order, then applies the rational-line rule

```text
first_fiber_rows = q - 1 and v_q(#G) >= 2  =>  same-prime liftable.
```

Results:

```text
q0=5, q=5:
  samples=80, initial_states=82, analyzed_rows=20
  comparable=20, unknown=0, mismatches=0
  actual_liftable=2
  every analyzed fiber had first_fiber_rows=4

q0=3, q=3:
  samples=80, initial_states=72, analyzed_rows=20
  comparable=20, unknown=0, mismatches=0
  actual_liftable=9
  every analyzed fiber had first_fiber_rows=2
```

So the same-prime rule survives at `10^48` in the common rational-line regime.
The timing also matters: at 160 bits, PARI `ellcard` took roughly 1.2-3.0s per
sampled `A`, while the local same-prime root check was only milliseconds.
Therefore the point-counting harness is not itself a speedup for `10^48`; it is
evidence that the correct fast implementation should reuse SEA/Frobenius Smith
data already needed for trace work, or compute the small `q`-primary invariant
without a full root/preimage search.

`same_prime_depth_probe.py` then removed the point count entirely and measured
the same q-primary depth by repeated same-prime preimage checks.  This is the
certificate-side version of computing the q-primary Smith depth:

```text
q0=5, q=5 at 10^48:
  samples=160, initial_states=173, analyzed_rows=40
  depth_buckets={1: 33, 2: 5, 3: 2}
  max_depth_seen=3
  repeated-lift work: 1.220s total

q0=3, q=3 at 10^48:
  samples=160, initial_states=154, analyzed_rows=40
  depth_buckets={1: 20, 2: 10, 3: 9, 6: 1}
  max_depth_seen=6
  repeated-lift work: 0.739s total

Expanded holdout:

q0=3, q=3 at 10^48:
  samples=800, analyzed_rows=160
  depth_buckets={1: 103, 2: 39, 3: 13, 4: 4, 5: 1}
  max_depth_seen=5
  repeated-lift work: 0.486s total

q0=5, q=5 at 10^48:
  samples=800, analyzed_rows=120
  depth_buckets={1: 97, 2: 16, 3: 5, 4: 2}
  max_depth_seen=4
  repeated-lift work: 2.006s total

q0=7, q=7 at 10^48:
  samples=800, initial_states=756, analyzed_rows=120
  depth_buckets={1: 107, 2: 12, 3: 1}
  max_depth_seen=3
  repeated-lift work: 1.874s total
```

This is not enough by itself to reach the `10^48` certificate bound, but it is
the right inexpensive primitive.  Same-prime q-depth can be measured at
millisecond scale using preimage equations, whereas full point counting spends
seconds per curve and can fall into SEA cliffs.  The next mixed-prime search
should use this depth primitive as a local score/source of q-primary valuation,
then combine several primes or quotient-class conditions instead of calling
`ellcard` on random curves.

`qprimary_depth_economics.py` prices this primitive as a prefilter and as a
putative long-chain source.  On the existing holdouts, using a 2.6s full-SEA
baseline at `10^48`, the cheap q-depth screen is worthwhile:

```text
artifact: artifacts/qprimary_depth_economics_10e48_holdout.json

q=3, 400 first-lift states:
  depth buckets = {1:252, 2:89, 3:38, 4:11, 5:7, 6:3}
  best screen: keep depth >= 6, accepted = 3/400
  modeled speedup vs random full SEA = 0.685 log10 ~= 4.84x

q=5, 120 first-lift states:
  depth buckets = {1:97, 2:16, 3:5, 4:2}
  best screen: keep depth >= 4, accepted = 2/120
  modeled speedup vs random full SEA = 0.634 log10 ~= 4.31x

q=7, 120 first-lift states:
  depth buckets = {1:107, 2:12, 3:1}
  best screen: keep depth >= 2, accepted = 13/120
  modeled speedup vs random full SEA = 0.474 log10 ~= 2.98x
```

Against the real two-sided curve/twist baseline, the same holdouts are still
useful but less dramatic:

```text
artifact: artifacts/qprimary_depth_economics_10e48_holdout_two_sided.json

q=3:
  best screen: keep depth >= 6
  modeled speedup vs two-sided random full SEA = 0.384 log10 ~= 2.42x

q=5:
  best screen: keep depth >= 4
  modeled speedup vs two-sided random full SEA = 0.333 log10 ~= 2.15x

q=7:
  best screen: keep depth >= 2
  modeled speedup vs two-sided random full SEA = 0.173 log10 ~= 1.49x
```

The same calculation is negative for pure long q-primary scaling.  To clear
the `10^48` one-shot threshold with only one odd prime would need:

```text
q=3: total q-depth 50, 49 levels after the first lift
q=5: total q-depth 34, 33 levels after the first lift
q=7: total q-depth 28, 27 levels after the first lift
```

At those crossing depths the two-sided random smooth-tail budget is only
`16.66` source bits.  Ordinary geometric q-depth sampling would cost about
`75-78` bits, or `10^22.8` to `10^23.4` first-lift candidates.  Thus q-primary
Smith depth is a good local prefilter and scoring primitive, but a scalable
one-prime method still needs a new recurrence/class source that makes long
Smith chains available far below their natural q-adic density.

The cost model sharpens that conclusion.  At `10^48`, a pure q-primary tower
would need roughly 49 levels for q=3, 33 levels for q=5, or 27 levels for q=7
to cross the one-shot bound.  The observed root-only tails are geometric and
stop around depth 3-6 in hundreds of rows.  Therefore the primitive is not a
search method by itself.
It is the local operation that a future Smith/Kummer class method must replace
or batch across many levels.

`same_prime_sea_prefix_probe.py` connects this q-primary tower picture back to
SEA.  It samples guided first-lift states, runs the patched SEA prefix stream,
and compares the early `ell=q0` trace record to both the completed
selected-component valuation and the certificate-side repeated root depth.  At
`10^48`, the first same-prime SEA record is exact whenever the returned
modulus is not saturated:

```text
q0=3, 50 guided first-lift states:
  SEA record: single mod 81 for every row
  usable unsaturated rows = 46
  exact valuation matches = 46/46
  root-depth matches = 46/46
  saturated rows = 4
  max exact/root depth = 5

q0=5, 40 guided first-lift states:
  SEA record: single mod 25 for every row
  usable unsaturated rows = 33
  exact valuation matches = 33/33
  root-depth matches = 33/33
  saturated rows = 7
  max exact/root depth = 4

q0=7, 18 guided first-lift states:
  SEA record: single mod 49 for every row
  usable unsaturated rows = 15
  exact valuation matches = 15/15
  root-depth matches = 15/15
  saturated rows = 3
  max exact/root depth = 2
```

This is a positive implementation result and a negative scaling result at the
same time.  The small-q Smith depth is already visible in the first SEA prefix
record, so a source-level `ellsea_prefix` primitive can replace many local
preimage checks for shallow depths.  But the visible modulus is tiny
(`3^4`, `5^2`, `7^2` here), while cryptographic-range one-prime towers would
need tens of q-adic levels.  Therefore the remaining mathematical problem is
not to expose the existing low-level SEA data; it is to find a way to force or
predict a long q-primary Smith chain.

`mixed_depth_profile.py` extends that primitive from same-prime depth to a
small-prime valuation vector.  For each guided first-lift state it measures, by
root checks only, the maximum visible extra depth for

```text
q in {2,3,5,7,11,13}.
```

It then predicts the product obtained by multiplying the independent extra
depths, and optionally tries to realize that product constructively.  The
realization step now defaults to chained same-prime probes: finish the visible
`2`-power depth with the cheap same-prime depth primitive, then rerun the same
primitive for `3`, `5`, and so on from the current lifted point.  This matches
the group-theoretic fact that for coprime `m,n`, membership in `mG` and `nG`
implies membership in `mnG`; multiplication by `m` is invertible on the
`n`-primary quotient.  At the `10^48` target this gives a useful separation
between three objects:

```text
scalar depth profile:
  cheap upper envelope for how many small-prime image conditions a point
  separately satisfies.

constructive combined lift:
  an actual point reached by choosing compatible preimage roots.

certificate bound:
  order > 1000000000002000000000001, about 79.7 bits.
```

The first full profile passes used 120 guided states per entry prime:

```text
q0=3:
  median=5.91 bits, p90=12.09 bits, p99=15.41 bits
  best_profile=26.11 bits, predicted_order=72441600
  best vector: q2:e2+6, q3:e1+0, q5:e0+2, q7:e0+3, q11:e0+1

q0=5:
  median=7.13 bits, p90=12.78 bits, p99=16.44 bits
  best_profile=18.50 bits, predicted_order=371800
  best vector: q2:e2+1, q5:e1+1, q11:e0+1, q13:e0+2

q0=7:
  median=7.98 bits, p90=12.88 bits, p99=15.61 bits
  best_profile=16.37 bits, predicted_order=84700
  best vector: q5:e0+2, q7:e1+0, q11:e0+2

q0=11:
  median=8.46 bits, p90=12.83 bits, p99=17.19 bits
  best_profile=17.87 bits, predicted_order=239580
  best vector: q3:e0+2, q5:e0+1, q11:e1+2
```

There are also real tail events.  In an independent `q0=11` sample, the top
candidate had

```text
predicted_bits = combined_bits = 27.07
combined_order = 140540400
vector = q2:e2+2, q3:e0+3, q5:e0+2, q7:e0+1, q11:e1+0, q13:e0+2
elapsed_seconds for profile+combine = 9.811
combine_seconds only = 0.817
```

so the valuation-vector score can identify constructively realizable mixed
products well beyond the earlier one-step tail searches.  The same correction
matters for `q0=3`.  The best 120-state profile predicted 26.11 bits, and the
original interleaved combiner only realized 22.11 bits:

```text
predicted_order = 72441600  = 2^8 * 3 * 5^2 * 7^3 * 11
interleaved     = 4527600   = 2^4 * 3 * 5^2 * 7^3 * 11
```

That was beam pruning, not a mathematical obstruction.  A prime-block combiner
with a 512-state beam completed the same profile exactly in 72.411s, and the
new chained combiner completed it with only 64 same-prime states per layer:

```text
chain_combined = 72441600
combined_bits  = 26.11
elapsed_seconds for profile+combine = 31.279
combine_seconds only = 0.748
```

The chain steps stay small because each prime is handled by its own depth
primitive:

```text
2^6 chain: parents grow 1 -> 64, total about 0.068s
5^2 chain: parents grow 1 -> 4, total about 0.026s
7^3 chain: parents grow 1 -> 42, total about 0.624s
11 chain: 1 parent, 11 roots, 10 children, about 0.032s
```

Thus the scalar valuation vector is a valid constructive target for coprime
prime products, provided realization preserves primary branches by chaining
same-prime witnesses rather than interleaving an aggressively pruned beam.  The
remaining scaling problem is not compatibility of the product once found; it is
finding or forcing much larger valuation vectors without random tail luck.

Fresh wider `10^48` panels test that boundary directly.  With 240 unique `A`
states, `q in {2,3,5,7,11,13}`, max extra depth 6, and chained realization of
the top 8 rows:

```text
q0=3:
  profiled_rows=240, elapsed=51.198s
  median=6.59 bits, p90=11.51 bits, p99=18.51 bits
  best_profile=best_combined=20.77 bits
  best vector: q2:e2+1, q3:e1+2, q7:e0+2, q13:e0+2

q0=11:
  profiled_rows=240, elapsed=50.117s
  median=8.63 bits, p90=14.21 bits, p99=19.24 bits
  best_profile=best_combined=25.42 bits
  best vector: q2:e2+1, q5:e0+2, q11:e1+2, q13:e0+2
```

The constructive score is real: every top row completed exactly, so the scalar
profile is not overpromising because of incompatible roots.  But the tail is
still far below the `79.73`-bit certificate threshold.  This supports the same
division of labor as the SEA-prefix experiments: the current implementation is
a good local scorer, while a scaling method needs a way to source or force the
high-depth Kummer/Smith classes instead of sampling the ordinary tail.

`valuation_profile_economics.py` asks whether this scorer is already useful as
a full-SEA prefilter.  It models:

```text
profile many first-lift states using q in {2,3,5,7,11,13}
keep states whose valuation-vector score crosses a threshold
call full SEA only on the accepted band
```

Using the measured profile time from the existing `10^48` artifacts and a 2.6s
full-SEA baseline, this is the strongest current screening layer.  The
two-sided correction compares against the actual curve/twist random baseline:

```text
artifact: artifacts/valuation_profile_economics_10e48_two_sided.json

120-state panels:
  q0=3:  best speedup = 0.760 log10 ~= 5.8x
         threshold = 13.49 bits, accepted = 6/120, avg accepted = 17.37 bits
  q0=5:  best speedup = 0.622 log10 ~= 4.2x
         threshold = 11.48 bits, accepted = 22/120, avg accepted = 13.59 bits
  q0=7:  best speedup = 0.640 log10 ~= 4.4x
         threshold = 11.44 bits, accepted = 23/120, avg accepted = 13.36 bits
  q0=11: best speedup = 0.661 log10 ~= 4.6x
         threshold = 11.69 bits, accepted = 22/120, avg accepted = 14.00 bits

240-state chain panels:
  q0=3:  best speedup = 0.688 log10 ~= 4.9x
         threshold = 12.17 bits, accepted = 17/240, avg accepted = 15.52 bits
  q0=11: best speedup = 0.811 log10 ~= 6.5x
         threshold = 13.54 bits, accepted = 30/240, avg accepted = 15.59 bits
```

This is an important practical improvement over random full SEA and over the
line-only menu.  It still does not change the asymptotic picture: the accepted
rows average only about `14-17` forced bits, far short of the `79.73`-bit
certificate threshold at `10^48`.  The mathematical target is now stricter:
find a source that produces valuation-vector scores in the certificate range,
or at least far beyond this profile-screen tail, without paying ordinary
q-adic/smooth-tail density.

`valuation_profile_scaling_model.py` extrapolates the same empirical
valuation-profile score distributions to larger challenge sizes.  It measures
work in full-SEA-equivalent calls, using the observed `10^48` profile/SEA cost
ratio of about `0.08` for the 240-state panels.  This removes the absolute
timing assumption and asks how much exponent the local profile actually buys:

```text
artifact: artifacts/valuation_profile_scaling_10e48_10e100_two_sided.json

q0=11 240-state profile:
  10^48: random log10 =  5.015, screened log10 =  4.204, speedup = 0.811
  10^60: random log10 =  6.438, screened log10 =  5.553, speedup = 0.884
  10^80: random log10 =  8.926, screened log10 =  7.957, speedup = 0.969
  10^100:random log10 = 11.504, screened log10 = 10.479, speedup = 1.025

q0=3 240-state profile:
  10^48: random log10 =  5.015, screened log10 =  4.328, speedup = 0.688
  10^60: random log10 =  6.438, screened log10 =  5.680, speedup = 0.758
  10^80: random log10 =  8.926, screened log10 =  8.086, speedup = 0.839
  10^100:random log10 = 11.504, screened log10 = 10.610, speedup = 0.894
```

An optimistic near-free q0=11 profile, charging only `0.001` full-SEA calls per
candidate, gives an upper bound on what pure engineering of this local screen
could do:

```text
artifact: artifacts/valuation_profile_scaling_10e48_10e100_nearfree_two_sided.json

10^48:  screened log10 = 3.403, speedup = 1.613
10^60:  screened log10 = 4.705, speedup = 1.733
10^80:  screened log10 = 7.060, speedup = 1.865
10^100: screened log10 = 9.553, speedup = 1.951
```

Thus the mixed valuation profile is a scalable support layer in the engineering
sense: it should keep buying roughly one decimal order of search at larger
sizes, and under two decimal orders even if computed almost for free from
SEA-prefix data.  But it remains an exponent offset, not a new source.  It
does not move `10^80` into easy range by itself.

`sea_abort_profile_probe.py` tests the direct hybrid version of this idea:
rank by the cheap mixed valuation profile, then hand the shortlist to PARI
`ellsea(E, torsion)` with the profile product as the known divisor.  The probe
now scores both abort-discovered torsion and the B-smooth part of any full
order returned by SEA, since at `10^48` the latter happens frequently and is
the honest visible signal.

```text
artifact: artifacts/sea_abort_profile_10e48_q11_top80_steps4_extract12_visible.json

source profile:
  q0=11 240-state panel
  best profile score = 25.42 bits

SEA-abort/profile hybrid:
  source_top = 80, max SEA-abort steps = 4
  elapsed = 48.88s, full_orders = 80/80
  best SEA-discovered torsion = 26.00 bits
  best visible B-smooth component = 45.87 bits
  best extracted smooth order = 45.87 bits
  verified certificate rows = 0
```

This is the clearest practical 10^48 test so far for the mixed-profile route.
It turns a 25-bit local score into occasional low-to-mid-40-bit component
smoothness after SEA, which is a useful ranking layer.  It still lands far
below the `79.73`-bit one-shot threshold.  The extra smoothness in the top rows
is residual smooth-tail luck after the local profile rather than a sourced
certificate-range product.

`profile_prefilter_search.py` is the end-to-end streaming version of the same
screen: generate q0-guided first-lift states, compute the mixed valuation
profile, and run selected-component extraction only above a score threshold.
The two-sided speedups below are recalculated in
`artifacts/profile_prefilter_search_10e48_q11_q3_two_sided_rebaseline.json`.
At `10^48`, using the q0=11 threshold predicted by the economics model:

```text
artifact: artifacts/profile_prefilter_search_10e48_q11_s1000_states240_thr13p536_seed20260804_econ.json

q0=11, profile q in {2,3,5,7,11,13}
threshold = 13.536 profile bits
profiled states = 240
accepted rows = 22  (9.17%)
profile time/state = 0.162s
extraction time/accepted row = 0.523s
total time/state = 0.228s
best profile score = 20.27 bits
best component smoothness = 43.77 bits
best extracted smooth order = 42.77 bits
verified certificate rows = 0

modelled speedup vs two-sided 2.6s random full-SEA baseline:
  random expected seconds log10 = 5.430
  profiled expected seconds log10 = 4.411
  speedup = 1.019 log10 ~= 10.5x
```

This validates the practical prefilter more strongly than the static economics
artifact did: the search plumbing preserves, and in this small run improves,
the constant-factor speedup.  But the best rows are still
certificate-range failures.  Mining the accepted rows shows why.  The extra
smoothness beyond the local profile is mostly a handful of medium primes outside
the profiled set:

```text
index 107:
  profile = 20.27 bits, component smooth = 43.77 bits
  residual factors beyond profile = 2^3 * 113 * 13147

index 47:
  profile = 13.67 bits, component smooth = 41.52 bits
  residual factors beyond profile = 73 * 937 * 3529

index 41:
  profile = 17.13 bits, component smooth = 36.64 bits
  residual factors beyond profile = 229 * 3257
```

The accepted rows also do not share a single local-depth signature; among the
22 accepted rows only one full `{2,3,5,7,11,13}` depth vector repeated, and that
repeat gave different residual smoothness (`41.52` and `28.80` component bits).
The profile/component correlation in this panel is only moderate
(`r ~= 0.39`).  So the profile screen is a good way to avoid many hopeless full
SEA calls, but the missing mathematical source is still the ability to construct
or cheaply predict the medium-prime residual factors together.

A fresh q0=3 run checks whether this is just a q0=11/seed artifact:

```text
artifact: artifacts/profile_prefilter_search_10e48_q3_s1000_states240_thr12p174_seed20260806_econ.json

q0=3, profile q in {2,3,5,7,11,13}
threshold = 12.174 profile bits
profiled states = 240
accepted rows = 21  (8.75%)
profile time/state = 0.202s
extraction time/accepted row = 0.514s
total time/state = 0.247s
best profile score = 19.62 bits
best component smoothness = 47.73 bits
best extracted smooth order = 47.73 bits
verified certificate rows = 0

modelled speedup vs two-sided 2.6s random full-SEA baseline:
  random expected seconds log10 = 5.430
  profiled expected seconds log10 = 4.579
  speedup = 0.851 log10 ~= 7.1x
```

This is a useful independent confirmation of the local-profile layer: it finds
a better smooth row than the q0=11 streaming panel, but the gain is still a
constant-factor engineering win rather than a certificate-range source.  The
best q0=3 extracted row has only `12.55` profile bits; almost all of its
`47.73` component smoothness is residual luck outside the local profile.

`residual_medium_gate_probe.py` tests the most direct follow-up: after a row
passes the q0=11 mixed profile threshold, add a second menu of medium
selected-component q-gates.  The probe uses the already-counted component orders
to model an ideal free medium menu, and optionally times the actual
`component_torsion_oracle` division-polynomial route.

```text
artifact: artifacts/residual_medium_gate_probe_10e48_q11_profile_thr13p536_menu251_ideal.json

medium menu q = odd primes 17..251
accepted profile rows = 22
best medium-menu bits = 14.94
best profile + medium-menu bits = 31.13
best ideal speedup vs random = 1.946 log10
best ideal speedup vs profile-only = 0.625 log10
```

This is an intentionally optimistic upper bound: it treats all q<=251 selected
component divisibility facts as free.  Even then the menu does not get close to
the `79.73`-bit threshold.  It also misses much of the actual residual mass in
the best profile rows:

```text
index 107:
  actual component smoothness = 43.77 bits
  q<=251 profile+menu bits = 27.09
  missed residual prime = 13147

index 47:
  actual component smoothness = 41.52 bits
  q<=251 profile+menu bits = 19.86
  missed residual primes = 937, 3529
```

The real division-polynomial oracle is much worse economically.  On the six
best extracted rows from the profile panel:

```text
artifact: artifacts/residual_medium_gate_probe_10e48_q11_profile_thr13p536_menu251_oracle_sample.json

q=17: 0.070s / row
q=23: 0.148s / row
q=31: 0.262s / row
q=43: 0.568s / row
q=59: 1.160s / row
q=73: 2.338s / row
```

The matched menu `{17,23,31,43,59,73}` adds at most `6.19` bits to any accepted
row in this panel.  If those gates are free, the best model is only `0.120`
log10 better than profile-only; if charged at the measured `4.545s` per accepted
row, it is `0.355` log10 worse than profile-only:

```text
artifacts/residual_medium_gate_probe_10e48_q11_profile_thr13p536_menu17_73_ideal.json
artifacts/residual_medium_gate_probe_10e48_q11_profile_thr13p536_menu17_73_costed.json
```

The same follow-up on the fresh q0=3 panel is weaker:

```text
artifact: artifacts/residual_medium_gate_probe_10e48_q3_profile_thr12p174_menu251_ideal.json

accepted profile rows = 21
best medium-menu bits = 7.80
best profile + medium-menu bits = 25.32
best ideal speedup vs random = 1.471 log10
best ideal speedup vs profile-only = 0.318 log10

artifact: artifacts/residual_medium_gate_probe_10e48_q3_profile_thr12p174_menu17_73_costed.json

medium menu q = {17,23,31,43,59,73}
best medium-menu bits = 4.09
best profile + medium-menu bits = 21.24
speedup vs profile-only when charged at 4.545s/accepted row = -0.339 log10
```

So medium-prime gates are the right mathematical object but the wrong current
mechanism.  Enumerating q-division roots one q at a time is too expensive, and
a finite medium menu only supplies a constant-offset screen.  A scaling method
needs either SEA/Frobenius access to these residues at nearly zero marginal
cost, or a construction that forces many medium trace residues together rather
than discovering them one by one.

`sea_known_torsion_horizon_probe.py` checks the SEA side of the same question.
The q0=11 profile product is not just a smoothness score; it is a known
selected-component divisor, hence a trace congruence.  That reduces the CRT
product SEA needs before the full trace is determined.  Therefore stock SEA
should usually stop earlier on profile-accepted rows, not later.

```text
artifact: artifacts/sea_known_torsion_horizon_10e48_q11_profile_thr13p536.json

stock 10^48 SEA horizon without known profile torsion:
  auxiliary primes = 19
  aux max = 67
  CRT product = 82.70 bits

q0=11 accepted profile rows, using predicted_order as known torsion:
  rows = 22
  known aux max min/median/max = 59 / 61 / 67
  average known auxiliary count = 18.09
  best visible total at known horizon = 24.88 bits
  best actual component smoothness = 43.77 bits
```

The high-smooth rows explain the failure mode:

```text
index 107:
  profile = 20.27 bits, component smooth = 43.77 bits
  known SEA horizon aux max = 61
  visible at horizon = 23.27 bits
  residual primes = 2, 113, 13147

index 47:
  profile = 13.67 bits, component smooth = 41.52 bits
  known SEA horizon aux max = 61
  visible at horizon = 13.67 bits
  residual primes = 73, 937, 3529

index 41:
  profile = 17.13 bits, component smooth = 36.64 bits
  known SEA horizon aux max = 59
  visible at horizon = 17.13 bits
  residual primes = 229, 3257
```

Forcing SEA past its natural horizon has the same cost problem as the
division-polynomial menu, just expressed in SEA work.  Averaged over the
accepted rows, continuing from the known-torsion horizon to q<=113 requires
about `77.28` extra auxiliary-product bits and about `11.91` extra primes; to
q<=251 requires about `257.68` extra product bits and `35.91` extra primes.
This confirms that "get medium residues from SEA" is only viable if they are
exposed as a byproduct of work already being done, or if there is a new
Frobenius/Smith shortcut.  Simply asking SEA to keep going after it already
knows the trace is another constant-factor engineering branch, not the missing
source.

`first_lift_family_gate_probe.py` tests another possible source loophole.  The
q0-guided first-lift construction samples an `x0` and solves
`x([q0]R)=1` for all Montgomery parameters `A`.  Even though mixed q-gates
descend to `A`, it was still possible that the source coordinate `x0` clustered
medium-good roots and gave a cheaper way to find them.

```text
artifact: artifacts/first_lift_family_gate_10e48_q11_g17_23_31_x1000_f40_r120_seed20260805_v2.json

q0 = 11
medium gates = 17,23,31
x0 values checked = 96
families with roots = 40
valid A roots = 84
valid roots per x0 checked = 0.875
valid roots per nonempty family = 2.10
first-lift solve time per x0 = 0.019s

q=17:
  root hit rate = 3/84 = 0.0357  (random ~= 1/17 = 0.0588)
  families with hits = 3
  all-hit multi-root families = 0
  mixed multi-root families = 2
  family-selected precision = 0.300

q=23:
  root hit rate = 5/84 = 0.0595  (random ~= 1/23 = 0.0435)
  families with hits = 5
  all-hit multi-root families = 0
  mixed multi-root families = 5
  family-selected precision = 0.263

q=31:
  root hit rate = 2/84 = 0.0238  (random ~= 1/31 = 0.0323)
  families with hits = 2
  all-hit multi-root families = 0
  mixed multi-root families = 1
  family-selected precision = 0.400
```

So the `x0` source coordinate does not turn medium divisibility into a clean
family-level event.  When a non-singleton family hits, it is mixed: only some
of the A roots have the medium trace residue.  This agrees with the earlier
descent result in a stronger source sense.  The q0 first-lift parameter is a
good way to enter a useful torsion surface, but medium residual gates remain
individual `A`/trace conditions inside that surface.

This changes the next mathematical target.  A scalar q-depth is a good cheap
score and a constructive recipe, but it still does not explain how to produce an
80-bit certificate-range product at useful density.  The scalable object should
be the A-line or cover-coordinate class that forces high q-depth, or combinations
of those classes, so the search chooses curves already in the high-depth tail
instead of sampling until such a vector appears.

Two tempting shortcuts were checked at `10^48` and do not look competitive.

First, `direct_product_lift.py` solves the composite first equation

```text
x([M]R) = 1
```

for `A`, then hands the resulting exact-order `4M` states to the same mixed-depth
profiler.  This really does force a smooth prefix, but the polynomial degree
wall arrives early:

```text
M=15:
  samples=40, roots=147, valid_prefix_states=44
  solve_seconds=4.821
  best_combined_bits=14.17

M=33:
  samples=3, roots=9, valid_prefix_states=4
  solve_seconds=29.973
  best_combined_bits=9.85

M=35:
  samples=2, roots=6, valid_prefix_states=1
  solve_seconds=29.293
  best_combined_bits=9.71
```

So raw composite-prefix solving is useful as a diagnostic, but it is not the
scaling method: by `M=33`/`35`, one spends tens of seconds just to force a prefix
that is weaker than ordinary guided q0=3/q0=11 tails.

Second, a q0=3 profile including larger lift primes

```text
q in {2,3,5,7,11,13,17,19,23}
```

with 40 states and max extra depth 4 took 43.839s and topped out at only 16.31
bits.  The best vector used `2^3 * 5 * 13^2`; the 17/19/23 entries contributed
zero depth.  Larger q may still matter in a tuned implementation, but simply
adding raw higher-degree preimage equations is not an immediate route to the
80-bit certificate range.

The high-depth tails were also mined for cheap visible features using
`high_depth_feature_miner.py`.  The screen tests simple quadratic characters and
small congruence classes of `A`, `{A,-A}`, `x`, `j`, `A +/- 2`, `A^2 - c`,
`rhs = x^2 + A*x + 1`, and `x*rhs`.

On the 10^48 profile artifacts it does find in-sample enrichments, for example:

```text
q0=3, top 10% total score:
  rhs mod 23 = 18: 2/2 positives
  A mod 7 = 1:     4/12 positives

q0=11, top 10% total score:
  x*rhs mod 17 = 9: 5/8 positives
  j mod 7 = 5:       6/18 positives

q0=11, q11 extra-depth >= 2:
  x*rhs mod 17 = 9: 3/8 positives, all three positives captured
```

But fresh conditioned probes show these are mostly small-sample artifacts rather
than usable forcing classes:

```text
q0=11, filter x*rhs mod 17 = 9, target q11 extra-depth >= 2:
  baseline: 1/120 = 0.0083
  filtered: 0/42  = 0.0000

q0=3, filter A mod 17 = 15, target q7 extra-depth >= 2:
  baseline: 4/120 = 0.0333
  filtered: 0/29  = 0.0000

q0=11, fresh top-5% bucket x mod 29 = 21:
  target q11 extra-depth >= 2, first holdout:
    baseline: 0/240 = 0.0000
    filtered: 3/80 = 0.0375
  target q11 extra-depth >= 2, independent repeat:
    baseline: 4/500 = 0.0080
    filtered: 1/120 = 0.0083
  target q13 extra-depth >= 2:
    baseline: 1/240 = 0.0042
    filtered: 0/78 = 0.0000
```

The first `x mod 29` holdout was tempting, but the repeat collapses to baseline
and the filter itself costs roughly a `1/29` thinning of generated rows.  It is
therefore another in-sample visible bucket, not a usable source.

The one feature that did survive out-of-sample was the already-expected signed
cover for halving:

```text
q0=3, filter chi(A+2)=1, target q2 extra-depth >= 3:
  baseline: 11/120 = 0.0917
  filtered: 18/120 = 0.1500
```

That is a real but small enrichment, and it matches the earlier observation that
2-gates naturally live on a signed `A` cover.  It is not enough to explain the
26-27 bit tails, and it reinforces the point that the next useful invariant is a
derived Kummer/Smith class, not an ad hoc low-degree residue of the visible
coordinates.

`feature_holdout_economics.py` repeats this source test for the full
valuation-vector score.  It mines cheap visible buckets on one profile artifact
and evaluates exactly those buckets on a separate holdout artifact.  The
`q0=3` top-tail filters do not survive:

```text
artifact: artifacts/feature_holdout_q3_profile_top10_to_fresh240.json
holdout positives = 24/240
best holdout p-value bucket:
  rhs mod 19 = 15
  holdout hits = 4/20, lift = 2.0, p = 0.133
best modeled cheap-feature speedup = 0.966 log10
```

The `q0=11` split produced one mildly repeatable bucket, but only at small
counts:

```text
artifact: artifacts/feature_holdout_q11_profile_top10_to_fresh240.json
A mod 23 = 8:
  train hits = 2/5
  holdout hits = 3/8, lift = 3.75, p = 0.038

artifact: artifacts/feature_holdout_q11_fresh240_to_profile_top10.json
A mod 23 = 8:
  train hits = 3/8
  holdout hits = 2/5, lift = 4.0, p = 0.081
```

`valuation_feature_target_probe.py` then targeted that exact bucket on a fresh
sample.  The enrichment collapses to a weak constant-factor effect:

```text
artifact: artifacts/valuation_feature_target_q11_Amod23_8_seed20260802.json
filter: q0=11 and A mod 23 = 8
threshold = 13.536 valuation-profile bits

baseline:
  hits = 8/120, rate = 0.0667
  p95 = 15.02 bits, p99 = 19.62 bits, max = 19.84 bits

filtered:
  hits = 11/120, rate = 0.0917
  enrichment = 1.38, binomial-tail p = 0.177
  p95 = 15.79 bits, p99 = 17.30 bits, max = 19.37 bits
```

So the visible-bucket branch is demoted for valuation-vector tails too.  The
high-score source, if it exists, is not a stable low-modulus residue of the raw
coordinates tested here; it has to be a normalized Kummer/Smith class or a
different construction of the trace/valuation vector.

The same holdout test now includes the p27-inspired `B1` sheet coordinate above
the marked `x=1` point.  In-sample, `B1` looks tempting, especially for q0=11:

```text
artifact: artifacts/high_depth_feature_mine_10e48_B1_top10_20260629.json

q0=11 profile panel:
  B1 mod 13 = 0: 6/16 top-tail hits, lift = 3.75, p = 0.0033
  B1 mod 29 = 4: 4/9 top-tail hits, lift = 4.44, p = 0.0083
```

But the train/holdout accounting demotes it:

```text
artifact: artifacts/feature_holdout_q11_B1_profile_to_stream_20260629.json
best B1 holdout bucket:
  B1 mod 29 = 4: 3/10 hits, lift = 3.00, p = 0.070
best modeled speed feature:
  x mod 11 = 7, speedup = 0.982 log10

artifact: artifacts/feature_holdout_q11_B1_stream_to_profile_20260629.json
best modeled speed feature:
  x mod 19 = 14, speedup = 1.255 log10
B1 legendre:
  13/126 hits, lift = 1.03, p = 0.496

artifact: artifacts/feature_holdout_q3_B1_profile_to_stream_20260629.json
best B1 holdout bucket:
  B1 mod 13 = 6: 3/13 hits, lift = 2.31, p = 0.134
best modeled speed feature:
  pmA mod 29 = 21, speedup = 1.069 log10

artifact: artifacts/feature_holdout_q3_B1_stream_to_profile_20260629.json
best B1 speed bucket:
  B1 mod 29 = 23, speedup = 0.843 log10, weak support
```

Thus `B1` behaves like the other visible buckets: useful as a falsifier and
maybe as a small constant-factor screen, but not a source-normalized route to
the high mixed valuation tails.

`mixed_prime_group_predictor.py` makes that invariant explicit on the small guard
fields.  For a guided first-lift row, orient the Kummer point `R` in the selected
curve/twist component `G`.  Then a q-gate is positive exactly when

```text
q | #G  and  R in qG.
```

Equivalently, the gate is the zero class of `R` in the quotient `G/qG`, with a
nontrivial q-primary kernel available to make the lifted point have exact order
multiplied by `q`.  This applies to mixed primes as well as the same-prime
exception.

The predictor enumerates `G`, builds `qG`, assigns each first-lift row a coset in
`G/qG`, and compares the zero-coset condition to the actual root/exact-order
gate bit.  Guard-field results:

```text
q0=5, p in {607,863,991,1231}, q in {2,3,5,7}:
  rows checked = 3708
  mismatches = 0

q0=3, p in {607,863}, q in {2,3,5,7}:
  rows checked = 2920
  mismatches = 0
```

The coset behavior also explains the earlier descent observations:

```text
mixed-prime gates q != q0:
  mixed_coset_fibers = 0 in every tested guard layer.
  All first-lift rows over the same A have the same G/qG class, so the bit
  descends to the A-fiber/quotient class.

same-prime gates q = q0:
  q0=5: mixed_coset_fibers = 90,186,138,193 over p=607,863,991,1231.
  q0=3: mixed_coset_fibers = 163,312 over p=607,863.
  These are precisely the torsion-fiber cases where the missing coordinate is a
  q0-torsion quotient/coset coordinate rather than bare A.
```

So the class-forcing target is no longer vague.  At cryptographic size we need a
way to compute or prescribe the small-prime coset of the marked point in `G/qG`
without enumerating `G`: this is the `q`-primary Smith/Kummer data of
`Frobenius - 1` together with the marked point's class.  The same data determines
the depth chain, while the cheap preimage probes provide a certificate-side
witness once the desired zero cosets have been found.

There is an important simplification for mixed primes `q != q0`.  Since the
first-lift relation is

```text
[q0]R = +/- P,  x(P)=1,
```

and `q0` is invertible on the `q`-primary quotient, the `q`-primary component of
`R` is zero whenever the fixed point `P` has zero `q`-primary component.  As `P`
has order 4, this holds for every odd `q != q0`.  Therefore the repeated mixed
q-depth is not a new tree search:

```text
extra q-depth of R = v_q(#G),  q odd, q != q0.
```

`component_torsion_sieve.py` checks the first gate using the Kummer q-division
denominator `Z_q(x)`: the selected component has rational q-torsion iff `Z_q`
has a root whose Montgomery RHS lies on that component.  It matches the mixed
odd gate bits exactly in the guard fixtures:

```text
q0=5, p in {607,863}, q in {3,7}: 2952 rows, mismatches=0
q0=3, p in {607,863}, q in {5,7}: 2920 rows, mismatches=0
```

`mixed_prime_line_packet.py` then compresses the same condition from raw
q-torsion points to basis-free Kummer q-torsion lines.  This is the quotient
object relevant to forcing mixed-prime gates: one rational q-line is enough,
and the `(q-1)` nonzero point choices on that line are not separate
mathematical conditions.

```text
artifact: artifacts/mixed_prime_line_packet_q0_3_q0_5.json

q0=5:
  F_607,  q=3: plus_fibers=66,  predicted_plus=66,  mismatches=0
  F_607,  q=7: plus_fibers=9,   predicted_plus=9,   mismatches=0
  F_863,  q=3: plus_fibers=120, predicted_plus=120, mismatches=0
  F_863,  q=7: plus_fibers=93,  predicted_plus=93,  mismatches=0
  F_991,  q=3: plus_fibers=66,  predicted_plus=66,  mismatches=0
  F_991,  q=7: plus_fibers=12,  predicted_plus=12,  mismatches=0
  F_1231, q=3: plus_fibers=90,  predicted_plus=90,  mismatches=0
  F_1231, q=7: plus_fibers=30,  predicted_plus=30,  mismatches=0

q0=3:
  F_607, q=5: plus_fibers=66,  predicted_plus=66,  mismatches=0
  F_607, q=7: plus_fibers=13,  predicted_plus=13,  mismatches=0
  F_863, q=5: plus_fibers=120, predicted_plus=120, mismatches=0
  F_863, q=7: plus_fibers=93,  predicted_plus=93,  mismatches=0
```

Most positive fibers contain exactly one rational q-line; occasional full
`E[3]` fibers contain four rational 3-lines.  This supports the line/eigenvalue
cost model above: the mixed-prime condition lives on a quotient of the q-torsion
fiber, not on the raw set of nonzero q-torsion points.

At `10^48`, `mixed_depth_valuation_probe.py` validates the repeated-depth
identity against PARI point counts, using `ellcard` only as a diagnostic:

```text
q0=3, q in {5,7,11,13}:
  rows=32, mismatches=0
  ellcard_seconds=3.713, root_depth_seconds=1.512

q0=11, q in {3,5,7,13}:
  rows=32, mismatches=0
  ellcard_seconds=4.351, root_depth_seconds=0.536

Expanded 10^48 validation:

q0=3, q in {5,7,11,13,17,19}:
  rows=720, mismatches=0
  ellcard_seconds=58.613, root_depth_seconds=58.600

q0=11, q in {3,5,7,13,17,19}:
  rows=720, mismatches=0
  ellcard_seconds=59.688, root_depth_seconds=69.190
```

The A-level first-gate oracle also survives a larger `10^48` sample:

```text
q0=3, q in {5,7,11,13}:
  states=150, mismatches=0
  oracle_plus/gate_plus = 32/32, 23/23, 19/19, 11/11

q0=11, q in {3,5,7,13}:
  states=156, mismatches=0
  oracle_plus/gate_plus = 75/75, 41/41, 28/28, 8/8
```

This further narrows the real scaling problem.  For mixed odd primes, one should
compute `v_q(#G)` from partial trace/Frobenius-Smith data, or force it by a trace
congruence, then use chained preimage probes only to produce the final witness.
The only branch that truly needs a first-lift fiber coordinate is the same-prime
`q=q0` depth, where the q0-torsion/coset coordinate can vary over rows with the
same `A`.

There is now a constructive version of the same idea.  Instead of sampling `A`
and asking whether the selected component has q-torsion, sample a candidate
torsion coordinate `x0` and solve

```text
Z_M(A, x0) = 0
```

for the Montgomery parameter `A`, where `Z_M` is the Kummer denominator of
`[M]`.  Keep only roots where `x0` lies on the same signed component as `x=1`
and has exact x-order `M`.  This forces

```text
M | #G
```

on the selected component before any point count.  The prototype is
`forced_torsion_scout.py`.  At `10^48`, after screening the forced roots for a
few additional component gates and point-counting only the top rows:

```text
force M=13:
  starts=120, selected exact roots=67
  elapsed/forced root=0.299s
  best selected-component smooth part among top rows = 45.20 bits

force M=19:
  starts=80, selected exact roots=45
  elapsed/forced root=0.569s
  best selected-component smooth part among top rows = 33.43 bits

force M=23:
  starts=40, selected exact roots=14
  elapsed/forced root=1.952s
  best selected-component smooth part among top rows = 44.47 bits

force M=15:
  starts=120, selected exact roots=62
  elapsed/forced root=0.389s
  best selected-component smooth part among top rows = 45.19 bits

force M=21:
  starts=80, selected exact roots=46
  elapsed/forced root=0.882s
  best selected-component smooth part among top rows = 36.33 bits
```

An inline stress probe showed `M=35` still works but has already jumped to about
`11.2s` of raw solve time per exact selected root before extra screening, so raw
`polrootsmod(Z_M(A,x0))` is not the final large-`M` implementation.  The useful
lesson is more structural: selected-component torsion forcing is much easier
than the earlier composite first-lift solve `x([M]R)=1`.  A scalable version
should use modular-curve/Tate-normal-form parameterizations or a
meet-in-the-middle denominator construction to force a growing smooth divisor
`M`, then use the valuation identity above to extract witnesses.

`forced_torsion_bridge.py` checks that the forced component torsion can actually
be turned into x-only certificate witnesses.  It solves `x([q0]R)=1` on the
forced curves, retains exact first-lift states of order `4*q0`, then asks the
chain combiner to realize the mixed-prime depths.  If `q0 | M`, that factor is
used only to make the first lift available; repeated q0-depth remains the
separate same-prime Smith/fiber problem.  At `10^48`:

```text
force M=13, q0=3:
  starts=120, selected roots=54, first-lift curves=29, first-lift states=58
  best predicted bridge = 17.94 bits
  best combined witness = 21.64 bits
  depths: q5^1 q13^2 q17^1 q19^1

force M=19, q0=3:
  starts=100, selected roots=45, first-lift curves=28, first-lift states=56
  best predicted bridge = 15.62 bits
  best combined witness = 19.41 bits
  depths: q7^1 q19^2 q23^1

force M=23, q0=3:
  starts=70, selected roots=31, first-lift curves=14, first-lift states=28
  best predicted bridge = 12.20 bits
  best combined witness = 12.20 bits

force M=13, q0=11:
  starts=100, selected roots=45, first-lift curves=6, first-lift states=60
  best predicted bridge = 15.87 bits
  best combined witness = 22.10 bits
  depths: q3^2 q5^3 q7^1 q13^1

force M=19, q0=11:
  starts=80, selected roots=33, first-lift curves=5, first-lift states=50
  best predicted bridge = 14.10 bits
  best combined witness = 16.91 bits
```

Every extracted top row completed, so the bridge validates the witness side of
the valuation identity.  The current raw-denominator forcing still underperforms
the best random guided profiles at `10^48`, which reached about `26-27` bits in
similar sample sizes.  The mathematical gain is the decomposition: prescribe a
mixed smooth divisor of `#G`, then separately solve for a first-lift fiber.  The
remaining scaling problem is to prescribe a substantially larger `M` without
solving a huge single `Z_M(A,x0)` polynomial.

There is an even stronger hybrid once a point count is allowed for only the
filtered curves.  After `ellcard` gives the selected component order `N`, one
does not need q-preimage root solving for every prime in the smooth part.  As in
`oneshot.gp`, choose random x-coordinates on the selected side, multiply by the
rough cofactor `N/s`, and strip the B-smooth order using x-only ladders.  This
uses large smooth primes such as `521`, `1543`, and `5953` that are impractical
as preimage-polynomial degrees.

`forced_component_search.py` implements this filtered full-component extractor.
At `10^48`:

```text
force M=13, starts=500, screen q in {3,5,7,11,17,19,23}:
  selected roots=262, point-counted top 24
  best gate score = 18.22 bits
  best component smooth part = 57.96 bits
  best extracted point order = 57.96 bits

force M=13, starts=700, screen q in {3,5,7,11,17}:
  selected roots=356, point-counted top 80
  best gate score = 15.87 bits
  best component smooth part = 57.96 bits
  best extracted point order = 57.96 bits

force M=15, starts=700, screen q in {7,11,13,17,19}:
  selected roots=316, point-counted top 80
  best gate score = 16.42 bits
  best component smooth part = 54.68 bits
  best extracted point order = 54.68 bits
```

This is below the `10^48` one-shot threshold of about 79.7 bits, but it is the
right architecture for scaling: cheap algebraic torsion forcing and gate screens
first, full SEA/point counting only on a filtered shortlist, and x-only
extraction of the entire smooth component order.  It also shows the limitation
of fixed-level forcing: forcing `M=13` or `M=15` buys a constant-factor density
gain, not an asymptotic escape.  The remaining mathematical target is a compact
way to force a growing smooth divisor `M` before the point count.

`forced_torsion_tower.py` tests the most direct compact representation: force a
small base point by `Z_M(A,x)=0`, then grow that same marked point through small
preimage covers `x([q]R)=x(P)` instead of solving a monolithic `Z_{Mq}`.  This
does avoid the large denominator polynomial, but the naive beam is currently
dominated by the fixed-M component filter:

```text
force base M=13, tower q in {3,5,7,11}, 150 starts:
  selected roots=73
  best forced tower order = 16.23 bits
  point-counted top 24
  best component smooth part = 47.46 bits
  best extracted point order = 47.46 bits
  tower root-solving time = 54.77s

force base M=13, tower q in {3,5,7,11,13}:
  partial run reached best forced tower order = 16.03 bits after 88 starts
  elapsed time = 121.7s, then stopped as dominated
```

So "small covers rather than one huge polynomial" is algebraically the right
shape, but not enough by itself.  The missing meet-in-the-middle ingredient is
to combine tower constraints without expanding all branches or repeatedly
calling `polrootsmod` on high-degree x-only preimage equations.

`primary_inverse_source_tradeoff.py` checks whether that missing ingredient
could simply be the inverse-lift degree structure.  For one odd inverse lift,
the equation `x([q]R)=y` has the same degree in `A` as the q-division
denominator:

```text
artifact: artifacts/primary_inverse_source_tradeoff_10e48_10e80_20260629.json

q   deg_A x([q]R)=y   modeled local source degree   alpha=log(degree)/log(q)
2   1                 2                             1.000
3   2                 2                             0.631
5   6                 6                             1.113
7   12                12                            1.277
11  30                30                            1.418
13  42                42                            1.457
```

The single q=2 inverse formula is linear, but a same-A 2-primary tower still
pays a per-level availability cost; q=3 is the only genuinely optimistic odd
case.  Even granting q=3 a local source cost of only `2` per forced factor, the
smooth-tail tradeoff is still worse than random:

```text
10^48:
  random expected work = 10^5.316
  best q=3 primary source = depth 1
  expected work = 10^5.482, overhead = 0.166 log10
  crossing the one-shot threshold needs depth 51 and costs 10.036 log10 worse

10^80:
  random expected work = 10^9.227
  best q=3 primary source = depth 1
  expected work = 10^9.382, overhead = 0.155 log10
  crossing the one-shot threshold needs depth 84 and costs 16.060 log10 worse
```

So an inverse q-primary tower is a useful extraction/local-depth tool, but not
the sub-density source.  A real meet-in-the-middle construction would need to
couple many distinct line/eigenvalue conditions at a cost below the q=3
`2^e` primary benchmark, not merely avoid writing down `Z_{q^e}`.

`component_gate_rescore.py` tests the complementary partial-SEA idea: keep the
cheap fixed-M candidates, but rescore a shortlist using wider first-depth
selected-component q-torsion gates before point counting.  On the
`forced_component_search_10e48_M13_700_top80_q17.json` candidates:

```text
source candidates rescored = 120
extra q-gates = {19,23,29,31}
extra gate time = 90.14s
best wide gate score = 18.22 bits
point-counted top 40 after rescore
best component smooth part = 57.96 bits
best extracted point order = 57.96 bits
```

The 57.96-bit row was only rank 10 by the wide gate score.  Wider first-depth
gates therefore do not solve the ranking problem: the large tails are coming
from q-adic depth and larger smooth primes, not just distinct small q-divisors.

Direct q-power denominator tests are also the wrong representation.  The
expanded x-only denominators grow quickly even before root solving:

```text
Z_9:  degree_x=87,   degree_A=20,  expression chars=6283
Z_25: degree_x=687,  degree_A=156, expression chars=98923
Z_27: degree_x=783,  degree_A=182, expression chars=118687
Z_49: degree_x=2655, degree_A=600, expression chars=616291
```

`component_qadic_tower_probe.py` tests the local alternative: do not build
`Z_{q^e}`; start from selected-component q-torsion roots and repeatedly solve
the small preimage equation `x([q]R)=x(P)`.  On the top 30 rows from the
`M=13` forced-component run at `10^48`, for q in `{3,5,7,11,13}`:

```text
q-rows = 150
component-order mismatches = 0
extracted-order mismatches = 0
total tower time = 16.34s
```

The cost is concentrated in the larger small primes:

```text
q=3:  30 rows, 0.06s total
q=5:  30 rows, 0.40s total
q=7:  30 rows, 1.03s total
q=11: 30 rows, 4.40s total
q=13: 30 rows, 10.45s total
```

So local q-adic towers really recover the selected-component q-primary
exponent, and they are a plausible operational proxy for the Smith invariant
that SEA is computing.  However, using the local exponents as a ranking signal
still does not solve the `10^48` search.  `component_qadic_rescore.py` rescored
120 `M=13` forced-component candidates, ranked by the refined product over
q in `{3,5,7,11,13}`, then point-counted/extracted the top 40:

```text
q-adic rescore time = 87.93s
elapsed time = 109.40s
best q-adic score = 20.92 bits
best component smooth part = 57.96 bits
best extracted point order = 57.96 bits
```

The top q-adic-ranked curve had only a `40.89`-bit smooth component.  The
previous best `57.96`-bit curve stayed in the top 40, but moved from old gate
rank 1 to q-adic rank 12 because its local exponents were just
`3*5*7*11*13`.  Among the extracted top 40, q-adic score correlated with smooth
component size better than first-depth gate score (`0.41` versus `0.27`), but
the improvement is not strong enough to change the dominant rare-tail barrier.

Repeating the same test on the `M=15` forced-component candidates confirms that
this is not just an `M=13` artifact:

```text
artifact: artifacts/component_qadic_rescore_10e48_M15_top120_extract40.json

q-adic rescore time = 35.92s
elapsed time = 57.50s
best q-adic score = 20.67 bits
best component smooth part = 54.68 bits
best extracted point order = 54.68 bits
verified_any = false
```

Here the q-adic score did not correlate with the extracted smooth component
among the top 40 (`0.006`, versus `0.123` for the older first-depth gate
score).  The best smooth row was only q-adic rank 32.  So small-prime q-adic
depth is a correct local invariant, but not a reliable enough global ranking
signal at `10^48`.

The known successful `10^48` curve explains why.  Its selected component has an
81.41-bit smooth part, but the local tower product over `{3,5,7,11,13}` sees
only `2^2 * 3`, or 3.58 bits:

```text
known winning A:
  q=3:  tower_exp=1
  q=5:  tower_exp=0
  q=7:  tower_exp=0
  q=11: tower_exp=0
  q=13: tower_exp=0
```

First-depth tests for the next actual factors are feasible on one curve but
already too expensive for a broad Python/local-cover screen:

```text
q=31: tower_exp=1, time=0.27s
q=41: tower_exp=1, time=0.55s
q=59: tower_exp=1, time=1.18s
```

The mass in the winner comes from larger one-shot factors such as
`31, 41, 59, 139, 991, 7573, 16759, 25523`, not from unusually deep tiny-prime
towers.  A scalable version therefore needs SEA/Frobenius access to these
component divisibility facts, or a way to force the larger residual smooth
factors, rather than more local preimage grinding.

This leaves a sharper SEA target: compute selected-component q-adic valuations
from trace/Frobenius-Smith residues without materializing q^e-division
polynomials.  First-depth q-torsion gates are useful constant-factor filters,
and local q-adic towers are a correct but still expensive way to see small-prime
depth.  The next scalable screen must either compute the same exponents much
more cheaply from SEA residues or start predicting/forcing smooth parts of the
residual component order, especially larger primes beyond the tiny q-tower
range.

So the extraction order should be:

1. Build the A-level Kummer class for each gate.
2. Test whether that class descends to `{A,-A}` / `j`; the raw low-degree
   rational branch-divisor route is now checked through degree 4 and negative.
3. If it descends but raw support is absent, normalize the cover coordinate
   rather than widening ad hoc A/pmA/j bucket searches.
4. Peel off visible signed-cover obstructions such as `chi(A+2)` for `q=2`
   and `chi(A)` for `pmA` failures.
5. For same-prime exceptions, use the recovered `q0`-torsion fiber coordinate:
   the liftable rows are exactly a `q0`-primary Frobenius/Smith kernel line
   when such a line exists.
6. For residual mixed-fiber exceptions not explained by signed covers or
   same-prime torsion lines, add a further first-lift fiber coordinate and
   repeat the class extraction on that cover.

Short fixed-word probes show the descent can persist after conditioning:

```text
F_607, sequence 5 first-lift then 7,2,3:
  depth 1 q=7: A_groups=156, A_mixed=0
  depth 2 q=2: A_groups=9,   A_mixed=0
  depth 3 q=3: A_groups=6,   A_mixed=0

F_863, sequence 5 first-lift then 7,2,3,5:
  depth 1 q=7: A_groups=213, A_mixed=0
  depth 2 q=2: A_groups=93,  A_mixed=0
  depth 3 q=3: A_groups=31,  A_mixed=0
  depth 4 q=5: A_groups=31,  A_mixed=0

F_607, sequence 5 first-lift then 2,3,5,7:
  depth 1 q=2: A_groups=156, A_mixed=0
  depth 2 q=3: A_groups=60,  A_mixed=0
  depth 3 q=5: A_groups=22,  A_mixed=0
  depth 4 q=7: A_groups=22,  A_mixed=0
```

Some low-degree polynomial hits appear in the later depths, but only after the
survivor set has collapsed to very few `A` groups.  Those should be treated as
interpolation artifacts unless they survive larger guard fields and match a
derived divisor class.

This is the most promising mathematical branch now:

```text
Construct a sourceable mixed-prime line/eigenvalue surface: after a guided
first lift, force many conditions "the selected component has a rational
q-torsion line with Frobenius eigenvalue 1" without choosing q-torsion points.
```

The line/eigenvalue cost model is close to density-neutral, unlike raw `X_1`
point forcing.  If successive q-line conditions can be represented as
pullbacks, translates, coboundaries, Hecke/eigenvalue constraints, or iterates
of a small normalized Kummer/divisor class, then we have a way to force many
mixed-prime gates by choosing a sourceable class condition rather than by
random branching.  If no such representation exists, the route collapses back
to independent trace congruence tests and loses its practical advantage.

## Live Frontier After 10^48 Tests

The current evidence now has one live proof-shape candidate, one missing
mathematical primitive, and two support tracks:

0. **Aggregate Hasse-window certificates:** replace the single
   `m > sqrt(n)` point-order threshold with many moderate smooth point orders
   whose Hasse-window intersection rules out every `q <= sqrt(n)`.  This is the
   first model in the thread with an apparent exponent-level improvement at
   `10^80`: the vectorized geometric panel has median aggregate hit `90,843`
   sampled SEA counts versus the current two-sided one-shot expectation
   `10^8.926`.  The lcm/window surplus is only an expected-survivor criterion,
   but the actual deterministic interval-intersection verifier now exists and
   verifies end-to-end aggregate certificates at `10^20`, `10^30`, and
   `10^49`.  The `10^49 + 9` run found a verified certificate in 256 curves and
   97.23 seconds; its minimized four point orders have `68.21`, `49.97`,
   `48.80`, and `48.66` bits, all below the `81.39`-bit one-shot threshold.
   The remaining make-or-break task is to make the residue-intersection proof
   memory-stable at high range and to confirm that point-exponent extraction
   does not erase the model's surplus.  Subject to those checks, this is now
   the main scaling route.

1. **True scaling primitive:** construct a large-discriminant isogeny class, or
   an equivalent marked torsion point, at far below class-number/generic
   modular-curve cost.  This includes any sourceable Kummer/divisor-class
   relation that couples many selected gates.  The exact `10^e` dream order
   shows why this would solve the problem immediately, but also prices the
   obstacle: the `10^80` dream trace already has about a `125`-bit class-number
   scale.  For fixed trace-residue products, the source must be sub-density:
   around `M^0.26` or cheaper at `10^80` against the real two-sided
   curve/twist baseline, not `M`, because the random smooth-tail budget is much
   smaller than the forced product.  Trace-CRT selection is the clean
   quotient-level version of this idea, but by itself it still needs class
   scale essentially `M`; at the `10^80` crossing it misses the source budget
   by about `100` bits against the two-sided baseline.  Adding
   CM square/conductor congruences does not repair this: in the trace-square
   entropy model, the first forced square prime at
   `10^80` increases the class-scale gap from `99.489` to `105.257` bits.
   Direct easy-CM scans through `D <= 10^6` also have no threshold crossings:
   the best represented order has `65` smooth bits at `10^48` and `86` at
   `10^80`, below thresholds `79.73` and `132.88`.  A
   direct `10^48` smooth-order/discriminant correlation probe also demotes the
   hope that the smooth Hasse tail naturally has smaller CM core: the top 500
   smooth orders from a 200k stream have class-scale median `79.40` bits,
   essentially the same as the uniform reservoir's `79.69` bits, and the two
   one-shot successes sit at `79.72` and `80.71` class bits.
   The point-exponent calibration also fails to expose hidden scaling slack:
   a 200k `10^48` Hasse-order sample had the same `1/200000` hit count after
   pessimistically removing every smooth factor that could split into the first
   group invariant, and the known certificate merely loses one factor of `2`
   from component smooth part to actual point order.
2. **Novelty diagnostic:** keep testing proposed coupled sources against the
   independent line-hit model and the broad menu-prefilter baseline.  A real
   source should push observed products far beyond the independent p99 tail and
   improve end-to-end extracted smooth bits per second by more than the current
   constant-factor local screens.  Fixed line products and ordinary guided
   first-lift sampling failed the high-tail test at `10^48`; the broad line
   menu is useful by about `1.6-2.0x`, same-prime q-depth by about `1.5-2.4x`
   against the two-sided baseline, and the static mixed valuation-vector screen
   by about `5-6.5x` in the current models.
   Cross-range extrapolation keeps the mixed-profile benefit near `10^1.0` at
   `10^80` with measured costs, and below `10^1.9` even if the profile is
   almost free.  A direct `10^48` mixed-profile-plus-SEA shortlist test reached
   `45.87` extracted smooth bits in the top 80 q0=11 rows, and the streaming
   q0=11 profile-prefilter driver validates a `1.019` log10 (`~10.5x`) modeled
   speedup against the two-sided 2.6s random full-SEA baseline.  A fresh q0=3
   streaming panel reached `47.73` extracted smooth bits and `0.851` log10
   (`~7.1x`) modeled speedup.  Both still fall far below the `79.73`-bit one-shot
   threshold.  An ideal free medium-prime menu through q<=251 adds only another
   `0.625` log10 over profile-only in the q0=11 panel and `0.318` log10 in the
   q0=3 panel, while the real q=17..73 division-polynomial menu is `0.355`
   log10 worse than q0=11 profile-only and `0.339` log10 worse than q0=3
   profile-only when charged at measured cost.  SEA-prefix safe-abort
   feasibility is also weak with the current record stream: in the
   known-winner-plus-random80 replay, even all stored prefix records leave a
   median `10^5.7` expected Hasse-compatible smooth witnesses and zero sampled
   rows below one expected witness.  Known profile
   torsion also lowers the natural SEA horizon to median auxiliary max `61`,
   leaving the best accepted row only `23.27` visible bits at horizon despite
   `43.77` actual component smoothness.  Grouping all q0=11 first-lift roots by
   their source `x0` does not make q=17,23,31 gates family-level events: the
   observed hit rates are near random and all multi-root hit families are mixed.
   The p27-inspired marked-point sheet coordinate `B1` is also demoted:
   10^48 train/holdout buckets stay in the weak constant-factor regime, and
   guard-field exact branch support on `B1` has zero degree-4 hits.
   The inverse q-primary tower is demoted as a standalone source too: the only
   favorable odd local degree is q=3 with cost `2` per forced factor, but the
   10^48 and 10^80 tradeoff optima are still one forced factor and remain
   `0.166` and `0.155` log10 worse than random, respectively.
   The natural A-line recurrence family is now checked too: Dickson/Chebyshev
   maps through degree 12, with S3 branch-set conjugation, have only the stable
   q=3 self-symmetry and no exact cross-prime/product-growing relation.
   Exact small-field enumeration of the raw selected-component `A` family also
   fails the high-tail test: for p=10007 and gates 3,5,7,11 the best observed
   product is `7.852` bits, below the random-order interval null at `8.589`
   bits.
   Those are now the engineering baselines a mathematical source has to beat.
3. **Engineering track:** smoothness-aware partial SEA and forced-component
   extraction can improve constants, especially by avoiding full point counts
   for hopeless curves.  The q0=11 profile-prefilter is now a concrete version
   of this track.  Medium-prime selected-component gates are the right next
   observable, but not via one-q-at-a-time division polynomials or by asking SEA
   to continue long after the trace is known.  This track is useful for pushing
   the range, but it does not change the random smooth-tail exponent unless
   paired with the first primitive.

So the next serious mathematical test should not be another raw bucket search
over `A`, `j`, or small visible characters.  It should produce a normalized
cover/class object, or a trace-residue construction primitive, and answer one
of two questions:

- does this object construct many trace congruences together for less than the
  product of their independent costs?
- does this object construct the marked point/order directly, without walking
  the generic `X_1(M)` tower?

[pari-ellsea]: https://pari.math.u-bordeaux.fr/dochtml/ref-stable/Elliptic_curves.html#ellsea
[danger3]: https://github.com/AndrewVSutherland/DANGER3/blob/main/README.md
[danger2026-research]: https://github.com/alexamclain/Danger2026DataChallenge/tree/main/research
[danger2026-p23-frontier]: https://github.com/alexamclain/Danger2026DataChallenge/blob/main/research/p23/p23_true_subsqrt_scaling_frontier_20260602.md
[danger2026-p25-practical]: https://github.com/alexamclain/Danger2026DataChallenge/blob/main/research/p25/lanes/practical-search.md
[danger2026-p26-gpu]: https://github.com/alexamclain/Danger2026DataChallenge/blob/main/research/p26/gpu-throughput-report_20260620.md
[danger2026-p27-frontier]: https://github.com/alexamclain/Danger2026DataChallenge/blob/main/research/p27/frontier.md
[danger2026-p27-a-level]: https://github.com/alexamclain/Danger2026DataChallenge/blob/main/research/p27/evidence/p27_a_level_kummer_extraction_packet_20260622.md
