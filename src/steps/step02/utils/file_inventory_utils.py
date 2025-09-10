"""
Utility functions for working with file inventory data from Step01 output.

Provides methods to locate and filter file inventory items from the filesystem
analyzer output JSON.
"""

from typing import Any, Dict, List, Optional

from domain.source_inventory import FileInventoryItem, SourceInventory
from utils.logging.logger_factory import LoggerFactory
from utils.path_utils import PathUtils


class FileInventoryUtils:
    """
    Utility class for working with file inventory data from Step01 output.
    
    Provides methods to search, filter, and locate files from the filesystem
    analyzer output structure.
    """
    
    def __init__(self, source_inventory: SourceInventory) -> None:
        """
        Initialize with Step01 filesystem analyzer output.
        
        Args:
            source_inventory: Complete Step01 output dictionary
        """
        self.source_inventory = source_inventory
        self.logger = LoggerFactory.get_logger("core")
    
    def find_file_by_path(self, target_path: str, source_location_path: str) -> Optional[FileInventoryItem]:
        """
        Find a file inventory item by its path.
        
        Args:
            target_path: Path to search for (e.g., "WEB-INF/validation.xml")
            source_location: Source location directory for resolving relative paths
            
        Returns:
            FileInventoryItem if found, None otherwise
        """
        # Get project root from config
        from config import Config
        config = Config.get_instance()
        project_root = config.get_project_source_path()
        self.logger.debug("Project root: %s", project_root)
        self.logger.debug("Source location path: %s", source_location_path)
        self.logger.debug("Target path: %s", target_path)
        
        # Navigate through the Step01 output structure
        source_locations = self.source_inventory.source_locations
        
        for source_location_item in source_locations:
            # if source_location_item.relative_path != source_location_path:
            #     continue
            subdomains = source_location_item.subdomains
            for subdomain in subdomains:
                file_inventory = subdomain.file_inventory
                for file_item in file_inventory:
                    file_path = file_item.path
                    if file_path == target_path:
                        return file_item
        
        return None
    
    def find_files_by_pattern(self, pattern: str, source_location_path: str) -> List[FileInventoryItem]:
        """
        Find file inventory items matching a pattern.
        
        Args:
            pattern: Pattern to match (supports simple wildcards like *.xml)
            
        Returns:
            List of matching file inventory items
        """
        import fnmatch
        
        matching_files = []
        pattern_normalized = PathUtils.normalize_path(pattern)
        
        # Navigate through the Step01 output structure
        source_locations = self.source_inventory.source_locations
        
        for source_location_item in source_locations:
            if source_location_item.relative_path != source_location_path:
                continue
            subdomains = source_location_item.subdomains
            for subdomain in subdomains:
                file_inventory = subdomain.file_inventory
                for file_item in file_inventory:
                    file_path = file_item.path
                    file_path_normalized = PathUtils.normalize_path(file_path)
                    if fnmatch.fnmatch(file_path_normalized, pattern_normalized):
                        matching_files.append(file_item)

        return matching_files
    
    def find_files_by_type(self, file_type: str, source_location_path: str) -> List[FileInventoryItem]:
        """
        Find file inventory items by type.
        
        Args:
            file_type: File type to search for (e.g., "config", "web", "java")
            
        Returns:
            List of matching file inventory items
        """
        matching_files = []
        
        # Navigate through the Step01 output structure
        source_locations = self.source_inventory.source_locations
        
        for source_location_item in source_locations:
            if source_location_item.relative_path != source_location_path:
                continue
            subdomains = source_location_item.subdomains
            for subdomain in subdomains:
                file_inventory = subdomain.file_inventory
                for file_item in file_inventory:
                    if file_item.type == file_type:
                        matching_files.append(file_item)

        return matching_files
    
    def find_files_by_language(self, language: str, source_location_path: str) -> List[FileInventoryItem]:
        """
        Find file inventory items by language.
        
        Args:
            language: Programming language to search for (e.g., "java", "xml", "jsp")
            
        Returns:
            List of matching file inventory items
        """
        matching_files = []
        
        # Navigate through the Step01 output structure
        source_locations = self.source_inventory.source_locations
        
        for source_location_item in source_locations:
            if source_location_item.relative_path != source_location_path:
                continue
            subdomains = source_location_item.subdomains
            for subdomain in subdomains:
                file_inventory = subdomain.file_inventory
                for file_item in file_inventory:
                    if file_item.language == language:
                        matching_files.append(file_item)

        return matching_files
    
    def find_files_by_functional_name(self, functional_name: str, source_location_path: str) -> List[FileInventoryItem]:
        """
        Find file inventory items by functional name.
        
        Args:
            functional_name: Functional name to search for (e.g., "validation", "struts")
            
        Returns:
            List of matching file inventory items
        """
        matching_files = []
        
        # Navigate through the Step01 output structure
        source_locations = self.source_inventory.source_locations
        
        for source_location_item in source_locations:
            if source_location_item.relative_path != source_location_path:
                continue
            subdomains = source_location_item.subdomains
            for subdomain in subdomains:
                file_inventory = subdomain.file_inventory
                for file_item in file_inventory:
                    if file_item.functional_name == functional_name:
                        matching_files.append(file_item)

        return matching_files
