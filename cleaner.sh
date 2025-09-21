#!/bin/bash

# 🧹 Emergence Simulator - Documentation and File Cleanup Script
# Removes outdated documentation files and unnecessary artifacts

echo "🧹 Starting Emergence Simulator cleanup..."

# Track what we're doing
FILES_REMOVED=0
DIRS_CLEANED=0

# Function to safely remove file
remove_file() {
    if [ -f "$1" ]; then
        echo "🗑️  Removing: $1"
        rm "$1"
        ((FILES_REMOVED++))
    fi
}

# Function to safely remove directory
remove_dir() {
    if [ -d "$1" ]; then
        echo "📁 Removing directory: $1"
        rm -rf "$1"
        ((DIRS_CLEANED++))
    fi
}

echo "🔍 Removing outdated documentation files..."

# Remove the outdated documentation files that are now consolidated
remove_file "MORPHIC_IMPLEMENTATION_SUMMARY.md"
remove_file "CORRECTED_MORPHIC_IMPLEMENTATION.md"
remove_file "FINAL_ENHANCED_IMPLEMENTATION.md"
remove_file "CLEANUP_REPORT.md"
remove_file "CHANGE-ROUND.md"

echo "🔍 Cleaning up development artifacts..."

# Remove Python cache and temporary files
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -type f -delete 2>/dev/null || true
find . -name "*.pyo" -type f -delete 2>/dev/null || true
find . -name ".DS_Store" -type f -delete 2>/dev/null || true

echo "🔍 Cleaning up duplicate and obsolete files..."

# Remove duplicate requirements files
remove_file "requirements-py313.txt"

# Remove .env duplicates (keep .env.example and .env)
remove_file ".env.sqlite"

echo "🔍 Reviewing script files for consolidation..."

# Check for redundant scripts
if [ -f "quick_test.sh" ] && [ -f "test.sh" ]; then
    echo "📝 Found both quick_test.sh and test.sh - consider consolidating"
fi

# Identify potentially redundant research scripts
RESEARCH_SCRIPTS=(
    "analyze_patterns.sh"
    "automated_research_pipeline.sh"
    "comprehensive_study.sh"
    "monitor_simulation.sh"
    "research_protocol.sh"
)

echo "📊 Research scripts found:"
for script in "${RESEARCH_SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        echo "  ✅ $script"
    fi
done

echo "🔍 Checking for empty or minimal directories..."

# Check for empty directories
find . -type d -empty -not -path "./venv/*" 2>/dev/null | while read dir; do
    if [ "$dir" != "." ]; then
        echo "📁 Empty directory found: $dir"
    fi
done

echo "🔍 Validating core file structure..."

# Ensure core directories exist
mkdir -p logs results test-results web/static/{css,js,images} web/templates storage/migrations core simulations/templates

echo "✅ Cleanup Summary:"
echo "  🗑️  Files removed: $FILES_REMOVED"
echo "  📁 Directories cleaned: $DIRS_CLEANED"
echo "  🧹 Python cache cleaned"
echo "  📝 Documentation consolidated into README.md and ENGINEERING.md"

echo "📋 Current project structure:"
echo "emergence-simulator/"
echo "├── README.md                 # 📚 Consolidated documentation"
echo "├── ENGINEERING.md            # 🔬 Technical implementation details"
echo "├── main.py                   # 🚀 FastAPI application"
echo "├── simple_viewer.py          # 📊 Enhanced historical viewer"
echo "├── training.sh               # 🏋️ Core simulation engine"
echo "├── launcher.sh               # 🔧 Environment setup"
echo "├── compare.sh                # 📈 Parameter sweeping"
echo "├── comprehensive_study.sh    # 🔬 Research pipeline"
echo "├── core/                     # 🧬 Morphic resonance logic"
echo "├── web/                      # 🌐 Web interface"
echo "├── storage/                  # 🗄️ Database layer"
echo "├── results/                  # 📊 Simulation results"
echo "└── web_cache/                # 💾 Visualization cache"

echo "🎯 Post-cleanup recommendations:"
echo "  1. Run './launcher.sh' to validate setup"
echo "  2. Run './test.sh' to verify core functionality"
echo "  3. Consider consolidating research scripts if needed"
echo "  4. Update .gitignore to prevent cache file accumulation"

echo "✨ Cleanup completed successfully!"

# Count final files
TOTAL_FILES=$(find . -type f -not -path "./venv/*" | wc -l | tr -d ' ')
echo "📊 Final file count: $TOTAL_FILES files (excluding venv/)"

exit 0