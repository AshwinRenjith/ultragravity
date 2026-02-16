
import logging
import time
import random
from playwright.sync_api import sync_playwright, Page, ElementHandle
from agent.humanizer import generate_human_path, random_sleep, typing_delay

# Import stealth
try:
    from playwright_stealth import Stealth

    def _apply_stealth(page):
        stealth = Stealth()
        stealth.apply_stealth_sync(page)

except Exception:
    try:
        from playwright_stealth import stealth_sync

        def _apply_stealth(page):
            stealth_sync(page)

    except Exception:
        def _apply_stealth(page):
            return None

class BrowserAgent:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.logger = logging.getLogger("BrowserAgent")

    def start(self):
        self.playwright = sync_playwright().start()
        # Launch with minimal arguments first to ensure stability
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
            ]
        )
        self.context = self.browser.new_context(
            viewport={"width": 1280, "height": 720}, # Standard viewport
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        
        self.page = self.context.new_page()
        
        # Apply stealth to the page
        _apply_stealth(self.page)
        
        # Add script to remove "navigator.webdriver" property as a backup
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

    def navigate(self, url: str):
        self.logger.info(f"Navigating to {url}")
        self.page.goto(url, wait_until="domcontentloaded")
        random_sleep(1, 2) # Human pause after load

    def get_screenshot(self, path: str = "screenshot.png"):
        self.page.screenshot(path=path)
        return path

    def get_accessibility_tree(self):
        return self.page.accessibility.snapshot()

    def human_click(self, x: int, y: int):
        """Simulate human mouse movement and click."""
        # Get current mouse position
        # Playwright doesn't expose current mouse pos directly easily in sync API without tracking, 
        # so we assume starting from a known or random point if it's the first move.
        # But we can just "teleport" to a random edge or use last known pos if we tracked it.
        # For simplicity, start from (0,0) or last pos.
        
        start_x, start_y = 0, 0 # In a real implementation we track self.mouse_pos
        
        path = generate_human_path((start_x, start_y), (x, y))
        
        for point in path:
            self.page.mouse.move(point[0], point[1])
            # Add a small, variable sleep to simulate velocity (faste in middle, slow at ends)
            # This is a very rough approximation.
            time.sleep(random.uniform(0.001, 0.003)) 
            
        random_sleep(0.1, 0.3)
        self.page.mouse.click(x, y)
        self.logger.info(f"Clicked at ({x}, {y})")

    def human_type(self, text: str, selector: str = None):
        """Simulate human typing."""
        if selector:
            self.page.click(selector)
            
        if not text:
            self.logger.warning("human_type called with empty or None text.")
            return

        for char in text:
            if char == '\n':
                self.page.keyboard.press("Enter")
            else:
                self.page.keyboard.type(char)
            typing_delay()
            
        self.logger.info(f"Typed text: {text}")

    def scroll_human(self, dy: int):
        """Smooth scroll."""
        self.page.mouse.wheel(0, dy)
        random_sleep(0.5, 1.0)

    def execute_action(self, action_plan: dict):
        """Executes the action determined by the Vision module."""
        action = action_plan.get("action")
        target = action_plan.get("target_element", {})
        coords = target.get("coordinates")
        
        if action == "click":
            if coords:
                self.human_click(coords[0], coords[1])
            else:
                self.logger.warning("Click action requested but no coordinates provided.")
        
        elif action == "type":
            text = action_plan.get("value", "")
            if coords:
                self.human_click(coords[0], coords[1])
            self.human_type(text)
            
        elif action == "scroll":
            # Default scroll down if not specified
            self.scroll_human(500)
            
        elif action == "wait":
            random_sleep(2, 4)
            
        elif action == "done":
            self.logger.info("Task completed.")
            
        elif action == "fail":
            self.logger.error(f"Action failed: {action_plan.get('reasoning')}")

    def stop(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
