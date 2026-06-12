"""
Módulo de validação para inputs e configurações.
"""
import re
from typing import Tuple

from fastapi import HTTPException


def validate_github_repo(repo: str) -> Tuple[str, str]:
    """
    Valida e normaliza repositório GitHub.
    
    Args:
        repo: String no formato owner/repo ou owner/repo-name
    
    Returns:
        Tupla (owner, repo_name) normalizada
    
    Raises:
        HTTPException: Se formato inválido
    """
    if not repo or not isinstance(repo, str):
        raise HTTPException(status_code=400, detail="Repositório inválido: valor vazio ou não é string")
    
    repo = repo.strip()
    
    # Validar comprimento
    if len(repo) > 255:
        raise HTTPException(status_code=400, detail="Repositório inválido: nome muito longo")
    
    # Validar formato owner/repo
    if "/" not in repo:
        raise HTTPException(status_code=400, detail="Repositório inválido: use formato owner/repo")
    
    parts = repo.split("/")
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Repositório inválido: esperado exatamente owner/repo")
    
    owner, name = parts
    
    # Validar owner
    if not owner or len(owner) > 39:
        raise HTTPException(status_code=400, detail="Owner inválido: deve ter 1-39 caracteres")
    
    if not re.match(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$", owner.lower()):
        raise HTTPException(
            status_code=400,
            detail="Owner inválido: deve começar/terminar com letra/número, sem espaços"
        )
    
    # Validar nome
    if not name or len(name) > 255:
        raise HTTPException(status_code=400, detail="Nome do repositório inválido: deve ter 1-255 caracteres")
    
    if not re.match(r"^[a-z0-9._-]+$", name.lower()):
        raise HTTPException(
            status_code=400,
            detail="Nome do repositório inválido: apenas letras, números, ., _ e - permitidos"
        )
    
    return owner.lower(), name.lower()


def validate_category_name(name: str) -> str:
    """
    Valida nome de categoria.
    
    Args:
        name: Nome da categoria
    
    Returns:
        Nome validado
    
    Raises:
        HTTPException: Se inválido
    """
    if not name or not isinstance(name, str):
        raise HTTPException(status_code=400, detail="Nome de categoria inválido: vazio ou não é string")
    
    name = name.strip()
    
    if len(name) < 2 or len(name) > 100:
        raise HTTPException(status_code=400, detail="Nome de categoria deve ter 2-100 caracteres")
    
    if not re.match(r"^[a-zA-Z0-9\s\-/()&.]+$", name):
        raise HTTPException(
            status_code=400,
            detail="Nome de categoria: apenas letras, números, espaços e -/()&. permitidos"
        )
    
    return name


def validate_score(score: float) -> float:
    """
    Valida score de validação.
    
    Args:
        score: Score entre 0-100
    
    Returns:
        Score validado
    
    Raises:
        HTTPException: Se inválido
    """
    try:
        score = float(score)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Score deve ser um número")
    
    if score < 0 or score > 100:
        raise HTTPException(status_code=400, detail="Score deve estar entre 0 e 100")
    
    return score
