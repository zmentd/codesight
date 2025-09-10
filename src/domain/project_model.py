"""Project domain model for representing complete project information."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from .component import Component, ComponentType
from .file_structure import FileStructure


class ProjectType(Enum):
    """Types of projects that can be analyzed."""
    
    # Java projects
    JAVA_ENTERPRISE = "java_enterprise"
    SPRING_BOOT = "spring_boot"
    SPRING_MVC = "spring_mvc"
    HIBERNATE_PROJECT = "hibernate_project"
    STRUTS_PROJECT = "struts_project"
    
    # Web projects
    WEB_APPLICATION = "web_application"
    REST_API = "rest_api"
    MICROSERVICE = "microservice"
    
    # Database projects
    DATABASE_SCHEMA = "database_schema"
    DATA_ACCESS_LAYER = "data_access_layer"
    
    # Configuration projects
    CONFIGURATION_PROJECT = "configuration_project"
    
    # Mixed/Unknown
    MIXED_PROJECT = "mixed_project"
    LEGACY_PROJECT = "legacy_project"
    UNKNOWN = "unknown"


class TechnologyStack(Enum):
    """Technology stacks that can be detected."""
    
    # Java stacks
    JAVA_EE = "java_ee"
    SPRING_FRAMEWORK = "spring_framework"
    HIBERNATE_JPA = "hibernate_jpa"
    STRUTS_FRAMEWORK = "struts_framework"
    
    # Web technologies
    JSP_SERVLET = "jsp_servlet"
    JAVASCRIPT_FRONTEND = "javascript_frontend"
    REST_SERVICES = "rest_services"
    
    # Database technologies
    JDBC = "jdbc"
    JPA = "jpa"
    HIBERNATE = "hibernate"
    
    # Build tools
    MAVEN = "maven"
    GRADLE = "gradle"
    ANT = "ant"
    
    # Application servers
    TOMCAT = "tomcat"
    JBOSS = "jboss"
    WEBSPHERE = "websphere"
    WEBLOGIC = "weblogic"


@dataclass
class ProjectMetadata:
    """Metadata associated with a project."""
    
    # Basic information
    creation_date: Optional[datetime] = None
    last_analysis_date: Optional[datetime] = None
    analysis_version: str = "1.0"
    
    # Project characteristics
    size_category: str = "medium"  # small, medium, large, enterprise
    complexity_level: str = "moderate"  # low, moderate, high, very_high
    
    # Technical debt indicators
    technical_debt_score: Optional[float] = None
    code_quality_score: Optional[float] = None
    maintainability_index: Optional[float] = None
    
    # Architecture patterns
    architectural_patterns: List[str] = field(default_factory=list)
    design_patterns: List[str] = field(default_factory=list)
    
    # Dependencies
    external_dependencies: List[str] = field(default_factory=list)
    framework_versions: Dict[str, str] = field(default_factory=dict)
    
    # Security and compliance
    security_issues: List[str] = field(default_factory=list)
    compliance_frameworks: List[str] = field(default_factory=list)
    
    # Documentation
    documentation_coverage: Optional[float] = None
    api_documentation_available: bool = False
    
    # Testing
    test_coverage: Optional[float] = None
    test_frameworks: List[str] = field(default_factory=list)
    
    # Performance
    performance_bottlenecks: List[str] = field(default_factory=list)
    scalability_concerns: List[str] = field(default_factory=list)
    
    # Custom metadata
    custom_attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Project:
    """
    Represents a complete software project with all its components,
    file structure, and metadata.
    """
    
    # Core identification
    id: str
    name: str
    project_type: ProjectType
    root_path: str
    
    # Project structure
    file_structure: Optional[FileStructure] = None
    components: List[Component] = field(default_factory=list)
    
    # Technology information
    technology_stacks: List[TechnologyStack] = field(default_factory=list)
    programming_languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    
    # Architecture information
    architecture_type: Optional[str] = None
    deployment_model: Optional[str] = None
    integration_patterns: List[str] = field(default_factory=list)
    
    # Component relationships
    component_dependencies: Dict[str, List[str]] = field(default_factory=dict)
    component_groups: Dict[str, List[str]] = field(default_factory=dict)
    
    # Database information
    database_schemas: List[str] = field(default_factory=list)
    database_tables: List[str] = field(default_factory=list)
    data_access_patterns: List[str] = field(default_factory=list)
    
    # API information
    api_endpoints: List[Dict[str, Any]] = field(default_factory=list)
    service_interfaces: List[Dict[str, Any]] = field(default_factory=list)
    
    # Configuration
    configuration_files: List[str] = field(default_factory=list)
    environment_configs: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    metadata: ProjectMetadata = field(default_factory=ProjectMetadata)
    
    # Analysis results
    analysis_summary: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    
    # Tags and classification
    tags: Set[str] = field(default_factory=set)
    description: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Post-initialization processing."""
        # Generate ID if not provided
        if not self.id:
            self.id = self._generate_id()
        
        # Initialize file structure if not provided
        if not self.file_structure:
            self.file_structure = FileStructure(
                root_path=self.root_path,
                project_name=self.name
            )
    
    def _generate_id(self) -> str:
        """Generate a unique ID for the project."""
        import hashlib

        # Use project name and root path to generate ID
        id_source = f"{self.name}:{self.root_path}"
        return hashlib.md5(id_source.encode()).hexdigest()[:16]
    
    def add_component(self, component: Component) -> None:
        """Add a component to the project."""
        if component not in self.components:
            self.components.append(component)
            
            # Update component relationships
            for dependency in component.uses:
                if dependency not in self.component_dependencies:
                    self.component_dependencies[dependency] = []
                if component.id not in self.component_dependencies[dependency]:
                    self.component_dependencies[dependency].append(component.id)
    
    def remove_component(self, component_id: str) -> bool:
        """Remove a component from the project."""
        component = self.get_component_by_id(component_id)
        if component:
            self.components.remove(component)
            
            # Clean up relationships
            if component_id in self.component_dependencies:
                del self.component_dependencies[component_id]
            
            return True
        return False
    
    def get_component_by_id(self, component_id: str) -> Optional[Component]:
        """Get a component by its ID."""
        for component in self.components:
            if component.id == component_id:
                return component
        return None
    
    def get_components_by_type(self, component_type: ComponentType) -> List[Component]:
        """Get all components of a specific type."""
        return [comp for comp in self.components if comp.type == component_type]
    
    def get_components_by_framework(self, framework: str) -> List[Component]:
        """Get all components related to a specific framework."""
        return [comp for comp in self.components 
                if comp.framework_type and framework.lower() in comp.framework_type.lower()]
    
    def get_web_components(self) -> List[Component]:
        """Get all web-related components."""
        return [comp for comp in self.components if comp.is_web_component()]
    
    def get_database_components(self) -> List[Component]:
        """Get all database-related components."""
        return [comp for comp in self.components if comp.is_database_related()]
    
    def get_configuration_components(self) -> List[Component]:
        """Get all configuration-related components."""
        config_types = {
            ComponentType.CONFIGURATION_FILE,
            ComponentType.PROPERTIES_FILE,
            ComponentType.XML_CONFIGURATION
        }
        return [comp for comp in self.components if comp.type in config_types]
    
    def analyze_architecture(self) -> Dict[str, Any]:
        """Analyze the project architecture."""
        analysis: Dict[str, Any] = {
            "total_components": len(self.components),
            "component_distribution": {},
            "framework_usage": {},
            "dependency_complexity": 0,
            "layer_separation": {},
            "architectural_patterns": []
        }
        
        # Component type distribution
        component_dist = analysis["component_distribution"]
        for component in self.components:
            comp_type = component.type.value
            if isinstance(component_dist, dict):
                component_dist[comp_type] = component_dist.get(comp_type, 0) + 1
        
        # Framework usage
        framework_usage = analysis["framework_usage"]
        for component in self.components:
            if component.framework_type:
                framework = component.framework_type
                if isinstance(framework_usage, dict):
                    framework_usage[framework] = framework_usage.get(framework, 0) + 1
        
        # Dependency complexity
        total_dependencies = sum(len(deps) for deps in self.component_dependencies.values())
        if self.components:
            analysis["dependency_complexity"] = total_dependencies / len(self.components)
        
        # Detect architectural patterns
        patterns = self._detect_architectural_patterns()
        analysis["architectural_patterns"] = patterns
        
        return analysis
    
    def _detect_architectural_patterns(self) -> List[str]:
        """Detect architectural patterns in the project."""
        patterns = []
        
        # Check for MVC pattern
        has_controllers = any(comp.type == ComponentType.SPRING_CONTROLLER 
                            for comp in self.components)
        has_services = any(comp.type == ComponentType.SPRING_SERVICE 
                         for comp in self.components)
        has_repositories = any(comp.type == ComponentType.SPRING_REPOSITORY 
                             for comp in self.components)
        
        if has_controllers and has_services and has_repositories:
            patterns.append("MVC (Model-View-Controller)")
            patterns.append("Layered Architecture")
        
        # Check for Repository pattern
        if has_repositories:
            patterns.append("Repository Pattern")
        
        # Check for Service layer pattern
        if has_services:
            patterns.append("Service Layer Pattern")
        
        # Check for Data Access Object pattern
        has_daos = any(comp.type == ComponentType.HIBERNATE_DAO 
                      for comp in self.components)
        if has_daos:
            patterns.append("Data Access Object (DAO) Pattern")
        
        # Check for Configuration pattern
        has_configs = any(comp.type == ComponentType.SPRING_CONFIGURATION 
                         for comp in self.components)
        if has_configs:
            patterns.append("Configuration Pattern")
        
        return patterns
    
    def get_api_summary(self) -> Dict[str, Any]:
        """Get a summary of API endpoints in the project."""
        endpoints = []
        
        for component in self.components:
            if component.is_web_component():
                component_endpoints = component.get_api_endpoints()
                endpoints.extend(component_endpoints)
        
        # Group by HTTP method
        method_distribution: Dict[str, int] = {}
        for endpoint in endpoints:
            method = endpoint.get("method", "GET")
            method_distribution[method] = method_distribution.get(method, 0) + 1
        
        return {
            "total_endpoints": len(endpoints),
            "endpoints": endpoints,
            "method_distribution": method_distribution,
            "unique_paths": len(set(ep.get("path", "") for ep in endpoints))
        }
    
    def get_database_summary(self) -> Dict[str, Any]:
        """Get a summary of database-related information."""
        entities = self.get_components_by_type(ComponentType.JPA_ENTITY)
        repositories = self.get_components_by_type(ComponentType.JPA_REPOSITORY)
        daos = self.get_components_by_type(ComponentType.HIBERNATE_DAO)
        
        # Extract table information
        tables = set()
        for entity in entities:
            if entity.database_table:
                tables.add(entity.database_table)
        
        return {
            "total_entities": len(entities),
            "total_repositories": len(repositories),
            "total_daos": len(daos),
            "database_tables": list(tables),
            "schemas": self.database_schemas,
            "data_access_patterns": self.data_access_patterns
        }
    
    def generate_modernization_recommendations(self) -> List[str]:
        """Generate recommendations for modernizing the project."""
        recommendations = []
        
        # Check for legacy patterns
        struts_components = self.get_components_by_type(ComponentType.STRUTS_ACTION)
        if struts_components:
            recommendations.append(
                "Consider migrating from Struts to Spring MVC for better maintainability"
            )
        
        # Check for modern Spring features
        spring_components = self.get_components_by_framework("spring")
        if spring_components and "Spring Boot" not in self.frameworks:
            recommendations.append(
                "Consider migrating to Spring Boot for simplified configuration and deployment"
            )
        
        # Check for REST API modernization
        web_components = self.get_web_components()
        if web_components and not any("REST" in pattern for pattern in self.integration_patterns):
            recommendations.append(
                "Consider implementing REST APIs for better service integration"
            )
        
        # Check for microservices opportunities
        if len(self.components) > 50:  # Large project
            recommendations.append(
                "Consider breaking down the monolithic architecture into microservices"
            )
        
        # Check for configuration externalization
        config_components = self.get_configuration_components()
        if config_components and not self.environment_configs:
            recommendations.append(
                "Consider externalizing configuration for different environments"
            )
        
        return recommendations
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the project."""
        self.tags.add(tag)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the project."""
        self.tags.discard(tag)
    
    def has_tag(self, tag: str) -> bool:
        """Check if project has a specific tag."""
        return tag in self.tags
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert project to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "project_type": self.project_type.value,
            "root_path": self.root_path,
            "technology_stacks": [stack.value for stack in self.technology_stacks],
            "programming_languages": self.programming_languages,
            "frameworks": self.frameworks,
            "architecture_type": self.architecture_type,
            "deployment_model": self.deployment_model,
            "integration_patterns": self.integration_patterns,
            "database_schemas": self.database_schemas,
            "database_tables": self.database_tables,
            "data_access_patterns": self.data_access_patterns,
            "api_endpoints": self.api_endpoints,
            "service_interfaces": self.service_interfaces,
            "configuration_files": self.configuration_files,
            "environment_configs": self.environment_configs,
            "tags": list(self.tags),
            "description": self.description,
            "components": [comp.to_dict() for comp in self.components],
            "file_structure": self.file_structure.to_dict() if self.file_structure else None,
            "component_dependencies": self.component_dependencies,
            "component_groups": self.component_groups,
            "analysis_summary": self.analysis_summary,
            "recommendations": self.recommendations,
            "metadata": {
                "size_category": self.metadata.size_category,
                "complexity_level": self.metadata.complexity_level,
                "technical_debt_score": self.metadata.technical_debt_score,
                "code_quality_score": self.metadata.code_quality_score,
                "maintainability_index": self.metadata.maintainability_index,
                "architectural_patterns": self.metadata.architectural_patterns,
                "design_patterns": self.metadata.design_patterns,
                "external_dependencies": self.metadata.external_dependencies,
                "framework_versions": self.metadata.framework_versions,
                "test_coverage": self.metadata.test_coverage,
                "documentation_coverage": self.metadata.documentation_coverage
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Project":
        """Create project from dictionary representation."""
        # Create metadata
        metadata_dict = data.get("metadata", {})
        metadata = ProjectMetadata(
            size_category=metadata_dict.get("size_category", "medium"),
            complexity_level=metadata_dict.get("complexity_level", "moderate"),
            technical_debt_score=metadata_dict.get("technical_debt_score"),
            code_quality_score=metadata_dict.get("code_quality_score"),
            maintainability_index=metadata_dict.get("maintainability_index"),
            architectural_patterns=metadata_dict.get("architectural_patterns", []),
            design_patterns=metadata_dict.get("design_patterns", []),
            external_dependencies=metadata_dict.get("external_dependencies", []),
            framework_versions=metadata_dict.get("framework_versions", {}),
            test_coverage=metadata_dict.get("test_coverage"),
            documentation_coverage=metadata_dict.get("documentation_coverage")
        )
        
        # Create project
        project = cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            project_type=ProjectType(data.get("project_type", ProjectType.UNKNOWN.value)),
            root_path=data.get("root_path", ""),
            technology_stacks=[TechnologyStack(stack) for stack in data.get("technology_stacks", [])],
            programming_languages=data.get("programming_languages", []),
            frameworks=data.get("frameworks", []),
            architecture_type=data.get("architecture_type"),
            deployment_model=data.get("deployment_model"),
            integration_patterns=data.get("integration_patterns", []),
            database_schemas=data.get("database_schemas", []),
            database_tables=data.get("database_tables", []),
            data_access_patterns=data.get("data_access_patterns", []),
            api_endpoints=data.get("api_endpoints", []),
            service_interfaces=data.get("service_interfaces", []),
            configuration_files=data.get("configuration_files", []),
            environment_configs=data.get("environment_configs", {}),
            tags=set(data.get("tags", [])),
            description=data.get("description"),
            component_dependencies=data.get("component_dependencies", {}),
            component_groups=data.get("component_groups", {}),
            analysis_summary=data.get("analysis_summary", {}),
            recommendations=data.get("recommendations", []),
            metadata=metadata
        )
        
        # Add components
        for comp_data in data.get("components", []):
            component = Component.from_dict(comp_data)
            project.add_component(component)
        
        return project
