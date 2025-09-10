from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .config_details import CodeMapping
from .source_inventory import FileDetailsBase


# SQL Details domain object
class DatabaseObjectType(Enum):
    TABLE = "table"
    VIEW = "view"
    PROCEDURE = "procedure"
    FUNCTION = "function"
    TRIGGER = "trigger"
    INDEX = "index"
    # Temporary/transient object types
    TEMP_TABLE = "temp_table"
    TABLE_ALIAS = "table_alias"


class SqlOperationType(Enum):
    """SQL operation types including both DDL and DML operations."""
    # DML operations
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    # DDL operations
    CREATE = "CREATE"
    ALTER = "ALTER"
    DROP = "DROP"
    # Other operations
    SET = "SET"

    @staticmethod
    def to_enum(value: str) -> 'SqlOperationType':
        """Check if the operation is a DML operation."""
        if value == SqlOperationType.SELECT.value:
            return SqlOperationType.SELECT
        elif value.upper() == "READ":
            return SqlOperationType.SELECT
        elif value == SqlOperationType.INSERT.value:
            return SqlOperationType.INSERT
        elif value == SqlOperationType.UPDATE.value:
            return SqlOperationType.UPDATE
        elif value == SqlOperationType.DELETE.value:
            return SqlOperationType.DELETE
        elif value == SqlOperationType.CREATE.value:
            return SqlOperationType.CREATE
        elif value == SqlOperationType.ALTER.value:
            return SqlOperationType.ALTER
        elif value == SqlOperationType.DROP.value:
            return SqlOperationType.DROP
        elif value == SqlOperationType.SET.value:
            return SqlOperationType.SET
        else:
            raise ValueError(f"Unknown SQL operation type: {value}")


@dataclass
class ColumnInfo:
    """Database column metadata."""
    name: str
    data_type: str
    max_length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    nullable: bool = True
    identity: bool = False
    identity_seed: Optional[int] = None
    identity_increment: Optional[int] = None
    default_value: Optional[str] = None


@dataclass
class ForeignKeyInfo:
    """Foreign key constraint metadata."""
    constraint_name: str
    source_columns: List[str]
    referenced_schema: Optional[str]
    referenced_table: str
    referenced_columns: List[str]


@dataclass
class IndexInfo:
    """Index metadata."""
    name: str
    index_type: str  # CLUSTERED, NONCLUSTERED, UNIQUE, etc.
    columns: List[str]
    sort_orders: List[str]  # ASC, DESC for each column
    included_columns: Optional[List[str]] = None
    filter_definition: Optional[str] = None


@dataclass
class ConstraintInfo:
    """General constraint metadata."""
    name: str
    constraint_type: str  # PRIMARY KEY, CHECK, DEFAULT, UNIQUE
    columns: List[str]
    definition: Optional[str] = None


@dataclass
class ParameterInfo:
    """Procedure/function parameter metadata."""
    name: str
    data_type: str
    direction: str = "IN"  # IN, OUT, INOUT
    default_value: Optional[str] = None


@dataclass
class DatabaseObject:
    """Database object definition with detailed metadata."""
    object_type: DatabaseObjectType  # table, view, procedure, function, trigger, index
    object_name: str
    schema_name: str
    logical_database: str  # Interfaces, Session, Storm2, TimeKeeper
    definition: str
    dependencies: List[str]
    
    # Detailed metadata (populated based on object type)
    columns: Optional[List[ColumnInfo]] = None
    primary_keys: Optional[List[str]] = None
    foreign_keys: Optional[List[ForeignKeyInfo]] = None
    indexes: Optional[List[IndexInfo]] = None
    constraints: Optional[List[ConstraintInfo]] = None
    parameters: Optional[List[ParameterInfo]] = None  # For procedures/functions
    referenced_objects: Optional[List[str]] = None  # For views/procedures
    operations: Optional[List[SqlOperationType]] = None  # Operations that can be performed on this object
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "object_type": self.object_type.value,
            "object_name": self.object_name,
            "schema_name": self.schema_name,
            "logical_database": self.logical_database,
            "definition": self.definition,
            "dependencies": self.dependencies,
            "columns": [col.__dict__ for col in self.columns] if self.columns else None,
            "primary_keys": self.primary_keys,
            "foreign_keys": [fk.__dict__ for fk in self.foreign_keys] if self.foreign_keys else None,
            "indexes": [idx.__dict__ for idx in self.indexes] if self.indexes else None,
            "constraints": [const.__dict__ for const in self.constraints] if self.constraints else None,
            "parameters": [param.__dict__ for param in self.parameters] if self.parameters else None,
            "referenced_objects": self.referenced_objects,
            "operations": [op.value for op in self.operations] if self.operations else None  # Convert enum to value
        }


@dataclass
class TableOperation:
    """Table operation extracted from DML statements."""
    operation: SqlOperationType  # SELECT, INSERT, UPDATE, DELETE
    table_name: str
    schema_name: Optional[str]
    logical_database: Optional[str]  # Database name (Interfaces, Session, Storm2, TimeKeeper)
    columns: List[str]
    conditions: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "operation": self.operation.value,
            "table_name": self.table_name,
            "schema_name": self.schema_name,
            "logical_database": self.logical_database,
            "columns": self.columns,
            "conditions": self.conditions
        }


