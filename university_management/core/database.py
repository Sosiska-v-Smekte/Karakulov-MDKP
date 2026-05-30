from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Создаем файл базы данных в корне проекта
DATABASE_URL = "sqlite:///university_management.db"

# Создаем движок (echo=True будет выводить SQL-запросы в консоль для отладки,
# перед релизом его лучше отключить)
engine = create_engine(DATABASE_URL, echo=False)

# Создаем фабрику сессий для работы с БД
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс, от которого будут наследоваться все наши таблицы
Base = declarative_base()

def get_db():
    """
    Утилита для получения сессии базы данных.
    Гарантирует безопасное закрытие сессии после использования.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Функция для первичного создания всех таблиц в базе данных.
    Вызывается при старте приложения.
    """
    Base.metadata.create_all(bind=engine)