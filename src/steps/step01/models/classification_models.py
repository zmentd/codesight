"""
Data models for file classification results.
"""

from dataclasses import dataclass, field
from typing import List, Optional

# Import domain classes to replace operational equivalents
from domain.source_inventory import ArchitecturalPattern, PackageLayer


@dataclass
class LayerMatch:
    """Represents a matched layer with pattern and confidence."""
    layer: str
    pattern: str
    confidence: float


@dataclass
class FileClassification:
    """Complete classification result for a file."""
    subdomain_name: str
    layer: str
    subdomain_type: str
    confidence: float
    architectural_info: ArchitecturalPattern
    package_layer_info: PackageLayer
    framework_hints: List[str]
    tags: List[str] = field(default_factory=list)


@dataclass
class SubdomainInfo:
    """Subdomain extraction results."""
    name: str
    type: str
    confidence: float
