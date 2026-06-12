from typing import Optional, Dict, Any

from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None


class SaveRepoRequest(BaseModel):
    repo_name: str
    category_id: int
    validation_data: Dict[str, Any]
