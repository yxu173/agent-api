from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_core.core_schema import FieldValidationInfo
from pydantic_settings import BaseSettings


class ApiSettings(BaseSettings):
    """Api settings that are set using environment variables."""

    title: str = "agent-api"
    version: str = "1.0"

    # Set to False to disable docs at /docs and /redoc
    docs_enabled: bool = True

    # Environment configuration
    environment: str = "development"
    dev_base_url: str = "http://localhost:8000"
    production_url: str = "https://your-domain.com"

    # Cors origin list to allow requests from.
    # This list is set using the set_cors_origin_list validator
    # which uses the runtime_env variable to set the
    # default cors origin list.
    cors_origin_list: Optional[List[str]] = Field(None, validate_default=True)

    @field_validator("cors_origin_list", mode="before")
    def set_cors_origin_list(cls, cors_origin_list, info: FieldValidationInfo):
        valid_cors = cors_origin_list or []

        # Add app.agno.com to cors to allow requests from the Agno playground.
        valid_cors.append("https://app.agno.com")
        # Add localhost to cors to allow requests from the local environment.
        valid_cors.append("http://localhost")
        # Add localhost:3000 to cors to allow requests from local Agent UI.
        valid_cors.append("http://localhost:3000")

        return valid_cors

    def get_base_url(self) -> str:
        """Get the appropriate base URL based on environment."""
        if self.environment.lower() == "production":
            return self.production_url
        else:
            return self.dev_base_url


# Create ApiSettings object
api_settings = ApiSettings()
