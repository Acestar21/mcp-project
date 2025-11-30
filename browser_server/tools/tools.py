from mcp.server.fastmcp import FastMCP
from utils.browser import manager,SCREENSHOT_DIR
from datetime import datetime


def register_browser_tools(mcp: FastMCP):

    @mcp.tool()
    async def open_url(url: str) -> str:
        """Open a URL in the browser."""
        return await manager.goto(url)
    
    @mcp.tool()
    async def get_page_content() -> str:
        """Get the HTML content of the current page."""
        return await manager.get_content()
    
    @mcp.tool()
    async def take_screenshot(filename: str = "screenshot.png") -> str:
        """
        Take a screenshot and save it in the browser server's screenshots folder.
        """
        await manager.start_browser()

        if filename is None or filename.strip() == "":
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"screenshot_{timestamp}.png"
        else:
            # Ensure .png extension
            if not filename.lower().endswith(".png"):
                filename += ".png"
            save_path = SCREENSHOT_DIR / filename

        try:
            await manager.page.screenshot(path=str(save_path))
            return f"Screenshot saved to: {save_path}"
        except Exception as e:
            return f"Error taking screenshot: {str(e)}"