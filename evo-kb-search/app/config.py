from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Postgres: reuse the stack's pgvector instance (service "postgres") ---
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_username: str = "postgres"
    postgres_password: str = ""
    postgres_database: str = "evo_community"

    # --- Embeddings: any OpenAI-compatible /embeddings endpoint ---
    # Default points at OpenAI (text-embedding-3-small, 1536 dim). To run fully
    # local/free, point embed_base_url at an OpenAI-compatible server (e.g.
    # Ollama: http://ollama:11434/v1, model nomic-embed-text) and adjust embed_dim.
    embed_base_url: str = "https://api.openai.com/v1"
    embed_api_key: str = ""
    embed_model: str = "text-embedding-3-small"
    embed_dim: int = 1536
    # Some models (e5 family) expect prefixes on queries vs. documents.
    query_prefix: str = ""
    doc_prefix: str = ""

    # --- Service auth: the X-API-Key the Evo agent's HTTP tool must send ---
    kb_api_key: str = ""

    # --- Chunking ---
    chunk_size: int = 900
    chunk_overlap: int = 150

    @property
    def dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_username}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
        )


settings = Settings()
