from enum import Enum

from pydantic_settings import BaseSettings

class Permissions(str, Enum):
    ORDER_ALL_READ = "order.all:read"
    ORDER_ALL_WRITE = "order.all:write"
    ORDER_ALL_DELETE = "order.all:delete"

    ORDER_OWN_READ = "order.own:read"
    ORDER_OWN_WRITE = "order.own:write"

class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"

class Settings(BaseSettings):
    # Database
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_NAME: str = "test_db"
    DB_USER: str = "postgres"
    DB_PASS: str = "testpass"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Application
    APP_NAME: str = "order-service"
    DEBUG: bool = True
    ROOT_PATH: str = ''
    ENVIRONMENT: Environment = Environment.DEVELOPMENT

    # RPC
    RPC_CALCULATOR_URL: str = "localhost:50052"
    RPC_API_URL: str = "localhost:50051"
    RPC_AUTH_URL: str = "localhost:50054"

    @property
    def enable_docs(self) -> bool:
        return self.ENVIRONMENT in [Environment.DEVELOPMENT]

settings = Settings()
