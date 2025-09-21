#!/usr/bin/env python3
"""
Test the server functionality including CSS serving and analysis endpoints
"""

import requests
import time
import subprocess
import signal
import os
import threading

def start_server():
    """Start the server in background"""
    return subprocess.Popen(
        ['./venv/bin/python', 'main.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid
    )

def wait_for_server(port=8000, timeout=10):
    """Wait for server to be ready"""
    for _ in range(timeout):
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=2)
            if response.status_code == 200:
                return True
        except:
            time.sleep(1)
    return False

def test_endpoints():
    """Test key endpoints"""
    base_url = "http://localhost:8000"

    tests = [
        ("/static/css/main.css", "CSS file"),
        ("/integrated-runs/gallery", "Gallery page"),
        ("/api/integrated-runs", "API endpoint"),
        ("/", "Main page")
    ]

    results = {}

    for endpoint, description in tests:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            results[description] = {
                'status': response.status_code,
                'success': response.status_code == 200
            }
            print(f"✅ {description}: {response.status_code}")
        except Exception as e:
            results[description] = {
                'status': 'ERROR',
                'success': False,
                'error': str(e)
            }
            print(f"❌ {description}: {e}")

    return results

def main():
    print("🧪 Testing Server Functionality")
    print("=" * 40)

    # Start server
    print("🚀 Starting server...")
    server_process = start_server()

    try:
        # Wait for server to be ready
        if wait_for_server():
            print("✅ Server started successfully")

            # Test endpoints
            print("\n📡 Testing endpoints...")
            results = test_endpoints()

            # Summary
            print(f"\n📊 Results Summary:")
            success_count = sum(1 for r in results.values() if r['success'])
            total_count = len(results)
            print(f"✅ {success_count}/{total_count} endpoints working correctly")

            if success_count == total_count:
                print("🎉 All tests passed! Server is fully functional.")
            else:
                print("⚠️  Some endpoints failed - check configuration.")

        else:
            print("❌ Server failed to start")

    finally:
        # Clean shutdown
        print("\n🛑 Shutting down server...")
        os.killpg(os.getpgid(server_process.pid), signal.SIGTERM)
        server_process.wait()
        print("✅ Server shutdown complete")

if __name__ == "__main__":
    main()