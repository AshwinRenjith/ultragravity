from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class Skill(ABC):
    """
    Abstract base class for all skills in the Skill Hub.
    Skills are specialized modules that perform specific tasks or workflows,
    reducing the need for constant VLM analysis and enhancing performance.
    """
    
    def __init__(self, agent_core):
        """
        Initialize the skill with a reference to the main agent core.
        This provides access to the browser, vision, and logger modules.
        """
        self.agent = agent_core
        self.logger = agent_core.logger
        self.name = self.__class__.__name__

    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the skill with the provided parameters.
        Returns a dictionary containing the result of the execution.
        """
        pass

    @abstractmethod
    def can_handle(self, instruction: str) -> float:
        """
        Determine if this skill is relevant for the given instruction.
        Returns a confidence score between 0.0 and 1.0.
        """
        pass
