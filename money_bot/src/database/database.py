from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Пример строки подключения для PostgreSQL
DATABASE_URL = os.getenv("POSTGRES_URL")

# Создаём engine
engine = create_engine('postgresql+psycopg://' + DATABASE_URL)

# Создаём фабрику сессий
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
