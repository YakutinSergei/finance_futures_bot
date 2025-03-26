from pydantic_settings import BaseSettings
from dataclasses import dataclass
from environs import Env


env = Env()
env.read_env()


class Settings(BaseSettings):
    # DB_HOST: str
    # DB_PORT: int
    # DB_USER: str
    # DB_PASS: str
    # DB_NAME: str

    @property
    def DATADASE_URL_asyncpg(self):
        return f"postgresql+asyncpg://{env('DB_USER')}:{env('DB_PASS')}@{env('DB_HOST')}:{env('DB_PORT')}/{env('DB_NAME')}"


    @property
    def DATADASE_URL_psycopg(self):
        return f"postgresql+psycopg://{env('DB_USER')}:{env('DB_PASS')}@{env('DB_HOST')}:{env('DB_PORT')}/{env('DB_NAME')}"


settings = Settings()



@dataclass
class TgBot:
    token: str  # Токен для доступа к телеграм-


@dataclass
class Config:
    tg_bot: TgBot


def load_config(path: str | None = None) -> Config:
    env = Env()
    env.read_env(path)
    return Config(tg_bot=TgBot(token=env('BOT_TOKEN')))