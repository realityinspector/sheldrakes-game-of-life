#!/usr/bin/env python3
"""
Batch Runner for Parameter Sweep Experiments

Orchestrates execution of multiple simulations with varying morphic field parameters
for systematic data generation.
"""

import argparse
import itertools
import json
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import List

from morphic_config import MorphicFieldConfig


def generate_control_runs(count: int = 20) -> List[dict]:
    """Generate control runs (no morphic field)"""
    control_runs = []

    for i in range(count):
        config = MorphicFieldConfig(
            field_strength=0.0,
            temporal_decay=0.0,
            similarity_threshold=1.0,  # Impossible threshold
            crystal_count=0,  # No crystals for control
            generations=200,
            grid_size=25,
            initial_density=0.4
        )

        control_runs.append({
            'run_id': f'control_{i:03d}',
            'mode': 'control',  # Classical mode
            'config': config.to_dict()
        })

    return control_runs


def generate_morphic_parameter_sweep() -> List[dict]:
    """Generate morphic runs with parameter sweep"""
    morphic_runs = []

    # Define parameter ranges
    field_strengths = [0.2, 0.4, 0.6, 0.8, 1.0]
    temporal_decays = [0.0, 0.1, 0.5, 0.9]
    similarity_thresholds = [0.5, 0.7, 0.9]
    influence_exponents = [1.0, 2.0]  # Added exponent variation

    run_counter = 0

    # Generate all combinations
    for fs, decay, thresh, exp in itertools.product(
        field_strengths, temporal_decays, similarity_thresholds, influence_exponents
    ):
        run_counter += 1

        config = MorphicFieldConfig(
            field_strength=fs,
            temporal_decay=decay,
            similarity_threshold=thresh,
            influence_exponent=exp,
            crystal_count=5,
            generations=200,
            grid_size=25,
            initial_density=0.4
        )

        morphic_runs.append({
            'run_id': f'morphic_{run_counter:03d}',
            'mode': 'morphic',
            'config': config.to_dict()
        })

    return morphic_runs


def generate_focused_experiments() -> List[dict]:
    """Generate focused experiments for specific hypotheses"""
    experiments = []

    # Experiment 1: No decay vs rapid decay at same field strength
    for decay in [0.0, 0.1, 0.5, 0.9]:
        config = MorphicFieldConfig(
            field_strength=0.6,
            temporal_decay=decay,
            similarity_threshold=0.7,
            crystal_count=5,
            generations=200
        )
        experiments.append({
            'run_id': f'decay_study_{int(decay*10):02d}',
            'mode': 'morphic',
            'config': config.to_dict()
        })

    # Experiment 2: Field strength variation with no decay
    for strength in [0.1, 0.3, 0.5, 0.7, 0.9]:
        config = MorphicFieldConfig(
            field_strength=strength,
            temporal_decay=0.0,
            similarity_threshold=0.7,
            crystal_count=5,
            generations=200
        )
        experiments.append({
            'run_id': f'strength_study_{int(strength*10):02d}',
            'mode': 'morphic',
            'config': config.to_dict()
        })

    # Experiment 3: Similarity threshold variation
    for thresh in [0.3, 0.5, 0.7, 0.9]:
        config = MorphicFieldConfig(
            field_strength=0.6,
            temporal_decay=0.1,
            similarity_threshold=thresh,
            crystal_count=5,
            generations=200
        )
        experiments.append({
            'run_id': f'threshold_study_{int(thresh*10):02d}',
            'mode': 'morphic',
            'config': config.to_dict()
        })

    return experiments


def run_experiment(experiment: dict, output_dir: Path, python_cmd: str = './venv/bin/python') -> bool:
    """Execute a single simulation experiment"""

    run_id = experiment['run_id']
    mode = experiment['mode']
    config = experiment['config']

    print(f"🧬 Running: {run_id}")
    print(f"   Mode: {mode}")
    print(f"   Field: {config['field_strength']:.2f}, Decay: {config['temporal_decay']:.2f}")

    try:
        # Build command
        cmd = [
            python_cmd,
            'scripts/run_simulation.py',
            mode,
            str(config['generations']),
            str(config['crystal_count']),
            str(config['grid_size']),
            str(config['field_strength']),
            str(config['temporal_decay']),
            str(config['similarity_threshold']),
            str(config.get('influence_exponent', 2.0))
        ]

        # Run simulation
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode == 0:
            print(f"   ✅ Success")

            # Find the output file (most recent in results/)
            results_dir = Path('results')
            pattern = f'simulation_{mode}_*.json'

            # Get most recent matching file
            files = list(results_dir.glob(pattern))
            if files:
                latest_file = max(files, key=lambda p: p.stat().st_mtime)

                # Copy to timeseries directory with run_id
                output_file = output_dir / f'{run_id}.json'

                # Load, add metadata, and save
                with open(latest_file, 'r') as f:
                    data = json.load(f)

                data['run_id'] = run_id
                data['config'] = config

                with open(output_file, 'w') as f:
                    json.dump(data, f, indent=2)

                print(f"   📁 Saved to: {output_file}")

                # Save config separately for easy reference
                config_file = output_dir / f'{run_id}_config.json'
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=2)

            return True
        else:
            print(f"   ❌ Failed")
            print(f"   Error: {result.stderr[:200]}")
            return False

    except subprocess.TimeoutExpired:
        print(f"   ⏰ Timeout")
        return False
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False


