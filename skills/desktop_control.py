
import re
import time
from skills.base import Skill
from agent.bridge_applescript import open_app
from termcolor import colored

class DesktopControlSkill(Skill):
    def __init__(self, agent):
        super().__init__(agent)

    def can_handle(self, instruction: str) -> float:
        # Only handle if in desktop mode or explicitly requested
        lower_instr = instruction.lower()

        # WhatsApp is handled by WhatsAppSkill — yield priority
        if "whatsapp" in lower_instr:
            return 0.1

        if "calculator" in lower_instr and ("calculate" in lower_instr or "open" in lower_instr):
            return 0.95
        if "open" in lower_instr or "launch" in lower_instr:
             # Check if it looks like an app name follows
             return 0.8
        return 0.1

    def execute(self, params: dict) -> dict:
        instruction = params["instruction"]
        lower_instr = instruction.lower()
        
        # 1. Handle "Open/Launch [App]"
        app_name = None
        if "calculator" in lower_instr:
            app_name = "Calculator"
        elif "notes" in lower_instr:
            app_name = "Notes"
        elif "safari" in lower_instr:
             app_name = "Safari"
        elif "messages" in lower_instr:
             app_name = "Messages"
        elif "terminal" in lower_instr:
             app_name = "Terminal"
             
        if app_name:
            print(colored(f"🖥️  Fast Path: Opening {app_name}...", "cyan"))
            open_app(app_name)
            time.sleep(2) # Wait for animation
            
            # 2. Handle specific app logic matching the instruction
            if app_name == "Calculator":
                # Extract math expression? 
                # "calculate 50 * 50"
                # Regex to find numbers and operators
                match = re.search(r'calculate\s+([\d\s\+\-\*\/\.]+)', lower_instr)
                if match:
                    expression = match.group(1).strip()
                    print(colored(f"🔢 Typing equation: {expression}", "cyan"))
                    self.agent.desktop.human_type(expression)
                    time.sleep(0.5)
                    self.agent.desktop.human_type("=") # Press equals
                    return {"status": "success", "message": f"Opened Calculator and typed '{expression}'"}
            
            if app_name == "Notes":
                # Check if we should create a note content
                # "write an essay on x in my notes app"
                if "write" in lower_instr or "create" in lower_instr:
                     # Simple extraction of everything after "on" or "about"
                     # helping the VLM rate limit issue by doing it here.
                     content = instruction
                     # Try to strip "write a note about"
                     for prefix in ["write a note about ", "write a note on ", "create a note about ", "write an essay on "]:
                         if prefix in lower_instr:
                             start = lower_instr.find(prefix) + len(prefix)
                             content = instruction[start:]
                             break
                     
                     print(colored(f"📝 Creating Note: {content[:30]}...", "cyan"))
                     from agent.bridge_applescript import create_note # Keep specific import or move to top if circular dependency risk is low. 
                     # Actually, to avoid circular deps with core->skills->bridge->... wait. 
                     # Core imports Skills. Skills imports Bridge. Bridge imports nothing (from agent).
                     # It is safe to import at top.
                     create_note(content)
                     return {"status": "success", "message": f"Created note about '{content[:20]}...'"}

            return {"status": "success", "message": f"Opened {app_name}"}

        return {"status": "fail", "reason": "Could not identify app or action."}
