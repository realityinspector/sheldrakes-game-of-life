#!/bin/bash
# Quick test of batch runner output
echo "🧪 Testing batch runner real-time output..."
echo "Running 1 experiment with 50 generations"
echo "You should see generation-by-generation progress"
echo "="

./venv/bin/python batch_runner.py --experiment-type=focused --limit=1
