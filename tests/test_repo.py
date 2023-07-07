import asyncio
import logging
import os

import pytest
import pytest_asyncio

from uuid import uuid4

from asyncpg.exceptions import UniqueViolationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.db.repo import StorageRepository, ItemType
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
    repo = StorageRepository(session_factory)
    yield repo
    await repo._remove_all()


async def test_list_items(repo: StorageRepository):
    assert await repo.list_items() == []


async def test_root_folder_creating(repo: StorageRepository):
    await repo.create_item(uuid4(), "test folder", ItemType.FOLDER)
    assert len(await repo.list_items()) == 1


async def test_nested_folder_creating(repo: StorageRepository):
    root_folder_id = uuid4()
    await repo.create_item(root_folder_id, "root", ItemType.FOLDER)

    inner_folders_count = 10
    for i in range(inner_folders_count):
        await repo.create_item(
            uuid4(), f"inner{i}", ItemType.FOLDER, parent_id=root_folder_id
        )

    assert len(await repo.list_items()) == 1
    assert len(await repo.list_items(root_folder_id)) == inner_folders_count


async def test_ordering(repo: StorageRepository):
    await repo.create_item(uuid4(), "folder", ItemType.FOLDER)
    await repo.create_item(uuid4(), "file", ItemType.FILE)
    list = [item.type for item in await repo.list_items()]
    assert list == [ItemType.FOLDER.value, ItemType.FILE.value]


async def test_nonunique_items(repo: StorageRepository):
    fn = "apchxuyebtvrt"
    await repo.create_item(uuid4(), fn, ItemType.FILE)
    with pytest.raises(IntegrityError):
        await repo.create_item(uuid4(), fn, ItemType.FILE)
    with pytest.raises(IntegrityError):
        await repo.create_item(uuid4(), fn, ItemType.FOLDER)
