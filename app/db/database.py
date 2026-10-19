from sqlalchemy import create_engine # used to manage the connection with Postgresql 
from sqlalchemy.orm import declarative_base, sessionmaker  # declarative_base : Use to create database table model from python classes.....sessionmaker: Helps in creating session for db operations
from pydantic_settings import BaseSettings # use to load configuration from .env file

class Settings(BaseSettings):
    DATABASE_URL: str

    class Config:
        env_file = ".env"


settings = Settings()

engine = create_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()