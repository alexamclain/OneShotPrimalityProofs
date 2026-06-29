#!/usr/bin/env python3
"""Deterministically intersect aggregate Hasse-window residue constraints.

Given candidate point orders m_i for a putative aggregate certificate for n,
any prime divisor q <= sqrt(n) must satisfy, with x = q + 1,

    |x - k_i m_i| <= H,  H = floor(2 * sqrt(floor(sqrt(n)))).

This script intersects those periodic interval constraints over the concrete
integer range 3 <= x <= floor(sqrt(n)) + 1.  Empty intersection is a
deterministic proof that no small prime divisor can satisfy all point-order
facts.  A small non-empty intersection can be checked by trial divisibility or
gcd in a later verifier.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Optional


@dataclass(frozen=True)
class IntersectionStep:
    index: int
    modulus: int
    modulus_bits: float
    interval_count: int
    candidate_integer_count: int
    elapsed_constraints: int


@dataclass(frozen=True)
class IntersectionResult:
    p: int
    run_index: int
    lower_x: int
    upper_x: int
    hasse_radius: int
    moduli_used: int
    empty: bool
    interval_count: int
    candidate_integer_count: int
    intervals_preview: list[tuple[int, int]]
    steps: list[IntersectionStep]


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


def ceil_div(a: int, b: int) -> int:
    return -((-a) // b)


def interval_integer_count(intervals: list[tuple[int, int]]) -> int:
    return sum(hi - lo + 1 for lo, hi in intervals)


def merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not intervals:
        return []
    intervals.sort()
    merged = [intervals[0]]
    for lo, hi in intervals[1:]:
        last_lo, last_hi = merged[-1]
        if lo <= last_hi + 1:
            merged[-1] = (last_lo, max(last_hi, hi))
        else:
            merged.append((lo, hi))
    return merged


def intersect_periodic_window(
    intervals: list[tuple[int, int]],
    modulus: int,
    radius: int,
    max_intervals: int,
) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for lo, hi in intervals:
        # #E_i(F_q) = k_i m_i is a positive group order, so k_i >= 1.
        # Allowing k_i = 0 would admit the spurious window x <= H around the
        # zero multiple for every large modulus.
        k_min = max(1, ceil_div(lo - radius, modulus))
        k_max = (hi + radius) // modulus
        if k_max >= k_min and len(out) + (k_max - k_min + 1) > max_intervals:
            raise RuntimeError(f"interval explosion: {len(out) + (k_max - k_min + 1)} > {max_intervals}")
        for k in range(k_min, k_max + 1):
            center = k * modulus
            new_lo = max(lo, center - radius)
            new_hi = min(hi, center + radius)
            if new_lo <= new_hi:
                out.append((new_lo, new_hi))
        if len(out) > max_intervals:
            raise RuntimeError(f"interval explosion: {len(out)} > {max_intervals}")
    return merge_intervals(out)


def load_moduli_from_aggregate(path: Path, run_index: int, max_components: Optional[int]) -> tuple[int, list[int]]:
    data = json.loads(path.read_text())
    if "runs" in data:
        run = data["runs"][run_index]
        p = int(run["target"]["p"])
        candidates = run["summary"]["accepted_candidates"]
    elif "panels" in data:
        panel = data["panels"][0]
        p = int(panel["target"]["p"])
        candidates = panel["runs"][run_index]["accepted_candidates"]
    else:
        raise ValueError(f"unrecognized aggregate artifact shape: {path}")
    moduli = [int(row["smooth_part"]) for row in candidates if "smooth_part" in row]
    if max_components is not None:
        moduli = moduli[:max_components]
    return p, moduli


def run_intersection(
    p: int,
    moduli: list[int],
    run_index: int,
    max_intervals: int,
    preview: int,
) -> IntersectionResult:
    lower = 3
    upper = math.isqrt(p) + 1
    radius = math.isqrt(4 * math.isqrt(p))
    intervals = [(lower, upper)]
    steps: list[IntersectionStep] = []

    ordered = sorted(set(moduli), reverse=True)
    for index, modulus in enumerate(ordered, start=1):
        # If the Hasse windows cover every residue modulo m, this constraint is
        # vacuous under the conservative fixed-radius model.
        if modulus <= 2 * radius + 1:
            continue
        intervals = intersect_periodic_window(intervals, modulus, radius, max_intervals)
        steps.append(
            IntersectionStep(
                index=index,
                modulus=modulus,
                modulus_bits=math.log2(modulus),
                interval_count=len(intervals),
                candidate_integer_count=interval_integer_count(intervals),
                elapsed_constraints=len(steps) + 1,
            )
        )
        if not intervals:
            break

    return IntersectionResult(
        p=p,
        run_index=run_index,
        lower_x=lower,
        upper_x=upper,
        hasse_radius=radius,
        moduli_used=len(steps),
        empty=not intervals,
        interval_count=len(intervals),
        candidate_integer_count=interval_integer_count(intervals),
        intervals_preview=intervals[:preview],
        steps=steps,
    )


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Intersect aggregate Hasse-window residue constraints.")
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--run-index", type=nonnegative_int, default=0)
    parser.add_argument("--max-components", type=positive_int)
    parser.add_argument("--max-intervals", type=positive_int, default=5_000_000)
    parser.add_argument("--preview", type=positive_int, default=10)
    parser.add_argument("--export-json", type=Path)
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    p, moduli = load_moduli_from_aggregate(args.artifact, args.run_index, args.max_components)
    result = run_intersection(p, moduli, args.run_index, args.max_intervals, args.preview)
    print(
        "intersection "
        f"run={result.run_index} empty={result.empty} "
        f"moduli_used={result.moduli_used} intervals={result.interval_count} "
        f"candidate_integer_count={result.candidate_integer_count} "
        f"hasse_radius={result.hasse_radius}",
        flush=True,
    )
    for step in result.steps:
        print(
            "step "
            f"{step.elapsed_constraints} modulus_bits={step.modulus_bits:.2f} "
            f"intervals={step.interval_count} candidates={step.candidate_integer_count}",
            flush=True,
        )
    if result.intervals_preview:
        print(f"preview={result.intervals_preview}", flush=True)
    if args.export_json:
        args.export_json.parent.mkdir(parents=True, exist_ok=True)
        args.export_json.write_text(json.dumps(asdict(result), indent=2, sort_keys=True) + "\n")
        print(f"export_json = {args.export_json}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