@dataclass  
class SQLStatement:
    """Individual SQL statement analysis."""
    statement_type: SqlOperationType  # CREATE, ALTER, DROP, SELECT, INSERT, etc.
    statement_text: str
    object_type: Optional[DatabaseObjectType]
    object_name: Optional[str]
    schema_name: Optional[str]
    logical_database: Optional[str]  # Database name (Interfaces, Session, Storm2, TimeKeeper)
    line_start: int
    line_end: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "statement_type": self.statement_type.value,
            "statement_text": self.statement_text,
            "object_type": self.object_type.value if self.object_type else None,
            "object_name": self.object_name,
            "schema_name": self.schema_name,
            "logical_database": self.logical_database,
            "line_start": self.line_start,
            "line_end": self.line_end
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SQLStatement':
        """Create instance from dictionary."""
        # Convert enum strings back to enums
        statement_type = SqlOperationType(data["statement_type"])
        object_type = DatabaseObjectType(data["object_type"]) if data.get("object_type") else None
        
        return cls(
            statement_type=statement_type,
            statement_text=data["statement_text"],
            object_type=object_type,
            object_name=data.get("object_name"),
            schema_name=data.get("schema_name"),
            logical_database=data.get("logical_database"),
            line_start=data["line_start"],
            line_end=data["line_end"]
        )


@dataclass  
class SQLStoredProcedureDetails:
    """Represents a SQL stored procedure execution call."""
    procedure_name: str
    schema_name: Optional[str]
    body: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "procedure_name": self.procedure_name,
            "schema_name": self.schema_name if self.schema_name else None,
            "body": self.body
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SQLStoredProcedureDetails':
        """Create instance from dictionary."""
        return cls(
            procedure_name=data["procedure_name"],
            schema_name=data.get("schema_name"),
            body=data["body"]
        )


@dataclass
class SQLDetails(FileDetailsBase):
    """Complete SQL file analysis results."""
    file_path: str
    dialect: str
    statements: List[SQLStatement]
    database_objects: List[DatabaseObject]
    table_operations: List[TableOperation]
    code_mappings: List[CodeMapping] = field(default_factory=list)
    
    def get_file_type(self) -> str:
        """Return the file type identifier."""
        return "sql"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        # Convert statements using their to_dict method
        statements_dict = [stmt.to_dict() for stmt in self.statements]
        
        # Convert database objects using their to_dict method
        database_objects_dict = [obj.to_dict() for obj in self.database_objects]
        
        # Convert table operations using their to_dict method
        table_operations_dict = [op.to_dict() for op in self.table_operations]
        
        # Convert code mappings (these should already handle their own serialization)
        code_mappings_dict = []
        for mapping in self.code_mappings:
            if hasattr(mapping, 'to_dict'):
                code_mappings_dict.append(mapping.to_dict())
            else:
                # Fallback to __dict__ if no to_dict method
                mapping_dict = mapping.__dict__.copy()
                # Handle enum conversion for semantic_category
                if hasattr(mapping, 'semantic_category') and mapping.semantic_category:
                    mapping_dict['semantic_category'] = mapping.semantic_category.value
                code_mappings_dict.append(mapping_dict)
        
        return {
            "file_path": self.file_path,
            "dialect": self.dialect,
            "statements": statements_dict,
            "database_objects": database_objects_dict,
            "table_operations": table_operations_dict,
            "code_mappings": code_mappings_dict
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SQLDetails':
        """Create instance from dictionary."""
        # Convert statements
        statements = []
        for stmt_data in data.get("statements", []):
            # Convert enum strings back to enums
            stmt_data_copy = stmt_data.copy()
            if isinstance(stmt_data_copy.get("statement_type"), str):
                stmt_data_copy["statement_type"] = SqlOperationType(stmt_data_copy["statement_type"])
            if isinstance(stmt_data_copy.get("object_type"), str) and stmt_data_copy.get("object_type"):
                stmt_data_copy["object_type"] = DatabaseObjectType(stmt_data_copy["object_type"])
            statements.append(SQLStatement(**stmt_data_copy))
        
        # Convert database objects (simplified - could be enhanced)
        database_objects = []
        for obj_data in data.get("database_objects", []):
            # Convert object_type string back to enum
            obj_data_copy = obj_data.copy()
            if isinstance(obj_data_copy.get("object_type"), str):
                obj_data_copy["object_type"] = DatabaseObjectType(obj_data_copy["object_type"])
            
            # Convert operations list back to enums if present
            if obj_data_copy.get("operations"):
                obj_data_copy["operations"] = [SqlOperationType(op) for op in obj_data_copy["operations"]]
            
            database_objects.append(DatabaseObject(**obj_data_copy))
        
        # Convert table operations
        table_operations = []
        for op_data in data.get("table_operations", []):
            # Convert enum strings back to enums
            op_data_copy = op_data.copy()
            if isinstance(op_data_copy.get("operation"), str):
                op_data_copy["operation"] = SqlOperationType(op_data_copy["operation"])
            table_operations.append(TableOperation(**op_data_copy))
        
        # Convert code mappings
        code_mappings = []
        for mapping_data in data.get("code_mappings", []):
            code_mappings.append(CodeMapping.from_dict(mapping_data))
        
        return cls(
            file_path=data["file_path"],
            dialect=data["dialect"],
            statements=statements,
            database_objects=database_objects,
            table_operations=table_operations,
            code_mappings=code_mappings
        )
