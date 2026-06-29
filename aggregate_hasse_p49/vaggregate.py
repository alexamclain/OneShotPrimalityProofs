#!/usr/bin/env python3
"""Verifier for aggregate one-shot ECPP certificates.

Certificate format:

    n A1 x1 m1 A2 x2 m2 ...

Each triple asserts that x_i is the x-coordinate of a point of exact smooth
order m_i on the Montgomery curve y^2 = x^3 + A_i x^2 + x over Z/nZ.  Instead
of requiring one m_i to exceed the one-shot bound, this verifier intersects the
Hasse-window residue constraints for all m_i.  If no x = q + 1 with
q <= sqrt(n) can satisfy all of them, n is prime.
"""

from __future__ import annotations

import sys
from math import gcd, isqrt
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aggregate_residue_intersection import run_intersection
from voneshot import check_orders, is_smooth, ladder, prime_divisors, sieve_primes


def verify_order_fact(n: int, A: int, x0: int, m: int, smooth_primes: Sequence[int]) -> bool:
    """Verify exact order m for one Montgomery x-coordinate over Z/nZ."""
    if m <= 0:
        return False
    if not (0 <= A < n) or not (0 <= x0 < n):
        return False

    # E is nonsingular modulo every prime divisor of n.
    if gcd((A * A - 4) % n, n) != 1:
        return False

    # A point order over F_n, if n is prime, cannot exceed the Hasse upper bound.
    if m > n + 1 + isqrt(4 * n):
        return False

    divisors = prime_divisors(m, smooth_primes, batch_bits=max(64, m.bit_length()))
    if not is_smooth(m, divisors):
        return False

    Xm, Zm = ladder(m, x0, 1, A, n)
    if Zm % n != 0 or gcd(Xm % n, n) != 1:
        return False

    radical = 1
    for q in divisors:
        radical *= q
    XQ, ZQ = ladder(m // radical, x0, 1, A, n)
    return check_orders(XQ, ZQ, divisors, A, n)


def aggregate_residue_empty(n: int, orders: Sequence[int]) -> bool:
    try:
        result = run_intersection(
            p=n,
            moduli=list(orders),
            run_index=0,
            max_intervals=200_000,
            preview=0,
        )
    except RuntimeError:
        return False
    return result.empty


def verify(n: int, triples: Sequence[tuple[int, int, int]]) -> bool:
    if n <= 3 or n % 2 == 0:
        return False
    if not triples:
        return False
    smooth_primes = sieve_primes(n.bit_length() * n.bit_length())
    orders = []
    for A, x0, m in triples:
        if not verify_order_fact(n, A, x0, m, smooth_primes):
            return False
        orders.append(m)
    return aggregate_residue_empty(n, orders)


def parse_flat_certificate(args: Sequence[str]) -> tuple[int, list[tuple[int, int, int]]]:
    if len(args) < 4 or (len(args) - 1) % 3:
        raise ValueError("usage: python vaggregate.py <n> <A1> <x1> <m1> [<A2> <x2> <m2> ...]")
    values = [int(item, 0) for item in args]
    n = values[0]
    triples = []
    for index in range(1, len(values), 3):
        triples.append((values[index], values[index + 1], values[index + 2]))
    return n, triples


def self_test() -> None:
    assert verify(101, [(3, 24, 24)]) is True
    assert verify(1003, [(3, 24, 24)]) is False
    known = (
        1000000000000000000000000000000000000000000000193,
        756629692972229602491961804298556859655820911395,
        918593905186155312035948211710330034366751932565,
        1606109062327986974770608,
    )
    assert verify(known[0], [(known[1], known[2], known[3])]) is True


def main(argv: Sequence[str]) -> int:
    if list(argv) == ["--test"]:
        self_test()
        print("ok")
        return 0
    try:
        n, triples = parse_flat_certificate(argv)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    except Exception:
        print("error: all certificate fields must be integers", file=sys.stderr)
        return 2
    result = verify(n, triples)
    print(result)
    return 0 if result else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
