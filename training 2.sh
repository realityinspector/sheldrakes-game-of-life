#!/bin/bash
# Training script for Emergence Simulator
# Supports both SQLite and PostgreSQL databases

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}🚀 Emergence Simulator Training${NC}"
    echo -e "${BLUE}===============================${NC}"
    echo ""
}

print_section() {
    echo ""
    echo -e "${CYAN}▶ $1${NC}"
    echo "────────────────────────────────────"
}

print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }

check_environment() {
    print_section "Environment Check"
    
    # Check if virtual environment is activated
    if [[ -z "$VIRTUAL_ENV" ]]; then
        print_warn "Virtual environment not detected. Using system Python."
        PYTHON_CMD="python3"
    else
        print_success "Virtual environment active: $VIRTUAL_ENV"
        PYTHON_CMD="python"
    fi
    
    # Check if .env exists
    if [[ ! -f ".env" ]]; then
        print_error ".env file not found. Run ./launcher.sh first."
        exit 1
    fi
    
    print_success "Environment configuration found"
}

check_database() {
    print_section "Database Configuration"
    
    # Test database configuration using our storage module
    echo "Testing database connection..."
    
    $PYTHON_CMD -c "
import sys
import os
sys.path.append('.')

try:
    from storage.database import get_database_info, create_tables
    
    info = get_database_info()
    print(f'✅ Database Type: {info[\"type\"]}')
    print(f'✅ Database URL: {info[\"url\"]}')
    
    if info['is_sqlite']:
        print('🗄️  Using SQLite - No external database required')
    elif info['is_postgres']:
        print('🐘 Using PostgreSQL - Ensure server is running')
    
    # Test table creation
    print('📋 Testing table creation...')
    create_tables()
    print('✅ Database tables ready')
    
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ Database error: {e}')
    sys.exit(1)
"
    
    if [[ $? -eq 0 ]]; then
        print_success "Database ready"
    else
        print_error "Database configuration failed"
        exit 1
    fi
}

check_dependencies() {
    print_section "Dependency Check"
    
    # Check core Python packages
    echo "Verifying required packages..."
    
    $PYTHON_CMD -c "
import sys
required_packages = [
    'sqlalchemy',
    'aiosqlite',  # For SQLite async
    'fastapi',
    'httpx',
    'requests'  # For LLM integration
]

postgres_packages = ['asyncpg', 'psycopg']

missing = []
postgres_available = False

for package in required_packages:
    try:
        __import__(package)
        print(f'✅ {package}')
    except ImportError:
        missing.append(package)
        print(f'❌ {package}')

# Check for at least one PostgreSQL driver
for package in postgres_packages:
    try:
        __import__(package)
        postgres_available = True
        print(f'✅ {package} (PostgreSQL support)')
        break
    except ImportError:
        continue

if not postgres_available:
    print('⚠️  No PostgreSQL drivers found (asyncpg or psycopg)')
    print('   SQLite will work, but PostgreSQL won\'t be available')

if missing:
    print('❌ Missing required packages:', ', '.join(missing))
    print('   Run ./launcher.sh to install dependencies')
    sys.exit(1)
else:
    print('✅ All required packages available')
"
    
    if [[ $? -eq 0 ]]; then
        print_success "Dependencies verified"
    else
        print_error "Missing dependencies"
        print_info "Run ./launcher.sh to install missing packages"
        exit 1
    fi
}

run_basic_simulation() {
    print_section "Basic Simulation Test"
    
    echo "Running basic simulation test..."
    
    $PYTHON_CMD -c "
import sys
import os
import asyncio
sys.path.append('.')

async def test_simulation():
    try:
        from storage import get_database_info, create_tables_async
        
        info = get_database_info()
        print(f'🗄️  Database: {info[\"type\"]} ({info[\"url\"]})')
        
        # Ensure tables exist
        await create_tables_async()
        print('📋 Database tables verified')
        
        # TODO: Add actual simulation logic here
        print('🎮 Simulation placeholder - ready for implementation')
        
        # Placeholder simulation results
        print('📊 Simulation Results:')
        print('   • Control group: Ready')
        print('   • Morphic group: Ready') 
        print('   • Memory crystals: Ready')
        
        return True
        
    except Exception as e:
        print(f'❌ Simulation error: {e}')
        return False

# Run async simulation test
result = asyncio.run(test_simulation())
sys.exit(0 if result else 1)
"
    
    if [[ $? -eq 0 ]]; then
        print_success "Basic simulation test passed"
    else
        print_error "Simulation test failed"
        exit 1
    fi
}

