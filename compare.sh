#!/bin/bash
# Emergence Simulator - Comparative Analysis Tool
# Batch parameter sweeping and emergence event clustering analysis

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Default configuration
CONFIG_FILE="compare_config.json"
OUTPUT_DIR="comparative_analysis"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BATCH_ID="batch_$TIMESTAMP"

# Function to show usage
show_usage() {
    echo -e "${BLUE}🔬 Emergence Simulator - Comparative Analysis${NC}"
    echo "=============================================="
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -c, --config FILE      Configuration file (default: compare_config.json)"
    echo "  -o, --output DIR       Output directory (default: comparative_analysis)"
    echo "  --check-only           Validate configuration and environment"
    echo "  --create-config        Create example configuration file"
    echo "  --analyze-only         Only analyze existing results (skip simulations)"
    echo "  --graph-only           Only generate graphs from existing analysis"
    echo "  -h, --help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                     Run with default configuration"
    echo "  $0 -c my_study.json    Run with custom configuration"
    echo "  $0 --create-config     Generate example config file"
    echo "  $0 --analyze-only      Analyze existing batch results"
}

# Function to create example configuration
create_example_config() {
    echo -e "${CYAN}📋 Creating example configuration: $CONFIG_FILE${NC}"
    
    cat > "$CONFIG_FILE" << 'EOF'
{
  "study_name": "Morphic Resonance Parameter Sweep",
  "description": "Comparative analysis of emergence events across parameter ranges",
  "timestamp": "auto",
  
  "parameter_ranges": {
    "generations": [100, 500, 1000],
    "crystal_count": [1, 3, 5, 10, 15],
    "grid_size": [15, 25, 35, 50],
    "initial_density": [0.3, 0.4, 0.5, 0.6]
  },
  
  "simulation_types": {
    "morphic": {
      "enabled": true,
      "description": "LLM-enhanced with morphic resonance"
    },
    "llm_control": {
      "enabled": true,
      "description": "LLM-enhanced without morphic resonance"
    },
    "classical": {
      "enabled": true,
      "description": "Pure Conway's Game of Life rules"
    }
  },
  
  "sampling": {
    "mode": "grid",
    "max_combinations": 200,
    "random_seed": 42
  },
  
  "analysis": {
    "emergence_threshold": 1.5,
    "stability_window": 20,
    "clustering": {
      "algorithm": "kmeans",
      "n_clusters": 5
    }
  },
  
  "output": {
    "save_raw_data": true,
    "generate_plots": true,
    "create_report": true,
    "plot_formats": ["png", "svg"]
  }
}
EOF
    
    echo -e "${GREEN}✅ Configuration file created: $CONFIG_FILE${NC}"
    echo "Edit this file to customize your parameter sweep study."
}

# Function to validate environment
check_environment() {
    echo -e "${CYAN}🔍 Environment Validation${NC}"
    echo "────────────────────────────────────"
    
    # Check virtual environment
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        echo -e "${GREEN}✅ Virtual environment active${NC}"
    else
        echo -e "${YELLOW}⚠️  Virtual environment not detected${NC}"
        if [[ -d "venv" ]]; then
            echo "   Run: source venv/bin/activate"
        else
            echo "   Run: ./launcher.sh to set up environment"
        fi
        return 1
    fi
    
    # Check Python dependencies using venv python
    echo "Checking Python dependencies..."
    local missing_deps=()
    
    for pkg in numpy matplotlib pandas seaborn plotly; do
        if ! python -c "import $pkg" 2>/dev/null; then
            missing_deps+=("$pkg")
        else
            echo -e "✅ $pkg"
        fi
    done
    
    # Special check for scikit-learn (import name is different)
    if ! python -c "import sklearn" 2>/dev/null; then
        missing_deps+=("scikit-learn")
    else
        echo -e "✅ scikit-learn"
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        echo -e "${RED}❌ Missing dependencies: ${missing_deps[*]}${NC}"
        echo "   Run: pip install ${missing_deps[*]}"
        return 1
    fi
    
    # Check configuration file
    if [[ ! -f "$CONFIG_FILE" ]]; then
        echo -e "${YELLOW}⚠️  Configuration file not found: $CONFIG_FILE${NC}"
        echo "   Run: $0 --create-config"
        return 1
    fi
    
    echo -e "${GREEN}✅ Environment ready for comparative analysis${NC}"
    return 0
}

# Function to run comparative analysis
run_comparative_analysis() {
    echo -e "${BLUE}🚀 Starting Comparative Analysis${NC}"
    echo "=================================="
    echo "Batch ID: $BATCH_ID"
    echo "Config: $CONFIG_FILE"
    echo "Output: $OUTPUT_DIR/$BATCH_ID"
    echo ""
    
    # Create output directory
    mkdir -p "$OUTPUT_DIR/$BATCH_ID"
    
    # Copy configuration for reproducibility
    cp "$CONFIG_FILE" "$OUTPUT_DIR/$BATCH_ID/config.json"
    
    # Run the Python analysis engine
    python -c "
import sys
sys.path.append('.')
from compare_engine import ComparativeAnalysisEngine

engine = ComparativeAnalysisEngine(
    config_file='$CONFIG_FILE',
    output_dir='$OUTPUT_DIR/$BATCH_ID',
    batch_id='$BATCH_ID'
)

try:
    engine.run_complete_analysis()
    print('🎉 Comparative analysis completed successfully!')
except Exception as e:
    print(f'❌ Analysis failed: {e}')
    sys.exit(1)
"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --check-only)
            check_environment
            exit $?
            ;;
        --create-config)
            create_example_config
            exit 0
            ;;
        --analyze-only)
            ANALYZE_ONLY=true
            shift
            ;;
        --graph-only)
            GRAPH_ONLY=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
echo -e "${PURPLE}🔬 Emergence Simulator - Comparative Analysis${NC}"
echo "============================================="
echo ""

# Validate environment
if ! check_environment; then
    exit 1
fi

# Run analysis
if [[ "$ANALYZE_ONLY" == "true" ]]; then
    echo -e "${CYAN}📊 Running analysis on existing data...${NC}"
    # TODO: Implement analyze-only mode
    echo "Analyze-only mode not yet implemented"
elif [[ "$GRAPH_ONLY" == "true" ]]; then
    echo -e "${CYAN}📈 Generating graphs from existing analysis...${NC}"
    # TODO: Implement graph-only mode
    echo "Graph-only mode not yet implemented"
else
    run_comparative_analysis
fi

echo ""
echo -e "${GREEN}🎉 Comparative analysis workflow completed!${NC}"
echo -e "📁 Results: $OUTPUT_DIR/$BATCH_ID"
echo -e "📊 Open the generated report for detailed findings."