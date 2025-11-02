"""
Unit tests for DictionaryService.
Tests dictionary CRUD operations and admin functionality.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.exceptions import (
    DictionaryNotFoundException,
    DictionaryAlreadyExistsException,
    DictionaryInvalidException
)


@pytest.mark.unit
class TestDictionaryServiceCRUD:
    """Test dictionary CRUD operations."""
    
    def test_get_dictionary_by_id(self, dict_service):
        """Test getting dictionary by ID."""
        result = dict_service.get_dictionary("dict_ro_basic")
        
        assert result["dict_id"] == "dict_ro_basic"
        assert result["name"] == "Romanian Basic"
        assert "words" in result
        assert result["word_count"] > 0
        
    def test_get_dictionary_not_found(self, dict_service):
        """Test getting non-existent dictionary."""
        with pytest.raises(DictionaryNotFoundException):
            dict_service.get_dictionary("dict_nonexistent")
            
    def test_list_dictionaries(self, dict_service):
        """Test listing all dictionaries."""
        result = dict_service.list_dictionaries()
        
        assert isinstance(result, list)
        assert len(result) >= 1
        assert any(d["dict_id"] == "dict_ro_basic" for d in result)
        
    def test_create_dictionary_success(self, dict_service):
        """Test creating a new dictionary."""
        dict_data = {
            "dict_id": "dict_test",
            "name": "Test Dictionary",
            "language": "en",
            "words": ["apple", "banana", "cherry"]
        }
        
        result = dict_service.create_dictionary(dict_data)
        
        assert result["dict_id"] == "dict_test"
        assert result["name"] == "Test Dictionary"
        assert result["word_count"] == 3
        assert "created_at" in result
        
    def test_create_dictionary_duplicate_id(self, dict_service):
        """Test creating dictionary with duplicate ID."""
        dict_data = {
            "dict_id": "dict_ro_basic",
            "name": "Duplicate",
            "language": "ro",
            "words": ["test"]
        }
        
        with pytest.raises(DictionaryAlreadyExistsException):
            dict_service.create_dictionary(dict_data)
            
    def test_create_dictionary_empty_words(self, dict_service):
        """Test creating dictionary with no words."""
        dict_data = {
            "dict_id": "dict_empty",
            "name": "Empty Dictionary",
            "language": "en",
            "words": []
        }
        
        with pytest.raises(DictionaryInvalidException, match="at least one word"):
            dict_service.create_dictionary(dict_data)
            
    def test_update_dictionary_success(self, dict_service):
        """Test updating an existing dictionary."""
        # Create a dictionary first
        dict_data = {
            "dict_id": "dict_update_test",
            "name": "Original Name",
            "language": "en",
            "words": ["word1", "word2"]
        }
        dict_service.create_dictionary(dict_data)
        
        # Update it
        updates = {
            "name": "Updated Name",
            "words": ["word1", "word2", "word3"]
        }
        result = dict_service.update_dictionary("dict_update_test", updates)
        
        assert result["name"] == "Updated Name"
        assert result["word_count"] == 3
        
    def test_update_dictionary_not_found(self, dict_service):
        """Test updating non-existent dictionary."""
        with pytest.raises(DictionaryNotFoundException):
            dict_service.update_dictionary("dict_nonexistent", {"name": "New Name"})
            
    def test_delete_dictionary_success(self, dict_service):
        """Test deleting a dictionary."""
        # Create a dictionary first
        dict_data = {
            "dict_id": "dict_delete_test",
            "name": "To Delete",
            "language": "en",
            "words": ["test"]
        }
        dict_service.create_dictionary(dict_data)
        
        # Delete it
        result = dict_service.delete_dictionary("dict_delete_test")
        assert result is True
        
        # Verify it's deleted
        with pytest.raises(DictionaryNotFoundException):
            dict_service.get_dictionary("dict_delete_test")
            
    def test_delete_dictionary_not_found(self, dict_service):
        """Test deleting non-existent dictionary."""
        with pytest.raises(DictionaryNotFoundException):
            dict_service.delete_dictionary("dict_nonexistent")


@pytest.mark.unit
class TestDictionaryServiceValidation:
    """Test dictionary validation."""
    
    def test_validate_words_format(self, dict_service):
        """Test that dictionary validates word format."""
        dict_data = {
            "dict_id": "dict_invalid_words",
            "name": "Invalid Words",
            "language": "en",
            "words": ["valid", "also-valid", ""]  # Empty string should be invalid
        }
        
        with pytest.raises(DictionaryInvalidException):
            dict_service.create_dictionary(dict_data)
            
    def test_validate_unique_words(self, dict_service):
        """Test that dictionary rejects duplicate words."""
        dict_data = {
            "dict_id": "dict_duplicate_words",
            "name": "Duplicate Words",
            "language": "en",
            "words": ["apple", "banana", "apple"]  # Duplicate "apple"
        }
        
        # Dictionary service should handle duplicates (either reject or deduplicate)
        result = dict_service.create_dictionary(dict_data)
        # Should have only 2 unique words
        assert result["word_count"] == 2
        
    def test_get_dictionary_stats(self, dict_service):
        """Test getting dictionary statistics."""
        # Create dictionary with known properties
        dict_data = {
            "dict_id": "dict_stats_test",
            "name": "Stats Test",
            "language": "en",
            "words": ["short", "medium", "verylongword"]
        }
        dict_service.create_dictionary(dict_data)
        
        result = dict_service.get_dictionary("dict_stats_test")
        
        assert result["word_count"] == 3
        assert "words" in result
