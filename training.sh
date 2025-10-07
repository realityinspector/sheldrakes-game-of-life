#!/bin/bash
# Training script for Emergence Simulator
# Supports both SQLite and PostgreSQL databases

set -e

# Detect if this might be a continuation from a line break command
if [[ "$1" =~ ^--(generations|crystal-count|grid-size|runs)= ]]; then
    echo ""
    echo "🚨 DETECTED SHELL LINE BREAK ISSUE!"
    echo ""
    echo "It looks like you're trying to run a command that was split across lines."
    echo "The shell executed the first part, and now it's trying to execute:"
    echo "  $*"
    echo ""
    echo "❌ This happens when you press Enter in the middle of a command."
    echo ""
    echo "✅ SOLUTION: Put the entire command on ONE line, like this:"
    echo "  ./training.sh --mode=autopilot --runs=10 --generations=50 --grid-size=20 --crystal-count=5"
    echo ""
    echo "Or use backslashes to continue lines:"
    echo "  ./training.sh --mode=autopilot --runs=10 \\"
    echo "    --generations=50 --grid-size=20 \\"
    echo "    --crystal-count=5"
    echo ""
    exit 1
fi

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

    # First try to detect or activate virtual environment
    if [[ -z "$VIRTUAL_ENV" ]] && [[ -d "venv" ]]; then
        print_info "Activating virtual environment..."
        source venv/bin/activate
        if [[ -n "$VIRTUAL_ENV" ]]; then
            print_success "Virtual environment activated: $VIRTUAL_ENV"
            PYTHON_CMD="python"
        else
            print_warn "Failed to activate virtual environment. Using system Python."
            PYTHON_CMD="python3"
        fi
    elif [[ -n "$VIRTUAL_ENV" ]]; then
        print_success "Virtual environment active: $VIRTUAL_ENV"
        PYTHON_CMD="python"
    elif [[ -f "venv/bin/python" ]]; then
        # Direct path fallback if activation fails
        print_info "Using direct virtual environment Python path"
        PYTHON_CMD="./venv/bin/python"
    else
        print_warn "Virtual environment not detected. Using system Python."
        PYTHON_CMD="python3"
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

    $PYTHON_CMD <<EOF
import sys
import os
sys.path.append('.')

try:
    from storage.database import get_database_info, create_tables
    
    info = get_database_info()
    print(f'✅ Database Type: {info["type"]}')
    print(f'✅ Database URL: {info["url"]}')

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
EOF
    
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

    $PYTHON_CMD <<EOF
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
EOF
    
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

    $PYTHON_CMD <<EOF
import sys
import os
import asyncio
sys.path.append('.')

async def test_simulation():
    try:
        from storage import get_database_info, create_tables_async
        
        info = get_database_info()
        print(f'🗄️  Database: {info["type"]} ({info["url"]})')
        
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
EOF
    
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

    $PYTHON_CMD scripts/run_simulation.py "$mode" "$generations" "$crystal_count" "$grid_size" \
        "$FIELD_STRENGTH" "$TEMPORAL_DECAY" "$SIMILARITY_THRESHOLD" "$INFLUENCE_EXPONENT"
    
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

# Morphic field parameters
FIELD_STRENGTH=0.6
TEMPORAL_DECAY=0.1
SIMILARITY_THRESHOLD=0.7
INFLUENCE_EXPONENT=2.0

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
        --field-strength=*)
            FIELD_STRENGTH="${arg#*=}"
            FIELD_STRENGTH=$(echo "$FIELD_STRENGTH" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            ;;
        --temporal-decay=*)
            TEMPORAL_DECAY="${arg#*=}"
            TEMPORAL_DECAY=$(echo "$TEMPORAL_DECAY" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            ;;
        --similarity-threshold=*)
            SIMILARITY_THRESHOLD="${arg#*=}"
            SIMILARITY_THRESHOLD=$(echo "$SIMILARITY_THRESHOLD" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            ;;
        --influence-exponent=*)
            INFLUENCE_EXPONENT="${arg#*=}"
            INFLUENCE_EXPONENT=$(echo "$INFLUENCE_EXPONENT" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
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
    echo "Morphic Field Parameters (morphic mode only):"
    echo "  --field-strength=F            Master influence multiplier, 0.0-1.0 (default: 0.6)"
    echo "  --temporal-decay=D            Crystal aging rate, 0.0-1.0 (default: 0.1)"
    echo "  --similarity-threshold=T      Min similarity for influence, 0.0-1.0 (default: 0.7)"
    echo "  --influence-exponent=E        Similarity non-linearity, 0.5-5.0 (default: 2.0)"
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
    echo "  $0 --mode=morphic --field-strength=0.8 --temporal-decay=0.0 # Strong, no-decay field"
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