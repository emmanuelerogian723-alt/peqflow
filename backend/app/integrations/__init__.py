from typing import Dict
from .base import BaseIntegration, ExecutionResult
from .paystack import PaystackIntegration
from .whatsapp import WhatsAppIntegration
from .gmail import GmailIntegration
from .slack import SlackIntegration
from .notion import NotionIntegration
from .google_sheets import GoogleSheetsIntegration
from .telegram import TelegramIntegration

INTEGRATION_REGISTRY = {
    "paystack": PaystackIntegration,
    "whatsapp": WhatsAppIntegration,
    "gmail": GmailIntegration,
    "slack": SlackIntegration,
    "notion": NotionIntegration,
    "google_sheets": GoogleSheetsIntegration,
    "telegram": TelegramIntegration,
}

def get_integration(name: str, credentials: Dict[str, str]):
    cls = INTEGRATION_REGISTRY.get(name)
    if cls:
        return cls(credentials)
    return None
