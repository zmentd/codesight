"""
JSP-specific file details for source inventory.

This module contains classes for representing JSP/HTML analysis results,
including forms, fields, buttons, and JSP-specific elements.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

# Add import for CodeMapping used by JSP code mappings
from .config_details import CodeMapping
from .source_inventory import FileDetailsBase


# ========================
# New enums aligning reader
# ========================
class JspDirectiveType(Enum):
    PAGE = "page"
    TAGLIB = "taglib"
    INCLUDE = "include"
    OTHER = "other"


class EmbeddedJavaType(Enum):
    SCRIPTLET = "scriptlet"
    EXPRESSION = "expression"


# =============================
# Existing domain (kept intact)
# =============================
@dataclass
class FormButton:
    """Represents a form button element."""
    name: str
    type: str
    onclick: Optional[str] = None
    css_classes: List[str] = field(default_factory=list)
    attributes: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'name': self.name,
            'type': self.type,
            'onclick': self.onclick,
            'css_classes': self.css_classes,
            'attributes': self.attributes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FormButton':
        """Create instance from dictionary."""
        return cls(
            name=data.get('name', ''),
            type=data.get('type', 'button'),
            onclick=data.get('onclick'),
            css_classes=data.get('css_classes', []),
            attributes=data.get('attributes', {})
        )


@dataclass
class FormField:
    """Represents a form field element."""
    name: str
    type: str
    required: bool = False
    validation_attributes: Dict[str, Any] = field(default_factory=dict)
    default_value: Optional[str] = None
    maxlength: Optional[int] = None
    css_classes: List[str] = field(default_factory=list)
    options: List[Dict[str, str]] = field(default_factory=list)  # For select elements
    
    def is_select(self) -> bool:
        """Check if field is a select element."""
        return self.type == 'select'
    
    def is_text_input(self) -> bool:
        """Check if field is a text input."""
        return self.type in ('text', 'email', 'password', 'tel', 'url')
    
    def has_validation(self) -> bool:
        """Check if field has validation attributes."""
        return bool(self.validation_attributes) or self.required
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            'name': self.name,
            'type': self.type,
            'required': self.required,
            'validation_attributes': self.validation_attributes,
            'default_value': self.default_value,
            'css_classes': self.css_classes
        }
        if self.maxlength is not None:
            result['maxlength'] = self.maxlength
        if self.options:
            result['options'] = self.options
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FormField':
        """Create instance from dictionary."""
        return cls(
            name=data.get('name', ''),
            type=data.get('type', 'text'),
            required=data.get('required', False),
            validation_attributes=data.get('validation_attributes', {}),
            default_value=data.get('default_value'),
            maxlength=data.get('maxlength'),
            css_classes=data.get('css_classes', []),
            options=data.get('options', [])
        )


@dataclass
class HtmlForm:
    """Represents an HTML form."""
    name: str
    action: str
    method: str = 'GET'
    fields: List[FormField] = field(default_factory=list)
    buttons: List[FormButton] = field(default_factory=list)
    css_classes: List[str] = field(default_factory=list)
    id: Optional[str] = None
    
    def get_required_fields(self) -> List[FormField]:
        """Get all required fields."""
        return [f for f in self.fields if f.required]
    
    def get_field_by_name(self, name: str) -> Optional[FormField]:
        """Get field by name."""
        for fld in self.fields:
            if fld.name == name:
                return fld
        return None
    
    def has_validation(self) -> bool:
        """Check if form has any field validation."""
        return any(f.has_validation() for f in self.fields)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            'name': self.name,
            'action': self.action,
            'method': self.method,
            'fields': [f.to_dict() for f in self.fields],
            'buttons': [b.to_dict() for b in self.buttons],
            'css_classes': self.css_classes
        }
        if self.id:
            result['id'] = self.id
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HtmlForm':
        """Create instance from dictionary."""
        fields = []
        for field_data in data.get('fields', []):
            fields.append(FormField.from_dict(field_data))
        
        buttons = []
        for button_data in data.get('buttons', []):
            buttons.append(FormButton.from_dict(button_data))
        
        return cls(
            name=data.get('name', ''),
            action=data.get('action', ''),
            method=data.get('method', 'GET'),
            fields=fields,
            buttons=buttons,
            css_classes=data.get('css_classes', []),
            id=data.get('id')
        )


@dataclass
class JspElement:
    """Represents a JSP-specific element (tag, scriptlet, etc.)."""
    tag: str
    attributes: Dict[str, str] = field(default_factory=dict)
    content: Optional[str] = None
    element_type: str = 'tag'  # tag, scriptlet, directive, expression
    
    def is_custom_tag(self) -> bool:
        """Check if this is a custom JSP tag."""
        return ':' in self.tag
    
    def get_tag_prefix(self) -> Optional[str]:
        """Get tag prefix (e.g., 'c' from 'c:forEach')."""
        if ':' in self.tag:
            return self.tag.split(':', 1)[0]
        return None
    
    def get_tag_name(self) -> str:
        """Get tag name without prefix."""
        if ':' in self.tag:
            return self.tag.split(':', 1)[1]
        return self.tag
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'tag': self.tag,
            'attributes': self.attributes,
            'content': self.content,
            'element_type': self.element_type
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JspElement':
        """Create instance from dictionary."""
        return cls(
            tag=data.get('tag', ''),
            attributes=data.get('attributes', {}),
            content=data.get('content'),
            element_type=data.get('element_type', 'tag')
        )


@dataclass
class ScreenElements:
    """Container for screen-related elements."""
    forms: List[HtmlForm] = field(default_factory=list)
    jsp_elements: List[JspElement] = field(default_factory=list)
    
    def get_forms_by_method(self, method: str) -> List[HtmlForm]:
        """Get forms filtered by HTTP method."""
        return [f for f in self.forms if f.method.upper() == method.upper()]
    
    def get_jsp_elements_by_tag(self, tag: str) -> List[JspElement]:
        """Get JSP elements filtered by tag name."""
        return [e for e in self.jsp_elements if e.tag == tag]
    
    def get_custom_jsp_tags(self) -> List[JspElement]:
        """Get all custom JSP tags."""
        return [e for e in self.jsp_elements if e.is_custom_tag()]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'forms': [f.to_dict() for f in self.forms],
            'jsp_elements': [e.to_dict() for e in self.jsp_elements]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScreenElements':
        """Create instance from dictionary."""
        forms = []
        for form_data in data.get('forms', []):
            forms.append(HtmlForm.from_dict(form_data))
        
        jsp_elements = []
        for element_data in data.get('jsp_elements', []):
            jsp_elements.append(JspElement.from_dict(element_data))
        
        return cls(
            forms=forms,
            jsp_elements=jsp_elements
        )


# ======================================
# New dataclasses aligning reader output
# ======================================
@dataclass
class JspDirective:
    type: str  # keep raw string to align with reader; helper available for enum
    attributes: Dict[str, str] = field(default_factory=dict)
    full_text: Optional[str] = None
    
    def as_enum(self) -> JspDirectiveType:
        t = (self.type or '').lower()
        if t == 'page':
            return JspDirectiveType.PAGE
        if t == 'taglib':
            return JspDirectiveType.TAGLIB
        if t == 'include':
            return JspDirectiveType.INCLUDE
        return JspDirectiveType.OTHER
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type,
            'attributes': self.attributes,
            'full_text': self.full_text
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JspDirective':
        return cls(
            type=data.get('type', ''),
            attributes=data.get('attributes', {}),
            full_text=data.get('full_text')
        )


@dataclass
class JspFormInput:
    tag: str
    attributes: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {'tag': self.tag, 'attributes': self.attributes}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JspFormInput':
        return cls(tag=data.get('tag', ''), attributes=data.get('attributes', {}))


@dataclass
class ParsedForm:
    type: str = 'form'
    attributes: Dict[str, str] = field(default_factory=dict)
    inputs: List[JspFormInput] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type,
            'attributes': self.attributes,
            'inputs': [i.to_dict() for i in self.inputs]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParsedForm':
        return cls(
            type=data.get('type', 'form'),
            attributes=data.get('attributes', {}),
            inputs=[JspFormInput.from_dict(i) for i in data.get('inputs', [])]
        )


@dataclass
class JspTagHit:
    tag_name: str
    attributes: Dict[str, str] = field(default_factory=dict)
    full_text: Optional[str] = None
    # New: line spans for evidence
    line: Optional[int] = None
    end_line: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'tag_name': self.tag_name,
            'attributes': self.attributes,
            'full_text': self.full_text,
            'line': self.line,
            'end_line': self.end_line,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JspTagHit':
        return cls(
            tag_name=data.get('tag_name', ''),
            attributes=data.get('attributes', {}),
            full_text=data.get('full_text'),
            line=data.get('line'),
            end_line=data.get('end_line'),
        )


@dataclass
class EmbeddedJavaBlock:
    type: str  # 'scriptlet' | 'expression' (align with reader)
    code: str
    full_text: Optional[str] = None
    # New: line spans for evidence
    line: Optional[int] = None
    end_line: Optional[int] = None
    
    def as_enum(self) -> EmbeddedJavaType:
        return EmbeddedJavaType(self.type) if self.type in (e.value for e in EmbeddedJavaType) else EmbeddedJavaType.SCRIPTLET
    
    def to_dict(self) -> Dict[str, Any]:
        return {'type': self.type, 'code': self.code, 'full_text': self.full_text, 'line': self.line, 'end_line': self.end_line}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmbeddedJavaBlock':
        return cls(type=data.get('type', 'scriptlet'), code=data.get('code', ''), full_text=data.get('full_text'), line=data.get('line'), end_line=data.get('end_line'))


@dataclass
class ElExpressionEntry:
    expression: str
    full_text: Optional[str] = None
    # New: line spans for evidence
    line: Optional[int] = None
    end_line: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {'expression': self.expression, 'full_text': self.full_text, 'line': self.line, 'end_line': self.end_line}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ElExpressionEntry':
        return cls(expression=data.get('expression', ''), full_text=data.get('full_text'), line=data.get('line'), end_line=data.get('end_line'))


@dataclass
class PatternHits:
    legacy: List[str] = field(default_factory=list)
    security: List[str] = field(default_factory=list)
    menu: List[str] = field(default_factory=list)
    service: List[str] = field(default_factory=list)
    tiles: List[str] = field(default_factory=list)
    custom_tag_prefixes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'legacy': self.legacy,
            'security': self.security,
            'menu': self.menu,
            'service': self.service,
            'tiles': self.tiles,
            'custom_tag_prefixes': self.custom_tag_prefixes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PatternHits':
        return cls(
            legacy=data.get('legacy', []),
            security=data.get('security', []),
            menu=data.get('menu', []),
            service=data.get('service', []),
            tiles=data.get('tiles', []),
            custom_tag_prefixes=data.get('custom_tag_prefixes', []),
        )


# New: iframe reference domain
@dataclass
class IframeRef:
    src: Optional[str] = None
    attributes: Dict[str, str] = field(default_factory=dict)
    full_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'src': self.src,
            'attributes': self.attributes,
            'full_text': self.full_text,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IframeRef':
        return cls(
            src=data.get('src'),
            attributes=data.get('attributes', {}),
            full_text=data.get('full_text'),
        )


# ======================================
# JspDetails with merged structural data
# ======================================
@dataclass
class JspDetails(FileDetailsBase):
    """JSP file details containing screen elements and structure."""
    # Convenience/legacy fields
    screen_elements: Optional[ScreenElements] = None
    tag_libraries: List[str] = field(default_factory=list)  # Tag library URIs
    includes: List[str] = field(default_factory=list)  # Included files
    page_directives: Dict[str, str] = field(default_factory=dict)

    # Merged structural fields (from former JspStructuralData)
    file_path: Optional[str] = None
    page_type: Optional[str] = None
    directives: List[JspDirective] = field(default_factory=list)
    form_elements: List[ParsedForm] = field(default_factory=list)
    jsp_tags: List[JspTagHit] = field(default_factory=list)
    embedded_java: List[EmbeddedJavaBlock] = field(default_factory=list)
    el_expressions: List[ElExpressionEntry] = field(default_factory=list)
    html_elements: Dict[str, int] = field(default_factory=dict)
    pattern_hits: PatternHits = field(default_factory=PatternHits)
    # New: iframe references detected in page
    iframes: List[IframeRef] = field(default_factory=list)
    # New: cross-file relationships captured as CodeMappings (includes, forwards, iframes, redirects)
    code_mappings: List[CodeMapping] = field(default_factory=list)
    
    def get_file_type(self) -> str:
        """Return the file type identifier."""
        return "jsp"
    
    def has_forms(self) -> bool:
        """Check if JSP has any forms."""
        if self.screen_elements is not None and len(self.screen_elements.forms) > 0:
            return True
        if self.form_elements:
            return True
        return False
    
    def get_form_count(self) -> int:
        """Get total number of forms."""
        if self.screen_elements and self.screen_elements.forms:
            return len(self.screen_elements.forms)
        if self.form_elements:
            return len(self.form_elements)
        return 0
    
    def uses_tag_library(self, prefix: str) -> bool:
        """Check if JSP uses specific tag library prefix."""
        if self.screen_elements and any(e.get_tag_prefix() == prefix for e in self.screen_elements.jsp_elements):
            return True
        # Check jsp_tags tag_name prefix presence
        return any(':' in t.tag_name and t.tag_name.split(':', 1)[0] == prefix for t in self.jsp_tags)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            'tag_libraries': self.tag_libraries,
            'includes': self.includes,
            'page_directives': self.page_directives,
            # merged structural fields
            'file_path': self.file_path,
            'page_type': self.page_type,
            'directives': [d.to_dict() for d in self.directives],
            'form_elements': [f.to_dict() for f in self.form_elements],
            'jsp_tags': [t.to_dict() for t in self.jsp_tags],
            'embedded_java': [e.to_dict() for e in self.embedded_java],
            'el_expressions': [e.to_dict() for e in self.el_expressions],
            'html_elements': self.html_elements,
            'pattern_hits': self.pattern_hits.to_dict(),
            'iframes': [i.to_dict() for i in self.iframes],
            # New: code mappings
            'code_mappings': [cm.to_dict() for cm in self.code_mappings],
        }
        if self.screen_elements:
            result['screen_elements'] = self.screen_elements.to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JspDetails':
        """Create instance from dictionary."""
        screen_elements = None
        if 'screen_elements' in data:
            screen_elements = ScreenElements.from_dict(data['screen_elements'])

        return cls(
            screen_elements=screen_elements,
            tag_libraries=data.get('tag_libraries', []),
            includes=data.get('includes', []),
            page_directives=data.get('page_directives', {}),
            file_path=data.get('file_path'),
            page_type=data.get('page_type'),
            directives=[JspDirective.from_dict(d) for d in data.get('directives', [])],
            form_elements=[ParsedForm.from_dict(f) for f in data.get('form_elements', [])],
            jsp_tags=[JspTagHit.from_dict(t) for t in data.get('jsp_tags', [])],
            embedded_java=[EmbeddedJavaBlock.from_dict(e) for e in data.get('embedded_java', [])],
            el_expressions=[ElExpressionEntry.from_dict(e) for e in data.get('el_expressions', [])],
            html_elements=data.get('html_elements', {}),
            pattern_hits=PatternHits.from_dict(data.get('pattern_hits', {})),
            iframes=[IframeRef.from_dict(i) for i in data.get('iframes', [])],
            code_mappings=[CodeMapping.from_dict(cm) for cm in data.get('code_mappings', [])],
        )
