"""
Base parser interface for Step 02 AST extraction.

Defines the common interface and data structures for all parsers.
"""

import abc
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from config import Config
from domain.source_inventory import FileDetailsBase, FileInventoryItem
from utils.logging.logger_factory import LoggerFactory


@dataclass
class ParseResultOld:
    """Result of parsing a single file."""
    success: bool
    file_path: str
    language: str
    structural_data: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    error_message: Optional[str] = None
    processing_time: float = 0.0
    framework_hints: List[str] = field(default_factory=list)


class BaseParser(abc.ABC):
    """
    Abstract base class for all Step 02 parsers.
    
    Provides common functionality and defines the interface
    that all parsers must implement.
    """
    
    def __init__(self, config: Config) -> None:
        """
        Initialize base parser.
        
        Args:
            config: Configuration instance
        """
        self.config = config
        self.logger = LoggerFactory.get_logger("steps")
    
    @abc.abstractmethod
    def can_parse(self, file_item: FileInventoryItem) -> bool:
        """
        Check if this parser can handle the given file.
        
        Args:
            c
            
        Returns:
            True if this parser can handle the file
        """
    
    @abc.abstractmethod
    def parse_file(self, file_item: FileInventoryItem) -> FileDetailsBase:
        """
        Parse a file and extract structural information.
        
        Args:
            file_item: FileInventoryItem
            
        Returns:
            Parse result with extracted structural data
        """
       
       
       
