"""Project-specific configuration management."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .exceptions import ProjectConfigError
from .loaders import ConfigLoader


@dataclass
class ProjectSpecificConfig:
    """Project-specific configuration section."""
    name: str
    description: str
    source_path: str
    output_path: str
    
    # Project-specific step overrides
    step_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Project-specific LLM settings
    llm_overrides: Dict[str, Any] = field(default_factory=dict)
    
    # Project-specific classification settings
    classification_overrides: Dict[str, Any] = field(default_factory=dict)
    architectural_patterns_overrides: Dict[str, List[str]] = field(default_factory=dict)
    # Project-specific jsp_analysis settings
    jsp_analysis_overrides: Dict[str, Any] = field(default_factory=dict)
    # Project-specific frameworks settings
    frameworks_overrides: Dict[str, Any] = field(default_factory=dict)
    
    # Project-specific language patterns settings
    languages_patterns_overrides: Dict[str, Any] = field(default_factory=dict)


class ProjectConfigManager:
    """Manages project-specific configuration loading and merging."""
    
    def __init__(self) -> None:
        self.loaded_projects: Dict[str, ProjectSpecificConfig] = {}
    
    def load_project_config(self, project_name: str) -> Optional[ProjectSpecificConfig]:
        """
        Load project-specific configuration from config-<project>.yaml
        
        Args:
            project_name: Name of the project
            
        Returns:
            ProjectSpecificConfig or None if not found
        """
        if project_name in self.loaded_projects:
            return self.loaded_projects[project_name]
        
        try:
            # Use the Config class's projects_root_path
            from .config import Config
            if hasattr(Config, 'projects_root_path') and Config.projects_root_path:
                projects_root = Config.projects_root_path
            else:
                # Fallback to original path resolution if Config not initialized
                projects_root = str(Path(__file__).parent.parent.parent.parent / "projects")
            
            config_path = Path(projects_root) / project_name / f"config-{project_name}.yaml"
            if not config_path.exists():
                return None
            
            config_data = ConfigLoader.load_yaml(str(config_path))
            
            # Extract project section
            project_data = config_data.get('project', {})
            
            project_config = ProjectSpecificConfig(
                name=project_data.get('name', project_name),
                description=project_data.get('description', ''),
                source_path=project_data.get('source_path', f'projects/{project_name}/source'),
                output_path=project_data.get('output_path', f'projects/{project_name}/output'),
                step_overrides=config_data.get('steps', {}),
                llm_overrides=config_data.get('llm', {}),
                classification_overrides=config_data.get('classification', {}),
                architectural_patterns_overrides=config_data.get('architectural_patterns', {}),
                frameworks_overrides=config_data.get('frameworks', {}),
                languages_patterns_overrides=config_data.get('languages_patterns', {}),
                jsp_analysis_overrides=config_data.get('jsp_analysis', {}),
            )
            
            self.loaded_projects[project_name] = project_config
            return project_config
            
        except Exception as e:
            raise ProjectConfigError(f"Failed to load project config for {project_name}: {e}") from e
    
    def merge_project_overrides(self, base_config: Any, project_config: ProjectSpecificConfig) -> Any:
        """
        Merge project-specific overrides into base configuration.
        
        Args:
            base_config: Base configuration object
            project_config: Project-specific configuration
            
        Returns:
            Merged configuration object
        """
        # Import here to avoid circular imports
        # Create a copy of the base config (shallow copy is fine for our use case)
        import copy

        from .sections import ArchitecturalPatternsConfig, ClassificationConfig
        merged_config = copy.copy(base_config)
        
        # Merge classification overrides
        if project_config.classification_overrides:
            classification_data = project_config.classification_overrides
            merged_config.classification = ClassificationConfig(
                layers=classification_data.get('layers', base_config.classification.layers),
                confidence_threshold=classification_data.get('confidence_threshold', base_config.classification.confidence_threshold),
                require_dual_match=classification_data.get('require_dual_match', base_config.classification.require_dual_match),
                fallback_layer=classification_data.get('fallback_layer', base_config.classification.fallback_layer)
            )
        
        # Merge architectural patterns overrides
        if project_config.architectural_patterns_overrides:
            patterns_data = project_config.architectural_patterns_overrides
            merged_config.architectural_patterns = ArchitecturalPatternsConfig(
                Application=patterns_data.get('application', base_config.architectural_patterns.Application) or [],
                Business=patterns_data.get('business', base_config.architectural_patterns.Business) or [],
                DataAccess=patterns_data.get('data_access', base_config.architectural_patterns.DataAccess) or [],
                Shared=patterns_data.get('shared', base_config.architectural_patterns.Shared) or []
            )
        
        # Merge language patterns overrides
        if project_config.languages_patterns_overrides:
            # This is more complex because LanguagesPatternsConfig has nested structure
            # For now, keep the base config
            pass
        
        # Merge frameworks overrides
        if project_config.frameworks_overrides:
            # Keep the base config for now
            pass
        
        return merged_config
    
    def get_project_source_path(self, project_name: str) -> str:
        """
        Get source path for specific project.
        
        Args:
            project_name: Name of the project
            
        Returns:
            Source path for the project
        """
        project_config = self.load_project_config(project_name)
        if project_config:
            return project_config.source_path
        return f"projects/{project_name}/source"
    
    def get_project_output_path(self, project_name: str) -> str:
        """
        Get output path for specific project.
        
        Args:
            project_name: Name of the project
            
        Returns:
            Output path for the project
        """
        project_config = self.load_project_config(project_name)
        if project_config:
            return project_config.output_path
        return f"projects/{project_name}/output"
