from typing import Any
from sqlalchemy import func, select
from sqlalchemy.orm import aliased, column_property
from sqlalchemy.dialects.postgresql import array

from app.db.core import Base
from app.db.models.item import Item

path_json_expression = lambda entity: func.json_build_object(
    "item_id", entity.item_id, "name", entity.name
)

name_expression = lambda entity: entity.name


def item_cte(column_expr, label):
    i = aliased(Item)

    cte = (
        select(i, array([column_expr(i)]).label(label))
        .where(i.parent_id.is_(None))
        .cte(recursive=True)
    )

    cte = cte.union_all(
        select(
            Item,
            func.array_append(cte.c.path, column_expr(Item)).label(label),
        )
        .join(cte, cte.c.item_id == Item.parent_id)
    )

    return cte

class ItemWithFullPath(Base):
    __table__ = item_cte(path_json_expression, "path")

    item_id = __table__.c.item_id
    name = __table__.c.name
    type = __table__.c.type
    parent_id = __table__.c.parent_id
    path = column_property(__table__.c.path)


class ItemWithPath(Base):
    __table__ = item_cte(name_expression, "path")

    item_id = __table__.c.item_id
    name = __table__.c.name
    type = __table__.c.type
    parent_id = __table__.c.parent_id
    path = column_property(__table__.c.path)


"""
    WITH RECURSIVE items_cte(item_id, name, type, parent_id, path) AS (
        SELECT i.item_id, i."name", i.type, i.parent_id, array[i."name"] AS path
        FROM item i
        WHERE i.parent_id IS NULL
        UNION ALL
        SELECT c.item_id, c."name", c.type, c.parent_id, array_append(p.path, c.name)
        FROM items_cte p
        JOIN item c ON c.parent_id = p.item_id
    )
    SELECT * FROM items_cte WHERE items_cte.parent_id = :parent_id
    ORDER BY array_position(ARRAY[:order_by]::varchar[], type)
    LIMIT :limit
    OFFSET :offset
;
"""
