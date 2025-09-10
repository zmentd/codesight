"""
Struts 2.x specific parser for Step 02 AST extraction.

Handles parsing of Struts 2.x configuration files (struts.xml, struts-*.xml)
and converts them into domain models.
"""

from typing import Any, Dict, List, Optional

from config import Config
from domain.config_details import (
    CodeMapping,
    CodeMappingGroup,
    ConfigurationDetails,
    DeterministicForward,
    SemanticCategory,
)
from domain.source_inventory import FileInventoryItem, SourceInventory
from steps.step02.utils.file_inventory_utils import FileInventoryUtils
from utils.logging.logger_factory import LoggerFactory


class Struts2xParser:
    """
    Struts 2.x configuration parser.
    
    Converts Struts 2.x configuration data (actions, packages, interceptors, etc.)
    into domain models.
    """
    
    def __init__(self, config: Config, source_inventory: SourceInventory):
        """
        Initialize Struts 2.x parser.
        
        Args:
            config: Configuration instance
            source_inventory: Source inventory for file lookup
        """
        self.config = config
        self.file_inventory_utils = FileInventoryUtils(source_inventory)
        self.logger = LoggerFactory.get_logger("steps.step02.struts2xparser")
    
    def parse(
        self, 
        structural_data: Dict[str, Any], 
        config_details: ConfigurationDetails, 
        file_item: FileInventoryItem
    ) -> None:
        """
        Parse Struts 2.x configuration data and populate ConfigurationDetails.
        
        Args:
            structural_data: Raw Struts 2.x configuration data
            config_details: ConfigurationDetails to populate
            file_item: File item containing source_location for resolving relative paths
        """
        self.logger.debug("Parsing Struts 2.x config with structural_data keys: %s", 
                         list(structural_data.keys()))
        
        # 1. Build global action registry (don't create final mappings yet)
        global_actions = self._process_actions(structural_data)
        
        # 2. Process packages and resolve action references
        self._process_packages(structural_data, config_details, global_actions)
        
        # 3. Handle any standalone global actions (not referenced by packages)
        self._process_standalone_globals(global_actions, config_details)
        
        # 4. Process other elements
        self._process_interceptors(structural_data, config_details)
        self._process_constants(structural_data, config_details)
        
        self.logger.debug("Completed Struts 2.x parsing: %d code_mappings", 
                         len(config_details.code_mappings))
    
    def _process_actions(
        self, 
        structural_data: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Process Struts 2.x global actions and build registry.
        
        Args:
            structural_data: Raw Struts configuration data
            
        Returns:
            Dictionary of global actions by name
        """
        actions = structural_data.get("actions", [])
        
        self.logger.debug("Found %d global Struts 2.x actions", len(actions))
        
        # Build global action registry
        global_actions = {}
        for action_data in actions:
            action_name = action_data.get("name", "")
            if action_name and action_data.get("class"):  # Full definition
                global_actions[action_name] = action_data
                self.logger.debug("Registered global action: %s -> %s", 
                                 action_name, action_data.get("class", ""))
        
        return global_actions
    
    def _create_action_mapping_for_package(
        self, 
        action_data: Dict[str, Any], 
        config_details: ConfigurationDetails,
        namespace: Optional[str] = None,
        package_name: Optional[str] = None
    ) -> Optional[CodeMapping]:
        """
        Create a CodeMapping for a Struts 2.x action within a package.
        
        Args:
            action_data: Action configuration data
            config_details: ConfigurationDetails for framework info
            namespace: Package namespace (optional)
            package_name: Package name (optional)
            
        Returns:
            CodeMapping instance or None if invalid
        """
        action_name = action_data.get("name", "")
        action_class = action_data.get("class", "")
        action_method = action_data.get("method", "execute")
        action_method_raw = action_data.get("method") or ""
        
        if action_name and action_class:
            # Build the action URL with namespace
            if namespace and namespace != "/":
                action_url = f"{namespace}/{action_name}"
            else:
                action_url = f"/{action_name}"
            
            # Build the target reference (just class name, method stored in attributes for consistency)
            target_reference = action_class
            
            self.logger.debug("Processing Struts 2.x action: name=%s, class=%s, method=%s, namespace=%s", 
                             action_name, action_class, action_method, namespace or "/")
            
            # Process action results as DeterministicForward objects
            forwards = []
            results = action_data.get("results", [])
            for result_data in results:
                result_name = result_data.get("name", "")
                result_value = result_data.get("value", "")
                
                if result_name and result_value:
                    forwards.append(DeterministicForward(name=result_name, path=result_value))
            
            code_mapping = CodeMapping(
                from_reference=action_url,
                to_reference=target_reference,
                mapping_type="action",
                framework=config_details.detected_framework,
                semantic_category=SemanticCategory.ENTRY_POINT,
                forwards=forwards if forwards else None,
                attributes={
                    "method": action_method,
                    "method_raw": action_method_raw,
                    "namespace": namespace or "/",
                    "package": package_name or "",
                    "results": str(len(results))
                }
            )
            self.logger.debug("Created Struts 2.x action mapping: %s -> %s", action_url, target_reference)
            return code_mapping
        
        return None

    def _process_standalone_globals(
        self, 
        global_actions: Dict[str, Dict[str, Any]], 
        config_details: ConfigurationDetails
    ) -> None:
        """
        Process any standalone global actions (not referenced by packages).
        
        Args:
            global_actions: Registry of global actions by name
            config_details: ConfigurationDetails to populate
        """
        # For now, we'll assume all global actions are handled by packages
        # This method is a placeholder for future enhancement if needed

    def _process_interceptors(
        self, 
        structural_data: Dict[str, Any], 
        config_details: ConfigurationDetails
    ) -> None:
        """
        Process Struts 2.x interceptors.
        
        Args:
            structural_data: Raw Struts configuration data
            config_details: ConfigurationDetails to populate
        """
        interceptors = structural_data.get("interceptors", [])
        interceptor_stacks = structural_data.get("interceptor_stacks", [])
        
        self.logger.debug("Found %d interceptors and %d interceptor stacks", 
                         len(interceptors), len(interceptor_stacks))
        
        # Process individual interceptors
        for interceptor_data in interceptors:
            interceptor_name = interceptor_data.get("name", "")
            interceptor_class = interceptor_data.get("class", "")
            
            if interceptor_name and interceptor_class:
                self.logger.debug("Processing interceptor: name=%s, class=%s", 
                                 interceptor_name, interceptor_class)
                
                # Use CodeMapping for interceptors with interceptor mapping type
                interceptor_mapping = CodeMapping(
                    from_reference=interceptor_name,
                    to_reference=interceptor_class,
                    mapping_type="interceptor",
                    framework=config_details.detected_framework,
                    semantic_category=SemanticCategory.CROSS_CUTTING,
                    attributes={"type": "interceptor"}
                )
                config_details.code_mappings.append(interceptor_mapping)
                self.logger.debug("Created interceptor mapping: %s -> %s", interceptor_name, interceptor_class)
        
        # Process interceptor stacks
        for stack_data in interceptor_stacks:
            stack_name = stack_data.get("name", "")
            interceptor_refs = stack_data.get("interceptor_refs", [])
            
            if stack_name:
                self.logger.debug("Processing interceptor stack: name=%s with %d references", 
                                 stack_name, len(interceptor_refs))
                
                # Create a mapping for the stack with reference list
                ref_names = [ref.get("name", "") for ref in interceptor_refs if ref.get("name")]
                
                # Use CodeMapping for interceptor stacks
                interceptor_mapping = CodeMapping(
                    from_reference=stack_name,
                    to_reference="<stack>",
                    mapping_type="interceptor_stack",
                    framework=config_details.detected_framework,
                    semantic_category=SemanticCategory.CROSS_CUTTING,
                    attributes={
                        "type": "stack",
                        "references": ",".join(ref_names),
                        "ref_count": str(len(ref_names))
                    }
                )
                config_details.code_mappings.append(interceptor_mapping)
                self.logger.debug("Created interceptor stack mapping: %s with refs: %s", 
                                 stack_name, ref_names)
    
    def _process_packages(
        self, 
        structural_data: Dict[str, Any], 
        config_details: ConfigurationDetails,
        global_actions: Dict[str, Dict[str, Any]]
    ) -> None:
        """
        Process Struts 2.x packages and resolve action references.
        
        Args:
            structural_data: Raw Struts configuration data
            config_details: ConfigurationDetails to populate
            global_actions: Registry of global actions by name
        """
        packages = structural_data.get("packages", [])
        self.logger.debug("Found %d Struts 2.x packages", len(packages))
        
        for package_data in packages:
            package_name = package_data.get("name", "")
            extends_package = package_data.get("extends", "")
            namespace = package_data.get("namespace", "/")
            
            if package_name:
                self.logger.debug("Processing package: name=%s, extends=%s, namespace=%s", 
                                 package_name, extends_package, namespace)
                
                # Create CodeMappingGroup for the package
                package_mappings = []
                
                # Process package actions (both references and full definitions)
                package_actions = package_data.get("actions", [])
                for action_data in package_actions:
                    if isinstance(action_data, dict):
                        action_name = action_data.get("name", "")
                        if action_data.get("class"):
                            # Full action definition within package
                            mapping = self._create_action_mapping_for_package(
                                action_data, config_details, namespace, package_name)
                            if mapping:
                                package_mappings.append(mapping)
                        elif action_name in global_actions:
                            # Reference to global action - merge with package context
                            resolved_action = global_actions[action_name].copy()
                            # Override with any package-specific settings
                            resolved_action.update({k: v for k, v in action_data.items() if v})
                            mapping = self._create_action_mapping_for_package(
                                resolved_action, config_details, namespace, package_name)
                            if mapping:
                                package_mappings.append(mapping)
                    elif isinstance(action_data, str):
                        # Simple string reference to global action
                        if action_data in global_actions:
                            mapping = self._create_action_mapping_for_package(
                                global_actions[action_data], config_details, namespace, package_name)
                            if mapping:
                                package_mappings.append(mapping)
                
                # Create the CodeMappingGroup for this package
                if package_mappings or extends_package:
                    code_mapping_group = CodeMappingGroup(
                        group_name=package_name,
                        namespace=namespace,
                        extends=extends_package if extends_package else None,
                        mappings=package_mappings
                    )
                    config_details.code_mappings.append(code_mapping_group)
                    self.logger.debug("Created CodeMappingGroup for package: %s with %d mappings", 
                                     package_name, len(package_mappings))
    
    def _process_constants(
        self, 
        structural_data: Dict[str, Any], 
        config_details: ConfigurationDetails
    ) -> None:
        """
        Process Struts 2.x constants (framework configuration).
        
        Args:
            structural_data: Raw Struts configuration data
            config_details: ConfigurationDetails to populate
        """
        constants = structural_data.get("constants", [])
        self.logger.debug("Found %d Struts 2.x constants", len(constants))
        
        for constant_data in constants:
            constant_name = constant_data.get("name", "")
            constant_value = constant_data.get("value", "")
            
            if constant_name:
                self.logger.debug("Processing constant: name=%s, value=%s", constant_name, constant_value)
                
                # Create a mapping for significant configuration constants
                if self._is_significant_constant(constant_name):
                    constant_mapping = CodeMapping(
                        from_reference=constant_name,
                        to_reference=constant_value,
                        mapping_type="configuration",
                        framework=config_details.detected_framework,
                        semantic_category=None,
                        attributes={
                            "type": "constant",
                            "category": self._categorize_constant(constant_name)
                        }
                    )
                    config_details.code_mappings.append(constant_mapping)
                    self.logger.debug("Created constant mapping: %s -> %s", constant_name, constant_value)
    
    def _is_significant_constant(self, constant_name: str) -> bool:
        """
        Determine if a constant is significant enough to track.
        
        Args:
            constant_name: Name of the constant
            
        Returns:
            True if the constant should be tracked
        """
        significant_patterns = [
            "struts.devMode",
            "struts.custom.",
            "struts.enable.",
            "struts.action.",
            "struts.ui.",
            "struts.multipart.",
            "struts.locale",
            "struts.i18n"
        ]
        
        return any(pattern in constant_name for pattern in significant_patterns)
    
    def _categorize_constant(self, constant_name: str) -> str:
        """
        Categorize a constant by its purpose.
        
        Args:
            constant_name: Name of the constant
            
        Returns:
            Category string
        """
        if "devMode" in constant_name:
            return "development"
        elif "i18n" in constant_name or "locale" in constant_name:
            return "internationalization"
        elif "enable" in constant_name:
            return "feature_toggle"
        elif "action" in constant_name:
            return "action_config"
        elif "ui" in constant_name:
            return "ui_config"
        elif "multipart" in constant_name:
            return "file_upload"
        else:
            return "general"

