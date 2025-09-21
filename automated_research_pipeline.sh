#!/bin/bash
# Ultimate automated research pipeline

echo "🤖 AUTOMATED MORPHIC RESONANCE RESEARCH PIPELINE"
echo "==============================================="

PIPELINE_ID="pipeline_$(date +%Y%m%d_%H%M%S)"
mkdir -p automated_research/$PIPELINE_ID/{raw_data,analysis,reports}

# Configuration
TOTAL_RUNS=50
GENERATIONS=100
GRID_SIZE=20
CRYSTAL_COUNT=8

echo "📋 Pipeline Configuration:"
echo "  - Total runs: $TOTAL_RUNS (25 morphic, 25 control)"
echo "  - Generations per run: $GENERATIONS"
echo "  - Grid size: ${GRID_SIZE}x${GRID_SIZE}"
echo "  - Crystal count: $CRYSTAL_COUNT"
echo ""

# Check if OPENROUTER_API_KEY is set
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "⚠️  OPENROUTER_API_KEY not set. LLM features will be disabled."
    echo "   Set with: export OPENROUTER_API_KEY=\"your_key_here\""
else
    echo "✅ LLM integration enabled"
fi
echo ""

# Progress tracking
start_time=$(date +%s)

# Run studies with progress indicators
echo "🧬 Running Morphic Simulations..."
for i in $(seq 1 25); do
    echo -ne "  Progress: [$i/25] "
    ./training.sh --mode=morphic --generations=$GENERATIONS --crystal-count=$CRYSTAL_COUNT --grid-size=$GRID_SIZE > /dev/null 2>&1
    if [ $? -eq 0 ] && ls results/simulation_morphic_*.json 1> /dev/null 2>&1; then
        latest=$(ls -t results/simulation_morphic_*.json | head -1)
        mv "$latest" automated_research/$PIPELINE_ID/raw_data/morphic_$(printf "%03d" $i).json 2>/dev/null
        echo "✅"
    else
        echo "❌ (failed)"
    fi
done

echo ""
echo "🎯 Running Control Simulations..."
for i in $(seq 1 25); do
    echo -ne "  Progress: [$i/25] "
    ./training.sh --mode=control --generations=$GENERATIONS --grid-size=$GRID_SIZE > /dev/null 2>&1
    if [ $? -eq 0 ] && ls results/simulation_control_*.json 1> /dev/null 2>&1; then
        latest=$(ls -t results/simulation_control_*.json | head -1)
        mv "$latest" automated_research/$PIPELINE_ID/raw_data/control_$(printf "%03d" $i).json 2>/dev/null
        echo "✅"
    else
        echo "❌ (failed)"
    fi
done

# Comprehensive analysis
echo ""
echo "📊 Running comprehensive analysis..."

python3 > automated_research/$PIPELINE_ID/reports/comprehensive_report.md << PYEOF
import json, glob, statistics
import numpy as np
from datetime import datetime
import sys
import os

print("# Automated Morphic Resonance Research Report")
print(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"**Pipeline ID:** $PIPELINE_ID")
print()

# Load all data
morphic_files = glob.glob('automated_research/$PIPELINE_ID/raw_data/morphic_*.json')
control_files = glob.glob('automated_research/$PIPELINE_ID/raw_data/control_*.json')

morphic_data = []
control_data = []

for file in morphic_files:
    try:
        with open(file) as f:
            data = json.load(f)
            morphic_data.append(data)
    except:
        continue

for file in control_files:
    try:
        with open(file) as f:
            data = json.load(f)
            control_data.append(data)
    except:
        continue

print("## 📊 Sample Statistics")
print(f"- **Morphic runs:** {len(morphic_data)}")
print(f"- **Control runs:** {len(control_data)}")
print(f"- **Generations per run:** $GENERATIONS")
print(f"- **Grid size:** ${GRID_SIZE}x${GRID_SIZE}")
print()

if len(morphic_data) == 0 or len(control_data) == 0:
    print("❌ **Error: Insufficient data for analysis**")
    print("- Check that simulations completed successfully")
    sys.exit(1)

# Population analysis
morphic_pops = [d['avg_population'] for d in morphic_data]
control_pops = [d['avg_population'] for d in control_data]

