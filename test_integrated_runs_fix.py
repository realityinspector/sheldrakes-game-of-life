#!/usr/bin/env python3
"""
Test script to verify integrated runs with virtual environment fixes
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path
sys.path.append('.')

from integrated_runs import integrated_run_engine

async def test_integrated_runs():
    print("🧪 Testing Integrated Runs with Fixes")
    print("=" * 50)

    # Test parameters (small and fast for testing)
    test_params = {
        "generations": 5,  # Very small for quick test
        "grid_size": 10,   # Small grid
        "crystal_count": 2,
        "initial_density": 0.4,
        "simulation_types": ["morphic", "classical"]  # Just 2 types
    }

    try:
        # Create run
        print("📝 Creating integrated run...")
        slug = await integrated_run_engine.create_integrated_run(test_params, "test-fix")
        print(f"✅ Created run: {slug}")

        # Check initial status
        status = integrated_run_engine.get_run_status(slug)
        print(f"📊 Initial status: {status['status']} - {status['current_stage']}")

        # Execute the run
        print("🚀 Executing integrated run...")
        await integrated_run_engine.execute_integrated_run(slug)

        # Check final status
        final_status = integrated_run_engine.get_run_status(slug)
        print(f"📊 Final status: {final_status['status']} - {final_status['current_stage']}")

        # Check if files were created
        results_dir = Path("results/integrated_runs") / slug
        if results_dir.exists():
            files_created = list(results_dir.glob("*.*"))
            print(f"📁 Files created: {[f.name for f in files_created]}")

            # Check file sizes
            for file_path in files_created:
                size = file_path.stat().st_size
                print(f"  📄 {file_path.name}: {size} bytes {'✅' if size > 0 else '❌ (empty)'}")
        else:
            print("❌ Results directory not found")

        print("✅ Test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        print(f"Traceback:\n{traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_integrated_runs())
    sys.exit(0 if success else 1)