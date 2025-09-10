"""Java language detection rules and patterns."""

import re
from typing import Any, Dict, List, Tuple, Union


class JavaDetectionRules:
    """
    Java language detection rules for identifying Java source files
    and Java-related technologies (JSP, Spring, Hibernate, Struts).
    """
    
    @staticmethod
    def get_file_extensions() -> List[str]:
        """Get Java-related file extensions."""
        return ['.java', '.jsp', '.jspx', '.tag', '.tagx']
    
    @staticmethod
    def get_java_keywords() -> List[str]:
        """Get Java language keywords."""
        return [
            'abstract', 'assert', 'boolean', 'break', 'byte', 'case', 'catch',
            'char', 'class', 'const', 'continue', 'default', 'do', 'double',
            'else', 'enum', 'extends', 'final', 'finally', 'float', 'for',
            'goto', 'if', 'implements', 'import', 'instanceof', 'int',
            'interface', 'long', 'native', 'new', 'package', 'private',
            'protected', 'public', 'return', 'short', 'static', 'strictfp',
            'super', 'switch', 'synchronized', 'this', 'throw', 'throws',
            'transient', 'try', 'void', 'volatile', 'while'
        ]
    
    @staticmethod
    def get_detection_patterns() -> List[Tuple[str, int]]:
        """Get regex patterns for Java detection with weights."""
        return [
            # Package and import statements
            (r'\bpackage\s+[a-zA-Z_][a-zA-Z0-9_.]*\s*;', 15),
            (r'\bimport\s+[a-zA-Z_][a-zA-Z0-9_.]*\s*;', 10),
            (r'\bimport\s+static\s+[a-zA-Z_][a-zA-Z0-9_.]*\s*;', 12),
            
            # Class and interface declarations
            (r'\bpublic\s+class\s+[a-zA-Z_][a-zA-Z0-9_]*', 15),
            (r'\bpublic\s+interface\s+[a-zA-Z_][a-zA-Z0-9_]*', 15),
            (r'\bpublic\s+enum\s+[a-zA-Z_][a-zA-Z0-9_]*', 12),
            (r'\bpublic\s+abstract\s+class\s+[a-zA-Z_][a-zA-Z0-9_]*', 15),
            
            # Method declarations
            (r'\bpublic\s+static\s+void\s+main\s*\(', 20),
            (r'\bpublic\s+\w+\s+\w+\s*\([^)]*\)\s*\{', 8),
            (r'\bprivate\s+\w+\s+\w+\s*\([^)]*\)\s*\{', 8),
            (r'\bprotected\s+\w+\s+\w+\s*\([^)]*\)\s*\{', 8),
            
            # Annotations
            (r'@Override', 10),
            (r'@Deprecated', 8),
            (r'@SuppressWarnings', 8),
            (r'@Test', 5),
            
            # Java-specific constructs
            (r'\bnew\s+[A-Z][a-zA-Z0-9_]*\s*\(', 5),
            (r'\bthrows\s+[A-Z][a-zA-Z0-9_]*Exception', 8),
            (r'\bSystem\.out\.println', 8),
            (r'\bString\s+\w+\s*=', 5),
            (r'\bArrayList|HashMap|HashSet', 5),
            
            # Exception handling
            (r'\btry\s*\{', 5),
            (r'\bcatch\s*\([^)]+\)\s*\{', 8),
            (r'\bfinally\s*\{', 6),
            
            # Generics
            (r'<[A-Z][a-zA-Z0-9_]*>', 6),
            (r'List<\w+>', 5),
            (r'Map<\w+,\s*\w+>', 5)
        ]
    
    @staticmethod
    def get_jsp_patterns() -> List[Tuple[str, int]]:
        """Get patterns specific to JSP files."""
        return [
            # JSP directives
            (r'<%@\s*page\s+', 20),
            (r'<%@\s*taglib\s+', 18),
            (r'<%@\s*include\s+', 15),
            
            # JSP scriptlets and expressions
            (r'<%=\s*.*?\s*%>', 15),
            (r'<%\s+.*?\s+%>', 12),
            (r'<%!\s*.*?\s*%>', 10),
            
            # JSP tags
            (r'<jsp:include\s+', 15),
            (r'<jsp:forward\s+', 12),
            (r'<jsp:useBean\s+', 12),
            (r'<jsp:setProperty\s+', 10),
            (r'<jsp:getProperty\s+', 10),
            
            # JSTL tags
            (r'<c:\w+', 12),
            (r'<fmt:\w+', 10),
            (r'<fn:\w+', 8),
            
            # EL expressions
            (r'\$\{[^}]+\}', 10),
            
            # JSP implicit objects
            (r'\brequest\.', 8),
            (r'\bresponse\.', 8),
            (r'\bsession\.', 8),
            (r'\bapplication\.', 6),
            (r'\bpageContext\.', 8),
            (r'\bout\.', 6)
        ]
    
    @staticmethod
    def get_spring_indicators() -> List[Tuple[str, int]]:
        """Get patterns that indicate Spring Framework usage."""
        return [
            # Spring annotations
            (r'@Controller', 15),
            (r'@RestController', 18),
            (r'@Service', 15),
            (r'@Repository', 15),
            (r'@Component', 12),
            (r'@Autowired', 15),
            (r'@Qualifier', 10),
            (r'@Value', 8),
            (r'@Configuration', 15),
            (r'@Bean', 12),
            (r'@RequestMapping', 15),
            (r'@GetMapping|@PostMapping|@PutMapping|@DeleteMapping', 12),
            (r'@PathVariable', 10),
            (r'@RequestParam', 10),
            (r'@RequestBody', 10),
            (r'@ResponseBody', 10),
            
            # Spring imports
            (r'import\s+org\.springframework\.', 15),
            (r'import\s+org\.springframework\.stereotype\.', 18),
            (r'import\s+org\.springframework\.beans\.factory\.annotation\.', 15),
            (r'import\s+org\.springframework\.web\.bind\.annotation\.', 18),
            (r'import\s+org\.springframework\.context\.', 12),
            
            # Spring XML configuration
            (r'<beans\s+', 15),
            (r'<context:component-scan', 12),
            (r'<mvc:annotation-driven', 15),
            (r'xmlns="http://www\.springframework\.org/', 18)
        ]
    
    @staticmethod
    def get_hibernate_indicators() -> List[Tuple[str, int]]:
        """Get patterns that indicate Hibernate/JPA usage."""
        return [
            # JPA/Hibernate annotations
            (r'@Entity', 18),
            (r'@Table', 15),
            (r'@Id', 15),
            (r'@GeneratedValue', 15),
            (r'@Column', 12),
            (r'@OneToMany|@ManyToOne|@OneToOne|@ManyToMany', 15),
            (r'@JoinColumn', 12),
            (r'@JoinTable', 10),
            (r'@Temporal', 8),
            (r'@Enumerated', 8),
            (r'@Embeddable', 10),
            (r'@Embedded', 8),
            (r'@Transient', 8),
            
            # JPA imports
            (r'import\s+javax\.persistence\.', 15),
            (r'import\s+org\.hibernate\.', 15),
            (r'import\s+org\.hibernate\.annotations\.', 12),
            
            # Hibernate specific classes
            (r'\bSession\s+\w+', 8),
            (r'\bSessionFactory\s+\w+', 10),
            (r'\bQuery\s+\w+', 6),
            (r'\bCriteria\s+\w+', 6),
            (r'\.createQuery\(', 8),
            (r'\.createCriteria\(', 8),
            
            # HQL patterns
            (r'from\s+[A-Z][a-zA-Z0-9_]*\s+where', 10),
            (r'select\s+\w+\s+from\s+[A-Z][a-zA-Z0-9_]*', 8)
        ]
    
    @staticmethod
    def get_struts_indicators() -> List[Tuple[str, int]]:
        """Get patterns that indicate Struts Framework usage."""
        return [
            # Struts imports
            (r'import\s+org\.apache\.struts2?\.', 18),
            (r'import\s+com\.opensymphony\.xwork2\.', 15),
            
            # Struts annotations
            (r'@Action', 15),
            (r'@Result', 12),
            (r'@Results', 12),
            (r'@Namespace', 10),
            (r'@ParentPackage', 10),
            
            # Struts classes
            (r'extends\s+ActionSupport', 18),
            (r'extends\s+Action', 15),
            (r'implements\s+Action', 15),
            
            # Struts XML configuration
            (r'<struts>', 15),
            (r'<package\s+name=', 12),
            (r'<action\s+name=', 15),
            (r'<result\s+name=', 12),
            (r'<interceptor-ref\s+', 10),
            
            # Struts methods
            (r'public\s+String\s+execute\s*\(\)', 15),
            (r'\.addActionError\(', 8),
            (r'\.addFieldError\(', 8),
            (r'\.getText\(', 6)
        ]
    
    @staticmethod
    def detect_java_version(content: str) -> Dict[str, Union[bool, List[str]]]:
        """Detect Java version based on language features."""
        features: Dict[str, Union[bool, List[str]]] = {
            'java_8_plus': False,
            'java_11_plus': False,
            'java_17_plus': False,
            'detected_features': []
        }
        
        # Java 8+ features
        detected_features = features['detected_features']
        assert isinstance(detected_features, list)  # Type assertion for mypy
        
        if re.search(r'->', content):  # Lambda expressions
            features['java_8_plus'] = True
            detected_features.append('Lambda expressions')
        
        if re.search(r'Stream<', content):  # Stream API
            features['java_8_plus'] = True
            detected_features.append('Stream API')
        
        if re.search(r'Optional<', content):  # Optional
            features['java_8_plus'] = True
            detected_features.append('Optional')
        
        # Java 9+ features
        if re.search(r'module\s+\w+\s*\{', content):  # Module system
            features['java_11_plus'] = True
            detected_features.append('Module system')
        
        # Java 11+ features
        if re.search(r'var\s+\w+\s*=', content):  # Local variable type inference
            features['java_11_plus'] = True
            detected_features.append('Local variable type inference')
        
        # Java 14+ features
        if re.search(r'record\s+\w+', content):  # Records
            features['java_17_plus'] = True
            detected_features.append('Records')
        
        if re.search(r'sealed\s+class', content):  # Sealed classes
            features['java_17_plus'] = True
            detected_features.append('Sealed classes')
        
        return features
    
    @staticmethod
    def detect_build_system(content: str, file_path: str) -> List[str]:
        """Detect build system indicators."""
        build_systems = []
        
        # Maven indicators
        if 'pom.xml' in file_path.lower():
            build_systems.append('maven')
        
        maven_patterns = [
            r'<groupId>',
            r'<artifactId>',
            r'<version>',
            r'<dependencies>',
            r'<dependency>'
        ]
        
        if any(re.search(pattern, content) for pattern in maven_patterns):
            build_systems.append('maven')
        
        # Gradle indicators
        if 'build.gradle' in file_path.lower():
            build_systems.append('gradle')
        
        gradle_patterns = [
            r'apply\s+plugin:',
            r'dependencies\s*\{',
            r'implementation\s+',
            r'testImplementation\s+',
            r'repositories\s*\{'
        ]
        
        if any(re.search(pattern, content) for pattern in gradle_patterns):
            build_systems.append('gradle')
        
        # Ant indicators
        if 'build.xml' in file_path.lower():
            build_systems.append('ant')
        
        ant_patterns = [
            r'<project\s+',
            r'<target\s+name=',
            r'<javac\s+',
            r'<jar\s+',
            r'<path\s+id='
        ]
        
        if any(re.search(pattern, content) for pattern in ant_patterns):
            build_systems.append('ant')
        
        return list(set(build_systems))  # Remove duplicates
    
    @staticmethod
    def is_test_file(file_path: str, content: str) -> bool:
        """Check if file is a test file."""
        # Path-based detection
        if any(test_dir in file_path.lower() for test_dir in ['test', 'tests', 'src/test']):
            return True
        
        # Content-based detection
        test_patterns = [
            r'@Test',
            r'import\s+org\.junit\.',
            r'import\s+org\.testng\.',
            r'import\s+static\s+org\.junit\.Assert\.',
            r'import\s+static\s+org\.hamcrest\.',
            r'extends\s+TestCase',
            r'class\s+\w+Test\s*\{',
            r'class\s+Test\w+\s*\{'
        ]
        
        return any(re.search(pattern, content) for pattern in test_patterns)
    
    @staticmethod
    def detect_design_patterns(content: str) -> List[str]:
        """Detect common design patterns in Java code."""
        patterns = []
        
        # Singleton pattern
        if re.search(r'private\s+static\s+\w+\s+instance', content):
            patterns.append('Singleton')
        
        # Factory pattern
        if re.search(r'class\s+\w*Factory', content) or re.search(r'create\w+\s*\(', content):
            patterns.append('Factory')
        
        # Builder pattern
        if re.search(r'class\s+\w*Builder', content) or re.search(r'\.build\s*\(\)', content):
            patterns.append('Builder')
        
        # Observer pattern
        if re.search(r'addObserver|removeObserver|notifyObservers', content):
            patterns.append('Observer')
        
        # Strategy pattern
        if re.search(r'interface\s+\w*Strategy', content):
            patterns.append('Strategy')
        
        # Decorator pattern
        if re.search(r'class\s+\w*Decorator', content):
            patterns.append('Decorator')
        
        # DAO pattern
        if re.search(r'class\s+\w*DAO', content) or re.search(r'interface\s+\w*DAO', content):
            patterns.append('DAO')
        
        return patterns
