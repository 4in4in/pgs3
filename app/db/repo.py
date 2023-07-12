from enum import Enum
from uuid import UUID

from sqlalchemy import select, delete, func, update
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.db.models.item import Item

# from app.db.models.item_extended import ItemWithFullPath, ItemWithPath


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
        *,
        count_only: bool = False,
    ) -> tuple[list[Item], int]:
        if count_only:
            _query = select(func.count(Item.item_id))
            if parent_id or not search_query:
                _query = _query.where(Item.parent_id == parent_id)
            if search_query:
                _query = _query.where(Item.name.like(f"%{search_query}%")).where(
                    Item.type == ItemType.FILE.value
                )
            return (await self.session.execute(_query)).scalar()

        order_func = func.array_position(
            array([ItemType.FOLDER.value, ItemType.FILE.value]),
            Item.type,
        )
        query = select(Item).order_by(order_func).order_by(Item.name).limit(limit).offset(offset)

        if parent_id or not search_query:
            query = query.where(Item.parent_id == parent_id)
        if search_query:
            query = query.where(Item.name.like(f"%{search_query}%")).where(
                Item.type == ItemType.FILE.value
            )
        items = (await self.session.execute(query)).scalars().all()
        return items

    async def get_item_by_id(self, item_id: ItemId) -> Item | None:
        return await self.session.get(Item, item_id)

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

    async def change_item_parent(self, item_id: ItemId, new_parent_id: ItemId):
        query = (
            update(Item).where(Item.item_id == item_id).values(parent_id=new_parent_id)
        )
        await self.session.execute(query)

    async def get_item_path(self, item_id: ItemId) -> list[Item]:
        cte = select(Item).where(Item.item_id == item_id).cte(recursive=True)
        cte = cte.union_all(select(Item).join(cte, Item.item_id == cte.c.parent_id))
        query = select(Item).join(cte, cte.c.item_id == Item.item_id)

        return (await self.session.execute(query)).scalars().all()

    async def get_item_id_by_path(self, path: str) -> ItemId:
        query = select(Item.item_id).where(Item.path == path)
        return (await self.session.execute(query)).scalar_one_or_none()

    async def is_item_exists(self, item_id: ItemId) -> bool:
        query = select(func.count(Item.item_id)).where(Item.item_id == item_id)
        return bool((await self.session.execute(query)).scalar())

    async def _remove_all(self) -> None:
        await self.session.execute(delete(Item))

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
