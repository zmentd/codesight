"""
Enhanced DDL Tokens module that extends simple_ddl_parser tokens.

This module provides additional tokens for parsing CREATE VIEW, CREATE PROCEDURE,
and CREATE FUNCTION statements that are not supported by the base simple_ddl_parser.
"""

from typing import Dict, Set, Tuple

try:
    from simple_ddl_parser import tokens as base_tokens  # type: ignore
except ImportError:
    # Fallback if simple_ddl_parser is not available
    base_tokens = None

# Define our custom tokens for enhanced DDL parsing
ENHANCED_TOKENS = [
    'VIEW',
    'PROCEDURE',
    'GO'  # SQL Server statement terminator
]

# Token definitions for common statements - extends simple_ddl_parser
ENHANCED_COMMON_STATEMENTS = {
    'VIEW': 'VIEW',
    'PROCEDURE': 'PROCEDURE',
    'GO': 'GO'
}

# Token definitions for DDL definition statements - extends simple_ddl_parser
ENHANCED_DEFINITION_STATEMENTS = {
    'VIEW': 'VIEW',
    'PROCEDURE': 'PROCEDURE'
}


def get_enhanced_tokens() -> Tuple[str, ...]:
    """
    Get the complete token list combining base and enhanced tokens.
    
    Returns:
        Tuple of all available tokens
    """
    
    if base_tokens and hasattr(base_tokens, 'tokens'):
        # Merge base tokens with our enhanced tokens
        base_token_set = set(base_tokens.tokens) if isinstance(base_tokens.tokens, (list, tuple)) else set()
        enhanced_token_set = set(ENHANCED_TOKENS)
        return tuple(base_token_set | enhanced_token_set)
    else:
        # If base tokens not available, return just our enhanced tokens
        return tuple(ENHANCED_TOKENS)


def get_enhanced_common_statements() -> Dict[str, str]:
    """
    Get enhanced common statements dictionary combining base and enhanced.
    
    Returns:
        Dictionary of common statement tokens
    """
    if base_tokens and hasattr(base_tokens, 'common_statements'):
        enhanced_common: Dict[str, str] = base_tokens.common_statements.copy()
        enhanced_common.update(ENHANCED_COMMON_STATEMENTS)
        return enhanced_common
    else:
        return ENHANCED_COMMON_STATEMENTS.copy()


def get_enhanced_definition_statements() -> Dict[str, str]:
    """
    Get enhanced definition statements dictionary combining base and enhanced.
    
    Returns:
        Dictionary of definition statement tokens  
    """
    if base_tokens and hasattr(base_tokens, 'definition_statements'):
        enhanced_definition: Dict[str, str] = base_tokens.definition_statements.copy()
        enhanced_definition.update(ENHANCED_DEFINITION_STATEMENTS)
        return enhanced_definition
    else:
        return ENHANCED_DEFINITION_STATEMENTS.copy()


# Export the enhanced token collections
tokens = get_enhanced_tokens()
common_statements = get_enhanced_common_statements()
definition_statements = get_enhanced_definition_statements()
