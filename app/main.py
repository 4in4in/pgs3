import logging

from pydantic import UUID4

# logging.basicConfig(level=logging.DEBUG)

from fastapi import FastAPI, Depends

from app.db.core import session_factory
from app.db.repositories.storage import StorageRepository
from app.db.repositories.bindings import BindingsRepository
from app.services.storage import FileStorageService
from app.s3_connector.connector import S3Connector

from app.schemas import CreateFolderSchema, DeleteItemResponse, MoveItemSchema, Page, PageWithHighlidtedItem

from app.settings import get_settings

app = FastAPI()

settings = get_settings()


async def dep():
    async with session_factory() as session:
        repo = StorageRepository(session)
        s3_connector = S3Connector(
            bucket_name=settings.S3_BUCKET_NAME,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            endpoint_url=settings.S3_ENDPOINT,
            debug=True,
        )
        service = FileStorageService(
            storage_repo=repo,
            s3_helper=s3_connector,
            src_prefix=settings.SRC_PREFIX,
            binding_repo=BindingsRepository(),
        )
        yield service


@app.get("/files", responses={200: {"model": list[Page]}})
async def get_files_route(
    folder_id: UUID4 | None = None,
    page: int = 1,
    per_page: int = 50,
    query: str | None = None,
    service: FileStorageService = Depends(dep),
):
    return await service.list_folder_items(
        folder_id, query, page=page, per_page=per_page
    )


@app.post("/folder", responses={200: {"model": Page}})
async def create_folder_route(
    data: CreateFolderSchema, service: FileStorageService = Depends(dep)
):
    return await service.create_folder(data.name, data.parent_id)


@app.post("/move", responses={200: {"model": Page}})
async def move_item_route(
    data: MoveItemSchema, service: FileStorageService = Depends(dep)
):
    await service.storage_repo.change_item_parent(data.id_, data.new_parent_id)
    await service.storage_repo.commit()


@app.delete("/delete", responses={200: {"model": DeleteItemResponse}})
async def delete_item_route(item_id: UUID4, service: FileStorageService = Depends(dep)):
    return await service.remove_item(item_id)


@app.get("/page-by-path", responses={200: {"model": PageWithHighlidtedItem}})
async def get_page_by_path_route(path: str, service: FileStorageService = Depends(dep)):
    return await service.get_page_by_path(path)
