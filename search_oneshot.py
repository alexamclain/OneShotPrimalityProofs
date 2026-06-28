#!/usr/bin/env python3
"""Progress-reporting driver for one-shot ECPP certificate searches.

This script reuses the PARI/GP functions in oneshot.gp, but calls sc_try one
curve at a time so long searches report curve counts and elapsed time.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from time import perf_counter

from cypari2 import Pari

from voneshot import verify


def least_prime_after_power(pari: Pari, exponent: int) -> int:
    return int(pari(f"nextprime(10^{exponent}+1)"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find and verify a one-shot ECPP certificate above 10^n."
    )
    parser.add_argument("exponent", type=int, help="target the least prime > 10^exponent")
    parser.add_argument(
        "--report-every",
        type=int,
        default=25,
        help="print progress after this many tested curves (default: 25)",
    )
    parser.add_argument(
        "--stack-mb",
        type=int,
        default=256,
        help="PARI stack size in MiB (default: 256)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="optional PARI random seed for reproducible random searches",
    )
    parser.add_argument(
        "--pari-threads",
        type=int,
        default=1,
        help="PARI worker threads to use; default 1 avoids cypari2/PARI thread hangs",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parent

    pari = Pari()
    pari.allocatemem(args.stack_mb * 1024 * 1024)
    pari(f"default(nbthreads,{args.pari_threads})")
    if args.seed is not None:
        pari(f"setrand({args.seed})")
    pari.read(str(root / "oneshot.gp"))

    p = least_prime_after_power(pari, args.exponent)
    gap = p - 10**args.exponent
    n = p.bit_length()
    bound = int(pari(f"scbound({p})"))
    print(f"target p = {p}", flush=True)
    print(f"gap = {gap}", flush=True)
    print(f"bitlength = {n}", flush=True)
    print(f"smoothness bound n^2 = {n * n}", flush=True)
    print(f"order lower bound = {bound}", flush=True)

    start = perf_counter()
    curves = 0
    while True:
        curves += 1
        res = pari(f"sc_try({p}, {n * n}, {bound})")
        if res.type() == "t_VEC":
            A, x0, m = (int(res[i]) for i in range(3))
            elapsed = perf_counter() - start
            cert = (p, A, x0, m)
            verified = verify(*cert)
            print("certificate = " + " ".join(str(x) for x in cert), flush=True)
            print(f"curves = {curves}", flush=True)
            print(f"elapsed_seconds = {elapsed:.3f}", flush=True)
            print(f"verified = {verified}", flush=True)
            return 0 if verified else 1
        if args.report_every > 0 and curves % args.report_every == 0:
            elapsed = perf_counter() - start
            rate = curves / elapsed if elapsed else 0.0
            print(
                f"tested_curves = {curves} elapsed_seconds = {elapsed:.3f} rate = {rate:.3f}/s",
                flush=True,
            )


if __name__ == "__main__":
    raise SystemExit(main())
