import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from simple_ddl_parser import DDLParser  # type: ignore

from config import Config

from .base_reader import BaseReader, ParseResult
from .enhanced_ddl_parser import EnhancedDDLParser
from .sql_dialect_detector import SQLDialectDetector


@dataclass
class DdlParseColumnInfo:
    name: str
    type: str
    size: Optional[str]
    identity: Optional[str]
    references: Optional[Dict[str, str]]
    unique: bool
    nullable: bool
    default: Optional[str]
    check: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'type': self.type,
            'size': self.size,
            'identity': self.identity,
            'references': self.references,
            'unique': self.unique,
            'nullable': self.nullable,
            'default': self.default,
            'check': self.check
        }


@dataclass
class DdlParseTableInfo:
    table_name: str
    schema_name: str
    logical_database_name: str
    columns: List[DdlParseColumnInfo] = field(default_factory=list)
    primary_key: List[str] = field(default_factory=list)
    alter: Optional[Dict[str, Any]] = None
    checks: Optional[List[Any]] = field(default_factory=list)
    index: Optional[List[Any]] = field(default_factory=list)
    partition_key: Optional[List[Any]] = field(default_factory=list)
    constraints: Optional[Dict[str, Any]] = None
    table_properties: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'table_name': self.table_name,
            'schema_name': self.schema_name,
            'logical_database_name': self.logical_database_name,
            'columns': [col.to_dict() for col in self.columns],
            'primary_key': self.primary_key,
            'alter': self.alter,
            'checks': self.checks,
            'index': self.index,
            'partition_key': self.partition_key,
            'constraints': self.constraints,
            'table_properties': self.table_properties
        }


@dataclass
class StructuredDdlData:
    dialect: str = "generic"    
    tables: List[DdlParseTableInfo] = field(default_factory=list)
    views: List[DdlParseTableInfo] = field(default_factory=list)
    procedures: List[DdlParseTableInfo] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'dialect': self.dialect,
            'tables': [table.to_dict() for table in self.tables],
            'views': [view.to_dict() for view in self.views],
            'procedures': [proc.to_dict() for proc in self.procedures],
        }


