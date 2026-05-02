from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = Field(default="dev", alias="APP_ENV")
    app_name: str = Field(default="EdgeSenseAI Backend", alias="APP_NAME")

    database_url: str = Field(default="postgresql://edgesenseai:edgesenseai@localhost:55532/edgesenseai", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:56390/0", alias="REDIS_URL")
    kafka_bootstrap_servers: str = Field(default="localhost:19093", alias="KAFKA_BOOTSTRAP_SERVERS")

    backend_base_url: str = Field(default="http://localhost:8900", alias="BACKEND_BASE_URL")
    cors_origins_raw: str = Field(default="http://localhost:3900,http://127.0.0.1:3900,http://frontend:3000", alias="CORS_ORIGINS")

    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    bedrock_model_id: str = Field(default="anthropic.claude-3-haiku-20240307-v1:0", alias="BEDROCK_MODEL_ID")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")

    live_trading_enabled: bool = Field(default=False, alias="LIVE_TRADING_ENABLED")
    paper_trading_enabled: bool = Field(default=True, alias="PAPER_TRADING_ENABLED")
    execution_agent_enabled: bool = Field(default=False, alias="EXECUTION_AGENT_ENABLED")
    require_human_approval: bool = Field(default=True, alias="REQUIRE_HUMAN_APPROVAL")
    paper_starting_cash: float = Field(default=100000.0, alias="PAPER_STARTING_CASH")
    max_daily_llm_cost: int = Field(default=10, alias="MAX_DAILY_LLM_COST")
    max_daily_agent_runs: int = Field(default=500, alias="MAX_DAILY_AGENT_RUNS")

    market_data_provider: str = Field(default="mock", alias="MARKET_DATA_PROVIDER")
    market_data_provider_priority_raw: str = Field(default="alpaca,yfinance,mock", alias="MARKET_DATA_PROVIDER_PRIORITY")
    market_data_provider_timeout_seconds: int = Field(default=10, alias="MARKET_DATA_PROVIDER_TIMEOUT_SECONDS")

    alpaca_market_data_enabled: bool = Field(default=False, alias="ALPACA_MARKET_DATA_ENABLED")
    alpaca_api_key: str = Field(default="", alias="ALPACA_API_KEY")
    alpaca_secret_key: str = Field(default="", alias="ALPACA_SECRET_KEY")
    alpaca_base_url: str = Field(default="https://data.alpaca.markets", alias="ALPACA_BASE_URL")

    polygon_api_key: str = Field(default="", alias="POLYGON_API_KEY")
    alpha_vantage_key: str = Field(default="", alias="ALPHA_VANTAGE_KEY")
    iex_cloud_key: str = Field(default="", alias="IEX_CLOUD_KEY")
    fred_api_key: str = Field(default="", alias="FRED_API_KEY")

    news_provider_enabled: bool = Field(default=False, alias="NEWS_PROVIDER_ENABLED")
    news_provider_primary: str = Field(default="none", alias="NEWS_PROVIDER_PRIMARY")
    news_api_key: str = Field(default="", alias="NEWS_API_KEY")
    finnhub_api_key: str = Field(default="", alias="FINNHUB_API_KEY")
    benzinga_api_key: str = Field(default="", alias="BENZINGA_API_KEY")
    news_provider_timeout_seconds: int = Field(default=10, alias="NEWS_PROVIDER_TIMEOUT_SECONDS")

    smtp_server: str = Field(default="", alias="SMTP_SERVER")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str = Field(default="", alias="SMTP_USERNAME")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from_email: str = Field(default="", alias="SMTP_FROM_EMAIL")
    slack_webhook_url: str = Field(default="", alias="SLACK_WEBHOOK_URL")
    notification_email_recipients: str = Field(default="", alias="NOTIFICATION_EMAIL_RECIPIENTS")

    @property
    def cors_origins(self) -> list[str]:
        origins = [item.strip() for item in self.cors_origins_raw.split(",") if item.strip()]
        if self.app_env.lower() in {"dev", "development", "local"}:
            for port in range(45000, 45100):
                origins.append(f"http://127.0.0.1:{port}")
                origins.append(f"http://localhost:{port}")
        return origins

    @property
    def market_data_provider_priority(self) -> list[str]:
        return [item.strip().lower() for item in self.market_data_provider_priority_raw.split(",") if item.strip()]

    @property
    def notification_email_recipients_list(self) -> list[str]:
        return [item.strip() for item in self.notification_email_recipients.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
