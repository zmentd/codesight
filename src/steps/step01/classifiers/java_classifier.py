"""
Java file classifier - handles Java source files using package patterns.
"""
import os
from typing import Any, Dict, List, Optional

from domain.source_inventory import (
    ArchitecturalLayerType,
    ArchitecturalPattern,
    LayerType,
    PackageLayer,
    PatternType,
)

from ..models.classification_models import FileClassification, LayerMatch
from .base_classifier import BaseFileClassifier


class JavaFileClassifier(BaseFileClassifier):
    """Handles Java source files with package-based classification."""

    def can_handle(self, file_info: Dict[str, Any]) -> bool:
        """Check if this classifier can handle Java files."""
        file_path = file_info.get('path', '')
        language = file_info.get('language')
        handle = False
        if file_path:
            handle = bool(file_path.endswith('.java'))
        if not handle and language:
            handle = bool(language == 'java')
            
        return handle

    def classify(self, file_info: Dict[str, Any]) -> FileClassification:
        """
        Classify Java file using package patterns and indicators.
        Maintains complete parity with existing logic.
        """
        file_path = file_info.get('path', '')
        language = file_info.get('language')
        tags = file_info.get('tags', [])
        
        self.logger.debug("Java file processing: %s", file_path)
        
        # Derive package name from file path
        package_name = self._derive_package_name(file_path)
        self.logger.debug("  Package name: %s", package_name)
        
        # 1. Detect Package Layer (UI, Service, Database, etc.)
        layer_match = self.match_package_patterns(package_name)
        package_layer_info = self.create_none_package_layer_info()
        
        if layer_match:
            self.logger.debug("  Package layer matched: %s (pattern: %s)", layer_match.layer, layer_match.pattern)
            package_layer_info = PackageLayer(
                layer=LayerType(layer_match.layer),
                pattern_type=PatternType.JAVA_PACKAGE,
                confidence=layer_match.confidence,
                package_name=package_name,
                matched_pattern=layer_match.pattern
            )
        else:
            self.logger.debug("  No package layer pattern matched for package: %s", package_name)
        
        # 2. Detect Architectural Pattern (ASL, GSL, DSL, ISL)
        arch_info = self._match_architectural_patterns(file_path)
        if not arch_info:
            arch_info = self.create_none_architectural_info()
            self.logger.debug("  No architectural pattern detected for file path: %s", file_path)
        else:
            self.logger.debug("  Architectural pattern detected: %s", arch_info.architectural_layer.value)
        
        # 3. If no package layer found but architectural pattern detected, infer layer
        if package_layer_info.layer == LayerType.NONE and arch_info.architectural_layer != ArchitecturalLayerType.UNKNOWN:
            inferred_layer = self.infer_package_layer_from_architectural_pattern(arch_info.architectural_layer.value)
            if inferred_layer:
                self.logger.debug("  Architectural inference applied: %s -> %s", arch_info.architectural_layer.value, inferred_layer)
                package_layer_info = PackageLayer(
                    layer=LayerType(inferred_layer),
                    pattern_type=PatternType.ARCHITECTURAL_INFERENCE,
                    confidence=0.8,
                    inferred_from_pattern=arch_info.architectural_layer.value
                )
            else:
                self.logger.debug("  Architectural inference failed for pattern: %s", arch_info.architectural_layer.value)
        elif package_layer_info.layer != LayerType.NONE:
            self.logger.debug("  Package layer already set, skipping architectural inference")
        else:
            self.logger.debug("  No architectural pattern available for inference")
        
        # 4. Extract subdomain name
        # If architectural pattern was detected, extract from file path; otherwise use package name
        if arch_info.architectural_layer != ArchitecturalLayerType.UNKNOWN:
            subdomain_name = self._extract_subdomain_from_architectural_pattern(file_path, arch_info)
        else:
            subdomain_name = self._extract_component_name(package_name, layer_match)
        
        # 5. Generate framework hints
        framework_hints = self.generate_framework_hints(file_info)
        
        # 6. Determine subdomain type from layer
        subdomain_type = self.map_layer_to_subdomain_type(package_layer_info.layer.value)
        
        # 7. Extract tags from directory context if available
        # tags = file_info.get('tags', [])
        
        return FileClassification(
            subdomain_name=subdomain_name,
            layer=package_layer_info.layer.value,
            subdomain_type=subdomain_type,
            confidence=0.9 if package_layer_info.layer != LayerType.NONE else 0.6,
            architectural_info=arch_info,
            package_layer_info=package_layer_info,
            framework_hints=framework_hints,
            tags=tags or []
        )

    def detect_package_layer(self, file_info: Dict[str, Any]) -> Optional[PackageLayer]:
        package_name = self._derive_package_name(file_info.get('path', ''))
        layer_match = self.match_package_patterns(package_name)
        package_layer_info = self.create_none_package_layer_info()
        
        if layer_match:
            self.logger.debug("  Package layer matched: %s (pattern: %s)", layer_match.layer, layer_match.pattern)
            package_layer_info = PackageLayer(
                layer=LayerType(layer_match.layer),
                pattern_type=PatternType.JAVA_PACKAGE,
                confidence=layer_match.confidence,
                package_name=package_name,
                matched_pattern=layer_match.pattern
            )

            return package_layer_info
        else:
            self.logger.debug("  No package layer pattern matched for package: %s", package_name)

        return None
    
    def _derive_package_name(self, file_path: str) -> str:
        """
        Derive Java package name from file path.
        Copied from existing _derive_package_name_from_path logic.
        """
        # Get package path by removing file name
        package_path = os.path.dirname(file_path)
        
        # Convert path separators to dots
        package_name = package_path.replace('/', '.')
        
        return package_name
    
    def match_package_patterns(self, package_name: str) -> Optional[LayerMatch]:
        """
        Match package name against configured patterns.
        Copied from existing _match_package_patterns logic.
        """
        if not hasattr(self.config, 'languages_patterns') or \
           not hasattr(self.config.languages_patterns, 'java') or \
           not hasattr(self.config.languages_patterns.java, 'package_patterns'):
            self.logger.debug("    No Java package patterns configured")
            return None
        
        patterns = self.config.languages_patterns.java.package_patterns
        
        # Check patterns in order - Integration patterns first for specificity
        layer_order = ['Integration', 'UI', 'Service', 'Database', 'Configuration', 'Utility', 'Reporting']
        
        for layer in layer_order:
            if hasattr(patterns, layer):
                layer_patterns = getattr(patterns, layer)
                self.logger.debug("    Checking %s patterns: %s", layer, layer_patterns)
                for pattern in layer_patterns:
                    if self.pattern_matcher.matches(package_name, pattern):
                        self.logger.debug("    MATCH: %s matches %s -> %s", package_name, pattern, layer)
                        return LayerMatch(layer=layer, pattern=pattern, confidence=0.9)
                    else:
                        self.logger.debug("    No match: %s vs %s", package_name, pattern)
        
        self.logger.debug("    No patterns matched for package: %s", package_name)
        return None
    
    def _match_architectural_patterns(self, file_path: str) -> Optional[ArchitecturalPattern]:
        """
        Match file path against STORM architectural patterns from configuration.
        
        Args:
            file_path: File path to match against patterns like '**/dsl/**'
            
        Returns:
            ArchitecturalPattern or None
        """
        if not hasattr(self.config, 'architectural_patterns'):
            self.logger.debug("    No architectural patterns configured")
            return None
        
        arch_patterns = self.config.architectural_patterns
        self.logger.debug("    Checking architectural patterns for file path: %s", file_path)
        
        # Check each architectural pattern from configuration using proper attribute mapping
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
                if patterns:  # Only process if we have actual patterns
                    self.logger.debug("    Checking %s patterns: %s", config_key, patterns)
                    for pattern in patterns:
                        if self.pattern_matcher.matches(file_path, pattern):
                            self.logger.debug("    ARCHITECTURAL MATCH: %s matches %s -> %s", file_path, pattern, config_key)
                            return ArchitecturalPattern(
                                pattern=pattern,  # The specific glob pattern that matched
                                architectural_layer=ArchitecturalLayerType(config_key),  # The business layer name
                                pattern_type=PatternType.DIRECTORY_BASED,
                                confidence=0.9,
                                package_name=None
                            )
                        else:
                            self.logger.debug("    No architectural match: %s vs %s", file_path, pattern)
        
        self.logger.debug("    No architectural patterns matched for file path: %s", file_path)
        return None
    
    def _extract_component_name(self, package_name: str, layer_match: Optional[LayerMatch]) -> str:
        """
        Extract component name from package using matched pattern.
        Copied from existing _extract_component_name logic.
        """
        if layer_match:
            return self.pattern_matcher.extract_component_from_package_pattern(package_name, layer_match.pattern)
        
        # Fallback: use the last meaningful part of the package
        package_parts = package_name.split('.')
        if package_parts:
            return package_parts[-1].strip('_')
        
        return 'unknown'        # Fallback: use the last meaningful part of the package
    
    def _extract_subdomain_from_architectural_pattern(self, file_path: str, arch_info: ArchitecturalPattern) -> str:
        """
        Extract subdomain name from file path when architectural pattern is detected.
        For STORM patterns like DSL, ASL, GSL, ISL - extract the directory name after the pattern.
        """
        self.logger.debug("    Extracting subdomain from architectural pattern: %s for file: %s", arch_info.pattern, file_path)
        
        # Extract the pattern without wildcards (e.g., "dsl" from "**/dsl/**")
        pattern_clean = arch_info.pattern.replace('**/', '').replace('/**', '').strip('*')
        self.logger.debug("    Clean pattern: %s", pattern_clean)
        
        # Find the pattern in the file path and extract the next directory
        path_parts = file_path.replace('\\', '/').split('/')
        
        for i, part in enumerate(path_parts):
            if part == pattern_clean:
                # Found the architectural pattern, get the deepest meaningful directory
                if i + 1 < len(path_parts):
                    # Get all directories after the architectural pattern
                    remaining_parts = path_parts[i + 1:]
                    
                    # Filter out generic/technical directories to find meaningful business domains
                    generic_dirs = {'xhtml', 'config', 'common', 'util', 'shared', 'resources'}
                    meaningful_parts = [part for part in remaining_parts 
                                       if part and part != '' and part.lower() not in generic_dirs]
                    
                    if meaningful_parts:
                        # Use the deepest meaningful directory for business domain specificity
                        subdomain_name = meaningful_parts[-1].strip('_')
                        self.logger.debug("    Extracted subdomain from path (deepest meaningful): %s", subdomain_name)
                        return subdomain_name
                    else:
                        # Fallback to first directory if no meaningful ones found
                        next_part = remaining_parts[0] if remaining_parts else pattern_clean
                        if next_part and next_part != '':
                            subdomain_name = next_part.strip('_')
                            self.logger.debug("    Extracted subdomain from path (fallback): %s", subdomain_name)
                            return subdomain_name
                # If no next part, use the pattern itself
                self.logger.debug("    No next part found, using pattern: %s", pattern_clean)
                return pattern_clean
        
        # Fallback: if pattern not found in path, extract from package name
        if hasattr(arch_info, 'package_name') and arch_info.package_name:
            package_parts = arch_info.package_name.split('.')
            if package_parts:
                subdomain_from_pkg = package_parts[-1].strip('_')
                self.logger.debug("    Fallback to package name: %s", subdomain_from_pkg)
                return subdomain_from_pkg
        
        # Final fallback
        self.logger.debug("    Final fallback: unknown")
        return 'unknown'