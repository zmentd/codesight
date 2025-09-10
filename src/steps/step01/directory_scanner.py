"""
Modular Directory Scanner that uses the classifier proxy pattern.
Maintains complete parity with the existing EnhancedDirectoryScanner.

"""

import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from config import Config
from domain.source_inventory import (
    ArchitecturalLayerType,
    ArchitecturalPattern,
    FileInventoryItem,
    LayerType,
    PackageLayer,
    PatternType,
    SourceInventory,
    SourceLocation,
    SourceType,
    Subdomain,
    SubdomainType,
)
from steps.step01.file_info_statistics import FileInfoStatistics
from utils.logging.logger_factory import LoggerFactory
from utils.path_utils import PathUtils
from utils.progress.progress_manager import StepProgressContext, SubtaskTracker

from .classifiers.file_classifier import FileClassifier
from .models.classification_models import FileClassification
from .source_locator import SourceLocator


@dataclass
class LayerMatch:
    """Represents a matched package pattern with layer and confidence."""
    layer: str
    pattern: str
    confidence: float


class DirectoryScanner:
    """
    Modular directory scanner that uses classifier proxy pattern and maintains
    complete parity with EnhancedDirectoryScanner functionality.
    """
    
    def __init__(self) -> None:
        self.logger = LoggerFactory.get_logger("steps")
        self.config = Config.get_instance()
        self.source_locator = SourceLocator()
        self.file_classifier = FileClassifier(self.config)
        self._discovered_build_files: List[str] = []  # Track build files for framework detection
        # Runtime metrics
        self._file_access_attempts: int = 0
        self._file_access_successes: int = 0
        self._metadata_successes: int = 0
        self._processing_time_ms: int = 0
    
    def scan_source_locations(self, progress_context: StepProgressContext,
                             project_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Main orchestration method that generates STEP01 compliant output.
        Maintains complete parity with existing method.
        
        Args:
            progress_context: Progress context for tracking file processing (required)
            project_path: Optional project path override. If None, uses config.
            
        Returns:
            STEP01 specification compliant JSON structure
        """
        if project_path is None:
            project_path = self.config.project.source_path
        
        # Reset per-run metrics and start timer
        self._file_access_attempts = 0
        self._file_access_successes = 0
        self._metadata_successes = 0
        start_ts = time.perf_counter()
        
        # Phase 1: Use SourceLocator to discover source roots
        source_inventory = self.source_locator.locate_source_directories(project_path)
        self.logger.debug("Discovered source locations: %s", len(source_inventory.source_locations))
        
        # Phase 1.5: Discover build files from the entire project directory (not just source locations)
        self._discover_build_files_globally(project_path)
        
        # Start progress tracking with the discovered source locations count
        progress_context.start_phase("scanning", "📁 Scanning and classifying files", len(source_inventory.source_locations))
        
        # Phase 2: Scan and classify files using modular classifiers
        processed_files = 0
        
        for source_location in source_inventory.source_locations:
            self.logger.debug("Scanning and classifying files for: %s", source_location.relative_path)
            
            # Create a subtask for this specific source location scanning
            # This won't interfere with the main "scanning" phase progress
            safe_path = source_location.relative_path.replace('/', '_').replace('\\', '_')
            with progress_context.create_subtask(
                f"scan_{safe_path}", 
                f"📂 {source_location.relative_path}", 
                100  # Initial estimate, will update with actual file count
            ) as subtask:
                
                # Use modular classification approach with subtask tracking
                self._scan_source_location(source_location, project_path, subtask)
                processed_files += source_location.get_total_files()
                subtask.complete()
            
            self.logger.debug("Found %s files and %s subdomains in %s", 
                            source_location.get_total_files(), len(source_location.subdomains), source_location.relative_path)
            
            # Update main progress for completed source location
            progress_context.update(
                1, 
                current_item=f"Completed {source_location.relative_path} ({source_location.get_total_files()} files)"
            )
            
            # Update the existing source_location in place with the scanned results
            source_location.subdomains = source_location.subdomains
            # source_locations_map[source_location.relative_path] = source_location
            
        self.logger.debug("Total source locations: %s, total files: %s", 
                         len(source_inventory.source_locations), source_inventory.get_total_files())
        
        # Phase 4: Generate STEP01 compliant output with new hierarchical structure
        output = self._generate_step01_output(
            source_inventory, project_path
        )
        
        # Stop timer and stamp processing time
        self._processing_time_ms = int((time.perf_counter() - start_ts) * 1000)
        try:
            if "step_metadata" in output:
                output["step_metadata"]["processing_time_ms"] = self._processing_time_ms
        except Exception:  # pylint: disable=broad-except
            pass
        
        self.logger.info("Modular directory scan complete. Found %s source locations, %s subdomains, %s files", 
                        len(source_inventory.source_locations), sum(len(s.subdomains) for s in source_inventory.source_locations), 
                        source_inventory.get_total_files())
        
        return output
    
    def _scan_source_location(self, source_location: SourceLocation, project_path: str, 
                             progress_context: Union[StepProgressContext, SubtaskTracker]) -> SourceLocation:
        """
        Scan files and classify them using the modular classifier system.
        Builds hierarchical structure: source_location -> subdomains -> file_inventory_items
        
        Args:
            source_location: Source location object to scan
            project_path: Root project path
            progress_context: Progress context for tracking individual files (StepProgressContext or SubtaskTracker)
        
        Returns:
            SourceLocation object with populated subdomains
        """
        file_inventory: List[Dict[str, Any]] = []
        source_path = os.path.join(project_path, source_location.relative_path)
        current_subdomain = None
        processed_files_count = 0
        
        if not os.path.exists(source_path):
            self.logger.warning("Source path does not exist: %s", source_path)
            return source_location
            
        # Quick file count to update progress total for SubtaskTracker
        if isinstance(progress_context, SubtaskTracker):
            total_files = 0
            for root, dirs, files in os.walk(source_path):
                # Apply exclusion patterns to directories
                dirs_to_remove = []
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    relative_dir = PathUtils.to_relative_path(dir_path, project_path)
                    if self._should_exclude_path(relative_dir):
                        dirs_to_remove.append(dir_name)
                for dir_name in dirs_to_remove:
                    dirs.remove(dir_name)
                
                # Count files that we would include
                for file in files:
                    file_path = os.path.join(root, file)
                    if self.should_include_file(file, file_path):
                        total_files += 1
            
            # Update the subtask with actual file count
            if progress_context.task_id in progress_context.manager._tasks:
                task = progress_context.manager._tasks[progress_context.task_id]
                if progress_context.manager.use_rich and progress_context.manager._progress:
                    progress_context.manager._progress.update(task, total=total_files)
            if progress_context.task_id in progress_context.manager._stats:
                progress_context.manager._stats[progress_context.task_id].total_items = total_files
        # Auto create an Other subdomain for unclassified files
        other_subdomain = Subdomain(    
            path=source_location.relative_path,
            name='other',
            type=SourceType.SOURCE,
            source_location=source_location.relative_path,
            confidence=0.6,
            preliminary_subdomain_type=SubdomainType.UNKNOWN,
            preliminary_subdomain_name='other',
            layers=set(),
            framework_hints=set(),
            file_inventory=[]
        )
        source_location.subdomains.append(other_subdomain)
        root_packages = []
        discovered_packages = set()  # Track unique packages found
        # Common root package names that we should walk through but not stop at
        common_roots = {'com', 'org', 'net', 'edu', 'gov', 'mil', 'int'}
        
        # Determine root package names by finding the first meaningful package levels
        # We want to find packages like "com.inbcu.storm.api" or "com.nbcuni.dcss.storm" 
        # but not their subpackages
        for root, dirs, files in os.walk(source_path):
            # Apply exclusion patterns to directories
            dirs_to_remove = []
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                relative_dir = PathUtils.to_relative_path(dir_path, project_path)
                if self._should_exclude_path(relative_dir):
                    dirs_to_remove.append(dir_name)
            
            for dir_name in dirs_to_remove:
                dirs.remove(dir_name)
            
            # Check if this directory has Java files or multiple subdirectories
            java_files = [f for f in files if f.lower().endswith(('.java'))]
            has_java_files = len(java_files) > 0
            has_multiple_subdirs = len(dirs) > 1
            
            if has_java_files or has_multiple_subdirs:
                # Get the relative path from the source location root
                root_relative = PathUtils.to_relative_path(root, os.path.join(project_path, source_location.relative_path))
                if root_relative != '.' and root_relative:
                    # Convert path separators to dots for package notation
                    package_path = root_relative.replace('/', '.').replace('\\', '.')
                    path_parts = package_path.split('.')
                    
                    # Find the meaningful root package level:
                    # For "com.inbcu.storm.api" -> we want "com.inbcu.storm.api"
                    # For "com.nbcuni.dcss.storm" -> we want "com.nbcuni.dcss.storm"
                    
                    # Skip paths that are too shallow (just common roots)
                    if len(path_parts) < 2:
                        continue
                        
                    # Look for a meaningful business package structure
                    # Pattern: common_root.organization.project.module
                    meaningful_package = None
                    
                    if len(path_parts) >= 4:  # e.g., com.inbcu.storm.api
                        # Check if first part is common root
                        if path_parts[0].lower() in common_roots:
                            # Take up to the 4th level as root package
                            meaningful_package = '.'.join(path_parts[:4])
                    elif len(path_parts) >= 3:  # e.g., com.company.project
                        # Check if first part is common root
                        if path_parts[0].lower() in common_roots:
                            # Take up to the 3rd level as root package
                            meaningful_package = '.'.join(path_parts[:3])
                    
                    # Only add if we haven't seen this package before and it's meaningful
                    if meaningful_package and meaningful_package not in discovered_packages:
                        discovered_packages.add(meaningful_package)
                        root_packages.append(meaningful_package)
                        self.logger.debug("Root package found: %s for source location: %s (found %d Java files)", 
                                        meaningful_package, source_location.relative_path, len(java_files))
            
            # Analyze current directory structure for architectural patterns
            root_relative = PathUtils.to_relative_path(root, os.path.join(project_path, source_location.relative_path))
            path_parts = root_relative.split('/') if root_relative != '.' else []
            
            # Check if we're in an architectural pattern directory
            # Use shared utility from classifier to ensure consistency
            file_details = {
                'path': root_relative,
                'language': source_location.primary_language
            }
            current_arch_pattern, current_subdomain_name = self.file_classifier.detect_architectural_pattern_and_subdomain(file_details)
            self.logger.debug("Directory analysis for %s: arch_pattern=%s, subdomain_name=%s", root_relative, current_arch_pattern, current_subdomain_name)
            package_name = '.'.join(path_parts)
            package_match = self.file_classifier.match_package_patterns(file_details, package_name)
            current_package_layer = None
            if package_match:
                current_package_layer = package_match.layer
            
            if current_arch_pattern is not None:
                # Create subdomain for architectural pattern using the extracted subdomain name
                subdomain_name = current_subdomain_name or current_arch_pattern  # Fallback to pattern if no name
                current_subdomain = Subdomain(
                    path=root_relative,
                    name=subdomain_name,
                    type=SourceType.SOURCE,
                    source_location=source_location.relative_path,
                    confidence=0.6,
                    preliminary_subdomain_type=SubdomainType.UNKNOWN,
                    preliminary_subdomain_name=subdomain_name,
                    layers=set(),
                    framework_hints=set(),
                    file_inventory=[]
                )
                source_location.subdomains.append(current_subdomain)
            else:
                self.logger.debug("Using 'Other' subdomain as no architectural pattern detected for %s. Package match is %s", root_relative, package_match)
                if package_match and package_match.layer != 'none':
                    subdomain_name = package_match.layer
                    current_subdomain = Subdomain(
                        path=root_relative,
                        name=subdomain_name,
                        type=SourceType.SOURCE,
                        source_location=source_location.relative_path,
                        confidence=0.6,
                        preliminary_subdomain_type=SubdomainType.UNKNOWN,
                        preliminary_subdomain_name=subdomain_name,
                        layers=set(),
                        framework_hints=set(),
                        file_inventory=[]
                    )
                    source_location.subdomains.append(current_subdomain)
                else:
                    current_subdomain = None
                
            # Process files in current directory
            for file in files:
                file_path = os.path.join(root, file)
                relative_to_source = PathUtils.to_relative_path(file_path, os.path.join(project_path, source_location.relative_path))
                
                # Check against include/exclude patterns
                if self.should_include_file(file, file_path):
                    # Count an access attempt for included file
                    self._file_access_attempts += 1
                    try:
                        self.logger.debug("Processing file: %s", relative_to_source)
                        
                        # Build file info with enhanced context
                        file_info = self.build_file_info_with_context(
                            file, file_path, relative_to_source, source_location,
                            current_arch_pattern, current_package_layer, path_parts
                        )
                        # If we reached here, we successfully accessed basic metadata
                        self._file_access_successes += 1
                        file_inventory.append(file_info)
                        
                        # Check if this is a build file and track it
                        self._discover_build_file(file, file_path, project_path)
                        
                        # Use modular classifier to get classification
                        # Create FileInventoryItem and add to appropriate subdomain
                        subdomain_name = current_subdomain_name or 'other'
                        file_inventory_item = self._create_file_inventory_item(file_info, subdomain_name)
                        # Consider metadata extraction successful if classification object exists
                        if file_info.get('classification') is not None:
                            self._metadata_successes += 1
                        
                        processed_files_count += 1
                        
                        # Update progress for each file processed
                        # For performance, only update the message every 10 files or for the first 20
                        if processed_files_count % 10 == 0 or processed_files_count <= 20:
                            progress_context.update(
                                1,  # Always update by 1 to match the actual file count
                                current_item=f"Processing {relative_to_source}"
                            )
                        else:
                            # Still update progress count but without changing the message
                            progress_context.update(1)
                        
                        if current_subdomain is not None:
                            if current_subdomain.architectural_pattern is None:
                                current_subdomain.architectural_pattern = file_info.get('architectural_pattern', None)
                            if current_subdomain.package_layer is None:
                                current_subdomain.package_layer = file_info.get('package_layer', None)
                            # Extract layer from classification
                            classification = file_info.get('classification', None)
                            layer = classification.layer if classification and classification.layer else 'none'
                            # Get framework hints from classification, not path parts
                            framework_hints = classification.framework_hints if classification and classification.framework_hints else []
                            current_subdomain.add_file_inventory_item(
                                file_inventory_item=file_inventory_item, 
                                layer=layer,
                                framework_hints=framework_hints
                            )
                        else:
                            # If no specific subdomain, add to 'other'
                            if other_subdomain.architectural_pattern is None:
                                other_subdomain.architectural_pattern = file_info.get('architectural_pattern', None)
                            if other_subdomain.package_layer is None:
                                other_subdomain.package_layer = file_info.get('package_layer', None)
                            # Extract layer from classification
                            classification = file_info.get('classification', None)
                            layer = classification.layer if classification and classification.layer else 'none'
                            # Get framework hints from classification, not path parts
                            framework_hints = classification.framework_hints if classification and classification.framework_hints else []
                            other_subdomain.add_file_inventory_item(
                                file_inventory_item=file_inventory_item, 
                                layer=layer,
                                framework_hints=framework_hints
                            )
                        
                    except (OSError, IOError) as e:
                        self.logger.warning("Failed to process file %s: %s", file_path, e)
                else:
                    self.logger.debug("Skipping excluded file: %s", relative_to_source)

        # Filter subdomains to remove any subdomains that have no files
        filtered = [subdomain for subdomain in source_location.subdomains if subdomain.file_inventory]
        source_location.subdomains = filtered
        
        # Set the root packages on the source location
        if root_packages:
            source_location.root_package = root_packages
            self.logger.debug("Set root packages '%s' for source location: %s", root_packages, source_location.relative_path)
        
        # Always show completion message regardless of throttling
        progress_context.update(
            0,  # Don't increment count, just update the message
            current_item=f"Completed {source_location.relative_path}"
        )
        
        return source_location

    def _discover_build_file(self, filename: str, file_path: str, project_path: str) -> None:
        """Discover and track build files for framework detection and metadata extraction."""
        # Check for common build file patterns
        build_file_patterns = [
            'build.xml',      # Ant
            'pom.xml',        # Maven  
            'build.gradle',   # Gradle
            'build.gradle.kts'  # Gradle Kotlin DSL
        ]
        is_build_file = False
        
        # Check exact matches first
        if filename.lower() in [pattern.lower() for pattern in build_file_patterns]:
            is_build_file = True
        
        # Check Ant variations
        elif filename.lower().endswith('.xml') and ('build' in filename.lower()):
            is_build_file = True
        
        if is_build_file:
            # Store relative path for later analysis
            relative_path = PathUtils.to_relative_path(file_path, project_path)
            if relative_path not in self._discovered_build_files:
                self._discovered_build_files.append(relative_path)
                self.logger.info("Discovered build file: %s", relative_path)

    def _discover_build_files_globally(self, project_path: str) -> None:
        """
        Discover build files from the entire project directory tree.
        This method scans the entire project, not just detected source locations,
        to find build files like Storm-AntBuild.xml that may be at the project root.
        """
        self.logger.debug("Starting global build file discovery in: %s", project_path)
        
        # Build file patterns to search for
        build_file_patterns = [
            'build.xml',      # Ant
            'pom.xml',        # Maven  
            'build.gradle',   # Gradle
            'build.gradle.kts',  # Gradle Kotlin DSL
            'package.json',   # Node.js
            'Makefile',       # Make
            'CMakeLists.txt',  # CMake
        ]
        
        # Walk through the entire project directory
        for root, dirs, files in os.walk(project_path):
            # Skip common build/output directories to avoid noise
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in [
                'target', 'build', 'dist', 'node_modules', 'bin', 'out'
            ]]
            
            for file in files:
                file_path = os.path.join(root, file)
                
                # Check for exact pattern matches
                is_build_file = False
                if file.lower() in [pattern.lower() for pattern in build_file_patterns]:
                    is_build_file = True
                
                # Check for Ant build file variations (including Storm-AntBuild.xml)
                elif file.lower().endswith('.xml') and ('build' in file.lower()):
                    is_build_file = True
                
                # Check for other common build file patterns
                elif any(pattern in file.lower() for pattern in ['makefile', 'cmake']):
                    is_build_file = True
                
                if is_build_file:
                    relative_path = PathUtils.to_relative_path(file_path, project_path)
                    if relative_path not in self._discovered_build_files:
                        self._discovered_build_files.append(relative_path)
                        self.logger.info("Globally discovered build file: %s", relative_path)

    def _create_file_inventory_item(self, file_info: Dict[str, Any], 
                                   subdomain_name: str) -> FileInventoryItem:
        """Create a FileInventoryItem with proper type safety."""
        # Extract values with proper defaults
        classification = file_info.get('classification', None)
        layer = classification.layer if classification and classification.layer else 'none'
        framework_hints = classification.framework_hints if classification and classification.framework_hints else set()
        
        # Ensure framework_hints is a set
        if not isinstance(framework_hints, set):
            framework_hints = set(framework_hints) if framework_hints else set()
        
        return FileInventoryItem(
            path=file_info.get('path', ''),
            language=file_info.get('language', 'unknown'),
            layer=layer,
            size_bytes=file_info.get('size_bytes', 0),
            source_location=file_info.get('source_location', ''),
            last_modified=file_info.get('last_modified', ''),
            type=file_info.get('type', 'unknown'),
            functional_name=file_info.get('preliminary_subdomain_name', subdomain_name),
            architectural_pattern=file_info.get('architectural_pattern', None),
            package_layer=file_info.get('package_layer', None),
            framework_hints=framework_hints,
            # New: provenance populated when enabled
            provenance=self._build_file_provenance(file_info, classification)
        )
    
    def _build_file_provenance(self, file_info: Dict[str, Any], classification: Optional[FileClassification]) -> Optional[Dict[str, Any]]:
        """Construct per-file provenance if enabled in config."""
        try:
            prov_cfg = getattr(self.config, 'provenance', None)
            if not prov_cfg or not getattr(prov_cfg, 'per_file_confidence_enabled', False):
                return None
            weights = getattr(prov_cfg, 'confidence_weights', None) or {'ast': 0.6, 'config': 0.3, 'llm': 0.1}
            # Derive a simple evidence breakdown for Step01
            ast_conf = 0.0
            config_conf = 0.0
            llm_conf = 0.0

            # Classification confidence if available
            if classification and hasattr(classification, 'confidence'):
                ast_conf = float(classification.confidence)
            # Basic metadata extracted successfully implies config-driven signals succeeded
            config_conf = 1.0 if file_info.get('language') and file_info.get('type') else 0.5

            # Weighted score (bounded 0..1)
            total = (weights.get('ast', 0) * ast_conf) + (weights.get('config', 0) * config_conf) + (weights.get('llm', 0) * llm_conf)
            total = max(0.0, min(1.0, total))

            # Safely unwrap enums to strings if present
            def _safe_enum_value(value: Any) -> Optional[str]:
                try:
                    if value is None:
                        return None
                    return value.value if hasattr(value, 'value') else str(value)
                except Exception:  # pylint: disable=broad-except
                    return None

            pkg_layer_obj = file_info.get('package_layer')
            arch_pat_obj = file_info.get('architectural_pattern')

            provenance = {
                'confidence_breakdown': {
                    'ast': round(ast_conf, 4),
                    'config': round(config_conf, 4),
                    'llm': round(llm_conf, 4),
                },
                'weights': weights,
                'overall_confidence': round(total, 4),
                'signals': {
                    'package_layer': {
                        'present': bool(pkg_layer_obj),
                        'layer': _safe_enum_value(getattr(pkg_layer_obj, 'layer', None)) if pkg_layer_obj else None,
                        'pattern_type': _safe_enum_value(getattr(pkg_layer_obj, 'pattern_type', None)) if pkg_layer_obj else None,
                    },
                    'architectural_pattern': {
                        'present': bool(arch_pat_obj),
                        'layer': _safe_enum_value(getattr(arch_pat_obj, 'architectural_layer', None)) if arch_pat_obj else None,
                        'pattern_type': _safe_enum_value(getattr(arch_pat_obj, 'pattern_type', None)) if arch_pat_obj else None,
                    },
                    'language_detected': file_info.get('language'),
                    'type_detected': file_info.get('type'),
                }
            }
            return provenance
        except Exception:  # pylint: disable=broad-except
            return None

    def build_file_info_with_context(self, filename: str, file_path: str, 
                                    relative_to_source: str, source_location: SourceLocation,
                                    current_arch_pattern: Optional[str],
                                    current_package_layer: Optional[str],
                                    path_parts: List[str]) -> Dict[str, Any]:
        """
        Build comprehensive file info with enhanced context from directory traversal.
        Uses modular classifier system to achieve same results as enhanced scanner.
        """
        # Extract preliminary component name and tags from directory structure
        preliminary_component, tags = self._extract_preliminary_component_and_tags(path_parts, current_arch_pattern)
        
        # Build basic file info first
        file_info = {
            'path': relative_to_source,
            'absolute_path': file_path,
            'size_bytes': os.path.getsize(file_path),
            'last_modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
            'type': self._determine_file_type(filename),
            'language': self._detect_language(filename),
            'source_location': source_location.relative_path,
            'extension': Path(filename).suffix.lower(),
            'preliminary_subdomain_name': preliminary_component,
            'tags': tags,
            'directory_context': {
                'path_parts': path_parts,
                'architectural_pattern_from_dir': current_arch_pattern,
                'package_layer_from_dir': current_package_layer
            }
        }
        
        # Use classifier system to get architectural pattern detection (equivalent to enhanced scanner's _detect_architectural_pattern_for_file)
        classification = self.file_classifier.classify_file(file_info)
        file_info['classification'] = classification
        
        # Debug: Log file classification results
        if classification and classification.subdomain_name != 'unknown':
            self.logger.debug("File %s classified with subdomain: %s, arch_pattern: %s", 
                            file_path, classification.subdomain_name, 
                            classification.architectural_info.pattern if classification.architectural_info else 'none')
        # Initialize architectural_pattern with defaults (always provide structure)
        architectural_pattern_obj = ArchitecturalPattern(
            pattern='none',
            architectural_layer=ArchitecturalLayerType.UNKNOWN,
            pattern_type=PatternType.NONE,
            confidence=0.0,
            detected_from_directory=False,
            package_name=None
        )
        
        package_layer_obj = PackageLayer(
            layer=LayerType.NONE,
            pattern_type=PatternType.NONE,
            confidence=0.0,
            matched_pattern=None,
            package_name=None,
            path_indicator=None,
            inferred_from_pattern=None
        )
        
        # Override defaults with classification results if available
        if classification:
            if classification.architectural_info:
                architectural_pattern_obj = classification.architectural_info
                # Ensure directory-based patterns have proper metadata
                if architectural_pattern_obj.pattern_type == PatternType.DIRECTORY_BASED:
                    if not architectural_pattern_obj.package_name and path_parts:
                        architectural_pattern_obj.package_name = '.'.join(path_parts)
                    if not architectural_pattern_obj.detected_from_directory:
                        architectural_pattern_obj.detected_from_directory = True
            
            if classification.package_layer_info:
                package_layer_obj = classification.package_layer_info
                # Ensure proper metadata population for package layers
                if not package_layer_obj.package_name and path_parts:
                    package_layer_obj.package_name = '.'.join(path_parts)
                if not package_layer_obj.matched_pattern and package_layer_obj.layer != LayerType.NONE:
                    package_layer_obj.matched_pattern = f"**/{package_layer_obj.layer.value.lower()}/**"
                if not package_layer_obj.inferred_from_pattern and package_layer_obj.layer != LayerType.NONE:
                    package_layer_obj.inferred_from_pattern = package_layer_obj.layer.value
        
        # If we detected architectural pattern from directory, use it to enhance file info (same logic as enhanced scanner)
        if current_arch_pattern:
            if architectural_pattern_obj.pattern == 'none':
                # Build package name from path parts
                package_name = '.'.join(path_parts) if path_parts else None
                
                architectural_pattern_obj = ArchitecturalPattern(
                    pattern=f"**/{current_arch_pattern}/**",
                    architectural_layer=ArchitecturalLayerType(current_arch_pattern),
                    pattern_type=PatternType.DIRECTORY_BASED,
                    confidence=0.9,
                    package_name=package_name,
                    detected_from_directory=True
                )
        
        # If we detected package layer from directory, use it to enhance file info (same logic as enhanced scanner)
        if current_package_layer:
            if package_layer_obj.layer == LayerType.NONE:
                # Build package name from path parts
                package_name = '.'.join(path_parts) if path_parts else None
                
                package_layer_obj = PackageLayer(
                    layer=LayerType(current_package_layer),
                    pattern_type=PatternType.JAVA_PACKAGE if any('java' in part.lower() for part in path_parts) else PatternType.UI_PATH,
                    confidence=0.8,
                    matched_pattern=f"**/{current_package_layer.lower()}/**",
                    package_name=package_name,
                    path_indicator='/'.join(path_parts) if path_parts else None,
                    inferred_from_pattern=current_package_layer
                )
        
        # Final metadata enhancement - ensure all directory-based patterns have complete metadata
        if (architectural_pattern_obj.pattern_type == PatternType.DIRECTORY_BASED or 
            str(architectural_pattern_obj.pattern_type).lower() == 'directory_based' or
                architectural_pattern_obj.pattern != 'none'):
            package_name = '.'.join(path_parts) if path_parts else None
            architectural_pattern_obj = ArchitecturalPattern(
                pattern=architectural_pattern_obj.pattern,
                architectural_layer=architectural_pattern_obj.architectural_layer,
                pattern_type=architectural_pattern_obj.pattern_type,
                confidence=architectural_pattern_obj.confidence,
                package_name=package_name,
                detected_from_directory=True
            )
        
        # Final metadata enhancement - ensure all package layers have complete metadata  
        if package_layer_obj.layer != LayerType.NONE:
            package_name = '.'.join(path_parts) if path_parts else package_layer_obj.package_name
            matched_pattern = package_layer_obj.matched_pattern or f"**/{package_layer_obj.layer.value.lower()}/**"
            inferred_from_pattern = package_layer_obj.inferred_from_pattern or package_layer_obj.layer.value
            
            package_layer_obj = PackageLayer(
                layer=package_layer_obj.layer,
                pattern_type=package_layer_obj.pattern_type,
                confidence=package_layer_obj.confidence,
                matched_pattern=matched_pattern,
                package_name=package_name,
                path_indicator=package_layer_obj.path_indicator,
                inferred_from_pattern=inferred_from_pattern
            )
        
        # Update file_info with the enhanced objects
        file_info['architectural_pattern'] = architectural_pattern_obj
        file_info['package_layer'] = package_layer_obj

        return file_info
    
    def detect_package_layer_from_directory_path(self, path_parts: List[str]) -> Optional[str]:
        """Copied from existing method."""
        if not hasattr(self.config, 'languages_patterns'):
            return None
        
        # Build layer indicators from configuration
        layer_indicators = {}
        
        # First, try to get indicators from fallback patterns
        if hasattr(self.config.languages_patterns, 'fallback'):
            fallback_patterns = self.config.languages_patterns.fallback
            
            if hasattr(fallback_patterns, 'items'):
                # Handle case where fallback_patterns might be a dict
                if isinstance(fallback_patterns, dict):
                    for layer, patterns in fallback_patterns.items():
                        if isinstance(patterns, list):
                            for pattern in patterns:
                                # Extract directory-like indicators from patterns
                                clean_pattern = pattern.strip('*').lower()
                                if clean_pattern and not clean_pattern.startswith('.'):
                                    layer_indicators[clean_pattern] = layer
        
        # Also check language-specific indicators for additional directory patterns
        for lang in ['java', 'javascript', 'jsp']:
            if hasattr(self.config.languages_patterns, lang):
                lang_config = getattr(self.config.languages_patterns, lang)
                if hasattr(lang_config, 'indicators'):
                    indicators = lang_config.indicators
                    if hasattr(indicators, 'items') and callable(getattr(indicators, 'items')):
                        for layer, indicator_list in indicators.items():
                            if isinstance(indicator_list, list):
                                for indicator in indicator_list:
                                    # Extract meaningful directory indicators
                                    clean_indicator = indicator.strip('*@').lower()
                                    if clean_indicator and not clean_indicator.startswith('.'):
                                        layer_indicators[clean_indicator] = layer
        
        # Check each path part against our configuration-driven indicators
        for part in path_parts:
            part_lower = part.lower()
            if part_lower in layer_indicators:
                return str(layer_indicators[part_lower])
        
        return None
    
    def _extract_preliminary_component_and_tags(self, path_parts: List[str], current_arch_pattern: Optional[str]) -> Tuple[Optional[str], List[str]]:
        """Copied from existing method."""
        preliminary_component = None
        tags: List[str] = []
        
        if not current_arch_pattern or not hasattr(self.config, 'architectural_patterns'):
            return preliminary_component, tags
        
        arch_patterns = self.config.architectural_patterns
        
        # Build reverse mapping from configuration to find directory names
        arch_dir = None
        attr_mapping = {
            'application': 'Application',
            'business': 'Business', 
            'data_access': 'DataAccess',
            'shared': 'Shared'
        }
        
        attr_name = attr_mapping.get(current_arch_pattern)
        if attr_name and hasattr(arch_patterns, attr_name):
            patterns = getattr(arch_patterns, attr_name)
            if patterns:
                for pattern in patterns:
                    # Extract directory names from glob patterns like "**/asl/**"
                    if '**/' in pattern and '/**' in pattern:
                        parts = pattern.split('/')
                        for part in parts:
                            if part and part != '**':
                                arch_dir = part.lower()
                                break
                        if arch_dir:
                            break
        
        if not arch_dir:
            return preliminary_component, tags
        
        # Find the architectural directory in the path
        arch_pattern_index = None
        for i, part in enumerate(path_parts):
            if part.lower() == arch_dir:
                arch_pattern_index = i
                break
        
        if arch_pattern_index is not None:
            # Preliminary component is the next directory after the architectural pattern
            if arch_pattern_index + 1 < len(path_parts):
                preliminary_component = path_parts[arch_pattern_index + 1]
                
                # Tags are all directories after the preliminary component
                if arch_pattern_index + 2 < len(path_parts):
                    tags = path_parts[arch_pattern_index + 2:]
        
        return preliminary_component, tags
    
    def should_include_file(self, filename: str, file_path: str) -> bool:
        """Copied from existing method."""
        # Check file extension against include patterns
        file_ext = Path(filename).suffix.lower()
        
        if hasattr(self.config, 'steps') and hasattr(self.config.steps, 'step01'):
            include_extensions = getattr(self.config.steps.step01, 'include_extensions', [])
            if include_extensions and file_ext not in include_extensions:
                return False
        
        # Check file size using absolute path
        try:
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            max_size = getattr(self.config.steps.step01, 'max_file_size_mb', 30)
            if file_size_mb > max_size:
                return False
        except (OSError, IOError):
            return False
        
        # Check against exclusion patterns using relative path
        relative_path = PathUtils.to_relative_path(file_path, self.config.project.source_path)
        return not self._should_exclude_path(relative_path)
    
    def _should_exclude_path(self, relative_path: str) -> bool:
        """Copied from existing method."""
        if hasattr(self.config, 'steps') and hasattr(self.config.steps, 'step01'):
            exclude_patterns = getattr(self.config.steps.step01, 'exclude_patterns', [])
            
            for pattern in exclude_patterns:
                # Convert glob pattern to simple matching
                clean_pattern = pattern.replace('**/', '').replace('/**', '').strip('*')
                if clean_pattern in relative_path:
                    return True
        
        return False
    
    def _determine_file_type(self, filename: str) -> str:
        """Copied from existing method."""
        ext = Path(filename).suffix.lower()
        
        type_mapping = {
            '.java': 'source',
            '.jsp': 'web', '.jspx': 'web', '.html': 'web', '.htm': 'web',
            '.js': 'script', '.css': 'style',
            '.xml': 'config', '.properties': 'config', '.yml': 'config', '.yaml': 'config',
            '.sql': 'database',
            '.tld': 'descriptor'
        }
        
        return type_mapping.get(ext, 'other')
    
    def _detect_language(self, filename: str) -> str:
        """Copied from existing method."""
        ext = Path(filename).suffix.lower()
        
        language_mapping = {
            '.java': 'java',
            '.jsp': 'jsp', '.jspx': 'jsp',
            '.js': 'javascript',
            '.html': 'html', '.htm': 'html',
            '.css': 'css',
            '.xml': 'xml',
            '.properties': 'properties',
            '.yml': 'yaml', '.yaml': 'yaml',
            '.sql': 'sql',
            '.tld': 'tld',
            '.vbs': 'vbscript'
        }
        
        return language_mapping.get(ext, 'other')
    
    def _generate_step01_output(self, source_inventory: SourceInventory, 
                               project_path: str) -> Dict[str, Any]:
        """
        Generate STEP01 specification compliant output using hierarchical SourceInventory structure.
        """
        
        # Build metadata section
        metadata = {
            "project_name": self.config.project.name,
            "analysis_date": datetime.now().isoformat(),
            "pipeline_version": "2.0-hierarchical",
            "languages_detected": self._extract_detected_languages_from_inventory(source_inventory),
            "frameworks_detected": self._detect_frameworks_from_inventory(source_inventory, project_path),
            "total_files_analyzed": source_inventory.get_total_files()
        }
        
        # Create flattening utility for statistics generation
        flat_files = self._flatten_for_statistics(source_inventory)
        
        # Build directory structure section
        directory_structure = {
            "discovered_patterns": self._detect_project_patterns(source_inventory),
            "source_directories": [loc.relative_path for loc in source_inventory.source_locations],
            "package_structure": {
                "architectural_packages": self._get_architectural_packages_from_config(),
                "business_packages": list(set(subdomain.name for source in source_inventory.source_locations 
                                            for subdomain in source.subdomains
                                            if subdomain.preliminary_subdomain_type and 
                                            subdomain.preliminary_subdomain_type.value in ['service', 'screen']))
            }
        }
        
        # Build validation results from real metrics when available
        attempts = max(self._file_access_attempts, 0)
        successes = max(self._file_access_successes, 0)
        meta_successes = max(self._metadata_successes, 0)
        access_rate = (successes / attempts) if attempts > 0 else 1.0
        metadata_rate = (meta_successes / successes) if successes > 0 else 1.0
        errors_encountered = attempts - successes if attempts >= successes else 0

        validation_results = {
            "file_access_success_rate": round(access_rate, 4),
            "metadata_extraction_success_rate": round(metadata_rate, 4),
            "framework_detection_confidence": 0.85,
            "issues": []
        }
        
        # Generate statistics using flattened data
        stats = FileInfoStatistics()
        stats_results = stats.get_statistics(flat_files)
        
        # Analyze build files for build configuration section
        build_configuration = self._analyze_build_files(project_path)
        
        # Final STEP01 output structure - NEW HIERARCHICAL FORMAT
        return {
            "step_metadata": {
                "step_name": "file_system_analysis",
                "execution_timestamp": datetime.now().isoformat(),
                "processing_time_ms": self._processing_time_ms or 0,
                "files_processed": source_inventory.get_total_files(),
                "errors_encountered": errors_encountered,
                "configuration_sources": ["config.yaml", f"config-{self.config.project.name}.yaml"]
            },
            "project_metadata": metadata,
            "build_configuration": build_configuration,  # NEW: Build configuration section
            "statistics": stats_results,
            "source_inventory": source_inventory.to_dict(),
            "directory_structure": directory_structure,
            "validation_results": validation_results
        }
    
    def _flatten_for_statistics(self, source_inventory: SourceInventory) -> List[Dict]:
        """Extract all files as dictionaries for statistics generation."""
        files = []
        for source in source_inventory.source_locations:
            for subdomain in source.subdomains:
                for file_item in subdomain.file_inventory:
                    file_dict = {
                        'path': file_item.path,
                        'type': file_item.type,
                        'language': file_item.language,
                        'layer': file_item.layer,
                        'size_bytes': file_item.size_bytes,
                        'last_modified': file_item.last_modified,
                        'source_location': file_item.source_location,
                        'framework_hints': list(file_item.framework_hints),
                        'preliminary_subdomain_type': subdomain.preliminary_subdomain_type.value if subdomain.preliminary_subdomain_type else None,
                        'preliminary_subdomain_name': subdomain.preliminary_subdomain_name,
                        'tags': subdomain.tags,
                        'package_layer': subdomain.package_layer.__dict__ if subdomain.package_layer else {"layer": "none", "pattern_type": "none", "confidence": 0.0},
                        'architectural_pattern': subdomain.architectural_pattern.__dict__ if subdomain.architectural_pattern else {"pattern": "none", "pattern_type": "none", "confidence": 0.0},
                        'confidence': subdomain.confidence
                    }
                    files.append(file_dict)
        return files
    
    def _extract_detected_languages_from_inventory(self, source_inventory: SourceInventory) -> List[str]:
        """Extract detected languages from source inventory."""
        languages = set()
        for source in source_inventory.source_locations:
            for subdomain in source.subdomains:
                for file_item in subdomain.file_inventory:
                    if file_item.language:
                        languages.add(file_item.language)
        return sorted(list(languages))
    
    def _detect_frameworks_from_inventory(self, source_inventory: SourceInventory, project_path: str) -> List[str]:
        """Detect frameworks from source inventory using comprehensive detection."""
        from .build_parsers.ant_parser import AntBuildParser
        from .framework_detector import FrameworkDetector

        # Parse build files for enhanced framework detection
        build_configuration = self._analyze_build_files(project_path)

        # Use framework detector with build configuration
        framework_detector = FrameworkDetector(self.config)
        return framework_detector.detect_frameworks(source_inventory, project_path, build_configuration)
    
    def _analyze_build_files(self, project_path: str) -> Dict[str, Any]:
        """Analyze discovered build files to extract configuration and dependencies."""
        from .build_parsers.ant_parser import AntBuildParser
        
        build_configuration: Dict[str, Any] = {}
        
        if not self._discovered_build_files:
            self.logger.debug("No build files discovered for analysis")
            return build_configuration
        
        for build_file_relative in self._discovered_build_files:
            build_file_path = os.path.join(project_path, build_file_relative)
            self.logger.debug("Analyzing build file: %s", build_file_path)
            
            if not os.path.exists(build_file_path):
                self.logger.warning("Build file not found: %s", build_file_path)
                continue
            
            filename = os.path.basename(build_file_path).lower()
            
            # Parse Ant build files
            if filename.endswith('build.xml') or ('build' in filename and filename.endswith('.xml')):
                ant_parser = AntBuildParser()
                ant_config = ant_parser.parse_build_file(build_file_path, project_path)
                
                if 'error' not in ant_config:
                    build_configuration.update(ant_config)
                    self.logger.info("Successfully analyzed Ant build file: %s", build_file_relative)
                    break  # Use the first successful build file analysis
                else:
                    self.logger.warning("Failed to analyze Ant build file %s: %s", build_file_relative, ant_config.get('error'))
            
            # Future: Add Maven and Gradle support here
            elif filename == 'pom.xml':
                self.logger.debug("Maven support not yet implemented for: %s", build_file_relative)
            elif 'build.gradle' in filename:
                self.logger.debug("Gradle support not yet implemented for: %s", build_file_relative)
        
        return build_configuration
    
    def _detect_project_patterns(self, source_inventory: SourceInventory) -> List[str]:
        """Copied from existing method."""
        patterns: List[str] = []
        # Project pattern detection logic would go here
        return patterns
    
    def _get_architectural_packages_from_config(self) -> List[str]:
        """Extract architectural package names from configuration patterns."""
        architectural_packages = []
        
        if hasattr(self.config, 'languages_patterns') and \
           hasattr(self.config.languages_patterns, 'java') and \
           hasattr(self.config.languages_patterns.java, 'package_patterns'):
            
            patterns = self.config.languages_patterns.java.package_patterns
            
            for layer in ['Service', 'Database', 'Integration']:
                if hasattr(patterns, layer):
                    layer_patterns = getattr(patterns, layer)
                    for pattern in layer_patterns:
                        # Extract meaningful package names from patterns
                        # Remove glob patterns and extract actual package components
                        clean_pattern = pattern.replace('**/', '').replace('/**', '').strip('*')
                        if clean_pattern and '.' in clean_pattern:
                            # Extract root package name (e.g., 'com.nbcuni.dcss' from 'com.nbcuni.dcss.storm')
                            package_parts = clean_pattern.split('.')
                            if len(package_parts) >= 3:  # Ensure we have meaningful package structure
                                # Take first 3 parts for organizational package (com.company.project)
                                org_package = '.'.join(package_parts[:3])
                                architectural_packages.append(org_package)
                                # Also add specific framework/layer packages if they exist
                                if len(package_parts) > 3:
                                    framework_part = package_parts[3]
                                    architectural_packages.append(framework_part)
        
        return list(set(architectural_packages))


