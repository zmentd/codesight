"""
Fallback file classifier - handles files that don't have specific language classifiers.
"""

import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional

from domain.source_inventory import ArchitecturalPattern, LayerType, PackageLayer, PatternType

from ..models.classification_models import FileClassification, LayerMatch
from .base_classifier import BaseFileClassifier


class FallbackFileClassifier(BaseFileClassifier):
    """Handles files that don't have specific language classifiers using fallback patterns."""
    
    def can_handle(self, file_info: Dict[str, Any]) -> bool:
        """Fallback classifier can handle any file."""
        return True
    
    def classify(self, file_info: Dict[str, Any]) -> FileClassification:
        """
        Classify file using fallback patterns.
        Maintains parity with existing _classify_other_file logic.
        """
        file_path = file_info.get('path', '')
        language = file_info.get('language')
        tags = file_info.get('tags', [])
        filename = Path(file_path).name
        
        self.logger.debug("Fallback file processing: %s", file_path)
        
        # 1. Detect Package Layer using fallback patterns
        package_layer_info = self._detect_package_layer_using_fallback(filename)
        
        # 2. Detect Architectural Pattern from path
        arch_info = self.detect_architectural_pattern(file_path)
        if not arch_info:
            arch_info = self.create_none_architectural_info()
        
        # 3. If we have an architectural pattern but no package layer, infer from architectural pattern
        if package_layer_info.layer == LayerType.NONE and arch_info.pattern != 'none':
            inferred_layer = self.infer_package_layer_from_architectural_pattern(arch_info.pattern)
            if inferred_layer:
                package_layer_info = PackageLayer(
                    layer=LayerType(inferred_layer),
                    pattern_type=PatternType.ARCHITECTURAL_INFERENCE,
                    confidence=0.8,
                    inferred_from_pattern=arch_info.pattern
                )
        
        # 4. If still no layer found, use file type fallback
        if package_layer_info.layer == LayerType.NONE:
            package_layer_info = self._fallback_layer_from_file_type(file_info)
        
        # 5. Extract subdomain name from filename
        subdomain_name = self.extract_component_from_filename(filename)
        
        # 6. Generate framework hints
        framework_hints = self.generate_framework_hints(file_info)
        
        # 7. Determine subdomain type from layer
        subdomain_type = self.map_layer_to_subdomain_type(package_layer_info.layer.value)
                
        return FileClassification(
            subdomain_name=subdomain_name,
            layer=package_layer_info.layer.value,
            subdomain_type=subdomain_type,
            confidence=0.7 if package_layer_info.layer != LayerType.OTHER else 0.4,
            architectural_info=arch_info,
            package_layer_info=package_layer_info,
            framework_hints=framework_hints,
            tags=tags or []
        )

    def detect_package_layer(self, file_info: Dict[str, Any]) -> Optional[PackageLayer]:
        """
        Detect package layer for fallback files using fallback patterns.
        Maintains consistency with other classifier interfaces.
        """
        filename = Path(file_info.get('path', '')).name
        
        package_layer_info = self._detect_package_layer_using_fallback(filename)
        
        if package_layer_info.layer != LayerType.NONE:
            return package_layer_info
        else:
            # Try file type fallback
            fallback_layer = self._fallback_layer_from_file_type(file_info)
            if fallback_layer.layer != LayerType.NONE:
                return fallback_layer
            return None

    def match_package_patterns(self, package_name: str) -> Optional[LayerMatch]:
        """
        Match package name against fallback patterns.
        Maintains consistency with other classifier interfaces.
        """
        # For fallback files, we use the filename from the package path
        file_path = package_name.replace('.', '/')
        filename = Path(file_path).name
        
        # Delegate to existing logic and convert result
        package_layer = self._detect_package_layer_using_fallback(filename)
        
        if package_layer.layer != LayerType.NONE:
            return LayerMatch(
                layer=package_layer.layer.value,
                pattern=package_layer.matched_pattern or f"*{filename}*",
                confidence=package_layer.confidence
            )
        
        self.logger.debug("    No fallback patterns matched for filename: %s", filename)
        return None
    
    def _detect_package_layer_using_fallback(self, filename: str) -> PackageLayer:
        """
        Detect Package Layer using fallback patterns.
        Copied from existing fallback pattern matching logic.
        """
        if hasattr(self.config, 'languages_patterns') and \
           hasattr(self.config.languages_patterns, 'fallback'):
            
            fallback_patterns = self.config.languages_patterns.fallback
            
            # Handle both dict and list structures for fallback patterns
            if isinstance(fallback_patterns, dict):
                # Dictionary structure: {layer: [patterns]}
                for layer, patterns in fallback_patterns.items():
                    if isinstance(patterns, list):
                        for pattern in patterns:
                            if fnmatch.fnmatch(filename, pattern):
                                return PackageLayer(
                                    layer=LayerType(layer),
                                    pattern_type=PatternType.FALLBACK,
                                    confidence=0.7,
                                    matched_pattern=pattern
                                )
            elif isinstance(fallback_patterns, list):
                # List structure: check against common fallback patterns
                for pattern in fallback_patterns:
                    if fnmatch.fnmatch(filename, pattern):
                        return PackageLayer(
                            layer=LayerType.OTHER,
                            pattern_type=PatternType.FALLBACK,
                            confidence=0.5,
                            matched_pattern=pattern
                        )
        
        return self.create_none_package_layer_info()
    
    def _fallback_layer_from_file_type(self, file_info: Dict[str, Any]) -> PackageLayer:
        """
        Fallback layer detection based on file type.
        Copied from existing fallback logic.
        """
        file_type_layer_mapping = {
            'web': 'UI',
            'script': 'UI',
            'style': 'UI',
            'source': 'Service',
            'config': 'Configuration',
            'database': 'Database'
        }
        
        file_type = file_info.get('type', 'other')
        layer = file_type_layer_mapping.get(file_type, 'Other')
        
        return PackageLayer(
            layer=LayerType(layer),
            pattern_type=PatternType.FILE_TYPE_FALLBACK,
            confidence=0.5
        )
