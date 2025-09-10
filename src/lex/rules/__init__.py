"""Language-specific detection rules package."""

from .java_rules import JavaDetectionRules
from .sql_rules import SqlDetectionRules
from .web_rules import WebDetectionRules

__all__ = [
    "JavaDetectionRules",
    "SqlDetectionRules",
    "WebDetectionRules"
]
