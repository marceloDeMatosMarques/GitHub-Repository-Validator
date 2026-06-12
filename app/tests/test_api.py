import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, Base, engine


@pytest.fixture(autouse=True)
def setup_test_db():
    """Cria tabelas antes de cada teste e limpa depois"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Cliente de teste FastAPI"""
    return TestClient(app)


def test_read_index(client):
    """Testa GET / retorna HTML"""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


def test_validate_invalid_repo_format(client):
    """Testa validação com formato inválido"""
    response = client.get("/validate?repo=invalid")
    assert response.status_code == 400
    assert "inválido" in response.json()["detail"].lower()


def test_create_category(client):
    """Testa criação de categoria"""
    response = client.post(
        "/categories",
        json={"name": "AI/ML", "description": "Repositórios de Machine Learning"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "AI/ML"
    assert data["id"] > 0


def test_list_categories_empty(client):
    """Testa listagem de categorias vazia"""
    response = client.get("/categories")
    assert response.status_code == 200
    assert response.json() == []


def test_list_categories_with_data(client):
    """Testa listagem de categorias com dados"""
    # Criar categoria
    client.post(
        "/categories",
        json={"name": "UI/UX", "description": "Repositórios de UI"}
    )
    
    # Listar
    response = client.get("/categories")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "UI/UX"


def test_save_repo_without_category(client):
    """Testa salvamento sem categoria válida"""
    response = client.post(
        "/save-repo",
        json={
            "repo_name": "python/cpython",
            "category_id": 999,
            "validation_data": {
                "verdict": "Aprovado",
                "score": 85.5,
                "elimination_reason": None
            }
        }
    )
    assert response.status_code == 404
    assert "não encontrada" in response.json()["detail"].lower()


def test_get_saved_repos_empty(client):
    """Testa listagem de repos salvos vazia"""
    response = client.get("/saved-repos")
    assert response.status_code == 200
    assert response.json() == []


def test_compare_without_repos(client):
    """Testa comparação sem repositórios"""
    response = client.get("/compare?repo_ids=1,2")
    assert response.status_code == 404


def test_export_json_empty(client):
    """Testa exportação JSON vazia"""
    response = client.get("/export/json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"


def test_export_csv_empty(client):
    """Testa exportação CSV vazia"""
    response = client.get("/export/csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]


def test_compare_single_repo(client):
    """Testa comparação com apenas 1 repo (deve falhar)"""
    response = client.get("/compare?repo_ids=1")
    assert response.status_code == 400
    assert "2-5" in response.json()["detail"]
