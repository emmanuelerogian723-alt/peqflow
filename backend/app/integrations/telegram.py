"""
Telegram Integration
Sends messages and files via Telegram Bot API.
"""
import httpx
from typing import Dict, Any
from .base import BaseIntegration, ExecutionResult


class TelegramIntegration(BaseIntegration):
    name = "telegram"
    display_name = "Telegram"
    
    def _get_url(self, method: str) -> str:
        token = self.credentials.get("bot_token", "")
        return f"https://api.telegram.org/bot{token}/{method}"
    
    def test_connection(self) -> ExecutionResult:
        try:
            resp = httpx.get(self._get_url("getMe"), timeout=10)
            data = resp.json()
            if data.get("ok"):
                return ExecutionResult(success=True, data={"bot_name": data["result"].get("username", "")})
            return ExecutionResult(success=False, error=data.get("description", "Auth failed"))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def execute_action(self, operation: str, parameters: Dict, context: Dict) -> ExecutionResult:
        if operation == "message.send":
            return self._send_message(parameters, context)
        elif operation == "photo.send":
            return self._send_photo(parameters, context)
        elif operation == "document.send":
            return self._send_document(parameters, context)
        return ExecutionResult(success=False, error=f"Unknown operation: {operation}")
    
    def _send_message(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            chat_id = params.get("chat_id") or context.get("telegram_chat_id", "")
            message = params.get("message", "")
            if not message:
                message = f"FlowMind Alert: {context.get('event_type', 'trigger fired')}"
                if context.get("amount"):
                    message += f"\nAmount: {context['amount']}"
                if context.get("customer_name"):
                    message += f"\nCustomer: {context['customer_name']}"
            
            resp = httpx.post(self._get_url("sendMessage"), json={
                "chat_id": chat_id, "text": message, "parse_mode": "HTML"
            }, timeout=15)
            data = resp.json()
            if data.get("ok"):
                return ExecutionResult(success=True, data={"message_id": data["result"].get("message_id", 0)})
            return ExecutionResult(success=False, error=data.get("description", "Send failed"))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def _send_photo(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            chat_id = params.get("chat_id") or context.get("telegram_chat_id", "")
            resp = httpx.post(self._get_url("sendPhoto"), json={
                "chat_id": chat_id, "photo": params.get("photo_url", ""),
                "caption": params.get("caption", "")
            }, timeout=15)
            data = resp.json()
            if data.get("ok"):
                return ExecutionResult(success=True, data={"message_id": data["result"].get("message_id", 0)})
            return ExecutionResult(success=False, error=data.get("description", "Photo failed"))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def _send_document(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            chat_id = params.get("chat_id") or context.get("telegram_chat_id", "")
            resp = httpx.post(self._get_url("sendDocument"), json={
                "chat_id": chat_id, "document": params.get("document_url", "")
            }, timeout=15)
            data = resp.json()
            if data.get("ok"):
                return ExecutionResult(success=True, data={"message_id": data["result"].get("message_id", 0)})
            return ExecutionResult(success=False, error=data.get("description", "Document failed"))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
