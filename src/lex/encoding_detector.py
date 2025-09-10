"""Text encoding detection for source files."""

from pathlib import Path
from typing import Any, Dict, List, Optional

import chardet

from config import Config
from config.exceptions import ConfigurationError
from utils.logging.logger_factory import LoggerFactory


class EncodingDetector:
    """
    Character encoding detection for source code files.
    
    Uses chardet library for automatic encoding detection
    with fallback strategies for common encodings.
    """
    
    def __init__(self, config: Optional[Config] = None) -> None:
        """Initialize encoding detector with configuration."""
        try:
            self.config = config if config is not None else Config.get_instance()
        except ConfigurationError as e:
            raise ConfigurationError(f"Failed to initialize encoding detector: {e}") from e
        self.logger = LoggerFactory.get_logger(__name__)
        # Access step01 config for encoding settings
        step01_config = getattr(self.config, 'step01', None)
        self.default_encoding = getattr(step01_config, 'default_encoding', 'utf-8') if step01_config else 'utf-8'
        self.confidence_threshold = getattr(step01_config, 'confidence_threshold', 0.7) if step01_config else 0.7
    
    def detect_encoding(self, file_path: str) -> Dict[str, Any]:
        """
        Detect the character encoding of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with encoding detection results
        """
        try:
            path = Path(file_path)
            
            if not path.exists() or path.is_dir():
                return {
                    'file_path': file_path,
                    'encoding': None,
                    'confidence': 0.0,
                    'error': 'File does not exist or is a directory'
                }
            
            # Read file as binary
            with open(file_path, 'rb') as f:
                raw_data = f.read()
            
            if not raw_data:
                return {
                    'file_path': file_path,
                    'encoding': self.default_encoding,
                    'confidence': 1.0,
                    'detection_method': 'default_empty_file'
                }
            
            # Use chardet for detection
            detection_result = chardet.detect(raw_data)
            
            detected_encoding = detection_result.get('encoding')
            confidence = detection_result.get('confidence', 0.0)
            
            # Validate and normalize encoding
            if detected_encoding:
                detected_encoding = self._normalize_encoding(detected_encoding)
            
            # Apply confidence threshold
            if confidence < self.confidence_threshold:
                # Try fallback methods
                fallback_result = self._try_fallback_encodings(raw_data)
                if fallback_result['encoding']:
                    return {
                        'file_path': file_path,
                        'encoding': fallback_result['encoding'],
                        'confidence': fallback_result['confidence'],
                        'detection_method': 'fallback',
                        'chardet_result': detection_result
                    }
            
            # Use detected encoding or default
            final_encoding = detected_encoding if confidence >= self.confidence_threshold else self.default_encoding
            final_confidence = confidence if detected_encoding else 0.5
            
            return {
                'file_path': file_path,
                'encoding': final_encoding,
                'confidence': final_confidence,
                'detection_method': 'chardet' if detected_encoding else 'default',
                'chardet_result': detection_result
            }
            
        except (OSError, IOError) as e:
            self.logger.error("Failed to detect encoding for %s: %s", file_path, e)
            return {
                'file_path': file_path,
                'encoding': self.default_encoding,
                'confidence': 0.0,
                'error': str(e),
                'method': 'error_fallback'
            }
        except (ValueError, RuntimeError) as e:
            self.logger.error("Unexpected error detecting encoding for %s: %s", file_path, e)
            return {
                'file_path': file_path,
                'encoding': self.default_encoding,
                'confidence': 0.0,
                'error': str(e),
                'method': 'error_fallback'
            }
    
    def _normalize_encoding(self, encoding: str) -> str:
        """Normalize encoding name to standard form."""
        if not encoding:
            return self.default_encoding
        
        encoding_lower = encoding.lower()
        
        # Common encoding mappings
        encoding_map = {
            'ascii': 'ascii',
            'utf-8': 'utf-8',
            'utf8': 'utf-8',
            'utf-16': 'utf-16',
            'utf16': 'utf-16',
            'utf-32': 'utf-32',
            'utf32': 'utf-32',
            'iso-8859-1': 'latin-1',
            'latin-1': 'latin-1',
            'cp1252': 'cp1252',
            'windows-1252': 'cp1252',
            'big5': 'big5',
            'gbk': 'gbk',
            'gb2312': 'gb2312',
            'shift_jis': 'shift_jis',
            'euc-jp': 'euc-jp',
            'euc-kr': 'euc-kr'
        }
        
        return encoding_map.get(encoding_lower, encoding)
    
    def _try_fallback_encodings(self, raw_data: bytes) -> Dict[str, Any]:
        """Try common encodings as fallback."""
        fallback_encodings = ['utf-8', 'latin-1', 'cp1252', 'ascii']
        
        for encoding in fallback_encodings:
            try:
                decoded = raw_data.decode(encoding)
                # Simple validation - check for null bytes or control characters
                if self._is_valid_text(decoded):
                    return {
                        'encoding': encoding,
                        'confidence': 0.8  # High confidence for successful fallback
                    }
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        return {'encoding': None, 'confidence': 0.0}
    
    def _is_valid_text(self, text: str) -> bool:
        """Validate if decoded text looks reasonable."""
        if not text:
            return True
        
        # Check for excessive null bytes or control characters
        null_ratio = text.count('\x00') / len(text)
        if null_ratio > 0.1:  # More than 10% null bytes
            return False
        
        # Check for excessive control characters (excluding common ones)
        control_chars = sum(1 for c in text if ord(c) < 32 and c not in '\t\n\r')
        control_ratio = control_chars / len(text)
        if control_ratio > 0.05:  # More than 5% control characters
            return False
        
        return True
    
    def read_file_with_encoding(self, file_path: str, encoding: Optional[str] = None) -> Dict[str, Any]:
        """
        Read file content with detected or specified encoding.
        
        Args:
            file_path: Path to the file
            encoding: Specific encoding to use (if None, will detect)
            
        Returns:
            Dictionary with file content and encoding info
        """
        try:
            if encoding is None:
                detection_result = self.detect_encoding(file_path)
                encoding = detection_result.get('encoding', self.default_encoding)
                confidence = detection_result.get('confidence', 0.0)
            else:
                confidence = 1.0  # User-specified encoding
            
            # Read file with detected/specified encoding
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read()
            
            return {
                'file_path': file_path,
                'content': content,
                'encoding': encoding,
                'confidence': confidence,
                'content_length': len(content),
                'success': True
            }
            
        except (OSError, IOError) as e:
            self.logger.error("Failed to read file %s with encoding %s: %s", file_path, encoding, e)
            
            # Try with default encoding and error replacement
            try:
                with open(file_path, 'r', encoding=self.default_encoding, errors='replace') as f:
                    content = f.read()
                
                return {
                    'file_path': file_path,
                    'content': content,
                    'encoding': self.default_encoding,
                    'confidence': 0.0,
                    'content_length': len(content),
                    'success': True,
                    'warning': f"Used fallback encoding due to error: {e}"
                }
            except (OSError, IOError) as fallback_error:
                return {
                    'file_path': file_path,
                    'content': None,
                    'encoding': None,
                    'confidence': 0.0,
                    'success': False,
                    'error': str(fallback_error)
                }
    
    def validate_encoding(self, file_path: str, encoding: str) -> Dict[str, Any]:
        """
        Validate if a file can be read with a specific encoding.
        
        Args:
            file_path: Path to the file
            encoding: Encoding to validate
            
        Returns:
            Dictionary with validation results
        """
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
            
            # Try to decode with specified encoding
            decoded = raw_data.decode(encoding)
            
            # Validate the decoded text
            is_valid = self._is_valid_text(decoded)
            
            return {
                'file_path': file_path,
                'encoding': encoding,
                'is_valid': is_valid,
                'content_length': len(decoded),
                'error': None
            }
            
        except (UnicodeDecodeError, UnicodeError) as e:
            return {
                'file_path': file_path,
                'encoding': encoding,
                'is_valid': False,
                'content_length': 0,
                'error': f"Encoding error: {e}"
            }
        except (OSError, IOError) as e:
            return {
                'file_path': file_path,
                'encoding': encoding,
                'is_valid': False,
                'content_length': 0,
                'error': f"File I/O error: {e}"
            }
    
    def get_supported_encodings(self) -> List[str]:
        """Get list of commonly supported encodings."""
        return [
            'utf-8',
            'utf-16',
            'utf-32',
            'ascii',
            'latin-1',
            'cp1252',
            'big5',
            'gbk',
            'gb2312',
            'shift_jis',
            'euc-jp',
            'euc-kr',
            'iso-8859-1',
            'iso-8859-2',
            'iso-8859-15'
        ]
    
    def detect_bom(self, file_path: str) -> Dict[str, Any]:
        """
        Detect Byte Order Mark (BOM) in file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with BOM detection results
        """
        try:
            with open(file_path, 'rb') as f:
                bom_bytes = f.read(4)  # Read first 4 bytes
            
            # BOM signatures
            bom_signatures = {
                b'\xef\xbb\xbf': 'utf-8',
                b'\xff\xfe': 'utf-16le',
                b'\xfe\xff': 'utf-16be',
                b'\xff\xfe\x00\x00': 'utf-32le',
                b'\x00\x00\xfe\xff': 'utf-32be'
            }
            
            detected_bom = None
            detected_encoding = None
            
            # Check for BOM signatures
            for bom, encoding in bom_signatures.items():
                if bom_bytes.startswith(bom):
                    detected_bom = bom
                    detected_encoding = encoding
                    break
            
            return {
                'file_path': file_path,
                'has_bom': detected_bom is not None,
                'bom_bytes': detected_bom,
                'bom_encoding': detected_encoding,
                'bom_length': len(detected_bom) if detected_bom else 0
            }
            
        except (OSError, IOError) as e:
            self.logger.error("Failed to detect BOM for %s: %s", file_path, e)
            return {
                'file_path': file_path,
                'has_bom': False,
                'bom_bytes': None,
                'bom_encoding': None,
                'bom_length': 0,
                'error': str(e)
            }
