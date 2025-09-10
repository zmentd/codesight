"""STEP01: File System Analysis - Main orchestrator using PocketFlow."""

import os
import time
from pathlib import Path
from typing import Any, Dict, List

from core.base_node import BaseNode, ValidationResult
from steps.step01.directory_scanner import DirectoryScanner
from utils.path_utils import PathUtils


class FilesystemAnalyzer(BaseNode):
    """
    STEP01: File System Analysis orchestrator using PocketFlow pattern.
    
    Responsibilities:
    - File discovery and basic metadata extraction
    - Language detection and framework identification
    - Project structure analysis
    - Component type prediction based on file patterns
    
    Conforms to STEP01_FILE_SYSTEM_ANALYSIS.md specification.
    """
    
    def __init__(self, node_id: str = "steps.step01"):
        super().__init__(node_id)
        self.scanner = DirectoryScanner()
        
        # Get dedicated console logger for important messages
        from utils.logging.logger_factory import LoggerFactory
        self.console_logger = LoggerFactory.get_logger("codesight")
        # self.classifier = FileClassifier()
    
    def _prep_implementation(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for file system analysis."""
        # Extract project path from shared state
        project_path = self.config.project.source_path
        if not project_path:
            raise ValueError("Missing required parameter: project_path")
        
        # Ensure project path exists
        if not os.path.exists(project_path):
            raise ValueError(f"Project path does not exist: {project_path}")
        
        return {
            "project_path": project_path,
            "project_name": shared.get("project_name", Path(project_path).name)
        }
    
    def _exec_implementation(self, prep_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute file system analysis with progress tracking.
        """
        project_path = prep_result["project_path"]
        project_name = prep_result["project_name"]
        
        # self.console_logger.info("🔍 Starting filesystem analysis for: %s", project_name)
        
        # Create progress context for the entire Step01 operation
        with self.create_progress_context() as progress:
            progress.display_result("Step 01 - File system analysis", "info")
            # Phase 1: Scanning phase
            scan_result = self.scanner.scan_source_locations(progress, project_path)

            # Phase 2: Metadata extraction (quick)
            progress.start_phase("Finalizing", "Finalizing Step 01", 3)
            build_files = scan_result.get("build_files", [])
            project_metadata = self._extract_project_metadata(project_path, build_files)
            project_metadata["project_name"] = project_name
            progress.update(1, current_item="Project metadata extracted")
            
            # Phase 3: Classification (quick)
            # Extract classification data from scanner results
            project_meta = scan_result.get("project_metadata", {})
            classification_result = {
                "components": [],
                "languages": project_meta.get("languages_detected", []),
                "frameworks": project_meta.get("frameworks_detected", [])
            }
            progress.update(1, current_item="Classification completed")
            
            # Count actual subdomains from source_inventory
            source_inventory = scan_result.get("source_inventory", {})
            
            # Count files and subdomains by traversing the hierarchical structure
            files_analyzed = 0
            unique_subdomains = set()
            
            if "source_locations" in source_inventory:
                for source_location in source_inventory["source_locations"]:
                    for subdomain in source_location.get("subdomains", []):
                        files_in_subdomain = subdomain.get("file_inventory", [])
                        files_analyzed += len(files_in_subdomain)
                        # Count unique subdomains (excluding "other")
                        subdomain_name = subdomain.get("name", "")
                        if subdomain_name and subdomain_name != "other":
                            unique_subdomains.add(subdomain_name)
            
            subdomains_count = len(unique_subdomains)
            if self._pipeline_step:
                self._pipeline_step.update(1, current_item="Progress update.")
            step01_output = self._generate_step01_output(
                project_metadata, scan_result, classification_result, project_path
            )
            progress.update(1, current_item="Output generated")
        
        return {
            "output_data": step01_output,
            "metadata": {
                "files_analyzed": files_analyzed,
                "languages_detected": classification_result["languages"],
                "frameworks_detected": classification_result["frameworks"],
                "subdomains_identified": subdomains_count
            }
        }

    def validate_results(self, output_data: Dict[str, Any]) -> ValidationResult:
        """Enhanced validation of STEP01 output data against DirectoryScanner structure."""
        errors = []
        warnings = []
        
        # Enforce quality gates from configuration
        # Gate: Unix-relative paths required
        if getattr(self.config.quality_gates.step01, 'unix_relative_required', True):
            path_issues = self._check_unix_path_compliance(output_data)
            errors.extend(path_issues)

        # Gate: Minimum file access success rate
        try:
            min_access_pct = getattr(self.config.quality_gates.step01, 'min_config_accessible_pct', 0.9)
            val = output_data.get('validation_results', {}) if isinstance(output_data, dict) else {}
            access_rate = val.get('file_access_success_rate')
            if access_rate is None:
                step_meta = output_data.get('step_metadata', {}) if isinstance(output_data, dict) else {}
                files_processed = step_meta.get('files_processed', 0)
                errors_encountered = step_meta.get('errors_encountered', 0)
                denom = (files_processed + errors_encountered) or 1
                access_rate = files_processed / denom
            if access_rate < min_access_pct:
                errors.append(f"File access success rate {access_rate:.3f} below required {min_access_pct:.3f}")
        except Exception as e:  # pylint: disable=broad-except
            warnings.append(f"Failed to evaluate access gate: {e}")

        # Check required top-level keys from DirectoryScanner output
        required_keys = ["step_metadata", "project_metadata", "source_inventory"]
        for key in required_keys:
            if key not in output_data:
                errors.append(f"Missing required key: {key}")
        
        # Validate step_metadata section
        if "step_metadata" in output_data:
            step_metadata = output_data["step_metadata"]
            required_step_metadata = ["step_name", "execution_timestamp", "files_processed"]
            for key in required_step_metadata:
                if key not in step_metadata:
                    errors.append(f"Missing step_metadata key: {key}")
            
            # Validate execution timestamp format
            if "execution_timestamp" in step_metadata:
                try:
                    time.strptime(step_metadata["execution_timestamp"], "%Y-%m-%dT%H:%M:%S.%f")
                except ValueError:
                    errors.append(f"Invalid execution_timestamp format: {step_metadata['execution_timestamp']}")
            
            # Validate processing time is reasonable (not negative, not excessive)
            processing_time = step_metadata.get("processing_time_ms", 0)
            if processing_time < 0:
                errors.append("processing_time_ms cannot be negative")
            elif processing_time > 300000:  # 5 minutes
                warnings.append(f"processing_time_ms is very high: {processing_time}ms")
        
        # Validate project_metadata section
        if "project_metadata" in output_data:
            project_metadata = output_data["project_metadata"]
            required_project_metadata = [
                "project_name", "analysis_date", "pipeline_version", 
                "languages_detected", "frameworks_detected", "total_files_analyzed"
            ]
            for key in required_project_metadata:
                if key not in project_metadata:
                    errors.append(f"Missing project_metadata key: {key}")
            
            # Validate pipeline version format
            if "pipeline_version" in project_metadata and not isinstance(project_metadata["pipeline_version"], str):
                errors.append("pipeline_version must be a string")
            
            # Validate date format
            if "analysis_date" in project_metadata:
                try:
                    time.strptime(project_metadata["analysis_date"], "%Y-%m-%dT%H:%M:%S.%f")
                except ValueError:
                    errors.append(f"Invalid analysis_date format: {project_metadata['analysis_date']}")
            
            # Validate language detection results
            languages_detected = project_metadata.get("languages_detected", [])
            if not isinstance(languages_detected, list):
                errors.append("languages_detected must be a list")
            elif len(languages_detected) == 0:
                warnings.append("No languages detected in project")
        
        # Enhanced validation of source_inventory section
        if "source_inventory" in output_data:
            source_inventory = output_data["source_inventory"]
            if not isinstance(source_inventory, dict):
                errors.append("source_inventory section must be a dictionary")
            else:
                # Validate source_locations array
                if "source_locations" not in source_inventory:
                    errors.append("source_inventory missing source_locations array")
                elif not isinstance(source_inventory["source_locations"], list):
                    errors.append("source_inventory.source_locations must be an array")
                else:
                    # Enhanced file validation with quality checks
                    self._validate_files_with_quality_checks(source_inventory["source_locations"], errors, warnings)
                    
                    # Statistical consistency validation
                    if "statistics" in output_data:
                        self._validate_statistical_consistency(output_data, errors, warnings)
        
        # Note: unix path violations already collected above when gate enabled
        
        # Business logic validation
        self._validate_business_logic_rules(output_data, errors, warnings)
 
        # Display completion message and analysis results using text-only progress
        with self.create_progress_context() as progress:
            # Show completion message
            progress.display_result("Filesystem analysis completed successfully", "success")
            
            # Calculate analysis results from the actual output data
            files_analyzed = 0
            unique_languages = set()
            unique_subdomains = set()
            
            # Extract data from source_inventory
            source_inventory = output_data.get("source_inventory", {})
            source_locations_count = 0
            if "source_locations" in source_inventory:
                source_locations_count = len(source_inventory["source_locations"])
                for source_location in source_inventory["source_locations"]:
                    for subdomain in source_location.get("subdomains", []):
                        files_in_subdomain = subdomain.get("file_inventory", [])
                        files_analyzed += len(files_in_subdomain)
                        
                        # Count unique subdomains (excluding "other")
                        subdomain_name = subdomain.get("name", "")
                        if subdomain_name and subdomain_name != "other":
                            unique_subdomains.add(subdomain_name)
                        
                        # Extract languages from files
                        for file_info in files_in_subdomain:
                            language = file_info.get("language", "").strip()
                            if language and language != "unknown":
                                unique_languages.add(language)
            
            # Show analysis results (these will appear as text-only, no progress bars)
            progress.display_result(f"Files analyzed: {files_analyzed}", "info")
            progress.display_result(f"Languages detected: {', '.join(sorted(unique_languages)) if unique_languages else 'None'}", "info")
            progress.display_result(f"Source locations: {source_locations_count}", "info")
            progress.display_result(f"Subdomains identified: {len(unique_subdomains)}", "info")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_files_with_quality_checks(self, source_locations: List[Dict], errors: List[str], warnings: List[str]) -> Dict[str, Any]:
        """Enhanced file validation with quality and consistency checks."""
        validation_stats = {
            "total_files": 0,
            "confidence_zero_count": 0,
            "confidence_low_count": 0,
            "missing_package_names": 0,
            "language_type_mismatches": 0,
            "extension_language_mismatches": 0,
            "pattern_inconsistencies": 0
        }
        
        for source_idx, source_location in enumerate(source_locations):
            if "subdomains" in source_location:
                for subdomain_idx, subdomain in enumerate(source_location["subdomains"]):
                    if "file_inventory" in subdomain:
                        for file_idx, file_info in enumerate(subdomain["file_inventory"]):
                            validation_stats["total_files"] += 1
                            
                            # Basic path validation
                            if "path" not in file_info:
                                errors.append(f"Source {source_idx}, subdomain {subdomain_idx}, file {file_idx} missing path")
                            elif os.path.isabs(file_info["path"]):
                                errors.append(f"Source {source_idx}, subdomain {subdomain_idx}, file {file_idx} has absolute path (must be relative): {file_info['path']}")
                            
                            # Check for Windows-style paths
                            if "path" in file_info and "\\" in file_info["path"]:
                                errors.append(f"Source {source_idx}, subdomain {subdomain_idx}, file {file_idx} has Windows-style path (must use /): {file_info['path']}")
                            
                            # Validate required file attributes
                            required_file_attrs = ["type", "language", "size_bytes"]
                            for attr in required_file_attrs:
                                if attr not in file_info:
                                    errors.append(f"Source {source_idx}, subdomain {subdomain_idx}, file {file_idx} missing required attribute: {attr}")
                            
                            # Quality checks
                            self._validate_file_quality(file_info, validation_stats, warnings)
        
        return validation_stats
    
    def _validate_file_quality(self, file_info: Dict, validation_stats: Dict[str, Any], warnings: List[str]) -> None:
        """Validate individual file quality metrics."""
        file_path = file_info.get("path", "unknown")
        
        # Check classification confidence
        if "package_layer" in file_info and isinstance(file_info["package_layer"], dict):
            confidence = file_info["package_layer"].get("confidence", 0.0)
            if confidence == 0.0:
                validation_stats["confidence_zero_count"] += 1
                warnings.append(f"File {file_path} has zero classification confidence")
            elif confidence < 0.3:
                validation_stats["confidence_low_count"] += 1
                warnings.append(f"File {file_path} has low classification confidence: {confidence}")
        
        # Check for missing package names
        if "package_layer" in file_info and isinstance(file_info["package_layer"], dict):
            package_name = file_info["package_layer"].get("package_name")
            if not package_name or package_name.strip() == "":
                validation_stats["missing_package_names"] += 1
                warnings.append(f"File {file_path} missing package name")
        
        # Language-type consistency checks
        file_type = file_info.get("type", "").lower()
        language = file_info.get("language", "").lower()
        
        # Check for type-language mismatches
        if file_type == "source" and language in ["text", "binary", "other"]:
            validation_stats["language_type_mismatches"] += 1
            warnings.append(f"File {file_path} marked as source but has non-source language: {language}")
        elif file_type in ["config", "documentation"] and language == "java":
            validation_stats["language_type_mismatches"] += 1
            warnings.append(f"File {file_path} marked as {file_type} but detected as Java")
        
        # Extension-language consistency
        if "path" in file_info:
            file_extension = os.path.splitext(file_info["path"])[1].lower()
            if file_extension == ".java" and language != "java":
                validation_stats["extension_language_mismatches"] += 1
                warnings.append(f"File {file_path} has .java extension but language is {language}")
            elif file_extension == ".xml" and language not in ["xml", "other"]:
                validation_stats["extension_language_mismatches"] += 1
                warnings.append(f"File {file_path} has .xml extension but language is {language}")
    
    def _validate_statistical_consistency(self, output_data: Dict[str, Any], errors: List[str], warnings: List[str]) -> None:
        """Validate statistical consistency across the analysis."""
        # Get computed statistics
        file_stats = output_data.get("file_statistics", {})
        computed_total = file_stats.get("total_files", 0)
        
        # Count actual files
        actual_file_count = 0
        layer_counts: dict[str, int] = {}
        language_counts: dict[str, int] = {}
        
        for source_location in output_data.get("source_locations", []):
            if "subdomains" in source_location:
                for subdomain in source_location["subdomains"]:
                    if "file_inventory" in subdomain:
                        for file_info in subdomain["file_inventory"]:
                            actual_file_count += 1
                            
                            # Track layer distribution
                            if "package_layer" in file_info and isinstance(file_info["package_layer"], dict):
                                layer_name = file_info["package_layer"].get("layer_name", "unknown")
                                layer_counts[layer_name] = layer_counts.get(layer_name, 0) + 1
                            
                            # Track language distribution
                            language = file_info.get("language", "unknown")
                            language_counts[language] = language_counts.get(language, 0) + 1
        
        # Validate total count consistency
        if computed_total != actual_file_count:
            errors.append(f"Statistics total_files ({computed_total}) doesn't match actual count ({actual_file_count})")
        
        # Validate layer distribution
        stats_by_layer = file_stats.get("by_layer", {})
        for layer_name, expected_count in stats_by_layer.items():
            actual_count = layer_counts.get(layer_name, 0)
            if expected_count != actual_count:
                errors.append(f"Layer {layer_name} statistics ({expected_count}) doesn't match actual count ({actual_count})")
        
        # Validate language distribution
        stats_by_language = file_stats.get("by_language", {})
        for language, expected_count in stats_by_language.items():
            actual_count = language_counts.get(language, 0)
            if expected_count != actual_count:
                errors.append(f"Language {language} statistics ({expected_count}) doesn't match actual count ({actual_count})")
        
        # Check for statistical outliers
        if actual_file_count > 0:
            # Check for dominant layer (>90% of files)
            for layer_name, count in layer_counts.items():
                percentage = (count / actual_file_count) * 100
                if percentage > 90:
                    warnings.append(f"Layer {layer_name} dominates with {percentage:.1f}% of files - verify classification")
            
            # Check for missing expected layers
            expected_layers = ["Database", "Service", "UI"]
            missing_layers = [layer for layer in expected_layers if layer not in layer_counts]
            if missing_layers:
                warnings.append(f"Expected layers not found: {missing_layers}")
    
    def _validate_business_logic_rules(self, output_data: Dict[str, Any], errors: List[str], warnings: List[str]) -> None:
        """Validate business logic and domain-specific rules."""
        # Rule 1: Java files should be primarily in Service layer
        java_in_wrong_layer = 0
        total_java_files = 0
        
        # Rule 2: JSP files should be in UI layer
        jsp_in_wrong_layer = 0
        total_jsp_files = 0
        
        # Rule 3: SQL files should be in Database layer
        sql_in_wrong_layer = 0
        total_sql_files = 0
        
        for source_location in output_data.get("source_locations", []):
            if "subdomains" in source_location:
                for subdomain in source_location["subdomains"]:
                    if "file_inventory" in subdomain:
                        for file_info in subdomain["file_inventory"]:
                            file_path = file_info.get("path", "")
                            language = file_info.get("language", "").lower()
                            layer_name = "unknown"
                            
                            if "package_layer" in file_info and isinstance(file_info["package_layer"], dict):
                                layer_name = file_info["package_layer"].get("layer_name", "unknown")
                            
                            # Java files business rule
                            if language == "java":
                                total_java_files += 1
                                if layer_name not in ["Service", "UI"]:  # Allow UI for some Java components
                                    java_in_wrong_layer += 1
                            
                            # JSP files business rule
                            if file_path.endswith(".jsp"):
                                total_jsp_files += 1
                                if layer_name != "UI":
                                    jsp_in_wrong_layer += 1
                            
                            # SQL files business rule
                            if language == "sql" or file_path.endswith(".sql"):
                                total_sql_files += 1
                                if layer_name != "Database":
                                    sql_in_wrong_layer += 1
        
        # Report business logic violations
        if total_java_files > 0:
            java_error_rate = (java_in_wrong_layer / total_java_files) * 100
            if java_error_rate > 20:  # Allow some tolerance
                warnings.append(f"{java_error_rate:.1f}% of Java files ({java_in_wrong_layer}/{total_java_files}) not in Service/UI layer")
        
        if jsp_in_wrong_layer > 0:
            warnings.append(f"{jsp_in_wrong_layer} JSP files not classified as UI layer")
        
        if sql_in_wrong_layer > 0:
            warnings.append(f"{sql_in_wrong_layer} SQL files not classified as Database layer")
    
    def _post_implementation(self, shared: Dict[str, Any], prep_result: Dict[str, Any], exec_result: Dict[str, Any]) -> None:
        """Save STEP01 output to the project output directory."""
        try:
            project_name = shared.get("project_name", "unknown")
            self.logger.debug("Saving STEP01 output for project: %s", project_name)
            # # Create output directory (relative to the root, not workflow directory)
            # import os
            # current_dir = os.getcwd()
            # if current_dir.endswith('workflow'):
            #     output_dir = Path("../projects") / project_name / "output"
            # else:
            #     output_dir = Path("projects") / project_name / "output"
            
            # output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save individual STEP01 output
            step01_output_path = self.config.get_output_path_for_step("step01", "step01_filesystem_analyzer")

            if "output_data" in exec_result:
                with open(step01_output_path, 'w', encoding='utf-8') as f:
                    import json
                    json.dump(exec_result["output_data"], f, indent=2, ensure_ascii=False)
                
                self.logger.debug("STEP01 output saved to: %s", step01_output_path)
            else:
                self.logger.warning("No output_data found in exec_result for STEP01")
                
        except (OSError, IOError, ValueError) as e:
            self.logger.error("Failed to save STEP01 output: %s", e)
            # Don't raise - this is post-processing, shouldn't fail the main execution
    
    def _extract_project_metadata(self, project_path: str, build_files: List[str]) -> Dict[str, Any]:
        """Extract project-level metadata from build files and directory structure."""
        metadata: Dict[str, Any] = {
            "project_name": os.path.basename(project_path),
            "project_type": "unknown",
            "build_system": "unknown",
            "main_language": "unknown",
            "dependency_files": []
        }
        
        # Detect project type and build system from build files
        for build_file_path in build_files:
            file_name = os.path.basename(build_file_path)
            
            if file_name in ["pom.xml", "build.gradle", "build.gradle.kts"]:
                metadata["project_type"] = "java"
                metadata["main_language"] = "java"
                metadata["build_system"] = "maven" if file_name == "pom.xml" else "gradle"
                metadata["dependency_files"].append(build_file_path)
            
            elif file_name in ["package.json", "package-lock.json", "yarn.lock"]:
                metadata["project_type"] = "javascript"
                metadata["main_language"] = "javascript"
                metadata["build_system"] = "npm"
                metadata["dependency_files"].append(build_file_path)
            
            elif file_name in ["requirements.txt", "setup.py", "pyproject.toml"]:
                metadata["project_type"] = "python"
                metadata["main_language"] = "python"
                metadata["build_system"] = "pip"
                metadata["dependency_files"].append(build_file_path)
        
        return metadata
    
    def _generate_step01_output(self, project_metadata: Dict[str, Any], scan_result: Dict[str, Any], 
                               classification_result: Dict[str, Any], project_path: str) -> Dict[str, Any]:
        """
        Generate STEP01 output that matches the actual DirectoryScanner structure.
        
        The DirectoryScanner already produces the correct output format, so we just need
        to return it directly rather than trying to convert it.
        """
        
        # DirectoryScanner already produces the complete, correct structure
        # Just return it as-is since it already matches what downstream steps expect
        return scan_result
    
    def _check_unix_path_compliance(self, data: Dict[str, Any]) -> List[str]:
        """Check for Windows-style paths or absolute paths in the data."""
        violations = []
        
        def check_paths_recursive(obj: Any, path_prefix: str = "") -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path_prefix}.{key}" if path_prefix else key
                    if key in ["path", "file_path", "directory"] and isinstance(value, str):
                        if "\\" in value:
                            violations.append(f"Windows-style path at {current_path}: {value}")
                        if os.path.isabs(value):
                            violations.append(f"Absolute path at {current_path}: {value}")
                    else:
                        check_paths_recursive(value, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_paths_recursive(item, f"{path_prefix}[{i}]")
        
        check_paths_recursive(data)
        return violations