def generate_manifest(experiments: List[dict], output_dir: Path):
    """Generate manifest file describing the dataset"""

    manifest = {
        'generated_at': datetime.now().isoformat(),
        'total_experiments': len(experiments),
        'experiment_types': {},
        'parameters': {
            'field_strength': [],
            'temporal_decay': [],
            'similarity_threshold': [],
            'influence_exponent': []
        },
        'experiments': []
    }

    # Collect statistics
    for exp in experiments:
        mode = exp['mode']
        config = exp['config']

        # Count by mode
        if mode not in manifest['experiment_types']:
            manifest['experiment_types'][mode] = 0
        manifest['experiment_types'][mode] += 1

        # Collect parameter values
        if mode == 'morphic':
            manifest['parameters']['field_strength'].append(config['field_strength'])
            manifest['parameters']['temporal_decay'].append(config['temporal_decay'])
            manifest['parameters']['similarity_threshold'].append(config['similarity_threshold'])
            manifest['parameters']['influence_exponent'].append(config.get('influence_exponent', 2.0))

        # Add experiment entry
        manifest['experiments'].append({
            'run_id': exp['run_id'],
            'mode': mode,
            'config': config
        })

    # Get unique parameter values
    for param in ['field_strength', 'temporal_decay', 'similarity_threshold', 'influence_exponent']:
        values = manifest['parameters'][param]
        if values:
            manifest['parameters'][param] = sorted(list(set(values)))

    # Save manifest
    manifest_file = output_dir / 'manifest.json'
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"📋 Manifest saved to: {manifest_file}")

    return manifest


def main():
    parser = argparse.ArgumentParser(description='Batch parameter sweep for morphic field experiments')
    parser.add_argument('--experiment-type', choices=['full', 'control', 'morphic', 'focused'], default='focused',
                        help='Type of experiment sweep to run')
    parser.add_argument('--output-dir', type=str, default='timeseries_data',
                        help='Output directory for results')
    parser.add_argument('--python', type=str, default='./venv/bin/python',
                        help='Python interpreter to use')
    parser.add_argument('--dry-run', action='store_true',
                        help='Generate experiment list without running')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit number of experiments (for testing)')

    args = parser.parse_args()

    print("🚀 Morphic Field Parameter Sweep")
    print("=" * 60)

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Output directory: {output_dir}")

    # Generate experiment list
    experiments = []

    if args.experiment_type == 'control':
        experiments = generate_control_runs()
    elif args.experiment_type == 'morphic':
        experiments = generate_morphic_parameter_sweep()
    elif args.experiment_type == 'focused':
        experiments = generate_focused_experiments()
    else:  # full
        experiments = generate_control_runs(20) + generate_morphic_parameter_sweep()

    # Apply limit if specified
    if args.limit:
        experiments = experiments[:args.limit]

    print(f"📊 Generated {len(experiments)} experiments")

    # Generate manifest
    manifest = generate_manifest(experiments, output_dir)

    if args.dry_run:
        print("\n🔍 Dry run - showing first 5 experiments:")
        for exp in experiments[:5]:
            print(f"  - {exp['run_id']}: {exp['mode']}, field={exp['config']['field_strength']:.2f}")
        print(f"\n✅ Would run {len(experiments)} experiments")
        return

    # Run experiments
    print(f"\n🏃 Running {len(experiments)} experiments...")
    print("=" * 60)

    success_count = 0
    fail_count = 0

    for i, exp in enumerate(experiments, 1):
        print(f"\n[{i}/{len(experiments)}]")
        success = run_experiment(exp, output_dir, args.python)

        if success:
            success_count += 1
        else:
            fail_count += 1

        # Brief pause between runs
        if i < len(experiments):
            import time
            time.sleep(1)

    # Summary
    print("\n" + "=" * 60)
    print("🏁 Batch Run Complete!")
    print(f"   ✅ Successful: {success_count}")
    print(f"   ❌ Failed: {fail_count}")
    print(f"   📁 Results: {output_dir}")
    print(f"   📋 Manifest: {output_dir / 'manifest.json'}")


if __name__ == '__main__':
    main()
