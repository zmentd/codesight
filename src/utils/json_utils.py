"""JSON processing utilities for CodeSight."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class JsonUtils:
    """
    JSON processing utilities responsible for:
    - JSON file loading and saving
    - Schema validation
    - Pretty printing and formatting
    - Error handling for JSON operations
    """
    
    @staticmethod
    def load_json(file_path: str) -> Any:
        """
        Load JSON data from file.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Loaded JSON data
            
        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file contains invalid JSON
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"JSON file not found: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @staticmethod
    def save_json(file_path: str, data: Union[Dict[str, Any], List[Any]], indent: int = 2) -> None:
        """
        Save data to JSON file.
        
        Args:
            file_path: Path to save JSON file
            data: Data to save
            indent: JSON indentation level
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
    
    @staticmethod
    def validate_json_structure(data: Any, required_keys: List[str]) -> bool:
        """
        Validate that JSON data contains required keys.
        
        Args:
            data: JSON data to validate
            required_keys: List of required keys
            
        Returns:
            True if all required keys are present
        """
        if not isinstance(data, dict):
            return False
            
        return all(key in data for key in required_keys)
    
    @staticmethod
    def merge_json_objects(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge two JSON objects recursively.
        
        Args:
            base: Base JSON object
            overlay: Overlay JSON object
            
        Returns:
            Merged JSON object
        """
        result = base.copy()
        
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = JsonUtils.merge_json_objects(result[key], value)
            else:
                result[key] = value
        
        return result
    
    @staticmethod
    def extract_nested_value(data: Dict[str, Any], key_path: str, default: Any = None) -> Any:
        """
        Extract nested value using dot notation.
        
        Args:
            data: JSON data
            key_path: Dot-separated key path (e.g., 'metadata.step_name')
            default: Default value if key not found
            
        Returns:
            Extracted value or default
        """
        keys = key_path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        
        return current
