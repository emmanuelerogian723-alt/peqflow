"""
Slack Integration
Sends messages and DMs via Slack Web API.
"""
import httpx
from typing import Dict, Any
from .base import BaseIntegration, ExecutionResult


class SlackIntegration(BaseIntegration):
    name = "slack"
    display_name = "Slack"
    BASE_URL = "https://slack.com/api"
    
    def _get_headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self.credentials.get('bot_token', '')}",
            "Content-Type": "application/json",
        }
    
    def test_connection(self) -> ExecutionResult:
        try:
            resp = httpx.post(f"{self.BASE_URL}/auth.test", headers=self._get_headers(), timeout=10)
            data = resp.json()
            if data.get("ok"):
                return ExecutionResult(success=True, data={"team": data.get("team", ""), "bot": data.get("user", "")})
            return ExecutionResult(success=False, error=data.get("error", "Auth failed"))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def execute_action(self, operation: str, parameters: Dict, context: Dict) -> ExecutionResult:
        if operation == "message.send":
            return self._send_message(parameters, context)
        elif operation == "dm.send":
            return self._send_dm(parameters, context)
        elif operation == "channel.create":
            return self._create_channel(parameters, context)
        return ExecutionResult(success=False, error=f"Unknown operation: {operation}")
    
    def _send_message(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            channel = params.get("channel", "general")
            message = params.get("message", "")
            if not message:
                # Build from context
                message = f"FlowMind Alert: {context.get('event_type', 'trigger fired')}"
                if context.get("customer_name"):
                    message += f" | Customer: {context['customer_name']}"
                if context.get("amount"):
                    message += f" | Amount: {context['amount']}"
            
            resp = httpx.post(f"{self.BASE_URL}/chat.postMessage",
                json={"channel": channel, "text": message},
                headers=self._get_headers(), timeout=15)
            data = resp.json()
            if data.get("ok"):
                return ExecutionResult(success=True, data={"ts": data.get("ts", ""), "channel": data.get("channel", "")})
            return ExecutionResult(success=False, error=data.get("error", "Send failed"))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def _send_dm(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            user = params.get("user", "")
            message = params.get("message", "FlowMind notification")
            # Open DM channel first
            dm_resp = httpx.post(f"{self.BASE_URL}/conversations.open",
                json={"users": user},
                headers=self._get_headers(), timeout=10)
            dm_data = dm_resp.json()
            if not dm_data.get("ok"):
                return ExecutionResult(success=False, error=dm_data.get("error", "DM open failed"))
            channel = dm_data["channel"]["id"]
            # Send message
            resp = httpx.post(f"{self.BASE_URL}/chat.postMessage",
                json={"channel": channel, "text": message},
                headers=self._get_headers(), timeout=15)
            data = resp.json()
            if data.get("ok"):
                return ExecutionResult(success=True, data={"ts": data.get("ts", "")})
            return ExecutionResult(success=False, error=data.get("error", "DM send failed"))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def _create_channel(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            name = params.get("name", "flowmind-alerts")
            resp = httpx.post(f"{self.BASE_URL}/conversations.create",
                json={"name": name},
                headers=self._get_headers(), timeout=15)
            data = resp.json()
            if data.get("ok"):
                return ExecutionResult(success=True, data={"channel_id": data["channel"]["id"]})
            return ExecutionResult(success=False, error=data.get("error", "Create failed"))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
