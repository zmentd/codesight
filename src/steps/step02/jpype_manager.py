"""
JPype manager for Java parser integration.

Manages JVM lifecycle and JavaParser JAR integration for AST extraction
with proper resource management and error handling.
"""

import glob
import os
import threading
import time
from typing import Any, Dict, List, Optional

from config import Config
from utils.logging.logger_factory import LoggerFactory


class JPypeManager:
    """
    Singleton JPype/JVM manager for Java AST parsing.
    
    Handles JVM startup/shutdown, JavaParser JAR loading,
    and provides Java AST parsing capabilities. Only one JVM 
    can exist per process, so this uses singleton pattern.
    """
    
    _instance: Optional['JPypeManager'] = None
    _initialized: bool = False
    _initialization_lock = threading.Lock()
    _jvm_started_globally: bool = False
    _jpype_module_global: Optional[Any] = None
    _java_parser_global: Optional[Any] = None
    
    def __new__(cls, config: Optional[Config] = None) -> 'JPypeManager':
        """Create or return singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Optional[Config] = None) -> None:
        """
        Initialize JPype manager (singleton).
        
        Args:
            config: Configuration instance (only used on first initialization)
        """
        # Only initialize once
        if self._initialized:
            return
            
        if config is None:
            raise ValueError("Config required for first initialization of JPypeManager")
            
        self.config = config
        self.logger = LoggerFactory.get_logger("steps")
        
        # Instance state (just for this instance)
        self._local_initialized = False
        self._files_processed = 0
        
        # Configuration with optimized JVM options for large-scale parsing
        self.jpype_config = getattr(config, 'jpype', {})
        self.lib_dir = self.jpype_config.get('lib_dir', 'lib')
        # Optimized JVM args for parsing large codebases
        default_jvm_args = [
            '-Xmx512m',  # Increased heap size for large file processing
            '-Xms128m',  # Initial heap size to reduce allocation overhead
            '-XX:NewRatio=2',  # Optimize young generation size for short-lived objects
            '-XX:+UseG1GC',  # Use G1 garbage collector for better pause times
            '-XX:MaxGCPauseMillis=100',  # Target max GC pause time
            '-Djava.awt.headless=true',  # Headless mode
            '-XX:+DisableExplicitGC',  # Disable explicit System.gc() calls
            '-XX:+UseStringDeduplication',  # Deduplicate strings to save memory
            '-XX:+PrintGC',  # Print GC events for monitoring
            '-XX:+PrintGCTimeStamps',  # Include timestamps in GC logs
            '-XX:+PrintGCDetails',  # Detailed GC information
            '-Xloggc:gc.log'  # Write GC logs to file
        ]
        self.jvm_args = self.jpype_config.get('jvm_args', default_jvm_args)
        self.timeout = self.jpype_config.get('timeout', 30)
        
        JPypeManager._initialized = True
    
    @staticmethod
    def initialize() -> None:
        """Initialize JPype manager (singleton) - thread-safe."""
        # Fast path - if already initialized, return immediately
        if JPypeManager._initialized:
            return
        
        # Slow path - acquire lock and double-check
        with JPypeManager._initialization_lock:
            # Double-check pattern: another thread might have initialized
            # while we were waiting for the lock
            if JPypeManager._initialized:
                return  # type: ignore  # Static analyzer false positive - this is reachable in concurrent scenarios
            
            config = Config.get_instance()
            JPypeManager._instance = JPypeManager(config)
            JPypeManager._instance._start_jvm()

    @classmethod
    def get_instance(cls) -> 'JPypeManager':
        """
        Get singleton instance.
        
        Args:
            config: Configuration (only required for first call)
            
        Returns:
            JPype manager singleton instance
        """
        if cls._instance is None:
            raise RuntimeError("JPypeManager not initialized. Call initialize() first.")
        return cls._instance
    
    @classmethod
    def reset_singleton(cls) -> None:
        """Reset singleton instance (for testing)."""
        if cls._instance is not None:
            try:
                cls._instance.shutdown_jvm()
            except (RuntimeError, AttributeError, ImportError):
                pass  # Ignore shutdown errors during reset
        cls._instance = None
        cls._initialized = False
        cls._jvm_started_globally = False
        cls._jpype_module_global = None
        cls._java_parser_global = None
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.shutdown_jvm()
        self.logger.info("JPypeManager context exited, JVM shutdown if started")
    
    def _start_jvm(self) -> bool:
        """
        Start JVM and initialize JavaParser (singleton operation).
        
        Returns:
            True if JVM started successfully
        """
        # Check global JVM state first
        if JPypeManager._jvm_started_globally:
            return True
        
        try:
            # Import JPype
            import jpype  # type: ignore
            JPypeManager._jpype_module_global = jpype
            
            # Double-check if JVM is already started (from outside our control)
            if jpype.isJVMStarted():
                self.logger.info("JVM already started externally, reusing existing instance")
                JPypeManager._jvm_started_globally = True
                self._initialize_java_parser()
                return True
            
            # Validate JAR files
            jar_files = self._find_jar_files()
            if not jar_files:
                self.logger.error("No JavaParser JAR files found in lib directory")
                return False
            
            # Build classpath with Windows-compatible separator
            classpath_sep = ";" if os.name == "nt" else ":"
            classpath = classpath_sep.join(jar_files)
            
            # Final check before attempting to start JVM
            if jpype.isJVMStarted():
                self.logger.info("JVM started between checks, using existing instance")
                JPypeManager._jvm_started_globally = True
                self._initialize_java_parser()
                return True
            
            # Start JVM with simple approach (following JPype quickguide)
            self.logger.info("Starting JVM with classpath: %s", classpath)
            try:
                jpype.startJVM(classpath=classpath)
                JPypeManager._jvm_started_globally = True
                self.logger.info("JVM started successfully")
            except RuntimeError as e:
                error_msg = str(e).lower()
                if "jvm already started" in error_msg or "already running" in error_msg or "cannot re-initialize" in error_msg:
                    self.logger.warning("JVM start failed but JVM might already be running: %s", str(e))
                    if jpype.isJVMStarted():
                        self.logger.info("JVM is indeed already started, continuing")
                        JPypeManager._jvm_started_globally = True
                        self._initialize_java_parser()
                        return True
                    else:
                        self.logger.error("JVM start failed and JVM is not running")
                        return False
                else:
                    self.logger.error("JVM startup failed with unexpected error: %s", str(e))
                    raise
            
            # Initialize JavaParser
            self._initialize_java_parser()
            
            return True
            
        except ImportError:
            self.logger.error("JPype not available - install with: pip install jpype1")
            return False
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Failed to start JVM: %s", str(e))
            return False
    
    def shutdown_jvm(self) -> None:
        """Shutdown JVM if it was started by this manager."""
        if not JPypeManager._jvm_started_globally or not JPypeManager._jpype_module_global:
            return
        self.logger.info("Shutting down JVM")
        self._shutdown_jvm_check()
        self.logger.info("JVM shutdown complete")
     
    def _shutdown_jvm_check(self) -> None:
        """Shutdown JVM if it was started by this manager."""
        # JVM is started and jpype module is available
        # NOTE: Static analysis false positive - this code IS reachable when _jvm_started_globally=True
        # and _jpype_module_global is not None (early returns don't trigger in that case)
        try:
            if JPypeManager._jpype_module_global and JPypeManager._jpype_module_global.isJVMStarted():
                self.logger.info("Shutting down JVM")
                JPypeManager._jpype_module_global.shutdownJVM()
        except (AttributeError, RuntimeError) as e:  # pylint: disable=broad-except
            self.logger.warning("Error during JVM shutdown: %s", str(e))
        finally:
            JPypeManager._jvm_started_globally = False
            JPypeManager._java_parser_global = None
   
    def parse_java_file(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Parse Java source code using JavaParser.
        
        Args:
            content: Java source code content
            
        Returns:
            Parsed AST structure or None if parsing failed
        """
        if not JPypeManager._jvm_started_globally or not JPypeManager._java_parser_global:
            raise RuntimeError("JVM not started or JavaParser not initialized")
        
        try:
            start_time = time.time()
            
            # Ensure JavaParser is available
            if JPypeManager._java_parser_global is None:
                self.logger.error("JavaParser not initialized")
                return None
            
            # Optional: Log memory usage for very large files
            content_size = len(content)
            if content_size > 100000:  # Log for files larger than 100KB
                self.logger.debug("Parsing large Java file: %d bytes", content_size)
            
            # Check JVM memory usage before parsing if we have many files processed
            if hasattr(self, '_files_processed'):
                self._files_processed += 1
                if self._files_processed % 50 == 0:  # Every 50 files, check memory
                    try:
                        if JPypeManager._jpype_module_global is not None:
                            Runtime = JPypeManager._jpype_module_global.JClass("java.lang.Runtime")
                            runtime = Runtime.getRuntime()
                            total_memory = runtime.totalMemory()
                            free_memory = runtime.freeMemory()
                            used_memory = total_memory - free_memory
                            max_memory = runtime.maxMemory()
                            
                            self.logger.debug("JVM Memory after %d files: Used=%dMB, Free=%dMB, Total=%dMB, Max=%dMB", 
                                            self._files_processed,
                                            used_memory // (1024*1024),
                                            free_memory // (1024*1024), 
                                            total_memory // (1024*1024),
                                            max_memory // (1024*1024))
                            
                            # Suggest GC if memory usage is high
                            memory_usage_percent = (used_memory / max_memory) * 100
                            if memory_usage_percent > 80:
                                self.logger.warning("High JVM memory usage: %.1f%% - consider garbage collection", memory_usage_percent)
                                runtime.gc()  # Suggest garbage collection
                                
                    except (AttributeError, RuntimeError) as e:
                        self.logger.debug("Could not check JVM memory: %s", str(e))
            else:
                self._files_processed = 1
            
            # Parse the Java content - JavaParser.parse() returns CompilationUnit directly
            compilation_unit = JPypeManager._java_parser_global.parse(content)
            
            # If we get here, parsing succeeded (exceptions are thrown on failure)
            ast_data = self._extract_ast_data(compilation_unit)
            
            processing_time = time.time() - start_time
            ast_data['processing_time'] = processing_time
            
            return ast_data
                
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Error parsing Java content: %s", str(e))
            return None
    
    def _find_jar_files(self) -> List[str]:
        """
        Find JavaParser JAR files in the lib directory.
        
        Returns:
            List of full paths to JavaParser JAR files
        """
        jar_files: List[str] = []
        
        # Get project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        lib_path = os.path.join(project_root, self.lib_dir)
        
        if not os.path.exists(lib_path):
            self.logger.warning("Lib directory not found: %s", lib_path)
            return jar_files
        
        # Search for javaparser JAR files
        patterns = [
            'javaparser-core-*.jar',
            'javaparser-symbol-solver-*.jar'
        ]
        
        for pattern in patterns:
            search_path = os.path.join(lib_path, pattern)
            found_files = glob.glob(search_path)
            
            if found_files:
                # Sort by version (latest first) and take the first match
                found_files.sort(reverse=True)
                jar_files.append(found_files[0])  # Only take the latest version
                self.logger.info("Found JavaParser JAR: %s", found_files[0])
        
        if not jar_files:
            self.logger.error("No JavaParser JAR files found in: %s", lib_path)
            
        return jar_files
    
    def _get_lib_directory(self) -> str:
        """
        Get full path to lib directory.
        
        Returns:
            Full path to lib directory
        """
        if os.path.isabs(self.lib_dir):
            return str(self.lib_dir)
        
        # Try relative to project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        lib_path = os.path.join(project_root, self.lib_dir)
        
        if os.path.exists(lib_path):
            return str(lib_path)
        
        # Try relative to current working directory
        return str(os.path.abspath(self.lib_dir))
    
    def _initialize_java_parser(self) -> None:
        """Initialize JavaParser classes."""
        if not JPypeManager._jpype_module_global:
            return
        
        self._initialize_java_parser_checked()

    def _initialize_java_parser_checked(self) -> None:
        """Initialize JavaParser classes."""

        try:
            # Import JavaParser classes
            if JPypeManager._jpype_module_global:
                StaticJavaParser = JPypeManager._jpype_module_global.JClass('com.github.javaparser.StaticJavaParser')
                JPypeManager._java_parser_global = StaticJavaParser
                
                self.logger.info("JavaParser initialized successfully")
            
        except (AttributeError, RuntimeError) as e:  # pylint: disable=broad-except
            self.logger.error("Failed to initialize JavaParser: %s", str(e))
            JPypeManager._java_parser_global = None 
   
    def _extract_ast_data(self, compilation_unit: Any) -> Dict[str, Any]:
        """
        Extract AST data from JavaParser CompilationUnit.
        
        Args:
            compilation_unit: JavaParser CompilationUnit object
            
        Returns:
            Dictionary with AST structural data
        """
        ast_data: Dict[str, Any] = {
            "package": None,
            "imports": [],
            "classes": [],
            "interfaces": [],
            "enums": [],
            "annotations": []
        }
        
        try:
            # Extract package declaration
            package_declaration = compilation_unit.getPackageDeclaration()
            if package_declaration.isPresent():
                package_name = str(package_declaration.get().getName())
                ast_data["package"] = package_name
            
            # Extract imports
            imports = compilation_unit.getImports()
            for import_decl in imports:
                import_name = str(import_decl.getName())
                is_static = import_decl.isStatic()
                is_asterisk = import_decl.isAsterisk()
                
                ast_data["imports"].append({
                    "name": import_name,
                    "static": is_static,
                    "asterisk": is_asterisk
                })
            
            # Extract type declarations (classes, interfaces, enums)
            types = compilation_unit.getTypes()
            for type_decl in types:
                type_data = self._extract_type_data(type_decl)
                
                if type_data["type"] == "class":
                    ast_data["classes"].append(type_data)
                elif type_data["type"] == "interface":
                    ast_data["interfaces"].append(type_data)
                elif type_data["type"] == "enum":
                    ast_data["enums"].append(type_data)
                elif type_data["type"] == "annotation":
                    ast_data["annotations"].append(type_data)
            
            # Store the raw AST for advanced processing
            ast_data["raw_ast"] = compilation_unit
        
        except (AttributeError, RuntimeError, ImportError) as e:  # pylint: disable=broad-except
            self.logger.warning("Error extracting AST data: %s", str(e))
        
        return ast_data
    
    def _extract_type_data(self, type_decl: Any) -> Dict[str, Any]:
        """
        Extract data from a type declaration.
        
        Args:
            type_decl: JavaParser type declaration
            
        Returns:
            Type data dictionary
        """
        type_data: Dict[str, Any] = {
            "name": str(type_decl.getName()),
            "type": "unknown",
            "modifiers": [],
            "annotations": [],
            "methods": [],
            "fields": [],
            "constructors": []
        }
        
        try:
            # Determine type
            class_name = type_decl.getClass().getSimpleName()
            if "ClassOrInterfaceDeclaration" in class_name:
                type_data["type"] = "interface" if type_decl.isInterface() else "class"
            elif "EnumDeclaration" in class_name:
                type_data["type"] = "enum"
            elif "AnnotationDeclaration" in class_name:
                type_data["type"] = "annotation"
            
            # Extract modifiers
            modifiers = type_decl.getModifiers()
            for modifier in modifiers:
                type_data["modifiers"].append(str(modifier.getKeyword()))
            
            # Extract annotations
            annotations = type_decl.getAnnotations()
            for annotation in annotations:
                type_data["annotations"].append(str(annotation.getName()))
            
            # Extract methods
            methods = type_decl.getMethods()
            for method in methods:
                method_data = self._extract_method_data(method)
                type_data["methods"].append(method_data)
            
            # Extract fields
            fields = type_decl.getFields()
            for field in fields:
                field_data = self._extract_field_data(field)
                type_data["fields"].append(field_data)
            
            # Extract constructors
            constructors = type_decl.getConstructors()
            for constructor in constructors:
                constructor_data = self._extract_constructor_data(constructor)
                type_data["constructors"].append(constructor_data)
            
            # Extract inheritance information for classes and interfaces
            if hasattr(type_decl, 'getExtendedTypes') and type_decl.getExtendedTypes():
                extended_types = type_decl.getExtendedTypes()
                if extended_types:
                    # For classes, there's typically only one extended type
                    type_data["extends"] = str(extended_types[0])
            
            if hasattr(type_decl, 'getImplementedTypes') and type_decl.getImplementedTypes():
                implemented_types = type_decl.getImplementedTypes()
                if implemented_types:
                    type_data["implements"] = [str(impl_type) for impl_type in implemented_types]
        
        except (AttributeError, RuntimeError) as e:  # pylint: disable=broad-except
            self.logger.warning("Error extracting type data: %s", str(e))
        
        return type_data
    
    def _extract_method_data(self, method: Any) -> Dict[str, Any]:
        """
        Extract method data.
        
        Args:
            method: JavaParser method declaration
            
        Returns:
            Method data dictionary
        """
        method_data: Dict[str, Any] = {
            "name": str(method.getName()),
            "return_type": str(method.getType()),
            "modifiers": [],
            "annotations": [],
            "parameters": []
        }
        
        try:
            # Extract modifiers
            modifiers = method.getModifiers()
            for modifier in modifiers:
                method_data["modifiers"].append(str(modifier.getKeyword()))
            
            # Extract annotations
            annotations = method.getAnnotations()
            for annotation in annotations:
                method_data["annotations"].append(str(annotation.getName()))
            
            # Extract parameters
            parameters = method.getParameters()
            for param in parameters:
                param_data = {
                    "name": str(param.getName()),
                    "type": str(param.getType())
                }
                method_data["parameters"].append(param_data)
            
            # Try to extract method body for complexity calculation
            try:
                if hasattr(method, 'getBody') and method.getBody().isPresent():
                    body = method.getBody().get()
                    # Count decision points in the AST body
                    method_data["complexity_score"] = self._calculate_complexity_from_ast(body)
                    method_data["line_count"] = self._calculate_lines_from_ast(body)
                    method_data["has_body"] = True
                    # Store the method body text for later use
                    method_data["body_text"] = str(body)
                else:
                    self.logger.debug("Method %s has no body", method_data["name"])
                    # Interface method or abstract method - no body
                    method_data["complexity_score"] = 1
                    method_data["line_count"] = 0
                    method_data["has_body"] = False
                    method_data["body_text"] = None
            except (AttributeError, RuntimeError) as e:
                self.logger.debug("Could not extract method body for %s: %s", method_data["name"], str(e))
                method_data["has_body"] = None  # Unknown, will fall back to regex
                method_data["body_text"] = None
        
        except (AttributeError, RuntimeError) as e:  # pylint: disable=broad-except
            self.logger.warning("Error extracting method data: %s", str(e))
        
        return method_data
    
    def _extract_field_data(self, field: Any) -> Dict[str, Any]:
        """
        Extract field data.
        
        Args:
            field: JavaParser field declaration
            
        Returns:
            Field data dictionary
        """
        field_data: Dict[str, Any] = {
            "name": str(field.getVariable(0).getName()),
            "type": str(field.getElementType()),
            "modifiers": [],
            "annotations": []
        }
        
        try:
            # Extract modifiers
            modifiers = field.getModifiers()
            for modifier in modifiers:
                field_data["modifiers"].append(str(modifier.getKeyword()))
            
            # Extract annotations
            annotations = field.getAnnotations()
            for annotation in annotations:
                field_data["annotations"].append(str(annotation.getName()))
        
        except (AttributeError, RuntimeError) as e:  # pylint: disable=broad-except
            self.logger.warning("Error extracting field data: %s", str(e))
        
        return field_data
    
    def _calculate_complexity_from_ast(self, body: Any) -> int:
        """
        Calculate cyclomatic complexity from JavaParser AST body.
        
        Args:
            body: JavaParser method body AST node
            
        Returns:
            Cyclomatic complexity score
        """
        try:
            complexity = 1  # Base complexity
            
            # Use JavaParser's AST visitor pattern to count decision points
            # This is more accurate than regex parsing
            statements = body.getStatements()
            for stmt in statements:
                complexity += self._count_decision_points_in_node(stmt)
            
            return max(1, complexity)
        except (AttributeError, RuntimeError) as e:
            self.logger.debug("Error calculating AST complexity: %s", str(e))
            return 1  # Fallback
    
    def _calculate_lines_from_ast(self, body: Any) -> int:
        """
        Calculate line count from JavaParser AST body.
        
        Args:
            body: JavaParser method body AST node
            
        Returns:
            Line count
        """
        try:
            # Count non-empty statements in the body
            statements = body.getStatements()
            return len(list(statements))
        except (AttributeError, RuntimeError) as e:
            self.logger.debug("Error calculating AST line count: %s", str(e))
            return 0  # Fallback
    
    def _count_decision_points_in_node(self, node: Any) -> int:
        """
        Recursively count decision points in an AST node.
        
        Args:
            node: JavaParser AST node
            
        Returns:
            Number of decision points in this node
        """
        try:
            decision_points = 0
            node_type = node.getClass().getSimpleName()
            
            # Count decision-making statements
            if node_type in ['IfStmt', 'WhileStmt', 'ForStmt', 'ForEachStmt', 
                           'DoStmt', 'SwitchStmt', 'CatchClause', 'ThrowStmt']:
                decision_points += 1
            elif node_type == 'SwitchEntry':  # case statements
                decision_points += 1
            elif node_type == 'ConditionalExpr':  # ternary operator
                decision_points += 1
            
            # Recursively process child nodes
            if hasattr(node, 'getChildNodes'):
                for child in node.getChildNodes():
                    decision_points += self._count_decision_points_in_node(child)
            
            return decision_points
        except (AttributeError, RuntimeError) as e:
            self.logger.debug("Error counting decision points: %s", str(e))
            return 0
    
    def _extract_constructor_data(self, constructor: Any) -> Dict[str, Any]:
        """
        Extract constructor data.
        
        Args:
            constructor: JavaParser constructor declaration
            
        Returns:
            Constructor data dictionary
        """
        constructor_data: Dict[str, Any] = {
            "name": str(constructor.getName()),
            "modifiers": [],
            "annotations": [],
            "parameters": []
        }
        
        try:
            # Extract modifiers
            modifiers = constructor.getModifiers()
            for modifier in modifiers:
                constructor_data["modifiers"].append(str(modifier.getKeyword()))
            
            # Extract annotations
            annotations = constructor.getAnnotations()
            for annotation in annotations:
                constructor_data["annotations"].append(str(annotation.getName()))
            
            # Extract parameters
            parameters = constructor.getParameters()
            for param in parameters:
                param_data = {
                    "name": str(param.getName()),
                    "type": str(param.getType())
                }
                constructor_data["parameters"].append(param_data)
        
        except (AttributeError, RuntimeError) as e:  # pylint: disable=broad-except
            self.logger.warning("Error extracting constructor data: %s", str(e))
        
        return constructor_data
    
    def is_available(self) -> bool:
        """
        Check if JPype and JavaParser are available.
        
        Returns:
            True if JPype is available and JAR files exist
        """
        try:
            import jpype
            jar_files = self._find_jar_files()
            return len(jar_files) > 0
        except ImportError:
            return False

