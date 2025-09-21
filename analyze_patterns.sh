#!/bin/bash
echo "🔍 MORPHIC PATTERN ANALYSIS"
echo "=========================="

if [ ! -d "results" ]; then
    echo "❌ No results directory found. Run some simulations first."
    exit 1
fi

morphic_files=$(ls results/simulation_morphic_*.json 2>/dev/null | wc -l)
if [ "$morphic_files" -eq 0 ]; then
    echo "❌ No morphic simulation results found."
    echo "Run: ./training.sh --mode=morphic --generations=50 --crystal-count=5 --grid-size=15"
    exit 1
fi

for file in results/simulation_morphic_*.json; do
  echo "File: $(basename $file)"

  # Extract pattern metrics using jq if available, otherwise use python
  if command -v jq &> /dev/null; then
    patterns=$(jq -r '.crystals[]? | .patterns[]? | length' $file 2>/dev/null | paste -sd+ 2>/dev/null | bc 2>/dev/null || echo "0")
    influences=$(jq -r '.morphic_influences | length' $file 2>/dev/null || echo "0")
    population=$(jq -r '.avg_population' $file 2>/dev/null || echo "0")
  else
    # Fallback to python if jq not available
    patterns=$(python3 -c "
import json
try:
    with open('$file') as f:
        data = json.load(f)
    total = sum(len(crystal.get('patterns', [])) for crystal in data.get('crystals', []))
    print(total)
except:
    print(0)
" 2>/dev/null || echo "0")

    influences=$(python3 -c "
import json
try:
    with open('$file') as f:
        data = json.load(f)
    print(len(data.get('morphic_influences', [])))
except:
    print(0)
" 2>/dev/null || echo "0")

    population=$(python3 -c "
import json
try:
    with open('$file') as f:
        data = json.load(f)
    print(f\"{data.get('avg_population', 0):.1f}\")
except:
    print(0.0)
" 2>/dev/null || echo "0.0")
  fi

  echo "  - Stored patterns: $patterns"
  echo "  - Morphic influences: $influences"
  echo "  - Avg population: $population"

  # Calculate influence rate
  if [ "$population" != "0" ] && [ "$influences" != "0" ]; then
    influence_rate=$(python3 -c "print(f'{($influences / ($population * 10)):.1f}%')" 2>/dev/null || echo "N/A")
    echo "  - Influence rate: $influence_rate"
  else
    echo "  - Influence rate: 0.0%"
  fi
  echo ""
done

echo "📊 Summary Analysis:"
total_morphic=$(ls results/simulation_morphic_*.json 2>/dev/null | wc -l)
total_control=$(ls results/simulation_control_*.json 2>/dev/null | wc -l)
echo "  - Morphic simulations: $total_morphic"
echo "  - Control simulations: $total_control"

if [ "$total_morphic" -gt 0 ]; then
    echo ""
    echo "🎯 Quick Comparison:"
    echo "Run './training.sh --mode=control --generations=50 --grid-size=15' for comparison"
fi