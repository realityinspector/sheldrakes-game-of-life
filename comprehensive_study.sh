#!/bin/bash
# Comprehensive Morphic Resonance Study Script

echo "🔬 Starting Comprehensive Morphic Resonance Study"

# Store the original directory
ORIGINAL_DIR=$(pwd)
BATCH_DIR="batch_results/$(date +%Y%m%d_%H%M)"

# Create batch directory but stay in original directory for running simulations
mkdir -p "$BATCH_DIR"
echo "📁 Results will be saved to: $BATCH_DIR"

# Run 5 morphic simulations (from original directory)
for i in {1..5}; do
  echo "Running morphic simulation $i/5..."
  ./training.sh --mode=morphic --generations=75 --crystal-count=7 --grid-size=20

  # Check if simulation was successful and move results
  if ls results/simulation_morphic_*.json 1> /dev/null 2>&1; then
    # Get the most recent morphic result file
    latest=$(ls -t results/simulation_morphic_*.json | head -1)
    mv "$latest" "$BATCH_DIR/morphic_run_$i.json"
    echo "  ✅ Morphic simulation $i completed successfully"
  else
    echo "  ❌ Morphic simulation $i failed - no results file found"
  fi
done

# Run 5 control simulations
for i in {1..5}; do
  echo "Running control simulation $i/5..."
  ./training.sh --mode=control --generations=75 --grid-size=20

  # Check if simulation was successful and move results
  if ls results/simulation_control_*.json 1> /dev/null 2>&1; then
    # Get the most recent control result file
    latest=$(ls -t results/simulation_control_*.json | head -1)
    mv "$latest" "$BATCH_DIR/control_run_$i.json"
    echo "  ✅ Control simulation $i completed successfully"
  else
    echo "  ❌ Control simulation $i failed - no results file found"
  fi
done

echo ""
echo "✅ Batch complete! Results in: $ORIGINAL_DIR/$BATCH_DIR"
echo "📊 View results: ls -la $BATCH_DIR/"

# Quick summary
morphic_count=$(ls "$BATCH_DIR"/morphic_run_*.json 2>/dev/null | wc -l)
control_count=$(ls "$BATCH_DIR"/control_run_*.json 2>/dev/null | wc -l)
echo "📈 Summary: $morphic_count morphic simulations, $control_count control simulations completed"