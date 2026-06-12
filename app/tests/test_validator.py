import pytest
from unittest.mock import AsyncMock, patch
from app.validator import GitHubRepoValidator


@pytest.mark.asyncio
async def test_normalize_repo_valid():
    """Testa normalização de repositório válido"""
    validator = GitHubRepoValidator()
    owner, name = validator._normalize_repo("python/cpython")
    assert owner == "python"
    assert name == "cpython"


def test_normalize_repo_invalid_format():
    """Testa rejeição de formato inválido"""
    validator = GitHubRepoValidator()
    with pytest.raises(ValueError, match="Repositório inválido"):
        validator._normalize_repo("invalid")


def test_normalize_repo_case_insensitive():
    """Testa normalização case-insensitive"""
    validator = GitHubRepoValidator()
    owner, name = validator._normalize_repo("Python/CPython")
    assert owner == "python"
    assert name == "cpython"


@pytest.mark.asyncio
async def test_close_client():
    """Testa fechamento correto do cliente HTTP"""
    validator = GitHubRepoValidator()
    await validator.close()
    # Se não lançar exceção, passou


@pytest.mark.asyncio
async def test_get_with_404_error():
    """Testa tratamento de erro 404"""
    from fastapi import HTTPException
    
    validator = GitHubRepoValidator()
    
    with patch.object(validator.client, "get", new_callable=AsyncMock) as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        with pytest.raises(HTTPException) as exc_info:
            await validator._get("/repos/nonexistent/repo")
        
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_with_rate_limit():
    """Testa detecção de rate limit"""
    from fastapi import HTTPException
    
    validator = GitHubRepoValidator()
    
    with patch.object(validator.client, "get", new_callable=AsyncMock) as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"message": "API rate limit exceeded"}
        mock_response.headers = {"X-RateLimit-Remaining": "0"}
        mock_get.return_value = mock_response
        
        with pytest.raises(HTTPException) as exc_info:
            await validator._get("/repos/test/test")
        
        assert exc_info.value.status_code == 429
        assert "rate limit" in exc_info.value.detail.lower()
