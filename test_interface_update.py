#!/usr/bin/env python3
"""
Test Suite for Updated Interface

Verify that the interface updates are working correctly.
"""

import requests
import json
from pathlib import Path

def test_interface_content():
    """Test that the main interface contains the expected content"""
    # Read the main.py file to verify content
    main_py = Path("main.py")
    assert main_py.exists(), "main.py should exist"

    content = main_py.read_text()

    # Check for new interface elements
    interface_elements = [
        "Integrated Research Platform",
        "🧬 Create Integrated Run",
        "📚 Browse Gallery",
        "hero-features",
        "showcase-section",
        "What Makes Integrated Runs Special",
        "Side-by-Side Analysis",
        "Research Notebooks",
        "Educational Content",
        "Version 2.0.0",
        "Integrated Runs Ready",
        "LLM Integration Active"
    ]

    for element in interface_elements:
        assert element in content, f"Interface should contain '{element}'"

    print("✅ Interface content verification passed")

def test_css_classes():
    """Test that new CSS classes are present"""
    main_py = Path("main.py")
    content = main_py.read_text()

    css_classes = [
        ".hero-features",
        ".hero-badge",
        ".quick-actions",
        ".cta-button",
        ".showcase-section",
        ".showcase-grid",
        ".showcase-card",
        ".nav-card.featured",
        ".card-features",
        ".badge.new"
    ]

    for css_class in css_classes:
        assert css_class in content, f"CSS should contain '{css_class}'"

    print("✅ CSS classes verification passed")

def test_responsive_design():
    """Test that responsive design elements are present"""
    main_py = Path("main.py")
    content = main_py.read_text()

    responsive_elements = [
        "@media (max-width: 768px)",
        "@media (max-width: 480px)",
        "flex-direction: column",
        "grid-template-columns: 1fr"
    ]

    for element in responsive_elements:
        assert element in content, f"Responsive design should contain '{element}'"

    print("✅ Responsive design verification passed")

def test_navigation_structure():
    """Test that navigation structure is properly organized"""
    main_py = Path("main.py")
    content = main_py.read_text()

    # Check for proper section organization
    sections = [
        "🚀 Integrated Research Platform",
        "🧪 Research Tools",
        "📚 Documentation & API",
        "🎯 What Makes Integrated Runs Special",
        "🔬 Core Technologies"
    ]

    for section in sections:
        assert section in content, f"Navigation should contain section '{section}'"

    print("✅ Navigation structure verification passed")

def test_api_endpoints():
    """Test that API endpoints are documented"""
    main_py = Path("main.py")
    content = main_py.read_text()

    api_endpoints = [
        "POST /api/integrated-runs",
        "GET /api/integrated-runs/{slug}/status",
        "GET /api/integrated-runs",
        "DELETE /api/integrated-runs/{slug}"
    ]

    for endpoint in api_endpoints:
        assert endpoint in content, f"API documentation should contain '{endpoint}'"

    print("✅ API endpoints documentation passed")

def test_integrated_runs_links():
    """Test that integrated runs links are present"""
    main_py = Path("main.py")
    content = main_py.read_text()

    links = [
        "/integrated-runs/create",
        "/integrated-runs/gallery",
        "/integrated-runs/{slug}"
    ]

    for link in links:
        assert link in content, f"Should contain link '{link}'"

    print("✅ Integrated runs links verification passed")

if __name__ == "__main__":
    print("🧪 Testing Updated Interface")
    print("=" * 40)

    try:
        test_interface_content()
        test_css_classes()
        test_responsive_design()
        test_navigation_structure()
        test_api_endpoints()
        test_integrated_runs_links()

        print("\n🎉 All interface tests passed!")
        print("✅ Interface update successful")

    except AssertionError as e:
        print(f"\n❌ Interface test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        exit(1)