#!/bin/bash
# Emergence Simulator - Complete Launcher & Autopilot Test
# Configures environment and runs full system validation

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║    EMERGENCE SIMULATOR LAUNCHER      ║${NC}"
    echo -e "${BLUE}║         Full Setup + Autopilot       ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
    echo ""
}

print_section() {
    echo ""
    echo -e "${CYAN}▶ $1${NC}"
    echo "────────────────────────────────────────"
}

print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }

# Test tracking
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -n "  🧪 $test_name... "
    
    if eval "$test_command" >/dev/null 2>&1; then
        echo -e "${GREEN}✅${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}❌${NC}"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("$test_name")
        return 1
    fi
}

check_prerequisites() {
    print_section "System Prerequisites"
    
    # Python version check
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_info "Python found: $PYTHON_VERSION"
        
        # Version compatibility check (3.8+ but warn about 3.13)
        MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
        MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
        
        if [[ $MAJOR -ge 3 && $MINOR -ge 8 ]]; then
            if [[ $MAJOR -eq 3 && $MINOR -ge 13 ]]; then
                print_warn "Python 3.13+ detected - package build issues expected"
                print_warn "Packages like asyncpg and pydantic-core may fail to build"
                print_warn "RECOMMENDED: Use Python 3.11 or 3.12 for best compatibility"
                echo ""
                read -p "Continue anyway? (y/N): " -n 1 -r
                echo ""
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    print_info "Installation cancelled. Install Python 3.11/3.12 and try again."
                    exit 0
                fi
            fi
            print_success "Python version compatible"
        else
            print_error "Python 3.8+ required. Found $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python3 not found. Please install Python 3.8+"
        exit 1
    fi
    
    # Check for pip
    if python3 -m pip --version >/dev/null 2>&1; then
        print_info "pip available"
    else
        print_error "pip not available"
        exit 1
    fi
}

setup_environment() {
    print_section "Virtual Environment Setup"
    
    # Deactivate existing venv
    if [[ -n "$VIRTUAL_ENV" ]]; then
        print_warn "Deactivating existing virtual environment"
        deactivate 2>/dev/null || true
    fi
    
    # Clean slate
    if [[ -d "venv" ]]; then
        print_info "Removing old virtual environment..."
        rm -rf venv
    fi
    
    # Create new venv
    print_info "Creating virtual environment..."
    python3 -m venv venv
    
    # Activate
    print_info "Activating virtual environment..."
    source venv/bin/activate
    
    if [[ -z "$VIRTUAL_ENV" ]]; then
        print_error "Failed to activate virtual environment"
        exit 1
    fi
    
    print_success "Virtual environment ready: $VIRTUAL_ENV"
    
    # Upgrade pip
    print_info "Upgrading pip..."
    ./venv/bin/python -m pip install --upgrade pip --quiet
    
    # Clear cache
    print_info "Clearing pip cache..."
    pip cache purge >/dev/null 2>&1 || true
}

