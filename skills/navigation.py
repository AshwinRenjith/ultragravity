from typing import Dict, Any
from .base import Skill

class NavigationSkill(Skill):
    """
    Skill for handling direct URL navigation.
    """

    def can_handle(self, instruction: str) -> float:
        """
        High confidence if instruction contains 'go to' or a URL.
        """
        if "go to" in instruction.lower() or "navigate to" in instruction.lower() or "http" in instruction:
            return 0.9
        return 0.1

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        url = params.get("url", "")
        if not url:
            # Try to extract URL from instruction if not explicitly provided
            instruction = params.get("instruction", "")
            words = instruction.split()
            for word in words:
                if word.startswith("http") or word.startswith("www"):
                    url = word
                    break
        
        if not url:
             return {"status": "fail", "reason": "No URL provided."}

        self.logger.info(f"Executing NavigationSkill to: '{url}'")
        try:
            self.agent.browser.navigate(url)
            return {"status": "success", "message": f"Navigated to '{url}'"}
        except Exception as e:
            return {"status": "fail", "reason": str(e)}
