"""
FlowMind Integration Base
Base class for all integrations. Each integration handles its own API calls.
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ExecutionResult:
    success: bool
    data: Dict[str, Any] = None
    error: str = ""
    
    def to_dict(self) -> Dict:
        return {"success": self.success, "data": self.data or {}, "error": self.error}


class BaseIntegration:
    """Base class for all FlowMind integrations."""
    name: str = "base"
    display_name: str = "Base"
    
    def __init__(self, credentials: Dict[str, str]):
        self.credentials = credentials
    
    def execute_trigger(self, operation: str, parameters: Dict, context: Dict) -> ExecutionResult:
        """Check if a trigger condition is met. Called by the runtime engine."""
        return ExecutionResult(success=True, data={"triggered": True})
    
    def execute_action(self, operation: str, parameters: Dict, context: Dict) -> ExecutionResult:
        """Execute an action. Called by the runtime engine."""
        return ExecutionResult(success=True, data={"executed": True})
    
    def test_connection(self) -> ExecutionResult:
        """Test if the integration credentials are valid."""
        return ExecutionResult(success=True, data={"connected": True})
