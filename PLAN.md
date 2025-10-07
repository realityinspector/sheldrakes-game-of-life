# 📋 Implementation Plan: Time Series Data Generation

**For Claude Code (local coding agent)**

This document explains how to extend the existing emergence simulator to generate large-scale time series data for ML training.

---

## Overview

We need to add **parameterized morphic field controls** and **batch processing** to systematically generate synthetic morphic field data with known ground truth parameters.

---

## Phase 2.1: Parameterize Morphic Field Properties

### Current State
The morphic system has hard-coded behavior:
- Crystal strength is binary (pattern works or doesn't)
- Influence is all-or-nothing based on similarity threshold
- No temporal decay of crystal influence
- No cross-run coupling

### Required Changes

#### 1. Add Morphic Field Parameters to Configuration

**File**: `integrated_runs.py` (or new `morphic_config.py`)

Add these parameters to the simulation configuration:

```python
@dataclass
class MorphicFieldConfig:
    """Parameters controlling morphic field behavior"""
    field_strength: float = 0.6  # 0.0-1.0, master influence multiplier
    temporal_decay: float = 0.1  # How fast crystal influence fades (0=no decay, 1=instant decay)
    cross_system_coupling: float = 0.0  # 0.0-1.0, inter-run influence
    similarity_threshold: float = 0.7  # Minimum similarity for morphic influence
    influence_exponent: float = 2.0  # Non-linearity in similarity->influence mapping
```

#### 2. Modify Crystal Influence Calculation

**File**: `integrated_runs.py` (in the morphic decision logic)

Current logic (simplified):
```python
if similarity > 0.8:
    # Apply influence
    influence = crystal_strength * similarity
```

New logic:
```python
# Apply morphic field parameters
if similarity > config.similarity_threshold:
    # Base influence from similarity and crystal strength
    base_influence = crystal_strength * (similarity ** config.influence_exponent)
    
    # Apply temporal decay based on crystal age
    time_factor = np.exp(-config.temporal_decay * crystal_age)
    
    # Apply master field strength
    final_influence = config.field_strength * base_influence * time_factor
    
    # Use this to decide cell fate
    if random.random() < final_influence:
        # Override Conway rule
```

#### 3. Add Crystal Age Tracking

**File**: `integrated_runs.py` (Crystal dataclass)

Add timestamp tracking to crystals:
```python
@dataclass
class Crystal:
    pattern: np.ndarray
    strength: float
    generation_created: int  # NEW: when this crystal was formed
    last_used: int  # NEW: most recent usage
    
    def age(self, current_generation: int) -> int:
        return current_generation - self.generation_created
```

---

## Phase 2.2: Batch Processing Infrastructure

### Goal
Run hundreds of simulations with parameter sweeps automatically.

### Required Components

#### 1. Create Batch Runner Script

**New File**: `batch_runner.py`

```python
#!/usr/bin/env python3
"""
Batch runner for parameter sweep experiments
"""

from dataclasses import dataclass, asdict
from typing import List
import json
import itertools
from pathlib import Path
import subprocess

@dataclass
class ExperimentConfig:
    run_id: str
    mode: str  # 'morphic', 'llm_control', 'classical'
    generations: int
    grid_size: int
    crystal_count: int
    
    # Morphic field parameters
    field_strength: float
    temporal_decay: float
    cross_system_coupling: float
    similarity_threshold: float

def generate_parameter_sweep() -> List[ExperimentConfig]:
    """Generate all parameter combinations"""
    
    # Control runs
    controls = [
        ExperimentConfig(
            run_id=f"control_{i}",
            mode="classical",
            generations=200,
            grid_size=25,
            crystal_count=0,
            field_strength=0.0,
            temporal_decay=0.0,
            cross_system_coupling=0.0,
            similarity_threshold=0.0
        )
        for i in range(20)
    ]
    
    # Morphic parameter sweep
    field_strengths = [0.2, 0.4, 0.6, 0.8, 1.0]
    decays = [0.0, 0.1, 0.5, 0.9]
    thresholds = [0.5, 0.7, 0.9]
    
    morphic_runs = []
    run_counter = 0
    
    for fs, decay, thresh in itertools.product(field_strengths, decays, thresholds):
        run_counter += 1
        morphic_runs.append(
            ExperimentConfig(
                run_id=f"morphic_{run_counter}",
                mode="morphic",
                generations=200,
                grid_size=25,
                crystal_count=5,
                field_strength=fs,
                temporal_decay=decay,
                cross_system_coupling=0.0,
                similarity_threshold=thresh
            )
        )
    
    return controls + morphic_runs

def run_experiment(config: ExperimentConfig, output_dir: Path):
    """Execute single simulation"""
    
    # Call training.sh with parameters
    cmd = [
        "./training.sh",
        f"--mode={config.mode}",
        f"--generations={config.generations}",
        f"--grid-size={config.grid_size}",
        f"--crystal-count={config.crystal_count}",
        f"--field-strength={config.field_strength}",
        f"--temporal-decay={config.temporal_decay}",
        f"--similarity-threshold={config.similarity_threshold}",
        f"--run-id={config.run_id}"
    ]
    
    print(f"Running: {config.run_id}")
    subprocess.run(cmd, check=True)
    
    # Save config
    config_file = output_dir / f"{config.run_id}_config.json"
    with open(config_file, 'w') as f:
        json.dump(asdict(config), f, indent=2)

if __name__ == "__main__":
    output_dir = Path("timeseries_data")
    output_dir.mkdir(exist_ok=True)
    
    experiments = generate_parameter_sweep()
    
    print(f"🧬 Running {len(experiments)} experiments...")
    
    for exp in experiments:
        try:
            run_experiment(exp, output_dir)
        except Exception as e:
            print(f"❌ Failed: {exp.run_id} - {e}")
```

#### 2. Modify `training.sh` to Accept Parameters

**File**: `training.sh`

Add argument parsing:
```bash
# Parse command line arguments
FIELD_STRENGTH=0.6
TEMPORAL_DECAY=0.1
SIMILARITY_THRESHOLD=0.7
RUN_ID="run-$(date +%Y%m%d-%H%M%S)-$(openssl rand -hex 4)"

while [[ $# -gt 0 ]]; do
  case $1 in
    --field-strength=*)
      FIELD_STRENGTH="${1#*=}"
      shift
      ;;
    --temporal-decay=*)
      TEMPORAL_DECAY="${1#*=}"
      shift
      ;;
    --similarity-threshold=*)
      SIMILARITY_THRESHOLD="${1#*=}"
      shift
      ;;
    --run-id=*)
      RUN_ID="${1#*=}"
      shift
      ;;
    # ... other args
  esac
done

# Pass to Python script
python integrated_runs.py \
  --mode=$MODE \
  --generations=$GENERATIONS \
  --field-strength=$FIELD_STRENGTH \
  --temporal-decay=$TEMPORAL_DECAY \
  --similarity-threshold=$SIMILARITY_THRESHOLD \
  --run-id=$RUN_ID
```

---

## Phase 2.3: Enhanced Time Series Output

### Goal
Save detailed time series data in structured format for ML training.

### Required Changes

#### Modify Results Storage

**File**: `integrated_runs.py` (results saving section)

Save additional time series data:

```python
def save_timeseries_data(run_slug: str, results: dict):
    """Save detailed time series for ML training"""
    
    timeseries_data = {
        "run_id": run_slug,
        "config": {
            "mode": results['mode'],
            "field_strength": results.get('field_strength', 0.0),
            "temporal_decay": results.get('temporal_decay', 0.0),
            "similarity_threshold": results.get('similarity_threshold', 0.0),
        },
        "timeseries": {
            "population": results['population_history'],
            "complexity": results['complexity_history'],
            "morphic_influence_rate": results.get('influence_rate_history', []),
            "pattern_diversity": results.get('diversity_history', []),
            "crystal_count": results.get('crystal_count_history', []),
            "resonance_events": results.get('resonance_events', []),
        },
        "summary_stats": {
            "final_population": results['final_population'],
            "max_population": max(results['population_history']),
            "avg_population": np.mean(results['population_history']),
            "population_std": np.std(results['population_history']),
            "convergence_generation": results.get('convergence_gen', None),
        }
    }
    
    output_file = Path("timeseries_data") / f"{run_slug}.json"
    with open(output_file, 'w') as f:
        json.dump(timeseries_data, f, indent=2)
```

#### Track Additional Metrics During Simulation

In the main simulation loop, track:
- **Morphic influence rate**: % of cells influenced by crystals each generation
- **Pattern diversity**: Number of unique patterns in current grid
- **Resonance events**: Times when crystal influence was high
- **Crystal utilization**: How often each crystal is used

---

## Phase 2.4: Integration Steps

### Implementation Order

1. **Add morphic field parameters** to config (2 hours)
   - Create `MorphicFieldConfig` dataclass
   - Add parameters to command line parsing
   - Pass through to simulation engine

2. **Modify crystal influence calculation** (3 hours)
   - Implement temporal decay
   - Add field strength multiplier
   - Add similarity exponent
   - Add crystal age tracking

3. **Create batch runner** (4 hours)
   - Write `batch_runner.py`
   - Modify `training.sh` for parameter passing
   - Test with small parameter sweep (3 runs)

4. **Enhanced metrics tracking** (3 hours)
   - Add influence rate tracking
   - Add pattern diversity calculation
   - Add resonance event detection
   - Modify results saving

5. **Full parameter sweep** (runtime: ~8-24 hours depending on hardware)
   - Run 100+ simulations
   - Validate data quality
   - Create manifest file

---

## Testing Strategy

### Unit Tests
- Test morphic field parameter application
- Test temporal decay calculation
- Test crystal age tracking
- Test parameter sweep generation

### Integration Tests
- Run 3 simulations with different field strengths
- Verify output files contain expected data
- Verify metrics are tracked correctly

### Validation
- Confirm control runs (field_strength=0) match classical behavior
- Confirm high field strength runs show increased influence
- Check that temporal decay reduces old crystal influence

---

## Expected Outputs

After implementation:

```
timeseries_data/
├── manifest.json (metadata about dataset)
├── control_1.json
├── control_2.json
├── ...
├── morphic_1.json (field_strength=0.2, decay=0.0, threshold=0.5)
├── morphic_2.json (field_strength=0.2, decay=0.0, threshold=0.7)
├── ...
└── morphic_80.json
```

Each JSON contains full time series data ready for ML training.

---

## Next Phase Preview

Once data generation is complete, Phase 3 will:
1. Extract features from time series
2. Train classification models (morphic vs control)
3. Train regression models (estimate field strength)
4. Analyze learned representations in embedding space

---

## Questions for Developer

1. Should cross-system coupling (runs influencing each other) be implemented now or deferred to later?
2. What's the preferred location for morphic field config? New file or integrate into existing?
3. Should we add visualization of field parameters to the web interface?

---

*This plan maintains compatibility with existing code while adding the parameterization needed for systematic data generation.*