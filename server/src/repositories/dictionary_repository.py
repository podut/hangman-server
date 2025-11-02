"""Dictionary repository: in-memory dictionary storage."""

from typing import Dict, Optional, List
from datetime import datetime
from pathlib import Path


class DictionaryRepository:
    """Repository for dictionary data management."""
    
    def __init__(self):
        self._dictionaries: Dict[str, dict] = {}
        self._initialize_default_dictionary()
        
    def _initialize_default_dictionary(self):
        """Initialize default Romanian dictionary."""
        dict_path = Path(__file__).parent.parent / "dict_ro_basic.txt"
        if not dict_path.exists():
            dict_path.write_text(
                "student\nprogramare\ncomputer\npython\nserver\nclient\n"
                "aplicatie\ndicționar\nîncercare\nstatistică"
            )
        words = [w.strip().lower() for w in dict_path.read_text(encoding="utf-8").splitlines() if w.strip()]
        
        self._dictionaries["dict_ro_basic"] = {
            "dictionary_id": "dict_ro_basic",
            "name": "Romanian Basic",
            "description": "Default Romanian word dictionary",
            "language": "ro",
            "difficulty": "auto",
            "words": words,
            "active": True,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
    def create(self, dict_data: dict) -> dict:
        """Create a new dictionary."""
        self._dictionaries[dict_data["dictionary_id"]] = dict_data
        return dict_data
        
    def get_by_id(self, dictionary_id: str) -> Optional[dict]:
        """Get dictionary by ID."""
        return self._dictionaries.get(dictionary_id)
        
    def get_all(self, active_only: bool = False) -> List[dict]:
        """Get all dictionaries."""
        dicts = list(self._dictionaries.values())
        if active_only:
            return [d for d in dicts if d.get("active", True)]
        return dicts
        
    def update(self, dictionary_id: str, updates: dict) -> Optional[dict]:
        """Update dictionary data."""
        if dictionary_id in self._dictionaries:
            self._dictionaries[dictionary_id].update(updates)
            return self._dictionaries[dictionary_id]
        return None
        
    def exists(self, dictionary_id: str) -> bool:
        """Check if dictionary exists."""
        return dictionary_id in self._dictionaries
