from pydantic_settings import BaseSettings


class Environ(BaseSettings):
    openai_api_key: str
