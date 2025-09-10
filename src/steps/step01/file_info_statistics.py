from typing import Any, Dict, List

from domain.source_inventory import EnumUtils
from utils.logging.logger_factory import LoggerFactory


class FileInfoStatistics:
    """
    This class provides methods to gather statistics about files in a directory.
    It can count the number of files, directories, and calculate the total size of files.
    """
    
    def __init__(self) -> None:
        self.logger = LoggerFactory.get_logger("steps")

    def get_statistics(self, file_inventory: List[Dict]) -> Dict[str, Any]:
        """Generate comprehensive statistics from step01 results."""
        
        # Get unique subdomain names and counts
        subdomain_stats = self._analyze_subdomains(file_inventory)
        
        return {
            'file_inventory_count': len(file_inventory),
            
            # Counts by type for each type (from enhanced scanner _determine_file_type)
            'count_type': self._count_by_field(file_inventory, 'type'),
            
            # Counts by language (from enhanced scanner _detect_language)
            'count_language': self._count_by_field(file_inventory, 'language'),
            
            # Counts by preliminary subdomain type 
            'count_preliminary_subdomain_type': self._count_subdomain_types(file_inventory),
            'count_preliminary_subdomain_type_none': self._count_none_values(file_inventory, 'preliminary_subdomain_type'),
            
            # Counts by preliminary subdomain name
            'count_preliminary_subdomain_name': self._count_subdomain_names(file_inventory),
            'count_preliminary_subdomain_name_none': self._count_none_values(file_inventory, 'preliminary_subdomain_name'),
            
            # Enhanced subdomain analysis
            'subdomain_analysis': subdomain_stats,
            
            # Counts by tags
            'count_tags': self._count_tags(file_inventory),
            'count_tags_none': self._count_empty_tags(file_inventory),
            
            # Counts by package layer for each layer type (from config package_patterns)
            'count_package_layer': self._count_package_layers(file_inventory),
            
            # Counts by architectural pattern for each pattern type (from config architectural_patterns)
            'count_architectural_pattern': self._count_architectural_patterns(file_inventory),
        }
    
    def _count_by_field(self, file_inventory: List[Dict], field: str) -> Dict[str, int]:
        """Count occurrences of values in a specific field."""
        counts: Dict[str, int] = {}
        for file_info in file_inventory:
            value = file_info.get(field, 'unknown')
            counts[value] = counts.get(value, 0) + 1
        return counts
    
    def _count_subdomain_types(self, file_inventory: List[Dict]) -> int:
        """Count files with meaningful preliminary subdomain types (not none/Other/unknown)."""
        count = 0
        excluded_types = {'none', 'other', 'unknown', None}
        
        for file_info in file_inventory:
            comp_type = file_info.get('preliminary_subdomain_type', '').lower()
            if comp_type not in excluded_types and comp_type:
                count += 1
        return count
    
    def _count_subdomain_names(self, file_inventory: List[Dict]) -> int:
        """Count files with meaningful preliminary subdomain names (not none/Other/unknown)."""
        count = 0
        excluded_names = {'none', 'other', 'unknown', None, ''}
        
        for file_info in file_inventory:
            comp_name = file_info.get('preliminary_subdomain_name')
            if comp_name and str(comp_name).lower() not in excluded_names:
                count += 1
        return count
    
    def _count_none_values(self, file_inventory: List[Dict], field: str) -> int:
        """Count files with none/Other/unknown values for a field."""
        count = 0
        excluded_values = {'none', 'other', 'unknown', None, ''}
        
        for file_info in file_inventory:
            value = file_info.get(field)
            if not value or str(value).lower() in excluded_values:
                count += 1
        return count
    
    def _count_tags(self, file_inventory: List[Dict]) -> int:
        """Count files with meaningful tags (not empty/none)."""
        count = 0
        for file_info in file_inventory:
            tags = file_info.get('tags', [])
            if tags and len(tags) > 0:
                count += 1
        return count
    
    def _count_empty_tags(self, file_inventory: List[Dict]) -> int:
        """Count files with empty or meaningless tags."""
        count = 0
        for file_info in file_inventory:
            tags = file_info.get('tags', [])
            if not tags or len(tags) == 0:
                count += 1
        return count
    
    def _count_package_layers(self, file_inventory: List[Dict]) -> Dict[str, int]:
        """Count files by package layer (from enhanced scanner package patterns)."""
        # All possible package layers from enhanced scanner _match_package_patterns
        layers = {
            'UI': 0,
            'Service': 0, 
            'Database': 0,
            'Integration': 0,
            'Configuration': 0,
            'Utility': 0,
            'Reporting': 0,
            'Other': 0,
            'none': 0
        }
        
        for i, file_info in enumerate(file_inventory):
            if 'package_layer' not in file_info:
                self.logger.error("Unexpected structure in file at index %d: %s", i, file_info)
                raise ValueError(f"File at index {i} missing 'package_layer' field. Expected structure: {{'package_layer': {{'layer': 'LayerName', ...}}}}")
            
            package_layer = file_info.get('package_layer', {})
            if not isinstance(package_layer, dict):
                self.logger.error("Unexpected structure in file at index %d: %s", i, file_info)
                raise ValueError(f"File at index {i} has invalid 'package_layer' structure. Expected dict with 'layer' field, got: {type(package_layer)}")
            
            if 'layer' not in package_layer:
                self.logger.error("Unexpected structure in file at index %d: %s", i, file_info)
                raise ValueError(f"File at index {i} 'package_layer' missing 'layer' field. Expected structure: {{'package_layer': {{'layer': 'LayerName', ...}}}}")
            
            layer = package_layer.get('layer', 'none')
            
            # Use EnumUtils to convert layer to LayerType enum, then get its value
            try:
                layer_enum = EnumUtils.to_layer_type(layer)
                layer = layer_enum.value
            except (ValueError, AttributeError) as e:
                self.logger.warning("Failed to convert layer '%s' to enum: %s", layer, e)
                layer = 'Other'
            
            # Normalize layer name
            layer = layer if layer in layers else 'Other'
            layers[layer] += 1
            
        return layers
    
    def _count_architectural_patterns(self, file_inventory: List[Dict]) -> Dict[str, int]:
        """Count files by architectural pattern (from enhanced scanner architectural_patterns)."""
        # All possible architectural patterns from enhanced scanner _match_architectural_patterns
        patterns = {
            'application': 0,
            'business': 0,
            'data_access': 0,
            'shared': 0,
            'security': 0,
            'integration': 0,
            'none': 0
        }
        
        for i, file_info in enumerate(file_inventory):
            if 'architectural_pattern' not in file_info:
                self.logger.error("Unexpected structure in file at index %d: %s", i, file_info)
                raise ValueError(f"File at index {i} missing 'architectural_pattern' field. Expected structure: {{'architectural_pattern': {{'architectural_layer': 'PatternName', ...}}}}")
            
            architectural_pattern = file_info.get('architectural_pattern', {})
            if not isinstance(architectural_pattern, dict):
                self.logger.error("Unexpected structure in file at index %d: %s", i, file_info)
                raise ValueError(f"File at index {i} has invalid 'architectural_pattern' structure. Expected dict with 'architectural_layer' field, got: {type(architectural_pattern)}")
            
            # Use architectural_layer field instead of pattern field
            pattern = architectural_pattern.get('architectural_layer', 'none')
            
            # Use EnumUtils to convert pattern to ArchitecturalLayerType enum, then get its value
            try:
                pattern_enum = EnumUtils.to_architectural_layer_type(pattern)
                pattern = pattern_enum.value
            except (ValueError, AttributeError) as e:
                self.logger.warning("Failed to convert architectural pattern '%s' to enum: %s", pattern, e)
                pattern = 'none'
            
            # Normalize pattern name to handle unknown values
            if pattern == 'unknown':
                pattern = 'none'
            pattern = pattern if pattern in patterns else 'none'
            patterns[pattern] += 1
            
        return patterns

    def _analyze_subdomains(self, file_inventory: List[Dict]) -> Dict[str, Any]:
        """Analyze subdomain distribution and provide detailed statistics."""
        subdomain_counts: Dict[str, int] = {}
        unique_subdomains = set()
        excluded_names = {'none', 'other', 'unknown', None, ''}
        
        # Count files per subdomain and collect unique names
        for file_info in file_inventory:
            subdomain_name = file_info.get('preliminary_subdomain_name')
            if subdomain_name and str(subdomain_name).lower() not in excluded_names:
                unique_subdomains.add(subdomain_name)
                subdomain_counts[subdomain_name] = subdomain_counts.get(subdomain_name, 0) + 1
        
        # Sort subdomains by file count (descending) for better analysis
        sorted_subdomains = sorted(subdomain_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'unique_subdomain_count': len(unique_subdomains),
            'unique_subdomain_names': sorted(list(unique_subdomains)),
            'subdomain_file_counts': dict(sorted_subdomains),
            'top_10_subdomains': dict(sorted_subdomains[:10]) if sorted_subdomains else {},
            'subdomain_coverage_percentage': round((len(unique_subdomains) * 100.0) / len(file_inventory), 2) if file_inventory else 0.0
        }
