"""
Enhanced DDL Parser that extends simple_ddl_parser to support CREATE VIEW and CREATE PROCEDURE statements.

This module provides an extended DDLParser class that adds grammar rules for parsing
CREATE VIEW and CREATE PROCEDURE statements that are not supported by the base simple_ddl_parser.
It follows the base parser's incremental and recursive pattern while using sqlparse for 
SELECT statement analysis.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Union

from simple_ddl_parser import DDLParser  # type: ignore
from simple_ddl_parser import tokens as base_tokens
from simple_ddl_parser.exception import SimpleDDLParserException  # type: ignore

from utils.logging.logger_factory import LoggerFactory

try:
    import sqlparse  # type: ignore
except ImportError:
    sqlparse = None

# Import our enhanced tokens module
from .enhanced_ddl_tokens import (
    ENHANCED_COMMON_STATEMENTS,
    ENHANCED_DEFINITION_STATEMENTS,
    ENHANCED_TOKENS,
)


class EnhancedDDLParserError(SimpleDDLParserException):
    """Exception for enhanced DDL parser errors."""


class EnhancedDDLParser(DDLParser):
    """
    Extended DDL Parser that adds support for CREATE VIEW and CREATE PROCEDURE statements.
    
    This parser extends the base simple_ddl_parser functionality to handle:
    - CREATE VIEW statements with AS clauses
    - CREATE PROCEDURE statements with parameter lists and body
    - Basic CREATE FUNCTION statements
    - View metadata extraction using sqlparse
    
    Usage:
        parser = EnhancedDDLParser(sql_content)
        results = parser.run()
    """
    
    def __init__(self, ddl_string: str, **kwargs: Any) -> None:
        """
        Initialize the enhanced DDL parser.
        
        Args:
            ddl_string: The DDL string to parse
            **kwargs: Additional arguments passed to the base DDLParser
        """
        # Set normalize_names=True by default to handle SQL Server square brackets
        if 'normalize_names' not in kwargs:
            kwargs['normalize_names'] = True
        self.logger = LoggerFactory.get_logger("steps.step02.enhanced_ddl_parser")   
        # Pre-process the DDL string to handle SQL Server specific syntax
        # Store original DDL for post-processing
        self._original_ddl = ddl_string
        
        processed_ddl = self._preprocess_sql_server_ddl(ddl_string)
        
        # Add our enhanced tokens to the base tokens before initializing
        self._setup_enhanced_tokens()
        
        # Initialize base parser
        super().__init__(processed_ddl, **kwargs)
        
        # Extend token dictionaries instead of replacing them
        self._extend_token_dictionaries()
    
    def _setup_enhanced_tokens(self) -> None:
        """Setup enhanced tokens by extending the base parser's tokens."""
        # Import base tokens
        try:
            # Create a temporary parser to get base tokens
            temp_parser = DDLParser('')
            base_tokens_tuple = temp_parser.tokens
            
            # Add our enhanced tokens
            enhanced_tokens = list(base_tokens_tuple) + ['VIEW', 'PROCEDURE']
            
            # Set the tokens attribute for PLY
            self.tokens = tuple(enhanced_tokens)
            
        except (ImportError, AttributeError, KeyError):
            # Fallback - just use our enhanced tokens
            self.tokens = ('VIEW', 'PROCEDURE')
    
    def _extend_token_dictionaries(self) -> None:
        """Extend base parser token dictionaries with our enhanced tokens."""
        # Extend common_statements for lexer token classification
        if hasattr(base_tokens, 'common_statements'):
            base_tokens.common_statements.update(ENHANCED_COMMON_STATEMENTS)
        
        # Extend definition_statements for DDL recognition
        if hasattr(base_tokens, 'definition_statements'):
            base_tokens.definition_statements.update(ENHANCED_DEFINITION_STATEMENTS)
    
    def _preprocess_sql_server_ddl(self, ddl_string: str) -> str:
        """
        Pre-process SQL Server DDL to handle specific syntax before PLY parsing.
        
        For CREATE VIEW statements, we need to extract the SELECT statement 
        and replace it with a placeholder to avoid PLY parsing issues.
        For CREATE PROCEDURE statements, we handle SQL Server specific syntax.
        
        Args:
            ddl_string: The original DDL string
            
        Returns:
            Processed DDL string that PLY can handle better
        """
        # Store original for later extraction
        self._original_ddl_for_processing = ddl_string
        
        # Check if this is a stored procedure file and handle accordingly
        if re.search(r'CREATE\s+PROCEDURE', ddl_string, re.IGNORECASE):
            # Handle SQL Server stored procedure files with complex syntax
            processed = ddl_string
            
            # Remove multiline comments
            processed = re.sub(r'/\*.*?\*/', '', processed, flags=re.DOTALL)
            
            # Remove SET statements
            processed = re.sub(r'SET\s+\w+\s+(ON|OFF)', '', processed, flags=re.IGNORECASE)
            
            # Remove IF EXISTS DROP statements
            processed = re.sub(r'IF\s+EXISTS.*?DROP\s+\w+\s+\S+', '', processed, flags=re.IGNORECASE)
            
            # Remove GO statements
            processed = re.sub(r'\bGO\b', '', processed, flags=re.IGNORECASE)
            
            # Extract CREATE PROCEDURE and simplify
            proc_match = re.search(r'CREATE\s+PROCEDURE\s+(\S+)', processed, re.IGNORECASE)
            if proc_match:
                proc_name = proc_match.group(1)
                return f'CREATE PROCEDURE {proc_name} AS SELECT 1'
                
            return processed
        
        # Remove GO statements for now - they cause parsing issues
        processed = re.sub(r'\bGO\b', '', ddl_string, flags=re.IGNORECASE)
        
        # For CREATE VIEW statements, replace everything after AS with a placeholder
        view_pattern = r'(CREATE\s+VIEW\s+[^\s]+\s+AS)\s+(.+?)(?:$|\s*;|\s*GO)'
        match = re.search(view_pattern, processed, re.IGNORECASE | re.DOTALL)
        
        if match:
            view_declaration = match.group(1)  # "CREATE VIEW viewname AS"
            select_statement = match.group(2)  # Everything after AS
            
            # Store the SELECT statement for post-processing
            self._extracted_select_statement = select_statement.strip()
            
            # Replace with just the CREATE VIEW AS part
            processed = view_declaration
        
        # Normalize whitespace
        processed = re.sub(r'\s+', ' ', processed.strip())
        
        return processed
    
    # Following base parser pattern - incremental CREATE VIEW rules
    def p_create_view_base(self, p: Any) -> None:
        """create_view : CREATE VIEW"""
        # Basic CREATE VIEW recognition - just the keywords
        p[0] = {
            'ddl_type': 'create_view',
            'table_type': 'VIEW'
        }
    
    def p_view_name(self, p: Any) -> None:
        """view_name : create_view t_name"""
        # Add table name to CREATE VIEW - follows base parser's table_name : create_table t_name pattern
        p[0] = p[1]  # Start with create_view dict
        p[0].update(p[2])  # Add t_name data (schema, table_name, etc.)
        p[0]['view_name'] = p[2]['table_name']
        # Keep schema from t_name if present
        if p[2]['schema']:
            p[0]['schema_name'] = p[2]['schema']
        else:
            p[0]['schema_name'] = 'dbo'  # Default schema
    
    def p_view_with_as_clause(self, p: Any) -> None:
        """expr : view_name AS"""
        # Handle CREATE VIEW with AS clause by capturing everything after AS
        if isinstance(p[1], dict) and p[1].get('ddl_type') == 'create_view':
            view_def = p[1]
            
            # For now, we'll handle this in a post-processing step
            # Mark this as needing post-processing
            view_def['needs_select_processing'] = True
            
            # Build basic view definition
            view_def.update({
                'view_definition': '',  # Will be filled in post-processing
                'columns': [],
                'referenced_tables': [],
                'primary_key': [],
                'alter': {},
                'checks': [],
                'index': [],
                'partitioned_by': [],
                'constraints': {}
            })
            
            p[0] = view_def
        else:
            # Not a view, pass through
            p[0] = p[1]
    
    def p_expression_view(self, p: Any) -> None:
        """expr : view_name"""
        # Connect view_name to main expr rule - follows base parser pattern like p_expression_table
        p[0] = p[1]
    
    # CREATE PROCEDURE following base parser pattern
    def p_create_procedure_base(self, p: Any) -> None:
        """create_procedure : CREATE PROCEDURE"""
        # Basic CREATE PROCEDURE recognition - just the keywords
        p[0] = {
            'ddl_type': 'create_procedure',
            'table_type': 'procedure'
        }
    
    def p_procedure_name(self, p: Any) -> None:
        """procedure_name : create_procedure t_name"""
        # Add procedure name to CREATE PROCEDURE - follows same pattern as view_name
        p[0] = p[1]  # Start with create_procedure dict
        p[0].update(p[2])  # Add t_name data (schema, table_name, etc.)
        p[0]['procedure_name'] = p[2]['table_name']
        # Keep schema from t_name if present
        if p[2]['schema']:
            p[0]['schema'] = p[2]['schema']
        else:
            p[0]['schema'] = 'dbo'  # Default schema
    
    def p_procedure_with_as_clause(self, p: Any) -> None:
        """expr : procedure_name AS"""
        # Handle CREATE PROCEDURE with AS clause
        if isinstance(p[1], dict) and p[1].get('ddl_type') == 'create_procedure':
            proc_def = p[1]
            
            # Mark for post-processing
            proc_def['needs_body_processing'] = True
            
            proc_def.update({
                'procedure_parameters': [],  # Could be enhanced later
                'procedure_body': '',  # Will be filled in post-processing
                'primary_key': [],
                'alter': {},
                'checks': [],
                'index': [],
                'partitioned_by': [],
                'constraints': {}
            })
            
            p[0] = proc_def
        else:
            # Not a procedure, pass through
            p[0] = p[1]
    
    def p_expression_procedure(self, p: Any) -> None:
        """expr : procedure_name"""
        # Connect procedure_name to main expr rule - follows base parser pattern
        p[0] = p[1]

    def run(self, group_by_type: bool = True, **kwargs: Any) -> Any:
        """Override run method to add post-processing for view/procedure bodies."""
        # Store original DDL for post-processing
        self._original_ddl = getattr(self, '_original_ddl', "")
        
        # Run base parser
        results = super().run(group_by_type=group_by_type, **kwargs)
        
        # Post-process results to extract SELECT statements and procedure bodies
        if isinstance(results, dict):
            # Handle grouped results (group_by_type=True)
            for category, items in results.items():
                if isinstance(items, list):
                    for i, item in enumerate(items):
                        if isinstance(item, dict):
                            items[i] = self._post_process_result(item)
        elif isinstance(results, list):
            # Handle flat list results (group_by_type=False)
            processed_results = []
            for result in results:
                if isinstance(result, dict):
                    processed_result = self._post_process_result(result)
                    processed_results.append(processed_result)
                else:
                    processed_results.append(result)
            return processed_results
            
        return results

    def _post_process_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Post-process a single result to extract view/procedure bodies."""
        # Get table properties where our flags might be stored
        table_props = result.get('table_properties', {})
        
        # Handle CREATE VIEW post-processing
        if (result.get('needs_select_processing', False) or 
                table_props.get('needs_select_processing', False)):
            
            select_statement = self._extract_select_from_ddl()
            if select_statement:
                result['view_definition'] = select_statement
                
                # Extract metadata using sqlparse
                view_metadata = self._extract_view_metadata(select_statement)
                result['columns'] = view_metadata.get('columns', [])
                result['referenced_tables'] = view_metadata.get('referenced_tables', [])
                result['operation_type'] = view_metadata.get('operation_type', 'SELECT')
                
            # Remove the processing flag from both locations
            result.pop('needs_select_processing', None)
            if 'table_properties' in result:
                result['table_properties'].pop('needs_select_processing', None)
            
        # Handle CREATE PROCEDURE post-processing  
        if (result.get('needs_body_processing', False) or 
                table_props.get('needs_body_processing', False)):
            
            procedure_body = self._extract_procedure_body_from_ddl()
            if procedure_body:
                result['procedure_body'] = procedure_body
                
                # Extract operation type and referenced tables from procedure body
                procedure_metadata = self._extract_procedure_metadata(procedure_body)
                result['operation_type'] = procedure_metadata.get('operation_type', 'SELECT')
                result['referenced_tables'] = procedure_metadata.get('referenced_tables', [])
                
            # Remove the processing flag from both locations
            result.pop('needs_body_processing', None)
            if 'table_properties' in result:
                result['table_properties'].pop('needs_body_processing', None)
                
        # Promote table_type from table_properties to top level if needed
        if (result.get('table_type') in [None, 'unknown'] and 
                table_props.get('table_type')):
            result['table_type'] = table_props['table_type']
            
        return result

    def _extract_select_from_ddl(self) -> str:
        """Extract SELECT statement from CREATE VIEW DDL using extracted statement."""
        # Use the pre-extracted SELECT statement if available
        if hasattr(self, '_extracted_select_statement'):
            return self._extracted_select_statement
            
        # Fallback to regex extraction from original DDL
        if not hasattr(self, '_original_ddl'):
            return ""
            
        # Match everything after AS in CREATE VIEW
        pattern = r'CREATE\s+VIEW\s+.+?\s+AS\s+(.+?)(?:$|\s*;|\s*GO)'
        match = re.search(pattern, self._original_ddl, re.IGNORECASE | re.DOTALL)
        
        if match:
            return match.group(1).strip()
        return ""

    def _extract_procedure_body_from_ddl(self) -> str:
        """Extract procedure body from CREATE PROCEDURE DDL using regex."""
        if not hasattr(self, '_original_ddl'):
            return ""
            
        # Match everything after AS in CREATE PROCEDURE
        # Try different patterns to handle various procedure formats
        patterns = [
            # Pattern 1: Procedure with BEGIN...END block
            r'CREATE\s+PROCEDURE\s+.+?\s+AS\s+(BEGIN.+?END)(?:\s*$|\s*;|\s*GO)',
            # Pattern 2: Procedure ending with END (most common)
            r'CREATE\s+PROCEDURE\s+.+?\s+AS\s+(.+?END)(?:\s*$|\s*;|\s*GO)',
            # Pattern 3: Fallback - everything after AS until end/GO
            r'CREATE\s+PROCEDURE\s+.+?\s+AS\s+(.+?)(?:\s*$|\s*GO)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self._original_ddl, re.IGNORECASE | re.DOTALL)
            if match:
                body = match.group(1).strip()
                if len(body) > 10:  # Make sure we got a meaningful body
                    return body
        
        return ""
    
    def _extract_view_metadata(self, select_statement: str) -> Dict[str, Any]:
        """
        Extract columns and referenced tables from SELECT statement using sqlparse.
        
        Args:
            select_statement: The SELECT statement text
            
        Returns:
            Dictionary with columns, referenced_tables, and operation_type
        """
        metadata: Dict[str, Any] = {
            'columns': [],
            'referenced_tables': [],
            'operation_type': 'SELECT'  # Views are always SELECT operations
        }
        
        if not sqlparse:
            # Fallback to regex-based extraction if sqlparse not available
            return self._simple_regex_extraction(select_statement)
        
        try:
            # Parse the SELECT statement
            parsed = sqlparse.parse(select_statement)
            if not parsed:
                return metadata
            
            statement = parsed[0]
            
            # Extract table references
            tables = self._extract_tables_from_statement(statement)
            metadata['referenced_tables'] = tables
            
            # Extract column references (simplified)
            columns = self._extract_columns_from_statement(statement)
            metadata['columns'] = columns
            
        except (ImportError, AttributeError, ValueError) as e:
            self.logger.warning("Failed to parse SELECT statement with sqlparse: %s", str(e))
            # Fallback to regex extraction
            return self._simple_regex_extraction(select_statement)
        
        return metadata
    
    def _extract_tables_from_statement(self, statement: Any) -> List[str]:
        """Extract table names from sqlparse statement with improved SQL Server support."""
        tables: List[str] = []
        tokens_list = list(statement.flatten())
        
        # Look for FROM and JOIN keywords, then extract table names that follow
        for i, token in enumerate(tokens_list):
            if (token.ttype in sqlparse.tokens.Keyword and 
                    token.value.upper() in ('FROM', 'JOIN')):
                
                # Look ahead for table name
                j = i + 1
                schema_part = None
                table_part = None
                
                while j < len(tokens_list):
                    next_token = tokens_list[j]
                    
                    # Skip whitespace and WITH clauses
                    if (next_token.ttype in (sqlparse.tokens.Whitespace, sqlparse.tokens.Punctuation) or
                            (next_token.ttype in sqlparse.tokens.Keyword and next_token.value.upper() == 'WITH')):
                        j += 1
                        continue
                    
                    # Skip WITH clause content in parentheses
                    if next_token.value == '(':
                        paren_count = 1
                        j += 1
                        while j < len(tokens_list) and paren_count > 0:
                            if tokens_list[j].value == '(':
                                paren_count += 1
                            elif tokens_list[j].value == ')':
                                paren_count -= 1
                            j += 1
                        continue
                    
                    # Found a name token
                    if next_token.ttype is sqlparse.tokens.Name:
                        name = next_token.value.strip('[]')
                        
                        # Filter out SQL keywords and very short names
                        if (name.upper() not in ('WITH', 'NOLOCK', 'AS', 'ON', 'SELECT', 'FROM', 'WHERE', 'ORDER', 'BY') and
                                len(name) > 1 and 
                                re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name)):
                            
                            if not schema_part:
                                schema_part = name
                            elif not table_part:
                                table_part = name
                                # We have schema.table
                                tables.append(f"{schema_part}.{table_part}")
                                break
                            else:
                                # Single table name case
                                tables.append(schema_part)
                                break
                    
                    # Handle dot separator
                    elif next_token.value == '.':
                        j += 1
                        continue
                    
                    # Break on keywords or other significant tokens
                    elif (next_token.ttype in sqlparse.tokens.Keyword or
                          next_token.value.upper() in ('WHERE', 'ORDER', 'GROUP', 'HAVING')):
                        # Add single table name if we only found one part
                        if schema_part and not table_part:
                            tables.append(schema_part)
                        break
                    
                    j += 1
                
                # Handle case where we reached end of tokens
                if schema_part and not table_part:
                    tables.append(schema_part)
        
        # Remove duplicates and filter out obvious non-table names
        filtered_tables = []
        for table in set(tables):
            # Additional filtering to remove false positives
            if (len(table) > 2 and 
                    not table.upper() in ('TOP', 'PERCENT', 'MAX', 'MIN', 'SUM', 'COUNT', 'AVG', 'ID', 'NAME') and
                    '(' not in table):
                filtered_tables.append(table)
        
        return sorted(filtered_tables)
    
    def _extract_columns_from_statement(self, statement: Any) -> List[Dict[str, Any]]:
        """Extract column information from sqlparse statement with improved filtering."""
        columns: List[Dict[str, Any]] = []
        tokens_list = list(statement.flatten())
        
        # Find the SELECT clause and extract columns until FROM
        in_select_clause = False
        select_depth = 0
        
        for i, token in enumerate(tokens_list):
            # Track when we enter SELECT clause - handle both Keyword.DML and Keyword
            if (token.ttype in sqlparse.tokens.Keyword and token.value.upper() == 'SELECT'):
                in_select_clause = True
                continue
            
            # Exit SELECT clause when we hit FROM at the same nesting level
            elif (token.ttype in sqlparse.tokens.Keyword and token.value.upper() == 'FROM' and select_depth == 0):
                in_select_clause = False
                break
            
            # Track parentheses depth for subqueries
            elif token.value == '(':
                select_depth += 1
                continue
            elif token.value == ')':
                select_depth -= 1
                continue
            
            # Skip TOP and PERCENT keywords
            elif (token.ttype in sqlparse.tokens.Keyword and 
                  token.value.upper() in ('TOP', 'PERCENT', 'DISTINCT', 'ALL')):
                continue
            
            # Skip numbers (like TOP 100)
            elif token.ttype in (sqlparse.tokens.Number, sqlparse.tokens.Number.Integer):
                continue
            
            # Extract column names from SELECT clause
            elif in_select_clause and token.ttype is sqlparse.tokens.Name:
                col_name = token.value.strip('[]')
                
                # Filter out SQL keywords and extract meaningful column names
                if (col_name and 
                        len(col_name) > 1 and
                        col_name.upper() not in ('SELECT', 'FROM', 'WHERE', 'JOIN', 'ON', 'AS', 'WITH', 'NOLOCK', 
                                               'ORDER', 'BY', 'GROUP', 'HAVING', 'TOP', 'PERCENT', 'DISTINCT', 'ALL',
                                               'MAX', 'MIN', 'SUM', 'COUNT', 'AVG', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END') and
                        re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', col_name)):
                    
                    # Check if this looks like a column name (not a table alias)
                    # Look ahead to see if there's a dot (indicating table.column)
                    is_column_name = True
                    if i + 1 < len(tokens_list) and tokens_list[i + 1].value == '.':
                        # This is a table/schema name, not a column
                        is_column_name = False
                    elif i > 0 and tokens_list[i - 1].value == '.':
                        # This follows a dot, so it's likely a column name
                        is_column_name = True
                    elif col_name.upper() in ('ID', 'NAME', 'TYPE', 'VALUE', 'CODE', 'STATUS', 'DATE', 'TIME'):
                        # Common column names
                        is_column_name = True
                    
                    if is_column_name:
                        # Check for duplicates
                        existing_names = [col['name'] for col in columns]
                        if col_name not in existing_names:
                            columns.append({
                                'name': col_name,
                                'type': 'UNKNOWN',
                                'nullable': True,
                                'primary_key': False,  # Views don't have primary keys
                                'unique': False,
                                'autoincrement': False,
                                'check': None,
                                'default': None,
                                'references': None
                            })
        
        # Limit to reasonable number and sort
        return sorted(columns[:20], key=lambda x: x['name'])
    
    def _simple_regex_extraction(self, select_statement: str) -> Dict[str, Any]:
        """
        Fallback regex-based extraction when sqlparse is not available.
        
        Args:
            select_statement: The SELECT statement text
            
        Returns:
            Dictionary with basic columns and tables information
        """
        metadata: Dict[str, Any] = {
            'columns': [],
            'referenced_tables': []
        }
        
        # Extract table names from FROM and JOIN clauses with better patterns
        # Pattern to match: FROM/JOIN [schema].[table] alias or FROM/JOIN table alias
        table_pattern = r'(?:FROM|JOIN)\s+(?:\[?([a-zA-Z_][a-zA-Z0-9_]*)\]?\.)?\[?([a-zA-Z_][a-zA-Z0-9_]*)\]?(?:\s+(?:AS\s+)?([a-zA-Z_][a-zA-Z0-9_]*))?\s*(?:WITH\s*\([^)]*\))?'
        table_matches = re.findall(table_pattern, select_statement, re.IGNORECASE)
        
        for match in table_matches:
            schema, table, alias = match
            if schema and table:
                metadata['referenced_tables'].append(f"{schema}.{table}")
            elif table:
                metadata['referenced_tables'].append(table)
        
        # Extract column names more accurately from SELECT clause
        # Find the SELECT clause up to FROM
        select_pattern = r'SELECT\s+(?:TOP\s+\d+\s+(?:PERCENT\s+)?)?(.+?)\s+FROM'
        select_match = re.search(select_pattern, select_statement, re.IGNORECASE | re.DOTALL)
        
        if select_match:
            columns_text = select_match.group(1)
            # Split by comma, but be careful of commas inside functions
            column_parts = self._split_columns_carefully(columns_text)
            
            for col in column_parts[:20]:  # Limit to first 20 columns
                col = col.strip()
                if not col:
                    continue
                    
                # Extract column name from various patterns:
                # table.column, [table].[column], column AS alias, etc.
                col_name = self._extract_column_name(col)
                
                if col_name and col_name.upper() not in ('SELECT', 'FROM', 'WHERE', 'JOIN', 'ON', 'AS', 'TOP', 'PERCENT'):
                    metadata['columns'].append({
                        'name': col_name,
                        'type': 'UNKNOWN',
                        'nullable': True,
                        'primary_key': False,  # Views don't have primary keys
                        'unique': False,
                        'autoincrement': False,
                        'check': None,
                        'default': None,
                        'references': None
                    })
        
        # Remove duplicates
        metadata['referenced_tables'] = list(set(metadata['referenced_tables']))
        
        return metadata
    
    def _split_columns_carefully(self, columns_text: str) -> List[str]:
        """Split column list by commas, respecting parentheses and brackets."""
        parts = []
        current_part = ""
        paren_depth = 0
        bracket_depth = 0
        
        for char in columns_text:
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            elif char == '[':
                bracket_depth += 1
            elif char == ']':
                bracket_depth -= 1
            elif char == ',' and paren_depth == 0 and bracket_depth == 0:
                parts.append(current_part.strip())
                current_part = ""
                continue
                
            current_part += char
            
        if current_part.strip():
            parts.append(current_part.strip())
            
        return parts
    
    def _extract_column_name(self, column_expr: str) -> str:
        """Extract the actual column name from a column expression."""
        column_expr = column_expr.strip()
        
        # Handle AS alias: "expression AS alias" -> use alias
        as_match = re.search(r'\s+AS\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*$', column_expr, re.IGNORECASE)
        if as_match:
            return as_match.group(1)
        
        # Handle qualified names: [table].[column] or table.column
        qualified_match = re.search(r'(?:\[?[a-zA-Z_][a-zA-Z0-9_]*\]?\.)?\[?([a-zA-Z_][a-zA-Z0-9_]*)\]?\s*$', column_expr)
        if qualified_match:
            return qualified_match.group(1)
        
        # Handle space-separated alias: "expression alias" -> use alias (last word)
        words = column_expr.split()
        if len(words) > 1:
            last_word = words[-1]
            # Check if last word looks like a column name (not a function or keyword)
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', last_word):
                return last_word
        
        # Fallback: try to extract any identifier-like string
        identifier_match = re.search(r'\[?([a-zA-Z_][a-zA-Z0-9_]*)\]?', column_expr)
        if identifier_match:
            return identifier_match.group(1)
            
        return ""
    
    def parse_enhanced_ddl(self, ddl_content: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse DDL content with enhanced support for views and procedures.
        
        Args:
            ddl_content: The DDL content to parse
            
        Returns:
            Dictionary with categorized database objects
        """
        # Parse using the enhanced parser
        results = self.run()
        
        # Categorize results by type
        categorized_results: Dict[str, List[Dict[str, Any]]] = {
            'tables': [],
            'views': [],
            'procedures': [],
            'functions': []
        }
        
        for result in results:
            table_type = result.get('table_type', '').lower()
            if table_type == 'view':
                categorized_results['views'].append(result)
            elif table_type == 'procedure':
                categorized_results['procedures'].append(result)
            elif table_type == 'function':
                categorized_results['functions'].append(result)
            else:
                # Regular table or other DDL
                categorized_results['tables'].append(result)
        
        return categorized_results

    def _extract_procedure_metadata(self, procedure_body: str) -> Dict[str, Any]:
        """
        Extract operation type and referenced tables from procedure body.
        
        Args:
            procedure_body: The stored procedure body content
            
        Returns:
            Dictionary with operation_type and referenced_tables
        """
        metadata: Dict[str, Any] = {
            'operation_type': 'READ',  # Default to READ
            'referenced_tables': []
        }
        
        if not procedure_body:
            return metadata
            
        # Convert to uppercase for keyword detection
        upper_body = procedure_body.upper()
        
        # Detect operation types based on SQL keywords
        has_select = 'SELECT' in upper_body
        has_insert = 'INSERT' in upper_body or 'INSERT INTO' in upper_body
        has_update = 'UPDATE' in upper_body
        has_delete = 'DELETE' in upper_body or 'DELETE FROM' in upper_body
        
        # Determine operation type
        # write_operations = [has_insert, has_update, has_delete]
        
        if has_insert:
            metadata['operation_type'] = 'INSERT'
        if has_update:
            metadata['operation_type'] = 'UPDATE'
        if has_delete:
            metadata['operation_type'] = 'DELETE'
        # if any(write_operations) and has_select:
        #     metadata['operation_type'] = 'MIXED'  # Both read and write
        # elif any(write_operations):
        #     metadata['operation_type'] = 'WRITE'  # Only write operations
        elif has_select:
            metadata['operation_type'] = 'SELECT'   # Only read operations
        # else:
        #     metadata['operation_type'] = 'OTHER'  # No clear SQL operations
            
        # Extract referenced tables using regex patterns
        # This is a simplified extraction - could be enhanced with sqlparse
        
        # Pattern for FROM and JOIN clauses
        table_patterns = [
            r'FROM\s+(?:\[?([a-zA-Z_][a-zA-Z0-9_]*)\]?\.)?\[?([a-zA-Z_][a-zA-Z0-9_]*)\]?',
            r'JOIN\s+(?:\[?([a-zA-Z_][a-zA-Z0-9_]*)\]?\.)?\[?([a-zA-Z_][a-zA-Z0-9_]*)\]?',
            r'INSERT\s+INTO\s+(?:\[?([a-zA-Z_][a-zA-Z0-9_]*)\]?\.)?\[?([a-zA-Z_][a-zA-Z0-9_]*)\]?',
            r'UPDATE\s+(?:\[?([a-zA-Z_][a-zA-Z0-9_]*)\]?\.)?\[?([a-zA-Z_][a-zA-Z0-9_]*)\]?',
            r'DELETE\s+FROM\s+(?:\[?([a-zA-Z_][a-zA-Z0-9_]*)\]?\.)?\[?([a-zA-Z_][a-zA-Z0-9_]*)\]?'
        ]
        
        tables = []
        for pattern in table_patterns:
            matches = re.finditer(pattern, procedure_body, re.IGNORECASE)
            for match in matches:
                schema = match.group(1) if match.group(1) else None
                table = match.group(2) if match.group(2) else None
                
                if table and len(table) > 2:  # Filter out very short names
                    if schema:
                        tables.append(f"{schema}.{table}")
                    else:
                        tables.append(table)
        
        # Remove duplicates and filter
        filtered_tables = []
        for table in set(tables):
            # Filter out SQL keywords and obvious non-table names
            if (table.upper() not in ('TOP', 'PERCENT', 'SET', 'WITH', 'AS', 'ON', 'WHERE') and
                    '(' not in table and len(table) > 2):
                filtered_tables.append(table)
        
        metadata['referenced_tables'] = sorted(filtered_tables)
        return metadata


# Utility functions for external use
def parse_ddl_string(ddl_content: str, **kwargs: Any) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parse DDL content with enhanced support for views and procedures.
    
    Args:
        ddl_content: The DDL content to parse
        
    Returns:
        Dictionary with categorized database objects
    """
    parser = EnhancedDDLParser(ddl_content, **kwargs)
    return parser.parse_enhanced_ddl(ddl_content)


def parse_ddl_file(file_path: str, **kwargs: Any) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parse a DDL file with enhanced support for views and procedures.
    
    Args:
        file_path: Path to the DDL file
        
    Returns:
        Dictionary with categorized database objects
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return parse_ddl_string(content, **kwargs) 
