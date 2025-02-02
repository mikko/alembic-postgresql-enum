import logging

import sqlalchemy
from alembic.operations.ops import (
    UpgradeOps,
    ModifyTableOps,
    AddColumnOp,
    CreateTableOp,
    DropColumnOp,
    DropTableOp,
)
from sqlalchemy import Column
from sqlalchemy.dialects import postgresql


class ReprWorkaround(postgresql.ENUM):
    """
    As postgresql.ENUM does not include create_type inside __repr__, we have to swap it with custom type
    """

    __module__ = "sqlalchemy.dialects.postgresql"

    def __repr__(self):
        return f"{super().__repr__()[:-1]}, create_type=False)".replace("ReprWorkaround", "ENUM").replace(
            ", metadata=MetaData()", ""
        )


def inject_repr_into_enums(column: Column):
    """Swap postgresql.ENUM class to ReprWorkaround for the column type"""
    if column.type.__class__ == sqlalchemy.Enum:
        if not column.type.native_enum:
            return
        log.info("%r converted into postgresql.ENUM", column.type)
        column.type = eval(repr(column.type).replace("Enum", "postgresql.ENUM"))
    if isinstance(column.type, postgresql.ENUM):
        if column.type.create_type:
            log.info("create_type=False injected into %r", column.type.name)
        replacement_enum_type = column.type
        replacement_enum_type.__class__ = ReprWorkaround

        column.type = replacement_enum_type


log = logging.getLogger(f"alembic.{__name__}")


def add_create_type_false(upgrade_ops: UpgradeOps):
    """Add create_type=False to all postgresql.ENUM types that are generated by alembic"""
    for operations_group in upgrade_ops.ops:
        if isinstance(operations_group, ModifyTableOps):
            for operation in operations_group.ops:
                if isinstance(operation, AddColumnOp):
                    column: Column = operation.column

                    inject_repr_into_enums(column)

                elif isinstance(operation, DropColumnOp):
                    column: Column = operation._reverse.column

                    inject_repr_into_enums(column)

        elif isinstance(operations_group, CreateTableOp):
            for column in operations_group.columns:
                if isinstance(column, Column):
                    inject_repr_into_enums(column)

        elif isinstance(operations_group, DropTableOp):
            for column in operations_group._reverse.columns:
                if isinstance(column, Column):
                    inject_repr_into_enums(column)
