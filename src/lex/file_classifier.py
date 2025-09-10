"""File type detection and classification."""

import mimetypes
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import Config
from config.exceptions import ConfigurationError
from utils.logging.logger_factory import LoggerFactory


class FileCategory(Enum):
    """Categories of files for analysis."""
    SOURCE_CODE = "source_code"
    CONFIGURATION = "configuration"
    WEB_RESOURCE = "web_resource"
    DATABASE = "database"
    DOCUMENTATION = "documentation"
    BUILD_SCRIPT = "build_script"
    ARCHIVE = "archive"
    BINARY = "binary"
    UNKNOWN = "unknown"


class FileClassifier:
    """
    File type detection and classification for CodeSight analysis.
    
    Provides:
    - File extension-based classification
    - MIME type detection
    - Content-based classification
    - Framework hint detection
    """
    
    def __init__(self, config: Optional[Config] = None) -> None:
        """Initialize file classifier with configuration."""
        try:
            self.config = config if config is not None else Config.get_instance()
        except ConfigurationError as e:
            raise ConfigurationError(f"Failed to initialize file classifier: {e}") from e
        self.logger = LoggerFactory.get_logger(__name__)
        self._initialize_mappings()
    
    def _initialize_mappings(self) -> None:
        """Initialize file type mappings."""
        # Source code extensions
        self.source_extensions = {
            '.java': 'java',
            '.jsp': 'jsp',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.vbs': 'vbscript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.py': 'python',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.vb': 'vb',
            '.php': 'php',
            '.rb': 'ruby',
            '.go': 'go',
            '.rs': 'rust',
            '.kt': 'kotlin',
            '.scala': 'scala'
        }
        
        # Configuration file extensions
        self.config_extensions = {
            '.xml': 'xml',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.properties': 'properties',
            '.ini': 'ini',
            '.conf': 'config',
            '.config': 'config',
            '.toml': 'toml'
        }
        
        # Web resource extensions
        self.web_extensions = {
            '.html': 'html',
            '.htm': 'html',
            '.xhtml': 'xhtml',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.less': 'less'
        }
        
        # Database extensions
        self.database_extensions = {
            '.sql': 'sql',
            '.ddl': 'ddl',
            '.dml': 'dml',
            '.plsql': 'plsql',
            '.psql': 'postgresql'
        }
        
        # Documentation extensions
        self.doc_extensions = {
            '.md': 'markdown',
            '.markdown': 'markdown',
            '.txt': 'text',
            '.rst': 'rst',
            '.adoc': 'asciidoc',
            '.tex': 'latex'
        }
        
        # Build script extensions
        self.build_extensions = {
            '.gradle': 'gradle',
            '.gradle.kts': 'gradle',
            '.sh': 'shell',
            '.bat': 'batch',
            '.ps1': 'powershell',
            '.make': 'makefile',
            '.cmake': 'cmake'
        }
        
        # Archive extensions
        self.archive_extensions = {
            '.jar': 'jar',
            '.war': 'war',
            '.ear': 'ear',
            '.zip': 'zip',
            '.tar': 'tar',
            '.gz': 'gzip',
            '.7z': '7zip',
            '.rar': 'rar'
        }
        
        # Special file names
        self.special_files = {
            'pom.xml': 'maven_pom',
            'build.gradle': 'gradle_build',
            'build.gradle.kts': 'gradle_build',
            'build.xml': 'ant_build',
            'package.json': 'npm_package',
            'composer.json': 'composer',
            'requirements.txt': 'pip_requirements',
            'dockerfile': 'dockerfile',
            'makefile': 'makefile',
            'readme.md': 'readme',
            'readme.txt': 'readme',
            'changelog.md': 'changelog',
            'license': 'license',
            'license.txt': 'license'
        }
    
    def classify_file(self, file_path: str) -> Dict[str, Any]:
        """
        Classify a file and return detailed information.
        
        Args:
            file_path: Path to the file to classify
            
        Returns:
            Dictionary with classification results
        """
        try:
            path = Path(file_path)
            
            # Basic file information
            classification = {
                'file_path': file_path,
                'file_name': path.name,
                'file_extension': path.suffix.lower(),
                'file_size': 0,
                'is_directory': path.is_dir(),
                'exists': path.exists(),
                'language': None,
                'file_type': None,
                'category': FileCategory.UNKNOWN.value,
                'mime_type': None,
                'framework_hints': [],
                'is_text_file': False,
                'encoding': None,
                'confidence': 0.0
            }
            
            if not path.exists():
                return classification
            
            # Get file size
            if not path.is_dir():
                classification['file_size'] = path.stat().st_size
            
            # Directory classification
            if path.is_dir():
                classification['category'] = FileCategory.UNKNOWN.value
                classification['file_type'] = 'directory'
                return classification
            
            # Get MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            classification['mime_type'] = mime_type
            
            # Classify by extension
            ext = path.suffix.lower()
            name_lower = path.name.lower()
            
            # Check special file names first
            if name_lower in self.special_files:
                file_type = self.special_files[name_lower]
                classification['file_type'] = file_type
                classification['category'] = self._get_category_for_type(file_type)
                classification['confidence'] = 1.0
            
            # Source code files
            elif ext in self.source_extensions:
                classification['language'] = self.source_extensions[ext]
                classification['file_type'] = self.source_extensions[ext]
                classification['category'] = FileCategory.SOURCE_CODE.value
                classification['is_text_file'] = True
                classification['confidence'] = 0.9
                
                # Detect framework hints
                classification['framework_hints'] = self._detect_framework_hints(file_path, ext)
            
            # Configuration files
            elif ext in self.config_extensions:
                classification['file_type'] = self.config_extensions[ext]
                classification['category'] = FileCategory.CONFIGURATION.value
                classification['is_text_file'] = True
                classification['confidence'] = 0.9
            
            # Web resources
            elif ext in self.web_extensions:
                classification['file_type'] = self.web_extensions[ext]
                classification['category'] = FileCategory.WEB_RESOURCE.value
                classification['is_text_file'] = True
                classification['confidence'] = 0.9
            
            # Database files
            elif ext in self.database_extensions:
                classification['file_type'] = self.database_extensions[ext]
                classification['category'] = FileCategory.DATABASE.value
                classification['is_text_file'] = True
                classification['confidence'] = 0.9
            
            # Documentation files
            elif ext in self.doc_extensions:
                classification['file_type'] = self.doc_extensions[ext]
                classification['category'] = FileCategory.DOCUMENTATION.value
                classification['is_text_file'] = True
                classification['confidence'] = 0.8
            
            # Build scripts
            elif ext in self.build_extensions:
                classification['file_type'] = self.build_extensions[ext]
                classification['category'] = FileCategory.BUILD_SCRIPT.value
                classification['is_text_file'] = True
                classification['confidence'] = 0.9
            
            # Archives
            elif ext in self.archive_extensions:
                classification['file_type'] = self.archive_extensions[ext]
                classification['category'] = FileCategory.ARCHIVE.value
                classification['is_text_file'] = False
                classification['confidence'] = 0.9
            
            # MIME type fallback
            elif mime_type:
                if mime_type.startswith('text/'):
                    classification['is_text_file'] = True
                    classification['category'] = FileCategory.UNKNOWN.value
                    classification['confidence'] = 0.5
                elif mime_type.startswith('application/'):
                    classification['category'] = FileCategory.BINARY.value
                    classification['confidence'] = 0.5
            
            # Final unknown classification
            else:
                classification['category'] = FileCategory.UNKNOWN.value
                classification['confidence'] = 0.1
            
            return classification
            
        except (OSError, IOError) as e:
            self.logger.error("Failed to classify file %s: %s", file_path, e)
            return {
                'file_path': file_path,
                'error': str(e),
                'category': FileCategory.UNKNOWN.value,
                'confidence': 0.0
            }
        except (ValueError, RuntimeError) as e:
            self.logger.error("Error processing file %s: %s", file_path, e)
            return {
                'file_path': file_path,
                'error': str(e),
                'category': FileCategory.UNKNOWN.value,
                'confidence': 0.0
            }
    
    def _get_category_for_type(self, file_type: str) -> str:
        """Get category for a specific file type."""
        type_category_map = {
            'maven_pom': FileCategory.BUILD_SCRIPT.value,
            'gradle_build': FileCategory.BUILD_SCRIPT.value,
            'ant_build': FileCategory.BUILD_SCRIPT.value,
            'npm_package': FileCategory.BUILD_SCRIPT.value,
            'composer': FileCategory.BUILD_SCRIPT.value,
            'pip_requirements': FileCategory.BUILD_SCRIPT.value,
            'dockerfile': FileCategory.BUILD_SCRIPT.value,
            'makefile': FileCategory.BUILD_SCRIPT.value,
            'readme': FileCategory.DOCUMENTATION.value,
            'changelog': FileCategory.DOCUMENTATION.value,
            'license': FileCategory.DOCUMENTATION.value
        }
        
        return type_category_map.get(file_type, FileCategory.UNKNOWN.value)
    
    def _detect_framework_hints(self, file_path: str, extension: str) -> List[str]:
        """Detect framework hints based on file content and path."""
        hints = []
        
        try:
            path = Path(file_path)
            
            # Path-based hints
            path_parts = path.parts
            
            # Spring framework hints
            if any('spring' in part.lower() for part in path_parts):
                hints.append('spring')
            
            # Struts framework hints
            if any('struts' in part.lower() for part in path_parts):
                hints.append('struts')
            
            # Hibernate hints
            if any('hibernate' in part.lower() for part in path_parts):
                hints.append('hibernate')
            
            # Maven structure hints
            if 'src/main/java' in str(path) or 'src/test/java' in str(path):
                hints.append('maven')
            
            # Web application hints
            if 'WEB-INF' in str(path) or 'webapp' in str(path):
                hints.append('web_application')
            
            # JSP hints
            if extension == '.jsp':
                hints.append('jsp')
                hints.append('web_application')
            
            # Content-based hints (for small files)
            if path.stat().st_size < 1024 * 1024:  # Files smaller than 1MB
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(1000)  # Read first 1000 characters
                        
                        # Spring annotations
                        if any(annotation in content for annotation in 
                              ['@Controller', '@Service', '@Repository', '@Component', '@Autowired']):
                            hints.append('spring')
                        
                        # Hibernate annotations
                        if any(annotation in content for annotation in 
                              ['@Entity', '@Table', '@Column', '@Id', '@GeneratedValue']):
                            hints.append('hibernate')
                            hints.append('jpa')
                        
                        # Struts annotations/imports
                        if any(struts_ref in content for struts_ref in 
                              ['org.apache.struts', 'ActionSupport', 'Action']):
                            hints.append('struts')
                        
                        # JSP tags
                        if extension in ['.jsp', '.jspx'] and any(tag in content for tag in 
                                       ['<%@', '<%=', '${', '<jsp:', '<c:', '<fmt:']):
                            hints.append('jsp')
                            hints.append('jstl')
                
                except (OSError, IOError, UnicodeDecodeError):
                    # Ignore content reading errors
                    pass
            
        except (OSError, IOError) as e:
            self.logger.warning("Failed to detect framework hints for %s: %s", file_path, e)
        
        return list(set(hints))  # Remove duplicates
    
    def is_source_code_file(self, file_path: str) -> bool:
        """Check if file is a source code file."""
        classification = self.classify_file(file_path)
        return classification.get('category') == FileCategory.SOURCE_CODE.value
    
    def is_configuration_file(self, file_path: str) -> bool:
        """Check if file is a configuration file."""
        classification = self.classify_file(file_path)
        return classification.get('category') == FileCategory.CONFIGURATION.value
    
    def is_web_resource(self, file_path: str) -> bool:
        """Check if file is a web resource."""
        classification = self.classify_file(file_path)
        return classification.get('category') == FileCategory.WEB_RESOURCE.value
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported programming languages."""
        return list(set(self.source_extensions.values()))
    
    def classify_directory(self, directory_path: str) -> Dict[str, Any]:
        """
        Classify all files in a directory.
        
        Args:
            directory_path: Path to directory to classify
            
        Returns:
            Dictionary with classification summary
        """
        try:
            path = Path(directory_path)
            
            if not path.exists() or not path.is_dir():
                return {'error': 'Directory does not exist or is not a directory'}
            
            classifications = []
            category_counts: Dict[str, int] = {}
            language_counts: Dict[str, int] = {}
            framework_hints = set()
            
            # Walk through directory
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    classification = self.classify_file(str(file_path))
                    classifications.append(classification)
                    
                    # Count categories
                    category = classification.get('category', 'unknown')
                    category_counts[category] = category_counts.get(category, 0) + 1
                    
                    # Count languages
                    language = classification.get('language')
                    if language:
                        language_counts[language] = language_counts.get(language, 0) + 1
                    
                    # Collect framework hints
                    file_hints = classification.get('framework_hints', [])
                    framework_hints.update(file_hints)
            
            return {
                'directory_path': directory_path,
                'total_files': len(classifications),
                'category_distribution': category_counts,
                'language_distribution': language_counts,
                'framework_hints': list(framework_hints),
                'classifications': classifications
            }
            
        except (OSError, IOError) as e:
            self.logger.error("Failed to classify directory %s: %s", directory_path, e)
            return {'error': str(e)}
