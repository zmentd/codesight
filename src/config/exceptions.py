"""Configuration exceptions for CodeSight."""


class ConfigurationError(Exception):
    """Base configuration error."""
    pass


class ConfigValidationError(ConfigurationError):
    """Configuration validation error."""
    pass


class ConfigFileNotFoundError(ConfigurationError):
    """Configuration file not found error."""
    pass


class ConfigLoadError(ConfigurationError):
    """Configuration loading error."""
    pass


class ProjectConfigError(ConfigurationError):
    """Project-specific configuration error."""
    pass
