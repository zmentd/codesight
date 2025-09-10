import re
from typing import List, Optional


class SQLDialectDetector:
    """Detect SQL dialect from content patterns."""
    
    DIALECT_PATTERNS = {
        'sqlserver': [
            r'SET ANSI_NULLS',
            r'SET QUOTED_IDENTIFIER', 
            r'\bGO\b',
            r'\[dbo\]\.',
            r'IDENTITY\(\d+,\d+\)',
            r'CONSTRAINT.*DEFAULT',
            r'\bNVARCHAR\b',
            r'\bUNIQUEIDENTIFIER\b',
            r'\bDATETIME2\b',
            r'\bBIT\b',
            r'\[\w+\]'  # Bracket identifiers pattern
        ],
        'mysql': [
            r'ENGINE\s*=',
            r'AUTO_INCREMENT',
            r'DELIMITER\s*;;'
        ],
        'postgresql': [
            r'SERIAL',
            r'::'  # Type casting
        ]
    }
    
    def detect_dialect(self, sql_content: str) -> str:
        """Detect SQL dialect from content patterns."""
        if not sql_content or not sql_content.strip():
            return 'generic'
            
        scores = {}
        
        for dialect, patterns in self.DIALECT_PATTERNS.items():
            score = sum(1 for pattern in patterns 
                       if re.search(pattern, sql_content, re.IGNORECASE))
            scores[dialect] = score
        
        # Get the dialect with the highest score
        best_dialect, best_score = max(scores.items(), key=lambda x: x[1])
        
        # Only return a specific dialect if it has a positive score
        return best_dialect if best_score > 0 else 'generic'        