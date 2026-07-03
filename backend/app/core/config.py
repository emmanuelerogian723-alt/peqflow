"""
FlowMind Core Configuration
Central settings for the automation engine, integrations, and runtime.
"""
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class IntegrationConfig:
    """Configuration for a single integration."""
    name: str
    display_name: str
    enabled: bool = False
    required_env_vars: List[str] = field(default_factory=list)
    icon: str = ""


@dataclass
class Settings:
    # Core
    APP_NAME: str = "FlowMind"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    SECRET_KEY: str = os.getenv("FLOWMIND_SECRET_KEY", "dev-secret-change-me")
    
    # AI Engine
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    AI_MODEL: str = os.getenv("AI_MODEL", "llama-3.3-70b-versatile")
    
    # Paystack
    PAYSTACK_SECRET_KEY: str = os.getenv("PAYSTACK_SECRET_KEY", "")
    PAYSTACK_PUBLIC_KEY: str = os.getenv("PAYSTACK_PUBLIC_KEY", "")
    
    # WhatsApp
    WHATSAPP_TOKEN: str = os.getenv("WHATSAPP_TOKEN", "")
    WHATSAPP_PHONE_ID: str = os.getenv("WHATSAPP_PHONE_ID", "")
    WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    
    # Gmail
    GMAIL_CLIENT_ID: str = os.getenv("GMAIL_CLIENT_ID", "")
    GMAIL_CLIENT_SECRET: str = os.getenv("GMAIL_CLIENT_SECRET", "")
    GMAIL_REFRESH_TOKEN: str = os.getenv("GMAIL_REFRESH_TOKEN", "")
    
    # Google Sheets
    GOOGLE_SHEETS_CREDENTIALS: str = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "")
    
    # Slack
    SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "")
    
    # Notion
    NOTION_TOKEN: str = os.getenv("NOTION_TOKEN", "")
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # MCP Server
    MCP_SERVER_PORT: int = int(os.getenv("MCP_SERVER_PORT", "8765"))
    MCP_AUTH_TOKEN: str = os.getenv("MCP_AUTH_TOKEN", "flowmind-mcp-auth-dev")
    
    # Runtime
    RUNNER_PORT: int = int(os.getenv("RUNNER_PORT", "8000"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///flowmind.db")
    
    # CORS
    CORS_ORIGINS: List[str] = field(default_factory=lambda: ["*"])


AVAILABLE_INTEGRATIONS: Dict[str, IntegrationConfig] = {
    "paystack": IntegrationConfig(
        name="paystack",
        display_name="Paystack (Payments)",
        required_env_vars=["PAYSTACK_SECRET_KEY"],
        icon="money"
    ),
    "whatsapp": IntegrationConfig(
        name="whatsapp",
        display_name="WhatsApp Business",
        required_env_vars=["WHATSAPP_TOKEN", "WHATSAPP_PHONE_ID"],
        icon="chat"
    ),
    "gmail": IntegrationConfig(
        name="gmail",
        display_name="Gmail",
        required_env_vars=["GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN"],
        icon="email"
    ),
    "google_sheets": IntegrationConfig(
        name="google_sheets",
        display_name="Google Sheets",
        required_env_vars=["GOOGLE_SHEETS_CREDENTIALS"],
        icon="spreadsheet"
    ),
    "slack": IntegrationConfig(
        name="slack",
        display_name="Slack",
        required_env_vars=["SLACK_BOT_TOKEN"],
        icon="bell"
    ),
    "notion": IntegrationConfig(
        name="notion",
        display_name="Notion",
        required_env_vars=["NOTION_TOKEN"],
        icon="note"
    ),
    "telegram": IntegrationConfig(
        name="telegram",
        display_name="Telegram",
        required_env_vars=["TELEGRAM_BOT_TOKEN"],
        icon="plane"
    ),
    "shopify": IntegrationConfig(
        name="shopify",
        display_name="Shopify",
        required_env_vars=["SHOPIFY_SHOP_DOMAIN", "SHOPIFY_ACCESS_TOKEN"],
        icon="cart"
    ),
}


def get_enabled_integrations() -> List[str]:
    """Return list of integrations that have their env vars configured."""
    enabled = []
    for key, config in AVAILABLE_INTEGRATIONS.items():
        if all(os.getenv(var) for var in config.required_env_vars):
            enabled.append(key)
    return enabled


settings = Settings()
