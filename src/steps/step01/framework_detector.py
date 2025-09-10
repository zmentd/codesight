"""Framework detection through build files and file patterns (no content parsing)."""

import glob
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from config import Config
from domain.source_inventory import SourceInventory
from utils.logging.logger_factory import LoggerFactory


class FrameworkDetector:
    """Framework detection through build files and file patterns (no content parsing)."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = LoggerFactory.get_logger("steps")
    
    def detect_frameworks(self, source_inventory: SourceInventory, project_path: str, build_configuration: Optional[Dict[str, Any]] = None) -> List[str]:
        """Main detection method - build files and file patterns only."""
        frameworks = set()
        
        # 1. Detect from build file JAR analysis (highest priority)
        if build_configuration and 'framework_jars' in build_configuration:
            frameworks.update(self._detect_from_build_jars(build_configuration['framework_jars']))
        
        # 2. Detect from XML files already in source_inventory (build files, config files)
        frameworks.update(self._detect_from_xml_files(source_inventory))
        
        # 3. Detect framework config files by name/extension patterns
        frameworks.update(self._detect_from_config_file_patterns(source_inventory))
        
        # 4. Discover JAR files from project directory for framework hints
        frameworks.update(self._detect_from_jar_files(project_path))
        
        # 5. File structure analysis (project conventions)
        frameworks.update(self._detect_from_project_structure(source_inventory))
        
        detected = sorted(list(frameworks))
        self.logger.info("Detected frameworks: %s", detected)
        return detected
    
    def _detect_from_xml_files(self, source_inventory: SourceInventory) -> Set[str]:
        """Detect frameworks from XML files already discovered in source_inventory."""
        frameworks = set()
        
        # Get framework patterns from existing configuration
        framework_configs = getattr(self.config, 'frameworks', None)
        if not framework_configs:
            self.logger.warning("No framework configuration found")
            return frameworks
        
        # Check XML files in source inventory for framework config patterns
        for source_location in source_inventory.source_locations:
            for subdomain in source_location.subdomains:
                for file_item in subdomain.file_inventory:
                    if file_item.language == 'xml':
                        filename = os.path.basename(file_item.path).lower()
                        
                        # Check against framework config file patterns
                        for framework_name in ['spring_boot', 'struts', 'jee']:
                            framework_config = getattr(framework_configs, framework_name, None)
                            if framework_config and hasattr(framework_config, 'config_files'):
                                for config_pattern in framework_config.config_files:
                                    if config_pattern.lower() in filename:
                                        frameworks.add(framework_name.replace('_', '-'))
                                        self.logger.debug("Found %s from config file: %s", framework_name, file_item.path)
        
        return frameworks
    
    def _detect_from_build_jars(self, framework_jars: List[str]) -> Set[str]:
        """Detect frameworks from JAR file names discovered by build file analysis."""
        frameworks = set()
        
        # Map JAR name patterns to framework names
        jar_framework_mapping = {
            'spring': ['spring-core', 'spring-context', 'spring-web', 'spring-mvc', 'spring-beans', 'springframework'],
            'struts': ['struts-core', 'struts-faces', 'struts2-core', 'struts-tiles'],
            'hibernate': ['hibernate-core', 'hibernate-validator', 'hibernate-entitymanager', 'hibernate'],
            'aspectj': ['aspectjweaver', 'aspectjrt', 'aspectj'],
            'jpa': ['persistence-api', 'jpa-api', 'javax.persistence', 'eclipselink', 'openjpa'],
            'jee': ['servlet-api', 'jsp-api', 'jstl', 'el-api', 'javax.servlet', 'javaee'],
            'log4j': ['log4j', 'log4j-core', 'log4j-api'],
            'tiles': ['tiles-core', 'tiles-api', 'tiles-servlet'],
            'commons': ['commons-lang', 'commons-collections', 'commons-io', 'commons-logging']
        }
        
        for jar_name in framework_jars:
            jar_lower = jar_name.lower()
            self.logger.debug("Analyzing JAR for framework hints: %s", jar_name)
            
            for framework, indicators in jar_framework_mapping.items():
                if any(indicator in jar_lower for indicator in indicators):
                    frameworks.add(framework)
                    self.logger.debug("Detected %s framework from JAR: %s", framework, jar_name)
                    break  # Only match the first framework to avoid duplicates
        
        return frameworks
    
    def _detect_from_config_file_patterns(self, source_inventory: SourceInventory) -> Set[str]:
        """Detect frameworks by presence of config files (name patterns only)."""
        frameworks = set()
        
        # Define additional config file patterns not covered by framework configs
        config_patterns = {
            'hibernate': ['hibernate.cfg.xml', 'hibernate.properties'],
            'log4j': ['log4j.xml', 'log4j.properties', 'log4j2.xml'],
            'aspectj': ['aop.xml', 'META-INF/aop.xml']
        }
        
        for source_location in source_inventory.source_locations:
            for subdomain in source_location.subdomains:
                for file_item in subdomain.file_inventory:
                    filename = os.path.basename(file_item.path).lower()
                    
                    # Check against additional config file patterns
                    for framework, patterns in config_patterns.items():
                        for pattern in patterns:
                            if pattern.lower() in filename:
                                frameworks.add(framework)
                                self.logger.debug("Found %s framework from config file: %s", framework, file_item.path)
        
        return frameworks
    
    def _detect_from_jar_files(self, project_path: str) -> Set[str]:
        """Discover JAR files from project directory and detect frameworks."""
        frameworks = set()
        
        try:
            # Use glob to find JAR files in common locations
            jar_patterns = [
                os.path.join(project_path, "**", "*.jar"),
                os.path.join(project_path, "lib", "*.jar"),
                os.path.join(project_path, "Deployment", "lib", "*.jar"),
                os.path.join(project_path, "*Ear", "**", "lib", "*.jar")
            ]
            
            discovered_jars = []
            for pattern in jar_patterns:
                discovered_jars.extend(glob.glob(pattern, recursive=True))
            
            if discovered_jars:
                self.logger.debug("Found %d JAR files for framework detection", len(discovered_jars))
                
                # Analyze JAR patterns for framework indicators
                jar_framework_mapping = {
                    'spring': ['spring-core', 'spring-context', 'spring-web', 'spring-mvc', 'spring.jar'],
                    'struts': ['struts-core', 'struts-faces', 'struts2-core', 'struts.jar'],
                    'hibernate': ['hibernate-core', 'hibernate-validator', 'hibernate-entitymanager'],
                    'aspectj': ['aspectjweaver', 'aspectjrt'],
                    'jpa': ['persistence-api', 'jpa-api', 'javax.persistence'],
                    'jee': ['servlet-api', 'jsp-api', 'jstl', 'el-api', 'javax.servlet']
                }
                
                for jar_path in discovered_jars:
                    jar_name = os.path.basename(jar_path).lower()
                    for framework, indicators in jar_framework_mapping.items():
                        if any(indicator in jar_name for indicator in indicators):
                            frameworks.add(framework)
                            self.logger.debug("Found %s framework from JAR: %s", framework, jar_name)
                            break
        
        except (OSError, IOError) as e:
            self.logger.warning("Failed to discover JAR files: %s", e)
        
        return frameworks
    
    def _detect_from_project_structure(self, source_inventory: SourceInventory) -> Set[str]:
        """Detect frameworks from project directory structure patterns."""
        frameworks = set()
        
        # Check for web application structure
        has_web_structure = any(
            'web-inf' in location.relative_path.lower() or 
            'webapp' in location.relative_path.lower() or
            'webcontent' in location.relative_path.lower()
            for location in source_inventory.source_locations
        )
        
        if has_web_structure:
            frameworks.add('jee')
            self.logger.debug("Found JEE framework from web application structure")
        
        # Check for framework-specific directory patterns
        directory_patterns = {
            'spring': ['spring', 'springframework'],
            'hibernate': ['hibernate'],
            'struts': ['struts', 'struts2']
        }
        
        for framework, dir_patterns in directory_patterns.items():
            for location in source_inventory.source_locations:
                for pattern in dir_patterns:
                    if pattern.lower() in location.relative_path.lower():
                        frameworks.add(framework)
                        self.logger.debug("Found %s framework from directory structure: %s", framework, location.relative_path)
        
        return frameworks
