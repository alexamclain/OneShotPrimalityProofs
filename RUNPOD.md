# RunPod CPU Search Notes

This repo's one-shot search is embarrassingly parallel across independent
random seeds. A RunPod CPU pod can run the same `parallel_search_oneshot.py`
driver as the local machine, then return a verified certificate line and JSONL
log.

## Pod Setup

Use an Ubuntu-based CPU pod with enough disk for the repo and Python build
artifacts. Inside the pod:

```bash
git clone https://github.com/alexamclain/OneShotPrimalityProofs.git
cd OneShotPrimalityProofs
bash scripts/setup_runpod_cpu.sh
```

If the repo is already present, run the script from the repo root after pulling:

```bash
git pull --ff-only
bash scripts/setup_runpod_cpu.sh
```

The setup script installs system PARI dependencies, installs `cypari2`, and
runs small smoke tests against `voneshot.py` and `parallel_search_oneshot.py`.

## Running A Search

Use one independent process per available CPU thread/core, but keep PARI itself
single-threaded. The driver does this by default with `--pari-threads 1`.

```bash
mkdir -p search_runs
python3 parallel_search_oneshot.py 45 \
  --workers "$(nproc)" \
  --seed 202606280601 \
  --batch-size 8 \
  --report-every 500 \
  --report-seconds 30 \
  --log-file search_runs/search-45-runpod-a.jsonl \
  --result-file search_runs/cert-45-runpod-a.txt
```

Use a different base seed on every pod. For example, use a shared prefix plus a
pod index:

```text
202606280601
202606280602
202606280603
```

If several pods are searching the same exponent, the first verified result wins.
No other coordination is required.

## Returning Results

When a pod finds a certificate, copy back:

- `search_runs/cert-<n>-*.txt`
- `search_runs/search-<n>-*.jsonl`

The certificate line should be appended to `challenge.csv`, documented in
`README.md`, and reverified locally with:

```bash
python3 voneshot.py --test
python3 - <<'PY'
from voneshot import verify
ok = 0
with open("challenge.csv") as f:
    for line in f:
        vals = [int(x) for x in line.strip().split(",")]
        if not verify(*vals):
            raise SystemExit(f"failed: {line.strip()}")
        ok += 1
print(f"ok {ok}")
PY
```

Also confirm the new prime is the least prime above the target power of ten:

```bash
python3 - <<'PY'
from cypari2 import Pari
pari = Pari()
exponent = 45
p = 10**45 + 9
base = 10**exponent
assert int(pari(f"nextprime({base}+1)")) == p
assert bool(pari(f"isprime({p})"))
print("least prime ok")
PY
```

Adjust `exponent` and `p` for the candidate being recorded.
