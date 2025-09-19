"""
Configuration file parser for XML/Properties/YAML configurations.

Handles Spring, web.xml, properties files and other configuration
using existing domain models and LEX utilities.
"""

import re
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
from xml.dom import minidom

try:
    import yaml  # type: ignore[import-untyped]
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from config import Config
from lex.file_classifier import FileClassifier
from lex.rules.java_rules import JavaDetectionRules

from .base_reader import BaseReader, ParseResult


class ConfigurationReader(BaseReader):
    """
    Configuration file parser for various formats.
    
    Handles XML (web.xml, Spring), Properties, YAML configuration files
    using existing LEX classification and rules.
    """
    
    def __init__(self, config: Config) -> None:
        """
        Initialize configuration parser.
        
        Args:
            config: Configuration instance
        """
        super().__init__(config)
        
        # Use existing LEX utilities, passing config
        self.file_classifier = FileClassifier(config)
        self.java_rules = JavaDetectionRules()
        
        # Configuration file patterns
        self.config_file_patterns = {
            'web.xml': r'web\.xml$',
            'struts_config': r'struts.*\.xml$',
            'spring_config': r'(applicationContext|spring).*\.xml$',
            'tiles_config': r'tiles.*\.xml$',
            'jboss_service': r'.*service\.xml$',
            'properties': r'.*\.properties$',
            'yaml': r'.*\.(yml|yaml)$',
            'log_config': r'(log4j|logback).*\.(xml|properties)$',
            'build_config': r'(pom\.xml|build\.xml|build\.gradle)$'
        }
    
    def can_parse(self, file_info: Dict[str, Any]) -> bool:
        """
        Check if this parser can handle configuration files.
        
        Args:
            file_info: File information dictionary
            
        Returns:
            True if file is a configuration file
        """
        file_path = file_info.get("path", "")
        file_type = file_info.get("type", "")
        
        # Check file type classification
        if file_type in ["xml", "properties", "yaml", "yml"]:
            return True
        
        # Check specific configuration patterns
        for config_type, pattern in self.config_file_patterns.items():
            if re.search(pattern, file_path, re.IGNORECASE):
                return True
        
        return False
    
    def parse_file(self, source_path: str, file_path: str) -> ParseResult:
        """
        Parse configuration file and extract structural information.
        
        Args:
            source_path: Path to base source directory
            file_path: Path to the configuration file

        Returns:
            Parse result with configuration structural data
        """
        start_time = time.time()
        
        try:
            content = self.read_file(source_path, file_path)
            # Pre-process content
            self._pre_process_content(content, file_path)
            
            # Determine configuration type
            config_type = self._determine_config_type(file_path, content)
            
            # Extract configuration data based on type
            structural_data = self._extract_config_structure(file_path, content, config_type)
            
            # Detect framework patterns
            framework_hints = self._detect_config_framework_patterns(file_path, content, config_type)
            
            # Calculate confidence
            confidence = self._calculate_confidence(structural_data)
            
            result = ParseResult(
                success=True,
                file_path=file_path,
                language=config_type,
                structural_data=structural_data,
                confidence=confidence,
                framework_hints=framework_hints,
                processing_time=time.time() - start_time
            )
            
            return self._post_process_result(result)
            
        except Exception as e:  # pylint: disable=broad-except
            return self._handle_parse_error(file_path, e)
    
    def _determine_config_type(self, file_path: str, content: str) -> str:
        """
        Determine the type of configuration file.
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            Configuration type string
        """
        file_lower = file_path.lower()
        
        if file_lower.endswith('.xml'):
            if 'web.xml' in file_lower:
                return 'web_xml'
            elif 'validator-rules.xml' in file_lower:
                return 'validator_rules_xml'
            elif 'validation.xml' in file_lower:
                return 'validation_xml'
            elif 'tiles' in file_lower and file_lower.endswith('.xml'):
                return 'tiles_xml'
            elif 'struts' in file_lower and file_lower.endswith('.xml'):
                return 'struts_xml'
            elif file_lower.endswith('service.xml') or 'jboss-service.xml' in file_lower:
                return 'jboss_service_xml'
            elif any(spring_hint in content for spring_hint in ['<beans', 'spring-', 'applicationContext']):
                return 'spring_xml'
            elif any(log_hint in content for log_hint in ['<configuration', 'log4j', 'logback']):
                return 'log_config_xml'
            elif 'pom.xml' in file_lower:
                return 'maven_pom'
            elif 'build.xml' in file_lower:
                return 'ant_build'
            # Check content for validation files
            elif '<form-validation>' in content and '<global>' in content and '<validator' in content:
                return 'validator_rules_xml'
            elif '<form-validation>' in content and '<formset>' in content:
                return 'validation_xml'
            else:
                return 'xml_config'
        elif file_lower.endswith('.properties'):
            return 'properties'
        elif file_lower.endswith(('.yml', '.yaml')):
            return 'yaml'
        elif file_lower.endswith('.gradle'):
            return 'gradle_build'
        else:
            return 'unknown_config'
    
    def _extract_config_structure(self, file_path: str, content: str, config_type: str) -> Dict[str, Any]:
        """
        Extract configuration structural information.
        
        Args:
            file_path: Path to the configuration file
            content: File content
            config_type: Type of configuration
            
        Returns:
            Structural data dictionary
        """
        structural_data = {
            "file_path": file_path,
            "config_type": config_type,
            "format": self._get_format_from_type(config_type)
        }
        
        if config_type in ['web_xml', 'struts_xml', 'tiles_xml', 'jboss_service_xml', 'spring_xml', 'log_config_xml', 'maven_pom', 'ant_build', 'xml_config', 'validator_rules_xml', 'validation_xml']:
            structural_data.update(self._extract_xml_structure(content, config_type))
        elif config_type == 'properties':
            structural_data.update(self._extract_properties_structure(content))
        elif config_type == 'yaml':
            structural_data.update(self._extract_yaml_structure(content))
        elif config_type == 'gradle_build':
            structural_data.update(self._extract_gradle_structure(content))
        
        return structural_data
    
    def _extract_xml_structure(self, content: str, config_type: str) -> Dict[str, Any]:
        """
        Extract XML configuration structure.
        
        Args:
            content: XML content
            config_type: Specific XML config type
            
        Returns:
            XML structural data
        """
        structure: Dict[str, Any] = {
            "root_element": None,
            "namespaces": {},
            "elements": {},
            "attributes": {}
        }
        
        try:
            # Parse XML with better namespace handling
            root = ET.fromstring(content)
            
            # Strip namespace from root element for cleaner output
            root_tag = root.tag
            if '}' in root_tag:
                namespace_uri = root_tag.split('}')[0][1:]  # Extract namespace URI
                root_tag = root_tag.split('}')[1]
                structure["namespaces"]["default"] = namespace_uri
            structure["root_element"] = root_tag
            
            # Extract namespaces from attributes
            for prefix, uri in root.attrib.items():
                if prefix.startswith('xmlns'):
                    ns_prefix = prefix.replace('xmlns:', '') if ':' in prefix else 'default'
                    structure["namespaces"][ns_prefix] = uri
            
            # Try to get namespace from minidom for better parsing
            try:
                dom = minidom.parseString(content)
                doc_element = dom.documentElement
                if doc_element and hasattr(doc_element, 'namespaceURI') and doc_element.namespaceURI:
                    structure["namespaces"]["document"] = doc_element.namespaceURI
            except (ET.ParseError, ValueError, AttributeError):
                pass  # Fallback to ET parsing
            
            # Extract elements based on config type
            if config_type == 'web_xml':
                structure.update(self._extract_web_xml_elements(root))
            elif config_type == 'struts_xml':
                structure.update(self._extract_struts_xml_elements(root))
            elif config_type == 'tiles_xml':
                structure.update(self._extract_tiles_xml_elements(root))
            elif config_type == 'jboss_service_xml':
                structure.update(self._extract_jboss_service_xml_elements(root))
            elif config_type == 'validator_rules_xml':
                structure.update(self._extract_validator_rules_xml_elements(root))
            elif config_type == 'validation_xml':
                structure.update(self._extract_validation_xml_elements(root))
            elif config_type == 'spring_xml':
                structure.update(self._extract_spring_xml_elements(root))
            elif config_type == 'maven_pom':
                structure.update(self._extract_maven_pom_elements(root))
            else:
                structure.update(self._extract_generic_xml_elements(root))
                
        except ET.ParseError as e:
            self.logger.warning("Failed to parse XML content: %s", str(e))
            structure["parse_error"] = str(e)
        
        return structure
    
    def _extract_web_xml_elements(self, root: ET.Element) -> Dict[str, Any]:
        """
        Extract web.xml specific elements.
        
        Args:
            root: XML root element
            
        Returns:
            Web.xml specific data
        """
        elements: Dict[str, Any] = {
            "servlets": [],
            "servlet_mappings": [],
            "filters": [],
            "filter_mappings": [],
            "listeners": [],
            "context_params": [],
            "security_constraints": [],
            "error_pages": [],
            "session_config": {}
        }
        
        # Extract servlets (namespace-agnostic)
        for elem in root.iter():
            if elem.tag.endswith('}servlet') or elem.tag == 'servlet':
                servlet_data: Dict[str, Any] = {}
                for child in elem:
                    if child.tag.endswith('}servlet-name') or child.tag == 'servlet-name':
                        servlet_data['name'] = (child.text or '').strip()
                    elif child.tag.endswith('}servlet-class') or child.tag == 'servlet-class':
                        servlet_data['class'] = (child.text or '').strip()
                if servlet_data:
                    elements["servlets"].append(servlet_data)
        
        # Extract servlet mappings (namespace-agnostic)
        for elem in root.iter():
            if elem.tag.endswith('}servlet-mapping') or elem.tag == 'servlet-mapping':
                mapping_data: Dict[str, Any] = {}
                for child in elem:
                    if child.tag.endswith('}servlet-name') or child.tag == 'servlet-name':
                        mapping_data['servlet_name'] = (child.text or '').strip()
                    elif child.tag.endswith('}url-pattern') or child.tag == 'url-pattern':
                        mapping_data['url_pattern'] = (child.text or '').strip()
                if mapping_data:
                    elements["servlet_mappings"].append(mapping_data)
        
        # Extract filters (handle namespaces by iterating and checking local names)
        for elem in root.iter():
            if elem.tag.endswith('}filter') or elem.tag == 'filter':
                filter_data = {}
                # Find filter-name and filter-class children
                for child in elem:
                    if child.tag.endswith('}filter-name') or child.tag == 'filter-name':
                        filter_data['name'] = child.text.strip() if child.text else ""
                    elif child.tag.endswith('}filter-class') or child.tag == 'filter-class':
                        filter_data['class'] = child.text.strip() if child.text else ""
                if filter_data:  # Only add if we found name or class
                    elements["filters"].append(filter_data)
        
        # Extract filter mappings (handle namespaces by iterating and checking local names)
        for elem in root.iter():
            if elem.tag.endswith('}filter-mapping') or elem.tag == 'filter-mapping':
                mapping_data = {}
                # Find filter-name and url-pattern children
                for child in elem:
                    if child.tag.endswith('}filter-name') or child.tag == 'filter-name':
                        mapping_data['filter_name'] = child.text
                    elif child.tag.endswith('}url-pattern') or child.tag == 'url-pattern':
                        mapping_data['url_pattern'] = child.text
                if mapping_data:  # Only add if we found name or pattern
                    elements["filter_mappings"].append(mapping_data)
        
        # Extract error pages (handle namespaces by iterating and checking local names)
        for elem in root.iter():
            if elem.tag.endswith('}error-page') or elem.tag == 'error-page':
                error_data = {}
                # Find error-code, exception-type, and location children
                for child in elem:
                    if child.tag.endswith('}error-code') or child.tag == 'error-code':
                        error_data['error_code'] = child.text
                    elif child.tag.endswith('}exception-type') or child.tag == 'exception-type':
                        error_data['exception_type'] = child.text
                    elif child.tag.endswith('}location') or child.tag == 'location':
                        error_data['location'] = child.text
                if error_data:  # Only add if we found any error page data
                    elements["error_pages"].append(error_data)
        
        # Extract session configuration (handle namespaces by iterating and checking local names)
        for elem in root.iter():
            if elem.tag.endswith('}session-config') or elem.tag == 'session-config':
                session_data: Dict[str, Any] = {}
                
                # Find session configuration children
                for child in elem:
                    if child.tag.endswith('}session-timeout') or child.tag == 'session-timeout':
                        session_data['session_timeout'] = child.text
                    elif child.tag.endswith('}tracking-mode') or child.tag == 'tracking-mode':
                        session_data['tracking_mode'] = child.text
                    elif child.tag.endswith('}cookie-config') or child.tag == 'cookie-config':
                        cookie_data: Dict[str, Any] = {}
                        for cookie_child in child:
                            if cookie_child.tag.endswith('}http-only') or cookie_child.tag == 'http-only':
                                cookie_data['http_only'] = cookie_child.text
                            elif cookie_child.tag.endswith('}secure') or cookie_child.tag == 'secure':
                                cookie_data['secure'] = cookie_child.text
                        if cookie_data:
                            session_data['cookie_config'] = cookie_data
                
                if session_data:
                    elements["session_config"] = session_data
                break  # Only process the first session-config element
        
        # Extract context parameters (handle namespaces by iterating and checking local names)
        for elem in root.iter():
            if elem.tag.endswith('}context-param') or elem.tag == 'context-param':
                param_data = {}
                # Find param-name and param-value children
                for child in elem:
                    if child.tag.endswith('}param-name') or child.tag == 'param-name':
                        param_data['name'] = child.text
                    elif child.tag.endswith('}param-value') or child.tag == 'param-value':
                        param_data['value'] = child.text
                if param_data:  # Only add if we found name or value
                    elements["context_params"].append(param_data)
        
        return elements
    
    def _extract_struts_xml_elements(self, root: ET.Element) -> Dict[str, Any]:
        """
        Extract Struts XML configuration elements.
        
        Args:
            root: XML root element
            
        Returns:
            Struts XML specific data
        """
        elements: Dict[str, Any] = {
            "constants": [],
            "packages": [],
            "actions": [],
            "interceptors": [],
            "interceptor_stacks": [],
            "global_results": [],
            "action_mappings": [],      # Struts 1.x
            "global_exceptions": [],    # Struts 1.x  
            "global_forwards": [],      # Struts 1.x
            "validator_plugins": []     # Struts 1.x
        }
        
        # Struts 2.x extraction (existing logic)
        # Extract constants
        for constant in root.findall('.//constant'):
            const_data = {
                'name': constant.get('name'),
                'value': constant.get('value')
            }
            elements["constants"].append(const_data)
        
        # Extract packages
        for package in root.findall('.//package'):
            package_data: Dict[str, Any] = {
                'name': package.get('name'),
                'extends': package.get('extends', None),
                'namespace': package.get('namespace'),
                'actions': [],
                'interceptors': [],
                'interceptor_stacks': [],
                'global_results': []
            }
            
            # Extract actions within package
            for action in package.findall('.//action'):
                action_data: Dict[str, Any] = {
                    'name': action.get('name'),
                    'class': action.get('class'),
                    'method': action.get('method'),
                    'results': []
                }
                
                # Extract results for this action
                for result in action.findall('.//result'):
                    result_data = {
                        'name': result.get('name', 'success'),
                        'type': result.get('type', 'dispatcher'),
                        'value': result.text.strip() if result.text else None
                    }
                    action_data['results'].append(result_data)
                
                package_data['actions'].append(action_data)
                elements["actions"].append(action_data)
            
            # Extract interceptors within package
            for interceptor in package.findall('.//interceptor'):
                interceptor_data = {
                    'name': interceptor.get('name'),
                    'class': interceptor.get('class')
                }
                package_data['interceptors'].append(interceptor_data)
                elements["interceptors"].append(interceptor_data)
            
            # Extract interceptor stacks within package
            for stack in package.findall('.//interceptor-stack'):
                stack_data: Dict[str, Any] = {
                    'name': stack.get('name'),
                    'interceptor_refs': []
                }
                
                # Extract interceptor references
                for ref in stack.findall('.//interceptor-ref'):
                    ref_data = {
                        'name': ref.get('name')
                    }
                    stack_data['interceptor_refs'].append(ref_data)
                
                package_data['interceptor_stacks'].append(stack_data)
                elements["interceptor_stacks"].append(stack_data)
            
            # Extract global results within package
            for result in package.findall('.//global-results/result'):
                result_data = {
                    'name': result.get('name'),
                    'type': result.get('type', 'dispatcher'),
                    'value': result.text.strip() if result.text else None
                }
                package_data['global_results'].append(result_data)
                elements["global_results"].append(result_data)
            
            elements["packages"].append(package_data)
        
        # Struts 1.x extraction (new logic)
        # Extract action-mappings (Struts 1.x)
        for action in root.findall('.//action-mappings/action'):
            action_data = {
                'path': action.get('path'),
                'type': action.get('type'),
                'parameter': action.get('parameter'),
                'scope': action.get('scope'),
                'validate': action.get('validate'),
                # New: capture form-bean name for validation linking
                'name': action.get('name'),
            }
            elements["action_mappings"].append(action_data)
        
        # Extract global-exceptions (Struts 1.x)
        for exception in root.findall('.//global-exceptions/exception'):
            exception_data = {
                'type': exception.get('type'),
                'handler': exception.get('handler'),
                'key': exception.get('key'),
                'scope': exception.get('scope')
            }
            elements["global_exceptions"].append(exception_data)
        
        # Extract global-forwards (Struts 1.x)
        for forward in root.findall('.//global-forwards/forward'):
            forward_data = {
                'name': forward.get('name'),
                'path': forward.get('path')
            }
            elements["global_forwards"].append(forward_data)
        
        # Extract validator plugins (Struts 1.x)
        for plugin in root.findall('.//plug-in'):
            if 'validator' in plugin.get('className', '').lower():
                plugin_data = {
                    'className': plugin.get('className'),
                    'pathnames': ''
                }
                # Extract set-property for pathnames
                for prop in plugin.findall('.//set-property'):
                    if prop.get('property') == 'pathnames':
                        plugin_data['pathnames'] = prop.get('value', '')
                elements["validator_plugins"].append(plugin_data)
        
        return elements

    def _extract_tiles_xml_elements(self, root: ET.Element) -> Dict[str, Any]:
        """
        Extract Tiles XML configuration elements.
        
        Args:
            root: XML root element
            
        Returns:
            Tiles XML specific data
        """
        elements: Dict[str, Any] = {
            "definitions": [],
            "template_definitions": [],
            "base_definitions": [],
            "extends_mappings": []
        }
        
        # Extract definition elements
        for definition in root.findall('.//definition'):
            definition_data: Dict[str, Any] = {
                'name': definition.get('name', ''),
                'path': definition.get('path', ''),
                'extends': definition.get('extends', ''),
                'template': definition.get('template', ''),
                'puts': []
            }
            
            # Extract put elements within definition
            for put in definition.findall('.//put'):
                put_data = {
                    'name': put.get('name', ''),
                    'value': put.get('value', ''),
                    'type': put.get('type', ''),
                    'direct': put.get('direct', 'false')
                }
                
                # If no value attribute, check for text content
                if not put_data['value'] and put.text:
                    put_data['value'] = put.text.strip()
                
                definition_data['puts'].append(put_data)
            
            elements["definitions"].append(definition_data)
            
            # Categorize definitions
            if definition_data['path']:
                elements["template_definitions"].append(definition_data)
            if definition_data['extends']:
                elements["extends_mappings"].append({
                    'name': definition_data['name'],
                    'extends': definition_data['extends']
                })
            if not definition_data['extends']:
                elements["base_definitions"].append(definition_data)
        
        return elements

    def _extract_spring_xml_elements(self, root: ET.Element) -> Dict[str, Any]:
        """
        Extract Spring XML configuration elements.
        
        Args:
            root: XML root element
            
        Returns:
            Spring XML specific data
        """
        elements: Dict[str, Any] = {
            "beans": [],
            "components": [],
            "imports": [],
            "property_sources": []
        }
        
        # Extract bean definitions (handle namespaces by iterating and checking local names)
        for elem in root.iter():
            if elem.tag.endswith('}bean') or elem.tag == 'bean':
                bean_data: Dict[str, Any] = {
                    'id': elem.get('id'),
                    'class': elem.get('class'),
                    'scope': elem.get('scope', 'singleton'),
                    'properties': []
                }
                
                # Extract properties (check children)
                for child in elem:
                    if child.tag.endswith('}property') or child.tag == 'property':
                        prop_data = {
                            'name': child.get('name'),
                            'value': child.get('value'),
                            'ref': child.get('ref')
                        }
                        bean_data['properties'].append(prop_data)
                
                elements["beans"].append(bean_data)
        
        # Extract component scans (handle namespaces)
        for elem in root.iter():
            if elem.get('base-package'):  # Any element with base-package attribute
                # Get local name for cleaner output
                tag_name = elem.tag
                if '}' in tag_name:
                    tag_name = tag_name.split('}')[1]
                elements["components"].append({
                    'tag': tag_name,
                    'base_package': elem.get('base-package')
                })
        
        # Extract imports (handle namespaces)
        for elem in root.iter():
            if elem.tag.endswith('}import') or elem.tag == 'import':
                resource = elem.get('resource')
                if resource:
                    elements["imports"].append(resource)
        
        return elements
    
    def _extract_maven_pom_elements(self, root: ET.Element) -> Dict[str, Any]:
        """
        Extract Maven POM elements.
        
        Args:
            root: XML root element
            
        Returns:
            Maven POM specific data
        """
        elements: Dict[str, Any] = {
            "group_id": None,
            "artifact_id": None,
            "version": None,
            "dependencies": [],
            "plugins": [],
            "properties": {}
        }
        
        # Extract basic project info
        group_id = root.find('.//groupId')
        if group_id is not None:
            elements["group_id"] = group_id.text
        
        artifact_id = root.find('.//artifactId')
        if artifact_id is not None:
            elements["artifact_id"] = artifact_id.text
        
        version = root.find('.//version')
        if version is not None:
            elements["version"] = version.text
        
        # Extract dependencies
        for dependency in root.findall('.//dependency'):
            dep_data = {}
            for child in dependency:
                if child.tag in ['groupId', 'artifactId', 'version', 'scope']:
                    dep_data[child.tag] = child.text
            elements["dependencies"].append(dep_data)
        
        # Extract plugins
        for plugin in root.findall('.//plugin'):
            plugin_data = {}
            for child in plugin:
                if child.tag in ['groupId', 'artifactId', 'version']:
                    plugin_data[child.tag] = child.text
            elements["plugins"].append(plugin_data)
        
        # Extract properties
        properties = root.find('.//properties')
        if properties is not None:
            for prop in properties:
                elements["properties"][prop.tag] = prop.text
        
        return elements
    
    def _extract_validator_rules_xml_elements(self, root: ET.Element) -> Dict[str, Any]:
        """
        Extract validator-rules.xml specific elements.
        
        Args:
            root: XML root element
            
        Returns:
            Validator rules specific data
        """
        elements: Dict[str, Any] = {
            "validators": []
        }
        
        # Extract validators from global section
        for validator in root.findall('.//global/validator'):
            js_function = validator.get("jsFunction", "") 
            if not js_function or js_function == "":
                js_function = validator.get("jsFunctionName", "")
            validator_data = {
                "name": validator.get("name", ""),
                "class": validator.get("classname", ""),
                "method": validator.get("method", ""),
                "depends": validator.get("depends", ""),
                "msg": validator.get("msg", ""),
                "jsFunction": js_function
            }
            elements["validators"].append(validator_data)
        
        return elements
    
    def _extract_validation_xml_elements(self, root: ET.Element) -> Dict[str, Any]:
        """
        Extract validation.xml specific elements.
        
        Args:
            root: XML root element
            
        Returns:
            Validation XML specific data
        """
        elements: Dict[str, Any] = {
            "forms": [],
            "formsets": []
        }
        
        # Extract formsets and forms
        for formset in root.findall('.//formset'):
            formset_data: Dict[str, Any] = {
                "forms": []
            }
            
            # Extract forms within formset
            for form in formset.findall('.//form'):
                form_data: Dict[str, Any] = {
                    "name": form.get("name", ""),
                    "fields": []
                }
                
                # Extract fields within form
                for field in form.findall('.//field'):
                    field_data: Dict[str, Any] = {
                        "property": field.get("property", ""),
                        "depends": field.get("depends", ""),
                        "vars": [],
                        "msgs": []
                    }
                    
                    # Extract variables
                    for var in field.findall('.//var'):
                        var_name_elem = var.find('var-name')
                        var_value_elem = var.find('var-value')
                        if var_name_elem is not None and var_value_elem is not None:
                            field_data["vars"].append({
                                "var-name": var_name_elem.text,
                                "var-value": var_value_elem.text
                            })
                    
                    # Extract messages
                    for msg in field.findall('.//msg'):
                        field_data["msgs"].append({
                            "name": msg.get("name", ""),
                            "key": msg.get("key", "")
                        })
                    
                    form_data["fields"].append(field_data)
                
                formset_data["forms"].append(form_data)
                elements["forms"].append(form_data)
            
            elements["formsets"].append(formset_data)
        
        return elements

    def _extract_jboss_service_xml_elements(self, root: ET.Element) -> Dict[str, Any]:
        """
        Extract JBoss service XML specific elements with proper parent-child relationships.
        
        Args:
            root: XML root element
            
        Returns:
            JBoss service XML data with MBean structure and hierarchical relationships
        """
        elements: Dict[str, Any] = {
            "element_counts": {},
            "attribute_counts": {},
            "mbeans": []
        }
        
        def clean_tag(tag: str) -> str:
            """Remove namespace from tag for cleaner output."""
            return tag.split('}')[1] if '}' in tag else tag
        
        # Extract MBean elements with their children
        for mbean_elem in root.findall('.//mbean'):
            mbean_data: Dict[str, Any] = {
                "tag": "mbean",
                "attributes": dict(mbean_elem.attrib),
                "dependencies": [],
                "config_attributes": []
            }
            
            # Count MBean
            elements["element_counts"]["mbean"] = elements["element_counts"].get("mbean", 0) + 1
            
            # Count MBean attributes
            for attr_name in mbean_elem.attrib:
                elements["attribute_counts"][attr_name] = elements["attribute_counts"].get(attr_name, 0) + 1
            
            # Extract dependencies (child <depends> elements)
            for depends_elem in mbean_elem.findall('./depends'):
                if depends_elem.text and depends_elem.text.strip():
                    mbean_data["dependencies"].append({
                        "tag": "depends",
                        "text": depends_elem.text.strip()
                    })
                    elements["element_counts"]["depends"] = elements["element_counts"].get("depends", 0) + 1
            
            # Extract configuration attributes (child <attribute> elements)
            for attr_elem in mbean_elem.findall('./attribute'):
                attr_data: Dict[str, Any] = {
                    "tag": "attribute",
                    "attributes": dict(attr_elem.attrib)
                }
                if attr_elem.text and attr_elem.text.strip():
                    attr_data["text"] = attr_elem.text.strip()
                
                mbean_data["config_attributes"].append(attr_data)
                elements["element_counts"]["attribute"] = elements["element_counts"].get("attribute", 0) + 1
                
                # Count attribute attributes
                for attr_attr_name in attr_elem.attrib:
                    elements["attribute_counts"][attr_attr_name] = elements["attribute_counts"].get(attr_attr_name, 0) + 1
            
            elements["mbeans"].append(mbean_data)
        
        return elements

    def _extract_generic_xml_elements(self, root: ET.Element) -> Dict[str, Any]:
        """
        Extract generic XML elements with actual data.
        
        Args:
            root: XML root element
            
        Returns:
            Generic XML data with element structure
        """
        elements: Dict[str, Any] = {
            "element_counts": {},
            "attribute_counts": {},
            "elements": [],
            "text_content": []
        }
        
        def clean_tag(tag: str) -> str:
            """Remove namespace from tag for cleaner output."""
            return tag.split('}')[1] if '}' in tag else tag
        
        # Extract all elements with their data
        for elem in root.iter():
            clean_tag_name = clean_tag(elem.tag)
            
            # Count element types
            if clean_tag_name in elements["element_counts"]:
                elements["element_counts"][clean_tag_name] += 1
            else:
                elements["element_counts"][clean_tag_name] = 1
            
            # Extract element data if it has text or attributes
            if elem.text and elem.text.strip():
                elements["text_content"].append({
                    "tag": clean_tag_name,
                    "text": elem.text.strip()
                })
            
            if elem.attrib:
                element_data = {
                    "tag": clean_tag_name,
                    "attributes": dict(elem.attrib)
                }
                if elem.text and elem.text.strip():
                    element_data["text"] = elem.text.strip()
                elements["elements"].append(element_data)
                
                # Count attributes
                for attr_name in elem.attrib:
                    if attr_name in elements["attribute_counts"]:
                        elements["attribute_counts"][attr_name] += 1
                    else:
                        elements["attribute_counts"][attr_name] = 1
        
        return elements
    
    def _extract_properties_structure(self, content: str) -> Dict[str, Any]:
        """
        Extract properties file structure.
        
        Args:
            content: Properties file content
            
        Returns:
            Properties structural data
        """
        structure: Dict[str, Any] = {
            "properties": {},
            "comments": [],
            "property_count": 0
        }
        
        lines: List[str] = content.split('\n')
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            elif line.startswith('#') or line.startswith('!'):
                structure["comments"].append(line)
            elif '=' in line:
                key, value = line.split('=', 1)
                structure["properties"][key.strip()] = value.strip()
                structure["property_count"] += 1
        
        return structure
    
    def _extract_yaml_structure(self, content: str) -> Dict[str, Any]:
        """
        Extract YAML file structure using proper YAML parsing.
        
        Args:
            content: YAML file content
            
        Returns:
            YAML structural data
        """
        structure: Dict[str, Any] = {
            "top_level_keys": [],
            "line_count": 0,
            "comment_count": 0,
            "parsed_data": None,
            "structure_type": "unknown"
        }
        
        lines: List[str] = content.split('\n')
        structure["line_count"] = len(lines)
        
        # Basic line-by-line analysis
        for line in lines:
            line = line.strip()
            
            if line.startswith('#'):
                structure["comment_count"] += 1
            elif line and ':' in line and not line.startswith(' '):
                key = line.split(':')[0].strip()
                structure["top_level_keys"].append(key)
        
        # Try to parse with YAML library if available
        if YAML_AVAILABLE:
            try:
                parsed_data = yaml.safe_load(content)
                structure["parsed_data"] = parsed_data
                
                if isinstance(parsed_data, dict):
                    structure["structure_type"] = "dictionary"
                    structure["top_level_keys"] = list(parsed_data.keys())
                    structure["key_count"] = len(parsed_data)
                    
                    # Analyze structure depth
                    max_depth = self._calculate_yaml_depth(parsed_data)
                    structure["max_depth"] = max_depth
                    
                elif isinstance(parsed_data, list):
                    structure["structure_type"] = "list"
                    structure["item_count"] = len(parsed_data)
                else:
                    structure["structure_type"] = "scalar"
                    
            except yaml.YAMLError as e:
                structure["yaml_error"] = str(e)
                self.logger.warning("Failed to parse YAML content: %s", str(e))
        
        return structure
    
    def _calculate_yaml_depth(self, data: Any, current_depth: int = 0) -> int:
        """
        Calculate the maximum depth of a YAML structure.
        
        Args:
            data: YAML data structure
            current_depth: Current depth level
            
        Returns:
            Maximum depth found
        """
        if isinstance(data, dict):
            if not data:
                return current_depth
            return max(self._calculate_yaml_depth(value, current_depth + 1) for value in data.values())
        elif isinstance(data, list):
            if not data:
                return current_depth
            return max(self._calculate_yaml_depth(item, current_depth + 1) for item in data)
        else:
            return current_depth
    
    def _extract_gradle_structure(self, content: str) -> Dict[str, Any]:
        """
        Extract Gradle build file structure.
        
        Args:
            content: Gradle file content
            
        Returns:
            Gradle structural data
        """
        structure: Dict[str, Any] = {
            "plugins": [],
            "dependencies": [],
            "repositories": [],
            "blocks": []
        }
        
        # Simple pattern matching for Gradle blocks
        plugin_pattern = re.compile(r'id\s+["\']([^"\']+)["\']', re.IGNORECASE)
        dependency_pattern = re.compile(r'(implementation|compile|testImplementation)\s+["\']([^"\']+)["\']', re.IGNORECASE)
        
        for match in plugin_pattern.finditer(content):
            structure["plugins"].append(match.group(1))
        
        for match in dependency_pattern.finditer(content):
            structure["dependencies"].append({
                "type": match.group(1),
                "dependency": match.group(2)
            })
        
        return structure
    
    def _get_format_from_type(self, config_type: str) -> str:
        """
        Get format from configuration type.
        
        Args:
            config_type: Configuration type
            
        Returns:
            Format string
        """
        if 'xml' in config_type:
            return 'xml'
        elif config_type == 'properties':
            return 'properties'
        elif config_type == 'yaml':
            return 'yaml'
        elif config_type == 'gradle_build':
            return 'gradle'
        else:
            return 'unknown'
    
    def _detect_config_framework_patterns(self, file_path: str, content: str, config_type: str) -> List[str]:
        """
        Detect framework patterns in configuration files.
        
        Args:
            file_path: Path to the configuration file
            content: File content
            config_type: Type of configuration
            
        Returns:
            List of detected framework hints
        """
        framework_hints = []
        
        try:
            # Use LEX Java rules for framework detection
            spring_patterns = self.java_rules.get_spring_indicators()
            hibernate_patterns = self.java_rules.get_hibernate_indicators()
            struts_patterns = self.java_rules.get_struts_indicators()
            
            for pattern, weight in spring_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    framework_hints.append("spring")
                    break
            
            for pattern, weight in hibernate_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    framework_hints.append("hibernate")
                    break
            
            for pattern, weight in struts_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    framework_hints.append("struts")
                    break
            
            # Add specific framework detection
            if config_type == 'spring_xml':
                framework_hints.append("spring")
            elif config_type == 'web_xml':
                framework_hints.append("servlet_container")
            
            # Check for specific technologies
            if 'hibernate' in content.lower():
                framework_hints.append("hibernate")
            if 'struts' in content.lower():
                framework_hints.append("struts")
            if 'log4j' in content.lower():
                framework_hints.append("log4j")
            
        except Exception as e:  # pylint: disable=broad-except
            self.logger.warning("Failed to detect config framework patterns: %s", str(e))
        
        return list(set(framework_hints))  # Remove duplicates
    
    def _calculate_confidence(self, structural_data: Optional[Dict[str, Any]]) -> float:
        """
        Calculate confidence score for configuration parsing.
        
        Args:
            structural_data: Extracted structural data
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not structural_data:
            return 0.0
        
        confidence = 0.6  # Base confidence for configuration files
        
        # Increase confidence based on configuration completeness
        config_type = structural_data.get("config_type", "")
        
        if config_type == "struts_xml":
            if structural_data.get("packages") and len(structural_data["packages"]) > 0:
                confidence += 0.2
            if structural_data.get("actions") and len(structural_data["actions"]) > 0:
                confidence += 0.1
            if structural_data.get("constants") and len(structural_data["constants"]) > 0:
                confidence += 0.1
        elif config_type == "web_xml":
            if structural_data.get("servlets") and len(structural_data["servlets"]) > 0:
                confidence += 0.2
            if structural_data.get("filters") and len(structural_data["filters"]) > 0:
                confidence += 0.1
            if structural_data.get("context_params") and len(structural_data["context_params"]) > 0:
                confidence += 0.1
        elif config_type == "spring_xml":
            if structural_data.get("beans") and len(structural_data["beans"]) > 0:
                confidence += 0.2
            if structural_data.get("components") and len(structural_data["components"]) > 0:
                confidence += 0.1
            if structural_data.get("imports") and len(structural_data["imports"]) > 0:
                confidence += 0.1
        elif config_type == "properties":
            if structural_data.get("properties") and len(structural_data["properties"]) > 0:
                confidence += 0.2
                # Extra confidence for well-structured properties
                properties = structural_data["properties"]
                if len(properties) > 5:
                    confidence += 0.1
                if any(key.startswith(('db.', 'app.', 'log.')) for key in properties.keys()):
                    confidence += 0.1
        
        return min(confidence, 1.0)
    
    def determine_framework(self, config_type: str, framework_hints: List[str], structural_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Public method to determine framework from config type and hints.
        
        Args:
            config_type: Configuration file type
            framework_hints: Framework hints from reader
            structural_data: Structural data to help with framework detection
            
        Returns:
            Framework identifier
        """
        if config_type == 'struts_xml':
            # Check if it's Struts 1.x or 2.x based on root element
            if structural_data:
                root_element = structural_data.get("root_element", "")
                if root_element == "struts-config":
                    return "struts_1x"  # struts-config is Struts 1.x
                elif root_element == "struts":
                    return "struts_2x"  # struts is Struts 2.x
            return "struts_2x"  # Default assumption for XML config
        elif config_type == 'web_xml':
            return "servlet"
        elif config_type == 'jboss_service_xml':
            return "jboss"
        elif config_type == 'tiles_xml':
            return "tiles"
        elif config_type in ['validation_xml', 'validator_rules_xml']:
            return "struts_1x"  # Validation files are typically Struts 1.x
        elif config_type == 'spring_xml':
            return "spring"
        elif "struts" in framework_hints:
            return "struts_2x"
        elif "spring" in framework_hints:
            return "spring"
        else:
            return "unknown"
    
    def extract_framework_version(self, structural_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract framework version from structural data.
        
        Args:
            structural_data: Raw structural data
            
        Returns:
            Framework version if detectable
        """
        # Look for version indicators in namespaces or DTD declarations
        namespaces = structural_data.get("namespaces", {})
        for uri in namespaces.values():
            if "struts-2.0" in uri:
                return "2.0"
            elif "struts-2.1" in uri:
                return "2.1"
            elif "struts-2.5" in uri:
                return "2.5"
        
        return None