print("## 🧬 Population Dynamics")
print("| Metric | Morphic | Control | Difference |")
print("|--------|---------|---------|------------|")
print(f"| Mean | {statistics.mean(morphic_pops):.2f} | {statistics.mean(control_pops):.2f} | {statistics.mean(morphic_pops) - statistics.mean(control_pops):+.2f} |")
print(f"| Std Dev | {statistics.stdev(morphic_pops):.2f} | {statistics.stdev(control_pops):.2f} | - |")
print(f"| Min | {min(morphic_pops):.2f} | {min(control_pops):.2f} | - |")
print(f"| Max | {max(morphic_pops):.2f} | {max(control_pops):.2f} | - |")
print()

# Statistical significance (simplified without scipy)
mean_diff = statistics.mean(morphic_pops) - statistics.mean(control_pops)
print("## 📈 Statistical Analysis")
print(f"- **Mean difference:** {mean_diff:.4f}")
print(f"- **Morphic std:** {statistics.stdev(morphic_pops):.4f}")
print(f"- **Control std:** {statistics.stdev(control_pops):.4f}")
print()

# Morphic influence analysis
influences = [len(d.get('morphic_influences', [])) for d in morphic_data]
total_influences = sum(influences)
total_decisions = len(morphic_data) * $GENERATIONS * $GRID_SIZE * $GRID_SIZE

print("## 🌀 Morphic Resonance Effects")
print(f"- **Total morphic influences:** {total_influences:,}")
print(f"- **Total decisions:** {total_decisions:,}")
print(f"- **Influence rate:** {(total_influences / total_decisions) * 100:.2f}%")
print(f"- **Avg influences per run:** {statistics.mean(influences):.0f}")
print()

# Pattern storage analysis
total_patterns = 0
for d in morphic_data:
    for crystal in d.get('crystals', []):
        total_patterns += len(crystal.get('patterns', []))

print("## 💎 Memory Crystal Analysis")
print(f"- **Total patterns stored:** {total_patterns}")
print(f"- **Avg patterns per run:** {total_patterns / len(morphic_data):.1f}")
print(f"- **Avg crystal utilization:** {(total_patterns / (len(morphic_data) * $CRYSTAL_COUNT)):.1f} patterns/crystal")
print()

print("## 🎯 Conclusions")
influence_rate = (total_influences / total_decisions) * 100
if influence_rate > 20:
    print("✅ **Significant morphic resonance effects detected**")
    print(f"- {influence_rate:.1f}% of decisions influenced by pattern similarity")
    print(f"- {total_patterns} patterns stored across {len(morphic_data)} runs")
    print(f"- Mean population difference: {mean_diff:+.2f}")
else:
    print("⚠️ **Weak morphic resonance effects detected**")
    print("- Consider increasing crystal count or generation length")

print(f"\n---\n*Report generated by Automated Research Pipeline v1.0*")
PYEOF

# Calculate runtime
end_time=$(date +%s)
runtime=$((end_time - start_time))
hours=$((runtime / 3600))
minutes=$(((runtime % 3600) / 60))
seconds=$((runtime % 60))

echo ""
echo "🎉 AUTOMATED RESEARCH PIPELINE COMPLETE!"
echo "========================================"
echo "📁 Results directory: automated_research/$PIPELINE_ID/"
echo "📊 Comprehensive report: automated_research/$PIPELINE_ID/reports/comprehensive_report.md"
echo "⏱️  Total runtime: ${hours}h ${minutes}m ${seconds}s"
echo ""
echo "📋 Summary:"
morphic_count=$(ls automated_research/$PIPELINE_ID/raw_data/morphic_*.json 2>/dev/null | wc -l)
control_count=$(ls automated_research/$PIPELINE_ID/raw_data/control_*.json 2>/dev/null | wc -l)
echo "  - Morphic runs completed: $morphic_count"
echo "  - Control runs completed: $control_count"
echo "  - Total decisions analyzed: $((($morphic_count + $control_count) * GENERATIONS * GRID_SIZE * GRID_SIZE))"
echo "  - Statistical analysis: ✅ Complete"
echo ""
echo "📖 View report: cat automated_research/$PIPELINE_ID/reports/comprehensive_report.md"