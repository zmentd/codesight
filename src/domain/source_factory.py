"""
Factory and utility functions for creating source inventory objects from JSON data.

This module provides convenience functions for parsing STEP01 output JSON and creating
the appropriate domain objects with proper type handling.
"""

from typing import Any, Dict, Iterator, Type

from .java_details import JavaClass, JavaDetails
from .jsp_details import JspDetails
from .source_inventory import FileDetailsBase, SourceInventory


def create_details_factory() -> Dict[str, Type[FileDetailsBase]]:
    """Create a factory mapping for file detail types."""
    return {
        'java': JavaDetails,
        'jsp': JspDetails
    }


def parse_step01_sources(sources_data: list) -> SourceInventory:
    """
    Parse sources data from STEP01 output JSON.
    
    Args:
        sources_data: List of source dictionaries from JSON
        
    Returns:
        SourceInventory: Parsed source inventory object
    """
    factory = create_details_factory()
    
    inventory_data = {'sources': sources_data}
    return SourceInventory.from_dict(inventory_data, factory)


def parse_step01_output(step01_json: Dict[str, Any]) -> SourceInventory:
    """
    Parse complete STEP01 output JSON.
    
    Args:
        step01_json: Complete STEP01 JSON output
        
    Returns:
        SourceInventory: Parsed source inventory object
    """
    if 'sources' not in step01_json:
        raise ValueError("No 'sources' key found in STEP01 output")
    
    return parse_step01_sources(step01_json['sources'])


# Example usage and validation functions
def validate_source_inventory(inventory: SourceInventory) -> Dict[str, Any]:
    """
    Validate and get statistics about source inventory.
    
    Args:
        inventory: Source inventory to validate
        
    Returns:
        Dict containing validation statistics
    """
    stats: Dict[str, Any] = {
        'total_sources': inventory.get_total_sources(),
        'total_files': inventory.get_total_files(),
        'java_files': len(inventory.get_all_files_by_language('java')),
        'jsp_files': len(inventory.get_all_files_by_language('jsp')),
        'sources_by_path': {}
    }
    
    for source in inventory.sources:
        stats['sources_by_path'][source.root_path] = {
            'subdomains': source.get_total_subdomains(),
            'files': source.get_total_files(),
            'java_files': len(source.get_files_by_language('java')),
            'jsp_files': len(source.get_files_by_language('jsp'))
        }
    
    return stats


def extract_business_packages(inventory: SourceInventory) -> list:
    """
    Extract meaningful business packages from Java files.
    
    Args:
        inventory: Source inventory to analyze
        
    Returns:
        List of unique business package names
    """
    def iter_java_classes(inv: SourceInventory) -> Iterator[JavaClass]:
        for source in inv.sources:
            for subdomain in source.subdomains:
                for file_item in subdomain.file_inventory:
                    if (file_item.language.lower() == 'java' and 
                        file_item.details and 
                        isinstance(file_item.details, JavaDetails)):
                        for java_class in file_item.details.classes:
                            yield java_class

    packages = set()
    for java_class in iter_java_classes(inventory):
        if java_class.package_name:
            package_parts = java_class.package_name.split('.')
            if len(package_parts) >= 3:
                business_package = '.'.join(package_parts[:4])
                packages.add(business_package)

    return sorted(list(packages))
