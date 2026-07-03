"""
Gmail Integration
Sends emails via Gmail API using OAuth2.
"""
import base64
import httpx
from typing import Dict, Any
from .base import BaseIntegration, ExecutionResult


class GmailIntegration(BaseIntegration):
    name = "gmail"
    display_name = "Gmail"
    BASE_URL = "https://gmail.googleapis.com/gmail/v1"
    
    def _get_access_token(self) -> str:
        """Refresh access token using refresh token."""
        try:
            resp = httpx.post("https://oauth2.googleapis.com/token", data={
                "client_id": self.credentials.get("client_id", ""),
                "client_secret": self.credentials.get("client_secret", ""),
                "refresh_token": self.credentials.get("refresh_token", ""),
                "grant_type": "refresh_token",
            }, timeout=10)
            data = resp.json()
            return data.get("access_token", "")
        except:
            return ""
    
    def _get_headers(self) -> Dict:
        token = self._get_access_token()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_connection(self) -> ExecutionResult:
        token = self._get_access_token()
        if token:
            return ExecutionResult(success=True, data={"connected": True})
        return ExecutionResult(success=False, error="Gmail auth failed")
    
    def execute_action(self, operation: str, parameters: Dict, context: Dict) -> ExecutionResult:
        if operation == "email.send":
            return self._send_email(parameters, context)
        elif operation == "email.reply":
            return self._reply_email(parameters, context)
        elif operation == "label.add":
            return self._add_label(parameters, context)
        return ExecutionResult(success=False, error=f"Unknown operation: {operation}")
    
    def _send_email(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            to = params.get("to") or context.get("customer_email", "")
            subject = params.get("subject", context.get("email_subject", "Notification from FlowMind"))
            body = params.get("body", context.get("email_body", "This is an automated message from FlowMind."))
            
            # Build raw RFC822 message
            raw = f"To: {to}\r\nSubject: {subject}\r\nContent-Type: text/html; charset=utf-8\r\n\r\n{body}"
            encoded = base64.urlsafe_b64encode(raw.encode()).decode()
            
            resp = httpx.post(
                f"{self.BASE_URL}/users/me/messages/send",
                json={"raw": encoded},
                headers=self._get_headers(),
                timeout=15
            )
            data = resp.json()
            if resp.status_code == 200:
                return ExecutionResult(success=True, data={"message_id": data.get("id", "")})
            return ExecutionResult(success=False, error=str(data))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def _reply_email(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            thread_id = params.get("thread_id") or context.get("thread_id", "")
            body = params.get("body", "Thank you for your email. This is an automated reply.")
            to = params.get("to") or context.get("sender_email", "")
            subject = f"Re: {context.get('email_subject', '')}"
            
            raw = f"To: {to}\r\nSubject: {subject}\r\nIn-Reply-To: {thread_id}\r\nContent-Type: text/html; charset=utf-8\r\n\r\n{body}"
            encoded = base64.urlsafe_b64encode(raw.encode()).decode()
            
            resp = httpx.post(
                f"{self.BASE_URL}/users/me/messages/send",
                json={"raw": encoded, "threadId": thread_id},
                headers=self._get_headers(),
                timeout=15
            )
            data = resp.json()
            if resp.status_code == 200:
                return ExecutionResult(success=True, data={"message_id": data.get("id", "")})
            return ExecutionResult(success=False, error=str(data))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def _add_label(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            email_id = params.get("email_id") or context.get("email_id", "")
            label = params.get("label", "FlowMind")
            resp = httpx.post(
                f"{self.BASE_URL}/users/me/messages/{email_id}/modify",
                json={"addLabelIds": [label]},
                headers=self._get_headers(),
                timeout=15
            )
            if resp.status_code == 200:
                return ExecutionResult(success=True, data={"labeled": True})
            return ExecutionResult(success=False, error="Label failed")
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
