"""Dictionary service: dictionary management for admin."""

from datetime import datetime
from typing import Dict, Any, List, Optional
import random
from ..repositories.dictionary_repository import DictionaryRepository


class DictionaryService:
    """Service for dictionary operations."""
    
    def __init__(self, dict_repo: DictionaryRepository):
        self.dict_repo = dict_repo
        
    def list_dictionaries(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """List all dictionaries (without words)."""
        dicts = self.dict_repo.get_all(active_only)
        
        # Return without full word list
        return [
            {
                "dictionary_id": d["dictionary_id"],
                "name": d["name"],
                "description": d.get("description"),
                "language": d["language"],
                "difficulty": d["difficulty"],
                "word_count": len(d["words"]),
                "active": d["active"],
                "created_at": d["created_at"]
            }
            for d in dicts
        ]
        
    def create_dictionary(
        self,
        name: str,
        words: List[str],
        description: Optional[str] = None,
        language: str = "ro",
        difficulty: str = "auto"
    ) -> Dict[str, Any]:
        """Create a new dictionary."""
        # Validate
        if len(words) < 10:
            raise ValueError("Dictionary must have at least 10 words")
            
        # Clean words
        clean_words = [w.strip().lower() for w in words if w.strip()]
        
        if len(clean_words) < 10:
            raise ValueError("Dictionary must have at least 10 valid words")
            
        # Generate ID
        dict_id = f"dict_{name.lower().replace(' ', '_')}_{len(self.dict_repo.get_all()) + 1}"
        
        dict_data = {
            "dictionary_id": dict_id,
            "name": name,
            "description": description,
            "language": language,
            "difficulty": difficulty,
            "words": clean_words,
            "active": True,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        self.dict_repo.create(dict_data)
        
        return {
            "dictionary_id": dict_id,
            "name": name,
            "description": description,
            "language": language,
            "difficulty": difficulty,
            "word_count": len(clean_words),
            "active": True,
            "created_at": dict_data["created_at"]
        }
        
    def update_dictionary(
        self,
        dictionary_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        active: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Update dictionary metadata (not words)."""
        dictionary = self.dict_repo.get_by_id(dictionary_id)
        
        if not dictionary:
            raise ValueError("Dictionary not found")
            
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        if active is not None:
            updates["active"] = active
            
        self.dict_repo.update(dictionary_id, updates)
        
        updated = self.dict_repo.get_by_id(dictionary_id)
        
        return {
            "dictionary_id": updated["dictionary_id"],
            "name": updated["name"],
            "description": updated.get("description"),
            "language": updated["language"],
            "difficulty": updated["difficulty"],
            "word_count": len(updated["words"]),
            "active": updated["active"],
            "created_at": updated["created_at"]
        }
        
    def get_dictionary_words(
        self,
        dictionary_id: str,
        sample: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get words from a dictionary (with optional sampling)."""
        dictionary = self.dict_repo.get_by_id(dictionary_id)
        
        if not dictionary:
            raise ValueError("Dictionary not found")
            
        words = dictionary["words"]
        
        if sample and sample < len(words):
            words = random.sample(words, sample)
            
        return {
            "dictionary_id": dictionary_id,
            "name": dictionary["name"],
            "total_words": len(dictionary["words"]),
            "returned_words": len(words),
            "words": words
        }
