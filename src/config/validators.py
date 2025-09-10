"""Configuration validation for CodeSight."""

from dataclasses import dataclass
from typing import Any, Dict, List

from .exceptions import ConfigValidationError


@dataclass
class ValidationError:
    """Configuration validation error."""
    field: str
    message: str
    value: Any = None


@dataclass
class ValidationWarning:
    """Configuration validation warning."""
    field: str
    message: str
    value: Any = None


@dataclass
class ValidationResult:
    """Configuration validation result."""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationWarning]
    recommendations: List[str]


class ConfigValidator:
    """Configuration validation and error reporting."""
    
    def validate_config(self, config: Any) -> ValidationResult:
        """
        Validate complete configuration.
        
        Args:
            config: Configuration object to validate
            
        Returns:
            Validation result
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        recommendations: List[str] = []
        
        # Validate LLM configuration
        llm_errors = self.validate_llm_config(config.llm)
        errors.extend(llm_errors)
        
        # Validate step configurations
        for step_name in ['step01', 'step02', 'step03', 'step04', 'step05', 'step06', 'step07']:
            step_config = getattr(config.steps, step_name)
            step_errors = self.validate_step_config(step_name, step_config)
            errors.extend(step_errors)
        
        # Validate paths exist
        path_errors = self._validate_paths(config)
        errors.extend(path_errors)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            recommendations=recommendations
        )
    
    def validate_llm_config(self, llm_config: Any) -> List[ValidationError]:
        """
        Validate LLM provider configuration.
        
        Args:
            llm_config: LLM configuration to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Validate provider selection
        valid_providers = ['ollama', 'openai', 'kong_aws', 'kong_azure', 'kong_gcp']
        if llm_config.provider not in valid_providers:
            errors.append(ValidationError(
                field='llm.provider',
                message=f'Invalid provider. Must be one of: {valid_providers}',
                value=llm_config.provider
            ))
        
        # Validate temperature range
        if not 0.0 <= llm_config.temperature <= 2.0:
            errors.append(ValidationError(
                field='llm.temperature',
                message='Temperature must be between 0.0 and 2.0',
                value=llm_config.temperature
            ))
        
        # Validate max_tokens
        if llm_config.max_tokens <= 0:
            errors.append(ValidationError(
                field='llm.max_tokens',
                message='max_tokens must be positive',
                value=llm_config.max_tokens
            ))
        
        return errors
    
    def validate_step_config(self, step_name: str, step_config: Any) -> List[ValidationError]:
        """
        Validate individual step configuration.
        
        Args:
            step_name: Name of the step
            step_config: Step configuration to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Step-specific validation
        if step_name == 'step01':
            if not step_config.include_extensions:
                errors.append(ValidationError(
                    field=f'{step_name}.include_extensions',
                    message='include_extensions cannot be empty'
                ))
        
        elif step_name == 'step02':
            if not step_config.java_parser_jar_path:
                errors.append(ValidationError(
                    field=f'{step_name}.java_parser_jar_path',
                    message='java_parser_jar_path is required'
                ))
        
        elif step_name == 'step05':
            if step_config.batch_size <= 0:
                errors.append(ValidationError(
                    field=f'{step_name}.batch_size',
                    message='batch_size must be positive',
                    value=step_config.batch_size
                ))
        
        return errors
    
    def validate_project_config(self, project_config: Any) -> List[ValidationError]:
        """
        Validate project-specific configuration.
        
        Args:
            project_config: Project configuration to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Validate required fields
        if not project_config.default_source_path:
            errors.append(ValidationError(
                field='project.default_source_path',
                message='default_source_path is required'
            ))
        
        if not project_config.default_output_path:
            errors.append(ValidationError(
                field='project.default_output_path',
                message='default_output_path is required'
            ))
        
        return errors
    
    def validate_environment_variables(self) -> List[ValidationError]:
        """
        Validate required environment variables.
        
        Returns:
            List of validation errors
        """
        errors: List[ValidationError] = []
        
        # Add environment variable validation if needed
        # Example: Check for required API keys
        
        return errors
    
    def _validate_paths(self, config: Any) -> List[ValidationError]:
        """
        Validate file paths in configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            List of validation errors
        """
        errors: List[ValidationError] = []
        
        # Add path validation logic here
        # Example: Check if JAR files exist
        
        return errors
