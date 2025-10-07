# Quick Start: Phase 2 Time Series Generation

Fast guide to generating morphic field datasets.

---

## 🚀 Run Your First Parameter Sweep

### 1. Test Configuration
```bash
# Verify setup
./venv/bin/python morphic_config.py
```

### 2. Single Simulation Test
```bash
# Run one morphic simulation with custom parameters
./venv/bin/python scripts/run_simulation.py morphic 50 5 25 0.8 0.1 0.7 2.0
#                                           mode  gen cr grid fs  td  st  ie

# Check output
ls timeseries_data/morphic_*.json
```

### 3. Small Batch Run
```bash
# Dry run to see what will be generated
./venv/bin/python batch_runner.py --experiment-type=focused --dry-run --limit=5

# Actually run 5 experiments
./venv/bin/python batch_runner.py --experiment-type=focused --limit=5

# Check results
ls -lh timeseries_data/
cat timeseries_data/manifest.json
```

---

## 📊 Generate Research Datasets

### Focused Studies (Recommended First)

**Temporal Decay Study** (4 runs):
```bash
./venv/bin/python batch_runner.py --experiment-type=focused
# Generates: decay_study_00 through decay_study_09
```

**Field Strength Study** (5 runs):
```bash
# Already included in focused experiments
# Tests field strengths: 0.1, 0.3, 0.5, 0.7, 0.9
```

**Similarity Threshold Study** (4 runs):
```bash
# Also included in focused experiments
# Tests thresholds: 0.3, 0.5, 0.7, 0.9
```

### Full Parameter Sweep (240+ runs)

```bash
# Generate complete dataset
./venv/bin/python batch_runner.py --experiment-type=full

# This creates:
# - 20 control runs (no morphic field)
# - 240 morphic runs (all parameter combinations)
```

**Parameter coverage**:
- Field strengths: 5 values [0.2, 0.4, 0.6, 0.8, 1.0]
- Temporal decays: 4 values [0.0, 0.1, 0.5, 0.9]
- Similarity thresholds: 3 values [0.5, 0.7, 0.9]
- Influence exponents: 2 values [1.0, 2.0]

**Total**: 5 × 4 × 3 × 2 = 120 combinations × 2 (for reproducibility) = 240 runs

### Custom Parameter Ranges

Edit `batch_runner.py` to customize:

```python
# Around line 72-75
field_strengths = [0.1, 0.3, 0.5, 0.7, 0.9]  # Your values here
temporal_decays = [0.0, 0.2, 0.5, 0.8]       # Your values here
similarity_thresholds = [0.4, 0.6, 0.8]      # Your values here
```

---

## 🔍 Analyze Results

### Quick Stats

```bash
# Count experiments
ls timeseries_data/*.json | wc -l

# Check manifest
cat timeseries_data/manifest.json | jq '.total_experiments'

# View parameter distribution
cat timeseries_data/manifest.json | jq '.parameters'
```

### Examine Single Run

```bash
# Pretty-print a run
cat timeseries_data/morphic_20251007_092501.json | jq '.'

# Extract just the time series
cat timeseries_data/morphic_*.json | jq '.timeseries'

# Get summary statistics
cat timeseries_data/morphic_*.json | jq '.summary_stats'
```

### Python Analysis

```python
import json
import glob
from pathlib import Path

# Load all runs
runs = []
for file in Path('timeseries_data').glob('*.json'):
    if file.name != 'manifest.json':
        with open(file) as f:
            runs.append(json.load(f))

# Analyze
print(f"Total runs: {len(runs)}")
print(f"Modes: {set(r['mode'] for r in runs)}")

# Compare morphic vs control
morphic = [r for r in runs if r['mode'] == 'morphic']
control = [r for r in runs if r['mode'] == 'control']

avg_pop_morphic = sum(r['summary_stats']['avg_population'] for r in morphic) / len(morphic)
avg_pop_control = sum(r['summary_stats']['avg_population'] for r in control) / len(control)

print(f"Avg population (morphic): {avg_pop_morphic:.1f}")
print(f"Avg population (control): {avg_pop_control:.1f}")
```

