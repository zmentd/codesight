"""
Tiles configuration specific parser for Step 02 AST extraction.

Handles parsing of tiles-defs.xml configuration files
and converts them into domain models.
"""

from typing import Any, Dict, List

from config import Config
from domain.config_details import CodeMapping, ConfigurationDetails, SemanticCategory
from domain.source_inventory import FileInventoryItem, SourceInventory
from steps.step02.utils.file_inventory_utils import FileInventoryUtils
from utils.logging.logger_factory import LoggerFactory


class TilesConfigParser:
    """
    Tiles configuration parser.
    
    Converts Tiles definition data (templates, definitions, extends mappings)
    into domain models.
    """
    
    def __init__(self, config: Config, source_inventory: SourceInventory):
        """
        Initialize Tiles configuration parser.
        
        Args:
            config: Configuration instance
            source_inventory: Source inventory for file lookups
        """
        self.config = config
        self.file_inventory_utils = FileInventoryUtils(source_inventory)
        self.logger = LoggerFactory.get_logger("steps.step02.tilesparser")
    
    def parse(
        self, 
        structural_data: Dict[str, Any], 
        config_details: ConfigurationDetails, 
        file_item: FileInventoryItem
    ) -> None:
        """
        Parse Tiles configuration data and populate ConfigurationDetails.
        
        Args:
            structural_data: Raw Tiles configuration data
            config_details: ConfigurationDetails to populate
            file_item: File item containing source_location for resolving relative paths
        """
        self.logger.debug("Parsing Tiles config with structural_data keys: %s", 
                         list(structural_data.keys()))
        
        # Process template definitions
        self._process_template_definitions(structural_data, config_details)
        
        # Process definition inheritance mappings
        self._process_extends_mappings(structural_data, config_details)
        
        # Process tile components (put elements)
        self._process_tile_components(structural_data, config_details)
        
        self.logger.debug("Completed Tiles parsing: %d code_mappings", 
                         len(config_details.code_mappings))
    
    def _process_template_definitions(
        self, 
        structural_data: Dict[str, Any], 
        config_details: ConfigurationDetails
    ) -> None:
        """
        Process template definitions from Tiles configuration.
        
        Args:
            structural_data: Raw Tiles configuration data
            config_details: ConfigurationDetails to populate
        """
        definitions = structural_data.get("definitions", [])
        template_definitions = structural_data.get("template_definitions", [])
        
        self.logger.debug("Found %d total definitions, %d template definitions", 
                         len(definitions), len(template_definitions))
        
        # Process all definitions to create name->path mappings
        for definition in definitions:
            name = definition.get("name", "")
            path = definition.get("path", "")
            template = definition.get("template", "")
            extends = definition.get("extends", "")
            
            if not name:
                continue
            
            # Create template mapping if this definition has a path (template file)
            if path:
                mapping = CodeMapping(
                    from_reference=name,
                    to_reference=path,
                    mapping_type="template",
                    framework="tiles",
                    semantic_category=SemanticCategory.COMPOSITION,
                    attributes={
                        "type": "template_definition",
                        "definition_name": name,
                        "template_path": path,
                        "extends": extends if extends else ""
                    }
                )
                config_details.code_mappings.append(mapping)
            
            # Create template reference mapping if this definition uses a template
            elif template:
                mapping = CodeMapping(
                    from_reference=name,
                    to_reference=template,
                    mapping_type="template_reference",
                    framework="tiles",
                    semantic_category=SemanticCategory.VIEW_RENDER,
                    attributes={
                        "type": "template_reference",
                        "definition_name": name,
                        "template_reference": template,
                        "extends": extends if extends else ""
                    }
                )
                config_details.code_mappings.append(mapping)
    
    def _process_extends_mappings(
        self, 
        structural_data: Dict[str, Any], 
        config_details: ConfigurationDetails
    ) -> None:
        """
        Process definition inheritance mappings from Tiles configuration.
        
        Args:
            structural_data: Raw Tiles configuration data
            config_details: ConfigurationDetails to populate
        """
        extends_mappings = structural_data.get("extends_mappings", [])
        
        self.logger.debug("Found %d extends mappings", len(extends_mappings))
        
        # Create inheritance mappings
        for extends_mapping in extends_mappings:
            name = extends_mapping.get("name", "")
            extends = extends_mapping.get("extends", "")
            
            if name and extends:
                mapping = CodeMapping(
                    from_reference=name,
                    to_reference=extends,
                    mapping_type="inheritance",
                    framework="tiles",
                    semantic_category=SemanticCategory.INHERITANCE,
                    attributes={
                        "type": "definition_inheritance",
                        "child_definition": name,
                        "parent_definition": extends,
                        "relationship": "extends"
                    }
                )
                config_details.code_mappings.append(mapping)
    
    def _process_tile_components(
        self, 
        structural_data: Dict[str, Any], 
        config_details: ConfigurationDetails
    ) -> None:
        """
        Process tile component mappings (put elements) from Tiles configuration.
        
        Args:
            structural_data: Raw Tiles configuration data
            config_details: ConfigurationDetails to populate
        """
        definitions = structural_data.get("definitions", [])
        
        # Process put elements within definitions
        for definition in definitions:
            definition_name = definition.get("name", "")
            puts = definition.get("puts", [])
            
            if not definition_name:
                continue
            
            for put in puts:
                put_name = put.get("name", "")
                put_value = put.get("value", "")
                put_type = put.get("type", "")
                put_direct = put.get("direct", "false")
                
                if put_name and put_value:
                    # Determine component type based on value pattern
                    component_type = self._determine_component_type(put_value, put_type)
                    
                    mapping = CodeMapping(
                        from_reference=f"{definition_name}.{put_name}",
                        to_reference=put_value,
                        mapping_type="component",
                        framework="tiles",
                        semantic_category=SemanticCategory.COMPOSITION,
                        attributes={
                            "type": "tile_component",
                            "definition_name": definition_name,
                            "component_name": put_name,
                            "component_value": put_value,
                            "component_type": component_type,
                            "put_type": put_type if put_type else "string",
                            "direct": put_direct
                        }
                    )
                    config_details.code_mappings.append(mapping)
    
    def _determine_component_type(self, value: str, put_type: str) -> str:
        """
        Determine the type of tile component based on its value and type.
        
        Args:
            value: The component value
            put_type: The explicit put type (if any)
            
        Returns:
            Component type classification
        """
        if put_type:
            return put_type
        
        # Classify based on value patterns
        value_lower = value.lower()
        
        # Check URLs first (before file extensions)
        if value_lower.startswith('http'):
            return "url"
        elif value_lower.endswith(('.jsp', '.jspx')):
            return "jsp_page"
        elif value_lower.endswith(('.html', '.htm')):
            return "html_page"
        elif value_lower.startswith('/') and ('/' in value_lower[1:]):
            return "path"
        else:
            return "string"
