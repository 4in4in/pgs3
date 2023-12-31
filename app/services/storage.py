from uuid import uuid4
from collections import namedtuple

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError

from app.db.repositories.bindings import BindingsRepositoryProtocol
from app.db.repositories.storage import ItemType, ItemId, StorageRepository
from app.s3.connector import S3Connector

from app.schemas import (
    DeleteItemResponseSchema,
    DeleteItemStatusCode,
    FileStorageItemSchema,
    PageSchema,
    PageWithHighlidtedItemSchema,
    PathResponseItemSchema,
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
        s3_connector: S3Connector | None = None,
        binding_repo: BindingsRepositoryProtocol | None = None,
        unique_id_factory=uuid4,
        delimiter: str = "/",
        src_prefix: str = "",
    ) -> None:
        self.s3_connector = s3_connector
        self.storage_repo = storage_repo
        self.unique_id_factory = unique_id_factory
        self.binding_repo = binding_repo
        self.delimiter = delimiter
        self.src_prefix = src_prefix

    def _page_to_limit_offset(self, page: int, per_page: int) -> tuple[int, int]:
        return LimitOffset(limit=per_page, offset=(page - 1) * per_page)

    async def _construct_page_path(
        self, folder_id: ItemId | None = None
    ) -> list[PathResponseItemSchema]:
        path = [PathResponseItemSchema(id=None, path=self.delimiter)]
        if folder_id:
            path_items = await self.storage_repo.get_item_path(folder_id)
            path.extend(
                [
                    PathResponseItemSchema(id=path_item.item_id, path=path_item.name)
                    for path_item in path_items
                ]
            )
        return path

    async def upload_file(self, raw_content: bytes, file_path: str) -> None:
        _file_path = file_path
        if not self.delimiter in _file_path:
            _file_path = self.delimiter + _file_path

        folder_path, file_name = _file_path.rsplit(self.delimiter, maxsplit=1)

        folder_id = None
        if folder_path:
            folder_id = await self.storage_repo.get_item_id_by_path(folder_path)
            if not folder_id:
                raise HTTPException(409, "Folder not found")

        existing_item_id = await self.storage_repo.get_item_id_by_path(file_path)
        if existing_item_id:
            answer = await self.remove_item(existing_item_id)
            if answer.statusCode == DeleteItemStatusCode.ERROR:
                return answer
        file_id = self.unique_id_factory()

        try:
            self.storage_repo.create_item(
                file_id,
                file_name,
                ItemType.FILE,
                parent_id=folder_id,
            )
            await self.s3_connector.upload_file(
                key=str(file_id),
                raw_content=raw_content,
            )
            await self.storage_repo.commit()
        except Exception as ex:
            await self.storage_repo.rollback()
            raise ex

    async def list_folder_items(
        self,
        folder_id: ItemId | None = None,
        query: str | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> PageSchema:
        limit, offset = self._page_to_limit_offset(page, per_page)

        raw_items = await self.storage_repo.list_items(folder_id, query, limit, offset)
        total = await self.storage_repo.list_items(folder_id, query, count_only=True)
        bindings, _ = await self.binding_repo.get_file_binds()

        items = [
            FileStorageItemSchema(
                title=item.name,
                id=item.item_id,
                type=item.type,
                src=self.src_prefix + item.path,
                path=item.path or item.name,
                bind_count=(bindings or {}).get(item.path, 0),
            )
            for item in raw_items
        ]

        return PageSchema(
            current_page=page,
            items=items,
            path=await self._construct_page_path(folder_id),
            all_page=int(total / per_page) + 1,
            total=total,
        )

    async def create_folder(
        self, name: str, parent_id: ItemId | None = None
    ) -> PageSchema:
        folder_id = self.unique_id_factory()
        try:
            self.storage_repo.create_item(
                folder_id, name, ItemType.FOLDER, parent_id=parent_id
            )
            await self.storage_repo.commit()

            return PageSchema(
                current_page=1,
                items=[],
                path=await self._construct_page_path(folder_id),
                all_page=1,
                total=0,
            )
        except IntegrityError as ex:
            await self.storage_repo.rollback()
            raise FolderExists

    async def move_item(
        self,
        item_id: ItemId,
        new_parent_id: ItemId | None = None,
        per_page: int = 50,
    ) -> PageSchema:
        await self.storage_repo.change_item_parent(item_id, new_parent_id)
        await self.storage_repo.commit()
        page = await self.storage_repo.get_page_number(new_parent_id, item_id, per_page)

        return await self.list_folder_items(new_parent_id, page=page, per_page=per_page)

    async def remove_item(
        self, item_id: ItemId, per_page: int = 50
    ) -> DeleteItemResponseSchema:
        item = await self.storage_repo.get_item_by_id(item_id)
        page = await self.storage_repo.get_page_number(
            item.parent_id, item_id, per_page
        )

        bindings = {}
        to_delete = [item]

        if item.type == ItemType.FILE:
            bindings, _ = await self.binding_repo.get_file_binds([item.path])
        elif item.type == ItemType.FOLDER:
            total_files = await self.storage_repo.list_items(item_id, count_only=True)
            to_delete.extend(
                await self.storage_repo.list_items(item_id, limit=total_files)
            )
            bindings, _ = await self.binding_repo.get_file_binds(
                [file.item_id for file in to_delete]
            )

        if bindings:
            binded_items = await self.storage_repo.get_items_by_paths(
                [path for path in bindings]
            )
            return DeleteItemResponseSchema(
                statusCode=DeleteItemStatusCode.ERROR,
                datas=[
                    PathResponseItemSchema(id=_item.item_id, path=_item.path)
                    for _item in binded_items
                ],
            )
        else:
            await self.s3_connector.remove_items(to_delete)
            await self.storage_repo.remove_item(item_id)
            await self.storage_repo.commit()

        new_page = await self.list_folder_items(item.parent_id, page=page)
        if not new_page.items and page > 1:
            new_page = await self.list_folder_items(item.parent_id, page=page - 1)
        return DeleteItemResponseSchema(
            statusCode=DeleteItemStatusCode.OK, datas=new_page
        )

    async def get_page_by_path(self, path: str, per_page: int = 50) -> PageSchema:
        _items = await self.storage_repo.get_items_by_paths([path])
        if not _items:
            ...  # not found
        item = _items[0]
        parent_id = item.parent_id

        page_number = await self.storage_repo.get_page_number(
            parent_id, item.item_id, per_page
        )
        if not page_number:
            ...  # something wrong
        page = await self.list_folder_items(
            parent_id, page=page_number, per_page=per_page
        )
        return PageWithHighlidtedItemSchema(
            current_page=page.current_page,
            items=page.items,
            path=page.path,
            all_page=page.all_page,
            total=page.total,
            highlighted_item_id=item.item_id,
        )

    async def get_file_by_path(self, file_path: str) -> StreamingResponse:
        file_id = await self.storage_repo.get_item_id_by_path(file_path)
        content = await self.s3_connector.download_file(file_id)
        return StreamingResponse(content)
