"""
Validation parser for Step 02 AST extraction.

Handles parsing of validation.xml files and converts them into ValidationRule domain models.
"""

from typing import Any, Dict, Optional

from config import Config
from domain.config_details import ConfigurationDetails, ValidationRule
from domain.source_inventory import FileInventoryItem
from utils.logging.logger_factory import LoggerFactory

from .configuration_reader import ConfigurationReader


class ValidationParser:
    """
    Validation parser for validation.xml files.
    
    Converts validation.xml configuration data into ValidationRule domain models.
    """
    
    def __init__(self, config: Config):
        """
        Initialize validation rules parser.
        
        Args:
            config: Configuration instance
        """
        self.config = config
        self.reader = ConfigurationReader(config)
        self.logger = LoggerFactory.get_logger("steps.step02.validationrulesparser")
    
    def parse_validation_file(self, validation_file: FileInventoryItem) -> Optional[ConfigurationDetails]:
        """
        Parse a validation.xml file and return ConfigurationDetails.
        
        Args:
            validation_file: FileInventoryItem for the validation.xml file
            
        Returns:
            ConfigurationDetails with validation rules or None if parsing fails
        """
        try:
            self.logger.debug("Parsing validation.xml file: %s from source_location: %s", 
                             validation_file.path, validation_file.source_location)
            
            # Use ConfigurationReader to parse the validation file
            reader_result = self.reader.parse_file(validation_file.source_location, validation_file.path)
            
            if not reader_result.success or not reader_result.structural_data:
                self.logger.warning("Failed to parse validation.xml file: %s - %s", 
                                   validation_file.path, reader_result.error_message)
                return None
            
            # Create ConfigurationDetails with detected framework
            detected_framework = self.reader.determine_framework(
                reader_result.structural_data.get("config_type", "unknown"),
                reader_result.framework_hints,
                reader_result.structural_data
            )
            
            config_details = ConfigurationDetails(
                detected_framework=detected_framework,
                framework_version=self.reader.extract_framework_version(reader_result.structural_data)
            )
            
            # Convert structural data to validation rules
            self._convert_validation_rules(reader_result.structural_data, config_details)
            
            self.logger.debug("Successfully parsed validation.xml file: %s - %d validation rules", 
                             validation_file.path, len(config_details.validation_rules))
            
            return config_details
            
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Failed to parse validation.xml file %s: %s", validation_file.path, str(e))
            return None
    
    def _convert_validation_rules(
        self, 
        structural_data: Dict[str, Any], 
        config_details: ConfigurationDetails
    ) -> None:
        """
        Convert validation rules (from validation.xml).
        
        Args:
            structural_data: Raw validation data
            config_details: ConfigurationDetails to populate
        """
        forms = structural_data.get("forms", [])
        self.logger.debug("Converting validation rules from %d forms", len(forms))
        
        for form in forms:
            form_name = form.get("name", "")
            fields = form.get("fields", [])
            
            self.logger.debug("Processing form: %s with %d fields", form_name, len(fields))
            
            for field in fields:
                field_name = field.get("property", "")
                validators = field.get("depends", "").split(",") if field.get("depends") else []
                
                self.logger.debug("Processing field: %s with validators: %s", field_name, validators)
                
                # Extract all variables for this field
                field_variables = {}
                for var in field.get("vars", []):
                    var_name = var.get("var-name", "")
                    var_value = var.get("var-value", "")
                    if var_name and var_value:
                        field_variables[var_name] = var_value
                
                for validator_name in validators:
                    validator_name = validator_name.strip()
                    if validator_name:
                        # Only assign variables to validators that use them
                        variables = {}
                        if self._validator_uses_variables(validator_name):
                            variables = field_variables.copy()
                        
                        # Extract error message
                        error_message_key = None
                        for msg in field.get("msgs", []):
                            if msg.get("name") == validator_name:
                                error_message_key = msg.get("key", "")
                                break
                        
                        validation_rule = ValidationRule(
                            form_name=form_name,
                            field_reference=field_name,
                            validation_type=validator_name,
                            validation_variables=variables,
                            error_message_key=error_message_key,
                            framework="struts_1x",
                            validation_source="xml"
                        )
                        config_details.validation_rules.append(validation_rule)
                        
                        self.logger.debug("Created validation rule: %s.%s (%s)", 
                                         form_name, field_name, validator_name)

    def _validator_uses_variables(self, validator_name: str) -> bool:
        """
        Determine if a validator uses variables.
        
        Args:
            validator_name: Name of the validator
            
        Returns:
            True if the validator uses variables, False otherwise
        """
        # List of validators that typically use variables
        variable_using_validators = {
            "intRange", "floatRange", "doubleRange",
            "minlength", "maxlength", "mask", "date",
            "creditCard", "email", "url"
        }
        
        return validator_name in variable_using_validators
