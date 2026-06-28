#!/usr/bin/env python3
"""Parallel progress driver for one-shot ECPP certificate searches.

This is intentionally a driver around the existing contract:
``oneshot.gp`` still produces ``[A, x0, m]`` via ``sc_try``, and the first
candidate is accepted only after ``voneshot.verify(p, A, x0, m)`` succeeds.

Typical use:

    python3 parallel_search_oneshot.py 40 --workers 8 --seed 20260628 \
        --log-file search-40.jsonl --result-file cert-40.txt

Each worker is a separate process with its own PARI instance and random seed.
The default PARI thread count is 1; use more worker processes for throughput
instead of PARI internal threads, which avoids the cypari2/PARI thread hang
seen by the single-process search driver.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import queue
import signal
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isqrt
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Iterable, List, Optional, TextIO, Tuple


SEED_MODULUS = 2**31 - 1

SC_TRY_BATCH = r'''
sc_try_batch(p, B, bound, batch) = {
  my(res);
  for(i = 1, batch,
    res = sc_try(p, B, bound);
    if(type(res) == "t_VEC", return([i, res[1], res[2], res[3]]))
  );
  0
}
'''


@dataclass(frozen=True)
class Target:
    exponent: Optional[int]
    p: int
    gap: Optional[int]
    bitlength: int
    smoothness_bound: int
    order_lower_bound: int


@dataclass(frozen=True)
class WorkerConfig:
    worker_id: int
    p: int
    smoothness_bound: int
    order_lower_bound: int
    seed: int
    batch_size: int
    report_every: int
    report_seconds: float
    stack_mb: int
    pari_threads: int
    root: str
    max_curves_per_worker: Optional[int]


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
        description="Search for and verify a one-shot ECPP certificate using independent worker processes."
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
        help="search for this exact probable prime instead of resolving a power-of-10 challenge target",
    )
    parser.add_argument(
        "--workers",
        type=positive_int,
        default=os.cpu_count() or 1,
        help="number of independent search processes (default: CPU count)",
    )
    parser.add_argument(
        "--batch-size",
        type=positive_int,
        default=8,
        help="curves tried per worker before checking for stop/progress (default: 8)",
    )
    parser.add_argument(
        "--report-every",
        type=nonnegative_int,
        default=100,
        help="worker progress interval in curves; 0 disables curve-count reports (default: 100)",
    )
    parser.add_argument(
        "--report-seconds",
        type=float,
        default=10.0,
        help="worker progress interval in seconds; 0 disables time reports (default: 10)",
    )
    parser.add_argument(
        "--stack-mb",
        type=positive_int,
        default=256,
        help="PARI stack size per process in MiB (default: 256)",
    )
    parser.add_argument(
        "--seed",
        type=nonnegative_int,
        help="base random seed; worker seeds are deterministically derived from it",
    )
    parser.add_argument(
        "--pari-threads",
        type=positive_int,
        default=1,
        help="PARI threads per worker; default 1 avoids cypari2/PARI thread hangs",
    )
    parser.add_argument(
        "--start-method",
        choices=("spawn", "fork", "forkserver"),
        default="spawn",
        help="multiprocessing start method (default: spawn, for isolated PARI processes)",
    )
    parser.add_argument(
        "--stop-timeout",
        type=float,
        default=5.0,
        help="seconds to wait for workers to exit after a certificate is found (default: 5)",
    )
    parser.add_argument(
        "--max-curves-per-worker",
        type=positive_int,
        help="optional smoke-test limit; workers stop after this many curves if no certificate is found",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        help="optional JSONL event log for progress, worker exits, and results",
    )
    parser.add_argument(
        "--result-file",
        type=Path,
        help="optional file to overwrite with the first verified certificate line",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)
    if (args.exponent is None) == (args.prime is None):
        parser.error("pass exactly one target: exponent or --prime")
    if args.exponent == 0:
        parser.error("exponent 0 targets p <= 3, which cannot have this certificate form")
    if args.report_seconds < 0:
        parser.error("--report-seconds must be nonnegative")
    if args.start_method not in mp.get_all_start_methods():
        parser.error(f"--start-method {args.start_method!r} is not available on this platform")
    return args


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_ready(event: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(event)
    out.setdefault("utc", utc_now())
    return out


def write_event(log_file: Optional[TextIO], event: Dict[str, Any]) -> None:
    if log_file is not None:
        print(json.dumps(json_ready(event), sort_keys=True), file=log_file, flush=True)


def open_log(path: Optional[Path]) -> Optional[TextIO]:
    if path is None:
        return None
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    return path.open("a", encoding="utf-8")


def derive_worker_seeds(base_seed: Optional[int], workers: int) -> Tuple[int, List[int]]:
    if base_seed is None:
        base_seed = int.from_bytes(os.urandom(8), "big")
    base = base_seed % (SEED_MODULUS - 1)
    seeds = []
    for worker_id in range(workers):
        seed = 1 + ((base + 1_000_003 * worker_id) % (SEED_MODULUS - 1))
        seeds.append(seed)
    return base_seed, seeds


def scbound(p: int) -> int:
    return isqrt(p) + 1 + isqrt(4 * isqrt(p))


def least_prime_after_power(exponent: int, stack_mb: int) -> int:
    from cypari2 import Pari

    pari = Pari()
    pari.allocatemem(stack_mb * 1024 * 1024, silent=True)
    pari("default(nbthreads,1)")
    return int(pari(f"nextprime(10^{exponent}+1)"))


def is_pseudoprime(p: int, stack_mb: int) -> bool:
    from cypari2 import Pari

    pari = Pari()
    pari.allocatemem(stack_mb * 1024 * 1024, silent=True)
    pari("default(nbthreads,1)")
    return bool(pari(f"ispseudoprime({p})"))


def resolve_target(args: argparse.Namespace) -> Target:
    if args.prime is None:
        p = least_prime_after_power(args.exponent, args.stack_mb)
        gap = p - 10**args.exponent
        exponent = args.exponent
    else:
        p = args.prime
        gap = None
        exponent = None
    if p <= 3 or p % 2 == 0:
        raise ValueError("target p must be an odd integer greater than 3")
    if args.prime is not None and not is_pseudoprime(p, args.stack_mb):
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


def put_event(event_queue: mp.Queue, event: Dict[str, Any]) -> None:
    event_queue.put(json_ready(event))


def worker_main(config: WorkerConfig, stop_event: mp.Event, event_queue: mp.Queue) -> None:
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    start = perf_counter()
    curves = 0
    last_report_curves = 0
    last_report_elapsed = 0.0

    try:
        from cypari2 import Pari
        from voneshot import verify

        pari = Pari()
        pari.allocatemem(config.stack_mb * 1024 * 1024, silent=True)
        pari(f"default(nbthreads,{config.pari_threads})")
        pari(f"setrand({config.seed})")
        pari.read(str(Path(config.root) / "oneshot.gp"))
        pari(SC_TRY_BATCH)

        put_event(
            event_queue,
            {
                "type": "worker_started",
                "worker_id": config.worker_id,
                "pid": os.getpid(),
                "seed": config.seed,
                "batch_size": config.batch_size,
            },
        )

        while not stop_event.is_set():
            if config.max_curves_per_worker is not None:
                remaining = config.max_curves_per_worker - curves
                if remaining <= 0:
                    break
                batch_size = min(config.batch_size, remaining)
            else:
                batch_size = config.batch_size

            res = pari(
                f"sc_try_batch({config.p}, {config.smoothness_bound}, "
                f"{config.order_lower_bound}, {batch_size})"
            )
            elapsed = perf_counter() - start

            if res.type() == "t_VEC":
                tried_in_batch = int(res[0])
                curves += tried_in_batch
                cert = (
                    config.p,
                    int(res[1]),
                    int(res[2]),
                    int(res[3]),
                )
                verified = bool(verify(*cert))
                put_event(
                    event_queue,
                    {
                        "type": "candidate",
                        "worker_id": config.worker_id,
                        "pid": os.getpid(),
                        "seed": config.seed,
                        "curves": curves,
                        "elapsed_seconds": elapsed,
                        "certificate": cert,
                        "verified_in_worker": verified,
                    },
                )
                return

            curves += batch_size
            should_report_curves = (
                config.report_every > 0 and curves - last_report_curves >= config.report_every
            )
            should_report_time = (
                config.report_seconds > 0
                and elapsed - last_report_elapsed >= config.report_seconds
            )
            if should_report_curves or should_report_time:
                put_event(
                    event_queue,
                    {
                        "type": "progress",
                        "worker_id": config.worker_id,
                        "pid": os.getpid(),
                        "seed": config.seed,
                        "curves": curves,
                        "elapsed_seconds": elapsed,
                        "rate": curves / elapsed if elapsed else 0.0,
                    },
                )
                last_report_curves = curves
                last_report_elapsed = elapsed

        reason = "stop_requested" if stop_event.is_set() else "max_curves_per_worker"
        put_event(
            event_queue,
            {
                "type": "worker_stopped",
                "worker_id": config.worker_id,
                "pid": os.getpid(),
                "seed": config.seed,
                "curves": curves,
                "elapsed_seconds": perf_counter() - start,
                "reason": reason,
            },
        )
    except BaseException as exc:  # send traceback to the parent before the process exits
        put_event(
            event_queue,
            {
                "type": "worker_error",
                "worker_id": config.worker_id,
                "pid": os.getpid(),
                "seed": config.seed,
                "curves": curves,
                "elapsed_seconds": perf_counter() - start,
                "error": repr(exc),
                "traceback": traceback.format_exc(),
            },
        )
        raise


def format_target(target: Target) -> List[str]:
    lines = [f"target p = {target.p}"]
    if target.exponent is not None:
        lines.append(f"gap = {target.gap}")
    lines.extend(
        [
            f"bitlength = {target.bitlength}",
            f"smoothness bound n^2 = {target.smoothness_bound}",
            f"order lower bound = {target.order_lower_bound}",
        ]
    )
    return lines


def shutdown_workers(processes: Dict[int, mp.Process], stop_event: mp.Event, timeout: float) -> None:
    stop_event.set()
    for proc in processes.values():
        proc.join(timeout)
    for proc in processes.values():
        if proc.is_alive():
            proc.terminate()
    for proc in processes.values():
        proc.join()


def print_aggregate(
    worker_curves: Dict[int, int],
    started_workers: int,
    total_workers: int,
    run_start: float,
) -> None:
    elapsed = perf_counter() - run_start
    total_curves = sum(worker_curves.values())
    rate = total_curves / elapsed if elapsed else 0.0
    print(
        "tested_curves = "
        f"{total_curves} elapsed_seconds = {elapsed:.3f} "
        f"rate = {rate:.3f}/s started_workers = {started_workers}/{total_workers}",
        flush=True,
    )


def write_certificate(path: Path, cert: Tuple[int, int, int, int]) -> None:
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(" ".join(str(x) for x in cert) + "\n", encoding="utf-8")


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    root = Path(__file__).resolve().parent
    try:
        target = resolve_target(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr, flush=True)
        return 2
    base_seed, seeds = derive_worker_seeds(args.seed, args.workers)

    log_file = open_log(args.log_file)
    try:
        for line in format_target(target):
            print(line, flush=True)
        print(f"workers = {args.workers}", flush=True)
        print(f"batch_size = {args.batch_size}", flush=True)
        print(f"base_seed = {base_seed}", flush=True)
        if args.log_file is not None:
            print(f"log_file = {args.log_file}", flush=True)
        if args.result_file is not None:
            print(f"result_file = {args.result_file}", flush=True)

        write_event(
            log_file,
            {
                "type": "run_started",
                "target": target.__dict__,
                "workers": args.workers,
                "batch_size": args.batch_size,
                "base_seed": base_seed,
                "worker_seeds": seeds,
                "pari_threads": args.pari_threads,
                "stack_mb": args.stack_mb,
                "start_method": args.start_method,
            },
        )

        ctx = mp.get_context(args.start_method)
        stop_event = ctx.Event()
        event_queue = ctx.Queue()
        processes: Dict[int, mp.Process] = {}

        for worker_id, seed in enumerate(seeds):
            config = WorkerConfig(
                worker_id=worker_id,
                p=target.p,
                smoothness_bound=target.smoothness_bound,
                order_lower_bound=target.order_lower_bound,
                seed=seed,
                batch_size=args.batch_size,
                report_every=args.report_every,
                report_seconds=args.report_seconds,
                stack_mb=args.stack_mb,
                pari_threads=args.pari_threads,
                root=str(root),
                max_curves_per_worker=args.max_curves_per_worker,
            )
            proc = ctx.Process(
                target=worker_main,
                args=(config, stop_event, event_queue),
                name=f"oneshot-worker-{worker_id}",
            )
            proc.start()
            processes[worker_id] = proc

        from voneshot import verify

        run_start = perf_counter()
        worker_curves = {worker_id: 0 for worker_id in processes}
        finished_workers = set()
        noted_exits = set()
        errors: List[Dict[str, Any]] = []
        started_workers = 0
        verified_cert: Optional[Tuple[int, int, int, int]] = None

        try:
            while len(finished_workers) < len(processes) and verified_cert is None:
                try:
                    event = event_queue.get(timeout=0.5)
                except queue.Empty:
                    for worker_id, proc in processes.items():
                        if worker_id in noted_exits or proc.is_alive():
                            continue
                        noted_exits.add(worker_id)
                        if proc.exitcode == 0:
                            finished_workers.add(worker_id)
                        else:
                            exit_event = {
                                "type": "worker_exit",
                                "worker_id": worker_id,
                                "exitcode": proc.exitcode,
                            }
                            errors.append(exit_event)
                            write_event(log_file, exit_event)
                            print(
                                f"worker {worker_id} exited with code {proc.exitcode}",
                                file=sys.stderr,
                                flush=True,
                            )
                    continue

                write_event(log_file, event)
                event_type = event.get("type")
                worker_id = int(event.get("worker_id", -1))

                if event_type == "worker_started":
                    started_workers += 1
                    print(
                        f"worker {worker_id} started pid={event['pid']} seed={event['seed']}",
                        flush=True,
                    )
                elif event_type == "progress":
                    worker_curves[worker_id] = int(event["curves"])
                    print_aggregate(worker_curves, started_workers, args.workers, run_start)
                elif event_type == "candidate":
                    worker_curves[worker_id] = int(event["curves"])
                    cert_tuple = tuple(int(x) for x in event["certificate"])
                    if len(cert_tuple) != 4:
                        errors.append(event)
                        print(f"worker {worker_id} returned malformed candidate", flush=True)
                        continue
                    cert = (cert_tuple[0], cert_tuple[1], cert_tuple[2], cert_tuple[3])
                    parent_verified = bool(verify(*cert))
                    result_event = dict(event)
                    result_event["type"] = "candidate_verified"
                    result_event["verified_in_parent"] = parent_verified
                    write_event(log_file, result_event)
                    if parent_verified:
                        verified_cert = cert
                        print("certificate = " + " ".join(str(x) for x in cert), flush=True)
                        print(f"verified = {parent_verified}", flush=True)
                        print_aggregate(worker_curves, started_workers, args.workers, run_start)
                        if args.result_file is not None:
                            write_certificate(args.result_file, cert)
                        stop_event.set()
                    else:
                        errors.append(result_event)
                        print(f"worker {worker_id} returned an unverified candidate; continuing", flush=True)
                elif event_type == "worker_stopped":
                    worker_curves[worker_id] = int(event["curves"])
                    finished_workers.add(worker_id)
                    print(
                        f"worker {worker_id} stopped reason={event['reason']} curves={event['curves']}",
                        flush=True,
                    )
                elif event_type == "worker_error":
                    worker_curves[worker_id] = int(event.get("curves", 0))
                    finished_workers.add(worker_id)
                    errors.append(event)
                    print(
                        f"worker {worker_id} error: {event.get('error')}",
                        file=sys.stderr,
                        flush=True,
                    )
                else:
                    print(f"event = {event}", flush=True)

        except KeyboardInterrupt:
            print("interrupted; stopping workers", file=sys.stderr, flush=True)
            write_event(log_file, {"type": "interrupted"})
            shutdown_workers(processes, stop_event, args.stop_timeout)
            return 130

        shutdown_workers(processes, stop_event, args.stop_timeout)

        if verified_cert is not None:
            write_event(
                log_file,
                {
                    "type": "run_finished",
                    "status": "found",
                    "certificate": verified_cert,
                    "total_curves": sum(worker_curves.values()),
                },
            )
            return 0

        status = "error" if errors else "not_found"
        write_event(
            log_file,
            {
                "type": "run_finished",
                "status": status,
                "total_curves": sum(worker_curves.values()),
                "errors": errors,
            },
        )
        print_aggregate(worker_curves, started_workers, args.workers, run_start)
        print(f"no verified certificate found ({status})", flush=True)
        return 2 if errors else 1
    finally:
        if log_file is not None:
            log_file.close()


if __name__ == "__main__":
    raise SystemExit(main())
