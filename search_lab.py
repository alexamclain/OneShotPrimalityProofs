#!/usr/bin/env python3
"""Ledger-driven search lab for n^4-smooth one-shot certificates.

This script is intentionally separate from ``oneshot.gp``.  It compares small
method variants, records every curve in a JSONL ledger, and writes only verified
certificates.  The certificate format remains the upstream format:

    p A x0 m q1 q2 ...
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import socket
import statistics
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter, process_time, sleep
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from cypari2 import Pari

from voneshot import verify


METHODS = ("baseline_gp", "factor_smoothpart", "two_sided_gp", "two_sided_factor")
DEFAULT_RUN_DIR = Path("search_runs")


LAB_GP = r'''
spf(N, B) = {
  my(f = factor(N, B), s = 1, r = N, q, e);
  for(i = 1, matsize(f)[1],
    q = f[i, 1]; e = f[i, 2];
    if(q <= B, s *= q^e; r /= q^e)
  );
  [s, r];
};

lell(A, p) = {
  my(E = ellinit([0, A, 0, 1, 0], p));
  if(#E == 0, return(0));
  ellcard(E);
};

lxdbl(xp, zp, A, p) = {
  my(xx = (xp * xp) % p, zz = (zp * zp) % p, xz = (xp * zp) % p, xo, zo);
  xo = ((xx - zz) * (xx - zz)) % p;
  zo = (4 * xz) % p * ((xx + A * xz + zz) % p) % p;
  [xo, zo];
};

lxadd(xa, za, xb, zb, xd, zd, p) = {
  my(a = (xa - za) * (xb + zb) % p, b = (xa + za) * (xb - zb) % p, s, d);
  s = (a + b) % p;
  d = (a - b) % p;
  [zd * (s * s % p) % p, xd * (d * d % p) % p];
};

llad(k, xp, zp, A, p) = {
  if(k == 0, return([1, 0]));
  xp %= p; zp %= p;
  if(k == 1, return([xp, zp]));
  my(xd = xp, zd = zp, xa = xp, za = zp, R = lxdbl(xp, zp, A, p),
     xb = R[1], zb = R[2], bits = binary(k), T);
  for(i = 2, #bits,
    if(bits[i] == 0,
      T = lxadd(xa, za, xb, zb, xd, zd, p); xb = T[1]; zb = T[2];
      T = lxdbl(xa, za, A, p); xa = T[1]; za = T[2],
      T = lxadd(xa, za, xb, zb, xd, zd, p); xa = T[1]; za = T[2];
      T = lxdbl(xb, zb, A, p); xb = T[1]; zb = T[2]
    )
  );
  [xa, za];
};

lisinf(P, p) = ((P[2] % p) == 0 && gcd(P[1] % p, p) == 1);

laffx(P, p) = lift(Mod(P[1], p) / Mod(P[2], p));

lside(A, x, p) = kronecker((x * ((x * x + A * x + 1) % p)) % p, p);

lrandx(A, p, side) = {
  my(x);
  for(t = 1, 256,
    x = random(p);
    if(lside(A, x, p) == side, return(x))
  );
  -1;
};

lextract(A, p, s, r, nsq, bound, side) = {
  my(fs = factor(s)[, 1], x, Q, T, ord, q, d, fo, fd, lp, qs, Qm);
  if(s <= bound, return(0));
  for(t = 1, 64,
    x = lrandx(A, p, side);
    if(x < 0, next);
    Q = llad(r, x, 1, A, p);
    if((Q[2] % p) == 0, next);
    ord = s;
    for(i = 1, #fs,
      q = fs[i];
      while(ord % q == 0,
        T = llad(ord / q, Q[1], Q[2], A, p);
        if(lisinf(T, p), ord /= q, break)
      )
    );
    if(ord > bound,
      d = ord; fo = factor(ord)[, 1];
      forstep(jj = #fo, 1, -1, q = fo[jj]; while(d % q == 0 && d / q > bound, d = d / q));
      fd = factor(d)[, 1]; lp = fd[1];
      if(d >= bound * lp, next);
      qs = select(qq -> qq > nsq, fd);
      Qm = llad(ord / d, Q[1], Q[2], A, p);
      if((Qm[2] % p) == 0, next);
      return([A, laffx(Qm, p), d, qs])
    )
  );
  0;
};
'''


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def method_name(value: str) -> str:
    if value not in METHODS:
        raise argparse.ArgumentTypeError(f"method must be one of: {', '.join(METHODS)}")
    return value


def exponent_list(value: str) -> List[int]:
    exponents: List[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start = positive_int(start_text)
            end = positive_int(end_text)
            if end < start:
                raise argparse.ArgumentTypeError(f"bad exponent range: {part}")
            exponents.extend(range(start, end + 1))
        else:
            exponents.append(positive_int(part))
    if not exponents:
        raise argparse.ArgumentTypeError("at least one exponent is required")
    return sorted(dict.fromkeys(exponents))


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def scbound(p: int) -> int:
    return math.isqrt(p) + 1 + math.isqrt(4 * math.isqrt(p))


def target_for_exponent(pari: Pari, exponent: int) -> Dict[str, int]:
    p = int(pari(f"nextprime(10^{exponent}+1)"))
    n = p.bit_length()
    n2 = n * n
    return {
        "exponent": exponent,
        "p": p,
        "gap": p - 10**exponent,
        "bitlength": n,
        "n2": n2,
        "n4": n2 * n2,
        "bound": scbound(p),
    }


def target_for_prime(pari: Pari, p: int, exponent: int = 0) -> Dict[str, int]:
    if not bool(pari(f"ispseudoprime({p})")):
        raise ValueError(f"target does not pass PARI ispseudoprime: {p}")
    n = p.bit_length()
    n2 = n * n
    return {
        "exponent": exponent,
        "p": p,
        "gap": p - 10**exponent if exponent > 0 else 0,
        "bitlength": n,
        "n2": n2,
        "n4": n2 * n2,
        "bound": scbound(p),
    }


def make_pari(stack_mb: int, seed: Optional[int] = None) -> Pari:
    pari = Pari()
    pari.allocatemem(stack_mb * 1024 * 1024, silent=True)
    pari("default(nbthreads,1)")
    if seed is not None:
        pari(f"setrand({seed})")
    pari.read(str(Path(__file__).resolve().parent / "oneshot.gp"))
    for gp_function in LAB_GP.strip().split("\n\n"):
        pari(gp_function)
    return pari


def json_ready(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [json_ready(item) for item in value]
    if isinstance(value, list):
        return [json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: json_ready(item) for key, item in value.items()}
    return value


def write_event(path: Path, event: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    event = dict(event)
    event.setdefault("utc", utc_now())
    with path.open("a", encoding="utf-8") as handle:
        print(json.dumps(json_ready(event), sort_keys=True), file=handle)


def smoothpart_call(method: str) -> str:
    if method in ("factor_smoothpart", "two_sided_factor"):
        return "spf"
    return "smoothpart"


def sides_for_method(method: str) -> Tuple[int, ...]:
    if method in ("two_sided_gp", "two_sided_factor"):
        return (1, -1)
    return (1,)


def side_name(side: int) -> str:
    return "curve" if side == 1 else "twist"


def gen_to_int_list(vec: Any) -> List[int]:
    return [int(item) for item in vec]


def try_extract(
    pari: Pari,
    p: int,
    A: int,
    s: int,
    r: int,
    n2: int,
    bound: int,
    side: int,
) -> Tuple[Optional[List[int]], float, bool]:
    start = perf_counter()
    res = pari(f"lextract({A}, {p}, {s}, {r}, {n2}, {bound}, {side})")
    elapsed = perf_counter() - start
    if res.type() != "t_VEC":
        return None, elapsed, False
    cert = [p, int(res[0]), int(res[1]), int(res[2])] + gen_to_int_list(res[3])
    return cert, elapsed, bool(verify(cert[0], cert[1], cert[2], cert[3], cert[4:]))


def run_one_curve(
    pari: Pari,
    method: str,
    target: Dict[str, int],
) -> Dict[str, Any]:
    p = target["p"]
    A = int(pari(f"random({p})"))
    ell_start = perf_counter()
    N = int(pari(f"lell({A}, {p})"))
    ell_seconds = perf_counter() - ell_start
    if N == 0:
        return {
            "status": "singular",
            "A": A,
            "ellcard_seconds": ell_seconds,
            "smoothpart_seconds": 0.0,
            "extract_seconds": 0.0,
            "best_smooth_bits": 0.0,
            "certificate": None,
            "verified": False,
            "side": None,
        }

    smooth_fn = smoothpart_call(method)
    smoothpart_seconds = 0.0
    extract_seconds = 0.0
    best_smooth_bits = 0.0
    side_metrics: List[Dict[str, Any]] = []
    certificate: Optional[List[int]] = None
    verified = False
    hit_side: Optional[int] = None
    status = "miss"

    for side in sides_for_method(method):
        order = N if side == 1 else 2 * p + 2 - N
        smooth_start = perf_counter()
        sr = pari(f"{smooth_fn}({order}, {target['n4']})")
        smooth_elapsed = perf_counter() - smooth_start
        smoothpart_seconds += smooth_elapsed
        s = int(sr[0])
        r = int(sr[1])
        smooth_bits = math.log2(s) if s > 0 else 0.0
        best_smooth_bits = max(best_smooth_bits, smooth_bits)
        side_metric: Dict[str, Any] = {
            "side": side_name(side),
            "smooth_bits": smooth_bits,
            "smoothpart_seconds": smooth_elapsed,
            "smooth_part": s,
        }
        if s > target["bound"]:
            cert, extract_elapsed, ok = try_extract(
                pari,
                p,
                A,
                s,
                r,
                target["n2"],
                target["bound"],
                side,
            )
            extract_seconds += extract_elapsed
            side_metric["extract_seconds"] = extract_elapsed
            side_metric["verified"] = ok
            if cert is not None:
                side_metric["certificate"] = cert
            if ok and cert is not None:
                certificate = cert
                verified = True
                hit_side = side
                status = "hit"
                side_metrics.append(side_metric)
                break
        side_metrics.append(side_metric)

    return {
        "status": status,
        "A": A,
        "ellcard_seconds": ell_seconds,
        "smoothpart_seconds": smoothpart_seconds,
        "extract_seconds": extract_seconds,
        "best_smooth_bits": best_smooth_bits,
        "certificate": certificate,
        "verified": verified,
        "side": side_name(hit_side) if hit_side is not None else None,
        "side_metrics": side_metrics,
    }


def certificate_path(cert_dir: Path, exponent: int, method: str, run_id: str) -> Path:
    cert_dir.mkdir(parents=True, exist_ok=True)
    return cert_dir / f"e{exponent}_{method}_{run_id}.txt"


def run_method(args: argparse.Namespace) -> int:
    run_dir = args.run_dir
    ledger = args.ledger or run_dir / "ledger.jsonl"
    cert_dir = args.cert_dir or run_dir / "certs"
    target_pari = make_pari(args.stack_mb)
    if args.prime is not None:
        target = target_for_prime(target_pari, args.prime, args.exponent or 0)
    else:
        target = target_for_exponent(target_pari, args.exponent)
    exponent = int(target["exponent"])
    seed = args.seed
    run_id = args.run_id or f"e{exponent}_{args.method}_s{seed}_{os.getpid()}"
    sha = git_sha()
    host = socket.gethostname()
    pari = make_pari(args.stack_mb, seed)

    common = {
        "run_id": run_id,
        "method": args.method,
        "exponent": exponent,
        "p": target["p"],
        "seed": seed,
        "worker_id": args.worker_id,
        "git_sha": sha,
        "host": host,
    }
    write_event(ledger, {**common, "event": "run_started", "status": "started", "target": target})
    wall_start = perf_counter()
    cpu_start = process_time()
    best_smooth_bits = 0.0
    hit_cert: Optional[List[int]] = None
    hit_curve = 0

    for curve in range(1, args.curves + 1):
        curve_wall = perf_counter()
        curve_cpu = process_time()
        result = run_one_curve(pari, args.method, target)
        best_smooth_bits = max(best_smooth_bits, float(result["best_smooth_bits"]))
        event = {
            **common,
            "event": "curve",
            "curves": curve,
            "curve_seconds": perf_counter() - curve_wall,
            "curve_cpu_seconds": process_time() - curve_cpu,
            "wall_seconds": perf_counter() - wall_start,
            "cpu_seconds": process_time() - cpu_start,
            "status": result["status"],
            "A": result["A"],
            "best_smooth_bits": best_smooth_bits,
            "curve_smooth_bits": result["best_smooth_bits"],
            "ellcard_seconds": result["ellcard_seconds"],
            "smoothpart_seconds": result["smoothpart_seconds"],
            "extract_seconds": result["extract_seconds"],
            "side": result["side"],
            "certificate": result["certificate"],
            "verified": result["verified"],
            "side_metrics": result.get("side_metrics", []),
        }
        write_event(ledger, event)
        print(
            f"{args.method} e={exponent} curve={curve}/{args.curves} "
            f"status={result['status']} smooth_bits={result['best_smooth_bits']:.2f} "
            f"curve_seconds={event['curve_seconds']:.3f}",
            flush=True,
        )
        if result["verified"] and result["certificate"]:
            hit_cert = result["certificate"]
            hit_curve = curve
            path = certificate_path(cert_dir, exponent, args.method, run_id)
            path.write_text(" ".join(str(x) for x in hit_cert) + "\n", encoding="utf-8")
            print(f"certificate_file = {path}", flush=True)
            if args.stop_on_hit:
                break

    finished = {
        **common,
        "event": "run_finished",
        "curves": hit_curve or args.curves,
        "wall_seconds": perf_counter() - wall_start,
        "cpu_seconds": process_time() - cpu_start,
        "status": "hit" if hit_cert else "not_found",
        "best_smooth_bits": best_smooth_bits,
        "certificate": hit_cert,
        "verified": bool(hit_cert),
        "notes": args.notes or "",
    }
    write_event(ledger, finished)
    if args.fail_on_no_hit and hit_cert is None:
        return 1
    return 0


def write_targets(args: argparse.Namespace) -> int:
    out = args.out or args.run_dir / "targets.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    pari = make_pari(args.stack_mb)
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["exponent", "p", "gap", "bitlength", "n2", "n4", "bound"])
        writer.writeheader()
        for exponent in range(args.start, args.end + 1):
            writer.writerow(target_for_exponent(pari, exponent))
    print(f"targets = {out}", flush=True)
    return 0


def summarize(args: argparse.Namespace) -> int:
    ledger = args.ledger or args.run_dir / "ledger.jsonl"
    out = args.out or args.run_dir / "summary.csv"
    curves: Dict[Tuple[str, int], List[Dict[str, Any]]] = defaultdict(list)
    runs: Dict[Tuple[str, int], Dict[str, Dict[str, Any]]] = defaultdict(dict)
    if not ledger.exists():
        raise SystemExit(f"ledger not found: {ledger}")
    with ledger.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            event = json.loads(line)
            key = (event["method"], int(event["exponent"]))
            if event.get("event") == "curve":
                curves[key].append(event)
            elif event.get("event") == "run_finished":
                runs[key][event["run_id"]] = event

    out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for key in sorted(set(curves) | set(runs), key=lambda item: (item[1], item[0])):
        method, exponent = key
        curve_events = curves.get(key, [])
        run_events = list(runs.get(key, {}).values())
        curve_count = len(curve_events)
        cpu_seconds = sum(float(event.get("curve_cpu_seconds", 0.0)) for event in curve_events)
        wall_seconds = sum(float(event.get("curve_seconds", 0.0)) for event in curve_events)
        hits = sum(1 for event in curve_events if event.get("verified"))
        seconds_per_curve = [float(event.get("curve_seconds", 0.0)) for event in curve_events if event.get("curve_seconds")]
        certs_per_cpu_hour = (hits / cpu_seconds * 3600.0) if cpu_seconds else 0.0
        rows.append(
            {
                "method": method,
                "exponent": exponent,
                "runs": len(run_events),
                "curves": curve_count,
                "cpu_seconds": f"{cpu_seconds:.6f}",
                "wall_seconds": f"{wall_seconds:.6f}",
                "hits": hits,
                "best_smooth_bits": f"{max((float(event.get('curve_smooth_bits', 0.0)) for event in curve_events), default=0.0):.6f}",
                "median_seconds_per_curve": f"{statistics.median(seconds_per_curve):.6f}" if seconds_per_curve else "0.000000",
                "certificates_per_cpu_hour": f"{certs_per_cpu_hour:.6f}",
            }
        )

    with out.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "method",
            "exponent",
            "runs",
            "curves",
            "cpu_seconds",
            "wall_seconds",
            "hits",
            "best_smooth_bits",
            "median_seconds_per_curve",
            "certificates_per_cpu_hour",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"summary = {out}", flush=True)
    return 0


def calibrate(args: argparse.Namespace) -> int:
    code = 0
    for exponent, curves in ((52, args.curves_52), (60, args.curves_60)):
        if curves <= 0:
            continue
        for method in METHODS:
            seed = args.seed + exponent * 1000
            ns = argparse.Namespace(
                method=method,
                exponent=exponent,
                prime=None,
                curves=curves,
                seed=seed,
                worker_id=0,
                stack_mb=args.stack_mb,
                run_dir=args.run_dir,
                ledger=args.ledger,
                cert_dir=args.cert_dir,
                run_id=f"cal_e{exponent}_{method}_s{seed}",
                stop_on_hit=args.stop_on_hit,
                fail_on_no_hit=False,
                notes="calibration",
            )
            result = run_method(ns)
            code = code or (0 if result in (0, 1) else result)
    summarize(argparse.Namespace(run_dir=args.run_dir, ledger=args.ledger, out=args.summary_out))
    return code


def sweep(args: argparse.Namespace) -> int:
    run_dir = args.run_dir
    ledger = args.ledger or run_dir / "ledger.jsonl"
    cert_dir = args.cert_dir or run_dir / "certs"
    shard_dir = args.shard_dir or run_dir / "shards"
    log_dir = args.log_dir or run_dir / "logs"
    shard_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    cert_dir.mkdir(parents=True, exist_ok=True)

    sweep_id = args.sweep_id or datetime.now(timezone.utc).strftime("sweep_%Y%m%dT%H%M%SZ")
    pairs = [(method, exponent) for exponent in args.exponents for method in args.methods]
    job_total = args.jobs or args.workers
    pending: List[Dict[str, Any]] = []
    for index in range(job_total):
        method, exponent = pairs[index % len(pairs)]
        seed = args.seed_start + index * args.seed_stride
        worker_id = index % args.workers
        run_id = f"{sweep_id}_j{index:03d}_w{worker_id:02d}_e{exponent}_{method}_s{seed}"
        shard = shard_dir / f"{run_id}.jsonl"
        log = log_dir / f"{run_id}.log"
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--run-dir",
            str(run_dir),
            "--stack-mb",
            str(args.stack_mb),
            "run",
            "--method",
            method,
            "--exponent",
            str(exponent),
            "--curves",
            str(args.curves_per_worker),
            "--seed",
            str(seed),
            "--worker-id",
            str(worker_id),
            "--ledger",
            str(shard),
            "--cert-dir",
            str(cert_dir),
            "--run-id",
            run_id,
            "--notes",
            args.notes or f"sweep:{sweep_id}",
        ]
        if args.fail_on_no_hit:
            command.append("--fail-on-no-hit")
        pending.append({"index": index, "run_id": run_id, "command": command, "shard": shard, "log": log})

    running: List[Dict[str, Any]] = []
    finished: List[Dict[str, Any]] = []
    print(
        f"sweep_id={sweep_id} jobs={job_total} workers={args.workers} "
        f"curves_per_worker={args.curves_per_worker}",
        flush=True,
    )

    while pending or running:
        while pending and len(running) < args.workers:
            job = pending.pop(0)
            log_handle = job["log"].open("w", encoding="utf-8")
            proc = subprocess.Popen(job["command"], stdout=log_handle, stderr=subprocess.STDOUT)
            log_handle.close()
            job["proc"] = proc
            job["started"] = perf_counter()
            running.append(job)
            print(f"started {job['run_id']} log={job['log']}", flush=True)

        any_finished = False
        for job in list(running):
            proc = job["proc"]
            returncode = proc.poll()
            if returncode is None:
                continue
            any_finished = True
            running.remove(job)
            job["returncode"] = returncode
            job["wall_seconds"] = perf_counter() - job["started"]
            finished.append(job)
            print(
                f"finished {job['run_id']} returncode={returncode} "
                f"wall_seconds={job['wall_seconds']:.1f}",
                flush=True,
            )
        if not any_finished and (pending or running):
            sleep(1.0)

    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as merged:
        for job in sorted(finished, key=lambda item: item["index"]):
            shard = job["shard"]
            if shard.exists():
                merged.write(shard.read_text(encoding="utf-8"))

    summarize(argparse.Namespace(run_dir=run_dir, ledger=ledger, out=args.summary_out))
    failures = [job for job in finished if job.get("returncode") not in (0, None)]
    return 1 if failures else 0


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ledger-driven one-shot search lab.")
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--stack-mb", type=positive_int, default=512)
    sub = parser.add_subparsers(dest="command", required=True)

    targets = sub.add_parser("targets", help="write deterministic target table")
    targets.add_argument("--start", type=positive_int, default=52)
    targets.add_argument("--end", type=positive_int, default=80)
    targets.add_argument("--out", type=Path)

    run = sub.add_parser("run", help="run one method/exponent seed budget")
    run.add_argument("--method", type=method_name, required=True)
    run.add_argument("--exponent", type=positive_int)
    run.add_argument("--prime", type=positive_int)
    run.add_argument("--curves", type=positive_int, required=True)
    run.add_argument("--seed", type=nonnegative_int, required=True)
    run.add_argument("--worker-id", type=int, default=0)
    run.add_argument("--ledger", type=Path)
    run.add_argument("--cert-dir", type=Path)
    run.add_argument("--run-id")
    run.add_argument("--notes")
    run.add_argument("--stop-on-hit", action="store_true", default=True)
    run.add_argument("--fail-on-no-hit", action="store_true")

    summary = sub.add_parser("summary", help="derive summary CSV from ledger")
    summary.add_argument("--ledger", type=Path)
    summary.add_argument("--out", type=Path)

    cal = sub.add_parser("calibrate", help="run a small local method tournament")
    cal.add_argument("--curves-52", type=int, default=20)
    cal.add_argument("--curves-60", type=int, default=10)
    cal.add_argument("--seed", type=nonnegative_int, default=20260701)
    cal.add_argument("--ledger", type=Path)
    cal.add_argument("--cert-dir", type=Path)
    cal.add_argument("--summary-out", type=Path)
    cal.add_argument("--stop-on-hit", action="store_true", default=True)

    sw = sub.add_parser("sweep", help="launch parallel seed shards and merge their ledgers")
    sw.add_argument("--methods", nargs="+", type=method_name, default=["two_sided_factor"])
    sw.add_argument("--exponents", type=exponent_list, required=True)
    sw.add_argument("--curves-per-worker", type=positive_int, required=True)
    sw.add_argument("--workers", type=positive_int, default=max(1, os.cpu_count() or 1))
    sw.add_argument("--jobs", type=positive_int)
    sw.add_argument("--seed-start", type=nonnegative_int, default=2026070100)
    sw.add_argument("--seed-stride", type=positive_int, default=1009)
    sw.add_argument("--ledger", type=Path)
    sw.add_argument("--cert-dir", type=Path)
    sw.add_argument("--shard-dir", type=Path)
    sw.add_argument("--log-dir", type=Path)
    sw.add_argument("--summary-out", type=Path)
    sw.add_argument("--sweep-id")
    sw.add_argument("--notes")
    sw.add_argument("--fail-on-no-hit", action="store_true")

    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "run" and (args.exponent is None) == (args.prime is None):
        parser.error("run requires exactly one of --exponent or --prime")
    return args


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    if args.command == "targets":
        return write_targets(args)
    if args.command == "run":
        return run_method(args)
    if args.command == "summary":
        return summarize(args)
    if args.command == "calibrate":
        return calibrate(args)
    if args.command == "sweep":
        return sweep(args)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
