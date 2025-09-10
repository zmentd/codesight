"""
SQL Parser implementation for Step 02 AST extraction.

Converts SQLReader structural data into domain model objects (SQLDetails).
This version works with the new sql_reader.py that uses simple_ddl_parser
and returns StructuredDdlData with DdlParseTableInfo objects.
"""

from typing import Any, Dict, List, Optional

from config import Config
from domain.config_details import CodeMapping, SemanticCategory
from domain.source_inventory import FileInventoryItem
from domain.sql_details import (
    ColumnInfo,
    ConstraintInfo,
    DatabaseObject,
    DatabaseObjectType,
    ForeignKeyInfo,
    IndexInfo,
    SQLDetails,
    SqlOperationType,
    SQLStatement,
    TableOperation,
)

from .base_parser import BaseParser
from .sql_reader import SQLReader


class SQLParser(BaseParser):
    """SQL parser that converts SQLReader output to domain objects."""
    
    def __init__(self, config: Config):
        super().__init__(config)
        self.sql_reader = SQLReader(config)
    
    def can_parse(self, file_item: FileInventoryItem) -> bool:
        """Check if this parser can handle SQL files."""
        return file_item.language == "sql"
    
    def parse_file(self, file_item: FileInventoryItem) -> SQLDetails:
        """
        Parse SQL file using SQLReader and convert to domain objects.
        
        Args:
            file_item: FileInventoryItem with file information
            
        Returns:
            SQLDetails object with converted domain data
        """
        try:
            # Use SQLReader to get structural data
            parse_result = self.sql_reader.parse_file(
                file_item.source_location, 
                file_item.path
            )
            
            if not parse_result.success:
                # Return minimal SQLDetails for failed parsing
                return SQLDetails(
                    file_path=file_item.path,
                    dialect="unknown",
                    statements=[],
                    database_objects=[],
                    table_operations=[],
                    code_mappings=[]
                )
            
            return self._convert_to_domain_model(file_item.path, parse_result.structural_data or {})
            
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Error parsing SQL file %s: %s", file_item.path, str(e))
            return SQLDetails(
                file_path=file_item.path,
                dialect="unknown", 
                statements=[],
                database_objects=[],
                table_operations=[],
                code_mappings=[]
            )
    
    def _convert_to_domain_model(self, file_path: str, structural_data: Dict[str, Any]) -> SQLDetails:
        """Convert SQLReader structural data to domain objects."""
        # Extract the ddl_parse_results from the new structure
        ddl_results = structural_data
        dialect = ddl_results.get("dialect", "unknown")  # Default dialect
        # Convert database objects from the DDL parser results
        database_objects = []
        statements: List[SQLStatement] = []
        
        # Convert tables
        tables = ddl_results.get("tables", [])
        for table_info in tables:
            db_obj = self._convert_table_to_database_object(table_info, "table")
            if db_obj:
                database_objects.append(db_obj)
        
        # Convert views
        views = ddl_results.get("views", [])
        for view_info in views:
            db_obj = self._convert_table_to_database_object(view_info, "view")
            if db_obj:
                database_objects.append(db_obj)
        
        # Convert procedures
        procedures = ddl_results.get("procedures", [])
        for proc_info in procedures:
            db_obj = self._convert_table_to_database_object(proc_info, "procedure")
            if db_obj:
                database_objects.append(db_obj)
        
        # Extract table operations from database objects (since we don't have individual statements)
        table_operations = self._extract_table_operations_from_objects(database_objects)
        
        # Generate code mappings for database relationships
        code_mappings = self._generate_code_mappings_from_objects(database_objects)
        
        return SQLDetails(
            file_path=file_path,
            dialect=dialect,
            statements=statements,  # Empty since new reader focuses on DDL objects
            database_objects=database_objects,
            table_operations=table_operations,
            code_mappings=code_mappings
        )
    
    def _convert_table_to_database_object(self, table_info: Any, object_type: str) -> Optional[DatabaseObject]:
        """Convert DdlParseTableInfo (dataclass or dict) to DatabaseObject."""
        try:
            # Helper function to safely get attributes from dataclass or dict
            def safe_get(obj: Any, attr: str, default: Any = None) -> Any:
                if isinstance(obj, dict):
                    return obj.get(attr, default)
                else:
                    return getattr(obj, attr, default)
            
            # Determine the database object type
            if object_type == "table":
                db_obj_type = DatabaseObjectType.TABLE
            elif object_type == "view":
                db_obj_type = DatabaseObjectType.VIEW
            elif object_type == "procedure":
                db_obj_type = DatabaseObjectType.PROCEDURE
            elif object_type == "table_alter":
                db_obj_type = DatabaseObjectType.TABLE  # ALTER statements modify tables
            else:
                db_obj_type = DatabaseObjectType.TABLE  # Default fallback
            
            # Convert columns
            columns = []
            table_columns = safe_get(table_info, 'columns', [])
            if table_columns:
                for col_info in table_columns:
                    # Handle both dict and dataclass column info
                    col_name = safe_get(col_info, 'name', '')
                    col_type = safe_get(col_info, 'type', '')
                    col_size = safe_get(col_info, 'size')
                    col_nullable = safe_get(col_info, 'nullable', True)
                    col_default = safe_get(col_info, 'default')
                    col_identity = safe_get(col_info, 'identity')
                    
                    # Handle column size - it could be int, string, or None
                    max_length = None
                    if col_size is not None:
                        if isinstance(col_size, int):
                            max_length = col_size
                        elif isinstance(col_size, str) and col_size.isdigit():
                            max_length = int(col_size)
                    
                    column = ColumnInfo(
                        name=col_name,
                        data_type=col_type,
                        max_length=max_length,
                        nullable=col_nullable,
                        default_value=col_default,
                        identity=bool(col_identity)
                    )
                    columns.append(column)
            
            # Extract foreign keys from column references
            foreign_keys = []
            if table_info["alter"]:
                alter = table_info["alter"]
                if alter and alter["columns"]:
                    alter_columns = alter["columns"]
                    for col in alter_columns:
                        if col.get("references"):
                            col_name = col.get("name", "")
                            references = col.get("references", {})
                            table_name = safe_get(table_info, 'table_name', '')
                            fk = ForeignKeyInfo(
                                constraint_name=f"FK_{table_name}_{col_name}",  # Generated name
                                source_columns=[col_name],
                                referenced_table=references.get("table", ""),
                                referenced_schema=references.get("schema"),
                                referenced_columns=[references.get("column", "")]
                            )
                            foreign_keys.append(fk)
            
            # Convert indexes (if available)
            indexes = []
            table_indexes = safe_get(table_info, 'index', [])
            if table_indexes:
                for idx_data in table_indexes:
                    if isinstance(idx_data, dict):
                        table_name = safe_get(table_info, 'table_name', '')
                        index = IndexInfo(
                            name=idx_data.get("name", f"IX_{table_name}"),
                            index_type=idx_data.get("type", "NONCLUSTERED"),
                            columns=idx_data.get("columns", []),
                            sort_orders=["ASC"] * len(idx_data.get("columns", []))  # Default to ASC
                        )
                        indexes.append(index)
            
            # Convert constraints (if available)
            constraints = []
            table_checks = safe_get(table_info, 'checks', [])
            if table_checks:
                for check_data in table_checks:
                    if isinstance(check_data, dict):
                        table_name = safe_get(table_info, 'table_name', '')
                        constraint = ConstraintInfo(
                            name=check_data.get("name", f"CK_{table_name}"),
                            constraint_type="CHECK",
                            columns=check_data.get("columns", []),
                            definition=check_data.get("definition", "")
                        )
                        constraints.append(constraint)
            
            # For procedures, extract parameters (not available in current DDL parser)
            parameters = None  # Not available in current DDL parser structure
            table_properties = safe_get(table_info, 'table_properties', {})

            # Get table info attributes using safe_get
            table_name = safe_get(table_info, 'table_name', '')
            schema_name = safe_get(table_info, 'schema_name', 'dbo')
            logical_database_name = safe_get(table_info, 'logical_database_name', 'default')
            primary_key = safe_get(table_info, 'primary_key', [])
            operation_type = None
            referenced_tables = []
            operations = []
            if table_properties:
                operation_type = table_properties.get("operation_type", "")
                referenced_tables = table_properties.get("referenced_tables", [])
                for ref_table in referenced_tables:
                    fk = ForeignKeyInfo(
                        constraint_name=table_name,  # Generated name
                        source_columns=[],
                        referenced_table=ref_table,
                        referenced_schema=schema_name,
                        referenced_columns=[]
                    )
                    foreign_keys.append(fk)
                    if operation_type:
                        operations.append(SqlOperationType.to_enum(operation_type))
            
            return DatabaseObject(
                object_type=db_obj_type,
                object_name=table_name,
                schema_name=schema_name or "dbo",  # Default schema if not specified
                logical_database=logical_database_name,
                definition="",  # Not available in current DDL parser, would need original SQL text
                dependencies=[],  # Not available in current DDL parser
                columns=columns if columns else None,
                primary_keys=primary_key if primary_key else None,
                foreign_keys=foreign_keys if foreign_keys else None,
                indexes=indexes if indexes else None,
                constraints=constraints if constraints else None,
                parameters=parameters,
                referenced_objects=None,  # Not available in current DDL parser
                operations=operations if operations else None,
            )
            
        except Exception as e:  # pylint: disable=broad-except
            self.logger.warning("Failed to convert table info to database object: %s", str(e))
            return None
    
    def _extract_table_operations_from_objects(self, database_objects: List[DatabaseObject]) -> List[TableOperation]:
        """Extract table operations from database objects (primarily procedures)."""
        operations: List[TableOperation] = []
        
        # For procedures, we would need to parse the procedure body to extract operations
        # Since the current DDL parser doesn't provide procedure body parsing,
        # we can only create basic operations based on the object existence
        
        for db_obj in database_objects:
            if db_obj.object_type == DatabaseObjectType.PROCEDURE and db_obj.operations:
                # Create a basic operation indicating the procedure exists
                # In a full implementation, we would parse the procedure body for actual table operations
                for db_operation in db_obj.operations:
                    operation = TableOperation(
                        operation=db_operation,  # Procedure creation/existence
                        table_name=db_obj.object_name,
                        schema_name=db_obj.schema_name,
                        logical_database=db_obj.logical_database,
                        columns=[],  # Would need procedure body parsing
                        conditions=[]  # Would need procedure body parsing
                    )
                    operations.append(operation)
        
        return operations
    
    def _generate_code_mappings_from_objects(self, database_objects: List[DatabaseObject]) -> List[CodeMapping]:
        """Generate CodeMapping objects from database objects."""
        code_mappings = []
        
        for db_obj in database_objects:
            source_ref = f"{db_obj.logical_database}.{db_obj.schema_name}.{db_obj.object_name}"
            
            # Foreign key relationships
            if db_obj.foreign_keys:
                for fk in db_obj.foreign_keys:
                    target_schema = fk.referenced_schema or db_obj.schema_name
                    target_ref = f"{db_obj.logical_database}.{target_schema}.{fk.referenced_table}"
                    if db_obj.object_type == DatabaseObjectType.PROCEDURE:
                        # For procedures, we can indicate that it references the table
                        code_mappings.append(CodeMapping(
                            from_reference=source_ref,
                            to_reference=target_ref,
                            mapping_type="procedure",
                            framework="sql",
                            semantic_category=SemanticCategory.COMPOSITION,
                            attributes={
                                "procedure_name": fk.constraint_name,
                                "source_columns": ",".join(fk.source_columns),
                                "referenced_table": fk.referenced_table,
                                "operations": ",".join(op.value for op in db_obj.operations) if db_obj.operations else ""
                            }
                        ))
                    else:
                        code_mappings.append(CodeMapping(
                            from_reference=source_ref,
                            to_reference=target_ref,
                            mapping_type="foreign_key",
                            framework="sql",
                            semantic_category=SemanticCategory.COMPOSITION,
                            attributes={
                                "constraint_name": fk.constraint_name,
                                "source_columns": ",".join(fk.source_columns),
                                "referenced_columns": ",".join(fk.referenced_columns)
                            }
                        ))
            
            # Dependencies (if available)
            if db_obj.dependencies:
                for dependency in db_obj.dependencies:
                    # Parse dependency to extract schema and object name
                    if "." in dependency:
                        schema, obj_name = dependency.rsplit(".", 1)
                        target_ref = f"{db_obj.logical_database}.{schema}.{obj_name}"
                    else:
                        target_ref = f"{db_obj.logical_database}.{db_obj.schema_name}.{dependency}"
                    
                    mapping_type = "view_dependency" if db_obj.object_type == DatabaseObjectType.VIEW else "object_dependency"
                    code_mappings.append(CodeMapping(
                        from_reference=source_ref,
                        to_reference=target_ref,
                        mapping_type=mapping_type,
                        framework="sql",
                        semantic_category=SemanticCategory.COMPOSITION,
                        attributes={
                            "object_type": db_obj.object_type.value,
                            "dependency_type": "direct_reference"
                        }
                    ))
            
            # Referenced objects (if available)
            if db_obj.referenced_objects:
                for ref_obj in db_obj.referenced_objects:
                    if "." in ref_obj:
                        schema, obj_name = ref_obj.rsplit(".", 1)
                        target_ref = f"{db_obj.logical_database}.{schema}.{obj_name}"
                    else:
                        target_ref = f"{db_obj.logical_database}.{db_obj.schema_name}.{ref_obj}"
                    
                    code_mappings.append(CodeMapping(
                        from_reference=source_ref,
                        to_reference=target_ref,
                        mapping_type="object_reference",
                        framework="sql",
                        semantic_category=SemanticCategory.COMPOSITION,
                        attributes={
                            "object_type": db_obj.object_type.value,
                            "reference_type": "internal_reference"
                        }
                    ))
        
        return code_mappings

    # Legacy methods maintained for API compatibility but noted as not available
    def _convert_statements(self, statements_data: List[dict]) -> List[SQLStatement]:
        """
        Convert statement dictionaries to SQLStatement objects.
        
        Note: The new SQL reader focuses on DDL objects rather than individual statements.
        This method is maintained for API compatibility but will return empty list.
        """
        # New reader doesn't extract individual statements, focusing on DDL objects instead
        return []
    
    def _convert_database_objects(self, objects_data: List[dict]) -> List[DatabaseObject]:
        """
        Convert database object dictionaries to DatabaseObject objects.
        
        Note: This method is maintained for API compatibility but the new implementation
        uses _convert_table_to_database_object instead.
        """
        # This is handled by _convert_table_to_database_object in the new implementation
        return []
    
    def _extract_table_operations(self, statements: List[SQLStatement], database_objects: List[DatabaseObject]) -> List[TableOperation]:
        """
        Extract table operations from statements and stored procedure definitions.
        
        Note: This method is maintained for API compatibility but the new implementation
        uses _extract_table_operations_from_objects instead.
        """
        # This is handled by _extract_table_operations_from_objects in the new implementation
        return []
    
    def _extract_operation_from_statement(self, stmt: SQLStatement) -> Optional[TableOperation]:
        """
        Extract table operation from a DML statement.
        
        Note: Not available in new reader - statements are not individually parsed.
        """
        return None
    
    def _extract_operations_from_procedure(self, procedure: DatabaseObject) -> List[TableOperation]:
        """
        Extract table operations from stored procedure definition.
        
        Note: Not available in new reader - procedure body parsing not implemented.
        """
        return []
    
    def _parse_table_from_text(self, statement_text: str) -> Optional[str]:
        """
        Parse table name from statement text.
        
        Note: Not available in new reader - individual statement parsing not implemented.
        """
        return None
    
    def _generate_code_mappings(self, statements: List[SQLStatement], database_objects: List[DatabaseObject]) -> List[CodeMapping]:
        """
        Generate CodeMapping objects from SQL analysis.
        
        Note: This method is maintained for API compatibility but the new implementation
        uses _generate_code_mappings_from_objects instead.
        """
        # This is handled by _generate_code_mappings_from_objects in the new implementation
        return []
