"""
Struts 1.x specific parser for Step 02 AST extraction.

Handles parsing of Struts 1.x configuration files (struts-config.xml)
and converts them into domain models.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

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

if TYPE_CHECKING:
    from .validation_parser import ValidationParser
    from .validator_rules_parser import ValidatorRulesParser


class Struts1xParser:
    """
    Struts 1.x configuration parser.
    
    Converts Struts 1.x configuration data (action-mappings, global-exceptions, etc.)
    into domain models.
    """
    
    def __init__(self, config: Config, source_inventory: SourceInventory):
        """
        Initialize Struts 1.x parser.
        
        Args:
            config: Configuration instance
            source_inventory: Source inventory for file lookup
        """
        self.config = config
        self.source_inventory = source_inventory
        self.file_inventory_utils = FileInventoryUtils(source_inventory)
        self.logger = LoggerFactory.get_logger("steps.step02.struts1xparser")
        
        # Initialize parsers for validation files (lazy loading to avoid circular imports)
        self._validation_parser: Optional['ValidationParser'] = None
        self._validator_rules_parser: Optional['ValidatorRulesParser'] = None

    @property
    def validation_parser(self) -> 'ValidationParser':
        """Lazy load ValidationParser to avoid circular imports."""
        if self._validation_parser is None:
            from .validation_parser import ValidationParser
            self._validation_parser = ValidationParser(self.config)
        return self._validation_parser

    @property
    def validator_rules_parser(self) -> 'ValidatorRulesParser':
        """Lazy load ValidatorRulesParser to avoid circular imports."""
        if self._validator_rules_parser is None:
            from .validator_rules_parser import ValidatorRulesParser
            self._validator_rules_parser = ValidatorRulesParser(self.config)
        return self._validator_rules_parser
    
    def parse(
        self, 
        structural_data: Dict[str, Any], 
        config_details: ConfigurationDetails, 
        file_item: FileInventoryItem
    ) -> None:
        """
        Parse Struts 1.x configuration data and populate ConfigurationDetails.
        
        Args:
            structural_data: Raw Struts 1.x configuration data
            config_details: ConfigurationDetails to populate
            file_item: File item containing source_location for resolving relative paths
        """
        self.logger.debug("Parsing Struts 1.x config with structural_data keys: %s", 
                         list(structural_data.keys()))
        
        # Process Struts 1.x action-mappings
        self._process_action_mappings(structural_data, config_details)
        
        # Process global exceptions
        self._process_global_exceptions(structural_data, config_details)
        
        # Process validation references and validation files
        self._process_validation_references(structural_data, config_details, file_item)
        
        self.logger.debug("Completed Struts 1.x parsing: %d code_mappings, %d exception_mappings", 
                         len(config_details.code_mappings), len(config_details.exception_mappings))
    
    def _process_action_mappings(
        self, 
        structural_data: Dict[str, Any], 
        config_details: ConfigurationDetails
    ) -> None:
        """
        Process Struts 1.x action-mappings.
        
        Args:
            structural_data: Raw Struts configuration data
            config_details: ConfigurationDetails to populate
        """
        action_mappings = structural_data.get("action_mappings", [])
        self.logger.debug("Found %d Struts 1.x action_mappings", len(action_mappings))
        
        for action_mapping_data in action_mappings:
            action_path = action_mapping_data.get("path", "")
            action_type = action_mapping_data.get("type", "")
            action_parameter = action_mapping_data.get("parameter", "")
            # New: capture Struts 1.x form-bean name if present
            form_name = action_mapping_data.get("name", "")
            
            self.logger.debug("Processing Struts 1.x action_mapping: path=%s, type=%s, parameter=%s", 
                             action_path, action_type, action_parameter)
            
            if action_path and action_type:
                # Create action mapping (URL path → Java class)
                code_mapping = CodeMapping(
                    from_reference=action_path,
                    to_reference=action_type,
                    mapping_type="action",
                    framework=config_details.detected_framework,
                    semantic_category=SemanticCategory.ENTRY_POINT,
                    attributes={
                        "parameter": action_parameter,
                        "scope": action_mapping_data.get("scope", "request"),
                        "validate": str(action_mapping_data.get("validate", "false")),
                        # New: expose form-bean name for downstream linking
                        "form_name": form_name or "",
                    }
                )
                config_details.code_mappings.append(code_mapping)
                self.logger.debug("Created Struts 1.x action mapping: %s -> %s", action_path, action_type)
    
    def _process_global_exceptions(
        self, 
        structural_data: Dict[str, Any], 
        config_details: ConfigurationDetails
    ) -> None:
        """
        Process Struts 1.x global exceptions.
        
        Args:
            structural_data: Raw Struts configuration data
            config_details: ConfigurationDetails to populate
        """
        global_exceptions = structural_data.get("global_exceptions", [])
        self.logger.debug("Found %d global_exceptions", len(global_exceptions))
        
        for exception in global_exceptions:
            exception_type = exception.get("type", "")
            exception_handler = exception.get("handler", "")
            
            self.logger.debug("Processing global exception: type=%s, handler=%s", 
                             exception_type, exception_handler)
            
            if exception_type and exception_handler:
                exception_mapping = ExceptionMapping(
                    exception_type=exception_type,
                    handler_reference=exception_handler,
                    framework=config_details.detected_framework,
                    attributes={"scope": "global"}
                )
                config_details.exception_mappings.append(exception_mapping)
                self.logger.debug("Created exception mapping: %s -> %s", exception_type, exception_handler)
    
    def _process_validation_references(
        self, 
        structural_data: Dict[str, Any], 
        config_details: ConfigurationDetails, 
        file_item: FileInventoryItem
    ) -> None:
        """
        Process validation references from Struts 1.x configuration.
        
        Args:
            structural_data: Raw Struts configuration data
            config_details: ConfigurationDetails to populate with validation data
            file_item: File item containing source_location for resolving relative paths
        """
        validation_references = self._find_validation_references(structural_data)
        
        if validation_references:
            self.logger.debug("Found validation references in Struts 1.x config: %s", validation_references)
            
            # Look for validation.xml and validator-rules.xml files using FileInventoryUtils
            source_location = file_item.source_location
            
            for reference in validation_references:
                if reference.startswith("/"):
                    reference = reference[1:]
                self.logger.debug("Processing validation reference: %s", reference)
                if reference.endswith("validation.xml"):
                    validation_file = self.file_inventory_utils.find_file_by_path(reference, source_location)
                    if validation_file:
                        self.logger.debug("Processing validation.xml file: %s", validation_file.path)

                        # Actually parse the validation file using ValidationParser
                        try:
                            validation_result = self.validation_parser.parse_validation_file(validation_file)
                            if validation_result and validation_result.validation_rules:
                                config_details.validation_rules.extend(validation_result.validation_rules)
                                self.logger.debug("Added %d validation rules from %s", 
                                                len(validation_result.validation_rules), validation_file.path)
                        except (ValueError, KeyError, AttributeError) as e:
                            self.logger.error("Failed to parse validation file %s: %s", validation_file.path, str(e))
                        # Find validation.xml file
                elif reference.endswith("validator-rules.xml"):
                    validator_rules_file = self.file_inventory_utils.find_file_by_path(reference, source_location)
                    if validator_rules_file:
                        self.logger.debug("Processing validator-rules.xml file: %s", validator_rules_file.path)

                        # Actually parse the validator rules file using ValidatorRulesParser
                        try:
                            validator_result = self.validator_rules_parser.parse_validator_rules_file(validator_rules_file)
                            if validator_result and validator_result.validator_definitions:
                                config_details.validator_definitions.extend(validator_result.validator_definitions)
                                self.logger.debug("Added %d validator definitions from %s", 
                                                len(validator_result.validator_definitions), validator_rules_file.path)
                        except (ValueError, KeyError, AttributeError) as e:
                            self.logger.error("Failed to parse validator rules file %s: %s", validator_rules_file.path, str(e))
                else:
                    self.logger.warning("Unknown validation reference type: %s", reference)
    
    def _find_validation_references(self, structural_data: Dict[str, Any]) -> List[str]:
        """
        Find validation references in Struts 1.x configuration data.
        
        Args:
            structural_data: Raw Struts configuration data
            
        Returns:
            List of validation references found
        """
        validation_references = []
        
        self.logger.debug("Looking for validation references in structural_data with keys: %s", 
                         list(structural_data.keys()))
        
        # Check for validator plugins (Struts 1.x)
        validator_plugins = structural_data.get("validator_plugins", [])
        self.logger.debug("Found %d validator_plugins", len(validator_plugins))
        
        for plugin in validator_plugins:
            plugin_class = plugin.get("className", "")
            pathnames = plugin.get("pathnames", "")
            
            self.logger.debug("Processing validator plugin: className=%s, pathnames=%s", 
                             plugin_class, pathnames)
            
            if "validator" in plugin_class.lower() and pathnames:
                # Split pathnames and add to references
                for pathname in pathnames.split(","):
                    pathname = pathname.strip()
                    if pathname:
                        validation_references.append(pathname)
        
        # Check actions for validation references (e.g., validate="true")
        action_mappings = structural_data.get("action_mappings", [])
        self.logger.debug("Found %d action_mappings to check for validation", len(action_mappings))
        
        for action in action_mappings:
            # Check if action has validation enabled
            if action.get("validate") == "true" or action.get("validate") is True:
                validation_references.append(f"action_{action.get('path', 'unknown')}_validation")
                self.logger.debug("Found action with validation enabled: %s", action.get('path', 'unknown'))
        
        self.logger.debug("Total validation references found: %d - %s", 
                         len(validation_references), validation_references)
        
        return validation_references