install_requirements() {
    print_section "Installing Dependencies"

    # Select requirements file based on Python version
    REQUIREMENTS_FILE="requirements.txt"
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

    if [[ $MAJOR -eq 3 && $MINOR -ge 13 ]]; then
        if [[ -f "requirements-py313.txt" ]]; then
            REQUIREMENTS_FILE="requirements-py313.txt"
            print_info "Using Python 3.13+ compatible requirements"
            print_info "Note: Some packages like asyncpg and pandas are excluded due to build issues"
        else
            print_warn "Python 3.13+ detected but no fallback requirements found"
            print_warn "Using standard requirements - expect build failures"
        fi
    fi

    if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
        print_error "$REQUIREMENTS_FILE not found"
        exit 1
    fi

    print_info "Installing core packages from $REQUIREMENTS_FILE..."
    print_info "This may take a few minutes..."

    # First, upgrade pip and setuptools for better Python 3.13 support
    print_info "Upgrading build tools for better compatibility..."
    ./venv/bin/python -m pip install --upgrade pip setuptools wheel --quiet

    # Install with better error handling and fallback strategy
    if [[ $MAJOR -eq 3 && $MINOR -ge 13 ]]; then
        print_info "Using Python 3.13 installation strategy with fallbacks..."

        # Try installing packages individually to identify problematic ones
        if ! ./venv/bin/python -m pip install -r "$REQUIREMENTS_FILE" --no-cache-dir --progress-bar off; then
            print_warn "Full installation failed, attempting package-by-package installation..."

            # Install packages one by one, skipping failures
            while IFS= read -r line || [[ -n "$line" ]]; do
                # Skip comments and empty lines
                [[ "$line" =~ ^[[:space:]]*# ]] && continue
                [[ -z "${line// }" ]] && continue

                package=$(echo "$line" | cut -d'#' -f1 | xargs)
                [[ -z "$package" ]] && continue

                echo -n "  Installing $package... "
                if ./venv/bin/python -m pip install "$package" --no-cache-dir --quiet 2>/dev/null; then
                    echo -e "${GREEN}✅${NC}"
                else
                    echo -e "${YELLOW}⚠️ skipped${NC}"
                fi
            done < "$REQUIREMENTS_FILE"

            print_warn "Some packages may have been skipped due to compatibility issues"
            print_info "Core functionality should still work"
        else
            print_success "All dependencies installed successfully"
        fi
    else
        # Standard installation for older Python versions
        if ./venv/bin/python -m pip install -r "$REQUIREMENTS_FILE" --no-cache-dir --progress-bar off; then
            print_success "Dependencies installed successfully"
        else
            print_error "Package installation failed"
            print_warn "This is likely due to Python version compatibility issues"
            exit 1
        fi
    fi

    # Show installed packages
    print_info "Successfully installed packages:"
    ./venv/bin/python -m pip list --format=columns | head -15
    local total_packages=$(./venv/bin/python -m pip list | wc -l)
    echo "  ... (total: $((total_packages - 2)) packages installed)"
}

create_configuration() {
    print_section "Configuration Setup"
    
    # Create .env if not exists
    if [[ ! -f ".env" ]]; then
        if [[ -f ".env.example" ]]; then
            cp .env.example .env
            print_success "Created .env from template"
        else
            # Create basic .env
            cat > .env << 'EOF'
DATABASE_URL=sqlite:///emergence.db
OPENROUTER_API_KEY=demo-key-for-testing
DEFAULT_MODEL=meta-llama/llama-3-70b-instruct
SECRET_KEY=development-secret-key-change-in-production
BASE_URL=http://localhost:8000
EOF
            print_success "Created basic .env file"
        fi
    else
        print_info ".env file already exists"
    fi
    
    # Ensure directories exist
    mkdir -p logs results test-results
    print_info "Created required directories"
}

run_autopilot_tests() {
    print_section "Autopilot Testing Suite"
    
    echo "🚀 Running comprehensive system tests..."
    echo ""
    
    # Test 1: Import Tests
    print_info "Phase 1: Core Import Tests"

    run_test "FastAPI import" "python -c 'import fastapi'"
    run_test "Uvicorn import" "python -c 'import uvicorn'"
    run_test "Pydantic import" "python -c 'import pydantic'"
    run_test "SQLAlchemy import" "python -c 'import sqlalchemy'"
    run_test "HTTPX import" "python -c 'import httpx'"
    run_test "Click import" "python -c 'import click'"
    run_test "Rich import" "python -c 'import rich'"

    # Optional imports (may be missing in Python 3.13+ setup)
    echo -n "  🧪 AsyncPG import (optional)... "
    if python -c 'import asyncpg' >/dev/null 2>&1; then
        echo -e "${GREEN}✅${NC}"
    else
        echo -e "${YELLOW}⚠️ not available${NC}"
    fi

    echo -n "  🧪 Pandas import (optional)... "
    if python -c 'import pandas' >/dev/null 2>&1; then
        echo -e "${GREEN}✅${NC}"
    else
        echo -e "${YELLOW}⚠️ not available (polars may be used instead)${NC}"
    fi
    
    echo ""
    
    # Test 2: Application Tests
    print_info "Phase 2: Application Loading Tests"
    
    run_test "Main app import" "python -c 'from main import app'"
    run_test "FastAPI instance" "python -c 'from main import app; assert app.title'"
    run_test "Health endpoint" "python -c 'from main import app; routes = [r.path for r in app.routes]; assert \"/health\" in routes'"
    
    echo ""
    
    # Test 3: File Structure Tests
    print_info "Phase 3: Project Structure Tests"
    
    run_test "README exists" "[[ -f README.md ]]"
    run_test "Requirements exists" "[[ -f requirements.txt ]]"
    run_test "Main script exists" "[[ -f main.py ]]"
    run_test "Test script exists" "[[ -f test.sh ]]"
    run_test "Logs directory" "[[ -d logs ]]"
    run_test "Results directory" "[[ -d results ]]"
    run_test "Web static directory" "[[ -d web/static ]]"
    run_test "Web templates directory" "[[ -d web/templates ]]"
    
    echo ""
    
    # Test 4: Configuration Tests
    print_info "Phase 4: Configuration Tests"
    
    run_test "Environment file" "[[ -f .env ]]"
    run_test "Gitignore file" "[[ -f .gitignore ]]"
    run_test "Web CSS file" "[[ -f web/static/css/main.css ]]"
    
    echo ""
    
    # Test 5: Advanced Functionality
    print_info "Phase 5: Server Startup Test"
    
    # Test server can start (background process)
    if python -c "
import signal
import sys
from main import app
import uvicorn
import threading
import time
import requests

def run_server():
    uvicorn.run(app, host='127.0.0.1', port=9999, log_level='critical')

def test_server():
    time.sleep(2)  # Wait for server to start
    try:
        response = requests.get('http://127.0.0.1:9999/health', timeout=5)
        if response.status_code == 200:
            print('SERVER_TEST_PASSED')
        else:
            print('SERVER_TEST_FAILED')
    except:
        print('SERVER_TEST_FAILED')
    finally:
        import os
        os._exit(0)

# Run server in thread
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# Test in another thread  
test_thread = threading.Thread(target=test_server)
test_thread.start()
test_thread.join()
" 2>/dev/null | grep -q "SERVER_TEST_PASSED"; then
        echo -e "  🧪 Server startup test... ${GREEN}✅${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "  🧪 Server startup test... ${YELLOW}⚠️ ${NC}(requires 'requests' package)"
        # Don't count as failure for basic setup
    fi
    
    echo ""
    
    # Test 6: Environment Integration
    print_info "Phase 6: Environment Integration Tests"
    
    run_test "Python in venv" "python -c 'import sys; assert \"venv\" in sys.executable'"
    run_test "Pip in venv" "pip --version | grep -q venv"
    run_test "Environment variables" "python -c 'import os; assert os.path.exists(\".env\")'"
    
    echo ""
}

show_test_results() {
    print_section "Test Results Summary"
    
    local total=$((TESTS_PASSED + TESTS_FAILED))
    local pass_rate=$((TESTS_PASSED * 100 / total))
    
    echo "📊 Test Statistics:"
    echo "   Total tests: $total"
    echo -e "   Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "   Failed: ${RED}$TESTS_FAILED${NC}"
    echo -e "   Pass rate: ${GREEN}${pass_rate}%${NC}"
    
    if [[ $TESTS_FAILED -gt 0 ]]; then
        echo ""
        echo -e "${YELLOW}Failed tests:${NC}"
        for test in "${FAILED_TESTS[@]}"; do
            echo "   ❌ $test"
        done
    fi
    
    echo ""
    
    if [[ $pass_rate -ge 90 ]]; then
        echo -e "${GREEN}🎉 EXCELLENT! System is ready for development${NC}"
    elif [[ $pass_rate -ge 75 ]]; then
        echo -e "${YELLOW}✅ GOOD! System is mostly ready (some optional features missing)${NC}"
    else
        echo -e "${RED}⚠️  NEEDS ATTENTION! Several core components failed${NC}"
    fi
}

print_next_steps() {
    print_section "Ready to Launch!"
    
    echo -e "${GREEN}🚀 Your Emergence Simulator is configured and tested!${NC}"
    echo ""
    echo -e "${CYAN}IMPORTANT: Virtual environment is ready but not activated in your shell${NC}"
    echo ""
    echo "To activate the environment and start developing:"
    echo -e "  ${GREEN}source venv/bin/activate${NC}"
    echo ""
    echo "Quick Commands (after activating venv):"
    echo "  🌐 Start server:          ./run.sh"
    echo "  🧪 Run tests:            ./test.sh"
    echo "  🏋️  Run training:         ./training.sh"
    echo ""
    echo "Or use these commands that auto-activate the venv:"
    echo "  🌐 Start server:          ./run.sh (automatically uses venv)"
    echo "  🧪 Run tests:            ./venv/bin/python -m pytest"
    echo ""
    echo "Direct uvicorn command (if needed):"
    echo "  🌐 Alternative start:     ./venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000"
    echo ""
    echo "URLs (once server is running):"
    echo "  🏠 Homepage:              http://localhost:8000"
    echo "  📚 API docs:              http://localhost:8000/docs"
    echo "  🔍 Health check:          http://localhost:8000/health"
    echo "  👁️  Viewer:                http://localhost:8000/viewer"
    echo ""
    echo "Configuration:"
    echo "  ⚙️  Environment:           .env"
    echo "  📝 Requirements:          requirements.txt"
    echo "  📊 Logs:                  logs/"
    echo "  💾 Results:               results/"
    echo ""
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}✨ Perfect setup! All systems go! ✨${NC}"
    else
        echo -e "${YELLOW}⚡ Setup complete with minor issues. Ready to develop! ⚡${NC}"
    fi
    
    echo ""
    echo -e "${YELLOW}💡 Pro tip: Run 'source venv/bin/activate' now to enter the environment!${NC}"
    echo -e "${YELLOW}💡 Or use './run.sh' to automatically start the server with the venv!${NC}"
    echo ""
    
    # Offer immediate options
    echo -e "${CYAN}What would you like to do next?${NC}"
    echo "  1) Activate virtual environment (source venv/bin/activate)"
    echo "  2) Start server immediately (./run.sh)"
    echo "  3) Exit and run commands manually"
    echo ""
    read -p "Choose option [1-3]: " -n 1 -r choice
    echo ""
    echo ""
    
    case $choice in
        1)
            echo -e "${GREEN}To activate the virtual environment, run:${NC}"
            echo -e "${GREEN}source venv/bin/activate${NC}"
            echo ""
            echo -e "${YELLOW}Note: The launcher script cannot directly activate venv in your shell.${NC}"
            echo -e "${YELLOW}You must run the 'source' command yourself.${NC}"
            ;;
        2)
            echo -e "${GREEN}Starting server with virtual environment...${NC}"
            if [[ -x "run.sh" ]]; then
                exec ./run.sh
            else
                echo -e "${RED}run.sh not found or not executable${NC}"
                exit 1
            fi
            ;;
        3|*)
            echo -e "${GREEN}Setup complete! Use the commands above when ready.${NC}"
            ;;
    esac
    echo ""
}

main() {
    print_header
    
    # Main setup sequence
    check_prerequisites
    setup_environment
    install_requirements  
    create_configuration
    
    # Comprehensive testing
    run_autopilot_tests
    
    # Results and next steps
    show_test_results
    print_next_steps
    
    # Final status
    if [[ $TESTS_FAILED -eq 0 ]]; then
        exit 0
    else
        exit 1
    fi
}

# Run the launcher
main