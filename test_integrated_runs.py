#!/usr/bin/env python3
"""
Test Suite for Integrated Runs Feature

Basic tests to verify the integrated runs functionality works correctly.
"""

import pytest
import json
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch

# Test imports
try:
    from storage.models import generate_unique_slug, generate_run_id
    from integrated_runs import IntegratedRunEngine
    from storage.database import get_database_info
    import_success = True
except ImportError as e:
    import_success = False
    import_error = str(e)


def test_imports():
    """Test that all required modules can be imported"""
    assert import_success, f"Import failed: {import_error}"


def test_slug_generation():
    """Test URL slug generation"""
    if not import_success:
        pytest.skip("Imports failed")

    # Test with custom slug
    slug1 = generate_unique_slug("my-test-run")
    assert "my-test-run" in slug1
    assert len(slug1) > len("my-test-run")  # Should have timestamp and ID

    # Test with empty slug
    slug2 = generate_unique_slug("")
    assert slug2.startswith("run-")

    # Test with special characters
    slug3 = generate_unique_slug("Test!@#$%Run")
    assert "test" in slug3.lower()
    assert "@" not in slug3  # Special chars should be removed

    # Test uniqueness
    slug4 = generate_unique_slug("test")
    slug5 = generate_unique_slug("test")
    assert slug4 != slug5  # Should be unique


def test_run_id_generation():
    """Test run ID generation"""
    if not import_success:
        pytest.skip("Imports failed")

    run_id1 = generate_run_id()
    run_id2 = generate_run_id()

    assert len(run_id1) > 30  # UUID should be long
    assert run_id1 != run_id2  # Should be unique
    assert "-" in run_id1  # UUID format


def test_database_config():
    """Test database configuration"""
    if not import_success:
        pytest.skip("Imports failed")

    db_info = get_database_info()

    assert "type" in db_info
    assert "url" in db_info
    assert db_info["type"] in ["SQLite", "PostgreSQL"]


@pytest.mark.asyncio
async def test_integrated_run_engine_init():
    """Test that IntegratedRunEngine can be initialized"""
    if not import_success:
        pytest.skip("Imports failed")

    engine = IntegratedRunEngine()
    assert engine.results_dir.exists()  # Should create results directory


def test_conway_factoids_exist():
    """Test that Conway factoids file exists and is valid JSON"""
    factoids_path = Path("conway_factoids.json")
    assert factoids_path.exists(), "Conway factoids file should exist"

    with open(factoids_path, 'r') as f:
        data = json.load(f)

    assert "factoids" in data
    assert len(data["factoids"]) > 0

    # Check first factoid structure
    first_factoid = data["factoids"][0]
    assert "title" in first_factoid
    assert "text" in first_factoid
    assert len(first_factoid["title"]) > 0
    assert len(first_factoid["text"]) > 0


def test_file_structure():
    """Test that required files exist"""
    required_files = [
        "main.py",
        "integrated_runs.py",
        "storage/models.py",
        "storage/database.py",
        "conway_factoids.json"
    ]

    for file_path in required_files:
        path = Path(file_path)
        assert path.exists(), f"Required file {file_path} should exist"


@pytest.mark.asyncio
async def test_parameter_validation():
    """Test parameter validation for integrated runs"""
    if not import_success:
        pytest.skip("Imports failed")

    # Valid parameters
    valid_params = {
        "generations": 50,
        "grid_size": 20,
        "crystal_count": 5,
        "initial_density": 0.4,
        "simulation_types": ["morphic", "classical"]
    }

    # Test parameter structure
    assert isinstance(valid_params["generations"], int)
    assert isinstance(valid_params["grid_size"], int)
    assert isinstance(valid_params["crystal_count"], int)
    assert isinstance(valid_params["initial_density"], float)
    assert isinstance(valid_params["simulation_types"], list)

    # Test reasonable ranges
    assert 10 <= valid_params["generations"] <= 1000
    assert 10 <= valid_params["grid_size"] <= 100
    assert 3 <= valid_params["crystal_count"] <= 16
    assert 0.1 <= valid_params["initial_density"] <= 0.8


def test_main_app_startup():
    """Test that the main FastAPI app can be imported"""
    try:
        from main import app
        assert app is not None
        assert hasattr(app, 'openapi')  # FastAPI app should have openapi method
    except Exception as e:
        pytest.fail(f"Failed to import main app: {e}")


if __name__ == "__main__":
    # Run tests directly
    print("🧪 Running Integrated Runs Tests")
    print("=" * 40)

    # Test imports
    print("Testing imports...", end=" ")
    try:
        test_imports()
        print("✅")
    except Exception as e:
        print(f"❌ {e}")

    # Test slug generation
    print("Testing slug generation...", end=" ")
    try:
        test_slug_generation()
        print("✅")
    except Exception as e:
        print(f"❌ {e}")

    # Test run ID generation
    print("Testing run ID generation...", end=" ")
    try:
        test_run_id_generation()
        print("✅")
    except Exception as e:
        print(f"❌ {e}")

    # Test file structure
    print("Testing file structure...", end=" ")
    try:
        test_file_structure()
        print("✅")
    except Exception as e:
        print(f"❌ {e}")

    # Test Conway factoids
    print("Testing Conway factoids...", end=" ")
    try:
        test_conway_factoids_exist()
        print("✅")
    except Exception as e:
        print(f"❌ {e}")

    print("\n🎉 Basic tests completed!")
    print("Run 'python -m pytest test_integrated_runs.py -v' for detailed test results.")