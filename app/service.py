from uuid import uuid4
from collections import namedtuple

from sqlalchemy.exc import IntegrityError

from app.db.repo import ItemType, ItemId, StorageRepository
from app.s3_connector.connector import S3Helper
from app.schemas import FileStorageItemSchema

LimitOffset = namedtuple("LimitOffset", ("limit", "offset"))


class FileExists(Exception):
    ...


class FolderExists(Exception):
    ...


class FileStorageService:
    def __init__(
        self,
        s3_helper: S3Helper,
        storage_repo: StorageRepository,
        unique_id_factory=uuid4,
        delimiter: str = "/",
    ) -> None:
        self.s3_helper = s3_helper
        self.storage_repo = storage_repo
        self.unique_id_factory = unique_id_factory
        self.delimiter = delimiter

    def _page_to_limit_offset(self, page: int, per_page: int) -> tuple[int, int]:
        return LimitOffset(limit=per_page, offset=(page - 1) * per_page)

    async def upload_file(
        self,
        filename: str,
        raw_content: bytes,
        *,
        folder_id: ItemId | None = None,
    ):
        file_id = self.unique_id_factory()
        try:
            await self.storage_repo.create_item(
                file_id, filename, ItemType.FILE, parent_id=folder_id
            )
            await self.s3_helper.upload_file(key=str(file_id), raw_content=raw_content)
            await self.storage_repo.commit()
        except IntegrityError as ex:
            raise FileExists
        except Exception as ex:
            await self.storage_repo.rollback()
            raise ex

    async def list_folder_items(
        self,
        folder_id: ItemId | None = None,
        query: str | None = None,
        page: int = 1,
        per_page: int = 50,
    ):
        limit, offset = self._page_to_limit_offset(page, per_page)
        result = await self.storage_repo.list_items(folder_id, query, limit, offset)
        return [
            FileStorageItemSchema(
                title=item.name,
                id=item.item_id,
                type=item.type,
                src=self.delimiter.join(item.path),
                path=self.delimiter.join(item.path),
            )
            for item in result
        ]

    async def create_folder(self, name: str, parent_id: ItemId | None = None):
        folder_id = self.unique_id_factory()
        try:
            self.storage_repo.create_item(folder_id, name, ItemType.FOLDER, parent_id)
            await self.storage_repo.commit()
        except IntegrityError as ex:
            await self.storage_repo.rollback()
            raise FolderExists

    async def remove_file(self, file_id: ItemId) -> None:
        try:
            await self.storage_repo.remove_item(file_id)
            await self.s3_helper.remove_items([file_id])
        except Exception as ex:
            raise ex

    async def remove_folder(self, folder_id: ItemId) -> None:
        try:
            await self.storage_repo.remove_item(folder_id)
        except Exception as ex:
            raise ex
