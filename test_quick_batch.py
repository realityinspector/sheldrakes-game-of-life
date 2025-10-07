#!/usr/bin/env python3
"""Quick test of batch runner with short simulations"""

import sys
import subprocess

# Run batch with very short simulations for quick testing
cmd = [
    './venv/bin/python', 'batch_runner.py',
    '--experiment-type=focused',
    '--limit=2'
]

print("🧪 Testing batch runner with real-time output...")
print("=" * 60)
print("NOTE: This should show experiment details and generation progress in real-time")
print("=" * 60)
print()

# Run without capturing output so we see it in real-time
result = subprocess.run(cmd, timeout=180)

print()
print("=" * 60)
print(f"Exit code: {result.returncode}")
print("=" * 60)

sys.exit(result.returncode)
