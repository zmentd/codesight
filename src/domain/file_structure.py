"""File structure domain model for representing project file hierarchies."""

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class FileType(Enum):
    """Types of files that can be identified."""
    
    # Source code files
    JAVA_SOURCE = "java_source"
    JAVASCRIPT_SOURCE = "javascript_source"
    TYPESCRIPT_SOURCE = "typescript_source"
    PYTHON_SOURCE = "python_source"
    
    # Web files
    HTML_FILE = "html_file"
    CSS_FILE = "css_file"
    JSP_FILE = "jsp_file"
    JSON_FILE = "json_file"
    XML_FILE = "xml_file"
    
    # Configuration files
    PROPERTIES_FILE = "properties_file"
    YAML_FILE = "yaml_file"
    INI_FILE = "ini_file"
    CONFIG_FILE = "config_file"
    
    # Build files
    MAVEN_POM = "maven_pom"
    GRADLE_BUILD = "gradle_build"
    ANT_BUILD = "ant_build"
    PACKAGE_JSON = "package_json"
    
    # Database files
    SQL_FILE = "sql_file"
    DDL_FILE = "ddl_file"
    DML_FILE = "dml_file"
    
    # Documentation
    MARKDOWN_FILE = "markdown_file"
    TEXT_FILE = "text_file"
    README_FILE = "readme_file"
    
    # Resources
    IMAGE_FILE = "image_file"
    FONT_FILE = "font_file"
    RESOURCE_FILE = "resource_file"
    
    # Archives
    JAR_FILE = "jar_file"
    WAR_FILE = "war_file"
    ZIP_FILE = "zip_file"
    
    # Special
    DIRECTORY = "directory"
    UNKNOWN = "unknown"


