"""
WhatsApp Business Integration
Handles sending messages, templates, images, and documents via WhatsApp Cloud API.
"""
import httpx
from typing import Dict, Any
from .base import BaseIntegration, ExecutionResult


class WhatsAppIntegration(BaseIntegration):
    name = "whatsapp"
    display_name = "WhatsApp Business"
    BASE_URL = "https://graph.facebook.com/v18.0"
    
    def _get_url(self) -> str:
        phone_id = self.credentials.get("phone_id", "")
        return f"{self.BASE_URL}/{phone_id}/messages"
    
    def _get_headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self.credentials.get('token', '')}",
            "Content-Type": "application/json",
        }
    
    def test_connection(self) -> ExecutionResult:
        if not self.credentials.get("token") or not self.credentials.get("phone_id"):
            return ExecutionResult(success=False, error="Missing WhatsApp credentials")
        return ExecutionResult(success=True, data={"connected": True})
    
    def execute_action(self, operation: str, parameters: Dict, context: Dict) -> ExecutionResult:
        if operation == "message.send":
            return self._send_text(parameters, context)
        elif operation == "message.send_template":
            return self._send_template(parameters, context)
        elif operation == "image.send":
            return self._send_image(parameters, context)
        elif operation == "document.send":
            return self._send_document(parameters, context)
        return ExecutionResult(success=False, error=f"Unknown operation: {operation}")
    
    def _send_text(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            to = params.get("to") or context.get("customer_phone", "")
            # Remove + if present
            if to.startswith("+"):
                to = to[1:]
            
            # Build message — use context data if available
            message = params.get("message", "")
            if not message:
                template = params.get("template", "")
                if template == "receipt":
                    amount = context.get("amount", "N/A")
                    ref = context.get("reference", "N/A")
                    name = context.get("customer_name", "Customer")
                    message = f"Hi {name}! We've received your payment of {amount}. Reference: {ref}. Thank you!"
                elif template == "follow_up":
                    name = context.get("customer_name", "there")
                    message = f"Hi {name}, just following up! Are you happy with your purchase? Let us know if you need anything."
                else:
                    message = context.get("message", "Hello from FlowMind!")
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": message}
            }
            resp = httpx.post(self._get_url(), json=payload, headers=self._get_headers(), timeout=15)
            data = resp.json()
            if resp.status_code == 200:
                return ExecutionResult(success=True, data={"message_id": data.get("messages", [{}])[0].get("id", "")})
            return ExecutionResult(success=False, error=str(data))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def _send_template(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            to = params.get("to") or context.get("customer_phone", "")
            if to.startswith("+"):
                to = to[1:]
            template_name = params.get("template_name", "hello_world")
            language = params.get("language", "en_US")
            components = []
            
            variables = params.get("variables", [])
            if variables:
                body_params = [{"type": "text", "text": str(v)} for v in variables]
                components.append({"type": "body", "parameters": body_params})
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": language},
                    "components": components,
                }
            }
            resp = httpx.post(self._get_url(), json=payload, headers=self._get_headers(), timeout=15)
            data = resp.json()
            if resp.status_code == 200:
                return ExecutionResult(success=True, data={"message_id": data.get("messages", [{}])[0].get("id", "")})
            return ExecutionResult(success=False, error=str(data))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def _send_image(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            to = params.get("to") or context.get("customer_phone", "")
            if to.startswith("+"):
                to = to[1:]
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "image",
                "image": {
                    "link": params.get("image_url", ""),
                    "caption": params.get("caption", ""),
                }
            }
            resp = httpx.post(self._get_url(), json=payload, headers=self._get_headers(), timeout=15)
            data = resp.json()
            if resp.status_code == 200:
                return ExecutionResult(success=True, data={"message_id": data.get("messages", [{}])[0].get("id", "")})
            return ExecutionResult(success=False, error=str(data))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def _send_document(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            to = params.get("to") or context.get("customer_phone", "")
            if to.startswith("+"):
                to = to[1:]
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "document",
                "document": {
                    "link": params.get("document_url", ""),
                    "filename": params.get("filename", "document.pdf"),
                }
            }
            resp = httpx.post(self._get_url(), json=payload, headers=self._get_headers(), timeout=15)
            data = resp.json()
            if resp.status_code == 200:
                return ExecutionResult(success=True, data={"message_id": data.get("messages", [{}])[0].get("id", "")})
            return ExecutionResult(success=False, error=str(data))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