show_next_steps() {
    print_section "Training Ready!"
    
    echo -e "${GREEN}🎯 Training system configured and tested!${NC}"
    echo ""
    echo "Current Status:"
    echo "  ✅ Environment configured"
    echo "  ✅ Database ready (SQLite/PostgreSQL)"
    echo "  ✅ Dependencies verified"
    echo "  ✅ Basic simulation test passed"
    echo ""
    echo "Next Steps for Research:"
    echo "  🔬 Run control simulation:     ./training.sh --mode=control --generations=100"
    echo "  🧬 Run morphic simulation:     ./training.sh --mode=morphic --generations=100 --crystal-count=5"
    echo "  📊 Compare results:            Via web interface or API"
    echo ""
    echo "Development Commands:"
    echo "  🌐 Web interface:  ./run.sh"
    echo "  🧪 Run tests:      ./test.sh"
    echo "  📚 API docs:       http://localhost:PORT/docs"
    echo "  📖 User guide:     http://localhost:PORT/user-guide"
    echo ""
    echo -e "${CYAN}💡 Ready to explore morphic resonance in artificial systems!${NC}"
}

run_autopilot() {
    local runs="$1"
    local generations="$2"
    local grid_size="$3"
    local crystal_count="$4"

    print_header
    print_section "🤖 Autopilot Mode - Automated Research Pipeline"

    echo "Autopilot Configuration:"
    echo "  🔄 Total Runs: $runs"
    echo "  📊 Per Run: $generations generations"
    echo "  📐 Grid Size: ${grid_size}x${grid_size}"
    echo "  💎 Memory Crystals: $crystal_count"
    echo ""

    # Quick environment validation
    check_environment
    check_dependencies
    check_database

    echo "🚀 Starting automated research pipeline..."
    echo ""

    local control_runs=$((runs / 2))
    local morphic_runs=$((runs - control_runs))

    echo "📋 Execution Plan:"
    echo "  🎯 Control runs: $control_runs"
    echo "  🧬 Morphic runs: $morphic_runs"
    echo ""

    # Run control simulations
    for ((i=1; i<=control_runs; i++)); do
        echo "🎯 Running control simulation $i/$control_runs..."
        run_simulation "control" "$generations" "$crystal_count" "$grid_size" "autopilot"
        if [[ $? -ne 0 ]]; then
            print_error "Control simulation $i failed, continuing..."
        fi

        if [[ $i -lt $control_runs ]]; then
            echo "⏳ Brief pause between runs..."
            sleep 2
        fi
    done

    echo ""
    echo "🧬 Switching to morphic simulations..."
    echo ""

    # Run morphic simulations
    for ((i=1; i<=morphic_runs; i++)); do
        echo "🧬 Running morphic simulation $i/$morphic_runs..."
        run_simulation "morphic" "$generations" "$crystal_count" "$grid_size" "autopilot"
        if [[ $? -ne 0 ]]; then
            print_error "Morphic simulation $i failed, continuing..."
        fi

        if [[ $i -lt $morphic_runs ]]; then
            echo "⏳ Brief pause between runs..."
            sleep 2
        fi
    done

    print_section "🏁 Autopilot Complete"
    echo "✅ Completed $runs simulation runs"
    echo "📁 All results saved to results/ directory"
    echo ""
    echo "🔍 Next Steps:"
    echo "  📊 Analyze results with comparative analysis tools"
    echo "  🌐 Visualize data using web interface (./run.sh)"
    echo "  📈 Generate research reports from collected data"
    echo ""
}

