
import logging
import time
import mss
import pyautogui
import os
from PIL import Image
from agent.humanizer import generate_human_path, random_sleep, typing_delay

logger = logging.getLogger("DesktopAgent")

class DesktopAgent:
    def __init__(self):
        self.sct = mss.mss()
        # PyAutoGUI safety settings
        pyautogui.FAILSAFE = True # Move mouse to corner to abort
        pyautogui.PAUSE = 0.1
        
        # Get screen size
        self.screen_width, self.screen_height = pyautogui.size()
        
        # Log scaling info for Retina/High-DPI debugging
        try:
            monitor = self.sct.monitors[1]
            scale_x = self.screen_width / monitor["width"]
            scale_y = self.screen_height / monitor["height"]
            logger.info(f"🖥️  Desktop Resolution: {self.screen_width}x{self.screen_height} (Logical) | {monitor['width']}x{monitor['height']} (Physical)")
            logger.info(f"📐 Coordinate Scaling: X={scale_x:.2f}, Y={scale_y:.2f}")
        except Exception as e:
            logger.warning(f"Could not determine screen scaling: {e}")
        
    def get_screenshot(self, path: str = "desktop_screenshot.png") -> str:
        """Captures the full desktop."""
        monitor = self.sct.monitors[1] # Primary monitor
        sct_img = self.sct.grab(monitor)
        
        # Convert to PIL Image and save
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        img.save(path)
        return path

    def human_click(self, x: int, y: int):
        """Simulate human mouse movement and click on Desktop."""
        start_x, start_y = pyautogui.position()
        
        path = generate_human_path((start_x, start_y), (x, y))
        
        for point in path:
            pyautogui.moveTo(point[0], point[1], _pause=False)
            # Short sleep for velocity simulation, similar to browser agent
            # But pyautogui.moveTo(duration=...) is also an option. 
            # We'll use our own for consistency with the bezier curve.
            # actually pyautogui.moveTo is blocking? yes.
            # let's just move instant to points in loop
            
        pyautogui.click(x, y)
        logger.info(f"Desktop Clicked at ({x}, {y})")

    def human_type(self, text: str):
        """Simulate human typing on Desktop."""
        if not text: return
        
        for char in text:
            pyautogui.write(char) # PyAutoGUI has its own delay, but we want ours
            typing_delay() # Use our humanizer delay
            
        logger.info(f"Desktop Typed text: {text}")

    def execute_action(self, action_plan: dict):
        """Executes the action on the Desktop."""
        action = action_plan.get("action")
        target = action_plan.get("target_element", {})
        coords = target.get("coordinates")
        
        if action == "click":
            if coords:
                # Coordinate mapping might be needed if VLM uses different scale
                # Usually VLM sees image size, which matches screenshot size (retina might differ)
                # But mss captures actual pixels. PyAutoGUI uses logical points.
                # On Retina Mac: Screenshot might be 2x size of PyAutoGUI points.
                # We need to handle this scaling. 
                # For now, let's assume 1:1 or rely on user to calibrate.
                # Wait, better fix:
                # If screenshot is 2560x1600 but pyautogui.size() is 1280x800, we divide by 2.
                
                scale_x = self.screen_width / self.sct.monitors[1]["width"]
                scale_y = self.screen_height / self.sct.monitors[1]["height"]
                
                true_x = int(coords[0] * scale_x)
                true_y = int(coords[1] * scale_y)
                
                self.human_click(true_x, true_y)
            else:
                logger.warning("Desktop Click action requested but no coordinates provided.")
        
        elif action == "type":
            text = action_plan.get("value", "")
            if coords:
                 scale_x = self.screen_width / self.sct.monitors[1]["width"]
                 scale_y = self.screen_height / self.sct.monitors[1]["height"]
                 self.human_click(int(coords[0]*scale_x), int(coords[1]*scale_y))
                 
            self.human_type(text)
            
        elif action == "wait":
            random_sleep(2, 4)
