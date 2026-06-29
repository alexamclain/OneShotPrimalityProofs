#!/usr/bin/env python3
"""Model aggregate Hasse-window filters from several smaller point orders.

The current verifier proves primality from one point whose exact smooth order
``m`` exceeds the largest possible elliptic-curve group order over any
``q <= sqrt(n)``.  This script tests a possible generalized proof shape:

For each certified point order m_i on a curve over Z/n, any prime q | n must
satisfy

    #E_i(F_q) = k_i m_i
    |#E_i(F_q) - (q + 1)| <= 2 sqrt(q).

Thus q + 1 lies in a Hasse-width window modulo each m_i.  If M = lcm(m_i), and
W = floor(4*n^(1/4)) + 3 bounds the number of allowed residues per m_i, then
the random-density estimate for possible q <= sqrt(n) is roughly

    (sqrt(n) + 1) * W^r / M

possible q values after r independent order facts.  The heuristic aggregate
target is therefore

    lcm(m_i) > (sqrt(n) + 1) * W^r.

Equivalently, the accumulated "surplus"

    log2(lcm(m_i)) - r*log2(W)

must exceed log2(sqrt(n)+1).

This inequality is not, by itself, a deterministic primality certificate: a
small interval can still contain a residue class even when its expected density
is tiny.  A real aggregate verifier would need to enumerate the surviving
Hasse-window residue intersection, or verify an auxiliary certificate that this
intersection contains no divisor of n.  The model is still useful because it
tests whether the rare-event scaling is promising enough to justify building
that residue-intersection verifier.

This is only a model for now: it assumes the B-smooth part of a sampled
component order can be extracted as a point order, and it would require a
generalized verifier that checks several exact point orders plus a deterministic
residue-intersection emptiness or gcd check.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Iterable, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cypari2 import Pari

from cm_search_oneshot import resolve_target
from smooth_tail_estimate import one_shot_bound, primes_upto


@dataclass(frozen=True)
class Candidate:
    sea_count: int
    side: str
    order: int
    smooth_part: int
    smooth_bits: float
    factors: dict[int, int]
    new_lcm_bits: float
    surplus_gain_bits: float


@dataclass(frozen=True)
class TrialSummary:
    samples: int
    sea_counts: int
    one_shot_hit_at: Optional[int]
    aggregate_hit_at: Optional[int]
    aggregate_components: int
    aggregate_lcm_bits: float
    aggregate_surplus_bits: float
    aggregate_required_surplus_bits: float
    window_bits: float
    one_shot_bound_bits: float
    accepted_candidates: list[Candidate]
    best_smooth_bits: float
    elapsed_seconds: float


def nonnegative_int(value: str) -> int:
    out = int(value, 0)
    if out < 0:
        raise argparse.ArgumentTypeError("must be nonnegative")
    return out


def positive_int(value: str) -> int:
    out = int(value, 0)
    if out <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return out


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Model aggregate Hasse-window certificates.")
    parser.add_argument("exponents", nargs="*", type=nonnegative_int, default=[48])
    parser.add_argument("--prime", type=positive_int)
    parser.add_argument("--samples", type=positive_int, default=200_000)
    parser.add_argument("--repetitions", type=positive_int, default=1)
    parser.add_argument("--seed", type=int, default=20260813)
    parser.add_argument("--stack-mb", type=positive_int, default=128)
    parser.add_argument("--export-json", type=Path)
    return parser.parse_args(list(argv) if argv is not None else None)


def smooth_factorization(value: int, primes: Sequence[int]) -> tuple[int, dict[int, int]]:
    rest = value
    smooth = 1
    factors: dict[int, int] = {}
    for q in primes:
        exp = 0
        while rest % q == 0:
            rest //= q
            smooth *= q
            exp += 1
        if exp:
            factors[q] = exp
    return smooth, factors


def lcm_bits_from_exponents(exponents: dict[int, int]) -> float:
    return sum(exp * math.log2(q) for q, exp in exponents.items())


def update_lcm_exponents(current: dict[int, int], factors: dict[int, int]) -> dict[int, int]:
    out = dict(current)
    for q, exp in factors.items():
        if exp > out.get(q, 0):
            out[q] = exp
    return out


def hasse_radius(p: int) -> int:
    return math.isqrt(4 * p)


def fourth_root_floor(value: int) -> int:
    return math.isqrt(math.isqrt(value))


def aggregate_window(p: int) -> int:
    # 4*n^(1/4) plus a small integer cushion for flooring and inclusive endpoints.
    return 4 * fourth_root_floor(p) + 3


def try_candidate(
    sea_count: int,
    side: str,
    order: int,
    smooth_primes: Sequence[int],
    lcm_exponents: dict[int, int],
    lcm_bits: float,
    window_bits: float,
) -> Candidate:
    smooth, factors = smooth_factorization(order, smooth_primes)
    new_exponents = update_lcm_exponents(lcm_exponents, factors)
    new_bits = lcm_bits_from_exponents(new_exponents)
    smooth_bits = math.log2(smooth)
    return Candidate(
        sea_count=sea_count,
        side=side,
        order=order,
        smooth_part=smooth,
        smooth_bits=smooth_bits,
        factors=factors,
        new_lcm_bits=new_bits,
        surplus_gain_bits=(new_bits - lcm_bits) - window_bits,
    )


def simulate_target(pari: Pari, exponent: Optional[int], prime: Optional[int], samples: int, seed: int) -> dict:
    class Args:
        pass

    args = Args()
    args.exponent = exponent
    args.prime = prime
    target = resolve_target(pari, args)
    p = target.p
    smooth_primes = primes_upto(p.bit_length() * p.bit_length())
    one_shot_threshold = one_shot_bound(p)
    one_shot_bound_bits = math.log2(one_shot_threshold)
    window = aggregate_window(p)
    window_bits = math.log2(window)
    required_surplus_bits = math.log2(math.isqrt(p) + 1)
    radius = hasse_radius(p)
    rng = random.Random(seed)

    started = perf_counter()
    lcm_exponents: dict[int, int] = {}
    lcm_bits = 0.0
    accepted: list[Candidate] = []
    one_shot_hit_at: Optional[int] = None
    aggregate_hit_at: Optional[int] = None
    best_smooth_bits = 0.0

    for sea_count in range(1, samples + 1):
        trace = rng.randrange(-radius, radius + 1)
        component_orders = [
            ("curve", p + 1 - trace),
            ("twist", p + 1 + trace),
        ]
        candidates = [
            try_candidate(sea_count, side, order, smooth_primes, lcm_exponents, lcm_bits, window_bits)
            for side, order in component_orders
        ]
        best_smooth_bits = max(best_smooth_bits, *(candidate.smooth_bits for candidate in candidates))
        if one_shot_hit_at is None and any(candidate.smooth_part > one_shot_threshold for candidate in candidates):
            one_shot_hit_at = sea_count
        candidates.sort(key=lambda item: item.surplus_gain_bits, reverse=True)
        for candidate in candidates:
            if candidate.surplus_gain_bits <= 0:
                continue
            lcm_exponents = update_lcm_exponents(lcm_exponents, candidate.factors)
            lcm_bits = lcm_bits_from_exponents(lcm_exponents)
            accepted.append(candidate)
        if aggregate_hit_at is None and lcm_bits - len(accepted) * window_bits > required_surplus_bits:
            aggregate_hit_at = sea_count
            break

    elapsed = perf_counter() - started
    summary = TrialSummary(
        samples=samples,
        sea_counts=sea_count,
        one_shot_hit_at=one_shot_hit_at,
        aggregate_hit_at=aggregate_hit_at,
        aggregate_components=len(accepted),
        aggregate_lcm_bits=lcm_bits,
        aggregate_surplus_bits=lcm_bits - len(accepted) * window_bits,
        aggregate_required_surplus_bits=required_surplus_bits,
        window_bits=window_bits,
        one_shot_bound_bits=one_shot_bound_bits,
        accepted_candidates=accepted,
        best_smooth_bits=best_smooth_bits,
        elapsed_seconds=elapsed,
    )
    return {
        "target": {
            "exponent": exponent,
            "p": p,
            "gap": target.gap,
            "bitlength": p.bit_length(),
            "smoothness_bound": p.bit_length() * p.bit_length(),
            "smooth_prime_count": len(smooth_primes),
        },
        "summary": asdict(summary),
    }


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    pari = Pari()
    pari.allocatemem(args.stack_mb * 1024 * 1024, silent=True)
    runs = []
    for exponent in args.exponents:
        for repetition in range(args.repetitions):
            run = simulate_target(pari, exponent, None, args.samples, args.seed + 1_000_003 * repetition)
            run["repetition"] = repetition
            runs.append(run)
    if args.prime is not None:
        for repetition in range(args.repetitions):
            run = simulate_target(pari, None, args.prime, args.samples, args.seed + 1_000_003 * repetition)
            run["repetition"] = repetition
            runs.append(run)

    for run in runs:
        target = run["target"]
        summary = run["summary"]
        label = f"10^{target['exponent']}" if target["exponent"] is not None else "custom"
        print(
            "summary "
            f"target={label} rep={run.get('repetition', 0)} bits={target['bitlength']} samples={summary['samples']} "
            f"sea_counts={summary['sea_counts']} "
            f"one_shot_hit_at={summary['one_shot_hit_at']} "
            f"aggregate_hit_at={summary['aggregate_hit_at']} "
            f"components={summary['aggregate_components']} "
            f"lcm_bits={summary['aggregate_lcm_bits']:.2f} "
            f"surplus_bits={summary['aggregate_surplus_bits']:.2f}/"
            f"{summary['aggregate_required_surplus_bits']:.2f} "
            f"window_bits={summary['window_bits']:.2f} "
            f"best_smooth_bits={summary['best_smooth_bits']:.2f} "
            f"elapsed_seconds={summary['elapsed_seconds']:.2f}",
            flush=True,
        )
        for index, candidate in enumerate(summary["accepted_candidates"][:12], start=1):
            print(
                "accepted "
                f"rank={index} sea={candidate['sea_count']} side={candidate['side']} "
                f"smooth_bits={candidate['smooth_bits']:.2f} "
                f"new_lcm_bits={candidate['new_lcm_bits']:.2f} "
                f"surplus_gain={candidate['surplus_gain_bits']:.2f}",
                flush=True,
            )

    by_label: dict[str, list[dict]] = {}
    for run in runs:
        target = run["target"]
        label = f"10^{target['exponent']}" if target["exponent"] is not None else "custom"
        by_label.setdefault(label, []).append(run["summary"])
    for label, summaries in by_label.items():
        aggregate_hits = [row["aggregate_hit_at"] for row in summaries if row["aggregate_hit_at"] is not None]
        one_shot_hits = [row["one_shot_hit_at"] for row in summaries if row["one_shot_hit_at"] is not None]
        if aggregate_hits:
            aggregate_hits_sorted = sorted(aggregate_hits)
            median_hit = aggregate_hits_sorted[len(aggregate_hits_sorted) // 2]
        else:
            median_hit = None
        print(
            "aggregate_panel "
            f"target={label} reps={len(summaries)} "
            f"aggregate_hits={len(aggregate_hits)} one_shot_hits={len(one_shot_hits)} "
            f"aggregate_median_hit={median_hit} "
            f"aggregate_min_hit={min(aggregate_hits) if aggregate_hits else None} "
            f"aggregate_max_hit={max(aggregate_hits) if aggregate_hits else None}",
            flush=True,
        )

    if args.export_json:
        args.export_json.parent.mkdir(parents=True, exist_ok=True)
        args.export_json.write_text(json.dumps({"runs": runs}, indent=2, sort_keys=True) + "\n")
        print(f"export_json = {args.export_json}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
