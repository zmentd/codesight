from typing import Any, Dict, List, Optional

import sqlparse  # type: ignore
from sqlparse import tokens

from config import Config
from domain.sql_details import DatabaseObjectType, SqlOperationType, SQLStatement
from utils.logging.logger_factory import LoggerFactory


class SQLStatementAnalyzer:
    """Analyze individual SQL statements using sqlparse."""
    
    def __init__(self) -> None:
        self.logger = LoggerFactory.get_logger('SQLStatementAnalyzer')
        self.config = Config.get_instance()

    def analyze_statement(self, statement: str, dialect: str, logical_database: str = "unknown", line_start: int = 1, line_end: int = 1) -> Optional[SQLStatement]:
        """Analyze a single SQL statement and extract metadata."""
        try:
            parsed = sqlparse.parse(statement)[0]
            
            stmt_type = self._extract_statement_type(parsed)
            object_info = self._extract_object_info(parsed, stmt_type)
            
            return SQLStatement(
                statement_type=stmt_type,
                statement_text=statement.strip(),
                object_type=self._map_object_type_to_enum(object_info.get('type')),
                object_name=object_info.get('name'),
                schema_name=object_info.get('schema'),
                logical_database=logical_database,
                line_start=line_start,
                line_end=line_end
            )
            
        except Exception as e:  # pylint: disable=broad-except
            self.logger.warning("Failed to analyze statement: %s", str(e))
            return None
    
    def _extract_statement_type(self, parsed: Any) -> SqlOperationType:
        """Extract statement type (CREATE, ALTER, etc.)."""
        # Look for primary operation keywords first (in order of priority)
        primary_operations = ['CREATE', 'ALTER', 'DROP', 'SELECT', 'INSERT', 'UPDATE', 'DELETE']
        flattened_tokens = list(parsed.flatten())
        for operation in primary_operations:
            for token in flattened_tokens:
                if (token.ttype in (tokens.Keyword, tokens.Keyword.DDL, tokens.Keyword.DML) and 
                        token.value.upper() == operation):
                    # Map to SqlOperationType enum values
                    if operation == 'SELECT':
                        return SqlOperationType.SELECT
                    elif operation == 'INSERT':
                        return SqlOperationType.INSERT
                    elif operation == 'UPDATE':
                        return SqlOperationType.UPDATE
                    elif operation == 'DELETE':
                        return SqlOperationType.DELETE
                    elif operation == 'CREATE':
                        return SqlOperationType.CREATE
                    elif operation == 'ALTER':
                        return SqlOperationType.ALTER
                    elif operation == 'DROP':
                        return SqlOperationType.DROP
        
        # Look for SET as a fallback (for standalone SET statements)
        for token in flattened_tokens:
            if (token.ttype in (tokens.Keyword, tokens.Keyword.DDL) and 
                    token.value.upper() == 'SET'):
                return SqlOperationType.SET
        
        # Default fallback
        return SqlOperationType.SELECT
    
    def _extract_object_info(self, parsed: Any, stmt_type: SqlOperationType) -> Dict[str, Optional[str]]:
        """Extract object type and name from statement."""
        # Check raw statement text for DDL operations since SqlOperationType only has DML
        stmt_text = str(parsed).upper().strip()
        
        if any(ddl_keyword in stmt_text for ddl_keyword in ['CREATE', 'ALTER', 'DROP']):
            return self._extract_ddl_object_info(parsed)
        elif stmt_type in [SqlOperationType.SELECT, SqlOperationType.INSERT, 
                          SqlOperationType.UPDATE, SqlOperationType.DELETE]:
            return self._extract_dml_table_info(parsed)
        return {'type': None, 'name': None, 'schema': None}
    
    def _extract_ddl_object_info(self, parsed: Any) -> Dict[str, Optional[str]]:
        """Extract object information from DDL statements."""
        result: Dict[str, Optional[str]] = {'type': None, 'name': None, 'schema': None}
        
        tokens_list = list(parsed.flatten())
        
        # Find CREATE/ALTER/DROP keyword
        for i, token in enumerate(tokens_list):
            if (token.ttype in (tokens.Keyword, tokens.Keyword.DDL) and 
                    token.value.upper() in ['CREATE', 'ALTER', 'DROP']):
                # Look for object type after CREATE/ALTER/DROP
                j = i + 1
                while j < len(tokens_list):
                    next_token = tokens_list[j]
                    if next_token.ttype is tokens.Keyword:
                        object_type = next_token.value.upper()
                        if object_type in ['TABLE', 'VIEW', 'PROCEDURE', 'FUNCTION', 'INDEX', 'TRIGGER']:
                            # Look for object name first
                            name_info = self._extract_object_name(tokens_list, j + 1)
                            result.update(name_info)
                            
                            # For tables, determine if temporary or alias
                            if object_type == 'TABLE' and name_info.get('name'):
                                table_name = name_info['name']
                                if table_name:  # Ensure table_name is not None
                                    statement_text = str(parsed).upper()
                                    
                                    if self._is_temporary_table(table_name, statement_text):
                                        result['type'] = 'temp_table'
                                    elif self._is_table_alias(table_name, statement_text):
                                        result['type'] = 'table_alias'
                                    else:
                                        result['type'] = object_type.lower()
                                else:
                                    result['type'] = object_type.lower()
                            else:
                                result['type'] = object_type.lower()
                            break
                    j += 1
                break
        
        return result
    
    def _extract_dml_table_info(self, parsed: Any) -> Dict[str, Optional[str]]:
        """Extract table information from DML statements."""
        result: Dict[str, Optional[str]] = {'type': 'table', 'name': None, 'schema': None}
        
        tokens_list = list(parsed.flatten())
        
        # Find table name based on statement type
        for i, token in enumerate(tokens_list):
            if token.ttype in (tokens.Keyword, tokens.Keyword.DML, tokens.Keyword.DDL):
                keyword = token.value.upper()
                if keyword in ['FROM', 'INTO', 'UPDATE', 'DELETE']:
                    # Look for table name after these keywords
                    name_info = self._extract_object_name(tokens_list, i + 1)
                    result.update(name_info)
                    break
        
        return result
    
    def _extract_object_name(self, tokens_list: List, start_index: int) -> Dict[str, Optional[str]]:
        """Extract object name and schema from token list starting at given index."""
        result: Dict[str, Optional[str]] = {'name': None, 'schema': None}
        
        # SQL keywords and system objects to exclude
        sql_keywords = {
            'ON', 'OFF', 'INTO', 'FROM', 'WHERE', 'ORDER', 'BY', 'GROUP', 'HAVING',
            'UNION', 'JOIN', 'INNER', 'OUTER', 'LEFT', 'RIGHT', 'FULL', 'CROSS',
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP',
            'TABLE', 'VIEW', 'INDEX', 'PROCEDURE', 'FUNCTION', 'TRIGGER',
            'SET', 'DECLARE', 'IF', 'ELSE', 'WHILE', 'FOR', 'CASE', 'WHEN', 'THEN',
            'AS', 'IS', 'NOT', 'NULL', 'AND', 'OR', 'IN', 'EXISTS', 'BETWEEN',
            'LIKE', 'ALL', 'ANY', 'SOME', 'PRIMARY', 'FOREIGN', 'KEY', 'REFERENCES',
            'CHECK', 'UNIQUE', 'DEFAULT', 'IDENTITY', 'AUTOINCREMENT',
            'SYS', 'SYSCOMMENTS', 'SYSOBJECTS', 'SYSINDEXES', 'SYSTYPES',
            'OBJECTS', 'COLUMNS', 'TABLES', 'VIEWS', 'PROCEDURES', 'FUNCTIONS',
            'INFORMATION_SCHEMA', 'MASTER', 'TEMPDB', 'MODEL', 'MSDB',
            # Additional single-letter and short SQL keywords/aliases
            'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
            'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
            'TT', 'MS', 'DT', 'SP', 'FN', 'VW'
        }
        
        i = start_index
        while i < len(tokens_list):
            token = tokens_list[i]
            
            # Skip whitespace and newlines
            if token.ttype in (tokens.Whitespace, tokens.Newline, tokens.Text.Whitespace):
                i += 1
                continue
            
            # Handle bracketed identifiers [schema].[table] pattern
            if token.value.startswith('[') and token.value.endswith(']'):
                name = token.value.strip('[]')
                
                # Check if the single token contains schema.table pattern like [dbo].[Employee]
                if token.value.count('].[') == 1:
                    # Split on '].[' pattern
                    parts = token.value.split('].[')
                    if len(parts) == 2:
                        schema_name = parts[0].strip('[')
                        table_name = parts[1].strip(']')
                        # Skip if table name is a SQL keyword
                        if table_name.upper() not in sql_keywords:
                            result['schema'] = schema_name
                            result['name'] = table_name
                        break
                
                # Check if next tokens form schema.table pattern: [schema] . [table]
                if (i + 2 < len(tokens_list) and 
                        tokens_list[i + 1].ttype is tokens.Punctuation and
                        tokens_list[i + 1].value == '.' and
                        tokens_list[i + 2].value.startswith('[') and
                        tokens_list[i + 2].value.endswith(']')):
                    # This is [schema].[table] pattern with separate tokens
                    table_name = tokens_list[i + 2].value.strip('[]')
                    # Skip if table name is a SQL keyword
                    if table_name.upper() not in sql_keywords:
                        result['schema'] = name
                        result['name'] = table_name
                    break
                else:
                    # Single bracketed identifier - skip if it's a SQL keyword
                    if name.upper() not in sql_keywords:
                        result['name'] = name
                    break
            
            # Handle regular identifiers
            elif token.ttype is None or token.ttype in (tokens.Name, tokens.Keyword):
                name = token.value.strip('[]')
                
                # Skip if this is a SQL keyword
                if name.upper() in sql_keywords:
                    i += 1
                    continue
                
                # Check if single token contains schema.table pattern like dbo.Employee
                if '.' in name and not name.startswith('['):
                    parts = name.split('.', 1)  # Split only on first dot
                    if len(parts) == 2:
                        schema_name = parts[0]
                        table_name = parts[1]
                        # Skip if table name is a SQL keyword
                        if table_name.upper() not in sql_keywords:
                            result['schema'] = schema_name
                            result['name'] = table_name
                        break
                
                # Check for schema.table pattern with separate tokens
                if (i + 2 < len(tokens_list) and 
                        tokens_list[i + 1].ttype is tokens.Punctuation and
                        tokens_list[i + 1].value == '.'):
                    table_name = tokens_list[i + 2].value.strip('[]')
                    # Skip if table name is a SQL keyword
                    if table_name.upper() not in sql_keywords:
                        result['schema'] = name
                        result['name'] = table_name
                    break
                else:
                    # Single identifier - only use if not a SQL keyword
                    result['name'] = name
                    break
            
            # Skip punctuation that's not a dot
            elif token.ttype is tokens.Punctuation and token.value != '.':
                i += 1
                continue
            else:
                # Stop at unexpected tokens
                break
            
        return result
    
    def _map_object_type_to_enum(self, object_type_str: Optional[str]) -> Optional[DatabaseObjectType]:
        """Map string object type to DatabaseObjectType enum."""
        if not object_type_str:
            return None
        
        type_map = {
            'table': DatabaseObjectType.TABLE,
            'temp_table': DatabaseObjectType.TEMP_TABLE,
            'table_alias': DatabaseObjectType.TABLE_ALIAS,
            'view': DatabaseObjectType.VIEW,
            'procedure': DatabaseObjectType.PROCEDURE,
            'function': DatabaseObjectType.FUNCTION,
            'trigger': DatabaseObjectType.TRIGGER,
            'index': DatabaseObjectType.INDEX
        }
        
        return type_map.get(object_type_str.lower())
    
    def _is_temporary_table(self, table_name: str, statement_text: str) -> bool:
        """Detect temporary tables across database systems."""
        # SQL Server patterns
        if table_name.startswith('#') or table_name.startswith('@'):
            return True
        
        # Universal temporary table keywords
        temp_keywords = [
            'CREATE TEMP TABLE',
            'CREATE TEMPORARY TABLE', 
            'CREATE GLOBAL TEMPORARY',
            'DECLARE @'
        ]
        
        return any(keyword in statement_text for keyword in temp_keywords)
    
    def _is_table_alias(self, table_name: str, statement_text: str) -> bool:
        """Detect table aliases and derived tables."""
        # Single letter table names are almost always aliases
        if len(table_name) == 1:
            return True
        
        # Very short names (likely aliases) - be more aggressive
        if len(table_name) <= 2:
            # Only allow very specific 2-character table names that are legitimate
            allowed_short_names = {'ID'}  # Much more restrictive
            if table_name.upper() not in allowed_short_names:
                return True
        
        # Common system table prefixes that aren't user tables
        system_prefixes = ['ms_', 'sys', 'dt_', 'sp_', 'fn_']
        if any(table_name.lower().startswith(prefix) for prefix in system_prefixes):
            return True
        
        # Tables starting with temp patterns
        temp_patterns = ['tmp', 'temp', '#', '@']
        if any(table_name.lower().startswith(pattern) for pattern in temp_patterns):
            return True
        
        # Common alias patterns in the statement
        upper_name = table_name.upper()
        statement_upper = statement_text.upper()
        
        alias_patterns = [
            f'{upper_name} AS',
            f' {upper_name} ',  # Isolated short names in FROM clauses
            'FROM (SELECT',  # Derived table
            f'WITH {upper_name} AS ('  # CTE
        ]
        
        # Check if this appears to be used as an alias
        if any(pattern in statement_upper for pattern in alias_patterns):
            return True
        
        # If it's a very short name and appears multiple times, likely an alias
        if len(table_name) <= 3 and statement_upper.count(upper_name) > 1:
            return True
        
        return False