---

## 🎯 Preset Configurations

Use built-in presets for common scenarios:

```bash
# Via Python
./venv/bin/python -c "
from morphic_config import get_preset
config = get_preset('strong_field')
print(config)
"

# Via training.sh (manual parameters)
./training.sh --mode=morphic \
  --field-strength=0.9 \
  --temporal-decay=0.05 \
  --similarity-threshold=0.5 \
  --generations=200
```

**Available presets**:
- `no_field`: Pure control (field_strength=0.0)
- `weak_field`: Subtle influence (0.3, decay=0.5, threshold=0.8)
- `moderate_field`: Balanced (0.6, decay=0.1, threshold=0.7) [default]
- `strong_field`: High influence (0.9, decay=0.05, threshold=0.5)
- `no_decay`: Immortal crystals (decay=0.0)
- `rapid_decay`: Fast aging (decay=0.9)

---

## ⚙️ Parameter Guide

### Field Strength (0.0 - 1.0)
- **0.0**: Pure Conway, no morphic influence
- **0.3**: Weak field, occasional influence
- **0.6**: Moderate field, balanced dynamics
- **0.9**: Strong field, high morphic control
- **1.0**: Maximum influence

### Temporal Decay (0.0 - 1.0)
- **0.0**: No aging, crystals remain potent forever
- **0.1**: Slow decay, crystals effective for ~100 generations
- **0.5**: Moderate decay, ~20 generation half-life
- **0.9**: Rapid decay, crystals age quickly

### Similarity Threshold (0.0 - 1.0)
- **0.3**: Loose matching, frequent influence
- **0.5**: Moderate matching
- **0.7**: Strict matching (default)
- **0.9**: Very strict, rare matches

### Influence Exponent (0.5 - 5.0)
- **1.0**: Linear similarity → influence
- **2.0**: Quadratic (default) - rewards high similarity
- **3.0**: Cubic - strongly non-linear

---

## 📁 Output Structure

```
timeseries_data/
├── manifest.json                    # Dataset metadata
├── control_001.json                 # Control runs
├── control_002.json
├── morphic_001.json                 # Morphic runs
├── morphic_002.json
├── decay_study_00.json              # Named studies
├── strength_study_03.json
└── threshold_study_07.json

results/
└── simulation_morphic_*.json        # Full detailed results (larger files)
```

---

## 🐛 Troubleshooting

### "No module named morphic_config"
```bash
# Make sure you're in the project root
pwd
# Should be: .../sheldrakes-game-of-life

# Verify file exists
ls morphic_config.py
```

### Simulations running slowly
```bash
# Reduce generations for testing
./venv/bin/python batch_runner.py --limit=5

# Or edit batch_runner.py line ~67:
# generations=50  # Instead of 200
```

### Time series files not created
```bash
# Check if directory exists
ls -ld timeseries_data/

# Create if needed
mkdir -p timeseries_data

# Check write permissions
touch timeseries_data/test.txt && rm timeseries_data/test.txt
```

---

## 🎓 Next Steps

1. **Generate baseline dataset**: Run 20 control + 20 morphic experiments
   ```bash
   ./venv/bin/python batch_runner.py --experiment-type=focused --limit=40
   ```

2. **Analyze results**: Look for patterns in influence rates vs parameters

3. **Scale up**: Run full parameter sweep overnight
   ```bash
   nohup ./venv/bin/python batch_runner.py --experiment-type=full > sweep.log 2>&1 &
   ```

4. **Phase 3**: Move to ML model training with generated dataset

---

## 📚 See Also

- `PHASE2_IMPLEMENTATION.md` - Detailed implementation notes
- `PLAN.md` - Original implementation plan
- `ROADMAP.md` - Overall project vision
- `morphic_config.py` - Configuration module documentation
- `batch_runner.py` - Source code with inline documentation
