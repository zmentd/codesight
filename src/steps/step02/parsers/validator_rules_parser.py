"""
Validator rules parser for Step 02 AST extraction.

Handles parsing of validator-rules.xml files and converts them into ValidatorDefinition domain models.
"""

from typing import Any, Dict, Optional

from config import Config
from domain.config_details import ConfigurationDetails, ValidatorDefinition
from domain.source_inventory import FileInventoryItem
from utils.logging.logger_factory import LoggerFactory

from .configuration_reader import ConfigurationReader


class ValidatorRulesParser:
    """
    Validator rules parser for validator-rules.xml files.
    
    Converts validator-rules.xml configuration data into ValidatorDefinition domain models.
    """
    
    def __init__(self, config: Config):
        """
        Initialize validator definitions parser.
        
        Args:
            config: Configuration instance
        """
        self.config = config
        self.reader = ConfigurationReader(config)
        self.logger = LoggerFactory.get_logger("steps.step02.validatordefinitionsparser")
    
    def parse_validator_rules_file(self, validator_rules_file: FileInventoryItem) -> Optional[ConfigurationDetails]:
        """
        Parse a validator-rules.xml file and return ConfigurationDetails.
        
        Args:
            validator_rules_file: FileInventoryItem for the validator-rules.xml file
            
        Returns:
            ConfigurationDetails with validator definitions or None if parsing fails
        """
        try:
            self.logger.debug("Parsing validator-rules.xml file: %s from source_location: %s", 
                             validator_rules_file.path, validator_rules_file.source_location)
            
            # Use ConfigurationReader to parse the validator rules file
            reader_result = self.reader.parse_file(validator_rules_file.source_location, validator_rules_file.path)
            
            if not reader_result.success or not reader_result.structural_data:
                self.logger.warning("Failed to parse validator-rules.xml file: %s - %s", 
                                   validator_rules_file.path, reader_result.error_message)
                return None
            
            # Create ConfigurationDetails with detected framework
            detected_framework = "struts_1x"
            
            config_details = ConfigurationDetails(
                detected_framework=detected_framework,
                framework_version=self.reader.extract_framework_version(reader_result.structural_data)
            )
            
            # Convert structural data to validator definitions
            self._convert_validator_definitions(reader_result.structural_data, config_details)
            
            self.logger.debug("Successfully parsed validator-rules.xml file: %s - %d validator definitions", 
                             validator_rules_file.path, len(config_details.validator_definitions))
            
            return config_details
            
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Failed to parse validator-rules.xml file %s: %s", validator_rules_file.path, str(e))
            return None
    
    def _convert_validator_definitions(
        self, 
        structural_data: Dict[str, Any], 
        config_details: ConfigurationDetails
    ) -> None:
        """
        Convert validator definitions (from validator-rules.xml).
        
        Args:
            structural_data: Raw validator rules data
            config_details: ConfigurationDetails to populate
        """
        validators = structural_data.get("validators", [])
        self.logger.debug("Converting %d validator definitions", len(validators))
        for validator in validators:
            js_function = validator.get("jsFunction", "") 
            if not js_function or js_function == "":
                js_function = validator.get("jsFunctionName", "")
            validator_def = ValidatorDefinition(
                validator_name=validator.get("name", ""),
                validator_class=validator.get("class", ""),
                validator_method=validator.get("method", ""),
                depends_on=validator.get("depends", "").split(",") if validator.get("depends") else [],
                default_message_key=validator.get("msg", ""),
                javascript_function=js_function,
                framework="struts_1x"
            )
            config_details.validator_definitions.append(validator_def)
            self.logger.debug("Created validator definition: %s", validator_def.validator_name)
