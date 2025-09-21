#!/bin/bash
# Quick run script for Emergence Simulator
# Automatically activates venv and starts server

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Emergence Simulator - Quick Start${NC}"
echo "======================================"

# Check if venv exists
if [[ ! -d "venv" ]]; then
    echo -e "${RED}❌ Virtual environment not found${NC}"
    echo "Run ./launcher.sh first to set up the environment"
    exit 1
fi

# Check if venv has packages installed
if [[ ! -f "venv/bin/python" ]]; then
    echo -e "${YELLOW}⚠️  Virtual environment appears incomplete (no Python)${NC}"
    echo "Run ./launcher.sh to reinstall dependencies"
    exit 1
fi

# Quick check for core dependencies
if ! ./venv/bin/python -c "import fastapi, uvicorn" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Virtual environment missing core packages${NC}"
    echo "Run ./launcher.sh to reinstall dependencies"
    exit 1
fi

echo -e "${GREEN}✅ Virtual environment found${NC}"

# Ensure required directories exist
echo -e "${GREEN}📁 Creating required directories...${NC}"
mkdir -p logs results results/integrated_runs test-results web/static/{css,js,images} web/templates storage/migrations core simulations/templates

# Find available port starting from 8000
PORT=8000
while lsof -i:$PORT >/dev/null 2>&1; do
    echo -e "${YELLOW}⚠️  Port $PORT is busy, trying next port...${NC}"
    ((PORT++))
    if [[ $PORT -gt 8010 ]]; then
        echo -e "${RED}❌ No available ports found in range 8000-8010${NC}"
        exit 1
    fi
done

echo -e "${GREEN}🌐 Starting server on port $PORT with venv Python...${NC}"
echo ""
echo "Server will be available at:"
echo "  🏠 Homepage:     http://localhost:$PORT"
echo "  📚 API docs:     http://localhost:$PORT/docs" 
echo "  👁️  Viewer:       http://localhost:$PORT/viewer"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Run with venv python on the found port - using more compatible startup method
echo "🌟 Starting Emergence Simulator on port $PORT..."

# Create a temporary Python script in current directory for better signal handling
cat > start_server_temp.py << EOF
import uvicorn
import sys
import os
from main import app

if __name__ == "__main__":
    try:
        # Use a simpler uvicorn configuration that's more compatible with Python 3.13
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=$PORT,
            log_level="info",
            access_log=True,
            use_colors=True,
            loop="asyncio"  # Use asyncio instead of uvloop for better compatibility
        )
    except KeyboardInterrupt:
        print('\n🛑 Server stopped by user.')
    except Exception as e:
        print(f'\n❌ Server error: {e}')
        sys.exit(1)
    finally:
        print('🛑 Server shutting down gracefully...')
EOF

# Trap signals to clean up temp file
trap 'rm -f start_server_temp.py' EXIT

# Run the server
exec ./venv/bin/python start_server_temp.py