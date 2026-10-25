#!/bin/sh
# Drives the pre-registered isolation-4 series (docs/prereg/isolation-4.md), then scores it.
set -e
cd "$(dirname "$0")/.."
export PATH="$PWD/node_modules/.bin:$PATH"
for label in positive-control-0.5pct isolation-4-1 isolation-4-2 isolation-4-3 isolation-4-4 isolation-4-5 isolation-4-6; do
  echo "== $label start $(date -u +%H:%M:%S)"
  node --experimental-strip-types --no-warnings rig/run-local.ts "rig/protocols/$label.json" > "explore/.out/run-$label.log" 2>&1 || { echo "== $label FAILED"; tail -20 "explore/.out/run-$label.log"; exit 1; }
  head -3 "rig/reports/$label.md" | tail -1
done
for label in isolation-4-1 isolation-4-2 isolation-4-3 isolation-4-4 isolation-4-5 isolation-4-6; do
  dir=$(ls -d rig/.data/$label-2026* | tail -1)
  node --experimental-strip-types --no-warnings explore/replay.ts "$dir" "explore/.out/$label.jsonl" | tail -1
  python3 explore/rawbits.py "$dir" "explore/.out/$label.rawbits.npz"
done
python3 explore/confirm.py > explore/.out/confirm.log 2>&1 && echo "== confirm done" || { echo "== confirm FAILED"; tail -20 explore/.out/confirm.log; exit 1; }
SESSIONS=isolation-4-1,isolation-4-2,isolation-4-3,isolation-4-4,isolation-4-5,isolation-4-6 PERMS=20000 python3 explore/battery.py > explore/.out/battery-fresh.log 2>&1 && cp explore/.out/battery.json explore/results/battery-isolation-4.json && echo "== battery done"
