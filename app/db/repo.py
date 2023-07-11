from enum import Enum
from uuid import UUID

from sqlalchemy import select, delete, func
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.item import Item
from app.db.models.item_extended import ItemWithFullPath, ItemWithPath


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
    ) -> tuple[list[ItemWithPath], int]:
        order_func = func.array_position(
            array([ItemType.FOLDER.value, ItemType.FILE.value]),
            ItemWithPath.type,
        )
        query = select(ItemWithPath).order_by(order_func).limit(limit).offset(offset)
        count_query = select(func.count(ItemWithPath.item_id))
        if parent_id or not search_query:
            query = query.where(ItemWithPath.parent_id == parent_id)
        if search_query:
            query = query.where(ItemWithPath.name.like(f"%{search_query}%"))
        items = (await self.session.execute(query)).scalars().all()
        total = (await self.session.execute(count_query)).scalar()
        return items, total

    async def get_item_by_id(self, item_id: ItemId) -> ItemWithFullPath | None:
        return await self.session.get(ItemWithFullPath, item_id)

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
        query = select(ItemWithPath.item_id).where(ItemWithPath.path == array(path))
        return (await self.session.execute(query)).scalar_one_or_none()

    async def _remove_all(self) -> None:
        await self.session.execute(delete(Item))

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
