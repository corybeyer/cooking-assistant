from pydantic_settings import BaseSettings
from functools import lru_cache


from urllib.parse import quote_plus


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    db_server: str = "localhost"
    db_name: str = "cookingdb"
    db_user: str = ""
    db_password: str = ""

    # Claude API
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"

    # Azure Speech (for later)
    azure_speech_key: str = ""
    azure_speech_region: str = "centralus"

    # Azure Communication Services (SMS)
    # Option 1: Use Managed Identity (preferred in Azure)
    azure_comm_endpoint: str = ""  # Format: https://<resource-name>.communication.azure.com
    # Option 2: Use connection string (for local development)
    azure_comm_connection_string: str = ""
    # Sender phone number (required for both options)
    azure_comm_sender_number: str = ""  # Format: +1XXXXXXXXXX

    # App base URL (for shareable links in SMS)
    app_base_url: str = ""  # e.g., https://your-app.azurecontainerapps.io

    # Note: Authentication handled by Azure Container Apps Easy Auth (Entra ID)

    @property
    def database_url(self) -> str:
        """Build the SQL Server connection string with properly encoded credentials."""
        # URL-encode password to handle special characters safely
        encoded_password = quote_plus(self.db_password)
        encoded_user = quote_plus(self.db_user)
        return (
            f"mssql+pyodbc://{encoded_user}:{encoded_password}"
            f"@{self.db_server}/{self.db_name}"
            f"?driver=ODBC+Driver+18+for+SQL+Server"
            f"&Encrypt=yes&TrustServerCertificate=no"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
