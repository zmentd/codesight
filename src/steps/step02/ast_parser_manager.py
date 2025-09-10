"""
AST Parser Manager for Step 02

Orchestrates AST parsing across multiple file types using existing LEX utilities
"""
import json
import shutil
import sys
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add src to Python path to ensure correct imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import Config
from domain.java_details import JavaDetails
from domain.source_inventory import FileInventoryItem, SourceInventory
from domain.sql_details import SQLDetails
from domain.step02_output import ProjectData, Statistics, Step02AstExtractorOutput, StepMetadata
from steps.step02.jpype_manager import JPypeManager
from steps.step02.parsers.configuration_parser import ConfigurationParser
from steps.step02.parsers.java_parser import JavaParser
from steps.step02.parsers.jsp_parser import JSPParser
from steps.step02.parsers.sql_parser import SQLParser
from steps.step02.source_inventory_query import (
    SourceInventoryQuery,
    find_entity_managers,
    find_sql_operations,
)
from utils.logging.logger_factory import LoggerFactory
from utils.progress.progress_manager import StepProgressContext, SubtaskTracker


class EnumJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Enum serialization by converting to their values."""
    def default(self, o: Any) -> Any:
        if isinstance(o, Enum):
            return o.value
        return super().default(o)


class ASTParserManager:
    """
    Orchestrates AST parsing using existing LEX utilities and framework detection.
    
    Responsibilities:
    - Coordinate multiple parser types
    - Use LEX utilities for preprocessing
    - Apply framework detection patterns
    - Manage JPype lifecycle for Java parsing
    """
    
    def __init__(self, config: Config, source_inventory: Optional[SourceInventory]) -> None:
        """Initialize parser manager with existing infrastructure."""
        # Initialize config for the specified project
        self.logger = LoggerFactory.get_logger("steps")
        JPypeManager.initialize()
        self.config = Config.get_instance()
        
        if not source_inventory:
            # Load the source inventory from the step01 output file
            step01_output_path = Path(self.config.get_output_path_for_step("step01"))
            output_dir = step01_output_path.parent
            step01_output_path = output_dir / "step01_filesystem_analyzer_output.json"
            self.logger.info("Loading source inventory from: %s", step01_output_path)
            if not step01_output_path.exists():
                raise FileNotFoundError(f"Step01 output file not found: {step01_output_path}")
            with open(step01_output_path, 'r', encoding='utf-8') as f:
                step01_data = json.load(f)
                source_inventory_data = step01_data.get("source_inventory", {})
                # Parse entire Step01 output using domain class
                self.source_inventory = SourceInventory.from_dict(source_inventory_data)
        else:
            self.source_inventory = source_inventory
        if not self.source_inventory:
            raise ValueError("Source inventory is empty or not provided")
        self.logger.info("Source inventory loaded with %d source locations", len(self.source_inventory.source_locations))
        self.output_dir = Path(self.config.project.output_path) / "step02"
    
    def parse_source_inventory(self, progress_context: StepProgressContext) -> Step02AstExtractorOutput:
        """
        Parse a list of files using appropriate parsers.
        
        Args:
            file_list: List of file information dictionaries
            progress_context: Optional progress tracking context
            
        Returns:
            List of parse results
        """
        start_time = time.time()

        self.logger.info("Creating step02 output at: %s", self.output_dir)

        # Calculate total files for progress tracking
        total_files = self.source_inventory.get_total_files()
        
        # Start progress tracking with total file count
        progress_context.start_phase("parsing", "🔍 Parsing files for structural extraction", total_files)

        # Track processing statistics
        total_files_processed = 0
        config_files_processed = 0
        java_files_processed = 0
        jsp_files_processed = 0
        sql_files_processed = 0
        files_with_config_details = 0
        parsing_errors: List[Dict[str, Any]] = []
        errors_encountered = 0
        successful_parses = 0
        failed_parses = 0
        syntax_error_count = 0
        parsing_warnings = 0  # reserved; populate when parsers emit warnings
        include_packages: List[str] = []
        config_parser = ConfigurationParser(self.config, self.source_inventory)
        sql_parser = SQLParser(self.config)
        java_parser = JavaParser(self.config, JPypeManager.get_instance())
        jsp_parser = JSPParser(self.config)
        
        # Helper to constrain scope from config
        def _is_in_scope(file_item: FileInventoryItem) -> bool:
            from fnmatch import fnmatch
            parsers_cfg = getattr(self.config, 'parsers')
            # Languages filter
            if getattr(parsers_cfg, 'languages', None):
                if file_item.language not in parsers_cfg.languages:
                    return False
            # Include globs: if provided, must match at least one
            if getattr(parsers_cfg, 'include_globs', None):
                if not any(fnmatch(file_item.path, pat) for pat in parsers_cfg.include_globs):
                    return False
            # Exclude globs: if provided and matches, skip
            if getattr(parsers_cfg, 'exclude_globs', None):
                if any(fnmatch(file_item.path, pat) for pat in parsers_cfg.exclude_globs):
                    return False
            return True
        
        # Process each source location
        for source_location in self.source_inventory.source_locations:
            self.logger.info("Processing source location: %s", source_location.relative_path)
            
            # Create subtask for this source location
            safe_path = source_location.relative_path.replace('/', '_').replace('\\', '_')
            with progress_context.create_subtask(
                f"parse_{safe_path}", 
                f"🔍 {source_location.relative_path}", 
                source_location.get_total_files()
            ) as subtask:
                
                # Append the source location root packages if available to include_packages, keeping unique
                if source_location.root_package:
                    new_packages = [pkg for pkg in source_location.root_package if pkg not in include_packages]
                    include_packages.extend(new_packages)
                    if new_packages:
                        self.logger.debug("Added %d new packages to include list: %s", 
                                         len(new_packages), new_packages)

                # Process each subdomain
                for subdomain in source_location.subdomains:
                    self.logger.debug("Processing subdomain: %s", subdomain.name)
                    # Process each file in the inventory
                    for file_item in subdomain.file_inventory:
                        if not _is_in_scope(file_item):
                            # Still advance progress to avoid stalling UI
                            total_files_processed += 1
                            subtask.update(1)
                            continue
                        total_files_processed += 1
                        try:
                            # Build the full file path
                            source_path = Path(self.config.project.source_path)
                            file_path = source_path / file_item.source_location / file_item.path
                            self.logger.debug("Processing file: %s (type: %s, language: %s, size: %s bytes)", 
                                             file_path, file_item.type, file_item.language, file_item.size_bytes)
                            
                            if self._is_configuration_file(file_item):
                                config_files_processed += 1
                                if config_parser.can_parse(file_item):
                                    # Parse the configuration file
                                    config_details = config_parser.parse_file(file_item)
                                    file_item.details = config_details
                                    files_with_config_details += 1
                                    if config_details:
                                        successful_parses += 1
                                    else:
                                        failed_parses += 1
                                else:
                                    failed_parses += 1
                            elif java_parser.can_parse(file_item):
                                java_files_processed += 1
                                # Parse Java files for AST extraction
                                java_details = java_parser.parse_file(file_item, include_packages, True)
                                file_item.details = java_details
                                if java_details:
                                    successful_parses += 1
                                else:
                                    failed_parses += 1
                            elif sql_parser.can_parse(file_item):
                                sql_files_processed += 1
                                # Parse SQL files for database object extraction
                                sql_details = sql_parser.parse_file(file_item)
                                file_item.details = sql_details
                                if sql_details:
                                    successful_parses += 1
                                else:
                                    failed_parses += 1
                            elif jsp_parser.can_parse(file_item):
                                jsp_files_processed += 1
                                # Parse JSP files for AST extraction
                                jsp_details = jsp_parser.parse_file(file_item)
                                file_item.details = jsp_details
                                if jsp_details:
                                    successful_parses += 1
                                else:
                                    failed_parses += 1
                            else:
                                self.logger.warning("No parser for file: %s", file_path)
                                failed_parses += 1
                            
                            # Update progress
                            if total_files_processed % 10 == 0 or total_files_processed <= 20:
                                subtask.update(1, current_item=f"Processing {file_item.path}")
                            else:
                                subtask.update(1)

                        except Exception as e:  # noqa: BLE001  # pylint: disable=W0718
                            errors_encountered += 1
                            error_type = self._classify_error_type(e)
                            if error_type == "syntax":
                                syntax_error_count += 1
                            error_info = {
                                "file_path": file_item.path,
                                "error": str(e),
                                "error_type": error_type
                            }
                            parsing_errors.append(error_info)
                            self.logger.error("Error parsing file %s: %s", file_item.path, str(e))
                
                subtask.complete()
            
            # Update main progress for completed source location
            progress_context.update(
                source_location.get_total_files(),
                current_item=f"Completed {source_location.relative_path}"
            )
        
        # Prepare query helper for summaries
        files_by_language = SourceInventoryQuery(self.source_inventory).files().count_by(lambda f: f.language)
        # Pre-compute interesting sets
        java_em_with_entities = find_entity_managers(self.source_inventory)
        java_with_sql = find_sql_operations(self.source_inventory)
        
        # Linkage and routing metrics from parsed details
        total_routes = 0
        resolved_routes = 0
        total_code_mappings = 0
        unresolved_refs = 0
        all_files = SourceInventoryQuery(self.source_inventory).files().execute().items
        for f in all_files:
            if hasattr(f, 'details') and f.details is not None:
                # rest_endpoints on JavaDetails
                try:
                    endpoints = getattr(f.details, 'rest_endpoints', []) or []
                    for ep in endpoints:
                        total_routes += 1
                        if ep.get('class_name') and ep.get('method_name'):
                            resolved_routes += 1
                except Exception:  # pylint: disable=broad-except
                    pass
                # code_mappings on details
                try:
                    mappings = getattr(f.details, 'code_mappings', []) or []
                    total_code_mappings += len(mappings)
                    for m in mappings:
                        to_ref = getattr(m, 'to_reference', None)
                        if not to_ref or str(to_ref).strip().lower() in {"", "unknown", "none"}:
                            unresolved_refs += 1
                except Exception:  # pylint: disable=broad-except
                    pass
        
        route_resolution_rate = round((resolved_routes / total_routes * 100.0), 2) if total_routes > 0 else 0.0
        unresolved_refs_pct = round((unresolved_refs / total_code_mappings * 100.0), 2) if total_code_mappings > 0 else 0.0
        
        # Build statistics
        base_stats = self._generate_statistics_from_query(self.source_inventory)
        stats_raw = base_stats.to_dict()
        
        # Parsing analysis aligned with NEXT_STEPS
        stats_raw["parsing_analysis"] = {
            "successful_parses": successful_parses,
            "failed_parses": failed_parses,
            "syntax_errors": syntax_error_count,
            "parsing_warnings": parsing_warnings,
            "files_with_details": stats_raw.get("parsing_analysis", {}).get("files_with_details", successful_parses),
            "parse_success_rate": round((successful_parses / total_files_processed * 100.0), 2) if total_files_processed > 0 else 0.0,
        }
        # Linkage metrics
        stats_raw["linkage_analysis"] = {
            "routes_detected": total_routes,
            "routes_resolved": resolved_routes,
            "route_resolution_rate": route_resolution_rate,
            "unresolved_refs_count": unresolved_refs,
            "unresolved_refs_pct": unresolved_refs_pct,
            "total_code_mappings": total_code_mappings,
        }
        
        output = Step02AstExtractorOutput(
            step_metadata=StepMetadata(
                step_name="step02_ast_extraction",
                execution_timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(start_time)),
                processing_time_ms=int((time.time() - start_time) * 1000),
                files_processed=total_files_processed,
                errors_encountered=errors_encountered,  # Use actual count
                configuration_sources=[f"config-{self.config.project.name}.yaml", "config.yaml"]
            ),
            project_metadata=ProjectData(
                project_name=self.config.project.name,
                analysis_date=time.strftime("%Y-%m-%d", time.gmtime(start_time)),
                languages_detected=list(files_by_language.keys()),
                frameworks_detected=self._detect_frameworks_from_query(self.source_inventory),  # Use query-based detection
                total_files_analyzed=total_files_processed,
                config_files_analyzed=config_files_processed,
                java_files_analyzed=java_files_processed,
                jsp_files_analyzed=jsp_files_processed,
                sql_files_analyzed=sql_files_processed,
                files_with_config_details=files_with_config_details,
                java_files_with_entity_mapping=java_em_with_entities.total_count,
                java_files_with_sql=java_with_sql.total_count,
                files_by_language=files_by_language
            ),
            statistics=Statistics.from_dict(stats_raw),
            source_inventory=self.source_inventory
        )

        return output
    
    def _classify_error_type(self, error: Exception) -> str:
        """Classify the type of parsing error for better reporting."""
        error_str = str(error).lower()
        if 'syntax' in error_str:
            return "syntax"
        elif 'encoding' in error_str or 'unicode' in error_str:
            return "encoding"
        elif 'file not found' in error_str or 'no such file' in error_str:
            return "access"
        else:
            return "parsing"
    
    def _detect_frameworks_from_query(self, source_inventory: SourceInventory) -> List[str]:
        """Detect frameworks using the query class from parsed data."""
        frameworks = set()
        
        # Use query to find specific patterns
        query = SourceInventoryQuery(source_inventory)
        
        # Find Java files and check their details for framework patterns
        java_files = query.files().language("java").execute()
        for item in java_files.items:
            if hasattr(item, 'details') and item.details and isinstance(item.details, JavaDetails):
                # Check class names for Spring patterns
                primary_class = item.details.get_primary_class()
                if primary_class and hasattr(primary_class, 'class_name'):
                    if any(indicator in primary_class.class_name for indicator in ['Controller', 'Service', 'Repository']):
                        frameworks.add('Spring')
                
                # Check framework hints
                if item.details.has_framework_hint('spring'):
                    frameworks.add('Spring')
                if item.details.has_framework_hint('struts'):
                    frameworks.add('Struts')
        
        # Find Struts actions
        struts_files = query.files().path_endswith("Action.java").execute()
        if not struts_files.is_empty():
            frameworks.add('Struts')
        
        # Find EntityMgr inheritance (legacy pattern)
        entity_mgr_files = find_entity_managers(source_inventory)
        if not entity_mgr_files.is_empty():
            frameworks.add('Custom Entity Framework')
        
        # Find JSP files (indicates web framework)
        jsp_files = query.files().language("jsp").execute()
        if not jsp_files.is_empty():
            frameworks.add('JSP')
        
        return sorted(list(frameworks))
    
    def _generate_statistics_from_query(self, source_inventory: SourceInventory) -> Statistics:
        """Generate comprehensive statistics using the query class."""
        query = SourceInventoryQuery(source_inventory)
        
        # Basic file counts
        total_files = query.files().count()
        files_by_language = query.files().count_by(lambda f: f.language)
        files_by_type = query.files().count_by(lambda f: f.type)
        
        # Layer analysis
        files_by_layer = query.files().count_by(lambda f: f.layer)
        
        # Subdomain analysis
        subdomains_by_type = query.subdomains().count_by(lambda s: s.preliminary_subdomain_type.value if s.preliminary_subdomain_type else 'unknown')
        
        # Framework hints analysis
        framework_usage = {}
        for hint in ['struts', 'spring', 'jsp', 'sql']:
            hint_files = query.files().framework_hint(hint).execute()
            if not hint_files.is_empty():
                framework_usage[hint] = hint_files.total_count
        
        # Size analysis
        large_files = query.files().min_size(50000).execute()
        very_large_files = query.files().min_size(100000).execute()
        
        # Legacy pattern analysis
        entity_managers = find_entity_managers(source_inventory)
        sql_operations = find_sql_operations(source_inventory)
        
        # Parse success analysis - count files with details manually
        files_with_details = 0
        all_files = query.files().execute()
        for file_item in all_files.items:
            if hasattr(file_item, 'details') and file_item.details is not None:
                files_with_details += 1
        
        parse_success_rate = (files_with_details / total_files * 100) if total_files > 0 else 0
        
        statistics_data = {
            "file_inventory_count": total_files,
            "count_language": files_by_language,
            "count_file_type": files_by_type,
            "count_layer": files_by_layer,
            "subdomain_analysis": {
                "total_subdomains": query.subdomains().count(),
                "subdomains_by_type": subdomains_by_type
            },
            "framework_analysis": {
                "framework_usage": framework_usage,
                "entity_managers_found": entity_managers.total_count,
                "sql_operations_found": sql_operations.total_count
            },
            "size_analysis": {
                "large_files_50kb": large_files.total_count,
                "very_large_files_100kb": very_large_files.total_count,
                "average_file_size": self._calculate_average_file_size(source_inventory)
            },
            "parsing_analysis": {
                "files_with_details": files_with_details,
                "parse_success_rate": round(parse_success_rate, 2)
            }
        }
        
        return Statistics(raw=statistics_data)

    def _calculate_average_file_size(self, source_inventory: SourceInventory) -> float:
        """Calculate average file size using query."""
        query = SourceInventoryQuery(source_inventory)
        files = query.files().execute()
        
        if files.is_empty():
            return 0.0
        
        total_size = sum(f.size_bytes for f in files.items if f.size_bytes)
        file_count = len(files.items)
        return round(float(total_size / file_count), 2) if file_count > 0 else 0.0
    
    def _is_configuration_file(self, file_item: FileInventoryItem) -> bool:
        """Enhanced configuration file detection for ct-hr-storm project."""
        # Based on actual data analysis, files with type 'config' are configuration files
        if file_item.type == 'config':
            return True
        
        # Enhanced XML configuration patterns (ct-hr-storm specific)
        config_patterns = [
            'web.xml', 'struts', 'spring', 'tiles', 'validation', 
            'validator-rules', 'jboss-service.xml'
        ]

        # Check if it's XML language and matches configuration patterns
        if file_item.language == 'xml':
            file_name_lower = file_item.path.lower()
            return any(pattern in file_name_lower for pattern in config_patterns)
        
        # Enhanced properties file detection
        if file_item.language == 'properties':
            return True
            
        return False


