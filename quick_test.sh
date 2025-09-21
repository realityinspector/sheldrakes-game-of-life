#!/bin/bash
# Quick test script to verify the system works

echo "🧪 Quick Morphic Resonance Test"
echo "==============================="

# Check if we're in the right environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ Virtual environment not active. Run: source venv/bin/activate"
    exit 1
fi

# Check dependencies
echo "📋 Checking dependencies..."
./training.sh --check-only
if [ $? -ne 0 ]; then
    echo "❌ Dependency check failed. Run: ./venv/bin/pip install requests"
    exit 1
fi

echo ""
echo "🚀 Running quick morphic test (5 generations, small grid)..."
./training.sh --mode=morphic --generations=5 --crystal-count=2 --grid-size=8

if [ -f "results/simulation_morphic_"*.json ]; then
    echo ""
    echo "✅ Success! Morphic simulation completed."
    echo "📊 Results file created: $(ls results/simulation_morphic_*.json | tail -1)"

    # Quick analysis
    latest=$(ls -t results/simulation_morphic_*.json | head -1)
    influences=$(python3 -c "
import json
try:
    with open('$latest') as f:
        data = json.load(f)
    print(len(data.get('morphic_influences', [])))
except:
    print('N/A')
")
    echo "🧬 Morphic influences detected: $influences"

    echo ""
    echo "🎯 Now you can run the comprehensive study:"
    echo "   ./comprehensive_study.sh"
else
    echo ""
    echo "❌ Test failed - no results file found"
    echo "Check the simulation output above for errors"
fi