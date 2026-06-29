#!/usr/bin/env python3
"""Experimental CM construction driver for one-shot ECPP certificates.

The random search in ``oneshot.gp`` pays for an exact point count on every
random curve.  This driver tries the opposite direction: find a CM trace ``t``
where ``N = p + 1 +/- t`` already has a large ``n^2``-smooth factor, then
construct curves with that trace from the Hilbert class polynomial.  If a
constructed curve admits a Montgomery model, the existing GP point-order code
extracts a certificate and ``voneshot.verify`` remains the final authority.
"""

from __future__ import annotations

import argparse
import math
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Iterable, Iterator, List, Optional, Set, Tuple

from cypari2 import Pari

from voneshot import verify


LOCAL_T24_MAGMA_PATH = Path.home() / "Documents/Codex/t24-search/private/magma-local/install/magma"


@dataclass(frozen=True)
class Target:
    exponent: Optional[int]
    p: int
    gap: Optional[int]
    bitlength: int
    smoothness_bound: int
    order_lower_bound: int


@dataclass(frozen=True)
class SmoothOrder:
    trace: int
    order: int
    smooth_part: int
    rough_part: int


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


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Try to construct one-shot ECPP certificates via small CM discriminants."
    )
    parser.add_argument(
        "exponent",
        nargs="?",
        type=nonnegative_int,
        help="target the least prime > 10^exponent",
    )
    parser.add_argument(
        "--prime",
        type=positive_int,
        help="search for this exact probable prime instead of resolving a power-of-10 target",
    )
    parser.add_argument(
        "--max-discriminant",
        type=positive_int,
        default=20_000,
        help="largest absolute CM discriminant to try (default: 20000)",
    )
    parser.add_argument(
        "--report-every",
        type=positive_int,
        default=500,
        help="print progress after this many discriminants have been considered",
    )
    parser.add_argument(
        "--stack-mb",
        type=positive_int,
        default=512,
        help="PARI stack size in MiB (default: 512)",
    )
    parser.add_argument(
        "--seed",
        type=nonnegative_int,
        help="optional PARI random seed for reproducible point extraction",
    )
    parser.add_argument(
        "--cm-backend",
        choices=("auto", "pari", "magma"),
        default="auto",
        help="backend for Hilbert class polynomial roots (default: auto)",
    )
    parser.add_argument(
        "--magma-cmd",
        type=Path,
        help="Magma executable or wrapper to use with --cm-backend magma/auto; can also be set with MAGMA",
    )
    parser.add_argument(
        "--magma-timeout",
        type=positive_int,
        default=300,
        help="seconds to allow each Magma class-polynomial root computation (default: 300)",
    )
    parser.add_argument(
        "--result-file",
        type=Path,
        help="optional file to overwrite with the first verified certificate line",
    )
    parser.add_argument(
        "--keep-going",
        action="store_true",
        help="continue after a verified certificate and print every one found",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)
    if (args.exponent is None) == (args.prime is None):
        parser.error("pass exactly one target: exponent or --prime")
    if args.exponent == 0:
        parser.error("exponent 0 targets p <= 3, which cannot have this certificate form")
    return args


def resolve_magma_cmd(args: argparse.Namespace) -> Optional[Path]:
    if args.magma_cmd is not None:
        return args.magma_cmd
    path = shutil.which("magma")
    if path is not None:
        return Path(path)
    env_path = os.environ.get("MAGMA")
    if env_path:
        return Path(env_path)
    if LOCAL_T24_MAGMA_PATH.exists():
        return LOCAL_T24_MAGMA_PATH
    return None


def scbound(p: int) -> int:
    return math.isqrt(p) + 1 + math.isqrt(4 * math.isqrt(p))


def resolve_target(pari: Pari, args: argparse.Namespace) -> Target:
    if args.prime is None:
        p = int(pari(f"nextprime(10^{args.exponent}+1)"))
        gap = p - 10**args.exponent
        exponent = args.exponent
    else:
        p = args.prime
        gap = None
        exponent = None
    if p <= 3 or p % 2 == 0:
        raise ValueError("target p must be an odd integer greater than 3")
    if args.prime is not None and not bool(pari(f"ispseudoprime({p})")):
        raise ValueError("exact --prime target must pass PARI ispseudoprime")
    bitlength = p.bit_length()
    return Target(
        exponent=exponent,
        p=p,
        gap=gap,
        bitlength=bitlength,
        smoothness_bound=bitlength * bitlength,
        order_lower_bound=scbound(p),
    )


