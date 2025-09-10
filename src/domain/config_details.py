"""
Configuration file details for source inventory.

This module contains classes for representing configuration mappings and relationships
extracted from Struts, web.xml, properties, and other enterprise configuration files.
Focus is on code-to-code mappings, validation rules, and error handling patterns
rather than configuration file structure.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from .source_inventory import FileDetailsBase


class SemanticCategory(Enum):
    """Semantic categories for code-to-code relationships across frameworks."""
    ENTRY_POINT = "entry_point"        # External identifier → Code: "action" (Struts actions), "servlet" (Servlet mappings), "mbean" (JMX MBean definitions)
    METHOD_CALL = "method_call"        # Code → Code invocation
    DATA_ACCESS = "data_access"        # Code → Database/File/API
    VIEW_RENDER = "view_render"        # Code → UI/Template: "forward" (Struts forwards to JSP), "template_reference" (Tiles template references)
    CROSS_CUTTING = "cross_cutting"    # Affects multiple flows: "filter" (Servlet filters), "interceptor" (Struts interceptors), "interceptor_stack" (Struts interceptor stacks)
    INHERITANCE = "inheritance"        # Extension relationships: "inheritance" (Tiles template inheritance)
    COMPOSITION = "composition"        # Component inclusion: "component" (Tiles components), "template" (Tiles template definitions), "service_dependency" (JMX service dependencies)


@dataclass
class DeterministicForward:
    name: str  # Name of the forward (e.g., "success", "error")
    path: str  # Path to the target resource (e.g., JSP page)

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary representation."""
        return {
            'name': self.name,
            'path': self.path
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'DeterministicForward':
        """Create instance from dictionary."""
        return cls(
            name=data.get('name', ''),
            path=data.get('path', '')
        )


class CodeMappingBase(ABC):
    """Abstract base class for file-specific details."""
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodeMappingBase':
        """Create instance from dictionary."""


@dataclass
class CodeMapping(CodeMappingBase):
    """Represents a code-to-code mapping (URL → Class, Action → JSP, etc.)."""
    from_reference: str  # URL pattern, action name, servlet name
    to_reference: str    # Java class name, JSP path, method name
    mapping_type: str    # "action", "servlet", "forward", "validation", "exception"
    framework: str       # "struts_1x", "struts_2x", "servlet", "spring"
    semantic_category: Optional[SemanticCategory] = None  # Semantic classification
    forwards: Optional[List[DeterministicForward]] = None  # Result names for Struts actions
    attributes: Dict[str, str] = field(default_factory=dict)  # HTTP method, parameters, etc.
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'from_reference': self.from_reference,
            'to_reference': self.to_reference,
            'mapping_type': self.mapping_type,
            'framework': self.framework,
            'semantic_category': self.semantic_category.value if self.semantic_category else None,
            'forwards': [f.to_dict() for f in self.forwards] if self.forwards else None,
            'attributes': self.attributes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodeMapping':
        """Create instance from dictionary."""
        forwards_data = data.get('forwards')
        forwards = None
        if forwards_data:
            if isinstance(forwards_data, list):
                forwards = [DeterministicForward.from_dict(f) for f in forwards_data]
            else:
                # Handle legacy single forward case
                forwards = [DeterministicForward.from_dict(forwards_data)]
        
        # Handle semantic_category
        semantic_category = None
        if data.get('semantic_category'):
            try:
                semantic_category = SemanticCategory(data['semantic_category'])
            except ValueError:
                # Handle invalid enum values gracefully
                semantic_category = None
        
        return cls(
            from_reference=data.get('from_reference', ''),
            to_reference=data.get('to_reference', ''),
            mapping_type=data.get('mapping_type', 'unknown'),
            framework=data.get('framework', 'unknown'),
            semantic_category=semantic_category,
            forwards=forwards,
            attributes=data.get('attributes', {})
        )


@dataclass
class CodeMappingGroup(CodeMappingBase):
    """Represents a group of related code mappings."""
    group_name: str
    namespace: Optional[str] = None
    extends: Optional[str] = None
    mappings: List[CodeMapping] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'group_name': self.group_name,
            'namespace': self.namespace,
            'extends': self.extends,
            'mappings': [m.to_dict() for m in self.mappings]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodeMappingGroup':
        """Create instance from dictionary."""
        mappings = [CodeMapping.from_dict(m) for m in data.get('mappings', [])]
        return cls(
            group_name=data.get('group_name', ''),
            namespace=data.get('namespace'),
            extends=data.get('extends'),
            mappings=mappings
        )


@dataclass
class ValidationRule:
    """Represents a validation rule that applies to form fields or data."""
    form_name: str              # Form this validation applies to (e.g., "singleTourForm") 
    field_reference: str        # Field name or data element (e.g., "unionId")
    validation_type: str        # "required", "integer", "intRange", "custom", etc.
    validation_value: Optional[str] = None  # Pattern, length limit, custom rule
    validation_variables: Dict[str, str] = field(default_factory=dict)  # min, max, etc.
    error_message_key: Optional[str] = None     # Message resource key (e.g., "tour.unionId")
    validator_class: Optional[str] = None       # Java class handling validation
    validator_method: Optional[str] = None      # Method in validator class
    framework: str = "struts_validator"         # Framework providing validation
    
    # Struts 2 specific fields
    action_method: Optional[str] = None         # Specific action method (e.g., "addTour")
    validation_source: str = "xml"              # "xml", "annotation", "programmatic"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            'form': self.form_name,
            'field': self.field_reference,
            'type': self.validation_type,
            'framework': self.framework,
            'variables': self.validation_variables,
            'validation_source': self.validation_source
        }
        if self.validation_value:
            result['value'] = self.validation_value
        if self.error_message_key:
            result['error_message_key'] = self.error_message_key
        if self.validator_class:
            result['validator_class'] = self.validator_class
        if self.validator_method:
            result['validator_method'] = self.validator_method
        if self.action_method:
            result['action_method'] = self.action_method
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ValidationRule':
        """Create instance from dictionary."""
        return cls(
            form_name=data.get('form', ''),
            field_reference=data.get('field', ''),
            validation_type=data.get('type', 'unknown'),
            validation_value=data.get('value'),
            validation_variables=data.get('variables', {}),
            error_message_key=data.get('error_message_key'),
            validator_class=data.get('validator_class'),
            validator_method=data.get('validator_method'),
            framework=data.get('framework', 'struts_validator'),
            action_method=data.get('action_method'),
            validation_source=data.get('validation_source', 'xml')
        )


