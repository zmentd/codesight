"""Component domain model for representing code components."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class Visibility(Enum):
    """Visibility levels for code components."""
    PUBLIC = "public"
    PRIVATE = "private"
    PROTECTED = "protected"
    PACKAGE_PRIVATE = "package_private"


class ComponentType(Enum):
    """Types of components that can be identified."""
    
    # Java/Spring Components
    SPRING_CONTROLLER = "spring_controller"
    SPRING_SERVICE = "spring_service"
    SPRING_REPOSITORY = "spring_repository"
    SPRING_CONFIGURATION = "spring_configuration"
    SPRING_COMPONENT = "spring_component"
    
    # JPA/Hibernate Components
    JPA_ENTITY = "jpa_entity"
    JPA_REPOSITORY = "jpa_repository"
    HIBERNATE_DAO = "hibernate_dao"
    
    # Struts Components
    STRUTS_ACTION = "struts_action"
    STRUTS_INTERCEPTOR = "struts_interceptor"
    STRUTS_RESULT = "struts_result"
    
    # Generic Components
    CLASS = "class"
    INTERFACE = "interface"
    ENUM = "enum"
    ANNOTATION = "annotation"
    PACKAGE = "package"
    
    # Database Components
    DATABASE_TABLE = "database_table"
    DATABASE_VIEW = "database_view"
    DATABASE_PROCEDURE = "database_procedure"
    
    # Configuration Components
    CONFIGURATION_FILE = "configuration_file"
    PROPERTIES_FILE = "properties_file"
    XML_CONFIGURATION = "xml_configuration"
    
    # Web Components
    JSP_PAGE = "jsp_page"
    JAVASCRIPT_FILE = "javascript_file"
    CSS_FILE = "css_file"
    
    # Build Components
    BUILD_SCRIPT = "build_script"
    MAVEN_POM = "maven_pom"
    ANT_BUILD = "ant_build"
    
    # Unknown/Other
    UNKNOWN = "unknown"


@dataclass
class ComponentMetadata:
    """Metadata associated with a component."""
    
    # Basic information
    creation_date: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    author: Optional[str] = None
    
    # Code metrics
    lines_of_code: int = 0
    cyclomatic_complexity: int = 0
    method_count: int = 0
    field_count: int = 0
    
    # Dependencies
    imports: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    
    # Framework-specific
    annotations: List[str] = field(default_factory=list)
    framework_patterns: List[str] = field(default_factory=list)
    
    # Quality metrics
    test_coverage: Optional[float] = None
    code_smells: List[str] = field(default_factory=list)
    security_issues: List[str] = field(default_factory=list)
    
    # Documentation
    has_javadoc: bool = False
    documentation_quality: Optional[str] = None
    
    # Additional metadata
    custom_attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Component:
    """
    Represents a code component identified during analysis.
    
    A component can be a class, interface, service, controller, entity,
    configuration file, or any other logical unit of code.
    """
    
    # Core identification
    id: str
    name: str
    type: ComponentType
    namespace: Optional[str] = None
    
    # File system information
    file_path: str = ""
    relative_path: str = ""
    package_name: Optional[str] = None
    
    # Component hierarchy
    parent_component: Optional[str] = None
    child_components: List[str] = field(default_factory=list)
    
    # Source code information
    source_code: Optional[str] = None
    ast_representation: Optional[Dict[str, Any]] = None
    
    # Component relationships
    implements: List[str] = field(default_factory=list)
    extends: Optional[str] = None
    uses: List[str] = field(default_factory=list)
    used_by: List[str] = field(default_factory=list)
    
    # Component interface
    public_methods: List[Dict[str, Any]] = field(default_factory=list)
    public_fields: List[Dict[str, Any]] = field(default_factory=list)
    interfaces: List[str] = field(default_factory=list)
    
    # Framework-specific information
    framework_type: Optional[str] = None
    framework_version: Optional[str] = None
    framework_annotations: List[Dict[str, Any]] = field(default_factory=list)
    
    # Configuration
    configuration_properties: Dict[str, Any] = field(default_factory=dict)
    environment_specific: bool = False
    
    # Database-related (for entities, DAOs, etc.)
    database_table: Optional[str] = None
    database_schema: Optional[str] = None
    database_operations: List[str] = field(default_factory=list)
    
    # Web-related (for controllers, pages, etc.)
    url_mappings: List[str] = field(default_factory=list)
    http_methods: List[str] = field(default_factory=list)
    view_mappings: List[str] = field(default_factory=list)
    
    # Metadata
    metadata: ComponentMetadata = field(default_factory=ComponentMetadata)
    
    # Analysis results
    complexity_score: Optional[float] = None
    maintainability_score: Optional[float] = None
    reusability_score: Optional[float] = None
    
    # Vector representation (for similarity analysis)
    embedding: Optional[List[float]] = None
    
    # Additional properties
    tags: Set[str] = field(default_factory=set)
    description: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        """Post-initialization processing."""
        # Generate ID if not provided
        if not self.id:
            self.id = self._generate_id()
        
        # Set relative path if not provided
        if not self.relative_path and self.file_path:
            self.relative_path = self.file_path
    
    def _generate_id(self) -> str:
        """Generate a unique ID for the component."""
        import hashlib

        # Use file path and name to generate ID
        id_source = f"{self.file_path}:{self.name}:{self.type.value}"
        return hashlib.md5(id_source.encode()).hexdigest()[:12]
    
    def add_dependency(self, component_id: str) -> None:
        """Add a dependency to this component."""
        if component_id not in self.uses:
            self.uses.append(component_id)
    
    def add_dependent(self, component_id: str) -> None:
        """Add a dependent to this component."""
        if component_id not in self.used_by:
            self.used_by.append(component_id)
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to this component."""
        self.tags.add(tag)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from this component."""
        self.tags.discard(tag)
    
    def has_tag(self, tag: str) -> bool:
        """Check if component has a specific tag."""
        return tag in self.tags
    
    def get_qualified_name(self) -> str:
        """Get the fully qualified name of the component."""
        if self.namespace:
            return f"{self.namespace}.{self.name}"
        elif self.package_name:
            return f"{self.package_name}.{self.name}"
        else:
            return self.name
    
    def is_framework_component(self) -> bool:
        """Check if this is a framework-specific component."""
        framework_types = {
            ComponentType.SPRING_CONTROLLER,
            ComponentType.SPRING_SERVICE,
            ComponentType.SPRING_REPOSITORY,
            ComponentType.SPRING_CONFIGURATION,
            ComponentType.SPRING_COMPONENT,
            ComponentType.JPA_ENTITY,
            ComponentType.JPA_REPOSITORY,
            ComponentType.HIBERNATE_DAO,
            ComponentType.STRUTS_ACTION,
            ComponentType.STRUTS_INTERCEPTOR,
            ComponentType.STRUTS_RESULT
        }
        return self.type in framework_types
    
    def is_database_related(self) -> bool:
        """Check if this component is database-related."""
        db_types = {
            ComponentType.JPA_ENTITY,
            ComponentType.JPA_REPOSITORY,
            ComponentType.HIBERNATE_DAO,
            ComponentType.DATABASE_TABLE,
            ComponentType.DATABASE_VIEW,
            ComponentType.DATABASE_PROCEDURE
        }
        return self.type in db_types or bool(self.database_table)
    
    def is_web_component(self) -> bool:
        """Check if this is a web-related component."""
        web_types = {
            ComponentType.SPRING_CONTROLLER,
            ComponentType.STRUTS_ACTION,
            ComponentType.JSP_PAGE,
            ComponentType.JAVASCRIPT_FILE,
            ComponentType.CSS_FILE
        }
        return self.type in web_types or bool(self.url_mappings)
    
    def get_api_endpoints(self) -> List[Dict[str, str]]:
        """Get API endpoints exposed by this component."""
        endpoints = []
        
        if self.url_mappings and self.http_methods:
            for mapping in self.url_mappings:
                for method in self.http_methods:
                    endpoints.append({
                        "path": mapping,
                        "method": method,
                        "component": self.get_qualified_name()
                    })
        
        return endpoints
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert component to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "namespace": self.namespace,
            "file_path": self.file_path,
            "relative_path": self.relative_path,
            "package_name": self.package_name,
            "qualified_name": self.get_qualified_name(),
            "parent_component": self.parent_component,
            "child_components": self.child_components,
            "implements": self.implements,
            "extends": self.extends,
            "uses": self.uses,
            "used_by": self.used_by,
            "public_methods": self.public_methods,
            "public_fields": self.public_fields,
            "interfaces": self.interfaces,
            "framework_type": self.framework_type,
            "framework_version": self.framework_version,
            "framework_annotations": self.framework_annotations,
            "configuration_properties": self.configuration_properties,
            "database_table": self.database_table,
            "database_schema": self.database_schema,
            "url_mappings": self.url_mappings,
            "http_methods": self.http_methods,
            "view_mappings": self.view_mappings,
            "complexity_score": self.complexity_score,
            "maintainability_score": self.maintainability_score,
            "reusability_score": self.reusability_score,
            "tags": list(self.tags),
            "description": self.description,
            "metadata": {
                "lines_of_code": self.metadata.lines_of_code,
                "cyclomatic_complexity": self.metadata.cyclomatic_complexity,
                "method_count": self.metadata.method_count,
                "field_count": self.metadata.field_count,
                "annotations": self.metadata.annotations,
                "framework_patterns": self.metadata.framework_patterns,
                "has_javadoc": self.metadata.has_javadoc
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Component":
        """Create component from dictionary representation."""
        # Extract metadata
        metadata_dict = data.get("metadata", {})
        metadata = ComponentMetadata(
            lines_of_code=metadata_dict.get("lines_of_code", 0),
            cyclomatic_complexity=metadata_dict.get("cyclomatic_complexity", 0),
            method_count=metadata_dict.get("method_count", 0),
            field_count=metadata_dict.get("field_count", 0),
            annotations=metadata_dict.get("annotations", []),
            framework_patterns=metadata_dict.get("framework_patterns", []),
            has_javadoc=metadata_dict.get("has_javadoc", False)
        )
        
        # Create component
        component = cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            type=ComponentType(data.get("type", ComponentType.UNKNOWN.value)),
            namespace=data.get("namespace"),
            file_path=data.get("file_path", ""),
            relative_path=data.get("relative_path", ""),
            package_name=data.get("package_name"),
            parent_component=data.get("parent_component"),
            child_components=data.get("child_components", []),
            implements=data.get("implements", []),
            extends=data.get("extends"),
            uses=data.get("uses", []),
            used_by=data.get("used_by", []),
            public_methods=data.get("public_methods", []),
            public_fields=data.get("public_fields", []),
            interfaces=data.get("interfaces", []),
            framework_type=data.get("framework_type"),
            framework_version=data.get("framework_version"),
            framework_annotations=data.get("framework_annotations", []),
            configuration_properties=data.get("configuration_properties", {}),
            database_table=data.get("database_table"),
            database_schema=data.get("database_schema"),
            url_mappings=data.get("url_mappings", []),
            http_methods=data.get("http_methods", []),
            view_mappings=data.get("view_mappings", []),
            complexity_score=data.get("complexity_score"),
            maintainability_score=data.get("maintainability_score"),
            reusability_score=data.get("reusability_score"),
            tags=set(data.get("tags", [])),
            description=data.get("description"),
            metadata=metadata
        )
        
        return component
