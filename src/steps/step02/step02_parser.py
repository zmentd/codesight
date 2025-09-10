"""
Integration test for ConfigurationParser using the ct-hr-storm-test project.

This test validates the complete configuration parsing pipeline using real CT-HR-STORM
configuration files from the test project with proper Configuration.initialize() setup.
"""

import json
import shutil
import sys
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List

# Add src to Python path to ensure correct imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import Config
from domain.java_details import JavaDetails
from domain.source_inventory import FileInventoryItem, SourceInventory
from domain.sql_details import SQLDetails
from steps.step02.jpype_manager import JPypeManager
from steps.step02.parsers.configuration_parser import ConfigurationParser
from steps.step02.parsers.java_parser import JavaParser
from steps.step02.parsers.sql_parser import SQLParser
from utils.logging.logger_factory import LoggerFactory


class EnumJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Enum serialization by converting to their values."""
    def default(self, o: Any) -> Any:
        if isinstance(o, Enum):
            return o.value
        return super().default(o)


class Step02Parser:
    """Integration test for Parsers using ct-hr-storm-test project."""
    def __init__(self, project_name: str = "ct-hr-storm") -> None:
        # Initialize config for the specified project
        Config.initialize(project_name=project_name)

        LoggerFactory.initialize("../../../config/logging.yaml")
        self.logger = LoggerFactory.get_logger("steps")
        JPypeManager.initialize()
        self.config = Config.get_instance()
        self.source_inventory = SourceInventory()

        # Load the source inventory from the step01 output file
        step01_output_path = Path(self.config.get_output_path_for_step("step01"))
        output_dir = step01_output_path.parent
        step01_output_path = output_dir / "step01_filesystem_analyzer_output.json"
        if not step01_output_path.exists():
            raise FileNotFoundError(f"Step01 output file not found: {step01_output_path}")

        self.logger.info("Loading source inventory from: %s", step01_output_path)
        with open(step01_output_path, 'r', encoding='utf-8') as f:
            step01_data = json.load(f)
            # Extract the source_inventory from the JSON structure
            if 'source_inventory' in step01_data:
                self.source_inventory = SourceInventory.from_dict(step01_data['source_inventory'])
            else:
                # Fallback: assume the entire JSON is the source inventory
                self.source_inventory = SourceInventory.from_dict(step01_data)
        self.logger.info("Source inventory loaded with %d source locations", len(self.source_inventory.source_locations))
        self.output_dir = Path(self.config.project.output_path) / "step02"

    def parse_source_inventory(self) -> None:
        """Test creating a step02 output file with configuration details."""
        start_time = time.time()
        # Get the step02 output path
        step02_output_path = Path(self.config.get_output_path_for_step("step02"))
        step02_output_path.parent.mkdir(parents=True, exist_ok=True)

        self.logger.info("Creating step02 output at: %s", step02_output_path)

        # Track processing statistics
        total_files_processed = 0
        config_files_processed = 0
        java_files_processed = 0
        sql_files_processed = 0
        files_with_config_details = 0
        include_packages = ["com.nbcuni.dcss.storm", "com.inbcu.storm"]
        # Create a copy of the source inventory data to modify
        output_data = {
            'source_inventory': {
                'source_locations': []
            },
            'processing_summary': {
                'total_files': 0,
                'configuration_files': 0,
                'java_files': 0,
                'sql_files': 0,
                'files_with_config_details': 0
            }
        }
        confiParser = ConfigurationParser(self.config, self.source_inventory)
        javaParser = JavaParser(self.config, JPypeManager.get_instance())
        sqlParser = SQLParser(self.config)
        # # Process each source location
        for source_location in self.source_inventory.source_locations:
            self.logger.info("Processing source location: %s", source_location.relative_path)
            # Process each subdomain
            for subdomain in source_location.subdomains:
                self.logger.info("Processing subdomain: %s", subdomain.name)
                # Process each file in the inventory
                for file_item in subdomain.file_inventory:
                    total_files_processed += 1
                    try:
                        # Build the full file path
                        source_path = Path(self.config.project.source_path)
                        file_path = source_path / file_item.source_location / file_item.path
                        self.logger.info("Processing file: %s", file_path)
                        
                        if self._is_configuration_file(file_item):
                            config_files_processed += 1
                            if confiParser.can_parse(file_item):
                                # Parse the configuration file
                                config_details = confiParser.parse_file(file_item)
                                file_item.details = config_details
                                files_with_config_details += 1
                        elif javaParser.can_parse(file_item):
                            java_files_processed += 1
                            # Parse Java files for AST extraction
                            java_details = javaParser.parse_file(file_item, include_packages, True)
                            file_item.details = java_details
                        elif sqlParser.can_parse(file_item):
                            sql_files_processed += 1
                            # Parse SQL files for database object extraction
                            sql_details = sqlParser.parse_file(file_item)
                            file_item.details = sql_details
                        else:
                            self.logger.warning("No parser for file: %s", file_path)

                    except Exception as e:  # noqa: BLE001  # pylint: disable=W0718
                        error_msg = "Error processing config file %s: %s"
                        self.logger.error(error_msg, file_item.path, str(e))

        output_data['source_inventory'] = self.source_inventory.to_dict()
        
        # Update processing summary
        output_data['processing_summary'] = {
            'total_files': total_files_processed,
            'configuration_files': config_files_processed,
            'java_files': java_files_processed,
            'sql_files': sql_files_processed,
            'files_with_config_details': files_with_config_details,
            'processing_date': '2025-08-01T00:00:00.000000',
            'step': 'step02',
            'parser_version': '1.0.0'
        }

        # Write the output file
        with open(step02_output_path, 'w', encoding='utf-8') as f:
            # Convert any sets to lists for JSON serialization
            # json_safe_data = self._convert_sets_to_lists(output_data)
            json.dump(output_data, f, indent=2, ensure_ascii=False, cls=EnumJSONEncoder)

        self.logger.info("Step02 output written to: %s", step02_output_path)
        self.logger.info("Processing summary:")
        self.logger.info("  Total files processed: %d", total_files_processed)
        self.logger.info("  Configuration files: %d", config_files_processed)
        self.logger.info("  Java files: %d", java_files_processed)
        self.logger.info("  SQL files: %d", sql_files_processed)
        self.logger.info("  Files with config details: %d", files_with_config_details)
        end_time = time.time()
        elapsed_time = end_time - start_time
        self.logger.info("  Elapsed time: %.2f seconds", elapsed_time)
        
        # Generate comprehensive analysis report using the source inventory report
        from steps.step02.source_inventory_report import SourceInventoryReport
        report = SourceInventoryReport(self.config.project.name, self.source_inventory)
        report.generate_full_report()

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


if __name__ == '__main__':
    # Get project name from command line arguments, default to "ct-hr-storm"
    project_name = sys.argv[1] if len(sys.argv) > 1 else "ct-hr-storm-test"
    
    print(f"Running Step02 parser for project: {project_name}")
    
    # Run the parser
    test = Step02Parser(project_name)
    test.parse_source_inventory()