run_simulation() {
    local mode="$1"
    local generations="$2"
    local crystal_count="$3"
    local grid_size="$4"
    local autopilot_mode="${5:-false}"

    if [[ "$autopilot_mode" != "autopilot" ]]; then
        print_header
    fi

    # Quick environment validation (skip in autopilot to reduce noise)
    if [[ "$autopilot_mode" != "autopilot" ]]; then
        check_environment
        check_dependencies
        check_database
    fi
    
    print_section "🎮 Conway's Game of Life - $mode Mode"
    
    echo "Simulation Parameters:"
    echo "  📐 Grid Size: ${grid_size}x${grid_size}"
    echo "  🔄 Generations: $generations"
    echo "  💎 Memory Crystals: $crystal_count"
    echo "  🧬 Mode: $mode"
    echo ""
    
    # Run the Python simulation
    print_info "Launching simulation engine..."
    
    $PYTHON_CMD -c "
import sys
import os
import asyncio
import random
import json
import time
from datetime import datetime
sys.path.append('.')

async def run_conway_simulation():
    try:
        from storage import get_database_info, create_tables_async
        
        info = get_database_info()
        print(f'🗄️  Database: {info[\"type\"]} ({info[\"url\"]})')
        
        # Ensure database is ready
        await create_tables_async()
        
        # Simulation parameters
        mode = '$mode'
        generations = $generations
        crystal_count = $crystal_count
        grid_size = $grid_size
        
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

        # Memory crystals for morphic mode
        crystals = []
        if mode == 'morphic':
            for i in range(crystal_count):
                crystal = {
                    'id': i + 1,
                    'patterns': [],
                    'strength': random.uniform(0.1, 0.8),
                    'created': datetime.now().isoformat(),
                    'activation_history': [],
                    'total_successes': 0,
                    'total_trials': 0,
                    'markov_predictor': MarkovPatternPredictor()
                }
                crystals.append(crystal)
            print(f'💎 Initialized {len(crystals)} memory crystals with pattern recognition')
        
        # Simulation metrics
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
            'morphic_influences': []  # Track morphic decision influences
        }
        
        print('🔄 Running simulation generations...')

        prev_alive_count = alive_count  # Initialize for first generation

        for gen in range(generations):
            # Conway's Game of Life rules
            new_grid = np.zeros((grid_size, grid_size), dtype=int)
            prev_grid = grid.copy()  # Store for Markov chain updates

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
                            grid=grid, i=i, j=j, grid_size=grid_size
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

            prev_alive_count = alive_count
            
            # Record generation data
            gen_data = {
                'generation': int(gen),
                'population': int(alive_count),
                'timestamp': datetime.now().isoformat()
            }
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
        print(f'   Final Population: {stats[\"final_population\"]}')
        print(f'   Max Population: {stats[\"max_population\"]}')
        print(f'   Avg Population: {stats[\"avg_population\"]:.1f}')
        print(f'   Stability Score: {stats[\"stability_score\"]:.3f}')
        print(f'   Complexity Score: {stats[\"complexity_score\"]:.3f}')
        print(f'   Emergence Events: {stats[\"emergence_events\"]}')
        
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
        
        return True
        
    except Exception as e:
        print(f'❌ Simulation error: {e}')
        import traceback
        traceback.print_exc()
        return False

# Run the simulation
result = asyncio.run(run_conway_simulation())
sys.exit(0 if result else 1)
"
    
    if [[ $? -eq 0 ]]; then
        print_success "Simulation completed successfully"
        echo ""
        echo "🔍 Analysis Tips:"
        echo "  📁 Check results/ directory for simulation data"
        echo "  🌐 Use web interface (./run.sh) for visualization"
        echo "  📊 Compare morphic vs control runs for research"
        echo ""
    else
        print_error "Simulation failed"
        exit 1
    fi
}

main() {
    print_header
    
    # Configuration and validation
    check_environment
    check_dependencies
    check_database
    
    # Basic functionality test
    run_basic_simulation
    
    # Results and next steps
    show_next_steps
}

# Parse command line arguments
MODE="setup"
GENERATIONS=50
CRYSTAL_COUNT=3
GRID_SIZE=25
CHECK_ONLY=false
AUTOPILOT_RUNS=10

parse_argument() {
    local arg="$1"
    # Remove any leading/trailing whitespace and validate format
    arg=$(echo "$arg" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

    if [[ -z "$arg" ]]; then
        return 0  # Skip empty arguments
    fi

    case "$arg" in
        -h|--help)
            show_help
            exit 0
            ;;
        --check-only)
            CHECK_ONLY=true
            ;;
        --mode=*)
            MODE="${arg#*=}"
            MODE=$(echo "$MODE" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            ;;
        --generations=*)
            GENERATIONS="${arg#*=}"
            GENERATIONS=$(echo "$GENERATIONS" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            ;;
        --crystal-count=*)
            CRYSTAL_COUNT="${arg#*=}"
            CRYSTAL_COUNT=$(echo "$CRYSTAL_COUNT" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            ;;
        --grid-size=*)
            GRID_SIZE="${arg#*=}"
            GRID_SIZE=$(echo "$GRID_SIZE" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            ;;
        --runs=*)
            AUTOPILOT_RUNS="${arg#*=}"
            AUTOPILOT_RUNS=$(echo "$AUTOPILOT_RUNS" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            ;;
        --*)
            print_error "Unknown option: $arg"
            echo "Use --help for usage information"
            exit 1
            ;;
        *)
            # Check if this looks like a stray parameter
            if [[ "$arg" =~ ^[0-9]+$ ]]; then
                print_error "Stray numeric parameter: $arg"
                print_error "Make sure all options are on the same line: --option=value"
            else
                print_error "Unknown argument: $arg"
            fi
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
}

