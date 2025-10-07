#!/usr/bin/env python3
"""Quick batch test with SHORT simulations for testing output"""

from batch_runner import *
from rich.console import Console

console = Console()

# Generate ONE quick experiment
experiments = [{
    'run_id': 'quick_test',
    'mode': 'morphic',
    'config': {
        'generations': 30,  # SHORT for testing
        'crystal_count': 3,
        'grid_size': 15,
        'field_strength': 0.6,
        'temporal_decay': 0.1,
        'similarity_threshold': 0.7,
        'influence_exponent': 2.0
    }
}]

console.print("\n[bold magenta]🧪 Quick Batch Output Test[/bold magenta]")
console.print("[bold magenta]=" * 30 + "[/bold magenta]\n")
console.print(f"[cyan]Running 1 experiment with 30 generations[/cyan]\n")

output_dir = Path('timeseries_data')
output_dir.mkdir(parents=True, exist_ok=True)

console.print("[bold green]▶ Starting test...[/bold green]\n")

success = run_experiment(experiments[0], output_dir, console, verbose=False)

if success:
    console.print("\n[bold green]✅ TEST PASSED - Real-time output working![/bold green]")
else:
    console.print("\n[bold red]❌ TEST FAILED[/bold red]")
