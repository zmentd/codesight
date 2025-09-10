"""
Web file classifier - handles JSP, JavaScript, CSS, HTML files using path patterns.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from domain.source_inventory import ArchitecturalPattern, LayerType, PackageLayer, PatternType

from ..models.classification_models import FileClassification, LayerMatch
from .base_classifier import BaseFileClassifier


class WebFileClassifier(BaseFileClassifier):
    """Handles web files (JSP, JavaScript, CSS, HTML) using path patterns and indicators."""
    
    def can_handle(self, file_info: Dict[str, Any]) -> bool:
        """Check if this classifier can handle web files."""
        file_path = file_info.get('path', '')
        language = file_info.get('language')
        handle = False

        if file_path:
            handle = bool(file_path.endswith(('.jsp', '.js', '.css', '.html')))
        if not handle and language:
            handle = language in ['jsp', 'javascript', 'css', 'html']
        return handle

    
    def classify(self, file_info: Dict[str, Any]) -> FileClassification:
        """
        Classify web file using path patterns and indicators.
        Maintains parity with existing UI file classification logic.
        """
        file_path = file_info['path']
        language = file_info['language']
        
        self.logger.debug("Web file processing: %s (language: %s)", file_path, language)
        
        # 1. Detect Package Layer using path patterns
        package_layer_info = self._detect_package_layer_from_path(file_path, language)
        
        # 2. Detect Architectural Pattern from path
        arch_info = self.detect_architectural_pattern(file_path)
        if not arch_info:
            arch_info = self.create_none_architectural_info()
        
        # 3. If no package layer found, default to UI or infer from architectural pattern
        if package_layer_info.layer == LayerType.NONE:
            if arch_info.pattern != 'none':
                inferred_layer = self.infer_package_layer_from_architectural_pattern(arch_info.pattern)
                if inferred_layer:
                    package_layer_info = PackageLayer(
                        layer=LayerType(inferred_layer),
                        pattern_type=PatternType.ARCHITECTURAL_INFERENCE,
                        confidence=0.8,
                        inferred_from_pattern=arch_info.pattern
                    )
                else:
                    # Default to UI for web files
                    package_layer_info = PackageLayer(
                        layer=LayerType.UI,
                        pattern_type=PatternType.UI_PATH,
                        confidence=0.6
                    )
            else:
                # Default to UI for web files
                package_layer_info = PackageLayer(
                    layer=LayerType.UI,
                    pattern_type=PatternType.UI_PATH,
                    confidence=0.6
                )
        
        # 4. Extract subdomain name from path
        subdomain_name = self._extract_component_name_from_path(file_path)
        
        # 5. Generate framework hints
        framework_hints = self.generate_framework_hints(file_info)
        
        # 6. Determine subdomain type from layer
        subdomain_type = self.map_layer_to_subdomain_type(package_layer_info.layer.value)
        
        # 7. Extract tags from directory context if available
        tags = file_info.get('tags', [])
        
        return FileClassification(
            subdomain_name=subdomain_name,
            layer=package_layer_info.layer.value,
            subdomain_type=subdomain_type,
            confidence=0.8 if package_layer_info.layer != LayerType.UI else 0.7,
            architectural_info=arch_info,
            package_layer_info=package_layer_info,
            framework_hints=framework_hints,
            tags=tags
        )

    def detect_package_layer(self, file_info: Dict[str, Any]) -> Optional[PackageLayer]:
        """
        Detect package layer for web files using path patterns.
        Maintains consistency with Java classifier interface.
        """
        file_path = file_info.get('path', '')
        language = file_info.get('language', '')
        
        package_layer_info = self._detect_package_layer_from_path(file_path, language)
        
        if package_layer_info.layer != LayerType.NONE:
            return package_layer_info
        else:
            return None

    def match_package_patterns(self, package_name: str) -> Optional[LayerMatch]:
        """
        Match package name against web-specific patterns.
        Maintains consistency with Java classifier interface.
        """
        # For web files, we adapt package name (dot-separated) back to path format
        file_path = package_name.replace('.', '/')
        
        # Try to detect language from file extension in the path
        detected_language = 'jsp'  # Default for web files
        if file_path.endswith('.js'):
            detected_language = 'javascript'
        elif file_path.endswith('.html') or file_path.endswith('.htm'):
            detected_language = 'html'
        elif file_path.endswith('.css'):
            detected_language = 'css'
        
        # Delegate to existing logic and convert result
        package_layer = self._detect_package_layer_from_path(file_path, detected_language)
        
        if package_layer.layer != LayerType.NONE:
            return LayerMatch(
                layer=package_layer.layer.value,
                pattern=package_layer.matched_pattern or package_layer.path_indicator or f"*{Path(file_path).name}*",
                confidence=package_layer.confidence
            )
        
        self.logger.debug("    No web patterns matched for path: %s", file_path)
        return None
    
    def _detect_package_layer_from_path(self, file_path: str, language: str) -> PackageLayer:
        """
        Detect package layer using path patterns for the specific language.
        """
        path_parts = file_path.split('/')
        
        # Check language-specific path patterns first
        if hasattr(self.config, 'languages_patterns') and hasattr(self.config.languages_patterns, language):
            lang_config = getattr(self.config.languages_patterns, language)
            
            if hasattr(lang_config, 'path_patterns'):
                path_patterns = lang_config.path_patterns
                if hasattr(path_patterns, 'items') and callable(getattr(path_patterns, 'items')):
                    for layer, patterns in path_patterns.items():
                        if isinstance(patterns, list):
                            for pattern in patterns:
                                if self.pattern_matcher.matches(file_path, pattern):
                                    return PackageLayer(
                                        layer=LayerType(layer),
                                        pattern_type=PatternType.UI_PATH,
                                        confidence=0.8,
                                        matched_pattern=pattern
                                    )
        
        # Build path-to-layer mapping from configuration patterns
        path_layer_mapping = self._build_path_layer_mapping()
        
        # Look for architectural layers in path
        for i, part in enumerate(path_parts):
            if part in path_layer_mapping:
                return PackageLayer(
                    layer=LayerType(path_layer_mapping[part]),
                    pattern_type=PatternType.UI_PATH,
                    confidence=0.8,
                    path_indicator=part
                )
        
        # Return none - will be handled by caller
        return self.create_none_package_layer_info()
    
    def _build_path_layer_mapping(self) -> Dict[str, str]:
        """
        Build path-to-layer mapping from configuration patterns.
        Copied from existing _build_path_layer_mapping logic.
        """
        path_layer_mapping: Dict[str, str] = {}
        
        if not hasattr(self.config, 'languages_patterns') or \
           not hasattr(self.config.languages_patterns, 'java') or \
           not hasattr(self.config.languages_patterns.java, 'package_patterns'):
            return path_layer_mapping
        
        patterns = self.config.languages_patterns.java.package_patterns
        
        # Extract architectural package identifiers from each layer's patterns
        for layer in ['Service', 'Database', 'Integration', 'UI', 'Configuration', 'Utility', 'Reporting']:
            if hasattr(patterns, layer):
                layer_patterns = getattr(patterns, layer)
                for pattern in layer_patterns:
                    # Extract meaningful directory names from patterns
                    if '**/' in pattern and '/**' in pattern:
                        parts = pattern.split('/')
                        for part in parts:
                            if part and part != '**' and not part.startswith('com.'):
                                path_layer_mapping[part.lower()] = layer
        
        # Add common path patterns that might not be in package patterns
        path_layer_mapping['jsp'] = 'UI'  # Default JSP location
        
        return path_layer_mapping
    
    def _extract_component_name_from_path(self, file_path: str) -> str:
        """
        Extract subdomain name from file path.
        Copied from existing UI classification logic.
        """
        path_parts = file_path.split('/')
        
        # Use pattern matcher utility for subdomain extraction
        subdomain_name = self.pattern_matcher.extract_component_from_path(file_path, path_parts)
        
        # Clean up subdomain name
        return subdomain_name.strip('_')