@dataclass
class ValidatorDefinition:
    """Represents a global validator definition from validator-rules.xml."""
    validator_name: str         # "required", "intRange", "twofields", etc.
    validator_class: str        # Java class implementing validation
    validator_method: str       # Method to call for validation
    depends_on: List[str] = field(default_factory=list)  # Dependencies on other validators
    default_message_key: Optional[str] = None    # Default error message key
    javascript_function: Optional[str] = None    # Client-side JS validation
    framework: str = "struts_validator"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            'name': self.validator_name,
            'class': self.validator_class,
            'method': self.validator_method,
            'depends_on': self.depends_on,
            'framework': self.framework
        }
        if self.default_message_key:
            result['default_message_key'] = self.default_message_key
        if self.javascript_function:
            result['javascript_function'] = self.javascript_function
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ValidatorDefinition':
        """Create instance from dictionary."""
        return cls(
            validator_name=data.get('name', ''),
            validator_class=data.get('class', ''),
            validator_method=data.get('method', ''),
            depends_on=data.get('depends_on', []),
            default_message_key=data.get('default_message_key'),
            javascript_function=data.get('javascript_function'),
            framework=data.get('framework', 'struts_validator')
        )


@dataclass
class ExceptionMapping:
    """Represents exception handling mapping (Exception → Handler)."""
    exception_type: str         # Java exception class name
    handler_reference: str      # Handler class or action
    error_page: Optional[str] = None      # Error page/view for user
    framework: str = "unknown"            # Framework handling exception
    attributes: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            'exception': self.exception_type,
            'handler': self.handler_reference,
            'framework': self.framework,
            'attributes': self.attributes
        }
        if self.error_page:
            result['error_page'] = self.error_page
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExceptionMapping':
        """Create instance from dictionary."""
        return cls(
            exception_type=data.get('exception', ''),
            handler_reference=data.get('handler', ''),
            error_page=data.get('error_page'),
            framework=data.get('framework', 'unknown'),
            attributes=data.get('attributes', {})
        )


