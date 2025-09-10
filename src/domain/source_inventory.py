"""
Source inventory domain models for representing file system analysis results.

This module contains the core classes for representing sources, subdomains, and file inventories
discovered during STEP01 filesystem analysis.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Type, Union


class SubdomainType(Enum):
    """Types of source locations."""
    SCREEN = "screen"
    SERVICE = "service" 
    INTEGRATION = "integration"
    UTILITY = "utility"
    DATABASE = "database"
    UNKNOWN = "unknown"


class SourceType(Enum):
    """Types of source locations."""
    SOURCE = "source"
    WEB = "web"
    DATABASE = "database"
    CONFIG = "config"
    SCRIPT = "script"
    STYLE = "style"
    DESCRIPTOR = "descriptor"


class LayerType(Enum):
    """Architectural layer types."""
    UI = "UI"
    SERVICE = "Service"
    DATABASE = "Database"
    INTEGRATION = "Integration"
    UTILITY = "Utility"
    CONFIGURATION = "Configuration"
    REPORTING = "Reporting"
    OTHER = "Other"
    NONE = "none"


class PatternType(Enum):
    """Pattern detection types."""
    JAVA_PACKAGE = "java_package"
    UI_PATH = "ui_path"
    FILE_TYPE_FALLBACK = "file_type_fallback"
    FALLBACK = "fallback"
    ARCHITECTURAL_INFERENCE = "architectural_inference"
    DIRECTORY_BASED = "directory_based"
    NONE = "none"


class ArchitecturalLayerType(Enum):
    """Architectural layer types from configuration."""
    APPLICATION = "application"
    BUSINESS = "business"
    DATA_ACCESS = "data_access"
    SECURITY = "security"
    SHARED = "shared"
    UNKNOWN = "unknown"


class EnumUtils:
    @staticmethod
    def to_layer_type(value: Union[str, LayerType, Any]) -> LayerType:
        """Convert string or enum to LayerType with fallback handling."""
        # Handle LayerType enum objects directly
        if isinstance(value, LayerType):
            return value
            
        # Handle enum objects directly (workaround for import issues)
        if hasattr(value, '__class__') and hasattr(value.__class__, '__name__'):
            if 'LayerType' in value.__class__.__name__:
                # Try to convert from enum-like object to LayerType
                try:
                    if hasattr(value, 'value'):
                        enum_value = getattr(value, 'value')
                    else:
                        enum_value = str(value)
                    return LayerType(enum_value)
                except (ValueError, AttributeError):
                    pass
        
        # Handle string values
        if isinstance(value, str):
            value_lower = value.lower()
            for layer_type in LayerType:
                if value_lower == layer_type.value.lower():
                    return layer_type
        
        return LayerType.OTHER
    
    @staticmethod
    def to_architectural_layer_type(value: Union[str, ArchitecturalLayerType, Any]) -> ArchitecturalLayerType:
        """Convert string or enum to ArchitecturalLayerType with fallback handling."""
        # Handle ArchitecturalLayerType enum objects directly
        if isinstance(value, ArchitecturalLayerType):
            return value
            
        # Handle enum objects directly (workaround for import issues)
        if hasattr(value, '__class__') and hasattr(value.__class__, '__name__'):
            if 'ArchitecturalLayerType' in value.__class__.__name__:
                # Try to convert from enum-like object to ArchitecturalLayerType
                try:
                    if hasattr(value, 'value'):
                        enum_value = getattr(value, 'value')
                    else:
                        enum_value = str(value)
                    return ArchitecturalLayerType(enum_value)
                except (ValueError, AttributeError):
                    pass
        
        # Handle string values
        if isinstance(value, str):
            value_lower = value.lower()
            for arch_type in ArchitecturalLayerType:
                if value_lower == arch_type.value.lower():
                    return arch_type
        
        return ArchitecturalLayerType.UNKNOWN


class FileDetailsFactory:
    """Factory for creating file details based on file type."""
    
    @staticmethod
    def create_details(file_type: str, data: Dict[str, Any]) -> Optional['FileDetailsBase']:
        """Create file details class based on file type."""
        # Import here to avoid circular imports
        from domain.config_details import ConfigurationDetails
        from domain.java_details import JavaDetails
        from domain.jsp_details import JspDetails
        from domain.sql_details import SQLDetails

        # Look for the corresponding details in the JSON data based on file type
        details_data = None
        
        if data.get('sql_details'):
            details_data = data['sql_details']
            try:
                # Details are stored as arrays in JSON, so take the first item
                if isinstance(details_data, list) and len(details_data) > 0:
                    return SQLDetails.from_dict(details_data[0])
                elif isinstance(details_data, dict):
                    return SQLDetails.from_dict(details_data)
            except Exception as e:  # pylint: disable=broad-except
                import traceback
                print(f"Error creating SQLDetails: {str(e)}")
                print(f"Stack trace:\n{traceback.format_exc()}")
                raise e
                
        elif data.get('java_details'):
            details_data = data['java_details']
            try:
                if isinstance(details_data, list) and len(details_data) > 0:
                    return JavaDetails.from_dict(details_data[0])
                elif isinstance(details_data, dict):
                    return JavaDetails.from_dict(details_data)
            except Exception as e:  # pylint: disable=broad-except
                import traceback
                print(f"Error creating JavaDetails: {str(e)}")
                print(f"Stack trace:\n{traceback.format_exc()}")
                raise e
                
        elif data.get('jsp_details'):
            details_data = data['jsp_details']
            try:
                if isinstance(details_data, list) and len(details_data) > 0:
                    return JspDetails.from_dict(details_data[0])
                elif isinstance(details_data, dict):
                    return JspDetails.from_dict(details_data)
            except Exception as e:  # pylint: disable=broad-except
                import traceback
                print(f"Error creating JspDetails: {str(e)}")
                print(f"Stack trace:\n{traceback.format_exc()}")
                raise e
                
        elif data.get('configuration_details'):
            details_data = data['configuration_details']
            try:
                if isinstance(details_data, list) and len(details_data) > 0:
                    return ConfigurationDetails.from_dict(details_data[0])
                elif isinstance(details_data, dict):
                    return ConfigurationDetails.from_dict(details_data)
            except Exception as e:  # pylint: disable=broad-except
                import traceback
                print(f"Error creating ConfigurationDetails: {str(e)}")
                print(f"Stack trace:\n{traceback.format_exc()}")
                raise e
        
        return None
    

@dataclass
class PackageLayer:
    """Represents package layer classification."""
    layer: LayerType
    pattern_type: PatternType
    confidence: float
    matched_pattern: Optional[str] = None
    package_name: Optional[str] = None
    path_indicator: Optional[str] = None
    inferred_from_pattern: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'layer': self.layer.value,
            'pattern_type': self.pattern_type.value,
            'confidence': self.confidence,
            'matched_pattern': self.matched_pattern,
            'package_name': self.package_name,
            'path_indicator': self.path_indicator,
            'inferred_from_pattern': self.inferred_from_pattern
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PackageLayer':
        """Create instance from dictionary."""
        return cls(
            layer=LayerType(data['layer']),
            pattern_type=PatternType(data['pattern_type']),
            confidence=data['confidence'],
            matched_pattern=data.get('matched_pattern'),
            package_name=data.get('package_name'),
            path_indicator=data.get('path_indicator'),
            inferred_from_pattern=data.get('inferred_from_pattern')
        )


@dataclass
class ArchitecturalPattern:
    """Represents architectural pattern detection."""
    pattern: str  # The specific glob pattern that matched (e.g., "**/dsl/**")
    architectural_layer: ArchitecturalLayerType  # WHAT was detected (business meaning, e.g., "data_access")
    pattern_type: PatternType  # HOW it was detected (detection method)
    confidence: float
    package_name: Optional[str] = None
    detected_from_directory: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'pattern': self.pattern,
            'architectural_layer': self.architectural_layer.value,
            'pattern_type': self.pattern_type.value,
            'confidence': self.confidence,
            'package_name': self.package_name,
            'detected_from_directory': self.detected_from_directory
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArchitecturalPattern':
        """Create instance from dictionary."""
        return cls(
            pattern=data['pattern'],
            architectural_layer=ArchitecturalLayerType(data['architectural_layer']),
            pattern_type=PatternType(data['pattern_type']),
            confidence=data['confidence'],
            package_name=data.get('package_name'),
            detected_from_directory=data.get('detected_from_directory', False)
        )


class FileDetailsBase(ABC):
    """Abstract base class for file-specific details."""
    
    @abstractmethod
    def get_file_type(self) -> str:
        """Return the file type identifier."""
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileDetailsBase':
        """Create instance from dictionary."""


@dataclass
class FileInventoryItem:
    """Represents a single file in the inventory."""
    path: str
    language: str
    layer: str
    size_bytes: int
    source_location: str
    last_modified: str  # ISO format datetime string
    type: str
    functional_name: str
    package_layer: Optional[PackageLayer] = None
    architectural_pattern: Optional[ArchitecturalPattern] = None
    framework_hints: Set[str] = field(default_factory=set)
    details: Optional[FileDetailsBase] = None
    # New: optional provenance payload populated by Step01 when enabled
    provenance: Optional[Dict[str, Any]] = None
    
    def get_last_modified_datetime(self) -> datetime:
        """Convert last_modified string to datetime object."""
        return datetime.fromisoformat(self.last_modified.replace('Z', '+00:00'))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            'path': self.path,
            'source_location': self.source_location,
            'size_bytes': self.size_bytes,
            'language': self.language,
            'layer': self.layer,
            'last_modified': self.last_modified,
            'type': self.type,
            'functional_name': self.functional_name,
            'package_layer': self.package_layer.to_dict() if self.package_layer else None,
            'architectural_pattern': self.architectural_pattern.to_dict() if self.architectural_pattern else None,
            'framework_hints': list(self.framework_hints)
        }
        
        if self.details:
            detail_key = f"{self.details.get_file_type()}_details"
            result[detail_key] = [self.details.to_dict()]
        
        # Include provenance if available
        if self.provenance is not None:
            result['provenance'] = self.provenance
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileInventoryItem':
        """Create instance from dictionary."""
        # Parse package_layer
        package_layer = None
        if data.get('package_layer'):
            package_layer = PackageLayer.from_dict(data['package_layer'])
        
        # Parse architectural_pattern
        architectural_pattern = None
        if data.get('architectural_pattern'):
            ap_data = data['architectural_pattern']
            architectural_pattern = ArchitecturalPattern(
                pattern=ap_data['pattern'],
                architectural_layer=ArchitecturalLayerType(ap_data['architectural_layer']),
                pattern_type=PatternType(ap_data['pattern_type']),
                confidence=ap_data['confidence'],
                package_name=ap_data.get('package_name'),
                detected_from_directory=ap_data.get('detected_from_directory', False)
            )
        
        details = FileDetailsFactory.create_details(
            data.get('language', ''),
            data
        )
        
        file_inventory_cls = cls(
            path=data['path'],
            source_location=data['source_location'],
            size_bytes=data['size_bytes'],
            language=data['language'],
            layer=data['layer'],
            last_modified=data['last_modified'],
            type=data['type'],
            functional_name=data['functional_name'],
            package_layer=package_layer,
            architectural_pattern=architectural_pattern,
            framework_hints=set(data.get('framework_hints', [])),
            details=details if details else None,
            provenance=data.get('provenance')
        )

        return file_inventory_cls


@dataclass
class Subdomain:
    """Represents a subdomain within a source location."""
    path: str
    name: str
    type: SourceType
    source_location: str
    confidence: float
    layers: Set[str] = field(default_factory=set)
    framework_hints: Set[str] = field(default_factory=set)
    preliminary_subdomain_type: Optional[SubdomainType] = None
    preliminary_subdomain_name: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    package_layer: Optional[PackageLayer] = None
    architectural_pattern: Optional[ArchitecturalPattern] = None
    file_inventory: List[FileInventoryItem] = field(default_factory=list)
    
    @staticmethod
    def _safe_enum_conversion(value: Any, enum_class: Any) -> Any:
        """Safely convert a value to an enum, handling both string and enum inputs."""
        if value is None:
            return None
        if isinstance(value, enum_class):
            return value
        if isinstance(value, str):
            try:
                return enum_class(value)
            except ValueError:
                # If the string doesn't match any enum value, return None
                return None
        return value
    
    def get_total_files(self) -> int:
        """Return total number of files in this subdomain."""
        return len(self.file_inventory)
    
    def get_files_by_language(self, language: str) -> List[FileInventoryItem]:
        """Return files filtered by language."""
        return [f for f in self.file_inventory if f.language.lower() == language.lower()]
    
    def get_files_by_type(self, file_type: str) -> List[FileInventoryItem]:
        """Return files filtered by type."""
        return [f for f in self.file_inventory if f.type == file_type]

    def add_file_inventory_item(self, file_inventory_item: FileInventoryItem, layer: str, framework_hints: Optional[List[str]] = None) -> None:
        """Add a file to this subdomain."""
        from pathlib import Path

        # Extract functional_name as filename without extension
        file_path = Path(file_inventory_item.path)
        functional_name = file_path.stem
        file_inventory_item.functional_name = functional_name
        file_inventory_item.layer = layer
        file_inventory_item.framework_hints = set(framework_hints or [])    
        self.file_inventory.append(file_inventory_item)
        self.layers.add(layer)
        if framework_hints:
            self.framework_hints.update(framework_hints)
    
    def add_file(self, file_info: Dict[str, Any], layer: str, framework_hints: Optional[List[str]] = None) -> None:
        """Add a file to this subdomain."""
        from pathlib import Path

        # Extract functional_name as filename without extension
        file_inventory_item = FileInventoryItem(
            path=file_info['path'],
            language=file_info['language'],
            layer=layer,
            size_bytes=file_info['size_bytes'],
            source_location=file_info.get('source_location', ''),
            last_modified=file_info['last_modified'],
            type=file_info.get('type', ''),
            functional_name="",
            framework_hints=set(framework_hints or []),
            details=None
        )
        self.add_file_inventory_item(file_inventory_item, layer, framework_hints)
 
    def get_unique_layers(self) -> Set[str]:
        """Get all unique layers this subdomain spans."""
        return self.layers
    
    def calculate_confidence(self) -> float:
        """Calculate confidence score for this subdomain."""
        base_confidence = 0.6
        
        # Higher confidence for subdomains with multiple files
        if len(self.file_inventory) > 3:
            base_confidence += 0.2
        
        # Higher confidence for multi-layer subdomains
        if len(self.layers) > 1:
            base_confidence += 0.1
        
        # Higher confidence for subdomains with framework hints
        if self.framework_hints:
            base_confidence += 0.1
        
        return min(base_confidence, 0.9)
    
    def merge_with(self, other_subdomain: 'Subdomain') -> None:
        """Merge another subdomain into this one."""
        self.file_inventory.extend(other_subdomain.file_inventory)
        self.layers.update(other_subdomain.layers)
        self.framework_hints.update(other_subdomain.framework_hints)
    
    def to_component_dict(self) -> Dict[str, Any]:
        """Convert subdomain to component-style dictionary format for output compatibility."""
        return {
            "name": self.name,
            "type": self.type.value if isinstance(self.type, SourceType) else str(self.type),
            "files": [{"path": f.path, "layer": f.layer} for f in self.file_inventory],
            "layers_detected": list(self.get_unique_layers()),
            "confidence": self.calculate_confidence(),
            "functional_requirements": {
                "description": f"Generated component for {self.name}",
                "business_rules": [],
                "data_entities": []
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'path': self.path,
            'name': self.name,
            'type': self.type.value if isinstance(self.type, SourceType) else self.type,
            'source_location': self.source_location,
            'confidence': self.confidence,
            'layers': list(self.layers),
            'framework_hints': list(self.framework_hints),
            'preliminary_subdomain_type': self.preliminary_subdomain_type.value if isinstance(self.preliminary_subdomain_type, SubdomainType) else self.preliminary_subdomain_type,
            'preliminary_subdomain_name': self.preliminary_subdomain_name,
            'tags': self.tags,
            'package_layer': self.package_layer.to_dict() if self.package_layer else None,
            'architectural_pattern': self.architectural_pattern.to_dict() if self.architectural_pattern else None,
            'file_inventory': [f.to_dict() for f in self.file_inventory]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Subdomain':
        """Create instance from dictionary."""
        # Parse package_layer
        package_layer = None
        if data.get('package_layer'):
            package_layer = PackageLayer.from_dict(data['package_layer'])
        
        # Parse architectural_pattern
        architectural_pattern = None
        if data.get('architectural_pattern'):
            ap_data = data['architectural_pattern']
            architectural_pattern = ArchitecturalPattern(
                pattern=ap_data['pattern'],
                architectural_layer=ArchitecturalLayerType(ap_data['architectural_layer']),
                pattern_type=PatternType(ap_data['pattern_type']),
                confidence=ap_data['confidence'],
                package_name=ap_data.get('package_name'),
                detected_from_directory=ap_data.get('detected_from_directory', False)
            )
        
        # Parse file inventory
        file_inventory = []
        for file_data in data.get('file_inventory', []):
            file_inventory.append(FileInventoryItem.from_dict(file_data))
        
        return cls(
            path=data['path'],
            name=data['name'],
            type=SourceType(data['type']),
            source_location=data['source_location'],
            confidence=data['confidence'],
            layers=set(data.get('layers', [])),
            framework_hints=set(data.get('framework_hints', [])),
            preliminary_subdomain_type=cls._safe_enum_conversion(data.get('preliminary_subdomain_type'), SubdomainType),
            preliminary_subdomain_name=data.get('preliminary_subdomain_name'),
            tags=data.get('tags', []),
            package_layer=package_layer,
            architectural_pattern=architectural_pattern,
            file_inventory=file_inventory
        )


@dataclass
class SourceLocation:
    """Represents a top-level source location."""
    relative_path: str
    directory_name: Optional[str] = None
    language_type: Optional[str] = None
    primary_language: Optional[str] = None
    root_package: Optional[List[str]] = None
    languages_detected: Set[str] = field(default_factory=set)
    file_counts_by_language: Dict[str, int] = field(default_factory=dict)
    subdomains: List[Subdomain] = field(default_factory=list)
    
    def get_total_subdomains(self) -> int:
        """Return total number of subdomains."""
        return len(self.subdomains)
    
    def get_total_files(self) -> int:
        """Return total number of files across all subdomains."""
        return sum(subdomain.get_total_files() for subdomain in self.subdomains)
    
    def get_subdomains_by_type(self, source_type: SourceType) -> List[Subdomain]:
        """Return subdomains filtered by type."""
        return [s for s in self.subdomains if s.type == source_type]
    
    def get_files_by_language(self, language: str) -> List[FileInventoryItem]:
        """Return all files filtered by language across all subdomains."""
        files = []
        for subdomain in self.subdomains:
            files.extend(subdomain.get_files_by_language(language))
        return files
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        # Extract subdomain analysis
        subdomain_names = []
        meaningful_subdomains = []
        excluded_names = {'none', 'other', 'unknown', ''}
        
        for subdomain in self.subdomains:
            subdomain_names.append(subdomain.name)
            if subdomain.name and subdomain.name.lower() not in excluded_names:
                meaningful_subdomains.append(subdomain.name)
        
        return {
            'relative_path': self.relative_path,
            'directory_name': self.directory_name,
            'language_type': self.language_type,
            'primary_language': self.primary_language,
            'root_package': self.root_package,
            'languages_detected': list(self.languages_detected),
            'file_counts_by_language': self.file_counts_by_language,
            'subdomain_summary': {
                'total_subdomains': len(self.subdomains),
                'all_subdomain_names': subdomain_names,
                'meaningful_subdomain_names': sorted(list(set(meaningful_subdomains))),
                'meaningful_subdomain_count': len(set(meaningful_subdomains))
            },
            'subdomains': [s.to_dict() for s in self.subdomains]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SourceLocation':
        """Create instance from dictionary."""
        subdomains = []
        for subdomain_data in data.get('subdomains', []):
            subdomains.append(Subdomain.from_dict(subdomain_data))
        
        return cls(
            relative_path=data['relative_path'],
            directory_name=data.get('directory_name'),
            language_type=data.get('language_type'),
            primary_language=data.get('primary_language'),
            root_package=data.get('root_package'),
            languages_detected=set(data.get('languages_detected', [])),
            file_counts_by_language=data.get('file_counts_by_language', {}),
            subdomains=subdomains
        )


@dataclass
class SourceInventory:
    """Container for all source inventory data."""
    root_path: Optional[str] = None
    source_locations: List[SourceLocation] = field(default_factory=list)
    
    def get_total_sources(self) -> int:
        """Return total number of sources."""
        return len(self.source_locations)

    def get_total_files(self) -> int:
        """Return total number of files across all sources."""
        return sum(source.get_total_files() for source in self.source_locations)

    def get_source_by_path(self, path: str) -> Optional[SourceLocation]:
        """Find source by path."""
        for source in self.source_locations:
            if source.relative_path == path:
                return source
        return None
    
    def get_all_files_by_language(self, language: str) -> List[FileInventoryItem]:
        """Return all files filtered by language across all sources."""
        files = []
        for source in self.source_locations:
            files.extend(source.get_files_by_language(language))
        return files
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'source_locations': [s.to_dict() for s in self.source_locations]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SourceInventory':
        """Create instance from dictionary."""
        source_locations = []
        for source_data in data.get('source_locations', []):
            source_locations.append(SourceLocation.from_dict(source_data))

        return cls(source_locations=source_locations)