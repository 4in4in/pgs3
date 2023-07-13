from uuid import uuid4
from collections import namedtuple


from sqlalchemy.exc import IntegrityError
from app.db.repositories.bindings import BindingsRepositoryProtocol

from app.db.repositories.storage import ItemType, ItemId, StorageRepository
from app.s3_connector.connector import S3Connector
from app.schemas import (
    DeleteItemResponse,
    DeleteItemStatusCode,
    FileStorageItemSchema,
    Page,
    PathResponseItem,
)

LimitOffset = namedtuple("LimitOffset", ("limit", "offset"))


class FileExists(Exception):
    ...


class FolderExists(Exception):
    ...


class FileStorageService:
    def __init__(
        self,
        storage_repo: StorageRepository,
        s3_helper: S3Connector | None = None,
        binding_repo: BindingsRepositoryProtocol | None = None,
        unique_id_factory=uuid4,
        delimiter: str = "/",
        src_prefix: str = "",
    ) -> None:
        self.s3_helper = s3_helper
        self.storage_repo = storage_repo
        self.unique_id_factory = unique_id_factory
        self.binding_repo = binding_repo
        self.delimiter = delimiter
        self.src_prefix = src_prefix

    def _page_to_limit_offset(self, page: int, per_page: int) -> tuple[int, int]:
        return LimitOffset(limit=per_page, offset=(page - 1) * per_page)

    async def _construct_page_path(
        self, folder_id: ItemId | None = None
    ) -> list[PathResponseItem]:
        path = [PathResponseItem(id=None, path=self.delimiter)]
        if folder_id:
            path_items = await self.storage_repo.get_item_path(folder_id)
            path.extend(
                [
                    PathResponseItem(id=path_item.item_id, path=path_item.name)
                    for path_item in path_items
                ]
            )
        return path

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
            if self.s3_helper:
                await self.s3_helper.upload_file(
                    key=str(file_id), raw_content=raw_content
                )
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

        raw_items = await self.storage_repo.list_items(folder_id, query, limit, offset)
        total = await self.storage_repo.list_items(folder_id, query, count_only=True)
        bindings, _ = await self.binding_repo.get_file_binds()

        items = [
            FileStorageItemSchema(
                title=item.name,
                id=item.item_id,
                type=item.type,
                src=self.src_prefix + item.path or item.name,
                path=item.path or item.name,
                bind_count=(bindings or {}).get(item.path, 0),
            )
            for item in raw_items
        ]

        return Page(
            current_page=page,
            items=items,
            path=await self._construct_page_path(folder_id),
            all_page=int(total / per_page) + 1,
            total=total,
        )

    async def create_folder(self, name: str, parent_id: ItemId | None = None):
        folder_id = self.unique_id_factory()
        try:
            self.storage_repo.create_item(
                folder_id, name, ItemType.FOLDER, parent_id=parent_id
            )
            await self.storage_repo.commit()

            return Page(
                current_page=1,
                items=[],
                path=await self._construct_page_path(folder_id),
                all_page=1,
                total=0,
            )
        except IntegrityError as ex:
            await self.storage_repo.rollback()
            raise FolderExists
    
    async def move_item(self, item_id: ItemId, new_parent_id: ItemId | None = None) -> Page:
        await self.storage_repo.change_item_parent(item_id, new_parent_id)
        await self.storage_repo.commit()
        return await self.list_folder_items(new_parent_id)

    async def remove_file(self, file_id: ItemId) -> None:
        try:
            await self.storage_repo.remove_item(file_id)
            if self.s3_helper:
                await self.s3_helper.remove_items([file_id])
        except Exception as ex:
            raise ex

    async def remove_folder(self, folder_id: ItemId) -> None:
        try:
            if self.s3_helper:
                total_files = await self.storage_repo.list_items(
                    folder_id, count_only=True
                )
                if total_files:
                    files = await self.storage_repo.list_items(
                        folder_id, limit=total_files
                    )
                    await self.s3_helper.remove_items([file.item_id for file in files])

            await self.storage_repo.remove_item(folder_id)
        except Exception as ex:
            raise ex

    async def remove_item(self, item_id: ItemId, page: int = 1) -> DeleteItemResponse:
        item = await self.storage_repo.get_item_by_id(item_id)
        bindings = {}
        to_delete = [item]

        if item.type == ItemType.FILE:
            bindings, _ = await self.binding_repo.get_file_binds([item.path])
        elif item.type == ItemType.FOLDER:
            total_files = await self.storage_repo.list_items(item_id, count_only=True)
            to_delete.append(
                await self.storage_repo.list_items(item_id, limit=total_files)
            )
            bindings, _ = await self.binding_repo.get_file_binds(
                [file.item_id for file in to_delete]
            )

        if bindings:
            binded_items = await self.storage_repo.get_items_by_paths(
                [path for path in bindings]
            )
            return DeleteItemResponse(
                statusCode=DeleteItemStatusCode.ERROR,
                datas=[
                    PathResponseItem(id=_item.item_id, path=_item.path)
                    for _item in binded_items
                ],
            )
        else:
            await self.s3_helper.remove_items(to_delete)
            await self.storage_repo.remove_item(item_id)

        new_page = await self.list_folder_items(item.parent_id, page=page)
        if not new_page.items and page > 1:
            new_page = await self.list_folder_items(item.parent_id, page=page - 1)
        return DeleteItemResponse(status_code=DeleteItemStatusCode.OK, datas=new_page)