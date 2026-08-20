from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql://bankfinances:bankfinances@localhost:5432/bankfinances"
    SECRET_KEY: str = "change_me"

    # BBVA — sync automático via Playwright
    BBVA_JGB_USER: str = ""
    BBVA_JGB_PASSWORD: str = ""
    BBVA_ADI_USER: str = ""
    BBVA_ADI_PASSWORD: str = ""


settings = Settings()
