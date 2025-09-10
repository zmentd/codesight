"""
Web.xml specific parser for Step 02 AST extraction.

Handles parsing of web.xml deployment descriptor files
and converts them into domain models.
"""

from typing import Any, Dict, List

from config import Config
from domain.config_details import (
    CodeMapping,
    ConfigurationDetails,
    ExceptionMapping,
    SemanticCategory,
)
from domain.source_inventory import FileInventoryItem, SourceInventory
from steps.step02.utils.file_inventory_utils import FileInventoryUtils
from utils.logging.logger_factory import LoggerFactory


class WebXmlParser:
    """
    Web.xml deployment descriptor parser.
    
    Converts web.xml configuration data (servlets, filters, error-pages, etc.)
    into domain models.
    """
    
    def __init__(self, config: Config, source_inventory: SourceInventory):
        """
        Initialize web.xml parser.
        
        Args:
            config: Configuration instance
            source_inventory: Source inventory for file lookups
        """
        self.config = config
        self.file_inventory_utils = FileInventoryUtils(source_inventory)
        self.logger = LoggerFactory.get_logger("steps.step02.webxmlparser")
    
    def parse(
        self, 
        structural_data: Dict[str, Any], 
        config_details: ConfigurationDetails, 
        file_item: FileInventoryItem
    ) -> None:
        """
        Parse web.xml configuration data and populate ConfigurationDetails.
        
        Args:
            structural_data: Raw web.xml configuration data
            config_details: ConfigurationDetails to populate
            file_item: File item containing source_location for resolving relative paths
        """
        self.logger.debug("Parsing web.xml config with structural_data keys: %s", 
                         list(structural_data.keys()))
        
        # Process servlet mappings
        self._process_servlet_mappings(structural_data, config_details)
        
        # Process filter mappings
        self._process_filter_mappings(structural_data, config_details)
        
        # Process error page mappings
        self._process_error_pages(structural_data, config_details)
        
        # Process session configuration
        self._process_session_config(structural_data, config_details)
        
        # Process context parameters
        self._process_context_params(structural_data, config_details)
        
        self.logger.debug("Completed web.xml parsing: %d code_mappings, %d exception_mappings", 
                         len(config_details.code_mappings), len(config_details.exception_mappings))
    
    def _process_servlet_mappings(
        self, 
        structural_data: Dict[str, Any], 
        config_details: ConfigurationDetails
    ) -> None:
        """
        Process servlet mappings from web.xml.
        
        Args:
            structural_data: Raw web.xml configuration data
            config_details: ConfigurationDetails to populate
        """
        servlets = structural_data.get("servlets", [])
        servlet_mappings = structural_data.get("servlet_mappings", [])
        
        # Create mapping from servlet name to class
        servlet_name_to_class = {}
        for servlet in servlets:
            name = servlet.get("name", "")
            servlet_class = servlet.get("class", "")
            if name and servlet_class:
                servlet_name_to_class[name] = servlet_class
        
        self.logger.debug("Found %d servlets and %d servlet mappings", 
                         len(servlets), len(servlet_mappings))
        
        # Convert servlet mappings to CodeMapping objects
        for mapping in servlet_mappings:
            servlet_name = mapping.get("servlet_name", "")
            url_pattern = mapping.get("url_pattern", "")
            servlet_class = servlet_name_to_class.get(servlet_name, "")
            
            self.logger.debug("Processing servlet mapping: name=%s, pattern=%s, class=%s", 
                             servlet_name, url_pattern, servlet_class)
            
            if url_pattern and servlet_class:
                code_mapping = CodeMapping(
                    from_reference=url_pattern,
                    to_reference=servlet_class,
                    mapping_type="servlet",
                    framework=config_details.detected_framework,
                    semantic_category=SemanticCategory.ENTRY_POINT,
                    attributes={
                        "servlet_name": servlet_name,
                        "type": "servlet_mapping"
                    }
                )
                config_details.code_mappings.append(code_mapping)
                self.logger.debug("Created servlet mapping: %s -> %s", url_pattern, servlet_class)
    
    def _process_filter_mappings(
        self, 
        structural_data: Dict[str, Any], 
        config_details: ConfigurationDetails
    ) -> None:
        """
        Process filter mappings from web.xml.
        
        Args:
            structural_data: Raw web.xml configuration data
            config_details: ConfigurationDetails to populate
        """
        filters = structural_data.get("filters", [])
        filter_mappings = structural_data.get("filter_mappings", [])
        
        # Create mapping from filter name to class
        filter_name_to_class = {}
        for filter_def in filters:
            name = filter_def.get("name", "")
            filter_class = filter_def.get("class", "")
            if name and filter_class:
                filter_name_to_class[name] = filter_class
        
        self.logger.debug("Found %d filters and %d filter mappings", 
                         len(filters), len(filter_mappings))
        
        # Convert filter mappings to CodeMapping objects
        for mapping in filter_mappings:
            filter_name = mapping.get("filter_name", "")
            url_pattern = mapping.get("url_pattern", "")
            filter_class = filter_name_to_class.get(filter_name, "")
            
            self.logger.debug("Processing filter mapping: name=%s, pattern=%s, class=%s", 
                             filter_name, url_pattern, filter_class)
            
            if url_pattern and filter_class:
                code_mapping = CodeMapping(
                    from_reference=url_pattern,
                    to_reference=filter_class,
                    mapping_type="filter",
                    framework=config_details.detected_framework,
                    semantic_category=SemanticCategory.CROSS_CUTTING,
                    attributes={
                        "filter_name": filter_name,
                        "type": "filter_mapping"
                    }
                )
                config_details.code_mappings.append(code_mapping)
                self.logger.debug("Created filter mapping: %s -> %s", url_pattern, filter_class)
        
        # Also create direct filter mappings for filters without explicit mappings
        # This captures filters that are defined but may have implicit mappings
        for filter_def in filters:
            filter_name = filter_def.get("name", "")
            filter_class = filter_def.get("class", "")
            
            if filter_name and filter_class:
                # Check if we already have a mapping for this filter
                # Filter for CodeMapping instances first to avoid type checking issues
                code_mappings = [m for m in config_details.code_mappings if isinstance(m, CodeMapping)]
                existing_mappings = [m for m in code_mappings 
                                   if m.mapping_type == "filter" and 
                                   m.attributes.get("filter_name") == filter_name]
                
                if not existing_mappings:
                    # Create a direct filter definition mapping
                    code_mapping = CodeMapping(
                        from_reference=filter_name,
                        to_reference=filter_class,
                        mapping_type="filter",
                        framework=config_details.detected_framework,
                        semantic_category=SemanticCategory.CROSS_CUTTING,
                        attributes={
                            "filter_name": filter_name,
                            "type": "filter_definition"
                        }
                    )
                    config_details.code_mappings.append(code_mapping)
                    self.logger.debug("Created filter definition mapping: %s -> %s", filter_name, filter_class)
    
    def _process_error_pages(
        self, 
        structural_data: Dict[str, Any], 
        config_details: ConfigurationDetails
    ) -> None:
        """
        Process error page mappings from web.xml.
        
        Args:
            structural_data: Raw web.xml configuration data
            config_details: ConfigurationDetails to populate
        """
        error_pages = structural_data.get("error_pages", [])
        self.logger.debug("Found %d error pages", len(error_pages))
        
        for error_page in error_pages:
            error_code = error_page.get("error_code", "")
            exception_type = error_page.get("exception_type", "")
            location = error_page.get("location", "")
            
            self.logger.debug("Processing error page: code=%s, exception=%s, location=%s", 
                             error_code, exception_type, location)
            
            if location:
                if error_code:
                    # HTTP error code mapping
                    exception_mapping = ExceptionMapping(
                        exception_type=f"HTTP_{error_code}",
                        handler_reference=location,
                        framework=config_details.detected_framework,
                        attributes={
                            "error_code": error_code,
                            "type": "error_page",
                            "scope": "global"
                        }
                    )
                    config_details.exception_mappings.append(exception_mapping)
                    self.logger.debug("Created error page mapping: HTTP_%s -> %s", error_code, location)
                
                elif exception_type:
                    # Exception type mapping
                    exception_mapping = ExceptionMapping(
                        exception_type=exception_type,
                        handler_reference=location,
                        framework=config_details.detected_framework,
                        attributes={
                            "type": "error_page",
                            "scope": "global"
                        }
                    )
                    config_details.exception_mappings.append(exception_mapping)
                    self.logger.debug("Created exception mapping: %s -> %s", exception_type, location)
    
    def _process_session_config(
        self, 
        structural_data: Dict[str, Any], 
        config_details: ConfigurationDetails
    ) -> None:
        """
        Process session configuration from web.xml.
        
        Args:
            structural_data: Raw web.xml configuration data
            config_details: ConfigurationDetails to populate
        """
        session_config = structural_data.get("session_config", {})
        if not session_config:
            return
        
        self.logger.debug("Processing session configuration: %s", session_config)
        
        session_timeout = session_config.get("session_timeout", "")
        cookie_config = session_config.get("cookie_config", {})
        tracking_mode = session_config.get("tracking_mode", "")
        
        if session_timeout or cookie_config or tracking_mode:
            # Create configuration mapping for session settings
            attributes = {}
            if session_timeout:
                attributes["session_timeout"] = str(session_timeout)
            if tracking_mode:
                attributes["tracking_mode"] = tracking_mode
            
            # Add cookie configuration
            if cookie_config:
                if cookie_config.get("http_only"):
                    attributes["cookie_http_only"] = str(cookie_config["http_only"])
                if cookie_config.get("secure"):
                    attributes["cookie_secure"] = str(cookie_config["secure"])
            
            code_mapping = CodeMapping(
                from_reference="session-config",
                to_reference="<session-configuration>",
                mapping_type="configuration",
                framework=config_details.detected_framework,
                semantic_category=None,
                attributes=attributes
            )
            config_details.code_mappings.append(code_mapping)
            self.logger.debug("Created session configuration mapping")
    
    def _process_context_params(
        self, 
        structural_data: Dict[str, Any], 
        config_details: ConfigurationDetails
    ) -> None:
        """
        Process context parameters from web.xml.
        
        Args:
            structural_data: Raw web.xml configuration data
            config_details: ConfigurationDetails to populate
        """
        context_params = structural_data.get("context_params", [])
        self.logger.debug("Found %d context parameters", len(context_params))
        
        for param in context_params:
            param_name = param.get("name", "")
            param_value = param.get("value", "")
            
            self.logger.debug("Processing context parameter: name=%s, value=%s", 
                             param_name, param_value)
            
            if param_name and param_value:
                code_mapping = CodeMapping(
                    from_reference=param_name,
                    to_reference=param_value,
                    mapping_type="configuration",
                    framework=config_details.detected_framework,
                    semantic_category=None,
                    attributes={
                        "type": "context_param",
                        "scope": "application"
                    }
                )
                config_details.code_mappings.append(code_mapping)
                self.logger.debug("Created context parameter mapping: %s -> %s", param_name, param_value)
