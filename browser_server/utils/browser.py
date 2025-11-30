from playwright.async_api import async_playwright   
from pathlib import Path

SCREENSHOT_DIR = Path(__file__).parent.parent / "screenshots" 
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
# Change the directory above as needed by default creates a screenshots folder in current directory

class BrowserManager:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None

    async def start_browser(self):
        """ensure the browser is started"""
        if self.playwright is None:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=False)
            self.page = await self.browser.new_page()

    async def goto(self, url: str):
        """navigate to a URL"""
        await self.start_browser()
        await self.page.goto(url)
        return f"Opened URL: {url}"
    
    async def get_content(self):
        """Return HTML of current page."""
        if not await self.ensure_page():
            return "Error: Browser not running."
        return await self.page.content()
    
    async def ensure_page(self):
        """Check if the page exists."""
        return self.page is not None
    
manager = BrowserManager()