"""
Domain models for Step 01 (file_system_analysis) output.

Provides typed dataclasses for:
- step_metadata
- project_metadata
- build_configuration
- statistics (kept flexible as a raw dict with helpers)
- source_inventory (reusing existing SourceInventory model)
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from domain.source_inventory import SourceInventory


@dataclass
class StepMetadata:
    step_name: str
    execution_timestamp: str
    processing_time_ms: Optional[int] = None
    files_processed: Optional[int] = None
    errors_encountered: Optional[int] = None
    configuration_sources: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StepMetadata":
        return cls(
            step_name=data.get("step_name", ""),
            execution_timestamp=data.get("execution_timestamp", ""),
            processing_time_ms=data.get("processing_time_ms"),
            files_processed=data.get("files_processed"),
            errors_encountered=data.get("errors_encountered"),
            configuration_sources=list(data.get("configuration_sources", [])),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_name": self.step_name,
            "execution_timestamp": self.execution_timestamp,
            "processing_time_ms": self.processing_time_ms,
            "files_processed": self.files_processed,
            "errors_encountered": self.errors_encountered,
            "configuration_sources": list(self.configuration_sources),
        }


@dataclass
class ProjectData:
    project_name: str
    analysis_date: str
    languages_detected: List[str] = field(default_factory=list)
    frameworks_detected: List[str] = field(default_factory=list)
    total_files_analyzed: Optional[int] = None
    config_files_analyzed: int = 0
    java_files_analyzed: int = 0
    jsp_files_analyzed: int = 0
    sql_files_analyzed: int = 0
    files_with_config_details: int = 0
    java_files_with_entity_mapping: int = 0
    java_files_with_sql: int = 0
    files_by_language: Dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectData":
        return cls(
            project_name=data.get("project_name", ""),
            analysis_date=data.get("analysis_date", ""),
            languages_detected=list(data.get("languages_detected", [])),
            frameworks_detected=list(data.get("frameworks_detected", [])),
            total_files_analyzed=data.get("total_files_analyzed"),
            config_files_analyzed=data.get("config_files_analyzed", 0),
            java_files_analyzed=data.get("java_files_analyzed", 0),
            jsp_files_analyzed=data.get("jsp_files_analyzed", 0),
            sql_files_analyzed=data.get("sql_files_analyzed", 0),
            files_with_config_details=data.get("files_with_config_details", 0),
            java_files_with_entity_mapping=data.get("java_files_with_entity_mapping", 0),
            java_files_with_sql=data.get("java_files_with_sql", 0),
            files_by_language=dict(data.get("files_by_language", {})),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "analysis_date": self.analysis_date,
            "languages_detected": list(self.languages_detected),
            "frameworks_detected": list(self.frameworks_detected),
            "total_files_analyzed": self.total_files_analyzed,
            "config_files_analyzed": self.config_files_analyzed,
            "java_files_analyzed": self.java_files_analyzed,
            "jsp_files_analyzed": self.jsp_files_analyzed,
            "sql_files_analyzed": self.sql_files_analyzed,
            "files_with_config_details": self.files_with_config_details,
            "java_files_with_entity_mapping": self.java_files_with_entity_mapping,
            "java_files_with_sql": self.java_files_with_sql,
            "files_by_language": dict(self.files_by_language),
        }


@dataclass
class Statistics:
    # Keep flexible to avoid strict coupling to evolving schema
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Statistics":
        return cls(raw=dict(data or {}))

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.raw)

    # Convenience getters
    def file_inventory_count(self) -> Optional[int]:
        return self.raw.get("file_inventory_count")

    def count_by_language(self) -> Dict[str, int]:
        return dict(self.raw.get("count_language", {}))

    def subdomain_analysis(self) -> Dict[str, Any]:
        return dict(self.raw.get("subdomain_analysis", {}))


@dataclass
class Step02AstExtractorOutput:
    step_metadata: StepMetadata
    project_metadata: ProjectData
    statistics: Statistics
    source_inventory: SourceInventory

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Step02AstExtractorOutput":
        return cls(
            step_metadata=StepMetadata.from_dict(data.get("step_metadata", {})),
            project_metadata=ProjectData.from_dict(data.get("project_metadata", {})),
            statistics=Statistics.from_dict(data.get("statistics", {})),
            source_inventory=SourceInventory.from_dict(data.get("source_inventory", {})),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_metadata": self.step_metadata.to_dict(),
            "project_metadata": self.project_metadata.to_dict(),
            "statistics": self.statistics.to_dict(),
            "source_inventory": self.source_inventory.to_dict(),
        }
