"""
Base file classifier for all language-specific classifiers.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import Config
from domain.source_inventory import (
    ArchitecturalLayerType,
    ArchitecturalPattern,
    EnumUtils,
    LayerType,
    PackageLayer,
    PatternType,
)
from utils.logging.logger_factory import LoggerFactory

from ..models.classification_models import FileClassification, LayerMatch
from ..utils.pattern_matcher import PatternMatcher


class BaseFileClassifier(ABC):
    """Abstract base class for all file type classifiers."""
    
    def __init__(self, config: Config, pattern_matcher: PatternMatcher):
        self.config = config
        self.pattern_matcher = pattern_matcher
        self.logger = LoggerFactory.get_logger(f"classifier.{self.__class__.__name__}")
    
    @abstractmethod
    def can_handle(self, file_info: Dict[str, Any]) -> bool:
        """Check if this classifier can handle the file type."""
        raise NotImplementedError("Subclasses must implement can_handle method")
    
    @abstractmethod
    def classify(self, file_info: Dict[str, Any]) -> FileClassification:
        """Classify the file and return classification results."""
        raise NotImplementedError("Subclasses must implement classify method")
    
    def generate_framework_hints(self, file_info: Dict[str, Any]) -> List[str]:
        """
        Generate framework hints - default implementation.
        Can be overridden by specific classifiers.
        """
        # Framework hint generation based on file content sampling
        # This would check file content against framework indicators from config
        return []

    def match_package_patterns(self, package_name: str) -> Optional[LayerMatch]:
        raise NotImplementedError("Subclasses must implement match_package_patterns method")

    def map_layer_to_subdomain_type(self, layer: str) -> str:
        """
        Map configuration layer to TARGET_SCHEMA subdomain type.
        Copied from existing _map_layer_to_component_type.
        """
        layer_mapping = {
            'UI': 'screen',
            'Service': 'service',
            'Database': 'service',  # DSL is database access but still service layer
            'Integration': 'integration',
            'Reporting': 'reporting',
            'Configuration': 'utility',
            'Utility': 'utility',
            'Other': 'utility'
        }
        
        return layer_mapping.get(layer, 'utility')
    
    def infer_package_layer_from_architectural_pattern(self, architectural_pattern: str) -> Optional[str]:
        """
        Infer package layer from architectural pattern for STORM architecture.
        Copied from existing logic.
        
        Args:
            architectural_pattern: The detected architectural pattern (application, business, data_access, shared)
            
        Returns:
            Inferred package layer name or None
        """
        # STORM architectural pattern to package layer mapping
        pattern_to_layer_mapping = {
            'application': 'UI',           # ASL -> Application/UI layer
            'business': 'Service',         # GSL -> Business/Service layer  
            'data_access': 'Database',     # DSL -> Data Access/Database layer
            'security': 'Utility',        # Security -> Utility layer (closest match)
            'shared': 'Utility'            # ISL -> Infrastructure/Utility layer
        }
        
        inferred_layer = pattern_to_layer_mapping.get(architectural_pattern)
        self.logger.debug("      Inference mapping: %s -> %s", architectural_pattern, inferred_layer)
        return inferred_layer
    
    def detect_architectural_pattern(self, file_path: str) -> Optional[ArchitecturalPattern]:
        """
        Detect STORM architectural pattern from file path.
        Copied from existing _detect_architectural_pattern_from_path logic.
        
        Args:
            file_path: File path to analyze
            
        Returns:
            ArchitecturalPattern or None
        """
        if not hasattr(self.config, 'architectural_patterns'):
            return None
        
        arch_patterns = self.config.architectural_patterns
        arch_patern = None
        self.logger.debug("Detecting architectural pattern for file path: %s", file_path)
        self.logger.debug("Using architectural patterns : %s", arch_patterns)
        # Check each architectural pattern from configuration
        for config_key in ['Application', 'Business', 'DataAccess', 'Shared', 'Security']:
            self.logger.debug("      Checking config key: %s", config_key)
            enum = EnumUtils.to_architectural_layer_type(config_key)
            if hasattr(arch_patterns, config_key):
                patterns = getattr(arch_patterns, config_key)
                self.logger.debug("      Checking patterns for %s: %s", config_key, patterns)
                # Use glob-style matching directly on the file path
                if patterns:  # Only process if we have actual patterns
                    for pattern in patterns:
                        # Use glob-style matching directly on the file path
                        self.logger.debug("      Checking pattern: %s", pattern)
                        # Convert glob pattern to regex for matching
                        if self.pattern_matcher.matches(file_path, pattern):
                            arch_patern = ArchitecturalPattern(
                                pattern=pattern,  # The specific glob pattern that matched
                                architectural_layer=enum,  # The business layer name
                                pattern_type=PatternType.DIRECTORY_BASED,
                                confidence=0.9
                            )
        self.logger.debug("      Detected architectural pattern: %s", arch_patern)
        return arch_patern

    def detect_architectural_pattern_and_subdomain(self, file_info: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        """
        Detect architectural pattern and extract subdomain name from directory path.
        Shared utility for both directory scanner and file classifier.
        
        Args:
            path_parts: List of directory path components
            
        Returns:
            Tuple of (pattern_type, subdomain_name) where:
            - pattern_type: 'application', 'business', 'data_access', 'shared', or None
            - subdomain_name: actual component name (directory after arch pattern), or None
        """
        self.logger.debug("Detecting architectural pattern and subdomain for file info: %s", file_info)
        file_path = file_info.get('path', '')
        if not hasattr(self.config, 'architectural_patterns'):
            return None, None
        path_parts = file_path.split('/')
        matched_pattern = self.detect_architectural_pattern(file_path)
        
        # Build pattern mapping from config
        pattern_mapping: Dict[str, str] = {}
        arch_patterns = self.config.architectural_patterns
        pattern_type = None
        subdomain_name = None
        # Map directory names to pattern types based on config
        for config_key in ['application', 'business', 'data_access', 'security', 'shared']:
            attr_mapping = {
                'application': 'Application',
                'business': 'Business', 
                'data_access': 'DataAccess',
                'security': 'Security',
                'shared': 'Shared'
            }
            attr_name = attr_mapping.get(config_key)
            if attr_name and hasattr(arch_patterns, attr_name):
                patterns = getattr(arch_patterns, attr_name)
                if patterns:
                    for pattern in patterns:
                        # Extract directory names from patterns like "**/asl/**"
                        if '**/' in pattern and '/**' in pattern:
                            parts = pattern.split('/')
                            for part in parts:
                                if part and part != '**':
                                    pattern_mapping[part.lower()] = config_key
         
        # Check if any path part matches our architectural patterns
        for i, part in enumerate(path_parts):
            part_lower = part.lower()
            if part_lower in pattern_mapping:
                pattern_type = matched_pattern.pattern if matched_pattern else None
                # Extract subdomain name - use deepest meaningful directory after architectural pattern
                subdomain_name = None
                if i + 1 < len(path_parts):
                    # Get all directories after the architectural pattern
                    remaining_parts = path_parts[i + 1:]
                    
                    # Filter out generic/technical directories to find meaningful business domains
                    generic_dirs = {'xhtml', 'config', 'common', 'util', 'shared', 'resources'}
                    meaningful_parts = [part for part in remaining_parts 
                                       if part and part.lower() not in generic_dirs]
                    
                    if meaningful_parts:
                        # Use the deepest meaningful directory for business domain specificity
                        subdomain_name = meaningful_parts[-1]
                    else:
                        # Fallback to first directory if no meaningful ones found
                        subdomain_name = remaining_parts[0] if remaining_parts else part
                else:
                    subdomain_name = part
                break
        
        self.logger.debug("      Detected pattern_type: %s, subdomain_name: %s", pattern_type, subdomain_name)
        return pattern_type, subdomain_name

    def detect_package_layer(self, file_info: Dict[str, Any]) -> Optional[PackageLayer]:
        raise NotImplementedError("Subclasses must implement detect_package_layer method")

    def extract_component_from_filename(self, filename: str) -> str:
        """Extract component name from filename."""
        return Path(filename).stem
    
    def create_none_architectural_info(self) -> ArchitecturalPattern:
        """Create default 'none' architectural info."""
        return ArchitecturalPattern(
            pattern='none',
            architectural_layer=ArchitecturalLayerType.UNKNOWN,
            pattern_type=PatternType.NONE,
            confidence=0.0
        )
    
    def create_none_package_layer_info(self) -> PackageLayer:
        """Create default 'none' package layer info."""
        return PackageLayer(
            layer=LayerType.NONE,
            pattern_type=PatternType.NONE,
            confidence=0.0
        )
