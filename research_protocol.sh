#!/bin/bash
# Complete Research Protocol - Publication-ready study

echo "🧬 COMPREHENSIVE MORPHIC RESONANCE RESEARCH STUDY"
echo "================================================="

# Parameters for rigorous study
STUDY_NAME="morphic_resonance_$(date +%Y%m%d)"
SAMPLE_SIZE=20
GENERATIONS=150
GRID_SIZE=22
CRYSTAL_COUNT=8

mkdir -p studies/$STUDY_NAME/{morphic,control,analysis}

# Phase 1: Control group (n=20)
echo "Phase 1: Control Group (n=$SAMPLE_SIZE)"
for i in $(seq 1 $SAMPLE_SIZE); do
  echo "  Control $i/$SAMPLE_SIZE..."
  ./training.sh --mode=control --generations=$GENERATIONS --grid-size=$GRID_SIZE
  if ls results/simulation_control_*.json 1> /dev/null 2>&1; then
    latest=$(ls -t results/simulation_control_*.json | head -1)
    mv "$latest" studies/$STUDY_NAME/control/control_$(printf "%02d" $i).json
  fi
done

# Phase 2: Morphic group (n=20)
echo "Phase 2: Morphic Group (n=$SAMPLE_SIZE)"
export OPENROUTER_API_KEY="your_key"  # Replace with actual key
for i in $(seq 1 $SAMPLE_SIZE); do
  echo "  Morphic $i/$SAMPLE_SIZE..."
  ./training.sh --mode=morphic --generations=$GENERATIONS --crystal-count=$CRYSTAL_COUNT --grid-size=$GRID_SIZE
  if ls results/simulation_morphic_*.json 1> /dev/null 2>&1; then
    latest=$(ls -t results/simulation_morphic_*.json | head -1)
    mv "$latest" studies/$STUDY_NAME/morphic/morphic_$(printf "%02d" $i).json
  fi
done

# Phase 3: Statistical analysis
echo "Phase 3: Statistical Analysis"

# Get the actual study name for Python script
ACTUAL_STUDY_NAME="$STUDY_NAME"

python3 > studies/$STUDY_NAME/analysis/statistical_report.txt << PYEOF
import json, glob, statistics
import numpy as np
try:
    from scipy import stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    print("Note: scipy not available, using simplified statistics")

STUDY_NAME = "$ACTUAL_STUDY_NAME"

# Load data
control_data = []
morphic_data = []
influence_data = []

for file in glob.glob(f'studies/{STUDY_NAME}/control/*.json'):
    with open(file) as f:
        data = json.load(f)
        control_data.append({
            'avg_population': data['avg_population'],
            'final_population': data['final_population'],
            'stability_score': data['stability_score'],
            'complexity_score': data['complexity_score']
        })

for file in glob.glob(f'studies/{STUDY_NAME}/morphic/*.json'):
    with open(file) as f:
        data = json.load(f)
        morphic_data.append({
            'avg_population': data['avg_population'],
            'final_population': data['final_population'],
            'stability_score': data['stability_score'],
            'complexity_score': data['complexity_score'],
            'morphic_influences': len(data.get('morphic_influences', []))
        })
        influence_data.append(len(data.get('morphic_influences', [])))

# Statistical analysis
print("MORPHIC RESONANCE RESEARCH STUDY RESULTS")
print("=" * 50)
print(f"Sample Size: {len(control_data)} control, {len(morphic_data)} morphic")
print()

# Population metrics
control_pop = [d['avg_population'] for d in control_data]
morphic_pop = [d['avg_population'] for d in morphic_data]

print("POPULATION ANALYSIS:")
print(f"Control avg population: {statistics.mean(control_pop):.2f} ± {statistics.stdev(control_pop):.2f}")
print(f"Morphic avg population: {statistics.mean(morphic_pop):.2f} ± {statistics.stdev(morphic_pop):.2f}")

# Statistical testing
if HAS_SCIPY and len(control_pop) > 1 and len(morphic_pop) > 1:
    t_stat, p_value = stats.ttest_ind(control_pop, morphic_pop)
    print(f"T-test p-value: {p_value:.6f}")
    print(f"Significant difference: {'Yes' if p_value < 0.05 else 'No'}")
else:
    mean_diff = statistics.mean(morphic_pop) - statistics.mean(control_pop)
    print(f"Mean difference: {mean_diff:.4f}")
    print("T-test: Not available (requires scipy and n>1)")
print()

# Morphic influence analysis
print("MORPHIC INFLUENCE ANALYSIS:")
if influence_data:
    print(f"Avg morphic influences per run: {statistics.mean(influence_data):.0f}")
    print(f"Total morphic decisions: {sum(influence_data)}")
    print(f"Influence rate: {(sum(influence_data) / (len(morphic_data) * $GENERATIONS * $GRID_SIZE * $GRID_SIZE)) * 100:.1f}%")
else:
    print("No morphic influence data found")
print()

# Effect size (Cohen's d)
if len(control_pop) > 1 and len(morphic_pop) > 1:
    try:
        import numpy as np
        pooled_std = np.sqrt(((len(control_pop)-1)*np.var(control_pop) + (len(morphic_pop)-1)*np.var(morphic_pop)) / (len(control_pop)+len(morphic_pop)-2))
        cohens_d = (statistics.mean(morphic_pop) - statistics.mean(control_pop)) / pooled_std
        print(f"Effect size (Cohen's d): {cohens_d:.3f}")
        print(f"Effect magnitude: {'Small' if abs(cohens_d) < 0.5 else 'Medium' if abs(cohens_d) < 0.8 else 'Large'}")
    except:
        print("Effect size calculation failed (requires numpy)")
else:
    print("Effect size: Not available (insufficient data)")
PYEOF

echo "✅ Publication study complete!"
echo "📊 Results available in: studies/$STUDY_NAME/"
echo "📄 Statistical report: studies/$STUDY_NAME/analysis/statistical_report.txt"