show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help                    Show this help message"
    echo "  --check-only                  Only run configuration checks"
    echo "  --mode=MODE                   Simulation mode: 'setup', 'control', 'morphic', 'autopilot'"
    echo "  --generations=N               Number of simulation generations (default: 50)"
    echo "  --crystal-count=N             Number of memory crystals (default: 3)"
    echo "  --grid-size=N                 Grid size NxN (default: 25)"
    echo "  --runs=N                      Number of autopilot runs (default: 10, autopilot mode only)"
    echo ""
    echo "IMPORTANT: All arguments must be on the same line!"
    echo "  ✅ Correct:   $0 --mode=control --generations=100 --crystal-count=5"
    echo "  ❌ Incorrect: $0 --mode=control \\"
    echo "                   --generations=100 \\"
    echo "                   --crystal-count=5"
    echo ""
    echo "Environment Variables:"
    echo "  DATABASE_URL          Database connection (SQLite or PostgreSQL)"
    echo "  OPENROUTER_API_KEY    OpenRouter API key for LLM integration"
    echo ""
    echo "Examples:"
    echo "  $0                                                    # Setup and validation only"
    echo "  $0 --check-only                                       # Just verify configuration"
    echo "  $0 --mode=control --generations=100                   # Run control simulation"
    echo "  $0 --mode=morphic --generations=100 --crystal-count=5 # Run morphic simulation"
    echo "  $0 --mode=autopilot --runs=20 --generations=50        # Run 20 automated simulations"
}

# Parse all arguments
while [[ $# -gt 0 ]]; do
    parse_argument "$1"
    shift
done

if [[ "$CHECK_ONLY" == "true" ]]; then
    print_header
    check_environment
    check_dependencies
    check_database
    print_success "Configuration checks passed"
    exit 0
fi

validate_parameters() {
    local errors=()

    # Validate mode
    if [[ ! "$MODE" =~ ^(setup|control|morphic|autopilot)$ ]]; then
        errors+=("Invalid mode: '$MODE'. Use 'setup', 'control', 'morphic', or 'autopilot'")
    fi

    # Validate generations
    if ! [[ "$GENERATIONS" =~ ^[0-9]+$ ]] || (( GENERATIONS < 1 )); then
        errors+=("Invalid generations: '$GENERATIONS'. Must be a positive integer")
    elif (( GENERATIONS > 1000 )); then
        errors+=("Generations too high: '$GENERATIONS'. Maximum is 1000 for performance")
    fi

    # Validate crystal count
    if ! [[ "$CRYSTAL_COUNT" =~ ^[0-9]+$ ]] || (( CRYSTAL_COUNT < 1 )); then
        errors+=("Invalid crystal count: '$CRYSTAL_COUNT'. Must be a positive integer")
    elif (( CRYSTAL_COUNT > 20 )); then
        errors+=("Crystal count too high: '$CRYSTAL_COUNT'. Maximum is 20 for performance")
    fi

    # Validate grid size
    if ! [[ "$GRID_SIZE" =~ ^[0-9]+$ ]] || (( GRID_SIZE < 5 )) || (( GRID_SIZE > 100 )); then
        errors+=("Invalid grid size: '$GRID_SIZE'. Must be between 5 and 100")
    fi

    # Validate autopilot runs
    if ! [[ "$AUTOPILOT_RUNS" =~ ^[0-9]+$ ]] || (( AUTOPILOT_RUNS < 2 )); then
        errors+=("Invalid autopilot runs: '$AUTOPILOT_RUNS'. Must be at least 2")
    elif (( AUTOPILOT_RUNS > 100 )); then
        errors+=("Autopilot runs too high: '$AUTOPILOT_RUNS'. Maximum is 100 for reasonable execution time")
    fi

    # Report all errors at once
    if [[ ${#errors[@]} -gt 0 ]]; then
        print_error "Parameter validation failed:"
        for error in "${errors[@]}"; do
            echo "  • $error"
        done
        echo ""
        echo "Current values:"
        echo "  MODE=$MODE"
        echo "  GENERATIONS=$GENERATIONS"
        echo "  CRYSTAL_COUNT=$CRYSTAL_COUNT"
        echo "  GRID_SIZE=$GRID_SIZE"
        echo "  AUTOPILOT_RUNS=$AUTOPILOT_RUNS"
        echo ""
        echo "Use --help for usage information"
        exit 1
    fi

    # Show configuration summary
    print_info "Configuration validated:"
    echo "  Mode: $MODE"
    echo "  Generations: $GENERATIONS"
    echo "  Crystal Count: $CRYSTAL_COUNT"
    echo "  Grid Size: ${GRID_SIZE}x${GRID_SIZE}"
    if [[ "$MODE" == "autopilot" ]]; then
        echo "  Autopilot Runs: $AUTOPILOT_RUNS"
    fi
    echo ""
}

# Validate parameters
validate_parameters

# Run appropriate mode
case "$MODE" in
    "setup")
        main
        ;;
    "control"|"morphic")
        run_simulation "$MODE" "$GENERATIONS" "$CRYSTAL_COUNT" "$GRID_SIZE"
        ;;
    "autopilot")
        run_autopilot "$AUTOPILOT_RUNS" "$GENERATIONS" "$GRID_SIZE" "$CRYSTAL_COUNT"
        ;;
esac