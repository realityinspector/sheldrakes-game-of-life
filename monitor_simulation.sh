#!/bin/bash
echo "🔍 REAL-TIME MORPHIC RESONANCE MONITORING"
echo "Starting monitoring... Press Ctrl+C to stop"
echo ""

while true; do
  clear
  echo "🔍 REAL-TIME MORPHIC RESONANCE MONITORING"
  echo "========================================="
  echo "$(date)"
  echo ""

  # Current simulations
  active_sims=$(ps aux | grep training.sh | grep -v grep | wc -l)
  echo "📊 Active Simulations: $active_sims"

  # Recent results
  echo ""
  echo "📈 Latest Results:"
  if [ -d "results" ]; then
    ls -lt results/simulation_*.json 2>/dev/null | head -3 | while read line; do
      echo "  $line"
    done
  else
    echo "  No results directory found"
  fi

  # Influence metrics from latest run
  echo ""
  latest=$(ls -t results/simulation_morphic_*.json 2>/dev/null | head -1)
  if [ -f "$latest" ]; then
    echo "🧬 Latest Morphic Run:"
    echo "  - File: $(basename $latest)"

    # Use python for JSON parsing since it's more reliable
    influences=$(python3 -c "
import json
try:
    with open('$latest') as f:
        data = json.load(f)
    print(len(data.get('morphic_influences', [])))
except:
    print('N/A')
" 2>/dev/null)

    population=$(python3 -c "
import json
try:
    with open('$latest') as f:
        data = json.load(f)
    print(f'{data.get(\"avg_population\", 0):.1f}')
except:
    print('N/A')
" 2>/dev/null)

    echo "  - Decision influences: $influences"
    echo "  - Population: $population"
  else
    echo "🧬 No morphic simulations found yet"
  fi

  echo ""
  echo "📋 Quick Commands:"
  echo "  ./training.sh --mode=morphic --generations=25 --crystal-count=3 --grid-size=10"
  echo "  ./analyze_patterns.sh"
  echo ""
  echo "Press Ctrl+C to stop monitoring..."

  sleep 5
done