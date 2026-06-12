import logging
from os import getenv
from typing import Any, List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .validator import GitHubRepoValidator
from .database import init_db, get_db
from .validators import validate_github_repo, validate_category_name
from . import crud
from .models import CategoryCreate, SaveRepoRequest

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(title="GitHub Repository Validator")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

validator = GitHubRepoValidator(token=getenv("GITHUB_TOKEN"))

@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Iniciando aplicação e criando banco de dados...")
    init_db()
    logger.info("Banco de dados inicializado com sucesso")

@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info("Encerrando aplicação...")
    await validator.close()
    logger.info("Aplicação encerrada")

@app.get("/", response_class=HTMLResponse)
async def read_index() -> Any:
    with open("app/static/index.html", encoding="utf-8") as html_file:
        return html_file.read()

@app.get("/validate")
async def validate(repo: str = Query(..., description="Repositório GitHub no formato owner/repo")) -> Any:
    logger.info(f"Validando repositório: {repo}")
    try:
        # Validar formato
        owner, name = validate_github_repo(repo)
        validated_repo = f"{owner}/{name}"
        
        result = await validator.validate(validated_repo)
        logger.info(f"Repositório {validated_repo} validado com sucesso: {result['verdict']}")
        return result
    except HTTPException as exc:
        logger.warning(f"Erro HTTP ao validar {repo}: {exc.status_code} - {exc.detail}")
        raise
    except ValueError as exc:
        logger.warning(f"Erro de validação para {repo}: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(f"Erro inesperado ao validar {repo}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao avaliar o repositório: {exc}")

# ===== ENDPOINTS DE CATEGORIAS =====

@app.get("/categories")
async def list_categories(db: Session = Depends(get_db)) -> Any:
    categories = crud.get_categories(db)
    return [{"id": c.id, "name": c.name, "description": c.description} for c in categories]

@app.post("/categories")
async def create_category(data: CategoryCreate, db: Session = Depends(get_db)) -> Any:
    logger.info(f"Criando categoria: {data.name}")
    try:
        # Validar nome
        validated_name = validate_category_name(data.name)
        
        existing = db.query(crud.Category).filter(crud.Category.name == validated_name).first()
        if existing:
            logger.warning(f"Categoria já existe: {validated_name}")
            raise HTTPException(status_code=400, detail="Categoria já existe")
        category = crud.create_category(db, validated_name, data.description)
        logger.info(f"Categoria criada com sucesso: {validated_name} (ID: {category.id})")
        return {"id": category.id, "name": category.name, "description": category.description}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Erro ao criar categoria: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao criar categoria: {exc}")

# ===== ENDPOINTS DE REPOSITÓRIOS SALVOS =====

@app.post("/save-repo")
async def save_repo(data: SaveRepoRequest, db: Session = Depends(get_db)) -> Any:
    logger.info(f"Salvando repositório: {data.repo_name} na categoria ID {data.category_id}")
    existing = crud.get_saved_repo(db, data.repo_name)
    if existing:
        logger.warning(f"Repositório já foi salvo: {data.repo_name}")
        raise HTTPException(status_code=400, detail="Repositório já foi salvo")
    
    category = crud.get_category(db, data.category_id)
    if not category:
        logger.error(f"Categoria não encontrada: ID {data.category_id}")
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    saved = crud.save_repository(db, data.repo_name, data.category_id, data.validation_data)
    logger.info(f"Repositório salvo com sucesso: {data.repo_name} (ID: {saved.id})")
    return {
        "id": saved.id,
        "repo_name": saved.repo_name,
        "category_id": saved.category_id,
        "verdict": saved.verdict,
        "score": saved.score,
    }

@app.get("/saved-repos")
async def list_saved_repos(category_id: int = None, db: Session = Depends(get_db)) -> Any:
    repos = crud.get_saved_repos(db, category_id)
    result = []
    for repo in repos:
        result.append({
            "id": repo.id,
            "repo_name": repo.repo_name,
            "category_id": repo.category_id,
            "verdict": repo.verdict,
            "score": repo.score,
            "created_at": repo.created_at.isoformat(),
        })
    return result

@app.delete("/saved-repos/{repo_id}")
async def delete_repo(repo_id: int, db: Session = Depends(get_db)) -> Any:
    if crud.delete_saved_repo(db, repo_id):
        return {"message": "Repositório removido"}
    raise HTTPException(status_code=404, detail="Repositório não encontrado")

# ===== COMPARAÇÃO =====

@app.get("/compare")
async def compare_repos(repo_ids: List[int] = Query(...), db: Session = Depends(get_db)) -> Any:
    if len(repo_ids) < 2:
        raise HTTPException(status_code=400, detail="Selecione pelo menos 2 repositórios")
    if len(repo_ids) > 5:
        raise HTTPException(status_code=400, detail="Máximo 5 repositórios para comparar")
    
    repos = []
    for repo_id in repo_ids:
        repo = db.query(crud.SavedRepository).filter(crud.SavedRepository.id == repo_id).first()
        if not repo:
            raise HTTPException(status_code=404, detail=f"Repositório {repo_id} não encontrado")
        repos.append(repo)
    
    comparison = {
        "repositories": [
            {
                "id": r.id,
                "name": r.repo_name,
                "verdict": r.verdict,
                "score": r.score,
                "details": r.full_data.get("details", {}),
            }
            for r in repos
        ]
    }
    return comparison

# ===== EXPORTAÇÃO =====

@app.get("/export/json")
async def export_json(category_id: int = None, db: Session = Depends(get_db)) -> Any:
    json_str = crud.export_as_json(db, category_id)
    return PlainTextResponse(json_str, media_type="application/json")

@app.get("/export/csv")
async def export_csv(category_id: int = None, db: Session = Depends(get_db)) -> Any:
    csv_str = crud.export_as_csv(db, category_id)
    return PlainTextResponse(csv_str, media_type="text/csv")
