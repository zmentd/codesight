"""
Configuration file parser for Step 02 AST extraction.

Extends BaseParser and orchestrates specific configuration parsers
to convert configuration files into domain models.
"""

import time
from typing import Any, Dict, List, Optional

from config import Config
from domain.config_details import (
    CodeMapping,
    ConfigurationDetails,
    ExceptionMapping,
    ValidationRule,
    ValidatorDefinition,
)
from domain.source_inventory import FileInventoryItem, SourceInventory
from steps.step02.utils.file_inventory_utils import FileInventoryUtils
from utils.path_utils import PathUtils

from .base_parser import BaseParser
from .configuration_reader import ConfigurationReader
from .jboss_service_parser import JBossServiceParser
from .struts1x_parser import Struts1xParser
from .struts2x_parser import Struts2xParser
from .tiles_parser import TilesConfigParser
from .validation_parser import ValidationParser
from .validator_rules_parser import ValidatorRulesParser
from .webxml_parser import WebXmlParser


class ConfigurationParser(BaseParser):
    """
    Configuration file parser orchestrator.
    
    Uses ConfigurationReader for low-level parsing and delegates to specific
    parsers based on configuration type to convert into domain models.
    """

    def __init__(self, config: Config, source_inventory: SourceInventory) -> None:
        """
        Initialize configuration parser orchestrator.
        
        Args:
            config: Configuration instance
            source_inventory: Step01 filesystem analyzer output for locating validation files
        """
        super().__init__(config)
        self.reader = ConfigurationReader(config)
        self.file_inventory_utils = FileInventoryUtils(source_inventory)
        
        # Initialize specific parsers
        self.struts1x_parser = Struts1xParser(config, source_inventory)
        self.struts2x_parser = Struts2xParser(config, source_inventory)
        self.webxml_parser = WebXmlParser(config, source_inventory)
        self.jboss_service_parser = JBossServiceParser(config, source_inventory)
        self.tiles_parser = TilesConfigParser(config, source_inventory)
        self.validation_parser = ValidationParser(config)
        self.validator_rules_parser = ValidatorRulesParser(config)

    def can_parse(self, file_item: FileInventoryItem) -> bool:
        """
        Check if this parser can handle configuration files.
        
        Args:
            file_info: File information dictionary
            
        Returns:
            True if file is a configuration file
        """
        file_info = {
            "path": file_item.path,
            "type": file_item.language,
        }
        return self.reader.can_parse(file_info)
    
    def parse_file(self, file_item: FileInventoryItem) -> ConfigurationDetails:
        """
        Parse configuration file and return domain models.
        
        Args:
            file_item: FileInventoryItem containing file details
            
        Returns:
            ConfigurationDetails domain model
        """
        try:
            file_path = file_item.path
            source_location = file_item.source_location

            self.logger.debug("Starting to parse configuration file: %s (source_location: %s)", 
                             file_path, source_location)
             
            # Use reader to get raw structural data
            reader_result = self.reader.parse_file(source_location, file_path)
            
            self.logger.debug("Reader result: success=%s, structural_data_keys=%s, framework_hints=%s", 
                             reader_result.success, 
                             list(reader_result.structural_data.keys()) if reader_result.structural_data else "None",
                             reader_result.framework_hints)
            
            if not reader_result.success:
                self.logger.warning("Reader failed to parse file: %s", file_path)
                # Return empty ConfigurationDetails on parse failure
                return ConfigurationDetails()
            
            # Convert raw data to domain models
            config_details = self._convert_to_domain_model(
                file_item, 
                reader_result.structural_data, 
                reader_result.framework_hints
            )
            
            self.logger.debug("Completed parsing file %s: framework=%s, code_mappings=%d, validation_rules=%d", 
                             file_path, config_details.detected_framework, 
                             len(config_details.code_mappings), len(config_details.validation_rules))
            
            return config_details
            
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Failed to parse configuration file %s: %s", file_path, str(e))
            return ConfigurationDetails()
    
    def _convert_to_domain_model(
        self, 
        file_item: FileInventoryItem, 
        structural_data: Optional[Dict[str, Any]], 
        framework_hints: List[str],
    ) -> ConfigurationDetails:
        if not structural_data:
            self.logger.debug("No structural data provided for file: %s", file_item.path)
            return ConfigurationDetails()
        
        config_type = structural_data.get("config_type", "unknown")
        self.logger.debug("Converting to domain model: file=%s, config_type=%s, framework_hints=%s", 
                         file_item.path, config_type, framework_hints)
        
        # Create base configuration details
        detected_framework = self.reader.determine_framework(config_type, framework_hints, structural_data)
        framework_version = self.reader.extract_framework_version(structural_data)
        
        self.logger.debug("Detected framework: %s, version: %s", detected_framework, framework_version)
        
        config_details = ConfigurationDetails(
            detected_framework=detected_framework,
            framework_version=framework_version
        )
        
        # Orchestrate specific parsers based on configuration type
        try:
            if config_type == 'struts_xml':
                self.logger.debug("Using Struts parser for: %s", config_type)
                if detected_framework == 'struts_1x':
                    self.struts1x_parser.parse(structural_data, config_details, file_item)
                elif detected_framework == 'struts_2x':
                    self.struts2x_parser.parse(structural_data, config_details, file_item)
                else:
                    self.logger.warning("Unknown Struts framework version: %s for file: %s", detected_framework, file_item.path)
            elif config_type == 'web_xml':
                self.logger.debug("Using WebXML parser for: %s", config_type)
                self.webxml_parser.parse(structural_data, config_details, file_item)
            elif config_type == 'jboss_service_xml':
                self.logger.debug("Using JBoss service parser for: %s", config_type)
                self.jboss_service_parser.parse(structural_data, config_details, file_item)
            elif config_type == 'tiles_xml':
                self.logger.debug("Using Tiles parser for: %s", config_type)
                self.tiles_parser.parse(structural_data, config_details, file_item)
            elif config_type == 'validation_xml':
                self.logger.debug("Using Validation parser for: %s", config_type)
                validation_result = self.validation_parser.parse_validation_file(file_item)
                if validation_result:
                    # Merge validation rules into our config_details
                    config_details.validation_rules.extend(validation_result.validation_rules)
            elif config_type == 'validator_rules_xml':
                self.logger.debug("Using ValidatorRules parser for: %s", config_type)
                validator_result = self.validator_rules_parser.parse_validator_rules_file(file_item)
                if validator_result:
                    # Merge validator definitions into our config_details
                    config_details.validator_definitions.extend(validator_result.validator_definitions)
            else:
                # Log warning for unsupported configuration types and skip processing
                self.logger.warning("No specific parser available for config type '%s' in file: %s. Skipping processing.", 
                                  config_type, file_item.path)
                
        except (AttributeError, KeyError, ValueError, TypeError) as e:
            self.logger.error("Error using specific parser for config type '%s' in file: %s: %s", 
                            config_type, file_item.path, str(e))
        
        return config_details
    