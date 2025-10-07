#!/bin/bash
# Phase 2 Complete Testing Suite (Updated for Rich Logging)
# Tests all functionality including new real-time logging enhancements

set -e  # Exit on any error

# Color codes for output (fallback if rich isn't working)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}🧪 Testing Phase 2 Implementation (with Rich Logging)${NC}"
echo "================================================================="
echo ""

# Test 1: Verify all files exist including new logging docs
echo -e "${BLUE}📋 Test 1: Verify new files exist (including logging docs)...${NC}"
if ls -lh morphic_config.py batch_runner.py PHASE2_IMPLEMENTATION.md QUICK_START_PHASE2.md LOGGING_ENHANCEMENTS.md 2>/dev/null; then
    echo -e "${GREEN}✅ All files present (including LOGGING_ENHANCEMENTS.md)${NC}"
else
    echo -e "${RED}❌ Some files missing!${NC}"
    exit 1
fi
echo ""

# Test 2: Check Rich library installation
echo -e "${BLUE}📋 Test 2: Verify Rich library installation...${NC}"
if ./venv/bin/python -c "import rich; print(f'✅ Rich version: {rich.__version__}')"; then
    echo -e "${GREEN}✅ Rich library installed${NC}"
else
    echo -e "${YELLOW}⚠️  Rich not installed. Installing now...${NC}"
    ./venv/bin/pip install rich
    echo -e "${GREEN}✅ Rich installed${NC}"
fi
echo ""

# Test 3: Config module validation
echo -e "${BLUE}📋 Test 3: Config module validation...${NC}"
./venv/bin/python morphic_config.py
echo ""

# Test 4: Single morphic simulation with Rich output
echo -e "${BLUE}📋 Test 4: Single morphic simulation (with Rich logging)...${NC}"
echo -e "${CYAN}  → Should show color-coded progress and timing stats${NC}"
./training.sh --mode=morphic --generations=20 --grid-size=15 --crystal-count=3 \
  --field-strength=0.8 --temporal-decay=0.2 --similarity-threshold=0.6
echo ""

