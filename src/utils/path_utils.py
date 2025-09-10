"""Path normalization and validation utilities for CodeSight."""

import os
from pathlib import Path, PurePosixPath
from typing import Optional


class PathUtils:
    """
    Path normalization and validation utilities responsible for:
    - Unix-style path normalization
    - Relative path conversion
    - Path validation
    - Cross-platform path handling
    """
    
    @staticmethod
    def normalize_path(path: str) -> str:
        """
        Normalize path to Unix-style forward slashes.
        
        Args:
            path: Path to normalize
            
        Returns:
            Normalized path with forward slashes
        """
        # First replace all backslashes with forward slashes
        normalized = path.replace('\\', '/')
        # Then use PurePosixPath to ensure proper POSIX format
        return PurePosixPath(normalized).as_posix()
    
    @staticmethod
    def to_relative_path(path: str, base_path: str) -> str:
        """
        Convert absolute path to relative path from base.
        
        Args:
            path: Path to convert
            base_path: Base path for relative conversion
            
        Returns:
            Relative path (Unix-style)
        """
        try:
            path_obj = Path(path)
            base_obj = Path(base_path)
            
            # Make paths absolute for proper relative calculation
            if not path_obj.is_absolute():
                path_obj = Path.cwd() / path_obj
            if not base_obj.is_absolute():
                base_obj = Path.cwd() / base_obj
            
            relative_path = path_obj.relative_to(base_obj)
            return relative_path.as_posix()  # FIX: as_posix() always gives Unix paths
            
        except ValueError:
            # If paths are not related, return normalized absolute path
            return PathUtils.normalize_path(path)
    
    @staticmethod
    def join_paths(*paths: str) -> str:
        """
        Join multiple paths with proper separator.
        
        Args:
            *paths: Path components to join
            
        Returns:
            Joined path (Unix-style)
        """
        if not paths:
            return ""
        
        # Use PurePosixPath for consistent forward slash joining
        result = PurePosixPath(paths[0])
        for path in paths[1:]:
            result = result / path
        
        return result.as_posix()
    
    @staticmethod
    def get_parent_path(path: str) -> str:
        """
        Get parent directory path.
        
        Args:
            path: File or directory path
            
        Returns:
            Parent directory path (Unix-style)
        """
        return PathUtils.normalize_path(str(Path(path).parent))
    
    @staticmethod
    def get_filename(path: str) -> str:
        """
        Get filename from path.
        
        Args:
            path: File path
            
        Returns:
            Filename without directory
        """
        return Path(path).name
    
    @staticmethod
    def get_filename_without_extension(path: str) -> str:
        """
        Get filename without extension.
        
        Args:
            path: File path
            
        Returns:
            Filename without extension
        """
        return Path(path).stem
    
    @staticmethod
    def is_absolute_path(path: str) -> bool:
        """
        Check if path is absolute.
        
        Args:
            path: Path to check
            
        Returns:
            True if path is absolute
        """
        return Path(path).is_absolute()
    
    @staticmethod
    def path_exists(path: str) -> bool:
        """
        Check if path exists.
        
        Args:
            path: Path to check
            
        Returns:
            True if path exists
        """
        return Path(path).exists()
    
    @staticmethod
    def is_file(path: str) -> bool:
        """
        Check if path is a file.
        
        Args:
            path: Path to check
            
        Returns:
            True if path is a file
        """
        return Path(path).is_file()
    
    @staticmethod
    def is_directory(path: str) -> bool:
        """
        Check if path is a directory.
        
        Args:
            path: Path to check
            
        Returns:
            True if path is a directory
        """
        return Path(path).is_dir()
    
    @staticmethod
    def make_relative_to_project(path: str, project_root: str) -> str:
        """
        Make path relative to project root with Unix-style separators.
        
        Args:
            path: Path to convert
            project_root: Project root directory
            
        Returns:
            Relative path from project root (Unix-style)
        """
        try:
            abs_path = Path(path).resolve()
            abs_root = Path(project_root).resolve()
            relative = abs_path.relative_to(abs_root)
            return PathUtils.normalize_path(str(relative))
        except ValueError:
            # Path is not under project root
            return PathUtils.normalize_path(path)
