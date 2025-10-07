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
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import List

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn, TextColumn
from rich.live import Live
from rich.table import Table

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


def run_experiment(experiment: dict, output_dir: Path, console: Console, verbose: bool = False) -> bool:
    """Execute a single simulation experiment with real-time logging"""

    run_id = experiment['run_id']
    mode = experiment['mode']
    config = experiment['config']

    # Print experiment header
    console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
    console.print(f"[bold green]▶ Starting:[/bold green] {run_id}")
    console.print(f"[cyan]  Mode:[/cyan] {mode}")
    console.print(f"[cyan]  Generations:[/cyan] {config['generations']}")
    console.print(f"[cyan]  Grid:[/cyan] {config['grid_size']}×{config['grid_size']}")

    if mode == 'morphic':
        console.print(f"[yellow]  Field Strength:[/yellow] {config['field_strength']}")
        console.print(f"[yellow]  Temporal Decay:[/yellow] {config['temporal_decay']}")
        console.print(f"[yellow]  Similarity Threshold:[/yellow] {config['similarity_threshold']}")

    console.print(f"[bold cyan]{'='*60}[/bold cyan]\n")

    start_time = time.time()

    try:
        # Build command
        cmd = [
            './training.sh',
            f'--mode={mode}',
            f'--generations={config["generations"]}',
            f'--grid-size={config["grid_size"]}',
            f'--crystal-count={config["crystal_count"]}',
        ]

        if mode == 'morphic':
            cmd.extend([
                f'--field-strength={config["field_strength"]}',
                f'--temporal-decay={config["temporal_decay"]}',
                f'--similarity-threshold={config["similarity_threshold"]}',
            ])

        # Run with live output streaming
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # Stream output in real-time
        for line in process.stdout:
            line = line.rstrip()
            if not line:
                continue

            # Color-code output based on content
            # ALWAYS show generation progress (not just in verbose mode)
            if 'Generation' in line or '🔄' in line:
                # Use print with flush for real-time updates
                print(line, flush=True)
            elif 'ERROR' in line or '❌' in line or 'Failed' in line:
                console.print(f"[bold red]{line}[/bold red]")
            elif 'SUCCESS' in line or '✅' in line or 'Complete' in line:
                console.print(f"[green]{line}[/green]")
            elif 'WARNING' in line or '⚠️' in line:
                console.print(f"[yellow]{line}[/yellow]")
            elif '💎' in line or '📊' in line or '💾' in line:
                print(line, flush=True)
            elif verbose:
                print(line, flush=True)

        process.wait()
        elapsed = time.time() - start_time

        if process.returncode == 0:
            console.print(f"\n[bold green]✅ Completed:[/bold green] {run_id}")
            console.print(f"[green]   Duration:[/green] {elapsed:.1f}s\n")

            # Find the output file (most recent in timeseries_data/)
            timeseries_dir = Path('timeseries_data')
            pattern = f'{mode}_*.json'

            # Get most recent matching file
            files = list(timeseries_dir.glob(pattern))
            if files:
                latest_file = max(files, key=lambda p: p.stat().st_mtime)

                # Copy to output directory with run_id
                output_file = output_dir / f'{run_id}.json'

                # Load, add metadata, and save
                with open(latest_file, 'r') as f:
                    data = json.load(f)

                data['run_id'] = run_id
                data['config'] = config

                with open(output_file, 'w') as f:
                    json.dump(data, f, indent=2)

                console.print(f"[dim]   📁 Saved to: {output_file}[/dim]")

                # Save config separately for easy reference
                config_file = output_dir / f'{run_id}_config.json'
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=2)

            return True
        else:
            console.print(f"\n[bold red]❌ Failed:[/bold red] {run_id}")
            console.print(f"[red]   Exit code:[/red] {process.returncode}")
            console.print(f"[red]   Duration:[/red] {elapsed:.1f}s\n")
            return False

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        console.print(f"\n[bold red]⏰ Timeout:[/bold red] {run_id}")
        console.print(f"[red]   Duration:[/red] {elapsed:.1f}s\n")
        return False
    except Exception as e:
        elapsed = time.time() - start_time
        console.print(f"\n[bold red]❌ Exception:[/bold red] {run_id}")
        console.print(f"[red]   Error:[/red] {str(e)}")
        console.print(f"[red]   Duration:[/red] {elapsed:.1f}s\n")
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
    parser.add_argument('--dry-run', action='store_true',
                        help='Generate experiment list without running')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit number of experiments (for testing)')
    parser.add_argument('--verbose', action='store_true',
                        help='Show all output including generation progress (default: condensed)')

    args = parser.parse_args()

    console = Console()

    console.print("\n[bold magenta]🚀 Morphic Field Parameter Sweep[/bold magenta]")
    console.print("[bold magenta]============================================================[/bold magenta]\n")

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"[cyan]📁 Output directory:[/cyan] {output_dir}")

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

    console.print(f"[cyan]📊 Total experiments:[/cyan] {len(experiments)}")

    # Estimate time (rough: 1 minute per 100 generations)
    avg_generations = sum(exp['config']['generations'] for exp in experiments) / len(experiments) if experiments else 0
    estimated_time = len(experiments) * (avg_generations / 100)
    console.print(f"[cyan]⏱️  Estimated time:[/cyan] {estimated_time:.0f}min (rough)\n")

    # Generate manifest
    manifest = generate_manifest(experiments, output_dir)

    if args.dry_run:
        console.print("[yellow]🔍 DRY RUN - No simulations will execute[/yellow]\n")
        for i, exp in enumerate(experiments[:10], 1):
            console.print(f"  [{i}] {exp['run_id']}: {exp['mode']}, field={exp['config']['field_strength']:.2f}")
        if len(experiments) > 10:
            console.print(f"  ... and {len(experiments) - 10} more")
        console.print(f"\n[bold]Would run {len(experiments)} experiments[/bold]")
        sys.exit(0)

    # Run experiments with real-time output
    console.print("[bold green]▶ Starting batch execution...[/bold green]\n")

    successful = 0
    failed = 0
    start_time = time.time()

    for i, exp in enumerate(experiments, 1):
        # Clear progress header
        console.print(f"\n[bold magenta]{'━' * 60}[/bold magenta]")
        console.print(f"[bold blue]📍 Experiment {i}/{len(experiments)}[/bold blue] [dim]({successful}✅ {failed}❌ so far)[/dim]")
        console.print(f"[bold magenta]{'━' * 60}[/bold magenta]")

        success = run_experiment(exp, output_dir, console, verbose=args.verbose)

        if success:
            successful += 1
        else:
            failed += 1

        # Show updated stats after each experiment
        elapsed = time.time() - start_time
        remaining = len(experiments) - i
        avg_time = elapsed / i if i > 0 else 0
        eta = remaining * avg_time

        console.print(f"\n[bold cyan]Progress:[/bold cyan] {i}/{len(experiments)} complete")
        console.print(f"[dim]Stats: ✅ {successful} succeeded, ❌ {failed} failed | "
                     f"Elapsed: {elapsed/60:.1f}min | ETA: {eta/60:.1f}min[/dim]")

        # Brief pause between runs
        if i < len(experiments):
            time.sleep(0.5)

    # Final summary
    total_time = time.time() - start_time
    console.print("\n[bold magenta]{'='*60}[/bold magenta]")
    console.print("[bold magenta]🏁 BATCH COMPLETE[/bold magenta]")
    console.print(f"[green]✅ Successful:[/green] {successful}/{len(experiments)}")
    console.print(f"[red]❌ Failed:[/red] {failed}/{len(experiments)}")
    console.print(f"[cyan]⏱️  Total time:[/cyan] {total_time/60:.1f} minutes")
    console.print(f"[cyan]📁 Data saved to:[/cyan] {output_dir}")
    console.print(f"[cyan]📋 Manifest:[/cyan] {output_dir / 'manifest.json'}")
    console.print("[bold magenta]{'='*60}[/bold magenta]\n")


if __name__ == '__main__':
    main()
