# Step 01 Test Suite

This directory contains comprehensive tests for Step 01 of the CodeSight pipeline, which handles filesystem analysis and source code discovery.

## Test Structure

### Test Files
- `test_filesystem_analyzer.py` - Tests for the FilesystemAnalyzer orchestrator component
- `test_directory_scanner.py` - Tests for DirectoryScanner core scanning functionality  
- `test_file_classifier.py` - Tests for FileClassifier file type detection
- `test_source_locator.py` - Tests for SourceLocator source discovery

### Test Fixtures
- `conftest.py` - Shared test fixtures including:
  - `TestConfigManager` - Configuration override management
  - `TestProjectFixture` - Test project creation and management
  - `TestProjectTemplates` - Predefined project structures

## Running Tests

### Using the Test Runner

The test runner script provides several configurations:

```bash
# Run all tests
python run_tests.py all

# Run only unit tests
python run_tests.py unit

# Run only integration tests  
python run_tests.py integration

# Run with coverage reporting
python run_tests.py coverage
```

### Using pytest directly

```bash
# Run all Step 01 tests
pytest test/steps/step01/ -v

# Run specific test file
pytest test/steps/step01/test_filesystem_analyzer.py -v

# Run with markers
pytest test/steps/step01/ -m unit -v
pytest test/steps/step01/ -m integration -v

# Run with coverage
pytest test/steps/step01/ --cov=steps.step01 --cov-report=html
```

## Test Categories

### Unit Tests
- Test individual component functionality in isolation
- Use mocked dependencies where appropriate
- Fast execution, focused on specific methods

### Integration Tests  
- Test component interactions and workflows
- Use real filesystem operations with temporary directories
- Validate end-to-end functionality

## Test Configuration

### Configuration Overrides
Tests use `TestConfigManager` to override configuration settings:

```python
def test_with_custom_config(test_config_manager):
    # Override specific configuration values
    config_overrides = {
        'analysis': {
            'max_file_size': 1000000,
            'excluded_patterns': ['*.tmp', '*.log']
        }
    }
    
    with test_config_manager.override_config(config_overrides):
        # Test code here uses the overridden configuration
        pass
```

### Test Projects
Tests use `TestProjectFixture` to create controlled test environments:

```python
def test_with_test_project(test_project_fixture):
    # Create a test project with specific structure
    project_structure = {
        'src/main/java': ['App.java', 'Utils.java'],
        'src/test/java': ['AppTest.java'],
        'pom.xml': '<maven project file content>'
    }
    
    with test_project_fixture.create_project(project_structure) as project_path:
        # Test code here operates on the test project
        pass
```

## Test Data and Fixtures

### Predefined Templates
`TestProjectTemplates` provides common project structures:

- `simple_java_project()` - Basic Java project structure
- `maven_project()` - Maven-based Java project
- `gradle_project()` - Gradle-based Java project
- `mixed_technology_project()` - Multi-language project

### Dynamic Test Data
Tests can create custom project structures as needed:

```python
def test_custom_structure(test_project_fixture):
    structure = {
        'custom/path': ['file1.java', 'file2.properties'],
        'another/path': ['config.xml']
    }
    
    with test_project_fixture.create_project(structure) as project_path:
        # Test with custom structure
        pass
```

## Key Testing Patterns

### Configuration Testing
- Test with different configuration combinations
- Validate configuration override mechanisms
- Test configuration validation and error handling

### Filesystem Testing
- Use temporary directories for filesystem operations
- Test with various file types and structures
- Validate path handling across platforms

### Error Handling Testing
- Test invalid inputs and edge cases
- Validate error messages and exception types
- Test recovery mechanisms

### Integration Testing
- Test component interactions
- Validate data flow between components
- Test complete workflows end-to-end

## Coverage Expectations

The test suite aims for comprehensive coverage of:
- All public methods and functions
- Error handling paths
- Configuration variations
- Different file types and project structures
- Platform-specific behavior

Target coverage: 90%+ for all Step 01 components.

## Debugging Tests

### Running Individual Tests
```bash
# Run single test method
pytest test/steps/step01/test_filesystem_analyzer.py::TestFilesystemAnalyzerBasic::test_initialization -v -s

# Run with detailed output
pytest test/steps/step01/ -v -s --tb=long
```

### Using Test Fixtures for Debugging
Test fixtures provide utilities for debugging:

```python
def test_debug_example(test_project_fixture, capsys):
    with test_project_fixture.create_project({'src': ['test.java']}) as project_path:
        # Add debug output
        print(f"Test project created at: {project_path}")
        
        # Test code here
        
        # Capture output for analysis
        captured = capsys.readouterr()
        print(f"Captured output: {captured.out}")
```

## Test Dependencies

Required packages for testing:
- `pytest` - Test framework
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Mocking utilities
- `pytest-asyncio` - Async test support (if needed)

Install test dependencies:
```bash
pip install pytest pytest-cov pytest-mock
```

## Adding New Tests

When adding new tests:

1. Follow the existing naming conventions
2. Use appropriate test markers (`@pytest.mark.unit`, `@pytest.mark.integration`)
3. Leverage existing fixtures where possible
4. Add docstrings explaining test purpose
5. Include both positive and negative test cases
6. Update this documentation if adding new test patterns
