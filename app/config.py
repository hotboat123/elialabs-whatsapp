"""
Configuration management using Pydantic Settings
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List, Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str
    
    # WhatsApp
    whatsapp_api_token: str
    whatsapp_phone_number_id: str
    whatsapp_business_account_id: str
    whatsapp_verify_token: str
    
    # AI (Groq - FREE!)
    groq_api_key: str
    
    # MCP / OpenAI bridge (optional)
    openai_mcp_url: Optional[str] = None
    openai_mcp_api_key: Optional[str] = None
    openai_mcp_tool_name: str = "openai_chat"
    openai_mcp_route_prefix: str = "/mcp"
    embed_mcp_server: bool = True
    
    # Bot - Business Information (all can be set via env variables)
    bot_name: str = "Asistente Virtual"
    business_name: str = "Mi Tienda"
    business_phone: str = "+1234567890"
    business_email: str = "info@mitienda.com"
    business_website: str = "https://mitienda.com"
    
    # Welcome message (optional, defaults to generic)
    welcome_message: str = ""
    
    # Database Views Configuration (comma-separated list of view names)
    # Leave empty to allow the bot to query every view/schema your PostgreSQL credentials can reach.
    # Example: "v_products,v_orders,v_stock,v_customers"
    db_views_enabled: str = ""
    
    # Server
    port: int = 8000
    host: str = "0.0.0.0"
    environment: str = "development"
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def get_enabled_views(self) -> List[str]:
        """Get list of enabled views"""
        if not self.db_views_enabled:
            return []
        return [v.strip() for v in self.db_views_enabled.split(",") if v.strip()]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


