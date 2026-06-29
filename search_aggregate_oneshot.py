#!/usr/bin/env python3
"""Search for aggregate one-shot ECPP certificates.

This is a prototype for the aggregate Hasse-window method.  It samples random
Montgomery curves, extracts moderate smooth point orders from the curve/twist,
and keeps an order only if it improves the deterministic Hasse-window
intersection used by ``vaggregate.py``.
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

from aggregate_residue_intersection import run_intersection
from cm_search_oneshot import resolve_target
from smooth_tail_estimate import one_shot_bound, primes_upto, smooth_part
from voneshot import ladder
from vaggregate import verify as verify_aggregate


@dataclass(frozen=True)
class AggregatePoint:
    curve_index: int
    A: int
    side: str
    x: int
    order: int
    order_bits: float
    component_order: int
    component_smooth_bits: float


@dataclass(frozen=True)
class SearchSummary:
    p: int
    gap: Optional[int]
    bitlength: int
    one_shot_bound_bits: float
    window_bits: float
    curves_tested: int
    accepted_points: int
    verified: bool
    elapsed_seconds: float
    points: list[AggregatePoint]


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


def distinct_prime_divisors(value: int) -> list[int]:
    divisors = []
    q = 2
    while q * q <= value:
        if value % q == 0:
            divisors.append(q)
            while value % q == 0:
                value //= q
        q += 1 if q == 2 else 2
    if value > 1:
        divisors.append(value)
    return divisors


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search for aggregate one-shot ECPP certificates.")
    parser.add_argument("exponent", nargs="?", type=nonnegative_int)
    parser.add_argument("--prime", type=positive_int)
    parser.add_argument("--max-curves", type=positive_int, default=50_000)
    parser.add_argument("--extract-tries", type=positive_int, default=32)
    parser.add_argument("--max-intervals", type=positive_int, default=200_000)
    parser.add_argument("--seed", type=int, default=20260816)
    parser.add_argument("--allow-one-shot", action="store_true")
    parser.add_argument("--stack-mb", type=positive_int, default=128)
    parser.add_argument("--export-json", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)
    if (args.exponent is None) == (args.prime is None):
        parser.error("pass exactly one target: exponent or --prime")
    return args


def aggregate_window_bits(p: int) -> float:
    return math.log2(math.isqrt(4 * math.isqrt(p)))


def aggregate_radius(p: int) -> int:
    return math.isqrt(4 * math.isqrt(p))


def certificate_triples(points: list[AggregatePoint]) -> list[tuple[int, int, int]]:
    return [(point.A, point.x, point.order) for point in points]


def curve_rhs(A: int, x: int, p: int) -> int:
    return (x * x * x + A * x * x + x) % p


def legendre(value: int, p: int) -> int:
    symbol = pow(value % p, (p - 1) // 2, p)
    return -1 if symbol == p - 1 else symbol


def random_x_on_side(rng: random.Random, A: int, p: int, side: int, tries: int = 4096) -> Optional[int]:
    for _ in range(tries):
        x = rng.randrange(2, p - 1)
        if legendre(curve_rhs(A, x, p), p) == side:
            return x
    return None


def affine_x(point: tuple[int, int], p: int) -> Optional[int]:
    x, z = point
    if z % p == 0:
        return None
    return x * pow(z, -1, p) % p


def extract_smooth_point(
    rng: random.Random,
    A: int,
    p: int,
    component: str,
    component_order: int,
    smooth_primes: Sequence[int],
    tries: int,
) -> tuple[int, Optional[int], int]:
    side = 1 if component == "curve" else -1
    smooth = smooth_part(component_order, smooth_primes)
    rough = component_order // smooth
    factors = distinct_prime_divisors(smooth)
    best_order = 0
    best_x: Optional[int] = None
    for _ in range(tries):
        x = random_x_on_side(rng, A, p, side)
        if x is None:
            break
        point = ladder(rough, x, 1, A, p)
        if point[1] % p == 0:
            continue
        order = smooth
        for q in factors:
            while order % q == 0:
                reduced = ladder(order // q, point[0], point[1], A, p)
                if reduced[1] % p == 0:
                    order //= q
                else:
                    break
        if order > best_order:
            best_order = order
            best_x = affine_x(point, p)
    return smooth, best_x, best_order


def residue_count(p: int, orders: list[int], max_intervals: int) -> tuple[bool, int, int]:
    if not orders:
        return False, 1, math.isqrt(p) - 1
    result = run_intersection(p, orders, 0, max_intervals, 0)
    return result.empty, result.interval_count, result.candidate_integer_count


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    rng = random.Random(args.seed)
    pari = Pari()
    pari.allocatemem(args.stack_mb * 1024 * 1024, silent=True)
    target = resolve_target(pari, args)
    p = target.p
    smooth_primes = primes_upto(p.bit_length() * p.bit_length())
    one_bound = one_shot_bound(p)
    one_bits = math.log2(one_bound)
    window_bits = aggregate_window_bits(p)
    radius = aggregate_radius(p)
    points: list[AggregatePoint] = []
    current_candidate_count = math.isqrt(p) - 1
    started = perf_counter()
    verified = False

    print(f"target p = {p}", flush=True)
    if target.gap is not None:
        print(f"gap = {target.gap}", flush=True)
    print(f"bitlength = {p.bit_length()}", flush=True)
    print(f"one_shot_bound_bits = {one_bits:.3f}", flush=True)
    print(f"window_bits = {window_bits:.3f}", flush=True)

    for curve_index in range(1, args.max_curves + 1):
        A = rng.randrange(0, p)
        if (A * A - 4) % p == 0:
            continue
        E = pari.ellinit([0, A, 0, 1, 0], p)
        if len(E) == 0:
            continue
        order = int(pari.ellcard(E))
        component_orders = [("curve", order), ("twist", 2 * p + 2 - order)]
        component_orders.sort(key=lambda item: smooth_part(item[1], smooth_primes), reverse=True)
        for side, component_order in component_orders:
            component_smooth = smooth_part(component_order, smooth_primes)
            if component_smooth <= 2 * radius + 1:
                continue
            smooth, x, extracted_order = extract_smooth_point(
                rng,
                A,
                p,
                side,
                component_order,
                smooth_primes,
                args.extract_tries,
            )
            if x is None or extracted_order <= 1:
                continue
            if not args.allow_one_shot and extracted_order > one_bound:
                continue
            tentative = points + [
                AggregatePoint(
                    curve_index=curve_index,
                    A=A,
                    side=side,
                    x=x,
                    order=extracted_order,
                    order_bits=math.log2(extracted_order),
                    component_order=component_order,
                    component_smooth_bits=math.log2(smooth),
                )
            ]
            try:
                empty, interval_count, candidate_count = residue_count(
                    p,
                    [point.order for point in tentative],
                    args.max_intervals,
                )
            except RuntimeError:
                continue
            if not empty and candidate_count >= current_candidate_count:
                continue
            points = tentative
            current_candidate_count = candidate_count
            print(
                "accepted "
                f"curves={curve_index} points={len(points)} "
                f"last_bits={math.log2(extracted_order):.2f} side={side} "
                f"intervals={interval_count} candidates={candidate_count}",
                flush=True,
            )
            verified = empty and verify_aggregate(p, certificate_triples(points))
            if verified:
                print("aggregate residue intersection is empty", flush=True)
                break
        if verified:
            break
        if curve_index % 1000 == 0:
            print(f"progress curves={curve_index} accepted={len(points)}", flush=True)

    summary = SearchSummary(
        p=p,
        gap=target.gap,
        bitlength=p.bit_length(),
        one_shot_bound_bits=one_bits,
        window_bits=window_bits,
        curves_tested=curve_index if "curve_index" in locals() else 0,
        accepted_points=len(points),
        verified=verified,
        elapsed_seconds=perf_counter() - started,
        points=points,
    )
    print(
        "summary "
        f"verified={summary.verified} curves={summary.curves_tested} "
        f"points={summary.accepted_points} elapsed_seconds={summary.elapsed_seconds:.2f}",
        flush=True,
    )
    if verified:
        flat = [str(p)]
        for point in points:
            flat += [str(point.A), str(point.x), str(point.order)]
        print("certificate_flat = " + " ".join(flat), flush=True)
    if args.export_json:
        args.export_json.parent.mkdir(parents=True, exist_ok=True)
        args.export_json.write_text(json.dumps(asdict(summary), indent=2, sort_keys=True) + "\n")
        print(f"export_json = {args.export_json}", flush=True)
    return 0 if verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
