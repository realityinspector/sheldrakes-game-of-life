#!/bin/bash
# Test script to simulate the line break argument issue

echo "Testing various argument patterns..."

echo ""
echo "1. Testing with line break (simulating user's issue):"
# This simulates what happens when there's a line break in the terminal
./training.sh --mode=control --generations=10 --grid-size=10 \
  --crystal-count=5

echo ""
echo "2. Testing with proper single line:"
./training.sh --mode=control --generations=10 --grid-size=10 --crystal-count=5

echo ""
echo "3. Testing stray argument detection:"
# This simulates what happens when the shell tries to execute the stray argument
echo "Simulating: zsh: command not found: --crystal-count=5"
echo "This happens when the shell interprets line breaks as command separators"