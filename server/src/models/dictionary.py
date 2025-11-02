"""Dictionary-related Pydantic models."""

from pydantic import BaseModel
from typing import Optional, List


class DictionaryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    language: str = "ro"
    difficulty: str = "auto"
    words: List[str]


class DictionaryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class DictionaryResponse(BaseModel):
    dictionary_id: str
    name: str
    description: Optional[str] = None
    language: str
    difficulty: str
    word_count: int
    active: bool
    created_at: str
