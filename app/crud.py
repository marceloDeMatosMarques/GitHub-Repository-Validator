import csv
import json
from io import StringIO
from typing import List

from sqlalchemy.orm import Session

from .database import Category, SavedRepository


def create_category(db: Session, name: str, description: str = None) -> Category:
    db_category = Category(name=name, description=description)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


def get_categories(db: Session) -> List[Category]:
    return db.query(Category).all()


def get_category(db: Session, category_id: int) -> Category:
    return db.query(Category).filter(Category.id == category_id).first()


def save_repository(
    db: Session, repo_name: str, category_id: int, validation_data: dict
) -> SavedRepository:
    db_repo = SavedRepository(
        repo_name=repo_name,
        category_id=category_id,
        verdict=validation_data.get("verdict"),
        score=validation_data.get("score"),
        elimination_reason=validation_data.get("elimination_reason"),
        full_data=validation_data,
    )
    db.add(db_repo)
    db.commit()
    db.refresh(db_repo)
    return db_repo


def get_saved_repos(db: Session, category_id: int = None) -> List[SavedRepository]:
    query = db.query(SavedRepository)
    if category_id:
        query = query.filter(SavedRepository.category_id == category_id)
    return query.all()


def get_saved_repo(db: Session, repo_name: str) -> SavedRepository:
    return db.query(SavedRepository).filter(SavedRepository.repo_name == repo_name).first()


def delete_saved_repo(db: Session, repo_id: int) -> bool:
    repo = db.query(SavedRepository).filter(SavedRepository.id == repo_id).first()
    if repo:
        db.delete(repo)
        db.commit()
        return True
    return False


def export_as_json(db: Session, category_id: int = None) -> str:
    repos = get_saved_repos(db, category_id)
    data = []
    for repo in repos:
        data.append({
            "id": repo.id,
            "repo_name": repo.repo_name,
            "category_id": repo.category_id,
            "verdict": repo.verdict,
            "score": repo.score,
            "created_at": repo.created_at.isoformat(),
            "data": repo.full_data,
        })
    return json.dumps(data, indent=2, ensure_ascii=False)


def export_as_csv(db: Session, category_id: int = None) -> str:
    repos = get_saved_repos(db, category_id)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Repository", "Verdict", "Score", "Created At"])
    for repo in repos:
        writer.writerow([
            repo.id,
            repo.repo_name,
            repo.verdict,
            repo.score,
            repo.created_at.isoformat(),
        ])
    return output.getvalue()
