"""
Simplified configuration management for CodeSight pipeline.
Provides direct attribute access with minimal complexity while maintaining
the exact same structure and override functionality.
"""


import logging
from typing import Any, Dict, List, Optional

from .loaders import ConfigLoader
from .project_config import ProjectConfigManager
from .providers import LLMConfig
from .sections import (
    AnalysisConfig,
    ArchitecturalPatternsConfig,
    ClassificationConfig,
    DatabaseConfig,
    DebugConfig,
    EnvironmentConfig,
    FrameworkConfig,
    FrameworksConfig,
    JspAnalysisConfig,
    LanguagesPatternsConfig,
    OutputConfig,
    ParsersConfig,
    PatternConfig,
    PerformanceConfig,
    ProjectConfig,
    ProvenanceConfig,
    QualityGatesConfig,
    StepsConfig,
    ThreadingConfig,
    ValidationConfig,
)

logger = logging.getLogger('config')


class Config:
    """Simple singleton configuration class with direct attribute access."""
    _instance: Optional['Config'] = None
    _initialized: bool = False
    # Class-level path attributes for backward compatibility
    code_sight_root_path: Optional[str] = None
    projects_root_path: Optional[str] = None
    config_root_path: Optional[str] = None
    project_name_path: Optional[str] = None
    project_output_path: Optional[str] = None

    def __new__(cls) -> 'Config':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        # Initialize _instance_initialized first
        if not hasattr(self, '_instance_initialized'):
            self._instance_initialized = False
            
        if self._instance_initialized:
            return
        
        # Initialize all configuration sections with defaults
        self.analysis = AnalysisConfig()
        self.project = ProjectConfig()
        self.environment = EnvironmentConfig()
        self.threading = ThreadingConfig()
        self.performance = PerformanceConfig()
        self.validation = ValidationConfig()
        self.parsers = ParsersConfig()
        self.output = OutputConfig()
        self.framework = FrameworkConfig()
        self.pattern = PatternConfig()
        self.debug = DebugConfig()
        self.steps = StepsConfig()
        self.classification = ClassificationConfig()
        self.database = DatabaseConfig()
        self.languages_patterns = LanguagesPatternsConfig()
        self.frameworks = FrameworksConfig()
        self.architectural_patterns = ArchitecturalPatternsConfig()
        self.llm = LLMConfig()
        self.jsp_analysis = JspAnalysisConfig()
        # New sections
        self.quality_gates = QualityGatesConfig()
        self.provenance = ProvenanceConfig()
        
        # Additional properties
        self.project_name = None
        self.projects_root_path = None
        self.config_file_path = None
        self.project_manager = ProjectConfigManager()
        
        self._instance_initialized = True
    
    @staticmethod
    def initialize(config_path: Optional[str] = None, project_name: Optional[str] = None, projects_root: Optional[str] = None) -> 'Config':
        """Initialize global configuration from YAML file with project overrides."""
        instance = Config()
        
        # Use ConfigLoader to handle all initialization logic (including setting class paths)
        # Convert None values to empty strings or provide defaults as needed
        ConfigLoader.initialize_config_object(
            instance, 
            config_path or "", 
            project_name or "", 
            projects_root or ""
        )
        
        # Mark as properly initialized at class level
        Config._initialized = True
        
        return instance
    
    @staticmethod
    def get_instance() -> 'Config':
        """Get the singleton configuration instance."""
        if Config._instance is None or not Config._initialized:
            from .exceptions import ConfigurationError
            raise ConfigurationError("Configuration not initialized. Call initialize() first.")
        return Config._instance
    
    @staticmethod
    def reset() -> None:
        """Reset singleton instance (for testing)."""
        Config._instance = None
        Config._initialized = False
    
    def get_project_source_path(self, project_name: Optional[str] = None) -> str:
        """Get source path for specific project or current project."""
        if project_name:
            return self.project_manager.get_project_source_path(project_name)
        return self.project.source_path or "source"
    
    def get_project_output_path(self, project_name: Optional[str] = None) -> str:
        """Get output path for specific project or current project."""
        # if project_name:
        #     return self.project_manager.get_project_output_path(project_name)
        return self.project.output_path or "output"
  
    def get_output_dir_for_step(self, step_name: str, default_filename: Optional[str] = None) -> str:
        """Get the output path for a specific step (backward compatibility)."""
        if hasattr(self.steps, step_name):
            step_config = getattr(self.steps, step_name)
            if hasattr(step_config, 'output_path') and step_config.output_path:
                return str(step_config.output_path)
        
        # Fallback: construct path from project output path
        base_path = self.get_project_output_path()
        
        return f"{base_path}/{step_name}"

    def get_output_path_for_step(self, step_name: str, default_filename: Optional[str] = None) -> str:
        """Get the output path for a specific step (backward compatibility)."""
        if hasattr(self.steps, step_name):
            step_config = getattr(self.steps, step_name)
            if hasattr(step_config, 'output_path') and step_config.output_path:
                return str(step_config.output_path)
        
        # Fallback: construct path from project output path
        base_path = self.get_project_output_path()
        base_name = default_filename or step_name
        filename = base_name + "_output.json"
        
        return f"{base_path}/{filename}"

    def get_project_embeddings_path(self) -> str:
        """
        Get embeddings path for specific project.

        Args:
            project_name: Name of the project
            
        Returns:
            Embeddings path for the project
        """
        project_name = self.project_name or "default_project"
        embeddings_path = f"projects/{project_name}/embeddings"
        if hasattr(self.steps, "step03"):
            step_config = getattr(self.steps, "step03")
            if hasattr(step_config, 'output_path') and step_config.output_path:
                return str(step_config.output_path)
            embeddings_directory = step_config.storage.embeddings_directory
            if embeddings_directory:
                embeddings_path = str(embeddings_directory)
                if "{project_name}" in embeddings_path:
                    embeddings_path = embeddings_path.replace("{project_name}", project_name)

        return embeddings_path
  
    def __repr__(self) -> str:
        """String representation."""
        info = []
        info.append(f"project={self.project_name}")
        if hasattr(self.llm, 'provider'):
            info.append(f"llm={self.llm.provider}")
        if hasattr(self.environment, 'environment'):
            info.append(f"env={self.environment.environment}")
        
        return f"Config({', '.join(info)})"


# Global access functions (same interface as before)
def get_config() -> Config:
    """Get the global configuration instance."""
    return Config.get_instance()


def initialize_config(config_path: Optional[str] = None, project_name: Optional[str] = None, projects_root: Optional[str] = None) -> Config:
    """Initialize global configuration with base config and project overrides."""
    return Config.initialize(config_path, project_name, projects_root)


def reset_config() -> Config:
    """Reset configuration singleton (for testing)."""
    Config.reset()
    return Config.get_instance()

