#!/usr/bin/env python3
"""Estimate the random-order smoothness barrier for one-shot searches.

For a random integer near p, the B-smooth part is modeled as

    prod_{q <= B} q**v_q(N),

where v_q(N) has the usual geometric distribution
Pr[v_q(N) >= e] = q**(-e).  This script uses the saddlepoint approximation for
the resulting additive random variable sum v_q(N) log(q).

The estimate is not a proof about elliptic-curve group orders, but it is a good
sanity check for search designs that still rely on random curve orders.
"""

from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass
from time import perf_counter
from typing import Iterable, List, Optional, Sequence


@dataclass(frozen=True)
class TailEstimate:
    exponent: int
    bitlength: int
    smoothness_bound: int
    prime_count: int
    threshold_bits: float
    mean_smooth_bits: float
    saddle_theta: float
    chernoff_log10: float
    saddle_log10: float
    full_sea_aux_prime_count: int
    full_sea_aux_prime_max: int
    full_sea_product_bits: float


def positive_int(value: str) -> int:
    out = int(value, 0)
    if out <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return out


def nonnegative_int(value: str) -> int:
    out = int(value, 0)
    if out < 0:
        raise argparse.ArgumentTypeError("must be nonnegative")
    return out


def primes_upto(limit: int) -> List[int]:
    if limit < 2:
        return []
    sieve = bytearray([1]) * (limit + 1)
    sieve[0] = sieve[1] = 0
    for q in range(2, math.isqrt(limit) + 1):
        if sieve[q]:
            sieve[q * q : limit + 1 : q] = bytearray(((limit - q * q) // q) + 1)
    return [q for q in range(2, limit + 1) if sieve[q]]


def one_shot_bound(p: int) -> int:
    sp = math.isqrt(p)
    return sp + 1 + math.isqrt(4 * sp)


def sea_auxiliary_profile(p: int, primes: Sequence[int]) -> tuple[int, int, float]:
    """Return the small-prime product size needed for generic SEA trace recovery."""
    target = 4 * math.isqrt(p)
    product = 1
    count = 0
    last = 1
    for q in primes:
        product *= q
        count += 1
        last = q
        if product > target:
            break
    return count, last, math.log2(product)


def saddlepoint_estimate(exponent: int) -> TailEstimate:
    p = 10**exponent
    bitlength = p.bit_length()
    smoothness_bound = bitlength * bitlength
    primes = primes_upto(smoothness_bound)
    logs = [math.log(q) for q in primes]
    threshold = math.log(one_shot_bound(p))

    def cumulants(theta: float) -> tuple[float, float, float]:
        K = 0.0
        Kp = 0.0
        Kpp = 0.0
        for q, logq in zip(primes, logs):
            a = q ** (theta - 1.0)
            K += math.log1p(-1.0 / q) - math.log1p(-a)
            Kp += logq * a / (1.0 - a)
            Kpp += logq * logq * a / ((1.0 - a) ** 2)
        return K, Kp, Kpp

    lo = 0.0
    hi = 1.0 - 1e-14
    for _ in range(100):
        mid = (lo + hi) / 2.0
        _, derivative, _ = cumulants(mid)
        if derivative < threshold:
            lo = mid
        else:
            hi = mid

    theta = (lo + hi) / 2.0
    K, _, Kpp = cumulants(theta)
    chernoff_log = K - theta * threshold
    saddle_log = chernoff_log - 0.5 * math.log(2.0 * math.pi * Kpp)
    _, mean, _ = cumulants(0.0)
    sea_count, sea_max, sea_bits = sea_auxiliary_profile(p, primes)

    return TailEstimate(
        exponent=exponent,
        bitlength=bitlength,
        smoothness_bound=smoothness_bound,
        prime_count=len(primes),
        threshold_bits=threshold / math.log(2.0),
        mean_smooth_bits=mean / math.log(2.0),
        saddle_theta=theta,
        chernoff_log10=chernoff_log / math.log(10.0),
        saddle_log10=saddle_log / math.log(10.0),
        full_sea_aux_prime_count=sea_count,
        full_sea_aux_prime_max=sea_max,
        full_sea_product_bits=sea_bits,
    )


def smooth_part(value: int, primes: Sequence[int]) -> int:
    out = 1
    rest = value
    for q in primes:
        while rest % q == 0:
            rest //= q
            out *= q
    return out


def monte_carlo(exponent: int, samples: int) -> None:
    p = 10**exponent
    bitlength = p.bit_length()
    primes = primes_upto(bitlength * bitlength)
    bound = one_shot_bound(p)
    width = math.isqrt(4 * p)
    low = p + 1 - width
    high = p + 1 + width
    hits = 0
    best: List[int] = []
    smooth_bit_sum = 0.0
    start = perf_counter()
    for _ in range(samples):
        order = random.randrange(low, high + 1)
        part = smooth_part(order, primes)
        smooth_bit_sum += math.log2(part)
        if part > bound:
            hits += 1
        if len(best) < 10 or part > best[0]:
            best.append(part)
            best.sort()
            best = best[-10:]
    elapsed = perf_counter() - start
    print(
        "monte_carlo "
        f"exponent={exponent} samples={samples} hits={hits} "
        f"hit_rate={hits / samples:.6g} "
        f"avg_smooth_bits={smooth_bit_sum / samples:.3f} "
        f"best_smooth_bits={[item.bit_length() for item in reversed(best)]} "
        f"elapsed_seconds={elapsed:.3f}",
        flush=True,
    )


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Estimate random-order smoothness tails for one-shot ECPP searches."
    )
    parser.add_argument(
        "exponents",
        nargs="*",
        type=nonnegative_int,
        default=[47, 48, 50, 60, 80, 100],
        help="decimal exponents to estimate (default: 47 48 50 60 80 100)",
    )
    parser.add_argument(
        "--monte-carlo-samples",
        type=positive_int,
        default=0,
        help="optional random-order samples per exponent for a direct sanity check",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    for exponent in args.exponents:
        estimate = saddlepoint_estimate(exponent)
        print(
            "estimate "
            f"exponent={estimate.exponent} "
            f"bits={estimate.bitlength} "
            f"B={estimate.smoothness_bound} "
            f"primes_le_B={estimate.prime_count} "
            f"threshold_bits={estimate.threshold_bits:.3f} "
            f"mean_smooth_bits={estimate.mean_smooth_bits:.3f} "
            f"theta={estimate.saddle_theta:.6f} "
            f"tail_log10_chernoff={estimate.chernoff_log10:.3f} "
            f"tail_log10_saddle={estimate.saddle_log10:.3f} "
            f"expected_random_trials_log10={-estimate.saddle_log10:.3f} "
            f"full_sea_aux_primes={estimate.full_sea_aux_prime_count} "
            f"full_sea_aux_prime_max={estimate.full_sea_aux_prime_max} "
            f"full_sea_product_bits={estimate.full_sea_product_bits:.3f}",
            flush=True,
        )
        if args.monte_carlo_samples:
            monte_carlo(exponent, args.monte_carlo_samples)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
