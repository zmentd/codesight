"""
File classifier proxy that dispatches to language-specific classifiers.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import Config
from domain.source_inventory import ArchitecturalPattern, PackageLayer
from utils.logging.logger_factory import LoggerFactory

from ..models.classification_models import FileClassification, LayerMatch
from ..utils.pattern_matcher import PatternMatcher
from .base_classifier import BaseFileClassifier
from .fallback_classifier import FallbackFileClassifier
from .java_classifier import JavaFileClassifier
from .web_classifier import WebFileClassifier


class FileClassifier:
    """Main proxy that dispatches to language-specific classifiers."""
    
    def __init__(self, config: Config):
        self.config = config
        self.pattern_matcher = PatternMatcher()
        self.logger = LoggerFactory.get_logger("steps.step01.file_classifier")
        
        # Initialize language-specific classifiers
        self.classifiers = [
            JavaFileClassifier(config, self.pattern_matcher),
            WebFileClassifier(config, self.pattern_matcher),
        ]
        
        # Fallback classifier handles any file type
        self.fallback_classifier = FallbackFileClassifier(config, self.pattern_matcher)

    def _get_classifier(self, file_info: Dict[str, Any]) -> BaseFileClassifier:
        """
        Get the appropriate classifier for the given file info.
        
        Args:
            file_info: Dictionary containing file information (path, language, etc.)
            
        Returns:
            An instance of BaseFileClassifier that can handle the file type.
        """
        self.logger.debug("Finding classifier by file_info: %s", file_info)
        for classifier in self.classifiers:
            if classifier.can_handle(file_info):
                self.logger.debug("Using %s for %s", classifier.__class__.__name__, file_info['path'])
                return classifier
        self.logger.debug("Using fallback classifier for %s", file_info['path'])
        return self.fallback_classifier
    
    def classify_file(self, file_info: Dict[str, Any]) -> FileClassification:
        """
        Main entry point - dispatches to appropriate classifier.
        
        Args:
            file_info: File information dictionary containing path, language, etc.
            
        Returns:
            FileClassification result
        """
        # Find the first classifier that can handle this file
        self.logger.debug("Classifying by file_info: %s", file_info)
        classifier = self._get_classifier(file_info)
        
        return classifier.classify(file_info)

    def detect_architectural_pattern(self, file_path: str, file_info: Dict[str, Any] ) -> Optional[ArchitecturalPattern]:
        """
        Detect architectural pattern from file path.
        
        Args:
            file_path: Path to the file.
            file_info: Dictionary containing file information (path, language, etc.)

        Returns:
            ArchitecturalPattern object with detected pattern.
        """
        self.logger.debug("Detecting architectural pattern for file_info: %s", file_info)

        classifier = self._get_classifier(file_info)
        return classifier.detect_architectural_pattern(file_path)

    def detect_architectural_pattern_and_subdomain(self, file_info: Dict[str, Any] ) -> Tuple[Optional[str], Optional[str]]:
        """
        Detect architectural pattern from file path.
        
        Args:
            file_path: Path to the file.
            file_info: Dictionary containing file information (path, language, etc.)

        Returns:
            ArchitecturalPattern object with detected pattern.
        """
        self.logger.debug("Detecting architectural pattern and subdomain by file_info: %s", file_info)
        classifier = self._get_classifier(file_info)
        return classifier.detect_architectural_pattern_and_subdomain(file_info)

    def match_package_patterns(self, file_info: Dict[str, Any], package_name: str) -> Optional[LayerMatch]:
        self.logger.debug("Matching package patterns by file_info: %s", file_info)
        classifier = self._get_classifier(file_info)
        return classifier.match_package_patterns(package_name)
    
    def detect_package_layer(self, file_info: Dict[str, Any]) -> Optional[PackageLayer]:
        self.logger.debug("Detecting package layer by file_info: %s", file_info)
        classifier = self._get_classifier(file_info)
        return classifier.detect_package_layer(file_info)

    def get_supported_languages(self) -> List[str]:
        """Return list of supported languages."""
        supported = []
        for classifier in self.classifiers:
            # This is a simple way to get supported languages
            # Could be enhanced with a more formal interface
            if hasattr(classifier, 'supported_languages'):
                supported.extend(classifier.supported_languages)
        return supported
    
    def register_classifier(self, classifier: BaseFileClassifier) -> None:
        """Allow runtime registration of new classifiers."""
        self.classifiers.append(classifier)
