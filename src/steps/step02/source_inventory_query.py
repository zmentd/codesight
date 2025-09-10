"""
Source inventory query and filtering utility for Step 02.

Provides a fluent API for searching, filtering, and counting items within
the source inventory based on various criteria.
"""
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union

from domain.source_inventory import (
    ArchitecturalLayerType,
    FileDetailsBase,
    FileInventoryItem,
    LayerType,
    PatternType,
    SourceInventory,
    SourceLocation,
    SourceType,
    Subdomain,
    SubdomainType,
)
from utils.logging.logger_factory import LoggerFactory


class QueryScope(Enum):
    """Defines the scope of the query operation."""
    SOURCE_LOCATIONS = "source_locations"
    SUBDOMAINS = "subdomains" 
    FILES = "files"


@dataclass
class QueryCriteria:
    """Represents search criteria for filtering inventory items."""
    # Path-based filters
    path_contains: Optional[str] = None
    path_regex: Optional[str] = None
    path_startswith: Optional[str] = None
    path_endswith: Optional[str] = None
    
    # Language and type filters
    languages: Optional[Set[str]] = None
    file_types: Optional[Set[str]] = None
    source_types: Optional[Set[SourceType]] = None
    subdomain_types: Optional[Set[SubdomainType]] = None
    
    # Layer and architectural filters
    layers: Optional[Set[LayerType]] = None
    architectural_layers: Optional[Set[ArchitecturalLayerType]] = None
    
    # Framework and pattern filters
    framework_hints: Optional[Set[str]] = None
    has_framework_hints: Optional[bool] = None
    
    # Size and metadata filters
    min_size_bytes: Optional[int] = None
    max_size_bytes: Optional[int] = None
    functional_name_contains: Optional[str] = None
    
    # Confidence and quality filters
    min_confidence: Optional[float] = None
    max_confidence: Optional[float] = None
    
    # Specific detail type filters
    has_entity_mapping: Optional[bool] = None
    has_sql_executions: Optional[bool] = None
    detail_types: Optional[Set[str]] = None  # java, jsp, sql, xml, etc.
    
    # Custom predicate filter
    custom_filter: Optional[Callable[[Any], bool]] = None


@dataclass
class QueryResult:
    """Contains the results of a query operation."""
    items: List[Any] = field(default_factory=list)
    total_count: int = 0
    scope: Optional[QueryScope] = None
    criteria_applied: Optional[QueryCriteria] = None
    
    def first(self) -> Optional[Any]:
        """Return first item or None if empty."""
        return self.items[0] if self.items else None
    
    def is_empty(self) -> bool:
        """Check if result is empty."""
        return self.total_count == 0
    
    def group_by(self, key_func: Callable[[Any], str]) -> Dict[str, List[Any]]:
        """Group results by a key function."""
        groups: Dict[str, List[Any]] = {}
        for item in self.items:
            key = key_func(item)
            if key not in groups:
                groups[key] = []
            groups[key].append(item)
        return groups


