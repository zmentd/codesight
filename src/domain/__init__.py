"""
Domain models for CodeSight source inventory.

This package contains the domain classes for representing file system analysis results
from STEP01, including source structures, Java details, JSP details, and factory functions.
"""

from .component import Component, ComponentMetadata, ComponentType
from .config_details import (
    CodeMapping,
    CodeMappingGroup,
    ConfigurationDetails,
    DeterministicForward,
    ExceptionMapping,
    ValidationRule,
    ValidatorDefinition,
)
from .file_structure import FileNode, FileStructure
from .java_details import (
    JavaAnnotation,
    JavaClass,
    JavaDetails,
    JavaField,
    JavaMethod,
    JavaParameter,
)
from .jsp_details import FormButton, FormField, HtmlForm, JspDetails, JspElement, ScreenElements
from .project_model import Project, ProjectMetadata
from .source_factory import (
    create_details_factory,
    extract_business_packages,
    parse_step01_output,
    parse_step01_sources,
    validate_source_inventory,
)
from .source_inventory import (
    ArchitecturalPattern,
    FileDetailsBase,
    FileInventoryItem,
    LayerType,
    PackageLayer,
    PatternType,
    SourceInventory,
    SourceLocation,
    SourceType,
    Subdomain,
)
from .step02_output import ProjectData, Statistics, Step02AstExtractorOutput, StepMetadata

__all__ = [
    "Component",
    "ComponentType", 
    "ComponentMetadata",
    "FileNode",
    "FileStructure",
    "Project",
    "ProjectMetadata",
    
    # New source inventory classes
    # Enums
    'SourceType',
    'LayerType', 
    'PatternType',
    
    # Base classes
    'PackageLayer',
    'ArchitecturalPattern',
    'FileDetailsBase',
    
    # Main inventory classes
    'FileInventoryItem',
    'Subdomain',
    'SourceLocation',
    'SourceInventory',
    
    # Java details
    'JavaAnnotation',
    'JavaParameter',
    'JavaMethod',
    'JavaField',
    'JavaClass',
    'JavaDetails',
    
    # JSP details
    'FormButton',
    'FormField',
    'HtmlForm',
    'JspElement',
    'ScreenElements',
    'JspDetails',
    
    # Factory functions
    'create_details_factory',
    'parse_step01_sources',
    'parse_step01_output',
    'validate_source_inventory',
    'extract_business_packages',

    # Configuration details
    'CodeMapping',
    'CodeMappingGroup',
    'ConfigurationDetails',
    'DeterministicForward',
    'ValidationRule',
    'ValidatorDefinition',
    'ExceptionMapping',

    # Step 02 output
    'StepMetadata',
    'Statistics',
    'Step02AstExtractorOutput',
    'ProjectData',
]