@dataclass
class FileNode:
    """
    Represents a file or directory node in the file structure tree.
    """
    
    # Basic properties
    name: str
    path: str
    relative_path: str
    file_type: FileType
    
    # File system properties
    is_directory: bool = False
    size_bytes: int = 0
    creation_time: Optional[float] = None
    modification_time: Optional[float] = None
    
    # Hierarchy
    parent: Optional["FileNode"] = None
    children: List["FileNode"] = field(default_factory=list)
    
    # Content analysis
    lines_of_code: int = 0
    encoding: str = "utf-8"
    content_hash: Optional[str] = None
    
    # Language detection
    programming_language: Optional[str] = None
    framework_indicators: List[str] = field(default_factory=list)
    
    # Dependencies
    imports: List[str] = field(default_factory=list)
    includes: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    
    # Metadata
    tags: Set[str] = field(default_factory=set)
    annotations: List[str] = field(default_factory=list)
    
    # Analysis flags
    is_test_file: bool = False
    is_generated: bool = False
    is_configuration: bool = False
    is_resource: bool = False
    
    # Custom attributes
    custom_attributes: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Post-initialization processing."""
        # Determine file type if not set
        if self.file_type == FileType.UNKNOWN:
            self.file_type = self._detect_file_type()
        
        # Set directory flag based on file type
        if self.file_type == FileType.DIRECTORY:
            self.is_directory = True
    
    def _detect_file_type(self) -> FileType:
        """Detect file type based on file extension and name."""
        if os.path.isdir(self.path):
            return FileType.DIRECTORY
        
        # Get file extension
        _, ext = os.path.splitext(self.name.lower())
        
        # Source code files
        if ext == ".java":
            return FileType.JAVA_SOURCE
        elif ext in [".js", ".jsx"]:
            return FileType.JAVASCRIPT_SOURCE
        elif ext in [".ts", ".tsx"]:
            return FileType.TYPESCRIPT_SOURCE
        elif ext == ".py":
            return FileType.PYTHON_SOURCE
        
        # Web files
        elif ext == ".html":
            return FileType.HTML_FILE
        elif ext == ".css":
            return FileType.CSS_FILE
        elif ext == ".jsp":
            return FileType.JSP_FILE
        elif ext == ".json":
            return FileType.JSON_FILE
        elif ext == ".xml":
            return FileType.XML_FILE
        
        # Configuration files
        elif ext == ".properties":
            return FileType.PROPERTIES_FILE
        elif ext in [".yml", ".yaml"]:
            return FileType.YAML_FILE
        elif ext == ".ini":
            return FileType.INI_FILE
        elif ext in [".conf", ".config"]:
            return FileType.CONFIG_FILE
        
        # Build files
        elif self.name.lower() == "pom.xml":
            return FileType.MAVEN_POM
        elif self.name.lower() in ["build.gradle", "build.gradle.kts"]:
            return FileType.GRADLE_BUILD
        elif self.name.lower() == "build.xml":
            return FileType.ANT_BUILD
        elif self.name.lower() == "package.json":
            return FileType.PACKAGE_JSON
        
        # Database files
        elif ext == ".sql":
            return FileType.SQL_FILE
        elif ext == ".ddl":
            return FileType.DDL_FILE
        elif ext == ".dml":
            return FileType.DML_FILE
        
        # Documentation
        elif ext in [".md", ".markdown"]:
            return FileType.MARKDOWN_FILE
        elif ext == ".txt":
            return FileType.TEXT_FILE
        elif self.name.lower().startswith("readme"):
            return FileType.README_FILE
        
        # Resources
        elif ext in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico"]:
            return FileType.IMAGE_FILE
        elif ext in [".ttf", ".otf", ".woff", ".woff2"]:
            return FileType.FONT_FILE
        
        # Archives
        elif ext == ".jar":
            return FileType.JAR_FILE
        elif ext == ".war":
            return FileType.WAR_FILE
        elif ext == ".zip":
            return FileType.ZIP_FILE
        
        # Default
        else:
            return FileType.UNKNOWN
    
    def add_child(self, child: "FileNode") -> None:
        """Add a child node."""
        child.parent = self
        self.children.append(child)
    
    def remove_child(self, child: "FileNode") -> None:
        """Remove a child node."""
        if child in self.children:
            child.parent = None
            self.children.remove(child)
    
    def get_depth(self) -> int:
        """Get the depth of this node in the tree."""
        depth = 0
        current = self.parent
        while current:
            depth += 1
            current = current.parent
        return depth
    
    def get_root(self) -> "FileNode":
        """Get the root node of the tree."""
        current: Optional["FileNode"] = self
        while current and current.parent:
            current = current.parent
        return current or self
    
    def get_path_from_root(self) -> List[str]:
        """Get the path from root to this node."""
        path_parts = []
        current: Optional["FileNode"] = self
        while current:
            path_parts.append(current.name)
            current = current.parent
        return list(reversed(path_parts))
    
    def find_children_by_type(self, file_type: FileType) -> List["FileNode"]:
        """Find all children of a specific file type."""
        result = []
        for child in self.children:
            if child.file_type == file_type:
                result.append(child)
            # Recursively search in subdirectories
            if child.is_directory:
                result.extend(child.find_children_by_type(file_type))
        return result
    
    def find_children_by_extension(self, extension: str) -> List["FileNode"]:
        """Find all children with a specific file extension."""
        result = []
        for child in self.children:
            if child.name.lower().endswith(extension.lower()):
                result.append(child)
            # Recursively search in subdirectories
            if child.is_directory:
                result.extend(child.find_children_by_extension(extension))
        return result
    
    def get_all_files(self) -> List["FileNode"]:
        """Get all file nodes (excluding directories) under this node."""
        files = []
        for child in self.children:
            if not child.is_directory:
                files.append(child)
            else:
                files.extend(child.get_all_files())
        return files
    
    def get_all_directories(self) -> List["FileNode"]:
        """Get all directory nodes under this node."""
        directories = []
        for child in self.children:
            if child.is_directory:
                directories.append(child)
                directories.extend(child.get_all_directories())
        return directories
    
    def is_source_file(self) -> bool:
        """Check if this is a source code file."""
        source_types = {
            FileType.JAVA_SOURCE,
            FileType.JAVASCRIPT_SOURCE,
            FileType.TYPESCRIPT_SOURCE,
            FileType.PYTHON_SOURCE
        }
        return self.file_type in source_types
    
    def is_web_file(self) -> bool:
        """Check if this is a web-related file."""
        web_types = {
            FileType.HTML_FILE,
            FileType.CSS_FILE,
            FileType.JSP_FILE,
            FileType.JAVASCRIPT_SOURCE,
            FileType.TYPESCRIPT_SOURCE
        }
        return self.file_type in web_types
    
    def is_config_file(self) -> bool:
        """Check if this is a configuration file."""
        config_types = {
            FileType.PROPERTIES_FILE,
            FileType.YAML_FILE,
            FileType.INI_FILE,
            FileType.CONFIG_FILE,
            FileType.XML_FILE,
            FileType.JSON_FILE
        }
        return self.file_type in config_types or self.is_configuration
    
    def is_build_file(self) -> bool:
        """Check if this is a build-related file."""
        build_types = {
            FileType.MAVEN_POM,
            FileType.GRADLE_BUILD,
            FileType.ANT_BUILD,
            FileType.PACKAGE_JSON
        }
        return self.file_type in build_types
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert file node to dictionary representation."""
        return {
            "name": self.name,
            "path": self.path,
            "relative_path": self.relative_path,
            "file_type": self.file_type.value,
            "is_directory": self.is_directory,
            "size_bytes": self.size_bytes,
            "lines_of_code": self.lines_of_code,
            "programming_language": self.programming_language,
            "framework_indicators": self.framework_indicators,
            "imports": self.imports,
            "includes": self.includes,
            "references": self.references,
            "tags": list(self.tags),
            "annotations": self.annotations,
            "is_test_file": self.is_test_file,
            "is_generated": self.is_generated,
            "is_configuration": self.is_configuration,
            "is_resource": self.is_resource,
            "children": [child.to_dict() for child in self.children]
        }


