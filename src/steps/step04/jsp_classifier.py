"""
Enhanced JSP Classification for Step04.

This module extends the existing Step04 linker to add JSP type classification
and improved relationship extraction.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from domain.jsp_details import JspDetails
from steps.step04.models import Entity as Step04Entity


class JspClassifier:
    """Classify JSPs into functional types based on content and naming patterns."""
    
    def __init__(self):
        self.menu_patterns = [
            'menu', 'nav', 'navigation', 'tabmenu', 'sidebar', 'header', 'footer'
        ]
        self.fragment_patterns = [
            'fragment', 'include', 'inc_', '_inc', 'header', 'footer', 'common'
        ]
        self.error_patterns = [
            'error', 'exception', 'blank', 'logout', 'login', 'unauthorized'
        ]
        self.admin_patterns = [
            'setup', 'admin', 'config', 'management', 'settings'
        ]
        self.report_patterns = [
            'report', 'dashboard', 'summary', 'chart', 'graph'
        ]
        self.dialog_patterns = [
            'dialog', 'popup', 'modal', 'overlay'
        ]
    
    def classify_jsp(self, file_path: str, details: Optional[JspDetails] = None) -> Dict[str, Any]:
        """
        Classify a JSP file into functional categories.
        
        Returns:
            Dict with classification information including:
            - jsp_function_type: primary functional classification
            - is_component: whether this is a reusable component
            - ui_complexity: estimated complexity (simple/medium/complex)
            - business_domain: domain hint from path structure
        """
        classification = {
            'jsp_function_type': 'business_screen',  # default
            'is_component': False,
            'ui_complexity': 'medium',
            'business_domain': None,
            'navigation_role': None,
            'has_forms': False,
            'has_security': False,
            'confidence': 0.7  # base confidence
        }
        
        # Extract file info
        file_name = Path(file_path).name.lower() if file_path else ''
        path_segments = file_path.split('/') if file_path else []
        
        # Extract business domain from path structure
        if '/jsp/' in file_path:
            jsp_index = path_segments.index('jsp') if 'jsp' in path_segments else -1
            if jsp_index >= 0 and jsp_index + 1 < len(path_segments):
                classification['business_domain'] = path_segments[jsp_index + 1]
        
        # Classify based on file name patterns
        confidence_boost = 0.0
        
        # Menu/Navigation classification
        if any(pattern in file_name for pattern in self.menu_patterns):
            classification['jsp_function_type'] = 'menu_navigation'
            classification['is_component'] = True
            classification['navigation_role'] = 'primary_menu'
            confidence_boost = 0.2
        
        # Fragment/Include classification  
        elif any(pattern in file_name for pattern in self.fragment_patterns):
            classification['jsp_function_type'] = 'fragment_include'
            classification['is_component'] = True
            classification['ui_complexity'] = 'simple'
            confidence_boost = 0.25
        
        # Error/Utility classification
        elif any(pattern in file_name for pattern in self.error_patterns):
            classification['jsp_function_type'] = 'error_utility'
            classification['ui_complexity'] = 'simple'
            confidence_boost = 0.3
        
        # Admin/Setup classification
        elif any(pattern in file_name for pattern in self.admin_patterns):
            classification['jsp_function_type'] = 'admin_setup'
            confidence_boost = 0.15
        
        # Report/Dashboard classification
        elif any(pattern in file_name for pattern in self.report_patterns):
            classification['jsp_function_type'] = 'report_dashboard'
            confidence_boost = 0.15
        
        # Dialog/Modal classification
        elif any(pattern in file_name for pattern in self.dialog_patterns):
            classification['jsp_function_type'] = 'dialog_modal'
            classification['is_component'] = True
            confidence_boost = 0.2
        
        # Use JSP details for enhanced classification
        if details:
            # Check for forms
            if details.has_forms():
                classification['has_forms'] = True
                if classification['jsp_function_type'] == 'business_screen':
                    confidence_boost += 0.1
            
            # Check for security patterns
            if details.pattern_hits and details.pattern_hits.security:
                classification['has_security'] = True
                confidence_boost += 0.1
            
            # Check for menu-specific patterns
            if details.pattern_hits and details.pattern_hits.menu:
                if classification['jsp_function_type'] == 'business_screen':
                    classification['jsp_function_type'] = 'menu_navigation'
                    classification['is_component'] = True
                    confidence_boost += 0.15
            
            # Analyze UI complexity based on content
            total_elements = 0
            if details.jsp_tags:
                total_elements += len(details.jsp_tags)
            if details.form_elements:
                total_elements += len(details.form_elements) * 3  # forms are complex
            if details.embedded_java:
                total_elements += len(details.embedded_java) * 2  # java adds complexity
            
            if total_elements < 5:
                classification['ui_complexity'] = 'simple'
            elif total_elements > 20:
                classification['ui_complexity'] = 'complex'
            
            # Special case: if it has many includes/iframes, it's likely a component
            includes_count = len(details.includes) + len(details.iframes)
            if includes_count > 2:
                classification['is_component'] = True
                confidence_boost += 0.1
        
        # Apply confidence boost
        final_confidence = min(0.95, classification['confidence'] + confidence_boost)
        classification['classification_confidence'] = final_confidence
        
        return classification


def enhance_jsp_entities_with_classification(jsp_entities: Dict[str, Step04Entity], 
                                           step02_inventory) -> Dict[str, Step04Entity]:
    """
    Enhance existing JSP entities with functional classification.
    
    This function modifies JSP entities in-place to add classification attributes
    without breaking existing functionality.
    """
    classifier = JspClassifier()
    
    # Import here to avoid circular dependencies
    from steps.step02.source_inventory_query import SourceInventoryQuery
    
    enhanced_entities = {}
    
    for jsp_id, entity in jsp_entities.items():
        # Get file details from Step02 inventory
        file_path = entity.attributes.get('file_path') if entity.attributes else None
        details = None
        
        if file_path:
            try:
                # Query for JSP details
                query = SourceInventoryQuery(step02_inventory).files().detail_type("jsp")
                if file_path.startswith('/'):
                    # Try path_endswith for logical paths
                    clean_path = file_path[1:] if file_path.startswith('/') else file_path
                    query = query.path_endswith(clean_path)
                else:
                    query = query.path_contains(file_path)
                
                result = query.execute()
                if result.total_count > 0:
                    file_info = result.items[0]
                    if isinstance(file_info.details, JspDetails):
                        details = file_info.details
            except Exception:
                # Robust - continue without details if query fails
                pass
        
        # Classify the JSP
        if file_path:
            classification = classifier.classify_jsp(file_path, details)
        else:
            # Default classification for JSPs without file paths
            classification = {
                'jsp_function_type': 'business_screen',
                'is_component': False,
                'ui_complexity': 'medium',
                'business_domain': None,
                'navigation_role': None,
                'has_forms': False,
                'has_security': False,
                'confidence': 0.5
            }
        
        # Create enhanced entity with classification attributes
        enhanced_attributes = dict(entity.attributes) if entity.attributes else {}
        enhanced_attributes.update({
            'jsp_function_type': classification['jsp_function_type'],
            'is_component': classification['is_component'],
            'ui_complexity': classification['ui_complexity'], 
            'has_forms': classification['has_forms'],
            'has_security': classification['has_security'],
            'classification_confidence': classification['confidence']
        })
        
        # Add optional attributes
        if classification['business_domain']:
            enhanced_attributes['business_domain'] = classification['business_domain']
        if classification['navigation_role']:
            enhanced_attributes['navigation_role'] = classification['navigation_role']
        
        # Create new entity with enhanced attributes
        enhanced_entity = Step04Entity(
            id=entity.id,
            type=entity.type,
            name=entity.name,
            attributes=enhanced_attributes,
            source_refs=entity.source_refs
        )
        
        enhanced_entities[jsp_id] = enhanced_entity
    
    return enhanced_entities
