#!/usr/bin/env python3
"""Fast geometric-valuation model for aggregate Hasse-window filters.

This is a scaling model, not a complete certificate verifier.  The aggregate
surplus condition estimates when the expected number of small prime divisors
surviving all Hasse-window congruences falls below one; a deterministic proof
would still need to certify the remaining residue intersection.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Iterable, Optional, Sequence

from cypari2 import Pari

from aggregate_hasse_certificate_model import aggregate_window, lcm_bits_from_exponents, update_lcm_exponents
from cm_search_oneshot import resolve_target
from mixed_prime_lift import positive_int
from smooth_tail_estimate import one_shot_bound, primes_upto


@dataclass(frozen=True)
class AcceptedCandidate:
    sea_count: int
    side: str
    smooth_bits: float
    new_lcm_bits: float
    surplus_gain_bits: float
    prime_count: int


@dataclass(frozen=True)
class GeometricRun:
    repetition: int
    sea_counts: int
    aggregate_hit_at: Optional[int]
    one_shot_hit_at: Optional[int]
    aggregate_components: int
    aggregate_lcm_bits: float
    aggregate_surplus_bits: float
    aggregate_required_surplus_bits: float
    window_bits: float
    one_shot_bound_bits: float
    best_smooth_bits: float
    accepted_candidates: list[AcceptedCandidate]
    elapsed_seconds: float


def nonnegative_int(value: str) -> int:
    out = int(value, 0)
    if out < 0:
        raise argparse.ArgumentTypeError("must be nonnegative")
    return out


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Geometric model for aggregate Hasse certificates.")
    parser.add_argument("exponents", nargs="*", type=nonnegative_int, default=[80])
    parser.add_argument("--prime", type=positive_int)
    parser.add_argument("--samples", type=positive_int, default=1_000_000)
    parser.add_argument("--repetitions", type=positive_int, default=20)
    parser.add_argument("--seed", type=int, default=20260814)
    parser.add_argument("--stack-mb", type=positive_int, default=128)
    parser.add_argument("--export-json", type=Path)
    return parser.parse_args(list(argv) if argv is not None else None)


def sample_component(
    rng: random.Random,
    primes: Sequence[int],
    log_primes: Sequence[float],
) -> tuple[dict[int, int], float]:
    factors: dict[int, int] = {}
    bits = 0.0
    for q, logq in zip(primes, log_primes):
        inv = 1.0 / q
        if rng.random() >= inv:
            continue
        exp = 1
        bits += logq
        while rng.random() < inv:
            exp += 1
            bits += logq
        factors[q] = exp
    return factors, bits


def simulate(
    p: int,
    primes: Sequence[int],
    log_primes: Sequence[float],
    samples: int,
    seed: int,
    repetition: int,
) -> GeometricRun:
    rng = random.Random(seed)
    threshold_bits = math.log2(one_shot_bound(p))
    window_bits = math.log2(aggregate_window(p))
    required_surplus_bits = math.log2(math.isqrt(p) + 1)
    lcm_exponents: dict[int, int] = {}
    lcm_bits = 0.0
    accepted: list[AcceptedCandidate] = []
    best_smooth_bits = 0.0
    one_shot_hit_at: Optional[int] = None
    aggregate_hit_at: Optional[int] = None
    started = perf_counter()

    for sea_count in range(1, samples + 1):
        rich: list[tuple[AcceptedCandidate, dict[int, int]]] = []
        for side in ("curve", "twist"):
            factors, smooth_bits = sample_component(rng, primes, log_primes)
            best_smooth_bits = max(best_smooth_bits, smooth_bits)
            if one_shot_hit_at is None and smooth_bits > threshold_bits:
                one_shot_hit_at = sea_count
            new_exponents = update_lcm_exponents(lcm_exponents, factors)
            new_bits = lcm_bits_from_exponents(new_exponents)
            rich.append(
                (
                    AcceptedCandidate(
                        sea_count=sea_count,
                        side=side,
                        smooth_bits=smooth_bits,
                        new_lcm_bits=new_bits,
                        surplus_gain_bits=(new_bits - lcm_bits) - window_bits,
                        prime_count=len(factors),
                    ),
                    factors,
                )
            )
        rich.sort(key=lambda item: item[0].surplus_gain_bits, reverse=True)
        for candidate, factors in rich:
            if candidate.surplus_gain_bits <= 0:
                continue
            lcm_exponents = update_lcm_exponents(lcm_exponents, factors)
            lcm_bits = lcm_bits_from_exponents(lcm_exponents)
            accepted.append(candidate)
        if lcm_bits - len(accepted) * window_bits > required_surplus_bits:
            aggregate_hit_at = sea_count
            break

    return GeometricRun(
        repetition=repetition,
        sea_counts=sea_count,
        aggregate_hit_at=aggregate_hit_at,
        one_shot_hit_at=one_shot_hit_at,
        aggregate_components=len(accepted),
        aggregate_lcm_bits=lcm_bits,
        aggregate_surplus_bits=lcm_bits - len(accepted) * window_bits,
        aggregate_required_surplus_bits=required_surplus_bits,
        window_bits=window_bits,
        one_shot_bound_bits=threshold_bits,
        best_smooth_bits=best_smooth_bits,
        accepted_candidates=accepted,
        elapsed_seconds=perf_counter() - started,
    )


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    pari = Pari()
    pari.allocatemem(args.stack_mb * 1024 * 1024, silent=True)
    runs = []
    for exponent in args.exponents:
        class Args:
            pass

        target_args = Args()
        target_args.exponent = exponent
        target_args.prime = None
        target = resolve_target(pari, target_args)
        p = target.p
        primes = primes_upto(p.bit_length() * p.bit_length())
        log_primes = [math.log2(q) for q in primes]
        target_runs = []
        for repetition in range(args.repetitions):
            run = simulate(p, primes, log_primes, args.samples, args.seed + 1_000_003 * repetition, repetition)
            target_runs.append(run)
            print(
                "summary "
                f"target=10^{exponent} rep={repetition} sea_counts={run.sea_counts} "
                f"aggregate_hit_at={run.aggregate_hit_at} one_shot_hit_at={run.one_shot_hit_at} "
                f"components={run.aggregate_components} surplus={run.aggregate_surplus_bits:.2f}/"
                f"{run.aggregate_required_surplus_bits:.2f} best_smooth_bits={run.best_smooth_bits:.2f} "
                f"elapsed_seconds={run.elapsed_seconds:.2f}",
                flush=True,
            )
        hits = [run.aggregate_hit_at for run in target_runs if run.aggregate_hit_at is not None]
        hits_sorted = sorted(hits)
        panel = {
            "target": {
                "exponent": exponent,
                "p": p,
                "gap": target.gap,
                "bitlength": p.bit_length(),
                "smoothness_bound": p.bit_length() * p.bit_length(),
                "smooth_prime_count": len(primes),
            },
            "runs": [asdict(run) for run in target_runs],
            "panel": {
                "repetitions": args.repetitions,
                "aggregate_hits": len(hits),
                "one_shot_hits": sum(run.one_shot_hit_at is not None for run in target_runs),
                "aggregate_median_hit": hits_sorted[len(hits_sorted) // 2] if hits_sorted else None,
                "aggregate_min_hit": min(hits) if hits else None,
                "aggregate_max_hit": max(hits) if hits else None,
            },
        }
        runs.append(panel)
        print(
            "aggregate_panel "
            f"target=10^{exponent} reps={args.repetitions} aggregate_hits={len(hits)} "
            f"one_shot_hits={panel['panel']['one_shot_hits']} "
            f"median={panel['panel']['aggregate_median_hit']} min={panel['panel']['aggregate_min_hit']} "
            f"max={panel['panel']['aggregate_max_hit']}",
            flush=True,
        )

    if args.export_json:
        args.export_json.parent.mkdir(parents=True, exist_ok=True)
        args.export_json.write_text(json.dumps({"panels": runs}, indent=2, sort_keys=True) + "\n")
        print(f"export_json = {args.export_json}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