@dataclass
class ConfigurationDetails(FileDetailsBase):
    """Configuration file details focused on mappings and relationships."""
    
    # Core mappings extracted from configuration
    code_mappings: List[CodeMappingBase] = field(default_factory=list)
    validation_rules: List[ValidationRule] = field(default_factory=list)
    validator_definitions: List[ValidatorDefinition] = field(default_factory=list)
    exception_mappings: List[ExceptionMapping] = field(default_factory=list)
    
    # Framework identification
    detected_framework: str = "unknown"  # "struts_1x", "struts_2x", "servlet", "spring"
    framework_version: Optional[str] = None
    
    # Configuration properties (for properties files)
    properties: Dict[str, str] = field(default_factory=dict)
    
    def get_file_type(self) -> str:
        """Return the file type identifier."""
        return "configuration"
    
    def get_action_mappings(self) -> List[CodeMapping]:
        """Get all action mappings (URL → Class)."""
        result = []
        for m in self.code_mappings:
            if isinstance(m, CodeMapping) and m.mapping_type == "action":
                result.append(m)
            elif isinstance(m, CodeMappingGroup):
                # Extract action mappings from groups
                result.extend([cm for cm in m.mappings if cm.mapping_type == "action"])
        return result
    
    def get_forward_mappings(self) -> List[CodeMapping]:
        """Get all forward mappings (Action → JSP)."""
        result = []
        for m in self.code_mappings:
            if isinstance(m, CodeMapping) and m.mapping_type == "forward":
                result.append(m)
            elif isinstance(m, CodeMappingGroup):
                # Extract forward mappings from groups
                result.extend([cm for cm in m.mappings if cm.mapping_type == "forward"])
        return result
    
    def get_servlet_mappings(self) -> List[CodeMapping]:
        """Get all servlet mappings (URL → Servlet Class)."""
        result = []
        for m in self.code_mappings:
            if isinstance(m, CodeMapping) and m.mapping_type == "servlet":
                result.append(m)
            elif isinstance(m, CodeMappingGroup):
                # Extract servlet mappings from groups
                result.extend([cm for cm in m.mappings if cm.mapping_type == "servlet"])
        return result
    
    def get_validation_for_field(self, form_name: str, field_name: str) -> List[ValidationRule]:
        """Get validation rules for specific form field."""
        return [r for r in self.validation_rules 
                if r.form_name == form_name and r.field_reference == field_name]
    
    def get_validation_for_form(self, form_name: str) -> List[ValidationRule]:
        """Get all validation rules for a specific form."""
        return [r for r in self.validation_rules if r.form_name == form_name]
    
    def get_validator_definition(self, validator_name: str) -> Optional[ValidatorDefinition]:
        """Get validator definition by name."""
        for validator in self.validator_definitions:
            if validator.validator_name == validator_name:
                return validator
        return None
    
    def get_form_names(self) -> List[str]:
        """Get all unique form names that have validation rules."""
        return list(set(rule.form_name for rule in self.validation_rules))
    
    def get_exception_handler(self, exception_type: str) -> Optional[ExceptionMapping]:
        """Get handler for specific exception type."""
        for mapping in self.exception_mappings:
            if mapping.exception_type == exception_type:
                return mapping
        return None
    
    def is_struts_config(self) -> bool:
        """Check if this is a Struts configuration."""
        return self.detected_framework in ["struts_1x", "struts_2x"]
    
    def is_web_xml(self) -> bool:
        """Check if this is a web.xml configuration."""
        return self.detected_framework == "servlet"
    
    def is_properties(self) -> bool:
        """Check if this is a properties configuration."""
        return bool(self.properties)
    
    def get_business_domains(self) -> List[str]:
        """Extract business domains from action/mapping names."""
        domains = set()
        for mapping in self.code_mappings:
            # Extract domain hints from action names
            if isinstance(mapping, CodeMapping):
                name = mapping.from_reference.lower()
                if 'user' in name or 'employee' in name:
                    domains.add('User_Management')
                elif 'pay' in name or 'earning' in name or 'transaction' in name:
                    domains.add('Payroll_Management')
                elif 'approver' in name or 'manager' in name:
                    domains.add('Approval_Workflow')
                elif 'holiday' in name or 'timekeeper' in name:
                    domains.add('Time_Management')
            elif isinstance(mapping, CodeMappingGroup):
                # Extract domains from group mappings
                for cm in mapping.mappings:
                    name = cm.from_reference.lower()
                    if 'user' in name or 'employee' in name:
                        domains.add('User_Management')
                    elif 'pay' in name or 'earning' in name or 'transaction' in name:
                        domains.add('Payroll_Management')
                    elif 'approver' in name or 'manager' in name:
                        domains.add('Approval_Workflow')
                    elif 'holiday' in name or 'timekeeper' in name:
                        domains.add('Time_Management')
            # Add more domain detection logic as needed
        return list(domains)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'detected_framework': self.detected_framework,
            'framework_version': self.framework_version,
            'code_mappings': [m.to_dict() for m in self.code_mappings],
            'validation_rules': [r.to_dict() for r in self.validation_rules],
            'validator_definitions': [v.to_dict() for v in self.validator_definitions],
            'exception_mappings': [e.to_dict() for e in self.exception_mappings],
            'properties': self.properties
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConfigurationDetails':
        """Create instance from dictionary."""
        code_mappings: List[CodeMappingBase] = []
        for mapping_data in data.get('code_mappings', []):
            if mapping_data.get('group_name'):
                # This is a CodeMappingGroup
                code_mappings.append(CodeMappingGroup.from_dict(mapping_data))
            else:
                # This is a CodeMapping
                code_mappings.append(CodeMapping.from_dict(mapping_data))
        
        validation_rules = []
        for rule_data in data.get('validation_rules', []):
            validation_rules.append(ValidationRule.from_dict(rule_data))
        
        validator_definitions = []
        for validator_data in data.get('validator_definitions', []):
            validator_definitions.append(ValidatorDefinition.from_dict(validator_data))
        
        exception_mappings = []
        for exception_data in data.get('exception_mappings', []):
            exception_mappings.append(ExceptionMapping.from_dict(exception_data))
        
        return cls(
            detected_framework=data.get('detected_framework', 'unknown'),
            framework_version=data.get('framework_version'),
            code_mappings=code_mappings,
            validation_rules=validation_rules,
            validator_definitions=validator_definitions,
            exception_mappings=exception_mappings,
            properties=data.get('properties', {})
        )
