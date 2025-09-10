"""
Test fixtures for Step 01 filesystem analysis.
Provides controlled test environments and configuration overrides.
"""

import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
import yaml

from config import Config
from config.loaders import ConfigLoader
from config.sections import AnalysisConfig, ClassificationConfig, ProjectConfig, StepsConfig


@dataclass
class TestProjectStructure:
    """Defines a test project structure for controlled testing."""
    name: str
    files: Dict[str, str] = field(default_factory=dict)  # path -> content
    directories: List[str] = field(default_factory=list)
    expected_languages: List[str] = field(default_factory=list)
    expected_frameworks: List[str] = field(default_factory=list)
    expected_subdomains: List[str] = field(default_factory=list)
    expected_file_count: int = 0


class TestConfigManager:
    """Manages test configuration overrides and isolation."""
    
    def __init__(self):
        self._original_instance = None
        self._original_paths = {}
        self._test_configs: Dict[str, Any] = {}
    
    def create_test_config(self, 
                          project_name: str = "test-project",
                          source_path: Optional[str] = None,
                          config_overrides: Optional[Dict[str, Any]] = None) -> Config:
        """
        Create a test configuration with specified overrides.
        
        Args:
            project_name: Name of the test project
            source_path: Path to test source code
            config_overrides: Dictionary of configuration overrides
            
        Returns:
            Configured Config instance for testing
        """
        # Store original instance and paths for restoration
        if Config._instance is not None:
            self._original_instance = Config._instance
            
        # Store original class-level paths
        self._original_paths = {
            'code_sight_root_path': Config.code_sight_root_path,
            'projects_root_path': Config.projects_root_path,
            'config_root_path': Config.config_root_path,
            'project_name_path': Config.project_name_path,
            'project_output_path': Config.project_output_path
        }
        
        # Reset singleton to create new instance
        Config._instance = None
        Config._initialized = False
        
        # Create new config instance
        config = Config()
        
        # Apply test-specific settings
        config.project.name = project_name
        if source_path:
            config.project.source_path = source_path
        
        # Set class-level path attributes for test environment
        codesight_root = Path(__file__).parent.parent.parent.parent
        projects_root = codesight_root / "test" / "test-projects"
        project_dir = projects_root / project_name
        
        # Ensure test directories exist
        projects_root.mkdir(parents=True, exist_ok=True)
        project_dir.mkdir(parents=True, exist_ok=True)
        
        Config.code_sight_root_path = str(codesight_root)
        Config.projects_root_path = str(projects_root)
        Config.config_root_path = str(codesight_root / "config") 
        Config.project_name_path = str(project_dir)  # Full path to project directory, not just name
        Config.project_output_path = str(project_dir / "output")
        
        # Set basic project configuration without calling initialize()
        config.project.name = project_name
        config.project.output_path = str(project_dir / "output")
        if source_path:
            config.project.source_path = source_path
        else:
            config.project.source_path = str(project_dir / "source")
        
        # Mark as initialized to avoid initialization checks
        Config._initialized = True
        
        # Setup test logging after config is ready (following main.py pattern)
        self._setup_test_logging(project_dir)
        
        # Apply custom overrides
        if config_overrides:
            self._apply_config_overrides(config, config_overrides)
        
        return config
    
    def _setup_test_logging(self, project_dir: Path):
        """Setup logging for tests using the same pattern as main.py."""
        import logging

        # Create a simple logging setup that writes to the project directory
        log_file = project_dir / 'codesight.log'
        
        # Clear any existing handlers to avoid conflicts
        logging.getLogger().handlers.clear()
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_file, mode='w', encoding='utf-8')  # Use 'w' to overwrite for tests
            ],
            force=True  # Force reconfiguration
        )
    
    def _apply_config_overrides(self, config: Config, overrides: Dict[str, Any]):
        """Apply configuration overrides recursively."""
        for key, value in overrides.items():
            if '.' in key:
                # Handle nested keys like 'steps.step01.max_file_size_mb'
                parts = key.split('.')
                obj = config
                for part in parts[:-1]:
                    obj = getattr(obj, part)
                setattr(obj, parts[-1], value)
            else:
                # Handle top-level keys
                if hasattr(config, key):
                    setattr(config, key, value)
    
    def restore_original_config(self):
        """Restore the original configuration instance and class-level paths."""
        if self._original_instance is not None:
            Config._instance = self._original_instance
            Config._initialized = True
            
        # Restore original class-level paths
        for path_name, path_value in self._original_paths.items():
            setattr(Config, path_name, path_value)


