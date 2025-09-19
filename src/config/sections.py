"""Configuration sections for CodeSight pipeline."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---- Top-level lightweight sections ----
@dataclass
class JspAnalysisConfig:
    legacy_patterns: List[str] = field(default_factory=list)
    security_tag_patterns: List[str] = field(default_factory=list)
    menu_detection: List[str] = field(default_factory=list)
    service_invocation_hints: List[str] = field(default_factory=list)
    tiles_patterns: List[str] = field(default_factory=list)
    custom_tag_prefixes: List[str] = field(default_factory=list)
    exclude_paths: List[str] = field(default_factory=list)
    include_paths: List[str] = field(default_factory=list)


@dataclass
class AnalysisConfig:
    enable_analysis: bool = True
    confidence_threshold: float = 0.7


@dataclass
class ProjectConfig:
    name: str = "default"
    description: str = ""
    source_path: str = "source"
    output_path: str = "output"
    default_source_path: str = "projects/{project_name}/source"
    default_output_path: str = "projects/{project_name}/output"
    enable_project_overrides: bool = True
    supported_languages: List[str] = field(default_factory=lambda: [
        "java", "jsp", "javascript", "vbscript", "xml", "properties", "yaml"
    ])


@dataclass
class EnvironmentConfig:
    environment: str = "development"
    debug_mode: bool = False


@dataclass
class ThreadingConfig:
    file_analysis: Dict[str, Any] = field(default_factory=lambda: {
        'max_workers': 8,
        'timeout_per_task': 300,
        'batch_timeout': 1800,
        'enable_thread_local_llm': True,
        'retry_attempts': 2
    })
    # Use a different name than 'global' (reserved in Python)
    global_config: Dict[str, Any] = field(default_factory=lambda: {
        'enable_threading': True,
        'adaptive_worker_count': True,
        'max_content_length': 50000,
        'progress_logging': True
    })


@dataclass
class PerformanceConfig:
    memory_limit_gb: int = 8
    enable_caching: bool = True
    cache_embeddings: bool = True
    cache_ast_results: bool = True


@dataclass
class ValidationConfig:
    enable_schema_validation: bool = True
    enable_cross_step_validation: bool = True
    confidence_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'minimum_overall': 0.6,
        'step01': 0.95,
        'step02': 0.9,
        'step03': 0.75,
        'step04': 0.8,
        'step05': 0.6,
        'step06': 0.75,
        'step07': 0.95
    })


@dataclass
class ParsersConfig:
    java: Dict[str, Any] = field(default_factory=lambda: {
        'lib_dir': 'lib',
        'jvm_args': ['-Xmx2g'],
        'frameworks': ['spring', 'hibernate', 'struts'],
        'source_roots': []
    })
    jsp: Dict[str, Any] = field(default_factory=lambda: {
        'lib_dir': 'lib',
        'jvm_args': ['-Xmx2g'],
        'web_frameworks': ['jsf', 'spring_mvc', 'struts'],
        'taglib_locations': []
    })
    # New: global parser scope controls for Step02
    include_globs: List[str] = field(default_factory=list)
    exclude_globs: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)


@dataclass
class OutputConfig:
    base_path: str = "output"
    format: str = "json"
    formats: List[str] = field(default_factory=lambda: ["json"])  # new
    reports_dir: str = "reports"  # new
    include_evidence_bundles: bool = False  # new
    pretty_print: bool = True
    include_metadata: bool = True
    generate_reports: bool = True
    files: Dict[str, str] = field(default_factory=lambda: {
        'final_output': 'final_output.json',
        'validation_report': 'validation_report.json',
        'processing_log': 'processing_log.json',
        'error_report': 'error_report.json'
    })


@dataclass
class SimpleFrameworkConfig:
    spring: Dict[str, Any] = field(default_factory=dict)
    hibernate: Dict[str, Any] = field(default_factory=dict)
    struts: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PatternConfig:
    enable_pattern_detection: bool = True
    confidence_threshold: float = 0.8


@dataclass
class DebugConfig:
    enable_debug_mode: bool = False
    save_intermediate_outputs: bool = True
    enable_step_timing: bool = True
    enable_memory_profiling: bool = False
    verbose_logging: bool = False


# ---- Steps configs ----
@dataclass
class BaseStepConfig:
    step_name: Optional[str] = None
    output_path: Optional[str] = None


@dataclass
class Step01Config(BaseStepConfig):
    step_name: str = "step01_filesystem_analyzer"
    include_extensions: List[str] = field(default_factory=lambda: [
        ".java", ".jsp", ".jspx", ".vbs", ".xml", ".properties",
        ".yml", ".yaml", ".sql", ".html", ".js", ".css"
    ])
    exclude_patterns: List[str] = field(default_factory=lambda: [
        "**/target/**", "**/build/**", "**/test/**",
        "**/node_modules/**", "**/.git/**"
    ])
    max_file_size_mb: int = 10
    enable_framework_detection: bool = True
    framework_confidence_threshold: float = 0.7
    build_parsers_optional: bool = False  # new


@dataclass
class Step02Config(BaseStepConfig):
    step_name: str = "step02_file_classifier"
    lib_dir: str = "lib"
    enable_symbol_resolution: bool = True
    parse_javadoc: bool = True
    extract_method_bodies: bool = True
    confidence_threshold: float = 0.9
    timeout_per_file_seconds: int = 30


@dataclass
class EmbeddingModelsConfig:
    primary: str = "microsoft/codebert-base"
    fallback: str = "sentence-transformers/all-MiniLM-L6-v2"
    dimension: int = 768
    device: str = "cpu"
    batch_size: int = 32
    max_sequence_length: int = 512

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary": self.primary,
            "fallback": self.fallback,
            "dimension": self.dimension,
            "device": self.device,
            "batch_size": self.batch_size,
            "max_sequence_length": self.max_sequence_length,
        }


@dataclass
class FaissConfig:
    index_type: str = "IndexFlatIP"
    dimension: int = 768
    memory_mapping: bool = True
    similarity_threshold: float = 0.7
    max_results_per_query: int = 20
    metric: str = "ip"  # new: ip|l2


@dataclass
class StorageConfig:
    embeddings_directory: str = "projects/{project_name}/embeddings"
    preserve_embeddings: bool = True
    cleanup_on_failure: bool = False


@dataclass
class ChunkingConfig:
    method_chunk_size: int = 200
    class_chunk_size: int = 500
    config_chunk_size: int = 300
    jsp_chunk_size: int = 400
    overlap_tokens: int = 20


@dataclass
class EnhancementConfig:
    confidence_boost_threshold: float = 0.05
    minimum_similarity_score: float = 0.6
    max_similar_components: int = 10
    clustering_threshold: float = 0.75
    min_chunks_for_clustering: int = 50
    min_cluster_size: int = 3  # new
    cohesion_metric: str = "silhouette"  # new


@dataclass
class Step03Config(BaseStepConfig):
    step_name: str = "step03_embeddings_analysis"
    enabled: bool = True
    models: EmbeddingModelsConfig = field(default_factory=EmbeddingModelsConfig)
    faiss: FaissConfig = field(default_factory=FaissConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    enhancement: EnhancementConfig = field(default_factory=EnhancementConfig)
    # New: configurable K for nearest-neighbor queries
    knn_k: int = 10


@dataclass
class Step04SecurityConfig:
    patterns: List[str] = field(default_factory=list)


@dataclass
class Step04RulesConfig:
    files: List[str] = field(default_factory=lambda: ["validation.xml", "validator-rules.xml"])


@dataclass
class Step04Config(BaseStepConfig):
    step_name: str = "step04_pattern_analysis"
    enable_spring_analysis: bool = True
    enable_hibernate_analysis: bool = True
    enable_struts_analysis: bool = True
    config_file_patterns: List[str] = field(default_factory=lambda: [
        "**/applicationContext*.xml", "**/spring*.xml",
        "**/hibernate*.xml", "**/persistence.xml",
        "**/application*.properties", "**/application*.yml",
    ])
    pattern_confidence_threshold: float = 0.8
    # New toggles
    enable_servlet: bool = True
    enable_jaxrs: bool = True
    enable_jsp_links: bool = True
    enable_sql_edges_java: bool = True
    enable_sql_edges_jsp: bool = False
    enable_sql_edges_sqlfiles: bool = True
    enable_security_roles: bool = True
    enable_jsp_security_detection: bool = False
    enable_trace_enrichment: bool = True
    enable_business_rules_extraction: bool = False
    # Nested configs
    security: Step04SecurityConfig = field(default_factory=Step04SecurityConfig)
    rules: Step04RulesConfig = field(default_factory=Step04RulesConfig)


@dataclass
class Step05Config(BaseStepConfig):
    step_name: str = "step05_llm_semantic_analysis"
    llm_provider: str = "kong_aws"
    batch_size: int = 5
    max_context_length: int = 8000
    confidence_threshold: float = 0.6
    enable_business_logic_extraction: bool = True
    enable_domain_classification: bool = True
    retry_attempts: int = 2
    # New: optional grouping of capabilities by dominant Step03 semantic cluster
    enable_cluster_grouping: bool = False


@dataclass
class Step06Config(BaseStepConfig):
    step_name: str = "step06_relationship_mapping"
    enable_service_interactions: bool = True
    enable_data_flow_analysis: bool = True
    relationship_confidence_threshold: float = 0.75
    max_relationship_depth: int = 5


@dataclass
class Step07Config(BaseStepConfig):
    step_name: str = "step07_output_generation"
    validate_target_schema: bool = True
    generate_validation_report: bool = True
    output_format: str = "json"
    pretty_print: bool = True
    include_debug_info: bool = False


# ---- Database / classification / patterns ----
@dataclass
class DatabaseConfig:
    discovery_pattern: str = "db/*"
    logical_name_pattern: str = "{directory_name}"


@dataclass
class ClassificationConfig:
    layers: List[str] = field(default_factory=lambda: [
        "UI", "Service", "Database", "Integration", "Configuration", "Reporting", "Utility", "Other"
    ])
    confidence_threshold: float = 0.5
    require_dual_match: bool = True
    fallback_layer: str = "Other"


@dataclass
class ArchitecturalPatternsConfig:
    Application: List[str] = field(default_factory=list)
    Business: List[str] = field(default_factory=list)
    DataAccess: List[str] = field(default_factory=list)
    Security: List[str] = field(default_factory=list)
    Shared: List[str] = field(default_factory=list)


@dataclass
class LayerPatternsConfig:
    UI: List[str] = field(default_factory=list)
    Service: List[str] = field(default_factory=list)
    Database: List[str] = field(default_factory=list)
    Integration: List[str] = field(default_factory=list)
    Reporting: List[str] = field(default_factory=list)
    Configuration: List[str] = field(default_factory=list)
    Utility: List[str] = field(default_factory=list)
    Other: List[str] = field(default_factory=list)
    _dynamic_layers: Dict[str, List[str]] = field(default_factory=dict)

    def __getattr__(self, name: str) -> List[str]:
        if name.startswith('_'):
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        return self._dynamic_layers.get(name, [])

    def __setattr__(self, name: str, value: List[str]) -> None:
        if name.startswith('_') or name in ['UI', 'Service', 'Database', 'Integration', 'Reporting', 'Configuration', 'Utility', 'Other']:
            super().__setattr__(name, value)
        else:
            if not hasattr(self, '_dynamic_layers'):
                super().__setattr__('_dynamic_layers', {})
            self._dynamic_layers[name] = value


@dataclass
class EntityManagerPatternsConfig:
    file_name_pattern: str = "**/*Mgr.java"
    class_declaration_pattern: str = r"class\s+(\w+Mgr)\s+extends\s+EntityMgr"
    table_name_method_pattern: str = r"protected\s+String\s+getTableName\(\)\s*\{"
    table_name_return_pattern: str = r"return\s+\"([^\"]+)\";"


@dataclass
class SqlExecutionPatternsConfig:
    prepared_statement_pattern: str = r"new\s+StormPS\s*\(\s*\"([^\";]+)\""
    exec_pattern: str = r"EXEC\s+(\w+)"
    dynamic_sp_pattern: str = r"getTableName\(\)\s*\+\s*\"(\w+)\""


@dataclass
class LanguageConfig:
    indicators: LayerPatternsConfig = field(default_factory=LayerPatternsConfig)
    package_patterns: LayerPatternsConfig = field(default_factory=LayerPatternsConfig)
    path_patterns: LayerPatternsConfig = field(default_factory=LayerPatternsConfig)
    entity_manager_patterns: Optional[EntityManagerPatternsConfig] = field(default_factory=EntityManagerPatternsConfig)
    sql_execution_patterns: Optional[SqlExecutionPatternsConfig] = field(default_factory=SqlExecutionPatternsConfig)


@dataclass
class LanguagesPatternsConfig:
    fallback: LayerPatternsConfig = field(default_factory=lambda: LayerPatternsConfig(
        UI=["*Controller*", "*Handler*", "*Servlet*", "*.jsp", "*.js", "*.html", "*View*"],
        Service=["*Service*", "*Manager*", "*Processor*", "*Business*", "*Logic*", "*Workflow*"],
        Database=["*DAO*", "*Repository*", "*Entity*", "*Model*", "*Mapper*"],
        Integration=["*Client*", "*Connector*", "*Adapter*", "*Gateway*", "*API*"],
        Reporting=["*Report*", "*Dashboard*", "*Analytics*", "*Chart*", "*Export*", "*PDF*", "*Excel*"],
        Configuration=["*.properties", "*.xml", "*.yaml", "*.yml", "*Config*", "*Configuration*"],
        Utility=["*Util*", "*Helper*", "*Common*", "*Shared*"]
    ))
    java: LanguageConfig = field(default_factory=lambda: LanguageConfig(
        indicators=LayerPatternsConfig(
            UI=["@Controller", "@RestController", "Servlet", "Handler"],
            Service=["@Service", "@Component", "Manager", "Processor"],
            Database=["@Repository", "@Entity", "DAO", "Mapper"],
            Integration=["@FeignClient", "Client", "Gateway", "Adapter"],
            Reporting=["Report", "Dashboard", "Analytics", "Chart", "Export", "PDF", "Excel"],
            Configuration=["@Configuration", "@ConfigurationProperties"],
        ),
        package_patterns=LayerPatternsConfig(
            UI=["com.**.controller.**"],
            Service=["com.**.service.**"],
            Database=["com.**.dao.**", "com.**.repository.**"],
            Integration=["com.**.client.**"],
            Reporting=["com.**.report.**", "com.**.reports.**", "com.**.dashboard.**", "com.**.analytics.**"],
            Configuration=["com.**.config.**"],
        ),
    ))
    javascript: LanguageConfig = field(default_factory=lambda: LanguageConfig(
        indicators=LayerPatternsConfig(
            UI=["Component", "View", "Page", "Route"],
            Service=["Service", "API", "Handler", "Manager"],
            Database=["Model", "Schema", "Repository"],
            Integration=["Client", "Adapter", "Connector"],
            Reporting=["Report", "Dashboard", "Chart", "Analytics", "Export", "EXCEL.application"],
            Configuration=["Config", "Settings", "Options"],
        ),
        path_patterns=LayerPatternsConfig(
            UI=["**/components/**", "**/pages/**"],
            Service=["**/services/**"],
            Database=["**/models/**"],
            Integration=["**/api/**"],
            Reporting=["**/reports/**", "**/dashboards/**", "**/analytics/**"],
        ),
    ))
    python: LanguageConfig = field(default_factory=lambda: LanguageConfig(
        indicators=LayerPatternsConfig(
            UI=["view", "handler", "controller", "template"],
            Service=["service", "manager", "processor", "business"],
            Database=["model", "dao", "repository", "entity"],
            Integration=["client", "adapter", "connector", "api"],
            Reporting=["report", "dashboard", "chart", "analytics", "export"],
        ),
        path_patterns=LayerPatternsConfig(
            UI=["**/views/**", "**/handlers/**"],
            Service=["**/services/**"],
            Database=["**/models/**"],
            Integration=["**/clients/**"],
            Reporting=["**/reports/**", "**/dashboards/**", "**/analytics/**"],
        ),
    ))
    sql: LanguageConfig = field(default_factory=lambda: LanguageConfig(
        indicators=LayerPatternsConfig(
            Database=[
                "CREATE TABLE", "ALTER TABLE", "DROP TABLE", "INSERT INTO", "UPDATE", "DELETE", "SELECT",
                "CREATE INDEX", "DROP INDEX", "CREATE PROCEDURE", "ALTER PROCEDURE", "DROP PROCEDURE", "BEGIN", "END", "EXEC",
            ]
        ),
        path_patterns=LayerPatternsConfig(
            Database=["**/sql/**", "**/database/**", "**/schemas/**", "**/scripts/**", "**/migrations/**", "**/*.sql"],
        ),
    ))
    jsp: LanguageConfig = field(default_factory=lambda: LanguageConfig(
        indicators=LayerPatternsConfig(
            UI=["<%@", "<%=", "<%!", "<jsp:", "<c:", "<f:", "<html>", "<body>"],
            Service=["<%", "import=", "session.", "request."],
            Database=["sql", "jdbc", "connection", "resultset"],
            Integration=["client", "webservice", "api"],
            Reporting=["report", "chart", "dashboard", "export", "EXCEL.application", "ActiveXObject"],
        ),
        path_patterns=LayerPatternsConfig(UI=["**/*.jsp", "**/*.jspx"]),
    ))
    vbscript: LanguageConfig = field(default_factory=lambda: LanguageConfig(
        indicators=LayerPatternsConfig(UI=["language=vbscript", "LANGUAGE=VBScript", "Sub ", "Function ", "Dim "])
    ))


@dataclass
class FrameworkConfig:
    indicators: List[str] = field(default_factory=list)
    layer_mapping: Dict[str, str] = field(default_factory=dict)
    config_files: List[str] = field(default_factory=list)


@dataclass
class FrameworksConfig:
    spring_boot: FrameworkConfig = field(default_factory=lambda: FrameworkConfig(
        indicators=["@SpringBootApplication", "@RestController", "@Service"],
        layer_mapping={
            "@Controller": "UI",
            "@RestController": "UI",
            "@Service": "Service",
            "@Repository": "Database",
            "@Component": "Service",
            "@Configuration": "Configuration",
        },
        config_files=["application.properties", "application.yml", "application.yaml", "bootstrap.properties", "bootstrap.yml"],
    ))
    react: FrameworkConfig = field(default_factory=lambda: FrameworkConfig(
        indicators=["import React", "function Component", "const Component"],
        layer_mapping={"Component": "UI", "Hook": "Service", "Context": "Service", "Reducer": "Service"},
        config_files=["package.json", "webpack.config.js", "babel.config.js", ".babelrc", "tsconfig.json"],
    ))
    django: FrameworkConfig = field(default_factory=lambda: FrameworkConfig(
        indicators=["from django", "models.Model", "views."],
        layer_mapping={
            "views": "UI",
            "models": "Database",
            "forms": "UI",
            "admin": "UI",
            "middleware": "Integration",
            "management": "Utility",
        },
        config_files=["settings.py", "urls.py", "wsgi.py", "asgi.py", "requirements.txt", "manage.py"],
    ))
    struts: FrameworkConfig = field(default_factory=lambda: FrameworkConfig(
        indicators=["Action", "ActionForm", "struts"],
        layer_mapping={"Action": "UI", "ActionForm": "UI", "DAO": "Database", "Service": "Service", "Exception": "Utility"},
        config_files=["struts.xml", "struts-config.xml", "web.xml", "validation.xml", "validator-rules.xml"],
    ))
    jee: FrameworkConfig = field(default_factory=lambda: FrameworkConfig(
        indicators=["@Stateless", "@Stateful", "@Entity", "@WebServlet", "@EJB"],
        layer_mapping={
            "@WebServlet": "UI",
            "@ManagedBean": "UI",
            "@Stateless": "Service",
            "@Stateful": "Service",
            "@Entity": "Database",
            "@EJB": "Service",
            "@MessageDriven": "Integration",
            "@WebService": "Integration",
        },
        config_files=["web.xml", "ejb-jar.xml", "persistence.xml", "application.xml", "beans.xml", "faces-config.xml"],
    ))


# ---- Quality gates and provenance ----
@dataclass
class QualityGatesStep01Config:
    unix_relative_required: bool = True
    min_config_accessible_pct: float = 0.9


@dataclass
class QualityGatesStep02Config:
    min_parse_success_pct: float = 0.7
    min_route_handler_resolution_pct: float = 0.5
    max_unresolved_refs_pct: float = 0.2


@dataclass
class QualityGatesStep03Config:
    min_embedding_coverage_pct: float = 0.8
    min_cluster_cohesion: float = 0.5


@dataclass
class QualityGatesStep04Config:
    min_config_parse_success_pct: float = 0.8
    min_pattern_confidence: float = 0.8


@dataclass
class QualityGatesStep05Config:
    min_citations_per_capability: int = 1
    min_capability_coverage_pct: float = 0.8


@dataclass
class QualityGatesStep06Config:
    min_route_chain_coverage_pct: float = 0.6
    require_iam_for_guarded_routes: bool = False


@dataclass
class QualityGatesConfig:
    step01: QualityGatesStep01Config = field(default_factory=QualityGatesStep01Config)
    step02: QualityGatesStep02Config = field(default_factory=QualityGatesStep02Config)
    step03: QualityGatesStep03Config = field(default_factory=QualityGatesStep03Config)
    step04: QualityGatesStep04Config = field(default_factory=QualityGatesStep04Config)
    step05: QualityGatesStep05Config = field(default_factory=QualityGatesStep05Config)
    step06: QualityGatesStep06Config = field(default_factory=QualityGatesStep06Config)


@dataclass
class ProvenanceConfig:
    per_file_confidence_enabled: bool = True
    confidence_weights: Dict[str, float] = field(default_factory=lambda: {'ast': 0.6, 'config': 0.3, 'llm': 0.1})
    evidence_sampling_rate: float = 1.0


# ---- Steps registry ----
@dataclass
class StepsConfig:
    step01: Step01Config = field(default_factory=Step01Config)
    step02: Step02Config = field(default_factory=Step02Config)
    step03: Step03Config = field(default_factory=Step03Config)
    step04: Step04Config = field(default_factory=Step04Config)
    step05: Step05Config = field(default_factory=Step05Config)
    step06: Step06Config = field(default_factory=Step06Config)
    step07: Step07Config = field(default_factory=Step07Config)
