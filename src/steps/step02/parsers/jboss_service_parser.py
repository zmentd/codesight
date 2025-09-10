"""
JBoss service XML specific parser for Step 02 AST extraction.

Handles parsing of JBoss service XML files (jboss-service.xml, *-service.xml)
and converts them into domain models.
"""

from typing import Any, Dict, List

from config import Config
from domain.config_details import CodeMapping, ConfigurationDetails, SemanticCategory
from domain.source_inventory import FileInventoryItem, SourceInventory
from steps.step02.utils.file_inventory_utils import FileInventoryUtils
from utils.logging.logger_factory import LoggerFactory


class JBossServiceParser:
    """
    JBoss service XML parser.
    
    Converts JBoss service configuration data (MBeans, dependencies, attributes)
    into domain models.
    """
    
    def __init__(self, config: Config, source_inventory: SourceInventory):
        """
        Initialize JBoss service parser.
        
        Args:
            config: Configuration instance
            source_inventory: Source inventory for file lookups
        """
        self.config = config
        self.file_inventory_utils = FileInventoryUtils(source_inventory)
        self.logger = LoggerFactory.get_logger("steps.step02.jbossserviceparser")
    
    def parse(
        self, 
        structural_data: Dict[str, Any], 
        config_details: ConfigurationDetails, 
        file_item: FileInventoryItem
    ) -> None:
        """
        Parse JBoss service XML configuration data and populate ConfigurationDetails.
        
        Args:
            structural_data: Raw JBoss service XML configuration data
            config_details: ConfigurationDetails to populate
            file_item: File item containing source_location for resolving relative paths
        """
        self.logger.debug("Parsing JBoss service XML config with structural_data keys: %s", 
                         list(structural_data.keys()))
        
        # Process MBean definitions
        self._process_mbeans(structural_data, config_details)
        
        self.logger.debug("Completed JBoss service XML parsing: %d code_mappings", 
                         len(config_details.code_mappings))
    
    def _process_mbeans(
        self, 
        structural_data: Dict[str, Any], 
        config_details: ConfigurationDetails
    ) -> None:
        """
        Process MBean definitions from JBoss service XML using structured MBean data.
        
        Args:
            structural_data: JBoss service XML structural data from configuration reader
            config_details: ConfigurationDetails to populate
        """
        # Check if we have the new structured format with proper MBean hierarchy
        mbeans = structural_data.get("mbeans", [])
        
        if not mbeans:
            # Fallback to generic XML structure for backward compatibility
            self.logger.warning("No structured MBean data found, falling back to generic XML parsing")
            self._process_mbeans_generic(structural_data, config_details)
            return
        
        self.logger.debug("Found %d MBeans in structured format", len(mbeans))
        
        for mbean_data in mbeans:
            mbean_attributes = mbean_data.get("attributes", {})
            mbean_code = mbean_attributes.get("code", "")  
            mbean_name = mbean_attributes.get("name", "")
            
            self.logger.debug("Processing MBean: name=%s, code=%s", mbean_name, mbean_code)
            
            if mbean_name and mbean_code:
                # Create service mapping
                attributes = {
                    "type": "mbean_service", 
                    "service_name": mbean_name
                }
                
                # Process dependencies (now properly scoped to this MBean)
                dependencies = []
                for dep_data in mbean_data.get("dependencies", []):
                    if dep_data.get("text"):
                        dependencies.append(dep_data["text"])
                
                # Process configuration attributes (now properly scoped to this MBean)
                config_attributes = {}
                for attr_data in mbean_data.get("config_attributes", []):
                    attr_attrs = attr_data.get("attributes", {})
                    attr_name = attr_attrs.get("name", "")
                    attr_text = attr_data.get("text", "")
                    if attr_name and attr_text:
                        config_attributes[attr_name] = attr_text
                
                if dependencies:
                    attributes["dependencies"] = dependencies
                    self.logger.debug("MBean %s has %d dependencies", mbean_name, len(dependencies))
                
                if config_attributes:
                    # Prefix config attributes to avoid conflicts
                    for key, value in config_attributes.items():
                        attributes[f"config_{key}"] = str(value)
                    self.logger.debug("MBean %s has %d configuration attributes", 
                                    mbean_name, len(config_attributes))
                
                code_mapping = CodeMapping(
                    from_reference=mbean_name,
                    to_reference=mbean_code,
                    mapping_type="service",
                    framework=config_details.detected_framework,
                    semantic_category=SemanticCategory.ENTRY_POINT,
                    attributes=attributes
                )
                config_details.code_mappings.append(code_mapping)
                self.logger.debug("Created service mapping: %s -> %s", mbean_name, mbean_code)

    def _process_mbeans_generic(
        self, 
        structural_data: Dict[str, Any], 
        config_details: ConfigurationDetails
    ) -> None:
        """
        Process MBean definitions using generic XML structure (fallback method).
        
        Args:
            structural_data: Generic XML structural data from configuration reader
            config_details: ConfigurationDetails to populate
        """
        # Extract MBeans from generic XML elements structure
        elements = structural_data.get("elements", [])
        mbeans = [elem for elem in elements if elem.get("tag") == "mbean"]
        
        self.logger.debug("Found %d MBeans in generic XML structure", len(mbeans))
        
        for mbean_elem in mbeans:
            mbean_attributes = mbean_elem.get("attributes", {})
            mbean_code = mbean_attributes.get("code", "")  
            mbean_name = mbean_attributes.get("name", "")
            
            self.logger.debug("Processing MBean: name=%s, code=%s", mbean_name, mbean_code)
            
            if mbean_name and mbean_code:
                # Create service mapping
                attributes = {
                    "type": "mbean_service", 
                    "service_name": mbean_name
                }
                
                # Find dependencies and configuration attributes by scanning all elements
                # WARNING: This approach assigns ALL dependencies and attributes to ALL MBeans
                dependencies = []
                config_attributes = {}
                
                # Collect <depends> elements from text_content (they don't have attributes)
                text_content = structural_data.get("text_content", [])
                for text_elem in text_content:
                    if text_elem.get("tag") == "depends" and text_elem.get("text"):
                        dependencies.append(text_elem["text"])
                
                # Collect <attribute> elements from elements (they have name attribute)
                for elem in elements:
                    if elem.get("tag") == "attribute":
                        attr_attrs = elem.get("attributes", {})
                        attr_name = attr_attrs.get("name", "")
                        attr_text = elem.get("text", "")
                        if attr_name and attr_text:
                            config_attributes[attr_name] = attr_text
                
                if dependencies:
                    attributes["dependencies"] = dependencies
                    self.logger.warning("MBean %s assigned %d dependencies (may include dependencies from other MBeans)", 
                                      mbean_name, len(dependencies))
                
                if config_attributes:
                    # Prefix config attributes to avoid conflicts
                    for key, value in config_attributes.items():
                        attributes[f"config_{key}"] = str(value)
                    self.logger.warning("MBean %s assigned %d configuration attributes (may include attributes from other MBeans)", 
                                      mbean_name, len(config_attributes))
                
                code_mapping = CodeMapping(
                    from_reference=mbean_name,
                    to_reference=mbean_code,
                    mapping_type="service",
                    framework=config_details.detected_framework,
                    semantic_category=SemanticCategory.ENTRY_POINT,
                    attributes=attributes
                )
                config_details.code_mappings.append(code_mapping)
                self.logger.debug("Created service mapping: %s -> %s", mbean_name, mbean_code)
