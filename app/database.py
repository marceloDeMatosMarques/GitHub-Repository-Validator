from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./repos.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SavedRepository(Base):
    __tablename__ = "saved_repositories"

    id = Column(Integer, primary_key=True, index=True)
    repo_name = Column(String, unique=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    verdict = Column(String)
    score = Column(Float)
    elimination_reason = Column(String, nullable=True)
    full_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
