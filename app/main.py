import logging

from pydantic import UUID4

from fastapi import FastAPI, Depends, Query, Path

from app.db.core import session_factory
from app.db.repositories.storage import StorageRepository
from app.db.repositories.bindings import BindingsRepositoryMock
from app.services.storage import FileStorageService
from app.s3.connector import S3Connector

from app.schemas import DeleteItemResponse, Page, PageWithHighlidtedItem

from app.settings import get_settings

app = FastAPI()

settings = get_settings()

logging.basicConfig(level=settings.DEBUG and logging.DEBUG or logging.INFO)

async def fs_service():
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
            s3_connector=s3_connector,
            src_prefix=settings.SRC_PREFIX,
            binding_repo=BindingsRepositoryMock(),
        )
        yield service


@app.get("/find_file", responses={200: {"model": list[Page]}})
@app.get("/filesV4", responses={200: {"model": list[Page]}})
async def get_files_route(
    folder_id: UUID4 | None = Query(None, alias="id"),
    page: int = 1,
    per_page: int = settings.PER_PAGE,
    query: str | None = Query(None, alias="text"),
    service: FileStorageService = Depends(fs_service),
):
    return await service.list_folder_items(
        folder_id,
        query,
        page=page,
        per_page=per_page,
    )


@app.post("/create_dirV2", responses={200: {"model": Page}})
async def create_folder_route(
    name: str,
    folder_id: UUID4 = Query(None, alias="id"),
    service: FileStorageService = Depends(fs_service),
):
    return await service.create_folder(name, folder_id)


@app.post("/movement", responses={200: {"model": Page}})
async def move_item_route(
    item_id: UUID4 = Query(..., description="Not filename anymore"),
    target_folder_id: UUID4 = Query(None, alias="new_id"),
    per_page: int = settings.PER_PAGE,
    old_parent_id: UUID4 = Query(None, alias="last_id", deprecated=True),
    service: FileStorageService = Depends(fs_service),
):
    return await service.move_item(item_id, target_folder_id, per_page)


@app.delete("/files/file/{id}/delete", responses={200: {"model": DeleteItemResponse}})
@app.delete("/files/folder/{id}/delete", responses={200: {"model": DeleteItemResponse}})
async def delete_item_route(
    item_id: UUID4 = Path(..., alias="id"),
    per_page: int = settings.PER_PAGE,
    page: int = Query(None, deprecated=True),
    service: FileStorageService = Depends(fs_service),
):
    return await service.remove_item(item_id, per_page)


@app.get("/page-by-path", responses={200: {"model": PageWithHighlidtedItem}})
async def get_page_by_path_route(
    path: str,
    per_page: int = settings.PER_PAGE,
    service: FileStorageService = Depends(fs_service),
):
    return await service.get_page_by_path(path, per_page)
