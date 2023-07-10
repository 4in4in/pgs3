import json

from sqlalchemy import Column, UUID, String, ForeignKey, Index, func, select
from sqlalchemy.orm import aliased, column_property
from sqlalchemy.dialects.postgresql import array


from app.db.core import Base

ZERO_UUID = "00000000-0000-0000-0000-000000000000"


def repr_func(data):
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


class Item(Base):
    __tablename__ = "item"

    item_id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String, nullable=False)
    parent_id = Column(
        UUID(as_uuid=True), ForeignKey("item.item_id", ondelete="CASCADE")
    )
    type = Column(String(1), nullable=False)

    __table_args__ = (
        Index("uix_item_id_name", item_id, name, unique=True),
        Index(
            "uix_folder_name_parent_id_1",
            name,
            func.coalesce(parent_id, ZERO_UUID),
            unique=True,
        ),
    )


i = aliased(Item)
cte = (
    select(i, array([i.name]).label("path"))
    .where(i.parent_id.is_(None))
    .cte(recursive=True)
)

cte = cte.union_all(
    select(Item, func.array_append(cte.c.path, Item.name).label("path")).join(
        cte, cte.c.item_id == Item.parent_id
    )
)


class ItemExtended(Base):
    __table__ = cte

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
