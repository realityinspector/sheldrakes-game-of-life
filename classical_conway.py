#!/usr/bin/env python3
"""
Classical Conway's Game of Life Implementation
Pure mathematical rules without LLM influence for apples-to-apples comparison
"""

import numpy as np
import json
import time
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import argparse


@dataclass
class ConwayConfig:
    """Configuration for classical Conway simulation"""
    grid_size: int = 25
    generations: int = 100
    initial_density: float = 0.4
    random_seed: Optional[int] = None
    output_file: Optional[str] = None


class ClassicalConway:
    """Pure Conway's Game of Life implementation"""
    
    def __init__(self, config: ConwayConfig):
        self.config = config
        self.grid = None
        self.generation_data = []
        
        # Set random seed for reproducibility
        if config.random_seed is not None:
            np.random.seed(config.random_seed)
    
    def initialize_grid(self) -> np.ndarray:
        """Initialize random grid with specified density"""
        self.grid = np.random.random((self.config.grid_size, self.config.grid_size))
        self.grid = (self.grid < self.config.initial_density).astype(int)
        return self.grid.copy()
    
    def count_neighbors(self, grid: np.ndarray, row: int, col: int) -> int:
        """Count live neighbors for a cell using classical rules"""
        neighbors = 0
        rows, cols = grid.shape
        
        # Check all 8 neighboring cells
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:  # Skip the cell itself
                    continue
                
                nr, nc = (row + dr) % rows, (col + dc) % cols  # Wrap around
                neighbors += grid[nr, nc]
        
        return neighbors
    
    def apply_conway_rules(self, grid: np.ndarray) -> np.ndarray:
        """Apply classical Conway's Game of Life rules"""
        new_grid = np.zeros_like(grid)
        rows, cols = grid.shape
        
        for row in range(rows):
            for col in range(cols):
                neighbors = self.count_neighbors(grid, row, col)
                cell_alive = grid[row, col]
                
                # Classic Conway rules:
                # 1. Any live cell with 2-3 neighbors survives
                # 2. Any dead cell with exactly 3 neighbors becomes alive
                # 3. All other cells die or stay dead
                if cell_alive:
                    if neighbors in [2, 3]:
                        new_grid[row, col] = 1
                else:
                    if neighbors == 3:
                        new_grid[row, col] = 1
        
        return new_grid
    
    def calculate_metrics(self, populations: List[int]) -> Dict:
        """Calculate simulation metrics"""
        if not populations:
            return {}
        
        # Basic statistics
        final_pop = populations[-1]
        max_pop = max(populations)
        avg_pop = np.mean(populations)
        
        # Stability score (low variance = high stability)
        if len(populations) > 20:
            recent_pops = populations[-20:]
            stability = 1.0 - (np.std(recent_pops) / (np.mean(recent_pops) + 1e-6))
        else:
            stability = 0.0
        
        # Complexity score (entropy-like measure)
        if max_pop > 0:
            complexity = 1.0 - abs(final_pop - avg_pop) / max_pop
        else:
            complexity = 0.0
        
        # Count emergence events (50%+ population jumps)
        emergence_events = sum(1 for i in range(1, len(populations))
                             if populations[i] > populations[i-1] * 1.5)
        
        return {
            'final_population': int(final_pop),
            'max_population': int(max_pop),
            'avg_population': float(avg_pop),
            'stability_score': float(max(0.0, min(1.0, stability))),
            'complexity_score': float(max(0.0, min(1.0, complexity))),
            'emergence_events': int(emergence_events),
            'total_generations': len(populations)
        }
    
    def run_simulation(self) -> Dict:
        """Run complete classical Conway simulation"""
        print(f"🎮 Starting Classical Conway's Game of Life")
        print(f"   Grid: {self.config.grid_size}x{self.config.grid_size}")
        print(f"   Generations: {self.config.generations}")
        print(f"   Initial Density: {self.config.initial_density}")
        
        # Initialize
        initial_grid = self.initialize_grid()
        initial_population = int(np.sum(initial_grid))
        current_grid = initial_grid.copy()
        
        populations = []
        start_time = time.time()
        
        # Run generations
        for generation in range(self.config.generations):
            population = int(np.sum(current_grid))
            populations.append(population)
            
            # Store generation data
            self.generation_data.append({
                'generation': generation,
                'population': population,
                'timestamp': datetime.now().isoformat()
            })
            
            # Progress reporting
            if generation % max(1, self.config.generations // 10) == 0:
                progress = (generation / self.config.generations) * 100
                print(f"   🔄 Generation {generation:4d}/{self.config.generations} "
                      f"({progress:5.1f}%) - Population: {population:4d}")
            
            # Apply Conway rules for next generation
            if generation < self.config.generations - 1:  # Don't compute next gen on last iteration
                current_grid = self.apply_conway_rules(current_grid)
        
        # Calculate final metrics
        end_time = time.time()
        runtime = end_time - start_time
        metrics = self.calculate_metrics(populations)
        
        # Compile results
        results = {
            'simulation_type': 'classical_conway',
            'config': {
                'grid_size': self.config.grid_size,
                'generations': self.config.generations,
                'initial_density': self.config.initial_density,
                'random_seed': self.config.random_seed
            },
            'runtime_seconds': float(runtime),
            'initial_population': int(initial_population),
            'generation_data': self.generation_data,
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        }
        
        # Print summary
        print(f"\n📊 Classical Conway Simulation Complete!")
        print(f"   Final Population: {metrics['final_population']}")
        print(f"   Max Population: {metrics['max_population']}")
        print(f"   Avg Population: {metrics['avg_population']:.1f}")
        print(f"   Stability Score: {metrics['stability_score']:.3f}")
        print(f"   Complexity Score: {metrics['complexity_score']:.3f}")
        print(f"   Emergence Events: {metrics['emergence_events']}")
        print(f"   Runtime: {runtime:.2f}s")
        
        return results
    
    def save_results(self, results: Dict, filename: Optional[str] = None) -> str:
        """Save simulation results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"results/classical_conway_{timestamp}.json"
        
        # Ensure results directory exists
        import os
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"💾 Results saved to: {filename}")
        return filename


def main():
    """Command line interface for classical Conway simulation"""
    parser = argparse.ArgumentParser(description='Classical Conway\'s Game of Life')
    parser.add_argument('--grid-size', type=int, default=25,
                       help='Grid size (default: 25)')
    parser.add_argument('--generations', type=int, default=100,
                       help='Number of generations (default: 100)')
    parser.add_argument('--initial-density', type=float, default=0.4,
                       help='Initial population density (default: 0.4)')
    parser.add_argument('--seed', type=int, default=None,
                       help='Random seed for reproducibility')
    parser.add_argument('--output', type=str, default=None,
                       help='Output file path')
    parser.add_argument('--quiet', action='store_true',
                       help='Suppress progress output')
    
    args = parser.parse_args()
    
    # Create configuration
    config = ConwayConfig(
        grid_size=args.grid_size,
        generations=args.generations,
        initial_density=args.initial_density,
        random_seed=args.seed,
        output_file=args.output
    )
    
    # Run simulation
    simulator = ClassicalConway(config)
    results = simulator.run_simulation()
    
    # Save results
    output_file = simulator.save_results(results, args.output)
    
    return results


if __name__ == "__main__":
    main()