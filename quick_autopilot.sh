#!/bin/bash
# Quick autopilot runner with preset configurations

set -e

echo "🤖 Quick Autopilot Configurations"
echo "================================"
echo ""
echo "Select a configuration:"
echo "  1) Small test (4 runs, 20 gens, 10x10 grid)"
echo "  2) Medium study (10 runs, 50 gens, 20x20 grid)"
echo "  3) Large research (20 runs, 100 gens, 25x25 grid)"
echo "  4) Custom configuration"
echo "  5) Cancel"
echo ""

read -p "Choice (1-5): " choice

case $choice in
    1)
        echo "Running small test configuration..."
        ./training.sh --mode=autopilot --runs=4 --generations=20 --grid-size=10 --crystal-count=3
        ;;
    2)
        echo "Running medium study configuration..."
        ./training.sh --mode=autopilot --runs=10 --generations=50 --grid-size=20 --crystal-count=5
        ;;
    3)
        echo "Running large research configuration..."
        ./training.sh --mode=autopilot --runs=20 --generations=100 --grid-size=25 --crystal-count=7
        ;;
    4)
        echo ""
        read -p "Number of runs (default 10): " runs
        read -p "Generations per run (default 50): " gens
        read -p "Grid size (default 20): " size
        read -p "Crystal count (default 5): " crystals

        runs=${runs:-10}
        gens=${gens:-50}
        size=${size:-20}
        crystals=${crystals:-5}

        echo "Running custom configuration: $runs runs, $gens gens, ${size}x${size} grid, $crystals crystals"
        ./training.sh --mode=autopilot --runs=$runs --generations=$gens --grid-size=$size --crystal-count=$crystals
        ;;
    5)
        echo "Cancelled."
        exit 0
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac