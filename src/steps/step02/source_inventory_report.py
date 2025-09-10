"""
Source Inventory Report Generator

This module provides comprehensive reporting capabilities for source inventory analysis,
including configuration file detection, SQL database analysis, and query API demonstrations.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add src to Python path to ensure correct imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import Config
from domain.source_inventory import FileInventoryItem, SourceInventory
from steps.step02.source_inventory_query import SourceInventoryQuery
from utils.logging.logger_factory import LoggerFactory


class SourceInventoryReport:
    """
    Generates comprehensive reports and statistics from source inventory data.
    
    This class provides powerful analysis capabilities using both traditional iteration
    and modern query-based aggregation to demonstrate the capabilities of the
    SourceInventoryQuery utility.
    """
    
    def __init__(self, project_name: str, source_inventory: Optional[SourceInventory] = None):
        """
        Initialize the report generator.
        
        Args:
            project_name: Name of the project to analyze
            source_inventory: Optional pre-loaded source inventory. If not provided,
                            will load from step02 output file.
        """
        self.project_name = project_name
        
        # Initialize configuration
        Config.initialize(project_name=project_name)
        self.config = Config.get_instance()
        
        # Initialize logging
        LoggerFactory.initialize("../../../config/logging.yaml")
        self.logger = LoggerFactory.get_logger("reports")
        
        # Load or use provided source inventory
        if source_inventory is not None:
            self.source_inventory = source_inventory
            self.logger.info("Using provided source inventory with %d source locations", 
                           len(self.source_inventory.source_locations))
        else:
            self.source_inventory = self._load_source_inventory_from_step02()
    
    def _load_source_inventory_from_step02(self) -> SourceInventory:
        """Load source inventory from step02 output file."""
        step02_output_path = Path(self.config.get_output_path_for_step("step02"))
        
        if not step02_output_path.exists():
            raise FileNotFoundError(f"Step02 output file not found: {step02_output_path}")
        
        self.logger.info("Loading source inventory from: %s", step02_output_path)
        
        with open(step02_output_path, 'r', encoding='utf-8') as f:
            step02_data = json.load(f)
            
            # Extract the source_inventory from the JSON structure
            if 'source_inventory' in step02_data:
                source_inventory = SourceInventory.from_dict(step02_data['source_inventory'])
            else:
                # Fallback: assume the entire JSON is the source inventory
                source_inventory = SourceInventory.from_dict(step02_data)
        
        self.logger.info("Source inventory loaded with %d source locations", 
                        len(source_inventory.source_locations))
        return source_inventory
    
    def generate_full_report(self) -> None:
        """Generate a comprehensive report with all analysis sections."""
        self.logger.info("\n%s", "="*80)
        self.logger.info("SOURCE INVENTORY COMPREHENSIVE ANALYSIS REPORT")
        self.logger.info("Project: %s", self.project_name)
        self.logger.info("%s", "="*80)
        
        # Generate all report sections
        self.generate_overview_statistics()
        self.generate_configuration_files_report()
        self.generate_sql_analysis_report()
        self.generate_subdomain_analysis_report()
        self.generate_java_analysis_report()
        self.generate_java_entity_mapping_analysis()
        self.generate_java_sql_analysis()
        
        self.logger.info("\n%s", "="*80)
        self.logger.info("COMPREHENSIVE ANALYSIS REPORT COMPLETE")
        self.logger.info("%s", "="*80)
    
    def generate_overview_statistics(self) -> None:
        """Generate overview statistics using query API."""
        self.logger.info("\n📊 PROJECT OVERVIEW STATISTICS:")
        
        query = SourceInventoryQuery(self.source_inventory)
        
        # Basic file counts
        total_files = query.files().execute().total_count
        self.logger.info("  Total files: %d", total_files)
        
        # Files by language
        file_counts_by_language = query.files().count_by(lambda f: f.language)
        self.logger.info("  Files by language: %s", dict(sorted(file_counts_by_language.items())))
        
        # Files by type
        file_counts_by_type = query.files().count_by(lambda f: f.type)
        self.logger.info("  Files by type: %s", dict(sorted(file_counts_by_type.items())))
        
        # Source locations
        total_locations = len(self.source_inventory.source_locations)
        self.logger.info("  Source locations: %d", total_locations)
        
        # Subdomains by type
        subdomain_counts = query.subdomains().count_by(lambda s: s.type.value if s.type else "Unknown")
        self.logger.info("  Subdomains by type: %s", dict(sorted(subdomain_counts.items())))
    
    def generate_configuration_files_report(self) -> None:
        """Generate detailed configuration files analysis."""
        self.logger.info("\n🔧 CONFIGURATION FILES ANALYSIS:")
        
        query = SourceInventoryQuery(self.source_inventory)
        
        # All file types to understand the data structure
        all_file_counts = query.files().count_by(lambda f: f.type)
        self.logger.info("  All file types found: %s", dict(sorted(all_file_counts.items())))
        
        # Configuration files by type (based on actual data: type='config')
        config_types = {k: v for k, v in all_file_counts.items() if k == 'config'}
        self.logger.info("  Configuration files by type: %s", dict(sorted(config_types.items())))
        
        # Alternative analysis using custom logic
        config_files_via_method = query.files().count_by(
            lambda f: "Configuration File" if self._is_configuration_file(f) else "Other File"
        )
        self.logger.info("  Configuration files via detection logic: %s", 
                        dict(sorted(config_files_via_method.items())))
        
        # Configuration files by language (using manual filtering since filter method not available)
        all_files = query.files().execute().items
        config_files = [f for f in all_files if self._is_configuration_file(f)]
        config_files_by_language: Dict[str, int] = {}
        for f in config_files:
            config_files_by_language[f.language] = config_files_by_language.get(f.language, 0) + 1
        self.logger.info("  Configuration files by language: %s", 
                        dict(sorted(config_files_by_language.items())))
    
    def generate_sql_analysis_report(self) -> None:
        """Generate comprehensive SQL database analysis report."""
        self.logger.info("\n🗃️ SQL DATABASE ANALYSIS REPORT:")
        
        query = SourceInventoryQuery(self.source_inventory)
        
        # Get all SQL files by language (not detail_type)
        sql_files_result = query.files().language("sql").execute()
        sql_files = sql_files_result.items
        total_sql_files = sql_files_result.total_count
        
        self.logger.info("  Total SQL files: %d", total_sql_files)
        
        if total_sql_files == 0:
            self.logger.info("  No SQL files found for analysis")
            return
        
        # SQL files by size ranges
        sql_file_size_ranges = query.files().language("sql").count_by(
            lambda f: "Large (>10KB)" if f.size_bytes > 10240 
                      else "Medium (1-10KB)" if f.size_bytes > 1024 
                      else "Small (<1KB)"
        )
        self.logger.info("  SQL files by size: %s", dict(sorted(sql_file_size_ranges.items())))
        
        # Large SQL files
        large_sql_files = query.files().language("sql").min_size(5000).execute()
        self.logger.info("  Large SQL files (>5KB): %d", large_sql_files.total_count)
        
        # Check for SQL files with parsed details 
        sql_files_with_details = [
            f for f in sql_files 
            if f.details and f.details.get_file_type() == 'sql'
        ]
        
        self.logger.info("  SQL files with parsed details: %d", len(sql_files_with_details))
        
        if sql_files_with_details:
            # Database objects analysis
            total_database_objects = 0
            total_code_mappings = 0
            total_table_operations = 0
            
            for file_item in sql_files_with_details:
                sql_detail = file_item.details
                total_database_objects += len(sql_detail.database_objects)
                total_code_mappings += len(sql_detail.code_mappings)
                total_table_operations += len(sql_detail.table_operations)
            
            self.logger.info("  Total database objects: %d", total_database_objects)
            self.logger.info("  Total code mappings: %d", total_code_mappings)
            self.logger.info("  Total table operations: %d", total_table_operations)
        else:
            self.logger.info("  No SQL files with parsed details found")
            self.logger.info("  (SQL files exist but haven't been processed by step02 parsers)")
    
    def generate_java_analysis_report(self) -> None:
        """Generate Java files analysis report."""
        self.logger.info("\n☕ JAVA FILES ANALYSIS REPORT:")
        
        query = SourceInventoryQuery(self.source_inventory)
        
        # Java files overview
        java_files_result = query.files().language("java").execute()
        java_files = java_files_result.items
        total_java_files = java_files_result.total_count
        
        self.logger.info("  Total Java files: %d", total_java_files)
        
        if total_java_files == 0:
            self.logger.info("  No Java files found for analysis")
            return
        
        # Java files with parsed details
        java_files_with_details = [
            f for f in java_files 
            if f.details and f.details.get_file_type() == 'java'
        ]
        
        self.logger.info("  Java files with parsed details: %d", len(java_files_with_details))
        
        if java_files_with_details:
            # Analyze architectural layers, frameworks, etc.
            layer_counts: Dict[str, int] = {}
            framework_hints = set()
            security_roles = set()
            total_rest_endpoints = 0
            manager_classes = 0
            total_code_mappings = 0
            service_dependencies = 0
            
            for file_item in java_files_with_details:
                java_detail = file_item.details
                
                # Layer analysis
                if hasattr(java_detail, 'detected_layer') and java_detail.detected_layer:
                    layer_name = java_detail.detected_layer.value
                    layer_counts[layer_name] = layer_counts.get(layer_name, 0) + 1
                
                # Framework detection
                if hasattr(java_detail, 'framework_hints'):
                    framework_hints.update(java_detail.framework_hints)
                
                # Security analysis
                if hasattr(java_detail, 'requires_security_roles'):
                    security_roles.update(java_detail.requires_security_roles)
                
                # REST endpoints
                if hasattr(java_detail, 'rest_endpoints'):
                    total_rest_endpoints += len(java_detail.rest_endpoints)
                
                # Manager pattern detection
                if hasattr(java_detail, 'is_manager_class') and java_detail.is_manager_class:
                    manager_classes += 1
                
                # Code mappings
                if hasattr(java_detail, 'code_mappings'):
                    total_code_mappings += len(java_detail.code_mappings)
                    
                    # Count service dependencies
                    service_dependencies += len([
                        mapping for mapping in java_detail.code_mappings 
                        if mapping.mapping_type in ['dependency_injection', 'service_dependency', 'method_call']
                    ])
            
            self.logger.info("  Architectural layers: %s", dict(sorted(layer_counts.items())))
            self.logger.info("  Detected frameworks: %s", sorted(framework_hints))
            self.logger.info("  Security roles found: %s", sorted(security_roles))
            self.logger.info("  REST endpoints: %d", total_rest_endpoints)
            self.logger.info("  Manager pattern classes: %d", manager_classes)
            self.logger.info("  Total code mappings: %d", total_code_mappings)
            self.logger.info("  Service dependencies: %d", service_dependencies)
        else:
            self.logger.info("  No Java files with parsed details found")
            self.logger.info("  (Java files exist but haven't been processed by step02 parsers)")

    def generate_subdomain_analysis_report(self) -> None:
        """Generate subdomain analysis report focusing on domain name patterns."""
        self.logger.info("\n🏗️ SUBDOMAIN ANALYSIS REPORT:")
        
        # Total subdomains by source location
        self.logger.info("Total Subdomains by Source Location:")
        location_counts = {}
        total_subdomains = 0
        
        # Track domain names and their locations/paths for duplicate analysis
        domain_name_locations: Dict[str, List[tuple[str, str]]] = {}  # domain_name -> list of (source_location, path)     
        for source_location in self.source_inventory.source_locations:
            subdomain_count = len(source_location.subdomains)
            location_counts[source_location.relative_path] = subdomain_count
            total_subdomains += subdomain_count
            
            # Track where each domain name appears
            for subdomain in source_location.subdomains:
                domain_name = subdomain.preliminary_subdomain_name
                if domain_name is not None:
                    if domain_name not in domain_name_locations:
                        domain_name_locations[domain_name] = []
                    domain_name_locations[domain_name].append((source_location.relative_path, subdomain.path))
        
        # Display counts by source location
        for location, count in sorted(location_counts.items()):
            self.logger.info("  %s: %d", location, count)
        
        self.logger.info("Total Subdomains: %d", total_subdomains)
        unique_domain_names = len(domain_name_locations)
        self.logger.info("Unique Domain Names: %d", unique_domain_names)
        
        # Analyze duplicate domain names
        duplicate_domains = {name: locations for name, locations in domain_name_locations.items() if len(locations) > 1}
        
        if duplicate_domains:
            self.logger.info("\nDuplicate Domain Names Analysis:")
            self.logger.info("  Domains appearing in multiple locations/paths: %d", len(duplicate_domains))
            
            # Show duplicate domains with count only
            for domain_name, locations in sorted(duplicate_domains.items()):
                self.logger.info("  '%s' appears in %d locations", domain_name, len(locations))
        else:
            self.logger.info("\nNo duplicate domain names found across locations/paths")
    
    def generate_java_entity_mapping_analysis(self) -> None:
        """Generate Java entity mapping analysis."""
        self.logger.info("\n🗺️ JAVA ENTITY MAPPING ANALYSIS:")
        
        query = SourceInventoryQuery(self.source_inventory)
        java_files = query.files().language("java").execute().items
        
        entity_mapping_classes = set()  # Use set to avoid duplicates
        for file_item in java_files:
            if file_item.details and hasattr(file_item.details, 'classes'):
                java_details = file_item.details
                for java_class in java_details.classes:
                    if java_class.entity_mapping is not None:
                        class_full_name = f"{java_class.package_name}.{java_class.class_name}" if java_class.package_name else java_class.class_name
                        entity_mapping_classes.add(class_full_name)
        
        self.logger.info("  Java classes with entity mappings: %d", len(entity_mapping_classes))
    
    def generate_java_sql_analysis(self) -> None:
        """Generate Java SQL usage analysis."""
        self.logger.info("\n🗄️ JAVA SQL USAGE ANALYSIS:")
        
        query = SourceInventoryQuery(self.source_inventory)
        java_files = query.files().language("java").execute().items
        
        stored_proc_classes = set()  # Use set to avoid duplicates
        sql_statement_classes = set()  # Use set to avoid duplicates
        
        for file_item in java_files:
            if file_item.details and hasattr(file_item.details, 'classes'):
                java_details = file_item.details
                
                for java_class in java_details.classes:
                    class_full_name = f"{java_class.package_name}.{java_class.class_name}" if java_class.package_name else java_class.class_name
                    
                    has_stored_procs = False
                    has_sql_statements = False
                    
                    for method in java_class.methods:
                        if method.sql_stored_procedures and len(method.sql_stored_procedures) > 0:
                            has_stored_procs = True
                        if method.sql_statements and len(method.sql_statements) > 0:
                            has_sql_statements = True
                    
                    if has_stored_procs:
                        stored_proc_classes.add(class_full_name)
                    if has_sql_statements:
                        sql_statement_classes.add(class_full_name)
        
        self.logger.info("  Java classes calling stored procedures: %d", len(stored_proc_classes))
        self.logger.info("  Java classes calling SQL statements: %d", len(sql_statement_classes))
    
    def _is_configuration_file(self, file_item: FileInventoryItem) -> bool:
        """Determine if a file is a configuration file."""
        # Based on actual data analysis, files with type 'config' are configuration files
        if file_item.type == 'config':
            return True
        
        # Also check for XML configuration files by language/extension patterns
        config_patterns = [
            'web.xml', 'struts', 'spring', 'tiles', 'validation', 'validator-rules', 'jboss-service.xml'
        ]

        # Check if it's XML language and matches configuration patterns
        if file_item.language == 'xml':
            file_name_lower = file_item.path.lower()
            return any(pattern in file_name_lower for pattern in config_patterns)
        
        # Check for properties files
        if file_item.language == 'properties':
            return True
            
        return False


def main() -> None:
    """Command-line interface for the source inventory report generator."""
    project_name = None   
    if len(sys.argv) < 2:
        print("Usage: python source_inventory_report.py <project_name>")
        print("Example: python source_inventory_report.py ct-hr-storm-test")
        project_name = "ct-hr-storm-test"
    elif len(sys.argv) == 2: 
        project_name = sys.argv[1]
    else:
        print("Too many arguments provided. Only the project name is required.")
        sys.exit(1)
    try:
        # Generate comprehensive report
        report = SourceInventoryReport(project_name)
        report.generate_full_report()
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Make sure step02 has been run for the specified project.")
        sys.exit(1)
    except Exception as e:  # pylint: disable=broad-except
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
