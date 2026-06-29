#!/usr/bin/env python3
"""Vectorized geometric model for aggregate Hasse-window filters.

This estimates the rare-event scaling of a possible aggregate certificate
shape.  It is not itself a deterministic verifier: after the lcm/window
surplus turns positive, a real proof still needs an efficient way to certify
that no small divisor of n lies in the surviving modular-window intersection.

Run with the bundled runtime if the default Python lacks NumPy:

    /Users/agent/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
      aggregate_hasse_numpy_model.py 80
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Iterable, Optional

import numpy as np

from smooth_tail_estimate import primes_upto


@dataclass(frozen=True)
class AcceptedCandidate:
    sea_count: int
    side: str
    smooth_part: int
    smooth_bits: float
    new_lcm_bits: float
    surplus_gain_bits: float
    prime_count: int


@dataclass(frozen=True)
class NumpyRun:
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


def positive_int(value: str) -> int:
    out = int(value, 0)
    if out <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return out


def one_shot_bound(p: int) -> int:
    sp = math.isqrt(p)
    return sp + 1 + math.isqrt(4 * sp)


def fourth_root_floor(value: int) -> int:
    return math.isqrt(math.isqrt(value))


def aggregate_window(p: int) -> int:
    return 4 * fourth_root_floor(p) + 3


def lcm_bits_from_exponents(exponents: dict[int, int]) -> float:
    return sum(exp * math.log2(q) for q, exp in exponents.items())


def update_lcm_exponents(current: dict[int, int], factors: dict[int, int]) -> dict[int, int]:
    out = dict(current)
    for q, exp in factors.items():
        if exp > out.get(q, 0):
            out[q] = exp
    return out


def is_probable_prime(n: int) -> bool:
    if n < 2:
        return False
    small_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]
    for q in small_primes:
        if n == q:
            return True
        if n % q == 0:
            return False
    d = n - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
    for a in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43]:
        if a >= n:
            continue
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(s - 1):
            x = (x * x) % n
            if x == n - 1:
                break
        else:
            return False
    return True


def next_prime_after_power(exponent: int) -> tuple[int, int]:
    base = 10**exponent
    candidate = base + 1
    if candidate % 2 == 0:
        candidate += 1
    while not is_probable_prime(candidate):
        candidate += 2
    return candidate, candidate - base


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NumPy geometric model for aggregate Hasse certificates.")
    parser.add_argument("exponents", nargs="*", type=nonnegative_int, default=[80])
    parser.add_argument("--prime", type=positive_int)
    parser.add_argument("--samples", type=positive_int, default=1_000_000)
    parser.add_argument("--repetitions", type=positive_int, default=20)
    parser.add_argument("--batch-sea", type=positive_int, default=512)
    parser.add_argument("--seed", type=int, default=20260815)
    parser.add_argument("--stack-mb", type=positive_int, default=128)
    parser.add_argument("--export-json", type=Path)
    return parser.parse_args(list(argv) if argv is not None else None)


def factors_from_hit_row(
    rng: np.random.Generator,
    row: np.ndarray,
    primes: list[int],
    log_primes: list[float],
) -> tuple[dict[int, int], float]:
    indices = np.flatnonzero(row)
    factors: dict[int, int] = {}
    bits = 0.0
    for index in indices:
        q = primes[int(index)]
        exp = 1
        bits += log_primes[int(index)]
        inv = 1.0 / q
        while rng.random() < inv:
            exp += 1
            bits += log_primes[int(index)]
        factors[q] = exp
    return factors, bits


def candidate_from_factors(
    sea_count: int,
    side: str,
    factors: dict[int, int],
    smooth_bits: float,
    lcm_exponents: dict[int, int],
    lcm_bits: float,
    window_bits: float,
) -> AcceptedCandidate:
    new_exponents = update_lcm_exponents(lcm_exponents, factors)
    new_bits = lcm_bits_from_exponents(new_exponents)
    smooth_part = 1
    for q, exp in factors.items():
        smooth_part *= q**exp
    return AcceptedCandidate(
        sea_count=sea_count,
        side=side,
        smooth_part=smooth_part,
        smooth_bits=smooth_bits,
        new_lcm_bits=new_bits,
        surplus_gain_bits=(new_bits - lcm_bits) - window_bits,
        prime_count=len(factors),
    )


def simulate(
    p: int,
    primes: list[int],
    samples: int,
    seed: int,
    repetition: int,
    batch_sea: int,
) -> NumpyRun:
    rng = np.random.default_rng(seed)
    log_primes = [math.log2(q) for q in primes]
    prime_array = np.array(primes, dtype=np.float64)
    inv_array = 1.0 / prime_array
    log_array = np.array(log_primes, dtype=np.float64)
    threshold_bits = math.log2(one_shot_bound(p))
    window_bits = math.log2(aggregate_window(p))
    required_surplus_bits = math.log2(math.isqrt(p) + 1)

    lcm_exponents: dict[int, int] = {}
    lcm_bits = 0.0
    accepted: list[AcceptedCandidate] = []
    one_shot_hit_at: Optional[int] = None
    aggregate_hit_at: Optional[int] = None
    best_smooth_bits = 0.0
    sea_count = 0
    started = perf_counter()

    while sea_count < samples:
        current_batch = min(batch_sea, samples - sea_count)
        component_count = 2 * current_batch
        hits = rng.random((component_count, len(primes))) < inv_array
        squarefree_bits = hits @ log_array
        best_smooth_bits = max(best_smooth_bits, float(squarefree_bits.max(initial=0.0)))

        for local_sea in range(current_batch):
            global_sea = sea_count + local_sea + 1
            rich: list[tuple[AcceptedCandidate, dict[int, int]]] = []
            for side_index, side in enumerate(("curve", "twist")):
                row_index = 2 * local_sea + side_index
                approx_bits = float(squarefree_bits[row_index])
                if one_shot_hit_at is None and approx_bits > threshold_bits:
                    one_shot_hit_at = global_sea
                if approx_bits <= window_bits:
                    continue
                factors, smooth_bits = factors_from_hit_row(rng, hits[row_index], primes, log_primes)
                best_smooth_bits = max(best_smooth_bits, smooth_bits)
                if one_shot_hit_at is None and smooth_bits > threshold_bits:
                    one_shot_hit_at = global_sea
                candidate = candidate_from_factors(
                    global_sea, side, factors, smooth_bits, lcm_exponents, lcm_bits, window_bits
                )
                rich.append((candidate, factors))
            rich.sort(key=lambda item: item[0].surplus_gain_bits, reverse=True)
            for candidate, factors in rich:
                refreshed = candidate_from_factors(
                    candidate.sea_count,
                    candidate.side,
                    factors,
                    candidate.smooth_bits,
                    lcm_exponents,
                    lcm_bits,
                    window_bits,
                )
                if refreshed.surplus_gain_bits <= 0:
                    continue
                lcm_exponents = update_lcm_exponents(lcm_exponents, factors)
                lcm_bits = lcm_bits_from_exponents(lcm_exponents)
                accepted.append(refreshed)
            if lcm_bits - len(accepted) * window_bits > required_surplus_bits:
                aggregate_hit_at = global_sea
                sea_count = global_sea
                break
        else:
            sea_count += current_batch
            continue
        break

    return NumpyRun(
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
    panels = []
    for exponent in args.exponents:
        p, gap = next_prime_after_power(exponent)
        primes = primes_upto(p.bit_length() * p.bit_length())
        runs = []
        for repetition in range(args.repetitions):
            run = simulate(
                p,
                primes,
                args.samples,
                args.seed + 1_000_003 * repetition,
                repetition,
                args.batch_sea,
            )
            runs.append(run)
            print(
                "summary "
                f"target=10^{exponent} rep={repetition} sea_counts={run.sea_counts} "
                f"aggregate_hit_at={run.aggregate_hit_at} one_shot_hit_at={run.one_shot_hit_at} "
                f"components={run.aggregate_components} surplus={run.aggregate_surplus_bits:.2f}/"
                f"{run.aggregate_required_surplus_bits:.2f} best_smooth_bits={run.best_smooth_bits:.2f} "
                f"elapsed_seconds={run.elapsed_seconds:.2f}",
                flush=True,
            )
        hits = [run.aggregate_hit_at for run in runs if run.aggregate_hit_at is not None]
        hits_sorted = sorted(hits)
        panel = {
            "target": {
                "exponent": exponent,
                "p": p,
                "gap": gap,
                "bitlength": p.bit_length(),
                "smoothness_bound": p.bit_length() * p.bit_length(),
                "smooth_prime_count": len(primes),
            },
            "runs": [asdict(run) for run in runs],
            "panel": {
                "repetitions": args.repetitions,
                "samples": args.samples,
                "aggregate_hits": len(hits),
                "one_shot_hits": sum(run.one_shot_hit_at is not None for run in runs),
                "aggregate_median_hit": hits_sorted[len(hits_sorted) // 2] if hits_sorted else None,
                "aggregate_min_hit": min(hits) if hits else None,
                "aggregate_max_hit": max(hits) if hits else None,
            },
        }
        panels.append(panel)
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
        args.export_json.write_text(json.dumps({"panels": panels}, indent=2, sort_keys=True) + "\n")
        print(f"export_json = {args.export_json}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
