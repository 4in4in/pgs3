import asyncio

from uuid import uuid4

from app.db.repo import ItemType, StorageRepository
from app.db.core import session_factory
from app.db.models import Item, ItemWithPath

from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload, subqueryload, load_only

from pydantic.type_adapter import TypeAdapter

from app.service import FileStorageService

repo = StorageRepository(session_factory)



async def work():
    async with session_factory() as session:
        repo = StorageRepository(session)
        service = FileStorageService(..., repo, uuid4)
        res = await service.list_folder_items()
        res = await service.list_folder_items("4c2a9930-af1d-4221-b10b-572fc37099f8")
        # print(res)
        # res = await service.list_folder_items("4c2a9930-af1d-4221-b10b-572fc37099f8")
        # res = await repo.list_items("4c2a9930-af1d-4221-b10b-572fc37099f8")
        # ([print(r.model_dump_json(indent=4)) for r in res])
        # query = select(Item).where(
        #     Item.item_id == "4c2a9930-af1d-4221-b10b-572fc37099f8"
        # )
        # result = (
        #     (await session.execute(query.options(joinedload(Item.parent, Item.items, Item))))
        #     .unique()
        #     .scalars()
        #     .all()
        # )
        # print([(r.items, r.parent) for r in result])


asyncio.run(work())
