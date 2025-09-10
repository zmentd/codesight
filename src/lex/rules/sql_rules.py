"""SQL language detection rules and patterns."""

import re
from typing import Any, Dict, List, Tuple, Union


class SqlDetectionRules:
    """
    SQL language detection rules for identifying SQL files
    and SQL dialects (MySQL, PostgreSQL, Oracle, SQL Server).
    """
    
    @staticmethod
    def get_file_extensions() -> List[str]:
        """Get SQL-related file extensions."""
        return ['.sql', '.ddl', '.dml', '.plsql', '.psql', '.mysql']
    
    @staticmethod
    def get_sql_keywords() -> List[str]:
        """Get SQL language keywords."""
        return [
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP',
            'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'FULL', 'OUTER',
            'ON', 'GROUP', 'BY', 'ORDER', 'HAVING', 'UNION', 'INTERSECT', 'EXCEPT',
            'TABLE', 'VIEW', 'INDEX', 'TRIGGER', 'PROCEDURE', 'FUNCTION',
            'DATABASE', 'SCHEMA', 'CONSTRAINT', 'PRIMARY', 'FOREIGN', 'KEY',
            'UNIQUE', 'NOT', 'NULL', 'DEFAULT', 'CHECK', 'REFERENCES',
            'AND', 'OR', 'IN', 'EXISTS', 'BETWEEN', 'LIKE', 'IS',
            'AS', 'DISTINCT', 'ALL', 'ANY', 'SOME', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
            'BEGIN', 'COMMIT', 'ROLLBACK', 'TRANSACTION', 'SAVEPOINT',
            'GRANT', 'REVOKE', 'DENY', 'EXECUTE', 'EXEC',
            'DECLARE', 'SET', 'IF', 'WHILE', 'FOR', 'LOOP', 'CURSOR',
            'OPEN', 'CLOSE', 'FETCH', 'RETURN'
        ]
    
    @staticmethod
    def get_detection_patterns() -> List[Tuple[str, int]]:
        """Get regex patterns for SQL detection with weights."""
        return [
            # Basic SQL statements
            (r'\bSELECT\s+.*?\bFROM\b', 20),
            (r'\bINSERT\s+INTO\s+\w+', 18),
            (r'\bUPDATE\s+\w+\s+SET\b', 18),
            (r'\bDELETE\s+FROM\s+\w+', 18),
            
            # DDL statements
            (r'\bCREATE\s+TABLE\s+\w+', 20),
            (r'\bCREATE\s+VIEW\s+\w+', 15),
            (r'\bCREATE\s+INDEX\s+\w+', 15),
            (r'\bCREATE\s+PROCEDURE\s+\w+', 15),
            (r'\bCREATE\s+FUNCTION\s+\w+', 15),
            (r'\bCREATE\s+TRIGGER\s+\w+', 12),
            (r'\bCREATE\s+DATABASE\s+\w+', 15),
            (r'\bCREATE\s+SCHEMA\s+\w+', 12),
            
            (r'\bALTER\s+TABLE\s+\w+', 15),
            (r'\bDROP\s+TABLE\s+\w+', 12),
            (r'\bDROP\s+VIEW\s+\w+', 10),
            (r'\bDROP\s+INDEX\s+\w+', 10),
            
            # Joins
            (r'\bJOIN\s+\w+\s+ON\b', 15),
            (r'\bINNER\s+JOIN\b', 12),
            (r'\bLEFT\s+JOIN\b', 12),
            (r'\bRIGHT\s+JOIN\b', 10),
            (r'\bFULL\s+OUTER\s+JOIN\b', 10),
            
            # Clauses
            (r'\bWHERE\s+\w+', 10),
            (r'\bGROUP\s+BY\s+\w+', 10),
            (r'\bORDER\s+BY\s+\w+', 10),
            (r'\bHAVING\s+\w+', 8),
            (r'\bUNION\s+SELECT\b', 12),
            
            # Constraints
            (r'\bPRIMARY\s+KEY\b', 12),
            (r'\bFOREIGN\s+KEY\b', 12),
            (r'\bUNIQUE\s+KEY\b', 8),
            (r'\bCHECK\s+CONSTRAINT\b', 8),
            (r'\bNOT\s+NULL\b', 6),
            
            # Functions and aggregates
            (r'\bCOUNT\s*\(', 8),
            (r'\bSUM\s*\(', 8),
            (r'\bAVG\s*\(', 8),
            (r'\bMAX\s*\(', 6),
            (r'\bMIN\s*\(', 6),
            (r'\bCOALESCE\s*\(', 6),
            (r'\bCONCAT\s*\(', 6),
            
            # Subqueries
            (r'\(\s*SELECT\s+', 10),
            (r'\bEXISTS\s*\(\s*SELECT\b', 8),
            (r'\bIN\s*\(\s*SELECT\b', 8),
            
            # Comments
            (r'--\s+.*', 3),
            (r'/\*.*?\*/', 3)
        ]
    
    @staticmethod
    def get_mysql_indicators() -> List[Tuple[str, int]]:
        """Get patterns specific to MySQL."""
        return [
            # MySQL-specific syntax
            (r'\bENGINE\s*=\s*InnoDB\b', 15),
            (r'\bENGINE\s*=\s*MyISAM\b', 12),
            (r'\bAUTO_INCREMENT\b', 15),
            (r'\bCHARSET\s*=\s*utf8\b', 10),
            (r'\bCOLLATE\s*=\s*utf8_', 8),
            
            # MySQL data types
            (r'\bTINYINT\b|\bSMALLINT\b|\bMEDIUMINT\b|\bBIGINT\b', 8),
            (r'\bTINYTEXT\b|\bMEDIUMTEXT\b|\bLONGTEXT\b', 8),
            (r'\bTINYBLOB\b|\bMEDIUMBLOB\b|\bLONGBLOB\b', 6),
            (r'\bENUM\s*\(', 8),
            (r'\bSET\s*\(', 6),
            
            # MySQL functions
            (r'\bCONCAT\s*\(', 6),
            (r'\bIF\s*\(', 6),
            (r'\bIFNULL\s*\(', 6),
            (r'\bDATE_FORMAT\s*\(', 8),
            (r'\bSTR_TO_DATE\s*\(', 8),
            (r'\bLIMIT\s+\d+', 10),
            (r'\bLIMIT\s+\d+\s*,\s*\d+', 12),
            
            # MySQL-specific keywords
            (r'\bSHOW\s+TABLES\b', 8),
            (r'\bSHOW\s+DATABASES\b', 8),
            (r'\bDESCRIBE\s+\w+\b', 6),
            (r'\bEXPLAIN\s+SELECT\b', 6)
        ]
    
    @staticmethod
    def get_postgresql_indicators() -> List[Tuple[str, int]]:
        """Get patterns specific to PostgreSQL."""
        return [
            # PostgreSQL-specific syntax
            (r'\bSERIAL\b|\bBIGSERIAL\b', 15),
            (r'\bBOOLEAN\b', 8),
            (r'\bARRAY\[', 10),
            (r'\bJSONB\b|\bJSON\b', 12),
            (r'\bUUID\b', 8),
            
            # PostgreSQL functions
            (r'\bGENERATE_SERIES\s*\(', 10),
            (r'\bCOALESCE\s*\(', 6),
            (r'\bNULLIF\s*\(', 6),
            (r'\bEXTRACT\s*\(', 8),
            (r'\bDATE_TRUNC\s*\(', 8),
            (r'\bREGEXP_REPLACE\s*\(', 8),
            
            # PostgreSQL-specific operators
            (r'\|\|', 6),  # String concatenation
            (r'@>', 6),    # Contains operator
            (r'<@', 6),    # Contained by operator
            (r'->', 8),    # JSON operator
            (r'->>', 8),   # JSON text operator
            
            # PostgreSQL commands
            (r'\\\w+', 8),  # psql commands like \dt, \d+
            (r'\bCOPY\s+\w+\s+FROM\b', 10),
            (r'\bCOPY\s+\w+\s+TO\b', 10),
            
            # Advanced features
            (r'\bWITH\s+RECURSIVE\b', 12),
            (r'\bWINDOW\s+\w+\s+AS\b', 10),
            (r'\bOVER\s*\(', 8)
        ]
    
    @staticmethod
    def get_oracle_indicators() -> List[Tuple[str, int]]:
        """Get patterns specific to Oracle."""
        return [
            # Oracle-specific data types
            (r'\bVARCHAR2\b', 15),
            (r'\bNVARCHAR2\b', 12),
            (r'\bNUMBER\s*\(', 15),
            (r'\bDATE\b', 6),
            (r'\bTIMESTAMP\b', 8),
            (r'\bCLOB\b|\bBLOB\b|\bNCLOB\b', 10),
            (r'\bRAW\b|\bLONG\s+RAW\b', 8),
            
            # Oracle functions
            (r'\bNVL\s*\(', 15),
            (r'\bNVL2\s*\(', 12),
            (r'\bDECODE\s*\(', 12),
            (r'\bROWNUM\b', 15),
            (r'\bROWID\b', 10),
            (r'\bSYSDATE\b', 12),
            (r'\bTO_DATE\s*\(', 10),
            (r'\bTO_CHAR\s*\(', 8),
            (r'\bTO_NUMBER\s*\(', 8),
            
            # Oracle-specific syntax
            (r'\bCONNECT\s+BY\b', 15),
            (r'\bSTART\s+WITH\b', 12),
            (r'\bPRIOR\s+\w+', 10),
            (r'\bDUAL\b', 15),
            (r'\bSEQUENCE\s+\w+', 12),
            (r'\.NEXTVAL\b', 12),
            (r'\.CURRVAL\b', 10),
            
            # PL/SQL
            (r'\bPL/SQL\b', 15),
            (r'\bPROCEDURE\s+\w+\s+IS\b', 15),
            (r'\bFUNCTION\s+\w+\s+RETURN\b', 15),
            (r'\bPACKAGE\s+\w+\s+IS\b', 12),
            (r'\bPACKAGE\s+BODY\s+\w+\s+IS\b', 15),
            (r'\bEXCEPTION\s+WHEN\b', 10),
            (r'\bRAISE_APPLICATION_ERROR\s*\(', 10)
        ]
    
    @staticmethod
    def get_sqlserver_indicators() -> List[Tuple[str, int]]:
        """Get patterns specific to SQL Server."""
        return [
            # SQL Server-specific data types
            (r'\bNVARCHAR\s*\(', 15),
            (r'\bNTEXT\b', 10),
            (r'\bUNIQUEIDENTIFIER\b', 15),
            (r'\bMONEY\b|\bSMALLMONEY\b', 10),
            (r'\bDATETIME2\b|\bDATETIMEOFFSET\b', 12),
            (r'\bIMAGE\b', 6),
            
            # SQL Server functions
            (r'\bISNULL\s*\(', 15),
            (r'\bCOALESCE\s*\(', 8),
            (r'\bGETDATE\s*\(\)', 15),
            (r'\bGETUTCDATE\s*\(\)', 12),
            (r'\bDATEADD\s*\(', 12),
            (r'\bDATEDIFF\s*\(', 12),
            (r'\bPATINDEX\s*\(', 8),
            (r'\bCHARINDEX\s*\(', 8),
            (r'\bLEN\s*\(', 6),
            (r'\bSTUFF\s*\(', 6),
            
            # SQL Server-specific syntax
            (r'\bIDENTITY\s*\(', 15),
            (r'\bSET\s+IDENTITY_INSERT\b', 12),
            (r'\bSET\s+NOCOUNT\s+ON\b', 10),
            (r'\bRAISERROR\s*\(', 10),
            (r'\bTHROW\s+\d+', 8),
            (r'\bGO\s*$', 15),
            (r'\bTOP\s+\d+\b', 12),
            
            # T-SQL
            (r'\bT-SQL\b', 12),
            (r'\bPRINT\s+', 8),
            (r'\bIF\s+@@', 10),
            (r'\b@@ROWCOUNT\b|\b@@ERROR\b|\b@@IDENTITY\b', 10),
            (r'\bWHILE\s+@@', 8),
            (r'\bBREAK\b|\bCONTINUE\b', 6)
        ]
    
    @staticmethod
    def detect_sql_dialect(content: str) -> Dict[str, Any]:
        """Detect SQL dialect based on content patterns."""
        dialects = {
            'mysql': 0,
            'postgresql': 0,
            'oracle': 0,
            'sqlserver': 0
        }
        
        # Score each dialect
        for pattern, weight in SqlDetectionRules.get_mysql_indicators():
            matches = len(re.findall(pattern, content, re.IGNORECASE))
            dialects['mysql'] += matches * weight
        
        for pattern, weight in SqlDetectionRules.get_postgresql_indicators():
            matches = len(re.findall(pattern, content, re.IGNORECASE))
            dialects['postgresql'] += matches * weight
        
        for pattern, weight in SqlDetectionRules.get_oracle_indicators():
            matches = len(re.findall(pattern, content, re.IGNORECASE))
            dialects['oracle'] += matches * weight
        
        for pattern, weight in SqlDetectionRules.get_sqlserver_indicators():
            matches = len(re.findall(pattern, content, re.IGNORECASE))
            dialects['sqlserver'] += matches * weight
        
        # Find best match
        best_dialect = max(dialects.keys(), key=lambda k: dialects[k])
        best_score = dialects[best_dialect]
        
        return {
            'detected_dialect': best_dialect if best_score > 0 else None,
            'confidence': min(best_score / 100, 1.0),  # Normalize to 0-1
            'scores': dialects
        }
    
    @staticmethod
    def classify_sql_statement_type(statement: str) -> str:
        """Classify the type of SQL statement."""
        statement_upper = statement.strip().upper()
        
        if statement_upper.startswith('SELECT'):
            return 'SELECT'
        elif statement_upper.startswith('INSERT'):
            return 'INSERT'
        elif statement_upper.startswith('UPDATE'):
            return 'UPDATE'
        elif statement_upper.startswith('DELETE'):
            return 'DELETE'
        elif statement_upper.startswith('CREATE TABLE'):
            return 'CREATE_TABLE'
        elif statement_upper.startswith('CREATE VIEW'):
            return 'CREATE_VIEW'
        elif statement_upper.startswith('CREATE INDEX'):
            return 'CREATE_INDEX'
        elif statement_upper.startswith('CREATE PROCEDURE'):
            return 'CREATE_PROCEDURE'
        elif statement_upper.startswith('CREATE FUNCTION'):
            return 'CREATE_FUNCTION'
        elif statement_upper.startswith('CREATE'):
            return 'CREATE_OTHER'
        elif statement_upper.startswith('ALTER'):
            return 'ALTER'
        elif statement_upper.startswith('DROP'):
            return 'DROP'
        elif statement_upper.startswith('GRANT'):
            return 'GRANT'
        elif statement_upper.startswith('REVOKE'):
            return 'REVOKE'
        elif statement_upper.startswith('COMMIT'):
            return 'COMMIT'
        elif statement_upper.startswith('ROLLBACK'):
            return 'ROLLBACK'
        elif statement_upper.startswith('--') or statement_upper.startswith('/*'):
            return 'COMMENT'
        else:
            return 'OTHER'
    
    @staticmethod
    def extract_table_names(content: str) -> List[str]:
        """Extract table names from SQL content."""
        table_names = set()
        
        # FROM clauses
        from_matches = re.findall(r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_.]*)', content, re.IGNORECASE)
        table_names.update(from_matches)
        
        # JOIN clauses
        join_matches = re.findall(r'\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_.]*)', content, re.IGNORECASE)
        table_names.update(join_matches)
        
        # INSERT INTO
        insert_matches = re.findall(r'\bINSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_.]*)', content, re.IGNORECASE)
        table_names.update(insert_matches)
        
        # UPDATE
        update_matches = re.findall(r'\bUPDATE\s+([a-zA-Z_][a-zA-Z0-9_.]*)', content, re.IGNORECASE)
        table_names.update(update_matches)
        
        # DELETE FROM
        delete_matches = re.findall(r'\bDELETE\s+FROM\s+([a-zA-Z_][a-zA-Z0-9_.]*)', content, re.IGNORECASE)
        table_names.update(delete_matches)
        
        # CREATE TABLE
        create_matches = re.findall(r'\bCREATE\s+TABLE\s+([a-zA-Z_][a-zA-Z0-9_.]*)', content, re.IGNORECASE)
        table_names.update(create_matches)
        
        # ALTER TABLE
        alter_matches = re.findall(r'\bALTER\s+TABLE\s+([a-zA-Z_][a-zA-Z0-9_.]*)', content, re.IGNORECASE)
        table_names.update(alter_matches)
        
        # DROP TABLE
        drop_matches = re.findall(r'\bDROP\s+TABLE\s+([a-zA-Z_][a-zA-Z0-9_.]*)', content, re.IGNORECASE)
        table_names.update(drop_matches)
        
        return list(table_names)
    
    @staticmethod
    def extract_column_names(content: str) -> List[str]:
        """Extract column names from SQL content."""
        column_names = set()
        
        # SELECT columns (basic extraction)
        select_pattern = r'\bSELECT\s+(.*?)\s+FROM\b'
        select_matches = re.findall(select_pattern, content, re.IGNORECASE | re.DOTALL)
        
        for match in select_matches:
            # Split by comma and clean up
            columns = [col.strip() for col in match.split(',')]
            for col in columns:
                # Extract column name (ignore aliases, functions, etc.)
                col_match = re.match(r'([a-zA-Z_][a-zA-Z0-9_.]*)', col)
                if col_match and col_match.group(1).upper() not in ['DISTINCT', 'ALL']:
                    column_names.add(col_match.group(1))
        
        return list(column_names)
    
    @staticmethod
    def detect_sql_complexity(content: str) -> Dict[str, Union[int, str]]:
        """Detect SQL complexity indicators."""
        complexity: Dict[str, Union[int, str]] = {
            'subquery_count': 0,
            'join_count': 0,
            'union_count': 0,
            'case_statement_count': 0,
            'window_function_count': 0,
            'cte_count': 0,
            'complexity_level': 'simple'
        }
        
        # Count various complexity indicators
        complexity['subquery_count'] = len(re.findall(r'\(\s*SELECT\b', content, re.IGNORECASE))
        complexity['join_count'] = len(re.findall(r'\bJOIN\b', content, re.IGNORECASE))
        complexity['union_count'] = len(re.findall(r'\bUNION\b', content, re.IGNORECASE))
        complexity['case_statement_count'] = len(re.findall(r'\bCASE\s+WHEN\b', content, re.IGNORECASE))
        complexity['window_function_count'] = len(re.findall(r'\bOVER\s*\(', content, re.IGNORECASE))
        complexity['cte_count'] = len(re.findall(r'\bWITH\s+\w+\s+AS\b', content, re.IGNORECASE))
        
        # Calculate complexity level
        subquery_count = complexity['subquery_count']
        join_count = complexity['join_count']
        union_count = complexity['union_count']
        case_count = complexity['case_statement_count']
        window_count = complexity['window_function_count']
        cte_count = complexity['cte_count']
        
        # Type assertions for mypy
        assert isinstance(subquery_count, int)
        assert isinstance(join_count, int)
        assert isinstance(union_count, int)
        assert isinstance(case_count, int)
        assert isinstance(window_count, int)
        assert isinstance(cte_count, int)
        
        total_complexity = (
            subquery_count * 2 +
            join_count +
            union_count * 2 +
            case_count +
            window_count * 3 +
            cte_count * 2
        )
        
        if total_complexity == 0:
            complexity['complexity_level'] = 'simple'
        elif total_complexity <= 5:
            complexity['complexity_level'] = 'moderate'
        elif total_complexity <= 15:
            complexity['complexity_level'] = 'complex'
        else:
            complexity['complexity_level'] = 'very_complex'
        
        return complexity
