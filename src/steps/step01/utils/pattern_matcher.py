"""
Pattern matching utility for file classification.
Handles glob-style patterns, regex patterns, and component extraction.
"""

import re
import fnmatch
from typing import Optional, List
from pathlib import Path


class PatternMatcher:
    """Universal pattern matching utility for all file classifiers."""
    
    def matches(self, text: str, pattern: str) -> bool:
        """
        Universal pattern matching - handles glob, regex, etc.
        
        Args:
            text: Text to match against
            pattern: Pattern to match (supports ** for multi-level, * for single level)
            
        Returns:
            True if pattern matches text
        """
        if '**' in pattern:
            return self._regex_match(text, pattern)
        else:
            return fnmatch.fnmatch(text, pattern)
    
    def _regex_match(self, text: str, pattern: str) -> bool:
        """
        Handle complex patterns with ** wildcards.
        Copied from existing _pattern_matches logic.
        """
        # Replace ** with .* for regex matching (matches any characters including dots)
        # Replace single * with [^.]* (matches any characters except dots)
        regex_pattern = pattern.replace('**', '___DOUBLE_STAR___').replace('*', '[^.]*').replace('___DOUBLE_STAR___', '.*')
        return bool(re.match(regex_pattern + '$', text))
    
    def extract_component_from_package_pattern(self, package_name: str, matched_pattern: str) -> str:
        """
        Extract component name from package using matched pattern.
        Copied from existing _extract_component_name logic.
        
        Args:
            package_name: Java package name
            matched_pattern: The pattern that matched
            
        Returns:
            Component name extracted from package
        """
        package_parts = package_name.split('.')
        
        # Parse the pattern to find meaningful parts
        pattern_parts = matched_pattern.replace('**', '').replace('*', '').split('.')
        
        # Find pattern parts that exist in package and extract next component
        for pattern_part in pattern_parts:
            if pattern_part in package_parts:
                part_index = package_parts.index(pattern_part)
                if part_index + 1 < len(package_parts):
                    component_name = package_parts[part_index + 1]
                    return component_name.strip('_')  # Handle _i213srvc -> i213srvc
        
        # Fallback: use the last meaningful part of the package
        if package_parts:
            return package_parts[-1].strip('_')
        
        return 'unknown'
    
    def extract_component_from_path(self, file_path: str, path_parts: List[str]) -> str:
        """
        Extract component name from file path.
        
        Args:
            file_path: File path
            path_parts: Pre-split path parts
            
        Returns:
            Component name extracted from path
        """
        # Skip common directory names and use the most specific one
        meaningful_parts = [p for p in path_parts if p not in ['src', 'main', 'java', 'webapp', 'jsp']]
        if meaningful_parts:
            return meaningful_parts[-1].strip('_')
        
        # Fallback to filename without extension
        return Path(file_path).stem
    
    def extract_architectural_directory_from_pattern(self, pattern: str) -> Optional[str]:
        """
        Extract directory name from architectural pattern like '**/asl/**'.
        
        Args:
            pattern: Glob pattern
            
        Returns:
            Directory name or None
        """
        if '**/' in pattern and '/**' in pattern:
            # Extract the middle part: "**/asl/**" -> "asl"
            parts = pattern.split('/')
            for part in parts:
                if part and part != '**':
                    return part.lower()
        return None
