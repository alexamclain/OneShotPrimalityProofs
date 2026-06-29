#!/usr/bin/env python3
"""Verify and summarize the aggregate certificate for 10^49 + 9."""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aggregate_residue_intersection import run_intersection
from vaggregate import verify


def parse_certificate(path: Path) -> tuple[int, list[tuple[int, int, int]]]:
    values = [int(item) for item in path.read_text().split()]
    if len(values) < 4 or (len(values) - 1) % 3:
        raise ValueError(f"bad aggregate certificate shape in {path}")
    triples = []
    for index in range(1, len(values), 3):
        triples.append((values[index], values[index + 1], values[index + 2]))
    return values[0], triples


def main() -> int:
    cert_path = Path(__file__).with_name("certificate_flat.txt")
    p, triples = parse_certificate(cert_path)
    orders = [m for _a, _x, m in triples]
    result = run_intersection(p, orders, run_index=0, max_intervals=200_000, preview=5)
    print(f"p = {p}")
    print(f"components = {len(triples)}")
    print(f"order_bits = {[round(math.log2(m), 2) for m in orders]}")
    print(f"one_shot_bound_bits = {math.log2(math.isqrt(p) + 1 + math.isqrt(4 * math.isqrt(p))):.3f}")
    for step in result.steps:
        print(
            "intersection_step "
            f"bits={step.modulus_bits:.2f} "
            f"intervals={step.interval_count} "
            f"candidate_x={step.candidate_integer_count}"
        )
    print(f"intersection_empty = {result.empty}")
    print(f"vaggregate.verify = {verify(p, triples)}")
    return 0 if result.empty and verify(p, triples) else 1


if __name__ == "__main__":
    raise SystemExit(main())
