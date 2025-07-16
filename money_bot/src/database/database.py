from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Пример строки подключения для PostgreSQL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/money_tracker"
)

# Создаём engine
engine = create_engine(DATABASE_URL)

# Создаём фабрику сессий
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
