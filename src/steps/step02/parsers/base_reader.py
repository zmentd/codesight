"""
Base parser interface for Step 02 AST extraction.

Defines the common interface and data structures for all parsers.
"""
import abc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import chardet

from config import Config
from utils.file_utils import FileUtils
from utils.logging.logger_factory import LoggerFactory


@dataclass
class ParseResult:
    """Result of parsing a single file."""
    success: bool
    file_path: str
    language: str
    structural_data: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    error_message: Optional[str] = None
    processing_time: float = 0.0
    framework_hints: List[str] = field(default_factory=list)


class BaseReader(abc.ABC):
    """
    Abstract base class for all Step 02 readers.

    Provides common functionality and defines the interface
    that all readers must implement.
    """
    
    def __init__(self, config: Config) -> None:
        """
        Initialize base reader.
        
        Args:
            config: Configuration instance
        """
        self.config = config
        self.logger = LoggerFactory.get_logger(f"steps.step02.{self.__class__.__name__.lower()}")
    
    def read_file(self, source_location: str, file_path: str) -> str:
        """
        Read file content safely with automatic encoding detection.
        
        Args:
            source_location: Source location identifier
            file_path: Path to the file
            
        Returns:
            File content as string
            
        Raises:
            FileNotFoundError: If file doesn't exist
            UnicodeDecodeError: If encoding detection fails
        """
        base_path = self.config.get_project_source_path()
        full_path = Path(f"{base_path}/{source_location}/{file_path}")
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {full_path.as_posix()}")
        
        # First try to detect encoding by reading raw bytes
        try:
            with open(full_path, 'rb') as f:
                raw_bytes = f.read()
            
            result = chardet.detect(raw_bytes)
            encoding = result['encoding']
            confidence = result['confidence']
            if encoding and confidence > 0.8:  # Consider a high confidence level
                self.logger.debug("Detected encoding: %s (confidence: %.2f)", encoding, confidence)
                # Read the file again with the detected encoding
                try:
                    with open(full_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    return content
                except UnicodeDecodeError as e:
                    # Fall back to BOM/other encodings instead of bailing out
                    self.logger.debug("Failed to read with detected encoding %s: %s; falling back", encoding, str(e))
            else:
                self.logger.warning(
                    "Could not confidently detect encoding for %s. Detected: %s, Confidence: %.2f",
                    full_path, encoding, confidence
                )

            # Check for BOM markers
            if raw_bytes.startswith(b'\xff\xfe'):
                # UTF-16 LE BOM
                return raw_bytes.decode('utf-16-le')
            elif raw_bytes.startswith(b'\xfe\xff'):
                # UTF-16 BE BOM
                return raw_bytes.decode('utf-16-be')
            elif raw_bytes.startswith(b'\xef\xbb\xbf'):
                # UTF-8 BOM
                return raw_bytes.decode('utf-8-sig')
            
            # Try different encodings in order of preference
            encodings_to_try = ['utf-8', 'utf-16', 'utf-16-le', 'utf-16-be', 'cp1252', 'latin1']
            
            for encoding in encodings_to_try:
                try:
                    # Try decoding the raw bytes directly
                    content = raw_bytes.decode(encoding)
                    self.logger.debug("Successfully decoded file %s with encoding: %s", full_path.as_posix(), encoding)
                    return content
                except UnicodeDecodeError as e:
                    self.logger.debug("Failed to decode with %s: %s", encoding, str(e))
                    continue
            
            # If all encodings fail, try with error handling
            self.logger.warning("All standard encodings failed for %s, trying with error replacement", full_path.as_posix())
            return raw_bytes.decode('utf-8', errors='replace')
            
        except Exception as e:
            # If all else fails, raise the original error
            raise UnicodeDecodeError('utf-8', b'', 0, 1, f"Unable to decode file with any supported encoding: {full_path.as_posix()}. Error: {str(e)}") from e

    @staticmethod
    def determine_encoding(file_path: str) -> str:
        """
        Determine the encoding of the SQL content.
        
        Args:
            content: The SQL file content as a string
            
        Returns:
            str: Detected encoding (default to 'utf-8' if not detected)
        """
        # Default to utf-8 if no BOM or specific encoding detected
        logger = LoggerFactory.get_logger("steps.step02.reader")
        detected_encoding = None
        try:
            with open(file_path, 'rb') as f:
                raw_bytes = f.read()
            
            result = chardet.detect(raw_bytes)
            encoding = result['encoding']
            confidence = result['confidence']
            if encoding and confidence > 0.8:  # Consider a high confidence level
                logger.debug("Detected encoding: %s (confidence: %.2f)", encoding, confidence)
                detected_encoding = encoding
            
        except Exception as e:
            # If all else fails, raise the original error
            raise UnicodeDecodeError('utf-8', b'', 0, 1, f"Unable to decode file with any supported encoding: {file_path}. Error: {str(e)}") from e

        return detected_encoding or 'utf-8'

    @abc.abstractmethod
    def can_parse(self, file_info: Dict[str, Any]) -> bool:
        """
        Check if this parser can handle the given file.
        
        Args:
            file_info: File information dictionary
            
        Returns:
            True if this parser can handle the file
        """
    
    @abc.abstractmethod
    def parse_file(self, source_path: str, file_path: str) -> ParseResult:
        """
        Parse a file and extract structural information.
        
        Args:
            file_path: Path to the file being parsed
            content: File content as string
            
        Returns:
            Parse result with extracted structural data
        """
    
    def _pre_process_content(self, content: str, file_path: str) -> str:
        """
        Pre-process file content before parsing.
        
        Args:
            content: Raw file content
            file_path: Path to the file
            
        Returns:
            Processed content
        """
        # Default implementation - subclasses can override
        return content
    
    def _post_process_result(self, result: ParseResult) -> ParseResult:
        """
        Post-process parse result before returning.
        
        Args:
            result: Initial parse result
            
        Returns:
            Enhanced parse result
        """
        # Default implementation - subclasses can override
        return result
    
    def _calculate_confidence(self, structural_data: Optional[Dict[str, Any]]) -> float:
        """
        Calculate confidence score for the parse result.
        
        Args:
            structural_data: Extracted structural data
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not structural_data:
            return 0.0
        
        # Basic confidence calculation - subclasses can override
        confidence = 0.5  # Base confidence
        
        # Increase confidence based on data completeness
        if "classes" in structural_data and structural_data["classes"]:
            confidence += 0.2
        if "methods" in structural_data and structural_data["methods"]:
            confidence += 0.2
        if "imports" in structural_data and structural_data["imports"]:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _handle_parse_error(self, file_path: str, error: Exception) -> ParseResult:
        """
        Handle parsing errors gracefully.
        
        Args:
            file_path: Path to the file that failed to parse
            error: Exception that occurred
            
        Returns:
            Error parse result
        """
        self.logger.error("Failed to parse %s: %s", file_path, str(error))
        
        return ParseResult(
            success=False,
            file_path=file_path,
            language="unknown",
            error_message=str(error),
            confidence=0.0
        )








