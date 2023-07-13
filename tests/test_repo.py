import asyncio
import logging
import os

import pytest
import pytest_asyncio

from uuid import uuid4

from asyncpg.exceptions import UniqueViolationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.db.repositories.storage import StorageRepository, ItemType
from app.db.core import session_factory

logger = logging.getLogger(__name__)

print(os.getcwd())

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def repo():
    async with session_factory() as session:
        repo = StorageRepository(session)
        yield repo
        await repo._remove_all()
        await repo.commit()


async def test_list_items(repo: StorageRepository):
    print(repo)
    assert await repo.list_items() == []


async def test_root_folder_creating(repo: StorageRepository):
    repo.create_item(uuid4(), "test folder", ItemType.FOLDER)
    await repo.commit()
    items = await repo.list_items()
    assert len(items) == 1



async def test_nested_folder_creating(repo: StorageRepository):
    root_folder_id = uuid4()
    repo.create_item(root_folder_id, "root", ItemType.FOLDER)

    inner_folders_count = 10
    for i in range(inner_folders_count):
        repo.create_item(
            uuid4(), f"inner{i}", ItemType.FOLDER, parent_id=root_folder_id
        )
    await repo.commit()

    assert len((await repo.list_items())) == 1
    assert len((await repo.list_items(root_folder_id))) == inner_folders_count
    assert len((await repo.list_items(search_query="inner"))) == inner_folders_count
    assert len((await repo.list_items(search_query="inner0"))) == 1


async def test_ordering(repo: StorageRepository):
    repo.create_item(uuid4(), "folder", ItemType.FOLDER)
    repo.create_item(uuid4(), "file", ItemType.FILE)
    await repo.commit()
    list = [item.type for item in (await repo.list_items())]
    assert list == [ItemType.FOLDER.value, ItemType.FILE.value]


async def test_nonunique_items(repo: StorageRepository):
    fn = "apchxuyebtvrt"
    repo.create_item(uuid4(), fn, ItemType.FILE)
    await repo.session.commit()
    with pytest.raises(IntegrityError):
        repo.create_item(uuid4(), fn, ItemType.FILE)
        await repo.session.commit()
    await repo.rollback()

    with pytest.raises(IntegrityError):
        repo.create_item(uuid4(), fn, ItemType.FOLDER)
        await repo.commit()
    await repo.rollback()


async def test_getting_by_path(repo: StorageRepository):
    root_folder_id = uuid4()
    root_folder_name = "RF"
    repo.create_item(root_folder_id, root_folder_name, ItemType.FOLDER)
    folder_id = uuid4()
    folder_name = "IF"
    repo.create_item(folder_id, folder_name, ItemType.FOLDER, parent_id=root_folder_id)
    await repo.commit()
    found_folder_id = await repo.get_item_id_by_path("/".join([root_folder_name, folder_name]))
    assert found_folder_id == folder_id