@dataclass
class FileStructure:
    """
    Represents the complete file structure of a project.
    """
    
    # Root information
    root_path: str
    project_name: str
    root_node: Optional[FileNode] = None
    
    # Structure metadata
    total_files: int = 0
    total_directories: int = 0
    total_size_bytes: int = 0
    
    # Language statistics
    language_distribution: Dict[str, int] = field(default_factory=dict)
    file_type_distribution: Dict[str, int] = field(default_factory=dict)
    
    # Framework detection
    detected_frameworks: List[str] = field(default_factory=list)
    build_system: Optional[str] = None
    
    # Special directories
    source_directories: List[str] = field(default_factory=list)
    test_directories: List[str] = field(default_factory=list)
    resource_directories: List[str] = field(default_factory=list)
    config_directories: List[str] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        """Post-initialization processing."""
        if not self.root_node:
            self.root_node = FileNode(
                name=self.project_name,
                path=self.root_path,
                relative_path="",
                file_type=FileType.DIRECTORY,
                is_directory=True
            )
    
    def add_file_node(self, file_path: str, parent_path: Optional[str] = None) -> FileNode:
        """Add a file node to the structure."""
        # Calculate relative path
        rel_path = os.path.relpath(file_path, self.root_path)
        
        # Create file node
        file_node = FileNode(
            name=os.path.basename(file_path),
            path=file_path,
            relative_path=rel_path,
            file_type=FileType.UNKNOWN  # Will be detected in __post_init__
        )
        
        # Find parent node
        if parent_path:
            parent_node = self.find_node_by_path(parent_path)
        else:
            # Find parent by path
            parent_dir = os.path.dirname(file_path)
            parent_node = self.find_node_by_path(parent_dir)
        
        if parent_node:
            parent_node.add_child(file_node)
        
        # Update statistics
        if file_node.is_directory:
            self.total_directories += 1
        else:
            self.total_files += 1
        
        return file_node
    
    def find_node_by_path(self, path: str) -> Optional[FileNode]:
        """Find a node by its absolute path."""
        if not self.root_node:
            return None
        
        if path == self.root_path:
            return self.root_node
        
        # Convert to relative path
        try:
            rel_path = os.path.relpath(path, self.root_path)
            return self._find_node_by_relative_path(self.root_node, rel_path)
        except ValueError:
            return None
    
    def _find_node_by_relative_path(self, node: FileNode, rel_path: str) -> Optional[FileNode]:
        """Find a node by relative path starting from given node."""
        if rel_path == "" or rel_path == ".":
            return node
        
        path_parts = rel_path.split(os.sep)
        current_node = node
        
        for part in path_parts:
            if part == "":
                continue
            
            # Find child with matching name
            found_child = None
            for child in current_node.children:
                if child.name == part:
                    found_child = child
                    break
            
            if not found_child:
                return None
            
            current_node = found_child
        
        return current_node
    
    def get_files_by_type(self, file_type: FileType) -> List[FileNode]:
        """Get all files of a specific type."""
        if not self.root_node:
            return []
        
        return self.root_node.find_children_by_type(file_type)
    
    def get_source_files(self) -> List[FileNode]:
        """Get all source code files."""
        source_types = [
            FileType.JAVA_SOURCE,
            FileType.JAVASCRIPT_SOURCE,
            FileType.TYPESCRIPT_SOURCE,
            FileType.PYTHON_SOURCE
        ]
        
        files = []
        for file_type in source_types:
            files.extend(self.get_files_by_type(file_type))
        
        return files
    
    def get_test_files(self) -> List[FileNode]:
        """Get all test files."""
        if not self.root_node:
            return []
        
        test_files = []
        all_files = self.root_node.get_all_files()
        
        for file_node in all_files:
            if file_node.is_test_file or "test" in file_node.relative_path.lower():
                test_files.append(file_node)
        
        return test_files
    
    def get_config_files(self) -> List[FileNode]:
        """Get all configuration files."""
        config_types = [
            FileType.PROPERTIES_FILE,
            FileType.YAML_FILE,
            FileType.INI_FILE,
            FileType.CONFIG_FILE,
            FileType.XML_FILE,
            FileType.JSON_FILE
        ]
        
        files = []
        for file_type in config_types:
            files.extend(self.get_files_by_type(file_type))
        
        return files
    
    def calculate_statistics(self) -> None:
        """Calculate structure statistics."""
        if not self.root_node:
            return
        
        all_files = self.root_node.get_all_files()
        all_dirs = self.root_node.get_all_directories()
        
        self.total_files = len(all_files)
        self.total_directories = len(all_dirs)
        
        # Calculate language distribution
        self.language_distribution = {}
        self.file_type_distribution = {}
        
        for file_node in all_files:
            # Language distribution
            if file_node.programming_language:
                lang = file_node.programming_language
                self.language_distribution[lang] = self.language_distribution.get(lang, 0) + 1
            
            # File type distribution
            file_type = file_node.file_type.value
            self.file_type_distribution[file_type] = self.file_type_distribution.get(file_type, 0) + 1
            
            # Size calculation
            self.total_size_bytes += file_node.size_bytes
    
    def detect_frameworks(self) -> None:
        """Detect frameworks used in the project."""
        self.detected_frameworks = []
        
        # Check for Spring framework
        if self.get_files_by_type(FileType.JAVA_SOURCE):
            # Look for Spring annotations in Java files
            java_files = self.get_files_by_type(FileType.JAVA_SOURCE)
            for java_file in java_files:
                if "spring" in [annotation.lower() for annotation in java_file.annotations]:
                    if "Spring" not in self.detected_frameworks:
                        self.detected_frameworks.append("Spring")
                    break
        
        # Check for Maven
        if self.get_files_by_type(FileType.MAVEN_POM):
            self.build_system = "Maven"
        
        # Check for Gradle
        elif self.get_files_by_type(FileType.GRADLE_BUILD):
            self.build_system = "Gradle"
        
        # Check for Ant
        elif self.get_files_by_type(FileType.ANT_BUILD):
            self.build_system = "Ant"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert file structure to dictionary representation."""
        return {
            "root_path": self.root_path,
            "project_name": self.project_name,
            "total_files": self.total_files,
            "total_directories": self.total_directories,
            "total_size_bytes": self.total_size_bytes,
            "language_distribution": self.language_distribution,
            "file_type_distribution": self.file_type_distribution,
            "detected_frameworks": self.detected_frameworks,
            "build_system": self.build_system,
            "source_directories": self.source_directories,
            "test_directories": self.test_directories,
            "resource_directories": self.resource_directories,
            "config_directories": self.config_directories,
            "structure": self.root_node.to_dict() if self.root_node else None
        }
