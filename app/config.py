from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Torqly / El Garagillo"
    app_env: str = "development"
    debug: bool = False
    secret_key: str = "change-this-secret-key"
    access_token_expire_minutes: int = 720
    auth_cookie_name: str = "torqly_access_token"
    timezone: str = "America/Mexico_City"
    base_url: str = Field(
        default="http://127.0.0.1:8000",
        validation_alias=AliasChoices("BASE_URL", "APP_PUBLIC_URL"),
    )
    cors_origins: str = "*"

    database_url: str | None = None
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "password"
    mysql_database: str = "torqly_db"

    bootstrap_admin_on_startup: bool = False
    default_admin_name: str = "Administrador"
    default_admin_phone: str = "6140000000"
    default_admin_email: str | None = None
    default_admin_password: str = "ChangeMe123!"

    meta_whatsapp_access_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("META_WHATSAPP_ACCESS_TOKEN", "WHATSAPP_ACCESS_TOKEN"),
    )
    meta_whatsapp_phone_number_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "META_WHATSAPP_PHONE_NUMBER_ID",
            "WHATSAPP_PHONE_NUMBER_ID",
        ),
    )
    meta_whatsapp_business_account_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "META_WHATSAPP_BUSINESS_ACCOUNT_ID",
            "WHATSAPP_BUSINESS_ACCOUNT_ID",
        ),
    )
    meta_whatsapp_verify_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("META_WHATSAPP_VERIFY_TOKEN", "WHATSAPP_VERIFY_TOKEN"),
    )
    meta_whatsapp_webhook_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "META_WHATSAPP_WEBHOOK_SECRET",
            "WHATSAPP_WEBHOOK_SECRET",
        ),
    )
    meta_whatsapp_api_version: str = Field(
        default="v20.0",
        validation_alias=AliasChoices("META_WHATSAPP_API_VERSION", "WHATSAPP_API_VERSION"),
    )

    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_project_id: str | None = None
    google_redirect_uri: str | None = None
    google_calendar_id: str = "primary"
    google_service_account_file: str | None = None
    google_refresh_token: str | None = None
    google_token_uri: str = "https://oauth2.googleapis.com/token"
    google_calendar_scopes: str = "https://www.googleapis.com/auth/calendar"
    google_calendar_send_updates: str = "all"
    google_sheets_enabled_flag: bool = Field(
        default=False,
        validation_alias=AliasChoices("GOOGLE_SHEETS_ENABLED", "GOOGLE_SHEETS_ENABLED_FLAG"),
    )
    google_sheets_spreadsheet_id: str | None = None
    google_sheets_credentials_file: str | None = None
    google_sheets_scopes: str = "https://www.googleapis.com/auth/spreadsheets"

    clickup_api_token: str | None = None
    clickup_team_id: str | None = None
    clickup_space_id: str | None = None
    clickup_folder_id: str | None = None
    clickup_list_id: str | None = None
    clickup_webhook_secret: str | None = None

    credential_master_key: str | None = None
    default_whatsapp_provider: str = "whatsapp_meta"
    integrations_allow_manual_selection: bool = True

    scheduler_enabled: bool = True
    daily_close_time: str = "20:00"

    privacy_policy_version: str = "1.0"
    google_login_enabled: bool = True

    groq_api_key: str | None = None
    groq_bot_model: str = "llama-3.1-8b-instant"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def whatsapp_enabled(self) -> bool:
        return bool(self.meta_whatsapp_access_token and self.meta_whatsapp_phone_number_id)

    @property
    def app_public_url(self) -> str:
        return self.base_url.rstrip("/")

    @property
    def google_calendar_enabled(self) -> bool:
        has_service_account = bool(
            self.google_service_account_file and Path(self.google_service_account_file).exists()
        )
        has_refresh_flow = bool(
            self.google_client_id
            and self.google_client_secret
            and self.google_refresh_token
        )
        return has_service_account or has_refresh_flow

    @property
    def google_sheets_enabled(self) -> bool:
        if not self.google_sheets_enabled_flag or not self.google_sheets_spreadsheet_id:
            return False
        has_service_account = bool(
            self.google_sheets_credentials_file and Path(self.google_sheets_credentials_file).exists()
        ) or bool(self.google_service_account_file and Path(self.google_service_account_file).exists())
        has_refresh_flow = bool(
            self.google_client_id
            and self.google_client_secret
            and self.google_refresh_token
        )
        return has_service_account or has_refresh_flow

    @property
    def google_calendar_scope_list(self) -> list[str]:
        return [scope.strip() for scope in self.google_calendar_scopes.split(",") if scope.strip()]

    @property
    def google_sheets_scope_list(self) -> list[str]:
        return [scope.strip() for scope in self.google_sheets_scopes.split(",") if scope.strip()]

    @property
    def clickup_enabled(self) -> bool:
        return bool(self.clickup_api_token and self.clickup_list_id)

    @property
    def credential_vault_enabled(self) -> bool:
        return bool(self.credential_master_key)

    def integration_warnings(self) -> list[str]:
        warnings: list[str] = []
        if not self.credential_vault_enabled:
            warnings.append("CREDENTIAL_MASTER_KEY no configurada: el panel de credenciales dinamicas quedara limitado.")
        if not self.google_calendar_enabled:
            warnings.append("Google Calendar sin credenciales validas: se omite sincronizacion de agenda.")
        if self.google_sheets_enabled_flag and not self.google_sheets_enabled:
            warnings.append("Google Sheets activado pero incompleto: revisa spreadsheet y credenciales.")
        if not self.whatsapp_enabled:
            warnings.append("WhatsApp Cloud API sin credenciales: notificaciones deshabilitadas.")
        if not self.clickup_enabled:
            warnings.append("ClickUp sin token/lista configurados: tareas externas deshabilitadas.")
        if "127.0.0.1" in self.app_public_url or "localhost" in self.app_public_url:
            warnings.append("APP_PUBLIC_URL apunta a entorno local: usa ngrok o URL publica para webhooks externos.")
        return warnings


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
