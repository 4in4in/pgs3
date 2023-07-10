from enum import Enum
from uuid import UUID

from sqlalchemy import select, delete, func
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Item, ItemExtended


ItemId = UUID | str


class ItemType(str, Enum):
    FILE = "-"
    FOLDER = "d"


class StorageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_items(
        self,
        parent_id: ItemId | None = None,
        search_query: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[ItemExtended]:
        order_func = func.array_position(
            array([ItemType.FOLDER.value, ItemType.FILE.value]),
            ItemExtended.type,
        )
        query = select(ItemExtended).order_by(order_func).limit(limit).offset(offset)
        if parent_id or not search_query:
            query = query.where(ItemExtended.parent_id == parent_id)
        if search_query:
            query = query.where(ItemExtended.name.like(f"%{search_query}%"))
        return (await self.session.execute(query)).scalars().all()

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

    async def get_item_id_by_path(self, path: list[str]) -> ItemId:
        query = select(ItemExtended.item_id).where(ItemExtended.path == array(path))
        return (await self.session.execute(query)).scalar_one_or_none()

    async def _remove_all(self) -> None:
        await self.session.execute(delete(Item))

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