def squarefree_sieve(limit: int) -> bytearray:
    squarefree = bytearray([1]) * (limit + 1)
    if limit >= 0:
        squarefree[0] = 0
    for q in range(2, math.isqrt(limit) + 1):
        qq = q * q
        for multiple in range(qq, limit + 1, qq):
            squarefree[multiple] = 0
    return squarefree


def is_square(value: int) -> bool:
    if value < 0:
        return False
    root = math.isqrt(value)
    return root * root == value


def legendre_symbol(a: int, p: int) -> int:
    value = pow(a % p, (p - 1) // 2, p)
    if value == p - 1:
        return -1
    return value


def tonelli_shanks(n: int, p: int) -> Optional[int]:
    """Return a square root of ``n`` modulo odd prime ``p``, or None."""
    n %= p
    if n == 0:
        return 0
    if p == 2:
        return n
    if legendre_symbol(n, p) != 1:
        return None
    if p % 4 == 3:
        return pow(n, (p + 1) // 4, p)

    q = p - 1
    s = 0
    while q % 2 == 0:
        s += 1
        q //= 2

    z = 2
    while legendre_symbol(z, p) != -1:
        z += 1

    m = s
    c = pow(z, q, p)
    t = pow(n, q, p)
    r = pow(n, (q + 1) // 2, p)
    while t != 1:
        i = 1
        t2i = t * t % p
        while t2i != 1:
            i += 1
            t2i = t2i * t2i % p
            if i >= m:
                return None
        b = pow(c, 1 << (m - i - 1), p)
        m = i
        c = b * b % p
        t = t * c % p
        r = r * b % p
    return r


def is_fundamental_abs(d: int, squarefree: bytearray) -> bool:
    """Return True iff ``-d`` is a negative fundamental discriminant."""
    if d % 4 == 3:
        return bool(squarefree[d])
    if d % 4 == 0:
        e = d // 4
        return e > 0 and e % 4 in (1, 2) and bool(squarefree[e])
    return False


def fundamental_discriminants(max_abs: int) -> Iterator[int]:
    squarefree = squarefree_sieve(max_abs)
    for d in range(3, max_abs + 1):
        if is_fundamental_abs(d, squarefree):
            yield d


def smooth_order(pari: Pari, target: Target, trace: int) -> Optional[SmoothOrder]:
    order = target.p + 1 - trace
    if order <= 0:
        return None
    sr = pari(f"smoothpart({order}, {target.smoothness_bound})")
    smooth_part = int(sr[0])
    if smooth_part <= target.order_lower_bound:
        return None
    return SmoothOrder(trace=trace, order=order, smooth_part=smooth_part, rough_part=int(sr[1]))


def cornacchia_prime(c: int, p: int) -> Set[int]:
    """Return ``x`` values satisfying ``x^2 + c*y^2 = p``."""
    if legendre_symbol(-c, p) != 1:
        return set()

    root = tonelli_shanks(-c, p)
    if root is None:
        return set()

    xs: Set[int] = set()
    for start in {root, (-root) % p}:
        a, b = p, start
        if b > p // 2:
            b = p - b
        while b * b > p:
            a, b = b, a % b
        x = b
        remainder = p - x * x
        if remainder % c != 0:
            continue
        y2 = remainder // c
        if not is_square(y2):
            continue
        xs.add(x)
    return xs


def cornacchia_four_p(d: int, p: int) -> Set[int]:
    """Return ``x`` values satisfying ``x^2 + d*y^2 = 4p``.

    This catches the odd-trace representations for discriminants ``-d`` with
    ``d == 3 (mod 4)``.  Even-trace representations are usually imprimitive in
    this equation and are handled by ``cornacchia_prime`` instead.
    """
    if d % 2 == 0 or legendre_symbol(-d, p) != 1:
        return set()

    root = tonelli_shanks(-d, p)
    if root is None:
        return set()

    modulus = 4 * p
    xs: Set[int] = set()
    for base in {root, (-root) % p}:
        start = base if base % 2 == 1 else base + p
        for r in {start, modulus - start}:
            a, b = modulus, r
            if b > modulus // 2:
                b = modulus - b
            while b * b > modulus:
                a, b = b, a % b
            x = b
            remainder = modulus - x * x
            if remainder % d != 0:
                continue
            y2 = remainder // d
            if not is_square(y2):
                continue
            xs.add(x)
    return xs


def represented_traces(d: int, p: int) -> Set[int]:
    """Traces satisfying ``t^2 + d*y^2 = 4p``.

    If ``-d`` is the CM discriminant, these are the possible Frobenius traces
    for curves obtained from roots of ``polclass(-d)`` modulo ``p``.
    """
    traces: Set[int] = set()
    c = d if d % 4 else d // 4
    for x in cornacchia_prime(c, p):
        trace = 2 * x
        traces.add(trace)
        if trace:
            traces.add(-trace)
    if d % 4 == 3:
        for trace in cornacchia_four_p(d, p):
            traces.add(trace)
            if trace:
                traces.add(-trace)
    return traces


def montgomery_coefficients(pari: Pari, p: int, j: int) -> Iterator[int]:
    """Yield Montgomery ``A`` values isomorphic to a curve with this ``j``.

    ``ellfromj`` returns a short Weierstrass model.  For every rational
    2-torsion root alpha where f'(alpha) is a square, shifting alpha to zero
    and scaling x by sqrt(f'(alpha)) gives ``B*y^2 = x^3 + A*x^2 + x``.
    """
    try:
        coeffs = pari(f"ellfromj(Mod({j}, {p}))")
    except Exception:
        return
    a1, a2, a3 = (int(coeffs[i]) % p for i in range(3))
    if (a1, a2, a3) != (0, 0, 0):
        return
    a4 = int(coeffs[3]) % p
    a6 = int(coeffs[4]) % p
    try:
        roots = pari(f"polrootsmod(x^3 + Mod({a4},{p})*x + Mod({a6},{p}), {p})")
    except Exception:
        return
    seen: Set[int] = set()
    for root in roots:
        alpha = int(root) % p
        derivative = (3 * alpha * alpha + a4) % p
        if derivative == 0:
            continue
        try:
            if not bool(pari(f"issquare(Mod({derivative}, {p}))")):
                continue
            u = int(pari(f"sqrt(Mod({derivative}, {p}))")) % p
        except Exception:
            continue
        for scale in (u, (-u) % p):
            if scale == 0:
                continue
            A = (3 * alpha * pow(scale, -1, p)) % p
            if A in seen:
                continue
            seen.add(A)
            yield A


def pari_cm_roots(pari: Pari, p: int, d: int) -> List[int]:
    roots = pari(f"polrootsmod(polclass(-{d}), {p})")
    return [int(root) % p for root in roots]


def magma_cm_roots(magma_cmd: Path, p: int, d: int, timeout: int) -> List[int]:
    script = f"""\
SetColumns(0);
P<x> := PolynomialRing(Integers());
Fp := GF({p});
R<X> := PolynomialRing(Fp);
f := R!HilbertClassPolynomial(-{d});
roots := Roots(f);
for root in roots do
    printf "CMROOT %o\\n", Integers()!root[1];
end for;
quit;
"""
    with tempfile.NamedTemporaryFile("w", suffix=".m", delete=False, encoding="utf-8") as handle:
        handle.write(script)
        script_path = Path(handle.name)
    try:
        result = subprocess.run(
            [str(magma_cmd), str(script_path)],
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    finally:
        try:
            script_path.unlink()
        except FileNotFoundError:
            pass

    if result.returncode != 0:
        raise RuntimeError(
            f"Magma exited with {result.returncode}: "
            f"{(result.stderr or result.stdout).strip()[-1000:]}"
        )

    roots: List[int] = []
    for line in result.stdout.splitlines():
        if not line.startswith("CMROOT "):
            continue
        roots.append(int(line.split()[1]) % p)
    return roots


def cm_roots(
    pari: Pari,
    target: Target,
    d: int,
    backend: str,
    magma_cmd: Optional[Path],
    magma_timeout: int,
) -> List[int]:
    if backend in ("auto", "magma") and magma_cmd is not None:
        try:
            return magma_cm_roots(magma_cmd, target.p, d, magma_timeout)
        except Exception as exc:
            if backend == "magma":
                raise
            print(f"cm_magma_failed D=-{d} error={exc!r}; falling back to PARI", flush=True)
    return pari_cm_roots(pari, target.p, d)


def try_cm_discriminant(
    pari: Pari,
    target: Target,
    d: int,
    orders: List[SmoothOrder],
    backend: str,
    magma_cmd: Optional[Path],
    magma_timeout: int,
) -> Optional[Tuple[int, int, int, int]]:
    if not orders:
        return None

    print(
        "cm_candidate "
        f"D=-{d} "
        + " ".join(
            f"trace={order.trace} smooth_bits={order.smooth_part.bit_length()} rough_bits={order.rough_part.bit_length()}"
            for order in orders
        ),
        flush=True,
    )

    try:
        roots = cm_roots(pari, target, d, backend, magma_cmd, magma_timeout)
    except Exception as exc:
        print(f"cm_roots_failed D=-{d} backend={backend} error={exc!r}", flush=True)
        return None

    for root in roots:
        j = root % target.p
        for A in montgomery_coefficients(pari, target.p, j):
            for order in orders:
                for side in (1, -1):
                    try:
                        res = pari(
                            f"sc_try_order({A}, {target.p}, {order.order}, "
                            f"{target.smoothness_bound}, {target.order_lower_bound}, {side})"
                        )
                    except Exception:
                        continue
                    if res.type() != "t_VEC":
                        continue
                    cert = (target.p, int(res[0]), int(res[1]), int(res[2]))
                    if verify(*cert):
                        print(
                            f"cm_verified D=-{d} trace={order.trace} "
                            f"order={order.order} side={side} j={j} A={A}",
                            flush=True,
                        )
                        return cert
                    print(
                        f"cm_rejected D=-{d} trace={order.trace} side={side} j={j} A={A}",
                        flush=True,
                    )
    return None


def write_certificate(path: Path, cert: Tuple[int, int, int, int]) -> None:
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(" ".join(str(x) for x in cert) + "\n", encoding="utf-8")


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    root = Path(__file__).resolve().parent
    pari = Pari()
    pari.allocatemem(args.stack_mb * 1024 * 1024, silent=True)
    pari("default(nbthreads,1)")
    if args.seed is not None:
        pari(f"setrand({args.seed})")
    pari.read(str(root / "oneshot.gp"))
    magma_cmd = resolve_magma_cmd(args)
    if args.cm_backend == "magma" and magma_cmd is None:
        print("error: --cm-backend magma requires --magma-cmd or a discoverable magma executable", file=sys.stderr)
        return 2

    try:
        target = resolve_target(pari, args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr, flush=True)
        return 2

    print(f"target p = {target.p}", flush=True)
    if target.gap is not None:
        print(f"gap = {target.gap}", flush=True)
    print(f"bitlength = {target.bitlength}", flush=True)
    print(f"smoothness bound n^2 = {target.smoothness_bound}", flush=True)
    print(f"order lower bound = {target.order_lower_bound}", flush=True)
    print(f"max_discriminant = {args.max_discriminant}", flush=True)
    print(f"cm_backend = {args.cm_backend}", flush=True)
    if magma_cmd is not None and args.cm_backend in ("auto", "magma"):
        print(f"magma_cmd = {magma_cmd}", flush=True)

    start = perf_counter()
    found = 0
    checked = 0
    represented = 0
    smooth = 0
    for d in fundamental_discriminants(args.max_discriminant):
        checked += 1
        traces = represented_traces(d, target.p)
        if traces:
            represented += 1
            orders = [
                order
                for trace in traces
                if (order := smooth_order(pari, target, trace)) is not None
            ]
            if orders:
                smooth += 1
                cert = try_cm_discriminant(
                    pari,
                    target,
                    d,
                    orders,
                    args.cm_backend,
                    magma_cmd,
                    args.magma_timeout,
                )
                if cert is not None:
                    found += 1
                    print("certificate = " + " ".join(str(x) for x in cert), flush=True)
                    if args.result_file is not None:
                        write_certificate(args.result_file, cert)
                    if not args.keep_going:
                        return 0
        if args.report_every > 0 and checked % args.report_every == 0:
            elapsed = perf_counter() - start
            print(
                f"checked_discriminants = {checked} represented = {represented} "
                f"smooth = {smooth} elapsed_seconds = {elapsed:.3f}",
                flush=True,
            )

    elapsed = perf_counter() - start
    print(
        f"no verified certificate found checked_discriminants={checked} "
        f"represented={represented} smooth={smooth} elapsed_seconds={elapsed:.3f}",
        flush=True,
    )
    return 0 if found else 1


if __name__ == "__main__":
    raise SystemExit(main())