class TestProjectFixture:
    """Creates and manages temporary test projects on filesystem."""
    
    def __init__(self):
        self.temp_dirs: List[str] = []
        self.temp_projects: Dict[str, str] = {}  # project_name -> project_path
    
    def create_test_project(self, structure: TestProjectStructure, 
                           use_projects_root: bool = True) -> str:
        """
        Create a temporary test project on the filesystem.
        
        Args:
            structure: TestProjectStructure defining the project
            use_projects_root: If True, create under test-projects directory structure
            
        Returns:
            Path to the created temporary directory
        """
        if use_projects_root:
            # Create under test-projects structure for config compatibility
            base_temp_dir = tempfile.mkdtemp(prefix="codesight_test_base_")
            projects_dir = os.path.join(base_temp_dir, "test-projects")
            os.makedirs(projects_dir, exist_ok=True)
            temp_dir = os.path.join(projects_dir, structure.name)
            os.makedirs(temp_dir, exist_ok=True)
            self.temp_dirs.append(base_temp_dir)  # Clean up the base
        else:
            # Create temporary directory as before
            temp_dir = tempfile.mkdtemp(prefix=f"codesight_test_{structure.name}_")
            self.temp_dirs.append(temp_dir)
        
        self.temp_projects[structure.name] = temp_dir
        
        # Create directory structure
        for directory in structure.directories:
            os.makedirs(os.path.join(temp_dir, directory), exist_ok=True)
        
        # Create files with content
        for file_path, content in structure.files.items():
            full_path = os.path.join(temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return temp_dir
    
    def get_project_path(self, project_name: str) -> Optional[str]:
        """Get the path to a created test project."""
        return self.temp_projects.get(project_name)
    
    def cleanup(self):
        """Clean up all temporary directories."""
        for temp_dir in self.temp_dirs:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        self.temp_dirs.clear()
        self.temp_projects.clear()


# Test project structures
class TestProjectTemplates:
    """Predefined test project structures for common scenarios."""
    
    @staticmethod
    def simple_java_project() -> TestProjectStructure:
        """Simple Java project with basic Spring structure."""
        return TestProjectStructure(
            name="simple_java",
            files={
                "src/main/java/com/example/Application.java": """
package com.example;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}
                """.strip(),
                "src/main/java/com/example/controller/UserController.java": """
package com.example.controller;

import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.GetMapping;

@RestController
public class UserController {
    @GetMapping("/users")
    public String getUsers() {
        return "users";
    }
}
                """.strip(),
                "src/main/java/com/example/service/UserService.java": """
package com.example.service;

import org.springframework.stereotype.Service;

@Service
public class UserService {
    public String findAll() {
        return "all users";
    }
}
                """.strip(),
                "src/main/webapp/WEB-INF/views/users.jsp": """
<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<html>
<head><title>Users</title></head>
<body>
    <h1>User List</h1>
    <form action="/users" method="post">
        <input type="text" name="username" required>
        <input type="submit" value="Add User">
    </form>
</body>
</html>
                """.strip(),
                "pom.xml": """
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>simple-java-project</artifactId>
    <version>1.0.0</version>
    <properties>
        <spring.version>5.3.0</spring.version>
    </properties>
    <dependencies>
        <dependency>
            <groupId>org.springframework</groupId>
            <artifactId>spring-web</artifactId>
            <version>${spring.version}</version>
        </dependency>
    </dependencies>
</project>
                """.strip()
            },
            directories=[
                "src/main/java/com/example/controller",
                "src/main/java/com/example/service", 
                "src/main/webapp/WEB-INF/views"
            ],
            expected_languages=["java", "jsp", "xml"],
            expected_frameworks=["spring"],
            expected_subdomains=["example"],
            expected_file_count=5
        )
    
    @staticmethod
    def enterprise_storm_project() -> TestProjectStructure:
        """Enterprise project mimicking STORM structure with custom patterns."""
        return TestProjectStructure(
            name="enterprise_storm",
            files={
                # ASL layer (Application Service Layer)
                "src/main/java/com/nbcu/storm/asl/UserApplicationService.java": """
package com.nbcu.storm.asl;

import org.springframework.stereotype.Service;

@Service
public class UserApplicationService {
    public void processUserRequest() {
        // Application service logic
    }
}
                """.strip(),
                # DSL layer (Domain Service Layer)
                "src/main/java/com/nbcu/storm/dsl/UserDomainService.java": """
package com.nbcu.storm.dsl;

import org.springframework.stereotype.Service;

@Service
public class UserDomainService {
    public void handleDomainLogic() {
        // Domain service logic
    }
}
                """.strip(),
                # GSL layer (Gateway Service Layer)
                "src/main/java/com/nbcu/storm/gsl/UserGatewayService.java": """
package com.nbcu.storm.gsl;

import org.springframework.stereotype.Component;

@Component
public class UserGatewayService {
    public void handleExternalCalls() {
        // Gateway service logic
    }
}
                """.strip(),
                # ISL layer (Integration Service Layer)
                "src/main/java/com/nbcu/storm/isl/UserIntegrationService.java": """
package com.nbcu.storm.isl;

import org.springframework.stereotype.Component;

@Component
public class UserIntegrationService {
    public void integrateWithExternal() {
        // Integration service logic
    }
}
                """.strip(),
                # Traditional controller
                "src/main/java/com/nbcu/storm/web/UserController.java": """
package com.nbcu.storm.web;

import org.springframework.web.bind.annotation.RestController;

@RestController
public class UserController {
    // Controller logic
}
                """.strip(),
                "build.xml": """
<?xml version="1.0" encoding="UTF-8"?>
<project name="storm-enterprise" default="compile">
    <property name="spring.version" value="4.3.0"/>
    <target name="compile">
        <echo>Compiling STORM enterprise application</echo>
    </target>
</project>
                """.strip()
            },
            directories=[
                "src/main/java/com/nbcu/storm/asl",
                "src/main/java/com/nbcu/storm/dsl", 
                "src/main/java/com/nbcu/storm/gsl",
                "src/main/java/com/nbcu/storm/isl",
                "src/main/java/com/nbcu/storm/web"
            ],
            expected_languages=["java", "xml"],
            expected_frameworks=["spring"],
            expected_subdomains=["storm"],
            expected_file_count=6
        )
    
    @staticmethod
    def mixed_technology_project() -> TestProjectStructure:
        """Project with multiple technologies and file types."""
        return TestProjectStructure(
            name="mixed_tech",
            files={
                "src/main/java/Service.java": "public class Service {}",
                "src/main/webapp/index.jsp": "<%@ page language='java' %>",
                "src/main/webapp/script.js": "console.log('test');",
                "src/main/webapp/style.css": "body { color: black; }",
                "src/main/resources/config.properties": "app.name=test",
                "src/main/resources/application.yml": "server:\n  port: 8080",
                "README.md": "# Test Project",
                "database/schema.sql": "CREATE TABLE users (id INT);",
                "build.gradle": """
plugins {
    id 'java'
    id 'org.springframework.boot' version '2.5.0'
}
                """.strip()
            },
            directories=[
                "src/main/java",
                "src/main/webapp",
                "src/main/resources",
                "database"
            ],
            expected_languages=["java", "jsp", "javascript", "css", "properties", "yaml", "sql"],
            expected_frameworks=["spring"],
            expected_subdomains=["main"],
            expected_file_count=9
        )
    
    @staticmethod
    def empty_project() -> TestProjectStructure:
        """Empty project for edge case testing."""
        return TestProjectStructure(
            name="empty",
            files={},
            directories=[],
            expected_languages=[],
            expected_frameworks=[],
            expected_subdomains=[],
            expected_file_count=0
        )


# Pytest fixtures
@pytest.fixture
def config_manager():
    """Provide a test configuration manager."""
    manager = TestConfigManager()
    yield manager
    manager.restore_original_config()


@pytest.fixture
def project_fixture():
    """Provide a test project fixture manager."""
    fixture = TestProjectFixture()
    yield fixture
    fixture.cleanup()


@pytest.fixture
def configured_test_project(config_manager, project_fixture):
    """
    Create a test project with proper Config class-level path integration.
    
    Returns:
        Tuple of (config, project_path, structure)
    """
    def _create_configured_project(structure: TestProjectStructure, 
                                  config_overrides: Optional[Dict[str, Any]] = None):
        # Create the test project with projects_root structure
        project_path = project_fixture.create_test_project(structure, use_projects_root=True)
        
        # Create config with proper paths
        config = config_manager.create_test_config(
            project_name=structure.name,
            source_path=project_path,
            config_overrides=config_overrides
        )
        
        return config, project_path, structure
    
    return _create_configured_project


@pytest.fixture
def simple_java_project(project_fixture):
    """Create a simple Java project for testing."""
    structure = TestProjectTemplates.simple_java_project()
    project_path = project_fixture.create_test_project(structure)
    return project_path, structure


@pytest.fixture
def enterprise_storm_project(project_fixture):
    """Create an enterprise STORM project for testing."""
    structure = TestProjectTemplates.enterprise_storm_project()
    project_path = project_fixture.create_test_project(structure)
    return project_path, structure


@pytest.fixture
def mixed_technology_project(project_fixture):
    """Create a mixed technology project for testing."""
    structure = TestProjectTemplates.mixed_technology_project()
    project_path = project_fixture.create_test_project(structure)
    return project_path, structure


@pytest.fixture
def empty_project(project_fixture):
    """Create an empty project for edge case testing."""
    structure = TestProjectTemplates.empty_project()
    project_path = project_fixture.create_test_project(structure)
    return project_path, structure
