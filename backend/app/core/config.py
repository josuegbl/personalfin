from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql://bankfinances:bankfinances@localhost:5432/bankfinances"
    SECRET_KEY: str = "change_me"

    PAYPAL_CLIENT_ID: str = ""
    PAYPAL_CLIENT_SECRET: str = ""
    PAYPAL_MODE: str = "sandbox"

    BBVA_USER: str = ""
    BBVA_PASSWORD: str = ""

    EUROCAJA_USER: str = ""
    EUROCAJA_PASSWORD: str = ""


settings = Settings()
