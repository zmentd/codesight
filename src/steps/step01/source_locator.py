"""
Source directory locator for STEP01 - Detects and categorizes source code locations.

This module analyzes directory structures to identify source code directories and their
characteristics, providing structured information about language types, detected languages,
and relative paths for package name determination.
"""

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from config import Config
from domain.source_inventory import SourceInventory, SourceLocation
from utils.logging.logger_factory import LoggerFactory
from utils.path_utils import PathUtils


class SourceLocator:
    """
    Locates and categorizes source code directories within a project.
    
    Analyzes directory structures to detect:
    - Source directories (src/, source/, lib/, etc.)
    - Web content directories (webcontent/, web/, static/, etc.)
    - Root-level source files
    - Language types and patterns
    """
    
    def __init__(self) -> None:
        self.logger = LoggerFactory.get_logger("core")
        self.config = Config.get_instance()
        # Directory patterns that indicate source code locations
        self.src_directory_patterns = {
            'src', 'source', 'sources', 'lib', 'libs', 'main', 
            'app', 'application', 'code', 'java', 'scala', 'kotlin',
            'python', 'py', 'scripts', 'bin'
        }
        
        self.web_directory_patterns = {
            'webcontent', 'web', 'webapp', 'webapps', 'www', 'html',
            'static', 'public', 'assets', 'resources', 'jsp', 'jsps',
            'templates', 'views', 'client', 'frontend', 'ui'
        }
        
        self.config_directory_patterns = {
            'config', 'conf', 'configuration', 'settings', 'properties',
            'etc', 'cfg', 'meta-inf', 'web-inf'
        }
        
        # Language detection patterns
        self.language_patterns = {
            'java': {'.java'},  # Source code only, no compiled artifacts
            'javascript': {'.js', '.jsx', '.ts', '.tsx', '.mjs', '.es6'},
            'python': {'.py', '.pyx', '.pyw'},  # Source code only, no compiled .pyc/.pyo
            'html': {'.html', '.htm'},
            'jsp': {'.jsp', '.jspx', '.jspf', '.tag'},  # Separated TLD files
            'tld': {'.tld'},  # Tag Library Descriptors - separate from JSP
            'css': {'.css', '.scss', '.sass', '.less'},
            'sql': {'.sql', '.ddl', '.dml', '.plsql'},
            'xml': {'.xml', '.xsl', '.xslt'},  # Separated XSD and DTD files
            'xsd': {'.xsd'},  # XML Schema Definitions - separate from XML
            'dtd': {'.dtd'},  # Document Type Definitions - separate from XML
            'properties': {'.properties', '.yml', '.yaml', '.json', '.ini'},
            'shell': {'.sh', '.bash', '.bat', '.cmd', '.ps1'},
            'c_cpp': {'.c', '.cpp', '.cc', '.cxx', '.h', '.hpp'},
            'csharp': {'.cs', '.vb', '.fs'},
            'ruby': {'.rb', '.rake', '.gemspec'},
            'php': {'.php', '.phtml', '.php3', '.php4', '.php5'},
            'go': {'.go'},
            'rust': {'.rs'},
            'kotlin': {'.kt', '.kts'},
            'scala': {'.scala', '.sc'}
        }
    
    def locate_source_directories(self, root_path: Optional[str] = None, exclude_patterns: Optional[List[str]] = None) -> SourceInventory:
        """
        Locate and categorize all source directories within the project.
        
        Args:
            root_path: Root project directory path
            exclude_patterns: Optional list of exclude patterns. If None, will use config.
            
        Returns:
            SourceInventory object containing all discovered source locations
        """
        # Use provided root_path or fall back to config
        if root_path is None:
            root_path = self.config.project.source_path
        
        # Use provided exclude_patterns or fall back to config
        if exclude_patterns is None:
            exclude_patterns = self.config.steps.step01.exclude_patterns
            
        self.logger.debug("Locating source directories in: %s", root_path)
        
        if not os.path.exists(root_path):
            raise ValueError(f"Root path does not exist: {root_path}")
        
        # Analyze directory structure to find source root directories
        source_dir_data = self._analyze_directory_structure(root_path, exclude_patterns)
        
        # Create SourceLocation objects from the analyzed data
        source_locations = []
        for dir_info in source_dir_data:
            source_location = SourceLocation(
                relative_path=dir_info['relative_path'],
                directory_name=dir_info['directory_name'],
                language_type=dir_info['language_type'],
                primary_language=dir_info['primary_language'],
                languages_detected=set(dir_info['languages_detected']),
                file_counts_by_language=dir_info['file_counts_by_language'],
                subdomains=[]  # Will be populated by directory scanner
            )
            source_locations.append(source_location)
        
        # Create SourceInventory object
        source_inventory = SourceInventory(
            root_path=PathUtils.normalize_path(root_path),
            source_locations=source_locations
        )
        
        self.logger.debug("Found %s source directories", len(source_locations))
        
        # Auto-save results to project output directory
        self._auto_save_results(source_inventory)
        
        return source_inventory
    
    def _analyze_directory_structure(self, root_path: str, exclude_patterns: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Find source root directories - both traditional and functional organization patterns."""
        source_directories = []
        
        # Get exclude patterns from parameter or configuration
        if exclude_patterns is None:
            try:
                config = Config.get_instance()
                exclude_patterns = config.steps.step01.exclude_patterns
            except (AttributeError, ImportError) as e:
                self.logger.warning("Could not get exclude patterns from config: %s, using defaults", e)
                exclude_patterns = [
                    "**/target/**", "**/build/**", "**/test/**", 
                    "**/node_modules/**", "**/.git/**", "**/bin/**", "**/dist/**"
                ]

        # First, find functional source roots (database, infrastructure, etc.)
        functional_sources = self._find_functional_source_roots(root_path, exclude_patterns)
        source_directories.extend(functional_sources)

        # Create set of paths already found as functional sources to avoid duplicates
        functional_paths = {source['relative_path'] for source in functional_sources}

        # Then find traditional source roots
        for root, dirs, files in os.walk(root_path):
            # Skip excluded directories
            relative_root = os.path.relpath(root, root_path)
            if self._should_exclude_directory(relative_root, exclude_patterns):
                dirs.clear()  # Don't descend into excluded directories
                continue

            # Skip if already found as functional source
            if PathUtils.normalize_path(relative_root) in functional_paths:
                dirs.clear()  # Don't process subdirectories of functional sources
                continue

            dir_name = os.path.basename(root).lower()
            
            # Check if this is a traditional source root directory
            if self._is_traditional_source_root_directory(dir_name, relative_root, files, dirs):
                # Count all files recursively in this source root
                total_files = []
                for subroot, subdirs, subfiles in os.walk(root):
                    # Skip excluded subdirectories
                    subrel = os.path.relpath(subroot, root_path)
                    if not self._should_exclude_directory(subrel, exclude_patterns):
                        total_files.extend(subfiles)
                
                # Analyze all files for languages
                languages_detected = self._detect_languages_in_files(total_files)
                file_counts_by_language = self._count_files_by_language(total_files)
                
                # Only include if we found recognized languages and sufficient files
                if languages_detected and len(total_files) >= 1:
                    primary_language = self._get_primary_language(file_counts_by_language)
                    dir_info = {
                        'directory_path': root,
                        'relative_path': PathUtils.normalize_path(relative_root),
                        'directory_name': os.path.basename(root),
                        'language_type': self._determine_source_root_type(dir_name, relative_root, languages_detected),
                        'languages_detected': sorted(list(languages_detected)),
                        'file_counts_by_language': file_counts_by_language,
                        'primary_language': primary_language,
                        'is_source_root': True
                    }
                    source_directories.append(dir_info)
                    
                    # Skip descending into subdirectories of this source root
                    # to avoid duplicate entries for package subdirectories
                    dirs.clear()
        
        return source_directories
    
    def _detect_languages_in_files(self, files: List[str]) -> Set[str]:
        """Detect programming languages based on file extensions."""
        detected_languages = set()
        
        for file in files:
            file_ext = Path(file).suffix.lower()
            for language, extensions in self.language_patterns.items():
                if file_ext in extensions:
                    detected_languages.add(language)
        
        return detected_languages
    
    def _count_files_by_language(self, files: List[str]) -> Dict[str, int]:
        """Count files by programming language based on file extensions."""
        file_counts: Dict[str, int] = {}
        
        for file in files:
            file_ext = Path(file).suffix.lower()
            for language, extensions in self.language_patterns.items():
                if file_ext in extensions:
                    file_counts[language] = file_counts.get(language, 0) + 1
        
        return file_counts
    
    def _get_primary_language(self, file_counts_by_language: Dict[str, int]) -> str:
        """Determine the primary language based on file counts."""
        if not file_counts_by_language:
            return "unknown"
        
        # Return the language with the most files
        return max(file_counts_by_language.items(), key=lambda x: x[1])[0]
    
    def _is_traditional_source_root_directory(self, dir_name: str, relative_path: str, files: List[str], dirs: List[str]) -> bool:
        """Check if a directory is a traditional source root directory (src/, webapp/, etc.)."""
        path_parts = relative_path.lower().split(os.sep)
        
        # Primary source root indicators
        if dir_name in {'src', 'source', 'sources', 'main'}:
            return True
            
        # Web content roots
        if dir_name in {'webcontent', 'web', 'webapp', 'webapps', 'www'}:
            return True
            
        # Configuration roots
        if dir_name in {'config', 'conf', 'configuration'}:
            return True
            
        # Check for specific path patterns that indicate source roots
        if any(pattern in relative_path.lower() for pattern in [
            '/src/', '/source/', '/webcontent/', '/web/'
        ]):
            return True
            
        # Additional patterns for source roots
        if any(part in {'src', 'source', 'webcontent'} for part in path_parts):
            return True
            
        return False

    def _find_functional_source_roots(self, root_path: str, exclude_patterns: List[str]) -> List[Dict[str, Any]]:
        """
        Find source roots organized by function rather than traditional src/ patterns.
        
        Handles languages/technologies that organize by purpose:
        - SQL: storedProcs, functions, triggers, tables, views, indexes
        - Infrastructure: modules, environments, roles  
        - Docs: api, guides, tutorials
        - Scripts: deploy, backup, monitoring
        """
        functional_sources = []
        found_functional_paths = set()  # Track to avoid duplicates
        
        # Define functional organization patterns
        functional_patterns = {
            'sql': {
                'root_indicators': ['db', 'database', 'sql', 'data'],
                'functional_dirs': ['storedprocs', 'functions', 'triggers', 'tables', 'views', 'indexes', 
                                   'ddls', 'scripts', 'procedures', 'interfaces', 'session', 'timekeeper',
                                   'dbtablecreeatescripts', 'dbviewcreatescripts']
            },
            'terraform': {
                'root_indicators': ['infra', 'infrastructure', 'terraform', 'tf'],
                'functional_dirs': ['modules', 'environments', 'providers', 'resources', 'data']
            },
            'ansible': {
                'root_indicators': ['ansible', 'playbooks', 'automation'],
                'functional_dirs': ['playbooks', 'roles', 'inventory', 'group_vars', 'host_vars']
            },
            'kubernetes': {
                'root_indicators': ['k8s', 'kubernetes', 'kube'],
                'functional_dirs': ['deployments', 'services', 'configmaps', 'secrets', 'ingress']
            },
            'docker': {
                'root_indicators': ['docker', 'containers'],
                'functional_dirs': ['dev', 'prod', 'test', 'staging', 'build']
            },
            'shell': {
                'root_indicators': ['scripts', 'bin', 'automation'],
                'functional_dirs': ['deploy', 'backup', 'monitoring', 'admin', 'maintenance']
            }
        }
        
        # Walk through directory structure looking for functional patterns
        for root, dirs, files in os.walk(root_path):
            relative_root = os.path.relpath(root, root_path)
            
            # Skip excluded directories
            if self._should_exclude_directory(relative_root, exclude_patterns):
                dirs.clear()
                continue
                
            # Check if this directory contains files of a functionally-organized language
            if files:
                detected_languages = self._detect_languages_in_files(files)
                
                for language in detected_languages:
                    if language in functional_patterns:
                        pattern = functional_patterns[language]
                        
                        # Check if we're in a functional organization context
                        if self._is_functional_context(relative_root, pattern['root_indicators']):
                            functional_dir = self._find_functional_source_directory(
                                root, relative_root, pattern['functional_dirs'], 
                                language, root_path, exclude_patterns
                            )
                            if functional_dir:
                                # Check for duplicates using normalized path
                                normalized_path = functional_dir['relative_path']
                                if normalized_path not in found_functional_paths:
                                    found_functional_paths.add(normalized_path)
                                    functional_sources.append(functional_dir)
        
        return functional_sources

    def _is_functional_context(self, relative_path: str, root_indicators: List[str]) -> bool:
        """Check if we're in a context that uses functional organization."""
        path_parts = relative_path.lower().split(os.sep)
        return any(indicator in path_parts for indicator in root_indicators)

    def _find_functional_source_directory(self, current_path: str, relative_path: str, 
                                        functional_dirs: List[str], language: str,
                                        root_path: str, exclude_patterns: List[str]) -> Optional[Dict[str, Any]]:
        """Find the appropriate functional source directory level."""
        path_parts = relative_path.split(os.sep)  # Keep original case
        path_parts_lower = [part.lower() for part in path_parts]  # For comparison
        
        # Check if current directory or any parent is a functional directory
        for i, part_lower in enumerate(path_parts_lower):
            if part_lower in functional_dirs:
                # Found a functional directory, use this level as source root
                functional_path = os.sep.join(path_parts[:i+1])  # Use original case
                full_functional_path = os.path.join(root_path, functional_path)
                
                if os.path.exists(full_functional_path):
                    # Count files in this functional directory
                    total_files = []
                    for subroot, subdirs, subfiles in os.walk(full_functional_path):
                        subrel = os.path.relpath(subroot, root_path)
                        if not self._should_exclude_directory(subrel, exclude_patterns):
                            total_files.extend(subfiles)
                    
                    # Get file counts by language for all files
                    file_counts_by_language = self._count_files_by_language(total_files)
                    languages_detected = self._detect_languages_in_files(total_files)
                    
                    # For functional directories, use lower threshold since they're organized by purpose
                    min_files = 1 if language in ['sql', 'terraform', 'ansible'] else 3
                    if len(total_files) >= min_files and language in languages_detected:
                        primary_language = self._get_primary_language(file_counts_by_language)
                        return {
                            'directory_path': full_functional_path,
                            'relative_path': PathUtils.normalize_path(functional_path),
                            'directory_name': path_parts[i],  # Use original case
                            'language_type': 'src_directory',
                            'languages_detected': sorted(list(languages_detected)),
                            'file_counts_by_language': file_counts_by_language,
                            'primary_language': primary_language,
                            'is_source_root': True
                        }
                break
        
        return None

    def _determine_source_root_type(self, dir_name: str, relative_path: str, languages: Set[str]) -> str:
        """Determine the type of source root directory."""
        path_parts = relative_path.lower().split(os.sep)
        
        # Check for src-type directories (including SQL as source code)
        if (dir_name in self.src_directory_patterns or 
                any(part in self.src_directory_patterns for part in path_parts) or
                'sql' in languages):
            return "src_directory"
        
        # Check for web content directories
        if (dir_name in self.web_directory_patterns or
                any(part in self.web_directory_patterns for part in path_parts) or
                'web' in languages or 'css' in languages):
            return "webcontent_directory"
        
        # Check for configuration directories
        if (dir_name in self.config_directory_patterns or
                any(part in self.config_directory_patterns for part in path_parts)):
            return "config_directory"
        
        # Default classification based on content
        if 'java' in languages or 'python' in languages or 'javascript' in languages:
            return "src_directory"
        elif 'web' in languages or 'css' in languages:
            return "webcontent_directory"
        else:
            return "other_source"
    
    def _should_exclude_directory(self, relative_path: str, exclude_patterns: List[str]) -> bool:
        """Check if directory should be excluded based on patterns."""
        for pattern in exclude_patterns:
            # Remove ** from patterns for simple matching
            clean_pattern = pattern.replace('**/', '').replace('/**', '').strip('*')
            if clean_pattern in relative_path:
                return True
        return False
    
    def _auto_save_results(self, source_inventory: SourceInventory) -> None:
        """Auto-save source directory analysis to project output directory."""
        try:
            # Use config's project_output_path to determine save location
            if hasattr(self.config, 'project_output_path') and self.config.project_output_path:
                output_dir = Path(self.config.project_output_path)
                output_file = output_dir / "step01_source_analysis.json"
                
                # Create output directory if it doesn't exist
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Save results using SourceInventory's to_dict method
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(source_inventory.to_dict(), f, indent=2, ensure_ascii=False)
                
                self.logger.debug("Source analysis auto-saved to: %s", output_file)
            else:
                self.logger.warning("No project_output_path configured, skipping auto-save")
                
        except (OSError, IOError, ValueError) as e:
            self.logger.error("Failed to auto-save source analysis: %s", e)
            # Don't raise - auto-save failure shouldn't break the analysis
 
 
 
 
 
 
 
