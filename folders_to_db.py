import argparse
import asyncio
import os
from uuid import UUID, uuid4

from app.db.repositories.storage import ItemType, StorageRepository
from app.db.core import session_factory
from app.s3.connector import S3Connector

from app.settings import get_settings


async def _create_folder_items(
    root: str,
    parent_id: UUID | None,
    repo: StorageRepository,
    s3connector: S3Connector,
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
        file_id = uuid4()
        repo.create_item(file_id, file, ItemType.FILE, parent_id=parent_id)
        await repo.commit()
        with open(os.path.join(root, file), "rb") as file:
            await s3connector.upload_file(str(file_id), file.read())

    for folder in folders:
        full_path = os.path.join(root, folder)
        try:
            folder_id = uuid4()
            repo.create_item(folder_id, folder, ItemType.FOLDER, parent_id=parent_id)
            await repo.commit()

            await _create_folder_items(full_path, folder_id, repo)

        except:
            print(full_path)


async def create_database_entities(root: str):
    settings = get_settings()
    async with session_factory() as session:
        repo = StorageRepository(session)
        connector = S3Connector(
            settings.S3_BUCKET_NAME,
            settings.S3_ACCESS_KEY,
            settings.S3_SECRET_KEY,
            settings.S3_ENDPOINT,
        )
        async with connector:
            await _create_folder_items(root, None, repo, connector)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="FoldersToPostgresS3",
        description="Create files struct in Posgresql database and upload files into S3 from specific location",
    )
    parser.add_argument("source")
    args = parser.parse_args()
    asyncio.run(create_database_entities(args.source))
