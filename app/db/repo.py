from enum import Enum
from typing import Callable
from contextlib import AbstractAsyncContextManager
from uuid import UUID
from pydantic import TypeAdapter

from sqlalchemy import and_, select, delete, func, text
from sqlalchemy.orm import aliased
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Item, ItemWithPath

ItemId = UUID | str


class ItemType(str, Enum):
    FILE = "-"
    FOLDER = "d"


class StorageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_items(
        self, parent_id: ItemId | None = None, limit: int = 10, offset: int = 0
    ) -> list[ItemWithPath]:
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
        query = (
            select(cte)
            .where(cte.c.parent_id == parent_id)
            .order_by(
                func.array_position(
                    array([ItemType.FOLDER.value, ItemType.FILE.value]), cte.c.type
                )
            )
            .limit(limit)
            .offset(offset)
        )
        raw_items = (await self.session.execute(query)).fetchall()
        adapter = TypeAdapter(list[ItemWithPath])
        return adapter.validate_python(item._mapping for item in raw_items)

    def create_item(
        self,
        item_id: ItemId,
        name: str,
        type_: ItemType,
        *,
        parent_id: ItemId | None = None,
    ) -> None:
        new_item = Item(
            item_id=item_id,
            name=name,
            type=type_,
            parent_id=parent_id,
        )
        self.session.add(new_item)

    async def remove_item(self, item_id: ItemId) -> None:
        query = delete(Item).where(Item.item_id == item_id)
        await self.session.execute(query)

    async def _remove_all(self) -> None:
        await self.session.execute(delete(Item))

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