class SourceInventoryQuery:
    """
    Fluent API for querying and filtering source inventory data.
    
    Example usage:
        query = SourceInventoryQuery(source_inventory)
        
        # Find all Java files with entity mappings
        java_entities = query.files().language("java").has_entity_mapping().execute()
        
        # Find large files in service layer
        large_services = query.files().layer(LayerType.SERVICE).min_size(50000).execute()
        
        # Find subdomains with SQL executions
        sql_subdomains = query.subdomains().has_sql_executions().execute()
        
        # Count files by language
        counts = query.files().count_by(lambda f: f.language)
    """
    
    def __init__(self, source_inventory: SourceInventory):
        """Initialize with source inventory to query."""
        self.source_inventory = source_inventory
        self.criteria = QueryCriteria()
        self.current_scope = QueryScope.FILES  # Default scope
        self.logger = LoggerFactory.get_logger("steps.step02")
    
    # Scope selection methods
    def source_locations(self) -> 'SourceInventoryQuery':
        """Query source locations."""
        self.current_scope = QueryScope.SOURCE_LOCATIONS
        return self
    
    def subdomains(self) -> 'SourceInventoryQuery':
        """Query subdomains."""
        self.current_scope = QueryScope.SUBDOMAINS
        return self
    
    def files(self) -> 'SourceInventoryQuery':
        """Query files (default scope)."""
        self.current_scope = QueryScope.FILES
        return self
    
    # Path-based filters
    def path_contains(self, pattern: str) -> 'SourceInventoryQuery':
        """Filter by path containing pattern."""
        self.criteria.path_contains = pattern
        return self
    
    def path_regex(self, regex: str) -> 'SourceInventoryQuery':
        """Filter by path matching regex pattern."""
        self.criteria.path_regex = regex
        return self
    
    def path_startswith(self, prefix: str) -> 'SourceInventoryQuery':
        """Filter by path starting with prefix."""
        self.criteria.path_startswith = prefix
        return self
    
    def path_endswith(self, suffix: str) -> 'SourceInventoryQuery':
        """Filter by path ending with suffix."""
        self.criteria.path_endswith = suffix
        return self
    
    # Language and type filters
    def language(self, *languages: str) -> 'SourceInventoryQuery':
        """Filter by programming language(s)."""
        if self.criteria.languages is None:
            self.criteria.languages = set()
        self.criteria.languages.update(languages)
        return self
    
    def file_type(self, *types: str) -> 'SourceInventoryQuery':
        """Filter by file type(s)."""
        if self.criteria.file_types is None:
            self.criteria.file_types = set()
        self.criteria.file_types.update(types)
        return self
    
    def source_type(self, *types: SourceType) -> 'SourceInventoryQuery':
        """Filter by source type(s)."""
        if self.criteria.source_types is None:
            self.criteria.source_types = set()
        self.criteria.source_types.update(types)
        return self
    
    def subdomain_type(self, *types: SubdomainType) -> 'SourceInventoryQuery':
        """Filter by subdomain type(s)."""
        if self.criteria.subdomain_types is None:
            self.criteria.subdomain_types = set()
        self.criteria.subdomain_types.update(types)
        return self
    
    # Layer and architectural filters
    def layer(self, *layers: LayerType) -> 'SourceInventoryQuery':
        """Filter by architectural layer(s)."""
        if self.criteria.layers is None:
            self.criteria.layers = set()
        self.criteria.layers.update(layers)
        return self
    
    def architectural_layer(self, *layers: ArchitecturalLayerType) -> 'SourceInventoryQuery':
        """Filter by architectural layer type(s)."""
        if self.criteria.architectural_layers is None:
            self.criteria.architectural_layers = set()
        self.criteria.architectural_layers.update(layers)
        return self
    
    # Framework and pattern filters
    def framework_hint(self, *hints: str) -> 'SourceInventoryQuery':
        """Filter by framework hint(s)."""
        if self.criteria.framework_hints is None:
            self.criteria.framework_hints = set()
        self.criteria.framework_hints.update(hints)
        return self
    
    def has_framework_hints(self, has_hints: bool = True) -> 'SourceInventoryQuery':
        """Filter by presence of framework hints."""
        self.criteria.has_framework_hints = has_hints
        return self
    
    # Size and metadata filters
    def min_size(self, size_bytes: int) -> 'SourceInventoryQuery':
        """Filter by minimum file size."""
        self.criteria.min_size_bytes = size_bytes
        return self
    
    def max_size(self, size_bytes: int) -> 'SourceInventoryQuery':
        """Filter by maximum file size."""
        self.criteria.max_size_bytes = size_bytes
        return self
    
    def functional_name_contains(self, pattern: str) -> 'SourceInventoryQuery':
        """Filter by functional name containing pattern."""
        self.criteria.functional_name_contains = pattern
        return self
    
    # Confidence filters
    def min_confidence(self, confidence: float) -> 'SourceInventoryQuery':
        """Filter by minimum confidence score."""
        self.criteria.min_confidence = confidence
        return self
    
    def max_confidence(self, confidence: float) -> 'SourceInventoryQuery':
        """Filter by maximum confidence score."""
        self.criteria.max_confidence = confidence
        return self
    
    # Entity mapping and SQL execution filters
    def has_entity_mapping(self, has_mapping: bool = True) -> 'SourceInventoryQuery':
        """Filter by presence of entity mapping."""
        self.criteria.has_entity_mapping = has_mapping
        return self
    
    def has_sql_executions(self, has_sql: bool = True) -> 'SourceInventoryQuery':
        """Filter by presence of SQL executions."""
        self.criteria.has_sql_executions = has_sql
        return self
    
    def detail_type(self, *types: str) -> 'SourceInventoryQuery':
        """Filter by detail type(s) - java, jsp, sql, xml, etc."""
        if self.criteria.detail_types is None:
            self.criteria.detail_types = set()
        self.criteria.detail_types.update(types)
        return self
    
    # Custom filter
    def where(self, predicate: Callable[[Any], bool]) -> 'SourceInventoryQuery':
        """Apply custom filter predicate."""
        self.criteria.custom_filter = predicate
        return self
    
    # Execution methods
    def execute(self) -> QueryResult:
        """Execute the query and return results."""
        try:
            items: List[Any]
            if self.current_scope == QueryScope.SOURCE_LOCATIONS:
                items = self._filter_source_locations()
            elif self.current_scope == QueryScope.SUBDOMAINS:
                items = self._filter_subdomains()
            else:  # FILES
                items = self._filter_files()
            
            return QueryResult(
                items=items,
                total_count=len(items),
                scope=self.current_scope,
                criteria_applied=self.criteria
            )
        except (AttributeError, TypeError, ValueError) as e:
            # Log error and return empty result rather than crashing
            self.logger.error("Error executing query: %s", str(e))
            return QueryResult(
                items=[],
                total_count=0,
                scope=self.current_scope,
                criteria_applied=self.criteria
            )
    
    def count(self) -> int:
        """Execute query and return count only."""
        return self.execute().total_count
    
    def exists(self) -> bool:
        """Check if any items match the criteria."""
        return self.count() > 0
    
    def first(self) -> Optional[Any]:
        """Execute query and return first result or None."""
        return self.execute().first()
    
    def count_by(self, key_func: Callable[[Any], str]) -> Dict[str, int]:
        """Execute query and count results grouped by key function."""
        result = self.execute()
        groups = result.group_by(key_func)
        return {key: len(items) for key, items in groups.items()}
    
    def group_by(self, key_func: Callable[[Any], str]) -> Dict[str, List[Any]]:
        """Execute query and group results by key function."""
        return self.execute().group_by(key_func)
    
    # Private filtering methods
    def _filter_source_locations(self) -> List[SourceLocation]:
        """Filter source locations based on criteria."""
        items: List[SourceLocation] = []
        for source_location in self.source_inventory.source_locations:
            if self._matches_source_location(source_location):
                items.append(source_location)
        return items
    
    def _filter_subdomains(self) -> List[Subdomain]:
        """Filter subdomains based on criteria."""
        items: List[Subdomain] = []
        for source_location in self.source_inventory.source_locations:
            for subdomain in source_location.subdomains:
                if self._matches_subdomain(subdomain):
                    items.append(subdomain)
        return items
    
    def _filter_files(self) -> List[FileInventoryItem]:
        """Filter files based on criteria."""
        items: List[FileInventoryItem] = []
        for source_location in self.source_inventory.source_locations:
            for subdomain in source_location.subdomains:
                for file_item in subdomain.file_inventory:
                    if self._matches_file(file_item):
                        items.append(file_item)
        return items
    
    def _matches_source_location(self, source_location: SourceLocation) -> bool:
        """Check if source location matches criteria."""
        # Path filters
        if not self._matches_path_criteria(source_location.relative_path):
            return False
        
        # Language filters
        if self.criteria.languages and not any(lang in source_location.languages_detected 
                                              for lang in self.criteria.languages):
            return False
        
        # Custom filter
        if self.criteria.custom_filter and not self.criteria.custom_filter(source_location):
            return False
        
        return True
    
    def _matches_subdomain(self, subdomain: Subdomain) -> bool:
        """Check if subdomain matches criteria."""
        # Path filters
        if not self._matches_path_criteria(subdomain.path):
            return False
        
        # Type filters
        if self.criteria.source_types and subdomain.type not in self.criteria.source_types:
            return False
        
        if (self.criteria.subdomain_types and 
                subdomain.preliminary_subdomain_type and 
                subdomain.preliminary_subdomain_type not in self.criteria.subdomain_types):
            return False
        
        # Layer filters
        if self.criteria.layers:
            subdomain_layers = set()
            for layer in subdomain.layers:
                if layer:
                    try:
                        # Convert string to LayerType enum
                        layer_enum = LayerType(layer)
                        subdomain_layers.add(layer_enum)
                    except (ValueError, AttributeError):
                        # Handle unknown layer types gracefully
                        continue
            
            if subdomain_layers and not subdomain_layers.intersection(self.criteria.layers):
                return False
        
        # Framework hints
        if self.criteria.framework_hints and not subdomain.framework_hints.intersection(self.criteria.framework_hints):
            return False
        
        if self.criteria.has_framework_hints is not None:
            has_hints = bool(subdomain.framework_hints)
            if has_hints != self.criteria.has_framework_hints:
                return False
        
        # Confidence filters
        if (self.criteria.min_confidence is not None and 
                (subdomain.confidence is None or subdomain.confidence < self.criteria.min_confidence)):
            return False
        
        if (self.criteria.max_confidence is not None and 
                (subdomain.confidence is None or subdomain.confidence > self.criteria.max_confidence)):
            return False
        
        # Entity mapping and SQL execution filters (check files in subdomain)
        if self.criteria.has_entity_mapping is not None or self.criteria.has_sql_executions is not None:
            has_entity = any(self._file_has_entity_mapping(f) for f in subdomain.file_inventory)
            has_sql = any(self._file_has_sql_executions(f) for f in subdomain.file_inventory)
            
            if self.criteria.has_entity_mapping is not None and has_entity != self.criteria.has_entity_mapping:
                return False
            
            if self.criteria.has_sql_executions is not None and has_sql != self.criteria.has_sql_executions:
                return False
        
        # Custom filter
        if self.criteria.custom_filter and not self.criteria.custom_filter(subdomain):
            return False
        
        return True
    
    def _matches_file(self, file_item: FileInventoryItem) -> bool:
        """Check if file matches criteria."""
        # Path filters
        if not self._matches_path_criteria(file_item.path):
            return False
        
        # Language and type filters
        if self.criteria.languages and file_item.language not in self.criteria.languages:
            return False
        
        if self.criteria.file_types and file_item.type not in self.criteria.file_types:
            return False
        
        # Layer filters
        if self.criteria.layers:
            if not file_item.layer:
                # If no layer specified, exclude unless criteria includes OTHER
                return LayerType.OTHER in self.criteria.layers
            
            try:
                file_layer = LayerType(file_item.layer)
                if file_layer not in self.criteria.layers:
                    return False
            except ValueError:
                # Handle unknown layer types - check if OTHER is allowed
                return LayerType.OTHER in self.criteria.layers
        
        # Size filters
        if self.criteria.min_size_bytes and file_item.size_bytes < self.criteria.min_size_bytes:
            return False
        
        if self.criteria.max_size_bytes and file_item.size_bytes > self.criteria.max_size_bytes:
            return False
        
        # Functional name filter
        if (self.criteria.functional_name_contains and 
                self.criteria.functional_name_contains not in file_item.functional_name):
            return False
        
        # Framework hints
        if self.criteria.framework_hints and not file_item.framework_hints.intersection(self.criteria.framework_hints):
            return False
        
        if self.criteria.has_framework_hints is not None:
            has_hints = bool(file_item.framework_hints)
            if has_hints != self.criteria.has_framework_hints:
                return False
        
        # Detail type filter
        if self.criteria.detail_types:
            if not file_item.details:
                return False
            file_detail_type = file_item.details.get_file_type()
            if file_detail_type not in self.criteria.detail_types:
                return False
        
        # Entity mapping filter
        if self.criteria.has_entity_mapping is not None:
            has_entity = self._file_has_entity_mapping(file_item)
            if has_entity != self.criteria.has_entity_mapping:
                return False
        
        # SQL execution filter
        if self.criteria.has_sql_executions is not None:
            has_sql = self._file_has_sql_executions(file_item)
            if has_sql != self.criteria.has_sql_executions:
                return False
        
        # Custom filter
        if self.criteria.custom_filter and not self.criteria.custom_filter(file_item):
            return False
        
        return True
    
    def _matches_path_criteria(self, path: str) -> bool:
        """Check if path matches path-based criteria."""
        if self.criteria.path_contains and self.criteria.path_contains not in path:
            return False
        
        if self.criteria.path_regex:
            try:
                if not re.search(self.criteria.path_regex, path):
                    return False
            except re.error:
                # Invalid regex pattern - log error and treat as non-matching
                self.logger.error("Invalid regex pattern: %s", self.criteria.path_regex)
                return False
        
        if self.criteria.path_startswith and not path.startswith(self.criteria.path_startswith):
            return False
        
        if self.criteria.path_endswith and not path.endswith(self.criteria.path_endswith):
            return False
        
        return True
    
    def _file_has_entity_mapping(self, file_item: FileInventoryItem) -> bool:
        """Check if file has entity mapping in its details."""
        if not file_item.details:
            return False
        
        # Check if it's a Java file with entity mapping
        if file_item.details.get_file_type() == 'java':
            from domain.java_details import JavaDetails
            if isinstance(file_item.details, JavaDetails):
                # Look for entity_mapping in class data directly
                for java_class in file_item.details.classes:
                    if java_class.entity_mapping is not None:
                        return True
        
        return False
    
    def _file_has_sql_executions(self, file_item: FileInventoryItem) -> bool:
        """Check if file has SQL executions in its details."""
        if not file_item.details:
            return False
        
        # Check if it's a Java file with SQL executions
        if file_item.details.get_file_type() == 'java':
            from domain.java_details import JavaDetails
            if isinstance(file_item.details, JavaDetails):
                # Look for sql_statements or stored procedure calls in method data directly
                for java_class in file_item.details.classes:
                    for method in java_class.methods:
                        if (method.sql_statements and len(method.sql_statements) > 0) or \
                           (method.sql_stored_procedures and len(method.sql_stored_procedures) > 0):
                            return True
        
        return False


# Convenience functions for common queries
def find_entity_managers(source_inventory: SourceInventory) -> QueryResult:
    """Find all files with entity mappings."""
    return SourceInventoryQuery(source_inventory).files().has_entity_mapping().execute()


def find_sql_operations(source_inventory: SourceInventory) -> QueryResult:
    """Find all files with SQL executions."""
    return SourceInventoryQuery(source_inventory).files().has_sql_executions().execute()


def count_files_by_language(source_inventory: SourceInventory) -> Dict[str, int]:
    """Count files grouped by programming language."""
    return SourceInventoryQuery(source_inventory).files().count_by(lambda f: f.language)


def find_large_files(source_inventory: SourceInventory, min_size: int = 50000) -> QueryResult:
    """Find files larger than specified size."""
    return SourceInventoryQuery(source_inventory).files().min_size(min_size).execute()


def find_service_layer_files(source_inventory: SourceInventory) -> QueryResult:
    """Find all files in the service layer."""
    return SourceInventoryQuery(source_inventory).files().layer(LayerType.SERVICE).execute()