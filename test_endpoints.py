#!/usr/bin/env python3
"""
Test all integrated runs endpoints to verify they work correctly
"""

import requests
import json
import time
from pathlib import Path

def test_endpoints():
    """Test all integrated runs endpoints"""
    base_url = "http://localhost:8000"

    print("🧪 Testing Integrated Runs Endpoints")
    print("=" * 50)

    # Test API endpoints
    print("\n📡 Testing API Endpoints")
    print("-" * 30)

    try:
        # Test list endpoint
        response = requests.get(f"{base_url}/api/integrated-runs", timeout=5)
        print(f"GET /api/integrated-runs: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Found {len(data['runs'])} runs")
            for run in data['runs'][:3]:
                print(f"    - {run['slug']} ({run['status']})")
        else:
            print(f"  Error: {response.text}")

    except requests.exceptions.ConnectionError:
        print("❌ Server not running on port 8000")
        print("💡 Start server with: ./venv/bin/python main.py")
        return False
    except Exception as e:
        print(f"❌ API Error: {e}")
        return False

    # Test frontend endpoints
    print("\n🌐 Testing Frontend Endpoints")
    print("-" * 30)

    endpoints = [
        "/integrated-runs/gallery",
        "/integrated-runs/create",
        "/",
        "/health"
    ]

    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            print(f"GET {endpoint}: {response.status_code}")
            if response.status_code != 200:
                print(f"  Error: {response.text[:100]}...")
        except Exception as e:
            print(f"GET {endpoint}: ERROR - {e}")

    # Test specific run page
    print("\n🔍 Testing Specific Run Pages")
    print("-" * 30)

    try:
        # Get a run slug to test
        response = requests.get(f"{base_url}/api/integrated-runs", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['runs']:
                slug = data['runs'][0]['slug']

                # Test run page
                response = requests.get(f"{base_url}/integrated-runs/{slug}", timeout=5)
                print(f"GET /integrated-runs/{slug}: {response.status_code}")

                # Test status API
                response = requests.get(f"{base_url}/api/integrated-runs/{slug}/status", timeout=5)
                print(f"GET /api/integrated-runs/{slug}/status: {response.status_code}")
                if response.status_code == 200:
                    status = response.json()
                    print(f"  Status: {status['status']}, Progress: {status['progress']}")
            else:
                print("No runs found to test")

    except Exception as e:
        print(f"❌ Run page test error: {e}")

    print("\n✅ Endpoint testing complete")
    return True

def test_server_info():
    """Get server information"""
    print("\n🔍 Server Information")
    print("-" * 30)

    # Check what's running on different ports
    ports = [8000, 8005, 8080, 8001]
    for port in ports:
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=2)
            if response.status_code == 200:
                print(f"✅ Server running on port {port}")
                try:
                    # Try to get API info
                    api_response = requests.get(f"http://localhost:{port}/api/integrated-runs", timeout=2)
                    if api_response.status_code == 200:
                        data = api_response.json()
                        print(f"   📊 {len(data['runs'])} integrated runs found")
                    else:
                        print(f"   ⚠️  Integrated runs API not available: {api_response.status_code}")
                except:
                    print(f"   ⚠️  No integrated runs API")
            else:
                print(f"❌ Port {port}: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"🔇 Port {port}: No server")
        except Exception as e:
            print(f"❓ Port {port}: {e}")

if __name__ == "__main__":
    test_server_info()
    test_endpoints()