# SQL Reader following JavaReader pattern  
class SQLReader(BaseReader):
    """SQL file reader with sqlparse integration."""
    
    def __init__(self, config: Config):
        """Initialize SQL reader."""
        super().__init__(config)
        self.log_dir = Path(self.config.get_output_dir_for_step("step02")).parent.parent
        self.log_file_path = self.log_dir / "parser221.log"
        self.dialect_detector = SQLDialectDetector()

    def can_parse(self, file_info: Dict[str, Any]) -> bool:
        """Check if the reader can parse the given file."""
        return file_info.get("file_type") == "sql"

    def parse_file(self, source_path: str, file_path: str) -> ParseResult:
        result = ParseResult(True, file_path, "sql", {}, 0.0, None, 0.0, [])
        # Ensure log directory exists
        logical_database = self._determine_logical_database(source_path)

        try:
            # Read the SQL content
            content = self.read_file(source_path, file_path)
            dialect = self.dialect_detector.detect_dialect(content)
            
            # Split statements by case-insensitive 'go' and remove comments
            statements = self.split_statements(content)
            
            # Filter statements for specific database object types (e.g., procedures)
            # print(f"DEBUG: Total statements found: {len(statements)}")
            
            # 1. Parse tables using original approach (which was working)
            filtered_statements = self.filter_statements_by_type(statements, "table", normalize_name=True)
            # print(f"DEBUG: CREATE TABLE statements found: {len(filtered_statements)}")
            table_statements = self._combine_statements_by_name(filtered_statements)
            table_results = self._parse_statements(logical_database, file_path, table_statements)
            # [
            # DdlParseTableInfo(
            # table_name='ABSENCE', 
            # schema_name='dbo', 
            # logical_database_name='Storm2',
            # columns=[DdlParseColumnInfo(name='Id', type='int', size=None, identity=(1, 1), 
            # references=None, unique=False, nullable=False, default=None, check=None
            # ), 
            # DdlParseColumnInfo(name='IsDisabled', type='bit', size=None, identity=None, 
            # references=None, unique=False, nullable=False, default=None, check=None), 
            # DdlParseColumnInfo(name='ResourceId', type='int', size=None, identity=None, references=None, unique=False, nullable=False, default=None, check=None), DdlParseColumnInfo(name='StartDate', type='datetime', size=None, identity=None, references=None, unique=False, nullable=False, default=None, check=None), DdlParseColumnInfo(name='EndDate', type='datetime', size=None, identity=None, references=None, unique=False, nullable=False, default=None, check=None), DdlParseColumnInfo(name='AbsenceReason', type='varchar', size=50, identity=None, references=None, unique=False, nullable=False, default=None, check=None), DdlParseColumnInfo(name='TimeZoneId', type='int', size=None, identity=None, references=None, unique=False, nullable=False, default=None, check=None)], primary_key=['Id'], alter={}, checks=[], index=[], partition_key=[], constraints={'primary_keys': [{'columns': ['Id'], 'constraint_name': 'PK_ABSENCE'}]}, table_properties={'with': {'properties': [{'name': 'PAD_INDEX', 'value': 'OFF'}, {'name': 'STATISTICS_NORECOMPUTE', 'value': 'OFF'}, {'name': 'IGNORE_DUP_KEY', 'value': 'OFF'}, {'name': 'ALLOW_ROW_LOCKS', 'value': 'ON'}, {'name': 'ALLOW_PAGE_LOCKS', 'value': 'ON'}, {'name': 'FILLFACTOR', 'value': '90'}], 'on': None}, 'on': 'PRIMARY'})]
            
            # 2. Use enhanced DDL parser for views and procedures
            filtered_statements = self._filter_statements_by_type("CREATE", statements, "view", normalize_name=True)
            # print(f"DEBUG: CREATE VIEW statements found: {len(filtered_statements)}")
            # view_statements = self._combine_statements_by_name(filtered_statements)
            view_results = self._parse_enhanced_statements(logical_database, file_path, filtered_statements)

            filtered_statements = self._filter_statements_by_type("CREATE", statements, "procedure", normalize_name=True)
            # print(f"DEBUG: CREATE PROCEDURE statements found: {len(filtered_statements)}")
            proc_statements = self._combine_statements_by_name(filtered_statements)
            proc_results = self._parse_enhanced_statements(logical_database, file_path, proc_statements)
        except (ValueError, TypeError, AttributeError, ImportError, FileNotFoundError) as e:
            print(f"DEBUG: Exception during parsing: {e}")
            self.logger.error("Error parsing SQL file %s: %s", file_path, str(e))
            result.success = False
            result.confidence = 0.0
            return result
        
        structured = StructuredDdlData(
            dialect=dialect,
            tables=table_results,
            views=view_results,
            procedures=proc_results,
        )
        
        result.structural_data = structured.to_dict()
        
        # Set success based on whether any meaningful results were found
        has_results = any([structured.tables, structured.views, structured.procedures])
        result.success = has_results
        result.confidence = 0.9 if has_results else 0.1
        
        # print(f"DEBUG: Parse success: {result.success}, Tables: {len(structured.tables)}, Views: {len(structured.views)}, Procedures: {len(structured.procedures)}")
        # print("=== DEBUG: Finished parse_file ===")
        return result

    def _combine_statements_by_name(self, statements: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Combine multiple SQL statements by their schema and name.
        
        Args:
            statements: List of dictionaries with 'schema', 'name', and 'statement' keys
            
        Returns:
            List of dictionaries with 'schema', 'name', and 'statement' keys where statements 
            with the same schema and name are combined using "GO" as separator with newlines
        """
        combined: Dict[str, Dict[str, str]] = {}
        
        for stmt_info in statements:
            schema = stmt_info.get('schema', '')
            name = stmt_info.get('name', '')
            statement = stmt_info.get('statement', '')
            
            if not name or not statement.strip():
                continue
            
            key = f"{schema}.{name}" if schema else name
            
            if key in combined:
                # Append with GO separator and newlines
                combined[key]['statement'] += f"\nGO\n{statement}"
            else:
                combined[key] = {
                    'schema': schema,
                    'name': name,
                    'statement': statement
                }
        
        return list(combined.values())   
    
    def _parse_statements(self, database: str, file_path: str, filtered: List[Dict[str, str]]) -> List[DdlParseTableInfo]:
        """Parse a list of SQL statements and return structured metadata."""
        
        # result = ParseResult(True, file_path, "sql", {}, 0.0, None, 0.0, [])
        
        # Process each statement separately
        all_parse_results = []
        successful_statements = 0
        statements = filtered  # filtered is already the list of statement dictionaries
        for i, stmt_info in enumerate(statements):
            statement = stmt_info['statement']
            schema = stmt_info['schema']
            name = stmt_info['name']
            if not statement.strip():
                continue
            
            table_info: DdlParseTableInfo = DdlParseTableInfo(
                table_name=name,
                schema_name=schema,
                logical_database_name=database
            )
            try:
                # print(f"DEBUG: Parsing statement {i+1}: {schema}.{name}")
                # print(f"DEBUG: Normalized statement: {statement[:200]}...")
                
                # Use original simple DDL parser for table parsing
                simple_parser = DDLParser(statement, normalize_names=True)
                parse_results = simple_parser.run()

                # [{
                # 'table_name': 'ABSENCE', 
                # 'schema': 'dbo', 
                # 'primary_key': [...], 
                # 'columns': [...], 
                # 'alter': {}, 
                # 'checks': [...], 
                # 'index': [...], 
                # 'partitioned_by': [...], 
                # 'constraints': {...}, 
                # 'tablespace': None, 
                # 'table_properties': {...}
                # }]
                #
                # print(f"DEBUG: Simple parser returned: {type(parse_results)}, length: {len(parse_results) if parse_results else 0}")
                # if parse_results:
                #     print(f"DEBUG: First result: {parse_results[0] if parse_results else None}")
                
                # The parser returns a list that we can use directly
                if parse_results and isinstance(parse_results, list):
                    # Handle results from simple parser
                    if parse_results:
                        extracted = self.extract_structued_data(database, parse_results)
                        if extracted:
                            all_parse_results.append(extracted)
                            successful_statements += 1
                        else:
                            # print(f"DEBUG: Statement {i+1} produced no results - {schema}.{name}")
                            all_parse_results.append(table_info)
                        # print(f"DEBUG: Statement {i+1} parsed successfully - {schema}.{name}")
                    else:
                        # print(f"DEBUG: Statement {i+1} produced no results - {schema}.{name}")
                        all_parse_results.append(table_info)
                else:
                    # print(f"DEBUG: Statement {i+1} produced no results - {schema}.{name}")
                    all_parse_results.append(table_info)  # Append basic table info
            except Exception as e:  # pylint: disable=broad-except
                # print(f"DEBUG: Statement {i+1} failed with simple DDL parser error: {e} - {schema}.{name}")
                self.logger.debug("Statement %d parsing failed: %s", i+1, str(e))
                all_parse_results.append(table_info)  # Append basic table info on failure
                continue

        return all_parse_results
    
    def _parse_enhanced_statements(self, database: str, file_path: str, filtered: List[Dict[str, str]]) -> List[DdlParseTableInfo]:
        """Parse a list of SQL statements and return structured metadata."""
        # Process each statement separately
        all_parse_results = []
        successful_statements = 0
        statements = filtered  # filtered is already the list of statement dictionaries
        for i, stmt_info in enumerate(statements):
            statement = stmt_info['statement']
            schema = stmt_info['schema']
            name = stmt_info['name']
            if not statement.strip():
                continue
            
            table_info: DdlParseTableInfo = DdlParseTableInfo(
                table_name=name,
                schema_name=schema,
                logical_database_name=database
            )
            try:
                # print(f"DEBUG: Parsing statement {i+1}: {schema}.{name}")
                # print(f"DEBUG: Normalized statement: {statement[:200]}...")
                
                # Use original simple DDL parser for table parsing
                simple_parser = EnhancedDDLParser(statement)
                parse_results = simple_parser.run()
                # print(f"DEBUG: Simple parser returned: {type(parse_results)}, length: {len(parse_results) if parse_results else 0}")
                
                # 
                # {'tables': [
                # {...}], 
                # 'types': [], 
                # 'sequences': [], 
                # 'domains': [], 
                # 'schemas': [], 
                # 'ddl_properties': []
                # }
                # The unlike _parse_statement which returns a list, the enhanced parser returns a single dictionary that we can use directly
                if parse_results and isinstance(parse_results, dict):
                    tables = parse_results.get("tables", [])
                    # print(f"DEBUG: First result: {tables[0] if tables else None}")
                    # Handle results from simple parser
                    if parse_results:
                        extracted = self.extract_structued_data(database, tables)
                        if extracted:
                            all_parse_results.append(extracted)
                            successful_statements += 1
                        else:
                            # print(f"DEBUG: Statement {i+1} produced no results - {schema}.{name}")
                            all_parse_results.append(table_info)
                        # print(f"DEBUG: Statement {i+1} parsed successfully - {schema}.{name}")
                    else:
                        # print(f"DEBUG: Statement {i+1} produced no results - {schema}.{name}")
                        all_parse_results.append(table_info)
                else:
                    # print(f"DEBUG: Statement {i+1} produced no results - {schema}.{name}")
                    all_parse_results.append(table_info)  # Append basic table info
            except Exception as e:  # pylint: disable=broad-except
                print(f"DEBUG: Statement {i+1} failed with simple DDL parser error: {e} - {schema}.{name}")
                self.logger.debug("Statement %d parsing failed: %s", i+1, str(e))
                all_parse_results.append(table_info)  # Append basic table info on failure
                continue

        return all_parse_results
    
    def extract_structued_data(self, database: str, parse_result: List) -> Union[DdlParseTableInfo, None]:
        """Extract structured data from the simple or enhanced DDL parser result."""
        stuctured = None        
        if parse_result and len(parse_result) > 0:
            result_dict = parse_result[0]  # This is a dictionary from DDL parser
            # print(f"DEBUG: extract_structued_data received: {type(result_dict)}")
            # print(f"DEBUG: result_dict keys: {list(result_dict.keys()) if isinstance(result_dict, dict) else 'Not a dict'}")
            
            # Extract columns information if available
            columns = []
            if "columns" in result_dict and result_dict["columns"]:
                for col_dict in result_dict["columns"]:
                    # print(f"DEBUG: Processing column: {col_dict}")
                    column_info = DdlParseColumnInfo(
                        name=col_dict.get("name", ""),
                        type=col_dict.get("type", ""),
                        size=col_dict.get("size"),
                        identity=col_dict.get("identity"),
                        references=col_dict.get("references"),
                        unique=col_dict.get("unique", False),
                        nullable=col_dict.get("nullable", True),
                        default=col_dict.get("default"),
                        check=col_dict.get("check")
                    )
                    columns.append(column_info)
            
            # Extract table properties and add enhanced parser metadata
            table_properties = result_dict.get("table_properties", {})
            
            # Add enhanced parser specific metadata if available
            if "operation_type" in result_dict:
                table_properties["operation_type"] = result_dict["operation_type"]
            if "referenced_tables" in result_dict:
                table_properties["referenced_tables"] = result_dict["referenced_tables"]
            if "view_definition" in result_dict:
                table_properties["view_definition"] = result_dict["view_definition"]
            if "procedure_body" in result_dict:
                table_properties["procedure_body"] = result_dict["procedure_body"]
            
            # Handle both simple parser and enhanced parser formats for table/view/procedure names
            table_name = (result_dict.get("table_name") or 
                         result_dict.get("view_name") or 
                         result_dict.get("procedure_name") or "")
            
            schema_name = (result_dict.get("schema") or 
                          result_dict.get("schema_name") or "")
            
            # print(f"DEBUG: Extracted table_name='{table_name}', schema_name='{schema_name}'")
            
            stuctured = DdlParseTableInfo(
                table_name=table_name,
                schema_name=schema_name,
                logical_database_name=database,
                columns=columns,
                primary_key=result_dict.get("primary_key", []),
                alter=result_dict.get("alter"),
                checks=result_dict.get("checks", []),
                index=result_dict.get("index", []),
                partition_key=result_dict.get("partition_key", result_dict.get("partitioned_by", [])),
                constraints=result_dict.get("constraints"),
                table_properties=table_properties if table_properties else None
            )
            
            # print(f"DEBUG: Created DdlParseTableInfo: table_name='{stuctured.table_name}', columns={len(stuctured.columns)}")
        
            if len(parse_result) > 1:
                self.logger.warning("Multiple parse results found, returning first one only")
        else:
            self.logger.debug("DEBUG: extract_structued_data received empty or None parse_result")

        return stuctured
       
    def _combine_parse_results(self, results_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine multiple parse results into a single result dictionary."""
        combined: Dict[str, Any] = {}
        all_metadata = []
        
        for enhanced_result in results_list:
            # Extract parse results and metadata
            parse_results = enhanced_result.get('parse_results', {})
            metadata = enhanced_result.get('metadata', {})
            
            # Store metadata separately
            all_metadata.append(metadata)
            
            # Combine parse results
            for key, value in parse_results.items():
                if key not in combined:
                    combined[key] = []
                if isinstance(value, list):
                    combined[key].extend(value)
                else:
                    combined[key].append(value)
        
        # Add metadata to combined results
        combined['statement_metadata'] = all_metadata
        
        return combined

    def filter_statements_by_type(self, statements: List[str], object_type: str, normalize_name: bool = False) -> List[Dict[str, str]]:
        """
        Filter SQL statements to find CREATE/ALTER objects of the specified type and extract metadata.
        
        Args:
            statements: List of SQL statements to filter
            object_type: Database object type to filter for (e.g., 'procedure', 'table', 'view', 'function')
            normalize_name: If True, remove brackets from schema and table names
            
        Returns:
            List of dictionaries with 'schema', 'table', and 'statement' keys
        """
        if not statements or not object_type:
            return []
        
        # Create regex pattern for "CREATE/ALTER [OR REPLACE] <object_type>"
        # Support both CREATE and ALTER statements
        pattern = rf'^\s*(?:CREATE|ALTER)\s+(?:OR\s+REPLACE\s+)?{re.escape(object_type)}\s+(?:\[?(\w+)\]?\.)?(?:\[?(\w+)\]?\.)?(?:\[?(\w+)\]?)'
        
        filtered_results = []
        for statement in statements:
            if not statement.strip():
                continue
                
            # Check if statement starts with CREATE/ALTER <object_type>
            match = re.match(pattern, statement, flags=re.IGNORECASE)
            if match:
                # Extract the captured groups (schema, table parts)
                groups = [g for g in match.groups() if g is not None]
                
                if len(groups) >= 1:
                    # Determine schema and table based on number of parts
                    if len(groups) == 1:
                        schema = ""
                        obj = groups[0]
                    elif len(groups) == 2:
                        schema = groups[0]
                        obj = groups[1]
                    else:  # 3 or more parts (database.schema.table)
                        schema = groups[-2] if len(groups) > 1 else ""
                        obj = groups[-1]
                    
                    # Normalize names if requested
                    if normalize_name:
                        schema = schema.strip('[]')
                        obj = obj.strip('[]')
                    
                    filtered_results.append({
                        'schema': schema,
                        'name': obj,
                        'statement': statement
                    })
                
        return filtered_results

    def _filter_statements_by_type(self, operation: str, statements: List[str], object_type: str, normalize_name: bool = False) -> List[Dict[str, str]]:
        """
        Filter SQL statements to find CREATE/ALTER objects of the specified type and extract metadata.
        
        Args:
            operation: The SQL operation to filter for (e.g., 'CREATE', 'ALTER')
            statements: List of SQL statements to filter
            object_type: Database object type to filter for (e.g., 'procedure', 'table', 'view', 'function')
            normalize_name: If True, remove brackets from schema and table names
            
        Returns:
            List of dictionaries with 'schema', 'name', and 'statement' keys
        """
        if not statements or not object_type or not operation:
            return []
        
        # Create regex pattern for specific operation with object type
        pattern = rf'^\s*{re.escape(operation)}\s+(?:OR\s+REPLACE\s+)?{re.escape(object_type)}\s+(?:\[?(\w+)\]?\.)?(?:\[?(\w+)\]?\.)?(?:\[?(\w+)\]?)'
        
        filtered_results = []
        for statement in statements:
            if not statement.strip():
                continue
                
            # Check if statement starts with operation <object_type>
            match = re.match(pattern, statement, flags=re.IGNORECASE)
            if match:
                # Extract the captured groups (schema, table parts)
                groups = [g for g in match.groups() if g is not None]
                
                if len(groups) >= 1:
                    # Determine schema and table based on number of parts
                    if len(groups) == 1:
                        schema = ""
                        obj = groups[0]
                    elif len(groups) == 2:
                        schema = groups[0]
                        obj = groups[1]
                    else:  # 3 or more parts (database.schema.table)
                        schema = groups[-2] if len(groups) > 1 else ""
                        obj = groups[-1]
                    
                    # Normalize names if requested
                    if normalize_name:
                        schema = schema.strip('[]')
                        obj = obj.strip('[]')
                    
                    filtered_results.append({
                        'schema': schema,
                        'name': obj,
                        'statement': statement
                    })
                
        return filtered_results

    def split_statements(self, content: str) -> List[str]:
        """
        Split SQL content by case-insensitive 'go' statements and remove comment lines.
        
        Args:
            content: The SQL content to split
            
        Returns:
            List of SQL statements with comments removed
        """
        if not content:
            return []
        
        # Step 1: Global replace case-insensitive 'go' with 'GO' using word boundaries
        content = re.sub(r'\bgo\b', 'GO', content, flags=re.IGNORECASE)
        
        # Step 2: Split by 'GO'
        statements = content.split('GO')
        
        # Step 3: Clean each statement
        cleaned_statements = []
        for statement in statements:
            cleaned = self._clean_statement(statement)
            
            if cleaned.strip():  # Only add non-empty statements
                cleaned_statements.append(cleaned)
        
        return cleaned_statements

    def _clean_statement(self, statement: str) -> str:
        """
        Clean a SQL statement by removing comment lines and normalizing whitespace.
        
        Args:
            statement: Raw SQL statement
            
        Returns:
            Cleaned SQL statement
        """
        if not statement:
            return ""
        
        lines = statement.split('\n')
        cleaned_lines = []
        
        in_multiline_comment = False
        
        for line in lines:
            original_line = line
            line = line.strip()
            
            # Handle multi-line comments /* ... */
            if '/*' in line and '*/' in line:
                # Single line /* comment */ - remove the comment part
                line = re.sub(r'/\*.*?\*/', '', line)
            elif '/*' in line:
                # Start of multi-line comment
                in_multiline_comment = True
                # Keep part before /*
                line = line[:line.find('/*')]
            elif '*/' in line and in_multiline_comment:
                # End of multi-line comment
                in_multiline_comment = False
                # Keep part after */
                line = line[line.find('*/') + 2:]
            elif in_multiline_comment:
                # Inside multi-line comment - skip entire line
                continue
            
            # Skip single-line comments that start with --
            if line.startswith('--'):
                continue
            
            # Remove inline -- comments but preserve the SQL before them
            if '--' in line:
                line = line[:line.find('--')]
            
            # Keep the line if it has content after cleaning
            line = line.strip()
            if line:
                cleaned_lines.append(line)
            elif original_line.strip() == '':
                # Preserve empty lines for readability
                cleaned_lines.append('')
        
        # Join lines and remove leading/trailing newlines and whitespace
        cleaned_statement = '\n'.join(cleaned_lines).strip()
        return cleaned_statement
    
    def _determine_logical_database(self, source_path: str) -> str:
        """Determine logical database name from source path."""
        # Extract database name from path like 'db/Storm2' -> 'Storm2'
        path_parts = source_path.split('/')
        if 'db' in path_parts:
            db_index = path_parts.index('db')
            if db_index + 1 < len(path_parts):
                return path_parts[db_index + 1]
        return 'Unknown'
