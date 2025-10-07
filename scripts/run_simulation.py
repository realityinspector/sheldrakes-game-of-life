#!/usr/bin/env python3
"""
Standalone simulation runner for training.sh
"""

import sys
import os
import asyncio
import random
import json
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def run_conway_simulation():
    try:
        from storage import get_database_info, create_tables_async

        info = get_database_info()
        print(f'🗄️  Database: {info["type"]} ({info["url"]})')

        # Ensure database is ready
        await create_tables_async()

        # Get parameters from command line
        mode = sys.argv[1] if len(sys.argv) > 1 else 'control'
        generations = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        crystal_count = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        grid_size = int(sys.argv[4]) if len(sys.argv) > 4 else 25

        print(f'🚀 Starting {mode} simulation...')
        print(f'📊 Grid: {grid_size}x{grid_size}, Generations: {generations}')

        # Import pattern similarity module
        import numpy as np
        from core.pattern_similarity import (
            extract_subpatterns,
            calculate_pattern_similarity,
            MarkovPatternPredictor,
            update_crystal_strength_bayesian,
            generate_llm_context,
            get_morphic_influence_for_cell,
            query_llm_for_decision,
            validate_morphic_implementation
        )

        # Initialize grid
        grid = np.array([[random.choice([0, 1]) for _ in range(grid_size)] for _ in range(grid_size)])
        alive_count = np.sum(grid)
        print(f'🌱 Initial population: {alive_count} cells')

        # Import morphic config
        from morphic_config import MorphicFieldConfig

        # Parse morphic field parameters from command line
        field_strength = float(sys.argv[5]) if len(sys.argv) > 5 else 0.6
        temporal_decay = float(sys.argv[6]) if len(sys.argv) > 6 else 0.1
        similarity_threshold = float(sys.argv[7]) if len(sys.argv) > 7 else 0.7
        influence_exponent = float(sys.argv[8]) if len(sys.argv) > 8 else 2.0

        # Create morphic config
        morphic_config = MorphicFieldConfig(
            field_strength=field_strength,
            temporal_decay=temporal_decay,
            similarity_threshold=similarity_threshold,
            influence_exponent=influence_exponent,
            crystal_count=crystal_count,
            generations=generations,
            grid_size=grid_size
        )

        # Memory crystals for morphic mode
        crystals = []
        if mode == 'morphic':
            for i in range(crystal_count):
                crystal = {
                    'id': i + 1,
                    'patterns': [],
                    'strength': random.uniform(0.1, 0.8),
                    'created': datetime.now().isoformat(),
                    'generation_created': 0,  # NEW: track when crystal was created
                    'activation_history': [],
                    'total_successes': 0,
                    'total_trials': 0,
                    'markov_predictor': MarkovPatternPredictor()
                }
                crystals.append(crystal)
            print(f'💎 Initialized {len(crystals)} memory crystals with pattern recognition')
            print(f'⚙️  Field config: strength={field_strength:.2f}, decay={temporal_decay:.2f}, threshold={similarity_threshold:.2f}')

        # Simulation metrics with enhanced tracking
        stats = {
            'mode': mode,
            'grid_size': grid_size,
            'generations': generations,
            'initial_population': alive_count,
            'generation_data': [],
            'crystals': crystals,
            'stability_score': 0,
            'complexity_score': 0,
            'emergence_events': 0,
            'morphic_influences': [],  # Track morphic decision influences

            # Enhanced metrics for time series analysis
            'morphic_config': morphic_config.to_dict() if mode == 'morphic' else {},
            'influence_rate_history': [],  # % of cells influenced each generation
            'pattern_diversity_history': [],  # Unique pattern count
            'crystal_utilization_history': [],  # Crystal usage per generation
            'resonance_events': [],  # High-influence events
            'complexity_evolution': [],  # Complexity over time
            'population_volatility': []  # Population change rate
        }

        print('🔄 Running simulation generations...')

        prev_alive_count = alive_count  # Initialize for first generation

        for gen in range(generations):
            # Conway's Game of Life rules
            new_grid = np.zeros((grid_size, grid_size), dtype=int)
            prev_grid = grid.copy()  # Store for Markov chain updates

            # Track metrics for this generation
            gen_influenced_cells = 0
            gen_total_cells = grid_size * grid_size
            gen_crystal_activations = {c['id']: 0 for c in crystals} if mode == 'morphic' else {}

            for i in range(grid_size):
                for j in range(grid_size):
                    # Count neighbors
                    neighbors = 0
                    for di in [-1, 0, 1]:
                        for dj in [-1, 0, 1]:
                            if di == 0 and dj == 0:
                                continue
                            ni, nj = i + di, j + dj
                            if 0 <= ni < grid_size and 0 <= nj < grid_size:
                                neighbors += grid[ni][nj]

                    # Apply Conway's rules
                    if grid[i][j] == 1:
                        # Live cell
                        if neighbors in [2, 3]:
                            decision = 1  # Stay alive
                        else:
                            decision = 0  # Die
                    else:
                        # Dead cell
                        if neighbors == 3:
                            decision = 1  # Become alive
                        else:
                            decision = 0  # Stay dead

                    # Apply morphic resonance influence at cell level
                    if mode == 'morphic' and crystals:
                        # Extract basic neighborhood for pattern matching (3x3 around cell)
                        neighborhood = grid[max(0,i-1):min(grid_size,i+2),
                                          max(0,j-1):min(grid_size,j+2)]

                        # Get morphic influence for this specific cell with adaptive neighborhood
                        morphic_decision, influence_strength, debug_info = get_morphic_influence_for_cell(
                            neighborhood, crystals, decision,
                            grid=grid, i=i, j=j, grid_size=grid_size,
                            morphic_config=morphic_config, current_generation=gen
                        )

                        # Store influence data for analysis
                        if debug_info.get('reason') == 'morphic_influence':
                            stats['morphic_influences'].append({
                                'generation': gen,
                                'position': [i, j],
                                'conway_decision': decision,
                                'morphic_decision': morphic_decision,
                                'influence_strength': influence_strength,
                                **debug_info
                            })

                            # Track influenced cells
                            if debug_info.get('applied_influence', False):
                                gen_influenced_cells += 1

                            # Track high-influence resonance events
                            if influence_strength > 0.8:
                                stats['resonance_events'].append({
                                    'generation': gen,
                                    'position': [i, j],
                                    'strength': influence_strength,
                                    'similarity': debug_info.get('top_similarity', 0)
                                })

                        # Apply the morphic decision
                        decision = morphic_decision

                        # Update crystal activation tracking
                        if debug_info.get('applied_influence', False):
                            # Find the crystal that influenced this decision
                            for crystal in crystals:
                                for pattern in crystal['patterns'][-10:]:
                                    try:
                                        sim = calculate_pattern_similarity(neighborhood, pattern)
                                        if sim > 0.3:  # Threshold for recording activation
                                            crystal['activation_history'].append({
                                                'generation': gen,
                                                'position': (i, j),
                                                'similarity': sim,
                                                'influenced': True,
                                                'decision_changed': decision != debug_info['conway_decision']
                                            })
                                            break
                                    except Exception:
                                        continue

                    new_grid[i][j] = decision

            # Update Markov chains with transition data
            if mode == 'morphic' and gen > 0:
                for crystal in crystals:
                    try:
                        crystal['markov_predictor'].update(prev_grid, new_grid)
                    except Exception:
                        pass

            grid = new_grid
            alive_count = np.sum(grid)

            # Detect patterns and update crystals with structural data
            if mode == 'morphic' and gen % 10 == 0:  # Every 10 generations
                if crystals and alive_count > 0:
                    # Select crystal based on current activity level
                    activity_score = alive_count / (grid_size * grid_size)

                    # Choose crystal probabilistically based on strength
                    weights = [c['strength'] for c in crystals]
                    total_weight = sum(weights)

                    if total_weight > 0:
                        r = random.uniform(0, total_weight)
                        cumsum = 0
                        selected_crystal = crystals[0]

                        for crystal in crystals:
                            cumsum += crystal['strength']
                            if r <= cumsum:
                                selected_crystal = crystal
                                break

                        # Store structural pattern with subpatterns
                        pattern_data = {
                            'generation': gen,
                            'grid': grid.copy(),
                            'subpatterns': extract_subpatterns(grid),
                            'population': alive_count,
                            'activity_score': activity_score,
                            'timestamp': datetime.now().isoformat(),
                            'outcome': 'stable' if gen > 0 and abs(alive_count - prev_alive_count) < 5 else 'dynamic'
                        }
                        selected_crystal['patterns'].append(pattern_data)

                        # Update crystal strength with Bayesian approach
                        emergence_detected = alive_count > prev_alive_count * 1.2  # Simple emergence detection
                        selected_crystal['total_trials'] += 1
                        if emergence_detected:
                            selected_crystal['total_successes'] += 1

                        new_strength = update_crystal_strength_bayesian(
                            selected_crystal, emergence_detected, crystals
                        )

                        # Limit pattern storage to prevent memory issues
                        if len(selected_crystal['patterns']) > 50:
                            selected_crystal['patterns'] = selected_crystal['patterns'][-50:]

            # Calculate pattern diversity (unique 3x3 patterns in grid)
            pattern_diversity = 0
            if mode == 'morphic' and alive_count > 0:
                unique_patterns = set()
                for i in range(grid_size - 2):
                    for j in range(grid_size - 2):
                        pattern = tuple(grid[i:i+3, j:j+3].flatten())
                        unique_patterns.add(pattern)
                pattern_diversity = len(unique_patterns)

            # Calculate complexity (variety in local densities)
            complexity = 0
            if alive_count > 0:
                local_densities = []
                for i in range(0, grid_size - 3, 3):
                    for j in range(0, grid_size - 3, 3):
                        block = grid[i:i+3, j:j+3]
                        density = np.sum(block) / 9.0
                        local_densities.append(density)
                if local_densities:
                    complexity = np.std(local_densities)

            # Calculate population volatility
            volatility = abs(alive_count - prev_alive_count) / max(1, prev_alive_count)

            # Store enhanced metrics
            if mode == 'morphic':
                influence_rate = gen_influenced_cells / gen_total_cells if gen_total_cells > 0 else 0
                stats['influence_rate_history'].append(influence_rate)
                stats['pattern_diversity_history'].append(pattern_diversity)
                stats['crystal_utilization_history'].append(gen_crystal_activations)

            stats['complexity_evolution'].append(complexity)
            stats['population_volatility'].append(volatility)

            prev_alive_count = alive_count

            # Record generation data
            gen_data = {
                'generation': int(gen),
                'population': int(alive_count),
                'timestamp': datetime.now().isoformat(),
                'complexity': float(complexity),
                'volatility': float(volatility)
            }

            if mode == 'morphic':
                gen_data['influence_rate'] = float(influence_rate)
                gen_data['pattern_diversity'] = int(pattern_diversity)

            stats['generation_data'].append(gen_data)

            # Progress indicator
            if gen % max(1, generations // 10) == 0:
                progress = (gen / generations) * 100
                print(f'  🔄 Generation {gen:4d}/{generations} ({progress:5.1f}%) - Population: {alive_count:4d}')

        # Calculate final metrics
        populations = [int(g['population']) for g in stats['generation_data']]
        stats['final_population'] = int(populations[-1]) if populations else 0
        stats['max_population'] = int(max(populations)) if populations else 0
        stats['min_population'] = int(min(populations)) if populations else 0
        stats['avg_population'] = float(sum(populations) / len(populations)) if populations else 0.0

        # Simple stability calculation
        if len(populations) > 10:
            recent_pop = populations[-10:]
            variance = sum((p - stats['avg_population'])**2 for p in recent_pop) / len(recent_pop)
            stats['stability_score'] = max(0, 1 - (variance / (stats['avg_population'] + 1)))

        # Simple complexity score
        stats['complexity_score'] = len(set(populations)) / len(populations) if populations else 0

        # Count emergence events (population spikes)
        stats['emergence_events'] = sum(1 for i in range(1, len(populations))
                                       if populations[i] > populations[i-1] * 1.5)

        print('')
        print('📊 Simulation Complete!')
        print(f'   Final Population: {stats["final_population"]}')
        print(f'   Max Population: {stats["max_population"]}')
        print(f'   Avg Population: {stats["avg_population"]:.1f}')
        print(f'   Stability Score: {stats["stability_score"]:.3f}')
        print(f'   Complexity Score: {stats["complexity_score"]:.3f}')
        print(f'   Emergence Events: {stats["emergence_events"]}')

        if mode == 'morphic':
            total_patterns = sum(len(c['patterns']) for c in crystals)
            avg_strength = sum(c['strength'] for c in crystals) / len(crystals) if crystals else 0
            total_activations = sum(len(c.get('activation_history', [])) for c in crystals)
            print(f'   💎 Crystal Patterns: {total_patterns}')
            print(f'   💎 Avg Crystal Strength: {avg_strength:.3f}')
            print(f'   💎 Total Activations: {total_activations}')

            # Run validation with morphic influence data
            try:
                valid, message = validate_morphic_implementation(crystals, stats.get('morphic_influences', []))
                if valid:
                    print(f'   ✅ {message}')
                else:
                    print(f'   ⚠️  Validation warning: {message}')
            except Exception as e:
                print(f'   ⚠️  Validation error: {e}')

        # Save results
        import os
        os.makedirs('results', exist_ok=True)
        os.makedirs('timeseries_data', exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'results/simulation_{mode}_{timestamp}.json'

        # Custom JSON encoder for numpy types
        class NumpyEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (np.integer, np.int64)):
                    return int(obj)
                elif isinstance(obj, (np.floating, np.float64)):
                    return float(obj)
                elif isinstance(obj, (np.bool_, bool)):
                    return bool(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif obj.__class__.__name__ == 'MarkovPatternPredictor':
                    return {'type': 'MarkovPatternPredictor', 'transitions_count': len(obj.transitions)}
                return super().default(obj)

        # Create serializable copy of stats
        stats_copy = stats.copy()
        if mode == 'morphic':
            # Clean up crystals for serialization
            serializable_crystals = []
            for crystal in stats_copy['crystals']:
                clean_crystal = crystal.copy()
                # Remove non-serializable objects
                if 'markov_predictor' in clean_crystal:
                    clean_crystal['markov_predictor_summary'] = {
                        'type': 'MarkovPatternPredictor',
                        'transitions_count': len(clean_crystal['markov_predictor'].transitions)
                    }
                    del clean_crystal['markov_predictor']
                serializable_crystals.append(clean_crystal)
            stats_copy['crystals'] = serializable_crystals

        with open(filename, 'w') as f:
            json.dump(stats_copy, f, indent=2, cls=NumpyEncoder)

        print(f'💾 Results saved to: {filename}')

        # Save enhanced time series format for ML training
        save_timeseries_format(stats_copy, mode, morphic_config if mode == 'morphic' else None, timestamp)

        return True

    except Exception as e:
        print(f'❌ Simulation error: {e}')
        import traceback
        traceback.print_exc()
        return False


def save_timeseries_format(stats: dict, mode: str, morphic_config, timestamp: str):
    """Save data in structured time series format for ML training"""
    try:
        import numpy as np

        # Custom JSON encoder for numpy types
        class NumpyEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (np.integer, np.int64)):
                    return int(obj)
                elif isinstance(obj, (np.floating, np.float64)):
                    return float(obj)
                elif isinstance(obj, (np.bool_, bool)):
                    return bool(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                return super().default(obj)

        # Extract time series data
        timeseries = {
            'population': [g['population'] for g in stats['generation_data']],
            'complexity': [g.get('complexity', 0) for g in stats['generation_data']],
            'volatility': [g.get('volatility', 0) for g in stats['generation_data']]
        }

        # Add morphic-specific time series
        if mode == 'morphic':
            timeseries['morphic_influence_rate'] = stats.get('influence_rate_history', [])
            timeseries['pattern_diversity'] = stats.get('pattern_diversity_history', [])
            timeseries['resonance_event_count'] = len(stats.get('resonance_events', []))

        # Calculate summary statistics
        populations = timeseries['population']
        summary_stats = {
            'final_population': int(populations[-1]) if populations else 0,
            'max_population': int(max(populations)) if populations else 0,
            'min_population': int(min(populations)) if populations else 0,
            'avg_population': float(np.mean(populations)) if populations else 0.0,
            'std_population': float(np.std(populations)) if populations else 0.0,
            'avg_complexity': float(np.mean(timeseries['complexity'])) if timeseries['complexity'] else 0.0,
            'avg_volatility': float(np.mean(timeseries['volatility'])) if timeseries['volatility'] else 0.0,
            'stability_score': stats.get('stability_score', 0.0),
            'emergence_events': stats.get('emergence_events', 0)
        }

        # Add morphic-specific summary stats
        if mode == 'morphic':
            influence_rates = timeseries.get('morphic_influence_rate', [])
            if influence_rates:
                summary_stats['avg_influence_rate'] = float(np.mean(influence_rates))
                summary_stats['max_influence_rate'] = float(max(influence_rates))

            pattern_divs = timeseries.get('pattern_diversity', [])
            if pattern_divs:
                summary_stats['avg_pattern_diversity'] = float(np.mean(pattern_divs))

            summary_stats['resonance_events'] = timeseries.get('resonance_event_count', 0)

        # Build complete time series dataset
        timeseries_data = {
            'run_id': f'{mode}_{timestamp}',
            'mode': mode,
            'config': morphic_config.to_dict() if morphic_config else {},
            'timeseries': timeseries,
            'summary_stats': summary_stats,
            'metadata': {
                'grid_size': stats.get('grid_size', 0),
                'generations': stats.get('generations', 0),
                'initial_population': stats.get('initial_population', 0),
                'timestamp': timestamp
            }
        }

        # Save to timeseries_data directory
        ts_filename = f'timeseries_data/{mode}_{timestamp}.json'
        with open(ts_filename, 'w') as f:
            json.dump(timeseries_data, f, indent=2, cls=NumpyEncoder)

        print(f'📊 Time series data saved to: {ts_filename}')

    except Exception as e:
        print(f'⚠️  Failed to save time series format: {e}')

if __name__ == '__main__':
    # Run the simulation
    result = asyncio.run(run_conway_simulation())
    sys.exit(0 if result else 1)