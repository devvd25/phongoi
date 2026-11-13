from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Cấu hình đọc từ biến môi trường hoặc file .env.

    Mặc định chạy được ngay không cần Docker: SQLite, không Elasticsearch,
    Celery chạy đồng bộ (eager). docker-compose.yml bật đủ PostgreSQL, ES, Redis.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Phòng Ơi API"
    # "development" | "production". Production không bao giờ trả liên kết đặt lại mật khẩu qua API.
    app_env: str = "development"
    database_url: str = "sqlite:///./phongoi.db"
    elasticsearch_url: str = ""
    es_index: str = "listings"
    redis_url: str = ""

    jwt_secret: str = "dev-secret-change-me"
    jwt_expire_minutes: int = 60 * 24 * 7
    ingest_token: str = "dev-ingest-token"

    # LLM: "gemini" (mặc định Cloud 0% GPU) | "openai" (Groq/OpenRouter/OpenAI) | "ollama" | "none" (ML CPU + Bộ phân tích luật)
    llm_provider: str = "gemini"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    ollama_timeout: float = 60
    # Hỗ trợ nhập 1 key hoặc nhiều key cách nhau bởi dấu phẩy (key1,key2,key3) để xoay vòng (Multi-Key Rotation)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    openai_api_key: str = ""
    # Mọi dịch vụ có API chuẩn OpenAI chính thức: Groq (https://api.groq.com/openai/v1), OpenAI, OpenRouter...
    openai_base_url: str = "https://api.groq.com/openai/v1"
    openai_model: str = "llama-3.3-70b-versatile"
    llm_cost_per_1k_tokens_vnd: float = 0.0

    # Cấu hình Facebook Group Bot 24/7 (tương thích cả Local lẫn Linux VPS Headless)
    fb_storage_state_path: str = "cookies/fb-auth.json"
    fb_proxy_url: str = ""

    # Email (quên mật khẩu). Chưa cấu hình SMTP thì môi trường phát triển hiển thị thẳng liên kết đặt lại.
    app_url: str = "http://localhost:5173"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "Phòng Ơi <no-reply@phongoi.vn>"

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    crawler_dir: str = "../crawler"
    price_model_path: str = "models/price_model.joblib"

    @property
    def auto_create_schema(self) -> bool:
        """Chỉ tạo schema tự động khi phát triển; production dùng Alembic."""
        return self.app_env != "production"

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.app_env != "production":
            return self
        invalid = {
            "jwt_secret": self.jwt_secret == "dev-secret-change-me" or len(self.jwt_secret) < 32,
            "ingest_token": self.ingest_token == "dev-ingest-token" or len(self.ingest_token) < 32,
        }
        bad = [name for name, is_invalid in invalid.items() if is_invalid]
        if self.jwt_secret == self.ingest_token:
            bad.append("jwt_secret/ingest_token must differ")
        if bad:
            raise ValueError("Cấu hình production không an toàn: " + ", ".join(bad))
        return self


settings = Settings()
