"""
Java-specific file details for source inventory.

This module contains classes for representing Java source code analysis results,
including class structures, methods, fields, and annotations.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from .config_details import CodeMapping
from .source_inventory import ArchitecturalLayerType, FileDetailsBase, LayerType
from .sql_details import SQLStatement, SQLStoredProcedureDetails


@dataclass
class EntityMappingDetails:
    """Details about entity to table mapping in Java classes."""
    entity_class: str
    table_name: str
    schema: Optional[str] = None
    database: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'entity_class': self.entity_class,
            'table_name': self.table_name,
            'schema': self.schema,
            'database': self.database
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EntityMappingDetails':
        """Create instance from dictionary."""
        return cls(
            entity_class=data['entity_class'],
            table_name=data['table_name'],
            schema=data.get('schema'),
            database=data.get('database')
        )
    

@dataclass
class JavaAnnotation:
    """Represents a Java annotation."""
    name: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    framework: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'name': self.name,
            'attributes': self.attributes,
            'framework': self.framework
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JavaAnnotation':
        """Create instance from dictionary."""
        return cls(
            name=data['name'],
            attributes=data.get('attributes', {}),
            framework=data.get('framework')
        )


@dataclass
class JavaParameter:
    """Represents a Java method parameter."""
    name: str
    type: str
    annotations: List[JavaAnnotation] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'name': self.name,
            'type': self.type,
            'annotations': [ann.to_dict() for ann in self.annotations]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JavaParameter':
        """Create instance from dictionary."""
        annotations = []
        for ann_data in data.get('annotations', []):
            if isinstance(ann_data, str):
                # Handle simple annotation names
                annotations.append(JavaAnnotation(name=ann_data))
            else:
                annotations.append(JavaAnnotation.from_dict(ann_data))
        
        return cls(
            name=data['name'],
            type=data['type'],
            annotations=annotations
        )


@dataclass
class JavaMethod:
    """Represents a Java method."""
    name: str
    visibility: str
    modifiers: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    parameters: List[JavaParameter] = field(default_factory=list)
    exceptions: List[str] = field(default_factory=list)
    annotations: List[JavaAnnotation] = field(default_factory=list)
    complexity_score: Optional[int] = None
    line_count: Optional[int] = None
    sql_statements: List[SQLStatement] = field(default_factory=list)
    sql_stored_procedures: List[SQLStoredProcedureDetails] = field(default_factory=list)
    
    def is_public(self) -> bool:
        """Check if method is public."""
        return self.visibility == 'public'
    
    def has_annotation(self, annotation_name: str) -> bool:
        """Check if method has specific annotation."""
        return any(ann.name == annotation_name for ann in self.annotations)
    
    def get_annotation(self, annotation_name: str) -> Optional[JavaAnnotation]:
        """Get specific annotation by name."""
        for ann in self.annotations:
            if ann.name == annotation_name:
                return ann
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'name': self.name,
            'visibility': self.visibility,
            'modifiers': self.modifiers,
            'return_type': self.return_type,
            'parameters': [p.to_dict() for p in self.parameters],
            'exceptions': self.exceptions,
            'annotations': [ann.to_dict() for ann in self.annotations],
            'complexity_score': self.complexity_score,
            'line_count': self.line_count,
            'sql_statements': [stmt.to_dict() for stmt in self.sql_statements],
            'sql_stored_procedures': [sp.to_dict() for sp in self.sql_stored_procedures]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JavaMethod':
        """Create instance from dictionary."""
        parameters = []
        for param_data in data.get('parameters', []):
            parameters.append(JavaParameter.from_dict(param_data))
        
        annotations = []
        for ann_data in data.get('annotations', []):
            if isinstance(ann_data, str):
                annotations.append(JavaAnnotation(name=ann_data))
            else:
                annotations.append(JavaAnnotation.from_dict(ann_data))
        
        return cls(
            name=data['name'],
            visibility=data['visibility'],
            modifiers=data.get('modifiers', []),
            return_type=data.get('return_type'),
            parameters=parameters,
            exceptions=data.get('exceptions', []),
            annotations=annotations,
            complexity_score=data.get('complexity_score'),
            line_count=data.get('line_count'),
            sql_statements=[SQLStatement.from_dict(stmt) for stmt in data.get('sql_statements', [])],
            sql_stored_procedures=[SQLStoredProcedureDetails.from_dict(sp) for sp in data.get('sql_stored_procedures', [])]
        )


@dataclass
class JavaField:
    """Represents a Java field."""
    name: str
    type: str
    visibility: str
    modifiers: List[str] = field(default_factory=list)
    annotations: List[JavaAnnotation] = field(default_factory=list)
    initial_value: Optional[str] = None
    
    def is_static(self) -> bool:
        """Check if field is static."""
        return 'static' in self.modifiers
    
    def is_final(self) -> bool:
        """Check if field is final."""
        return 'final' in self.modifiers
    
    def has_annotation(self, annotation_name: str) -> bool:
        """Check if field has specific annotation."""
        return any(ann.name == annotation_name for ann in self.annotations)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'name': self.name,
            'type': self.type,
            'visibility': self.visibility,
            'modifiers': self.modifiers,
            'annotations': [ann.to_dict() for ann in self.annotations],
            'initial_value': self.initial_value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JavaField':
        """Create instance from dictionary."""
        annotations = []
        for ann_data in data.get('annotations', []):
            if isinstance(ann_data, str):
                annotations.append(JavaAnnotation(name=ann_data))
            else:
                annotations.append(JavaAnnotation.from_dict(ann_data))
        
        return cls(
            name=data['name'],
            type=data['type'],
            visibility=data['visibility'],
            modifiers=data.get('modifiers', []),
            annotations=annotations,
            initial_value=data.get('initial_value')
        )


@dataclass
class JavaClass:
    """Represents a Java class."""
    package_name: str
    class_name: str
    class_type: str  # class, interface, enum, annotation
    superclass: Optional[str] = None
    interfaces: List[str] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)
    annotations: List[JavaAnnotation] = field(default_factory=list)
    is_inner_class: bool = False
    enclosing_class: Optional[str] = None
    methods: List[JavaMethod] = field(default_factory=list)
    fields: List[JavaField] = field(default_factory=list)
    inner_classes: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    entity_mapping: Optional[EntityMappingDetails] = None

    def get_full_name(self) -> str:
        """Get fully qualified class name."""
        return f"{self.package_name}.{self.class_name}" if self.package_name else self.class_name
    
    def is_interface(self) -> bool:
        """Check if this is an interface."""
        return self.class_type == 'interface'
    
    def is_enum(self) -> bool:
        """Check if this is an enum."""
        return self.class_type == 'enum'
    
    def has_annotation(self, annotation_name: str) -> bool:
        """Check if class has specific annotation."""
        return any(ann.name == annotation_name for ann in self.annotations)
    
    def get_public_methods(self) -> List[JavaMethod]:
        """Get all public methods."""
        return [m for m in self.methods if m.is_public()]
    
    def get_annotated_methods(self, annotation_name: str) -> List[JavaMethod]:
        """Get methods with specific annotation."""
        return [m for m in self.methods if m.has_annotation(annotation_name)]
    
    def get_annotated_fields(self, annotation_name: str) -> List[JavaField]:
        """Get fields with specific annotation."""
        return [f for f in self.fields if f.has_annotation(annotation_name)]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'package_name': self.package_name,
            'class_name': self.class_name,
            'class_type': self.class_type,
            'superclass': self.superclass,
            'interfaces': self.interfaces,
            'modifiers': self.modifiers,
            'annotations': [ann.to_dict() for ann in self.annotations],
            'is_inner_class': self.is_inner_class,
            'enclosing_class': self.enclosing_class,
            'methods': [m.to_dict() for m in self.methods],
            'fields': [f.to_dict() for f in self.fields],
            'inner_classes': self.inner_classes,
            'imports': self.imports,
            'dependencies': self.dependencies,
            'entity_mapping': self.entity_mapping.to_dict() if self.entity_mapping else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JavaClass':
        """Create instance from dictionary."""
        annotations = []
        for ann_data in data.get('annotations', []):
            if isinstance(ann_data, str):
                annotations.append(JavaAnnotation(name=ann_data))
            else:
                annotations.append(JavaAnnotation.from_dict(ann_data))
        
        methods = []
        for method_data in data.get('methods', []):
            methods.append(JavaMethod.from_dict(method_data))
        
        fields = []
        for field_data in data.get('fields', []):
            fields.append(JavaField.from_dict(field_data))
        
        return cls(
            package_name=data.get('package_name', ''),
            class_name=data['class_name'],
            class_type=data.get('class_type', 'class'),
            superclass=data.get('superclass'),
            interfaces=data.get('interfaces', []),
            modifiers=data.get('modifiers', []),
            annotations=annotations,
            is_inner_class=data.get('is_inner_class', False),
            enclosing_class=data.get('enclosing_class'),
            methods=methods,
            fields=fields,
            inner_classes=data.get('inner_classes', []),
            imports=data.get('imports', []),
            dependencies=data.get('dependencies', []),
            entity_mapping=EntityMappingDetails.from_dict(data['entity_mapping']) if data.get('entity_mapping') else None
        )


@dataclass
class JavaDetails(FileDetailsBase):
    """Java file details containing class information."""
    classes: List[JavaClass] = field(default_factory=list)
    code_mappings: List[CodeMapping] = field(default_factory=list)
    detected_layer: Optional[LayerType] = None
    architectural_pattern: Optional[ArchitecturalLayerType] = None
    framework_hints: List[str] = field(default_factory=list)
    requires_security_roles: List[str] = field(default_factory=list)
    rest_endpoints: List[Dict[str, Any]] = field(default_factory=list)
    aop_pointcuts: List[Dict[str, Any]] = field(default_factory=list)
    
    # Manager pattern specific fields
    factory_methods: List[Dict[str, Any]] = field(default_factory=list)
    manager_interfaces: List[Dict[str, Any]] = field(default_factory=list)
    manager_usage: List[Dict[str, Any]] = field(default_factory=list)
    orchestration_info: Dict[str, Any] = field(default_factory=dict)
    is_manager_class: bool = False
    is_orchestrator_class: bool = False
    
    def get_file_type(self) -> str:
        """Return the file type identifier."""
        return "java"
    
    def get_primary_class(self) -> Optional[JavaClass]:
        """Get the primary (non-inner) class."""
        for java_class in self.classes:
            if not java_class.is_inner_class:
                return java_class
        return self.classes[0] if self.classes else None
    
    def get_inner_classes(self) -> List[JavaClass]:
        """Get all inner classes."""
        return [c for c in self.classes if c.is_inner_class]
    
    def has_annotation(self, annotation_name: str) -> bool:
        """Check if any class has specific annotation."""
        return any(c.has_annotation(annotation_name) for c in self.classes)
    
    def get_detected_layer_name(self) -> str:
        """Get the detected layer name as string."""
        return self.detected_layer.value if self.detected_layer else "Unknown"
    
    def get_architectural_pattern_name(self) -> str:
        """Get the architectural pattern name as string."""
        return self.architectural_pattern.value if self.architectural_pattern else "unknown"
    
    def has_framework_hint(self, framework: str) -> bool:
        """Check if a specific framework hint is present."""
        return framework.lower() in [hint.lower() for hint in self.framework_hints]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            'classes': [c.to_dict() for c in self.classes],
            'code_mappings': [cm.to_dict() for cm in self.code_mappings],
            'framework_hints': self.framework_hints,
            'requires_security_roles': self.requires_security_roles,
            'rest_endpoints': self.rest_endpoints,
            'aop_pointcuts': self.aop_pointcuts,
            'factory_methods': self.factory_methods,
            'manager_interfaces': self.manager_interfaces,
            'manager_usage': self.manager_usage,
            'orchestration_info': self.orchestration_info,
            'is_manager_class': self.is_manager_class,
            'is_orchestrator_class': self.is_orchestrator_class
        }
        
        # Add layer information if present
        if self.detected_layer:
            result['detected_layer'] = self.detected_layer.value
        if self.architectural_pattern:
            result['architectural_pattern'] = self.architectural_pattern.value
            
        return result
    
    @classmethod
    def from_dict(cls, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> 'JavaDetails':
        """Create instance from dictionary."""
        classes = []
        code_mappings = []
        detected_layer = None
        architectural_pattern = None
        framework_hints: List[str] = []
        requires_security_roles: List[str] = []
        rest_endpoints: List[Dict[str, Any]] = []
        aop_pointcuts: List[Dict[str, Any]] = []
        factory_methods: List[Dict[str, Any]] = []
        manager_interfaces: List[Dict[str, Any]] = []
        manager_usage: List[Dict[str, Any]] = []
        orchestration_info: Dict[str, Any] = {}
        is_manager_class: bool = False
        is_orchestrator_class: bool = False
        
        # Handle both single class and multiple classes
        if isinstance(data, list):
            # Direct list of class data
            for class_data in data:
                if isinstance(class_data, dict):
                    classes.append(JavaClass.from_dict(class_data))
        elif isinstance(data, dict):
            if 'classes' in data:
                # Wrapped in classes array
                for class_data in data['classes']:
                    if isinstance(class_data, dict):
                        classes.append(JavaClass.from_dict(class_data))
            else:
                # Single class data
                classes.append(JavaClass.from_dict(data))
            
            # Handle code_mappings if present
            if 'code_mappings' in data:
                for mapping_data in data['code_mappings']:
                    if isinstance(mapping_data, dict):
                        code_mappings.append(CodeMapping.from_dict(mapping_data))
            
            # Handle layer information if present
            if 'detected_layer' in data:
                try:
                    detected_layer = LayerType(data['detected_layer'])
                except ValueError:
                    detected_layer = None
            
            if 'architectural_pattern' in data:
                try:
                    architectural_pattern = ArchitecturalLayerType(data['architectural_pattern'])
                except ValueError:
                    architectural_pattern = None
            
            # Handle framework hints and new fields
            framework_hints = data.get('framework_hints', [])
            requires_security_roles = data.get('requires_security_roles', [])
            rest_endpoints = data.get('rest_endpoints', [])
            aop_pointcuts = data.get('aop_pointcuts', [])
            factory_methods = data.get('factory_methods', [])
            manager_interfaces = data.get('manager_interfaces', [])
            manager_usage = data.get('manager_usage', [])
            orchestration_info = data.get('orchestration_info', {})
            is_manager_class = data.get('is_manager_class', False)
            is_orchestrator_class = data.get('is_orchestrator_class', False)
        
        return cls(
            classes=classes, 
            code_mappings=code_mappings,
            detected_layer=detected_layer,
            architectural_pattern=architectural_pattern,
            framework_hints=framework_hints,
            requires_security_roles=requires_security_roles,
            rest_endpoints=rest_endpoints,
            aop_pointcuts=aop_pointcuts,
            factory_methods=factory_methods,
            manager_interfaces=manager_interfaces,
            manager_usage=manager_usage,
            orchestration_info=orchestration_info,
            is_manager_class=is_manager_class,
            is_orchestrator_class=is_orchestrator_class
        )

