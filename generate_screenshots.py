#!/usr/bin/env python3
"""
Screenshot generator for Cardboard Cabinet
Generates screenshots of different views for the README
"""
import asyncio
import os
from playwright.async_api import async_playwright

async def generate_screenshots():
    """Generate screenshots of the Cardboard Cabinet application"""
    
    # Create screenshots directory if it doesn't exist
    screenshots_dir = "screenshots"
    os.makedirs(screenshots_dir, exist_ok=True)
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            device_scale_factor=2  # High DPI for crisp screenshots
        )
        
        page = await context.new_page()
        
        print("🌐 Loading Cardboard Cabinet...")
        await page.goto("http://localhost:8000")
        
        # Wait for the app to load
        await page.wait_for_selector("#results", timeout=10000)
        
        # Wait a bit more for any animations to complete
        await asyncio.sleep(2)
        
        print("📸 Generating screenshots...")
        
        # 1. Main Dashboard View (Tile View)
        print("  - Main Dashboard (Tile View)")
        await page.screenshot(
            path=f"{screenshots_dir}/01-main-dashboard-tile-view.png",
            full_page=True
        )
        
        # 2. Switch to List View
        print("  - Switching to List View")
        await page.click("#view-toggle")
        await asyncio.sleep(1)  # Wait for transition
        
        await page.screenshot(
            path=f"{screenshots_dir}/02-list-view.png",
            full_page=True
        )
        
        # 3. Switch back to Tile View
        print("  - Switching back to Tile View")
        await page.click("#view-toggle")
        await asyncio.sleep(1)
        
        # 4. Show Mechanics Filter
        print("  - Mechanics Filter View")
        # Click on a mechanics tag to show filtering
        mechanics_tags = await page.query_selector_all(".tag")
        if mechanics_tags:
            await mechanics_tags[0].click()
            await asyncio.sleep(1)
            
        await page.screenshot(
            path=f"{screenshots_dir}/03-mechanics-filter.png",
            full_page=True
        )
        
        # 5. Show Search Functionality
        print("  - Search Functionality")
        search_input = await page.query_selector("#search")
        if search_input:
            await search_input.fill("Ticket")
            await asyncio.sleep(1)
            
        await page.screenshot(
            path=f"{screenshots_dir}/04-search-functionality.png",
            full_page=True
        )
        
        # 6. Show Filters Panel
        print("  - Filters Panel")
        # Scroll to show more filters
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(1)
        
        await page.screenshot(
            path=f"{screenshots_dir}/05-filters-panel.png",
            full_page=True
        )
        
        # 7. Mobile Responsive View
        print("  - Mobile Responsive View")
        await page.set_viewport_size({'width': 768, 'height': 1024})
        await asyncio.sleep(1)
        
        await page.screenshot(
            path=f"{screenshots_dir}/06-mobile-responsive.png",
            full_page=True
        )
        
        # 8. Desktop Full View
        print("  - Desktop Full View")
        await page.set_viewport_size({'width': 1920, 'height': 1080})
        await asyncio.sleep(1)
        
        await page.screenshot(
            path=f"{screenshots_dir}/07-desktop-full-view.png",
            full_page=True
        )
        
        await browser.close()
        
        print(f"✅ Screenshots generated in '{screenshots_dir}/' directory")
        print("📁 Generated screenshots:")
        for file in sorted(os.listdir(screenshots_dir)):
            if file.endswith('.png'):
                print(f"   - {file}")

if __name__ == "__main__":
    print("🎲 Cardboard Cabinet Screenshot Generator")
    print("=" * 50)
    
    try:
        asyncio.run(generate_screenshots())
    except Exception as e:
        print(f"❌ Error generating screenshots: {e}")
        print("\n💡 Make sure:")
        print("   1. The app is running on http://localhost:8000")
        print("   2. You have some games loaded in the collection")
        print("   3. Playwright is installed: pip install playwright")
        print("   4. Playwright browsers are installed: playwright install")

