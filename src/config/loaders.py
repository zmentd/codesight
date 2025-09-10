"""Configuration loading utilities for CodeSight pipeline."""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml  # type: ignore[import-untyped]

logger = logging.getLogger('config.loader')


class ConfigLoader:
    """Static utility class for loading, processing, and initializing configuration."""
    
    @staticmethod
    def load_yaml(file_path: str) -> Dict[str, Any]:
        """
        Load YAML configuration from file with environment variable substitution.
        
        Args:
            file_path: Path to YAML file
            
        Returns:
            Dictionary containing configuration data
        """
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        # Substitute environment variables
        content = ConfigLoader._substitute_env_vars(content)
        
        return yaml.safe_load(content) or {}
    
    @staticmethod
    def _substitute_env_vars(content: str) -> str:
        """
        Substitute environment variables in configuration content.
        Supports ${VAR_NAME} and ${VAR_NAME:default_value} syntax.
        
        Args:
            content: Configuration file content
            
        Returns:
            Content with environment variables substituted
        """
        def replace_var(match: Any) -> str:
            var_expr = match.group(1)
            if ':' in var_expr:
                var_name, default_value = var_expr.split(':', 1)
                return os.getenv(var_name, default_value)
            else:
                return os.getenv(var_expr, '')
        
        return re.sub(r'\$\{([^}]+)\}', replace_var, content)
    
    @staticmethod
    def merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge override configuration into base configuration.
        
        Args:
            base_config: Base configuration dictionary
            override_config: Override configuration dictionary
            
        Returns:
            Merged configuration dictionary
        """
        def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
            result = base.copy()
            
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = _deep_merge(result[key], value)
                else:
                    result[key] = value
            
            return result
        
        return _deep_merge(base_config, override_config)
    
    @staticmethod
    def validate_config_path(path: str) -> Path:
        """
        Validate and normalize configuration file path.
        
        Args:
            path: Configuration file path
            
        Returns:
            Normalized Path object
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        return config_path
    
    @staticmethod
    def initialize_config_object(config_obj: Any, config_path: Optional[str] = None, project_name: Optional[str] = None, projects_root: Optional[str] = None) -> None:
        """
        Initialize a configuration object by loading base config and applying project overrides.
        
        Args:
            config_obj: The configuration object to initialize
            config_path: Path to main configuration file (absolute path recommended)
            project_name: Name of specific project for overrides
            projects_root: Root directory for project configurations (absolute path recommended)
        """
        # Set paths with robust resolution
        if config_path:
            config_obj.config_file_path = Path(config_path).resolve()
        else:
            # Try multiple fallback locations for config.yaml
            config_obj.config_file_path = ConfigLoader._find_config_file()
        
        config_obj.project_name = project_name
        
        if projects_root:
            config_obj.projects_root_path = Path(projects_root).resolve()
        else:
            # Try multiple fallback locations for projects directory
            config_obj.projects_root_path = ConfigLoader._find_projects_root()
        
        # Load and apply configuration
        ConfigLoader._load_configuration(config_obj)
        
        logger.info("Configuration initialized: %s", config_obj.config_file_path)
        if project_name:
            logger.info("Project overrides applied: %s", project_name)
    
    @staticmethod
    def _load_configuration(config_obj: Any) -> None:
        """Load base configuration and apply project overrides."""
        try:
            # Load base configuration
            base_config = ConfigLoader.load_yaml(str(config_obj.config_file_path))
            ConfigLoader._apply_config_data(config_obj, base_config)
            
            # Apply project overrides if specified
            if config_obj.project_name:
                ConfigLoader._apply_project_overrides(config_obj)
            
            # Set class-level path attributes after all configuration is loaded
            ConfigLoader._set_class_paths(config_obj)
                
        except Exception as e:
            logger.error("Configuration loading failed: %s", e)
            from .exceptions import ConfigurationError
            raise ConfigurationError(f"Failed to load configuration: {e}") from e
    
    @staticmethod
    def _apply_config_data(config_obj: Any, config_data: Dict[str, Any]) -> None:
        """Apply configuration data to section objects."""
        for section_name, section_data in config_data.items():
            if hasattr(config_obj, section_name) and section_data:
                section_obj = getattr(config_obj, section_name)
                ConfigLoader._update_section_object(section_obj, section_data)
    
    @staticmethod
    def _update_section_object(section_obj: Any, section_data: Dict[str, Any]) -> None:
        """Recursively update section object attributes with configuration data."""
        
        # Special handling for ArchitecturalPatternsConfig field name mapping
        from .sections import ArchitecturalPatternsConfig
        if isinstance(section_obj, ArchitecturalPatternsConfig):
            # Map snake_case YAML keys to PascalCase class attributes
            field_mapping = {
                'application': 'Application',
                'business': 'Business',
                'data_access': 'DataAccess',
                'security': 'Security',
                'shared': 'Shared'
            }
            
            for yaml_key, value in section_data.items():
                class_attr = field_mapping.get(yaml_key)
                if class_attr and hasattr(section_obj, class_attr):
                    setattr(section_obj, class_attr, value)
                elif hasattr(section_obj, yaml_key):
                    # Fallback to direct mapping if no field mapping exists
                    setattr(section_obj, yaml_key, value)
        
        # Special handling for LLMConfig to ensure provider is set before model
        elif hasattr(section_obj, '__class__') and section_obj.__class__.__name__ == 'LLMConfig':
            # Set provider first if it exists
            if 'provider' in section_data:
                setattr(section_obj, 'provider', section_data['provider'])
            
            # Then set other attributes
            for key, value in section_data.items():
                if key == 'provider':
                    continue  # Already handled above
                if hasattr(section_obj, key):
                    current_attr = getattr(section_obj, key)
                    
                    # Handle nested objects (like step configs, provider configs)
                    if hasattr(current_attr, '__dict__') and isinstance(value, dict):
                        ConfigLoader._update_section_object(current_attr, value)
                    else:
                        setattr(section_obj, key, value)
        else:
            # Normal processing for other objects
            for key, value in section_data.items():
                if hasattr(section_obj, key):
                    current_attr = getattr(section_obj, key)
                    
                    # Handle nested objects (like step configs, provider configs)
                    if hasattr(current_attr, '__dict__') and isinstance(value, dict):
                        ConfigLoader._update_section_object(current_attr, value)
                    else:
                        setattr(section_obj, key, value)
    
    @staticmethod
    def _apply_project_overrides(config_obj: Any) -> None:
        """Load and apply project-specific configuration overrides."""
        try:
            # Load project configuration
            project_config = ConfigLoader._load_project_config(config_obj.project_name, config_obj.projects_root_path)
            if project_config:
                # Update project section
                if project_config.name:
                    config_obj.project.name = project_config.name
                if project_config.description:
                    config_obj.project.description = project_config.description
                if project_config.source_path:
                    config_obj.project.source_path = project_config.source_path
                if project_config.output_path:
                    config_obj.project.output_path = project_config.output_path
                
                # Apply step overrides
                if project_config.step_overrides:
                    for step_name, step_data in project_config.step_overrides.items():
                        if hasattr(config_obj.steps, step_name):
                            step_obj = getattr(config_obj.steps, step_name)
                            ConfigLoader._update_section_object(step_obj, step_data)
                
                # Apply other overrides
                if project_config.llm_overrides:
                    ConfigLoader._update_section_object(config_obj.llm, project_config.llm_overrides)
                
                if project_config.classification_overrides:
                    ConfigLoader._update_section_object(config_obj.classification, project_config.classification_overrides)
                
                if project_config.architectural_patterns_overrides:
                    ConfigLoader._update_section_object(config_obj.architectural_patterns, project_config.architectural_patterns_overrides)
                
                if project_config.frameworks_overrides:
                    ConfigLoader._update_section_object(config_obj.frameworks, project_config.frameworks_overrides)
                
                if project_config.languages_patterns_overrides:
                    ConfigLoader._update_section_object(config_obj.languages_patterns, project_config.languages_patterns_overrides)

                # Apply jsp_analysis overrides (always if present in project config)
                if hasattr(project_config, 'jsp_analysis_overrides'):
                    if project_config.jsp_analysis_overrides:
                        ConfigLoader._update_section_object(config_obj.jsp_analysis, project_config.jsp_analysis_overrides)
        except (FileNotFoundError, PermissionError, yaml.YAMLError) as e:
            logger.warning("Failed to apply project overrides for %s: %s", config_obj.project_name, e)
    
    @staticmethod
    def _set_class_paths(config_obj: Any) -> None:
        """Set class-level path attributes on Config after all configuration is loaded."""
        try:
            # Import here to avoid circular imports
            from .config import Config

            # Find project root
            project_root = ConfigLoader._find_project_root()
            
            # Set class-level paths
            Config.code_sight_root_path = str(project_root)
            Config.projects_root_path = str(project_root / "projects")
            Config.config_root_path = str(project_root / "config")
            
            # Set project-specific paths if project is specified
            if config_obj.project_name:
                Config.project_name_path = str(project_root / "projects" / config_obj.project_name)
                Config.project_output_path = str(project_root / "projects" / config_obj.project_name / "output")
            else:
                Config.project_name_path = None
                Config.project_output_path = None
                
            logger.debug("Class paths set - root: %s, project: %s", Config.code_sight_root_path, Config.project_name_path)
            
        except (AttributeError, ImportError) as e:
            logger.warning("Failed to set class paths: %s", e)
    
    @staticmethod
    def _load_project_config(project_name: str, projects_root_path: Path) -> Optional[Any]:
        """Load project-specific configuration."""
        try:
            config_path = projects_root_path / project_name / f"config-{project_name}.yaml"
            if not config_path.exists():
                return None
            
            config_data = ConfigLoader.load_yaml(str(config_path))
            
            # Create project config object
            from .project_config import ProjectSpecificConfig
            project_data = config_data.get('project', {})
            
            # Resolve source_path relative to the project config file directory
            source_path = project_data.get('source_path', f'projects/{project_name}/source')
            if not Path(source_path).is_absolute():
                # Resolve relative to the project config file's directory
                project_config_dir = config_path.parent
                resolved_source_path = (project_config_dir / source_path).resolve()
                source_path = str(resolved_source_path)
            
            project_config = ProjectSpecificConfig(
                name=project_data.get('name', project_name),
                description=project_data.get('description', ''),
                source_path=source_path,
                output_path=project_data.get('output_path', f'projects/{project_name}/output'),
                step_overrides=config_data.get('steps', {}),
                llm_overrides=config_data.get('llm', {}),
                classification_overrides=config_data.get('classification', {}),
                architectural_patterns_overrides=config_data.get('architectural_patterns', {}),
                frameworks_overrides=config_data.get('frameworks', {}),
                languages_patterns_overrides=config_data.get('languages_patterns', {}),
                jsp_analysis_overrides=config_data.get('jsp_analysis', {}),
            )
            
            return project_config
            
        except (FileNotFoundError, PermissionError, yaml.YAMLError) as e:
            logger.warning("Failed to load project config for %s: %s", project_name, e)
            return None
    
    @staticmethod
    def _find_config_file() -> Path:
        """
        Find config.yaml file by searching in multiple locations.
        
        Returns:
            Path to config.yaml file
            
        Raises:
            FileNotFoundError: If config.yaml is not found in any location
        """
        # 1. Environment variable (highest priority)
        env_path = os.getenv('CODESIGHT_CONFIG_PATH')
        if env_path and Path(env_path).exists():
            logger.debug("Found config file via environment variable: %s", env_path)
            return Path(env_path).resolve()
        
        # 2. Find project root and look for config there
        try:
            project_root = ConfigLoader._find_project_root()
            config_path = project_root / "config" / "config.yaml"
            if config_path.exists():
                logger.debug("Found config file in project root: %s", config_path)
                return config_path.resolve()
        except FileNotFoundError:
            pass  # Continue with other search methods
        
        # 3. Additional fallback locations
        search_locations = [
            # Current working directory
            Path.cwd() / "config" / "config.yaml",
            Path.cwd() / "config.yaml",
            # Relative to this module (last resort)
            Path(__file__).parent.parent.parent / "config" / "config.yaml",
        ]
        
        for config_path in search_locations:
            if config_path.exists():
                logger.debug("Found config file at: %s", config_path)
                return config_path.resolve()
        
        # If not found, create a helpful error message
        searched_paths = [env_path] if env_path else []
        searched_paths.extend([str(p) for p in search_locations])
        raise FileNotFoundError(
            "config.yaml not found in any of these locations:\n" + 
            "\n".join(f"  - {path}" for path in searched_paths if path) +
            f"\n\nCurrent working directory: {Path.cwd()}" +
            f"\nModule location: {Path(__file__).parent}" +
            "\n\nSet CODESIGHT_CONFIG_PATH environment variable or provide explicit config_path parameter."
        )
    
    @staticmethod
    def _find_project_root() -> Path:
        """
        Find the CodeSight project root by walking up the directory tree.
        Similar to the old find_root_path but more flexible.
        
        Returns:
            Path to project root directory
            
        Raises:
            FileNotFoundError: If project root not found
        """
        logger.debug("Searching for CodeSight project root directory")
        start = Path.cwd()
        current = start.resolve()
        logger.debug("Starting search from: %s", current)
        
        while current != current.parent:
            logger.debug("Checking directory: %s", current)
            
            # Look for CodeSight project markers
            if current.name.lower() == "codesight":
                # Check for workflow subdirectory (original marker)
                if any(child.is_dir() and child.name.lower() == "workflow" for child in current.iterdir()):
                    logger.info("Found CodeSight root directory: %s", current)
                    return current
            
            # Also look for config directory as a marker
            if (current / "config" / "config.yaml").exists():
                logger.info("Found project root via config.yaml: %s", current)
                return current
            
            # Look for other project markers
            if (current / "workflow").exists() and (current / "projects").exists():
                logger.info("Found project root via structure: %s", current)
                return current
            
            current = current.parent
        
        logger.warning("Could not find CodeSight root folder starting from %s", start)
        raise FileNotFoundError(f"Could not find the CodeSight project root starting from {start}")
    
    @staticmethod
    def _find_projects_root() -> Path:
        """
        Find projects root directory by searching in multiple locations.
        
        Returns:
            Path to projects directory
        """
        # 1. Environment variable (highest priority)
        env_path = os.getenv('CODESIGHT_PROJECTS_ROOT')
        if env_path and Path(env_path).exists():
            logger.debug("Found projects directory via environment variable: %s", env_path)
            return Path(env_path).resolve()
        
        # 2. Find project root and look for projects there
        try:
            project_root = ConfigLoader._find_project_root()
            projects_path = project_root / "projects"
            if projects_path.exists() and projects_path.is_dir():
                logger.debug("Found projects directory in project root: %s", projects_path)
                return projects_path.resolve()
        except FileNotFoundError:
            pass  # Continue with other methods
        
        # 3. Fallback locations
        search_locations = [
            Path.cwd() / "projects",
            Path.cwd().parent / "projects",
        ]
        
        for projects_path in search_locations:
            if projects_path.exists() and projects_path.is_dir():
                logger.debug("Found projects directory at: %s", projects_path)
                return projects_path.resolve()
        
        # If not found, use fallback location (will be created if needed)
        fallback_path = Path.cwd() / "projects"
        logger.warning("Projects directory not found, using fallback: %s", fallback_path)
        return fallback_path.resolve()
