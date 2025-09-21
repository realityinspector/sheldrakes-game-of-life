#!/bin/bash
# Simple test runner for Emergence Simulator

set -e

echo "🧪 Emergence Simulator - Basic Tests"
echo "=================================="

# Check Python environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Virtual environment not activated. Run: source venv/bin/activate"
fi

echo "🐍 Python version: $(python --version)"
echo "📍 Working directory: $(pwd)"
echo ""

# Test core imports
echo "📦 Testing core imports..."

python -c "
import sys
success = True

modules = [
    'fastapi',
    'uvicorn', 
    'pydantic',
    'httpx',
    'sqlalchemy'
]

print('Testing module imports:')
for module in modules:
    try:
        __import__(module)
        print(f'  ✅ {module}')
    except ImportError as e:
        print(f'  ❌ {module}: {e}')
        success = False

print()
if success:
    print('🎉 All core imports successful!')
else:
    print('⚠️  Some imports failed - install missing packages')
    sys.exit(1)
"

echo ""

# Test basic API
echo "🌐 Testing API startup..."
python -c "
try:
    from main import app
    print('✅ FastAPI app loads successfully')
except Exception as e:
    print(f'❌ FastAPI app failed to load: {e}')
    import sys
    sys.exit(1)
"

echo ""

# Test file structure
echo "📁 Testing project structure..."

required_files=(
    "README.md"
    "requirements.txt" 
    "main.py"
    ".env.example"
)

for file in "${required_files[@]}"; do
    if [[ -f "$file" ]]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (missing)"
    fi
done

required_dirs=(
    "web/static"
    "web/templates"
    "logs"
    "results"
)

for dir in "${required_dirs[@]}"; do
    if [[ -d "$dir" ]]; then
        echo "  ✅ $dir/"
    else
        echo "  ❌ $dir/ (missing)"
    fi
done

echo ""
echo "🎯 Basic tests completed!"
echo ""
echo "To run the server:"
echo "  python main.py"
echo ""
echo "To run full tests (when implemented):"
echo "  pytest tests/ -v"
echo ""