#!/usr/bin/env python3
"""
Playwright script to debug integrated runs page loading issues
"""

import asyncio
import sys
from playwright.async_api import async_playwright

async def debug_integrated_run():
    async with async_playwright() as p:
        # Launch browser in headless mode for debugging
        browser = await p.chromium.launch(
            headless=True,   # Run headlessly for CI/automation
            slow_mo=1000     # Slow down actions for easier debugging
        )

        page = await browser.new_page()

        # Set up console logging
        page.on("console", lambda msg: print(f"🔹 Console [{msg.type}]: {msg.text}"))
        page.on("pageerror", lambda error: print(f"🔴 Page Error: {error}"))

        # Set up request failure logging
        page.on("requestfailed", lambda request: print(f"🔴 Request Failed: {request.url} - {request.failure}"))

        # Navigate to the integrated run page
        url = "http://localhost:8000/integrated-runs/run-20250919-111635-3b76ca6f"
        print(f"🌐 Navigating to: {url}")

        try:
            await page.goto(url, timeout=10000)
            print("✅ Page loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load page: {e}")
            # Try to start the server
            print("🔄 Attempting to check if server is running...")
            try:
                await page.goto("http://localhost:8000/health", timeout=5000)
                print("✅ Server is running, retrying original URL...")
                await page.goto(url, timeout=10000)
            except:
                print("❌ Server not running. Please start with ./run.sh")
                await browser.close()
                return

        # Wait for the page to load
        await page.wait_for_timeout(3000)

        # Check if results container is visible
        results_container = await page.locator("#results-container").is_visible()
        print(f"📊 Results container visible: {results_container}")

        # Check for loading state
        loading_state = await page.locator(".loading-state").count()
        print(f"⏳ Loading state elements: {loading_state}")

        # Check for error messages
        error_messages = await page.locator(".error").count()
        print(f"❌ Error messages: {error_messages}")

        # Check if images are loading
        images = await page.locator("img").all()
        print(f"🖼️  Total images found: {len(images)}")

        for i, img in enumerate(images):
            src = await img.get_attribute("src")
            alt = await img.get_attribute("alt") or "no alt"
            is_loaded = await img.evaluate("img => img.complete && img.naturalHeight !== 0")
            print(f"  Image {i+1}: {alt} - {src} - {'✅ Loaded' if is_loaded else '❌ Not loaded'}")

        # Wait specifically for the educational content to appear
        print("⏳ Waiting for educational content to load...")
        try:
            # Wait up to 10 seconds for educational content to appear
            await page.wait_for_selector(".educational-walkthrough", timeout=10000)
            print("✅ Educational walkthrough content found!")
        except:
            print("⚠️ Educational walkthrough content not found within 10 seconds, continuing anyway...")

        # Wait a bit more for content to fully render
        await page.wait_for_timeout(2000)

        # Check if educational content is present AFTER waiting
        educational_content_after_wait = await page.locator(".educational-walkthrough").count()
        print(f"🎓 Educational walkthrough elements after wait: {educational_content_after_wait}")

        # Check for key educational sections
        concept_boxes_after_wait = await page.locator(".concept-box").count()
        print(f"💡 Concept boxes found after wait: {concept_boxes_after_wait}")

        # Get the actual content from results-content div
        results_content = await page.locator("#results-content").inner_html()
        print(f"📄 Actual results-content HTML (first 500 chars): {results_content[:500]}...")

        # Scroll down to see more content
        await page.evaluate("window.scrollBy(0, 500)")
        await page.wait_for_timeout(1000)

        # Take a screenshot AFTER content is loaded
        screenshot_path = "debug_integrated_run_screenshot.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"📸 Screenshot saved: {screenshot_path}")

        # Check again after screenshot
        educational_content = await page.locator(".educational-walkthrough").count()
        print(f"🎓 Educational walkthrough elements after screenshot: {educational_content}")

        concept_boxes = await page.locator(".concept-box").count()
        print(f"💡 Concept boxes found after screenshot: {concept_boxes}")

        animation_cards = await page.locator(".animation-card.enhanced").count()
        print(f"🎬 Enhanced animation cards: {animation_cards}")

        # Get a sample of the content
        results_html = await page.locator("#results-content").inner_html()
        content_sample = results_html[:500] if results_html else "No content"
        print(f"📄 Content sample: {content_sample}...")

        # Check network requests
        print("\n🌐 Checking for failed network requests...")

        # Set up network monitoring for future requests
        failed_requests = []

        def handle_response(response):
            if response.status >= 400:
                failed_requests.append(f"❌ {response.status} {response.url}")
            else:
                print(f"✅ {response.status} {response.url}")

        page.on("response", handle_response)

        # Trigger a page refresh to capture network activity
        print("🔄 Refreshing page to capture network activity...")
        await page.reload()
        await page.wait_for_timeout(5000)

        # Print failed requests
        if failed_requests:
            print("\n❌ Failed Network Requests:")
            for req in failed_requests:
                print(f"  {req}")
        else:
            print("\n✅ No failed network requests detected")

        # Check final state
        final_content = await page.locator("#results-content").inner_text()
        print(f"\n📄 Results content preview: {final_content[:200]}...")

        print("\n🔍 Debug session complete.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_integrated_run())