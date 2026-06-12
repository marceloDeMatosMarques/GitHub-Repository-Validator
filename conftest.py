"""
Configuração central para testes pytest.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base


@pytest.fixture(scope="session")
def test_db():
    """
    Cria banco de dados SQLite em memória para testes.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_db_session(test_db):
    """
    Cria sessão de banco para cada teste.
    """
    TestingSessionLocal = sessionmaker(bind=test_db)
    session = TestingSessionLocal()
    yield session
    session.close()
