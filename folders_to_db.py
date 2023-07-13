ROOT = "/home/ADMSK/asleon17/Projects/mts_connectwizard/gui/flow_backend/ivr_content"


import asyncio
import os
from uuid import UUID, uuid4
from app.db.repositories.storage import ItemType, StorageRepository
from app.db.core import session_factory


async def _create_folder_items(
    root: str,
    parent_id: UUID | None,
    repo: StorageRepository,
):
    items = os.listdir(root)
    folders = []
    files = []

    for item in items:
        full_item_path = os.path.join(root, item)
        if os.path.isfile(full_item_path):
            files.append(item)
        else:
            folders.append(item)

    for file in files:
        repo.create_item(uuid4(), file, ItemType.FILE, parent_id=parent_id)
        await repo.commit()

    for folder in folders:
        full_path = os.path.join(root, folder)
        try:
            folder_id = uuid4()
            repo.create_item(folder_id, folder, ItemType.FOLDER, parent_id=parent_id)
            await repo.commit()

            await _create_folder_items(full_path, folder_id, repo)

        except:
            print(full_path)


async def create_database_entities():
    async with session_factory() as session:
        repo = StorageRepository(session)
        await _create_folder_items(ROOT, None, repo)


asyncio.run(create_database_entities())
