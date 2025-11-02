"""Dictionary service: dictionary management for admin."""

from datetime import datetime
from typing import Dict, Any, List, Optional
import random
from ..repositories.dictionary_repository import DictionaryRepository
from ..exceptions import (
    DictionaryNotFoundException,
    DictionaryAlreadyExistsException,
    DictionaryInvalidException,
    DictionaryTooFewWordsException
)


class DictionaryService:
    """Service for dictionary operations."""
    
    def __init__(self, dict_repo: DictionaryRepository):
        self.dict_repo = dict_repo
        
    def get_dictionary(self, dictionary_id: str) -> Dict[str, Any]:
        """Get a dictionary by ID with full details including words."""
        dictionary = self.dict_repo.get_by_id(dictionary_id)
        
        if not dictionary:
            raise DictionaryNotFoundException(dictionary_id)
        
        return {
            "dict_id": dictionary["dictionary_id"],
            "dictionary_id": dictionary["dictionary_id"],
            "name": dictionary["name"],
            "description": dictionary.get("description"),
            "language": dictionary["language"],
            "difficulty": dictionary.get("difficulty", "auto"),
            "words": dictionary["words"],
            "word_count": len(dictionary["words"]),
            "active": dictionary.get("active", True),
            "created_at": dictionary["created_at"]
        }
    
    def list_dictionaries(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """List all dictionaries (without words)."""
        dicts = self.dict_repo.get_all(active_only)
        
        # Return without full word list
        return [
            {
                "dict_id": d["dictionary_id"],
                "dictionary_id": d["dictionary_id"],
                "name": d["name"],
                "description": d.get("description"),
                "language": d["language"],
                "difficulty": d.get("difficulty", "auto"),
                "word_count": len(d["words"]),
                "active": d.get("active", True),
                "created_at": d["created_at"]
            }
            for d in dicts
        ]
        
    def create_dictionary(self, dict_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new dictionary."""
        # Extract fields
        dict_id = dict_data.get("dict_id")
        name = dict_data.get("name")
        words = dict_data.get("words", [])
        description = dict_data.get("description")
        language = dict_data.get("language", "ro")
        difficulty = dict_data.get("difficulty", "auto")
        
        # Validate dict_id
        if not dict_id:
            raise DictionaryInvalidException("Dictionary ID is required")
        
        # Check if already exists
        existing = self.dict_repo.get_by_id(dict_id)
        if existing:
            raise DictionaryAlreadyExistsException(dict_id)
        
        # Validate words
        if not words or len(words) == 0:
            raise DictionaryInvalidException("Dictionary must have at least one word")
        
        # Check for empty strings before cleaning
        if any(not w or not w.strip() for w in words):
            raise DictionaryInvalidException("Dictionary contains invalid words (empty or whitespace)")
            
        # Clean and deduplicate words
        clean_words = list(set([w.strip().lower() for w in words if w.strip()]))
        
        if len(clean_words) == 0:
            raise DictionaryInvalidException("Dictionary must have at least one valid word")
            
        # Create dictionary
        full_dict_data = {
            "dictionary_id": dict_id,
            "name": name,
            "description": description,
            "language": language,
            "difficulty": difficulty,
            "words": clean_words,
            "active": True,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        self.dict_repo.create(full_dict_data)
        
        return {
            "dict_id": dict_id,
            "dictionary_id": dict_id,
            "name": name,
            "description": description,
            "language": language,
            "difficulty": difficulty,
            "word_count": len(clean_words),
            "active": True,
            "created_at": full_dict_data["created_at"]
        }
        
    def update_dictionary(self, dictionary_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update dictionary metadata and/or words."""
        dictionary = self.dict_repo.get_by_id(dictionary_id)
        
        if not dictionary:
            raise DictionaryNotFoundException(dictionary_id)
        
        # If updating words, clean and deduplicate them
        if "words" in updates:
            words = updates["words"]
            if not words or len(words) == 0:
                raise DictionaryInvalidException("Dictionary must have at least one word")
            clean_words = list(set([w.strip().lower() for w in words if w.strip()]))
            if len(clean_words) == 0:
                raise DictionaryInvalidException("Dictionary must have at least one valid word")
            updates["words"] = clean_words
            
        self.dict_repo.update(dictionary_id, updates)
        
        updated = self.dict_repo.get_by_id(dictionary_id)
        
        return {
            "dict_id": updated["dictionary_id"],
            "dictionary_id": updated["dictionary_id"],
            "name": updated["name"],
            "description": updated.get("description"),
            "language": updated["language"],
            "difficulty": updated.get("difficulty", "auto"),
            "word_count": len(updated["words"]),
            "active": updated.get("active", True),
            "created_at": updated["created_at"]
        }
    
    def delete_dictionary(self, dictionary_id: str) -> bool:
        """Delete a dictionary."""
        dictionary = self.dict_repo.get_by_id(dictionary_id)
        
        if not dictionary:
            raise DictionaryNotFoundException(dictionary_id)
        
        return self.dict_repo.delete(dictionary_id)
        
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
