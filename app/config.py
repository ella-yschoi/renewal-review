from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "RR_"}

    llm_enabled: bool = False
    llm_provider: str = "openai"
    data_path: str = "data/renewals.json"


settings = Settings()
