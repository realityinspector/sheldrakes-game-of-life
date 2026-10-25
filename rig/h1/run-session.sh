#!/bin/sh
# Run the blind drawers for one human-in-the-loop session (docs/prereg/h1.md).
#   sh rig/h1/run-session.sh <sid> [seconds=1800] [chunk=5]
# Both drawers run as the system user rig-tester, which cannot read rig/h1/.private.
# They are given only the session's 12 candidates (sorted), never which six are trained.
set -e
cd "$(dirname "$0")"
sid="$1"; secs="${2:-1800}"; chunk="${3:-5}"
[ -f "sessions/$sid.json" ] || { echo "no such session $sid"; exit 1; }
cands=$(python3 -c "import json,sys; print(' '.join(str(c['index']) for c in json.load(open('sessions/$sid.json'))['pool']))")
N=$(python3 -c "import json; print(json.load(open('sessions/$sid.json'))['N'])")
mkdir -p .data/"$sid" .bin
gcc -O2 -mrdseed -o .bin/drawer drawer.c
chmod 755 .bin .bin/drawer
id -u rig-tester >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin rig-tester
chown rig-tester:rig-tester .data/"$sid"; chmod 700 .data/"$sid"
chmod 700 .private
echo "go $(date -u +%Y-%m-%dT%H:%M:%SZ) sid=$sid seconds=$secs candidates=$cands"
for src in rdseed urandom; do
  runuser -u rig-tester -- sh -c "$(pwd)/.bin/drawer $src $N $secs $chunk $cands > $(pwd)/.data/$sid/$src.jsonl" &
done
wait
echo "done $(date -u +%Y-%m-%dT%H:%M:%SZ)"
