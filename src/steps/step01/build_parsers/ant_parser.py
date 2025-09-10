"""Ant build file parser for extracting dependencies and metadata."""

import glob
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Set

from utils.logging.logger_factory import LoggerFactory


class AntBuildParser:
    """Parser for Ant build.xml files to extract dependencies and metadata."""
    
    def __init__(self):
        self.logger = LoggerFactory.get_logger("steps")
    
    def parse_build_file(self, build_file_path: str, project_path: str) -> Dict[str, Any]:
        """Parse Ant build.xml and extract configuration metadata."""
        try:
            self.logger.info("Parsing Ant build file: %s", build_file_path)
            tree = ET.parse(build_file_path)
            root = tree.getroot()
            
            # Convert absolute path to relative POSIX path
            relative_build_path = self._get_relative_posix_path(build_file_path, project_path)
            
            # Extract framework JARs by scanning actual JAR directories
            framework_jars = self._discover_framework_jars_from_directories(root, project_path, build_file_path)
            
            result = {
                "build_system": "ant",
                "build_file_path": relative_build_path,
                "project_name": root.get("name", "unknown"),
                "framework_jars": framework_jars,
                "total_dependencies": len(framework_jars),
                "dependency_directories": self._extract_dependency_directories(root, project_path, build_file_path),
                "java_version": self._extract_java_version(root),
                "classpath_entries": self._extract_classpath_entries(root)
            }
            
            self.logger.info("Ant build analysis complete. Found %d framework JARs, %d dependency directories", 
                           len(framework_jars), len(result["dependency_directories"]))
            return result
            
        except (ET.ParseError, OSError, IOError) as e:
            self.logger.error("Failed to parse Ant build file %s: %s", build_file_path, e)
            return {"error": f"Failed to parse Ant build file: {str(e)}"}
    
    def _discover_framework_jars_from_directories(self, root: ET.Element, project_path: str, build_file_path: str) -> List[str]:
        """Discover actual framework JAR files by scanning dependency directories."""
        framework_jars = []
        framework_indicators = [
            "spring", "hibernate", "struts", "aspectj", "jpa", 
            "jersey", "jackson", "log4j", "slf4j", "commons",
            "javax", "servlet", "jsp", "jstl", "tiles", "faces"
        ]
        
        # Get dependency directories from build file
        dependency_dirs = self._extract_dependency_directories(root, project_path, build_file_path)
        
        # Scan each dependency directory for actual JAR files
        for dep_dir in dependency_dirs:
            try:
                # Convert relative paths to absolute paths
                if not os.path.isabs(dep_dir):
                    # Try relative to build file directory first
                    build_dir = os.path.dirname(build_file_path)
                    abs_dep_dir = os.path.join(build_dir, dep_dir)
                    if not os.path.exists(abs_dep_dir):
                        # Try relative to project root
                        abs_dep_dir = os.path.join(project_path, dep_dir)
                else:
                    abs_dep_dir = dep_dir
                
                if os.path.exists(abs_dep_dir):
                    self.logger.debug("Scanning dependency directory: %s", abs_dep_dir)
                    
                    # Find all JAR files in the directory
                    jar_files = glob.glob(os.path.join(abs_dep_dir, "*.jar"))
                    
                    for jar_file in jar_files:
                        jar_name = os.path.basename(jar_file).lower()
                        
                        # Check if this JAR indicates a framework
                        for indicator in framework_indicators:
                            if indicator in jar_name:
                                framework_jars.append(os.path.basename(jar_file))
                                self.logger.debug("Found framework JAR: %s (indicator: %s)", os.path.basename(jar_file), indicator)
                                break
                else:
                    self.logger.warning("Dependency directory not found: %s", abs_dep_dir)
                    
            except (OSError, IOError) as e:
                self.logger.warning("Failed to scan dependency directory %s: %s", dep_dir, e)
        
        return sorted(list(set(framework_jars)))  # Remove duplicates and sort
    
    def _extract_dependency_directories(self, root: ET.Element, project_path: str, build_file_path: str) -> List[str]:
        """Extract dependency directory paths from classpath."""
        dirs = set()
        
        # Look for <fileset> elements with dir attributes
        for fileset in root.findall(".//fileset"):
            dir_attr = fileset.get("dir", "")
            if dir_attr:
                # Common dependency directory patterns
                dir_lower = dir_attr.lower()
                if any(pattern in dir_lower for pattern in ["lib", "jar", "dependency", "dependencies"]):
                    dirs.add(dir_attr)
                    self.logger.debug("Found dependency directory in fileset: %s", dir_attr)
        
        # Look for <path> elements with pathelement references
        for path_elem in root.findall(".//path"):
            for pathelement in path_elem.findall("pathelement"):
                location = pathelement.get("location", "")
                if location and ".jar" in location:
                    # Extract directory from JAR path
                    jar_dir = os.path.dirname(location)
                    if jar_dir:
                        dirs.add(jar_dir)
                        self.logger.debug("Found dependency directory from pathelement: %s", jar_dir)
        
        # Look for property definitions that might point to dependency directories
        for prop in root.findall(".//property"):
            name = prop.get("name", "").lower()
            value = prop.get("value", "")
            if value and any(pattern in name for pattern in ["lib", "jar", "dependency"]):
                if os.path.isdir(os.path.join(os.path.dirname(build_file_path), value)):
                    dirs.add(value)
                    self.logger.debug("Found dependency directory from property: %s", value)
        
        # Add some common default directories if they exist
        build_dir = os.path.dirname(build_file_path)
        common_dirs = ["lib", "libs", "dependencies", "jars", "WEB-INF/lib"]
        
        for common_dir in common_dirs:
            full_path = os.path.join(build_dir, common_dir)
            if os.path.exists(full_path):
                dirs.add(common_dir)
                self.logger.debug("Found common dependency directory: %s", common_dir)
        
        return sorted(list(dirs))
    
    def _extract_java_version(self, root: ET.Element) -> str:
        """Extract Java version from build properties."""
        # Look for common Java version properties
        for prop in root.findall(".//property"):
            name = prop.get("name", "").lower()
            value = prop.get("value", "")
            
            if value and any(pattern in name for pattern in ["java.version", "javac.target", "target.version", "source.version"]):
                self.logger.debug("Found Java version from property %s: %s", name, value)
                return value
        
        # Look for javac tasks with target attributes
        for javac in root.findall(".//javac"):
            target = javac.get("target", "")
            source = javac.get("source", "")
            
            if target:
                self.logger.debug("Found Java version from javac target: %s", target)
                return target
            elif source:
                self.logger.debug("Found Java version from javac source: %s", source)
                return source
        
        return "unknown"
    
    def _extract_classpath_entries(self, root: ET.Element) -> List[str]:
        """Extract classpath entries for framework detection."""
        entries = []
        
        # Look for <path> elements with classpath IDs
        for path_elem in root.findall(".//path"):
            path_id = path_elem.get("id", "")
            if "classpath" in path_id.lower():
                self.logger.debug("Found classpath path element: %s", path_id)
                
                # Extract fileset directories
                for fileset in path_elem.findall("fileset"):
                    dir_attr = fileset.get("dir", "")
                    if dir_attr:
                        entries.append(dir_attr)
                        self.logger.debug("Added classpath entry from fileset: %s", dir_attr)
                
                # Extract pathelement locations
                for pathelement in path_elem.findall("pathelement"):
                    location = pathelement.get("location", "")
                    if location:
                        entries.append(location)
                        self.logger.debug("Added classpath entry from pathelement: %s", location)
        
        return entries

    def _get_relative_posix_path(self, file_path: str, project_path: str) -> str:
        """Convert absolute file path to relative POSIX path from project directory."""
        try:
            # Convert both paths to Path objects for cross-platform handling
            file_path_obj = Path(file_path)
            project_path_obj = Path(project_path)
            
            # Get relative path and convert to POSIX format
            relative_path = file_path_obj.relative_to(project_path_obj)
            return relative_path.as_posix()
            
        except ValueError:
            # If relative_to fails, file is outside project directory
            # Return just the filename as fallback
            return Path(file_path).name