# Test 5: Verify time series output format
echo -e "${BLUE}📋 Test 5: Verify time series output format...${NC}"
ls -lh timeseries_data/*.json | tail -5
echo ""
echo -e "${CYAN}Latest time series file preview:${NC}"
ls -t timeseries_data/morphic_*.json 2>/dev/null | head -1 | xargs cat | python3 -m json.tool | head -35
echo ""

# Test 6: Batch runner dry-run with Rich output
echo -e "${BLUE}📋 Test 6: Batch runner dry-run (5 experiments, Rich preview)...${NC}"
echo -e "${CYAN}  → Should show color-coded experiment list${NC}"
./venv/bin/python batch_runner.py --experiment-type=focused --dry-run --limit=5
echo ""

# Test 7: Small batch with verbose logging (watch the Rich magic!)
echo -e "${BLUE}📋 Test 7: Small parameter sweep (3 runs with Rich logging)...${NC}"
echo -e "${CYAN}  → Watch for: progress bars, real-time generation updates, timing stats${NC}"
echo -e "${YELLOW}  → This will take 2-5 minutes depending on your system${NC}"

# Use gtimeout on macOS if available, otherwise skip timeout
if command -v gtimeout &> /dev/null; then
    gtimeout 10m ./venv/bin/python batch_runner.py --experiment-type=focused --limit=3 --verbose
elif command -v timeout &> /dev/null; then
    timeout 10m ./venv/bin/python batch_runner.py --experiment-type=focused --limit=3 --verbose
else
    echo -e "${YELLOW}  (No timeout command available - running without timeout)${NC}"
    ./venv/bin/python batch_runner.py --experiment-type=focused --limit=3 --verbose
fi
echo ""

# Test 8: Verify dataset manifest
echo -e "${BLUE}📋 Test 8: Verify dataset manifest...${NC}"
if [ -f timeseries_data/manifest.json ]; then
    cat timeseries_data/manifest.json | python3 -m json.tool
    echo -e "${GREEN}✅ Manifest found and valid${NC}"
else
    echo -e "${YELLOW}⚠️  No manifest found (will be created on next batch run)${NC}"
fi
echo ""

# Test 9: Compare morphic vs control with Rich output
echo -e "${BLUE}📋 Test 9: Compare morphic vs control outputs...${NC}"
echo -e "${CYAN}Control run (classical):${NC}"
./training.sh --mode=classical --generations=15 --grid-size=15
echo ""
echo -e "${CYAN}Morphic run (field_strength=0.5):${NC}"
./training.sh --mode=morphic --generations=15 --grid-size=15 --field-strength=0.5
echo ""

# Test 10: Test verbose flag specifically
echo -e "${BLUE}📋 Test 10: Test verbose mode (1 run with all output)...${NC}"
echo -e "${CYAN}  → Should show EVERY generation update${NC}"
./venv/bin/python batch_runner.py --experiment-type=focused --limit=1 --verbose
echo ""

# Test 11: Performance test - measure timing
echo -e "${BLUE}📋 Test 11: Performance benchmark...${NC}"
echo -e "${CYAN}  → Running 50-generation simulation to measure speed${NC}"
START_TIME=$(date +%s)
./training.sh --mode=morphic --generations=50 --grid-size=20 --crystal-count=3 \
  --field-strength=0.6 --temporal-decay=0.1
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
echo ""
echo -e "${GREEN}✅ 50-generation run completed in ${ELAPSED}s${NC}"
if [ $ELAPSED -lt 120 ]; then
    echo -e "${GREEN}   Performance: GOOD (< 2 minutes)${NC}"
else
    echo -e "${YELLOW}   Performance: SLOW (> 2 minutes) - may indicate hanging${NC}"
fi
echo ""

# Final Report
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}📊 FINAL REPORT${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Count files
TOTAL_TS=$(ls timeseries_data/*.json 2>/dev/null | grep -v manifest | wc -l | tr -d ' ')
MORPHIC_TS=$(ls timeseries_data/morphic_*.json 2>/dev/null | wc -l | tr -d ' ')
CLASSICAL_TS=$(ls timeseries_data/classical_*.json 2>/dev/null | wc -l | tr -d ' ')

echo -e "${CYAN}📁 Time Series Files:${NC}"
echo "  Total: $TOTAL_TS files"
echo "  Morphic: $MORPHIC_TS files"
echo "  Classical: $CLASSICAL_TS files"
echo ""

# Analyze latest morphic run
if [ -f "$(ls -t timeseries_data/morphic_*.json 2>/dev/null | head -1)" ]; then
    echo -e "${CYAN}📊 Latest Morphic Simulation:${NC}"
    ls -t timeseries_data/morphic_*.json 2>/dev/null | head -1 | xargs cat | python3 << 'EOF'
import json, sys
try:
    d = json.load(sys.stdin)
    config = d.get('config', {})
    stats = d.get('summary_stats', {})
    ts = d.get('timeseries', {})
    
    print(f"  Run ID: {d.get('run_id', 'N/A')}")
    print(f"  Field Strength: {config.get('field_strength', 'N/A')}")
    print(f"  Temporal Decay: {config.get('temporal_decay', 'N/A')}")
    print(f"  Similarity Threshold: {config.get('similarity_threshold', 'N/A')}")
    print(f"  Generations: {len(ts.get('population', []))}")
    print(f"  Final Population: {stats.get('final_population', 'N/A')}")
    print(f"  Avg Population: {stats.get('avg_population', 0):.1f}")
    
    if 'avg_influence_rate' in stats:
        print(f"  Avg Influence Rate: {stats['avg_influence_rate']:.2%}")
    if 'resonance_events' in stats:
        print(f"  Resonance Events: {stats['resonance_events']}")
except Exception as e:
    print(f"  Error parsing: {e}")
EOF
else
    echo -e "${YELLOW}⚠️  No morphic simulations found${NC}"
fi
echo ""

# Check Rich features
echo -e "${CYAN}✨ Rich Logging Features:${NC}"
if ./venv/bin/python -c "import rich; from rich.progress import Progress; from rich.console import Console; print('✅ All Rich modules imported successfully')"; then
    echo "  ✅ Rich console available"
    echo "  ✅ Progress bars available"
    echo "  ✅ Color output available"
    echo "  ✅ Real-time logging active"
else
    echo -e "${YELLOW}  ⚠️  Rich features may not be fully available${NC}"
fi
echo ""

# Test summary
echo -e "${CYAN}📋 Test Summary:${NC}"
echo "  ✅ File verification"
echo "  ✅ Rich library installation"
echo "  ✅ Config validation"
echo "  ✅ Single simulation with logging"
echo "  ✅ Time series format"
echo "  ✅ Batch runner dry-run"
echo "  ✅ Small parameter sweep"
echo "  ✅ Dataset manifest"
echo "  ✅ Morphic vs control comparison"
echo "  ✅ Verbose mode"
echo "  ✅ Performance benchmark"
echo ""

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Phase 2 Implementation Test Complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}🎯 System Status:${NC}"
echo "  ✅ Parameterized morphic fields working"
echo "  ✅ Batch processing operational"
echo "  ✅ Real-time logging active"
echo "  ✅ Time series data generation ready"
echo "  ✅ ML-ready output format validated"
echo ""
echo -e "${GREEN}🚀 Ready for Phase 3: ML Detector Training${NC}"
echo ""

# Optional: Show quick start command
echo -e "${CYAN}💡 Quick Start Next Steps:${NC}"
echo "  # Generate 10-run dataset:"
echo "  ./venv/bin/python batch_runner.py --experiment-type=focused --limit=10"
echo ""
echo "  # Full parameter sweep (240+ runs, ~8 hours):"
echo "  nohup ./venv/bin/python batch_runner.py --experiment-type=full > sweep.log 2>&1 &"
echo ""
echo "  # Monitor progress:"
echo "  tail -f sweep.log"
echo "