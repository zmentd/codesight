"""File system operations utilities for CodeSight."""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Generator, Pattern
import fnmatch
import re


class FileUtils:
    """
    File system operations utilities responsible for:
    - File and directory operations
    - File pattern matching
    - Path validation and normalization
    - Safe file operations
    """
    
    @staticmethod
    def ensure_directory(dir_path: str) -> None:
        """
        Ensure directory exists, create if necessary.
        
        Args:
            dir_path: Directory path to ensure
        """
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def list_files_recursively(
        root_path: str, 
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> List[str]:
        """
        List files recursively with pattern filtering.
        
        Args:
            root_path: Root directory to search
            include_patterns: Glob patterns to include
            exclude_patterns: Glob patterns to exclude
            
        Returns:
            List of matching file paths (Unix-style relative paths)
        """
        root = Path(root_path)
        if not root.exists():
            return []
        
        all_files = []
        
        for file_path in root.rglob('*'):
            if file_path.is_file():
                # Convert to Unix-style relative path
                relative_path = file_path.relative_to(root).as_posix()
                
                # Apply include patterns
                if include_patterns:
                    if not any(fnmatch.fnmatch(relative_path, pattern) for pattern in include_patterns):
                        continue
                
                # Apply exclude patterns
                if exclude_patterns:
                    if any(fnmatch.fnmatch(relative_path, pattern) for pattern in exclude_patterns):
                        continue
                
                all_files.append(relative_path)
        
        return sorted(all_files)
    
    @staticmethod
    def read_file_content(file_path: str, encoding: str = 'utf-8') -> str:
        """
        Read file content safely.
        
        Args:
            file_path: Path to file
            encoding: File encoding
            
        Returns:
            File content
            
        Raises:
            FileNotFoundError: If file doesn't exist
            UnicodeDecodeError: If encoding is incorrect
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(path, 'r', encoding=encoding) as f:
            return f.read()
    
    @staticmethod
    def write_file_content(file_path: str, content: str, encoding: str = 'utf-8') -> None:
        """
        Write content to file safely.
        
        Args:
            file_path: Path to file
            content: Content to write
            encoding: File encoding
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding=encoding) as f:
            f.write(content)
    
    @staticmethod
    def get_file_size(file_path: str) -> int:
        """
        Get file size in bytes.
        
        Args:
            file_path: Path to file
            
        Returns:
            File size in bytes
        """
        return Path(file_path).stat().st_size
    
    @staticmethod
    def get_file_extension(file_path: str) -> str:
        """
        Get file extension.
        
        Args:
            file_path: Path to file
            
        Returns:
            File extension (including dot)
        """
        return Path(file_path).suffix.lower()
    
    @staticmethod
    def copy_file(source: str, destination: str) -> None:
        """
        Copy file safely.
        
        Args:
            source: Source file path
            destination: Destination file path
        """
        dest_path = Path(destination)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    
    @staticmethod
    def move_file(source: str, destination: str) -> None:
        """
        Move file safely.
        
        Args:
            source: Source file path
            destination: Destination file path
        """
        dest_path = Path(destination)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(source, destination)
    
    @staticmethod
    def delete_file(file_path: str) -> None:
        """
        Delete file safely.
        
        Args:
            file_path: Path to file to delete
        """
        path = Path(file_path)
        if path.exists():
            path.unlink()
