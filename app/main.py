import logging

from pydantic import UUID4

from fastapi import FastAPI, Depends, Query, Path, UploadFile

from app.db.core import session_factory
from app.db.repositories.storage import StorageRepository
from app.db.repositories.bindings import BindingsRepositoryMock
from app.services.storage import FileStorageService
from app.s3.connector import S3Connector

from app.schemas import DeleteItemResponseSchema, PageSchema, PageWithHighlidtedItemSchema

from app.settings import get_settings

app = FastAPI()

settings = get_settings()

logging.basicConfig(level=settings.DEBUG and logging.DEBUG or logging.INFO)


async def fs_service():
    async with session_factory() as session:
        async with S3Connector(
            bucket_name=settings.S3_BUCKET_NAME,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            endpoint_url=settings.S3_ENDPOINT,
            debug=settings.DEBUG,
        ) as s3_connector:
            repo = StorageRepository(session)
            service = FileStorageService(
                storage_repo=repo,
                s3_connector=s3_connector,
                src_prefix=settings.SRC_PREFIX,
                binding_repo=BindingsRepositoryMock(),
            )
            yield service


@app.get("/find_file", responses={200: {"model": list[PageSchema]}})
@app.get("/filesV4", responses={200: {"model": list[PageSchema]}})
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


@app.post("/create_dirV2", responses={200: {"model": PageSchema}})
async def create_folder_route(
    name: str,
    folder_id: UUID4 = Query(None, alias="id"),
    service: FileStorageService = Depends(fs_service),
):
    return await service.create_folder(name, folder_id)


@app.post("/movement", responses={200: {"model": PageSchema}})
async def move_item_route(
    item_id: UUID4 = Query(..., description="Not filename anymore"),
    target_folder_id: UUID4 = Query(None, alias="new_id"),
    per_page: int = settings.PER_PAGE,
    old_parent_id: UUID4 = Query(None, alias="last_id", deprecated=True),
    service: FileStorageService = Depends(fs_service),
):
    return await service.move_item(item_id, target_folder_id, per_page)


@app.delete("/files/file/{id}/delete", responses={200: {"model": DeleteItemResponseSchema}})
@app.delete("/files/folder/{id}/delete", responses={200: {"model": DeleteItemResponseSchema}})
async def delete_item_route(
    item_id: UUID4 = Path(..., alias="id"),
    per_page: int = settings.PER_PAGE,
    page: int = Query(None, deprecated=True),
    service: FileStorageService = Depends(fs_service),
):
    return await service.remove_item(item_id, per_page)


@app.get("/page-by-path", responses={200: {"model": PageWithHighlidtedItemSchema}})
async def get_page_by_path_route(
    path: str,
    per_page: int = settings.PER_PAGE,
    service: FileStorageService = Depends(fs_service),
):
    return await service.get_page_by_path(path, per_page)


@app.put("/file/{file_path}", tags=["webdav"])
async def put_webdav_file_route(
    file_path: str,
    file: UploadFile,
    service: FileStorageService = Depends(fs_service),
):
    return await service.upload_file(await file.read(), file_path)


@app.get("/file/{file_path}", tags=["webdav"])
async def get_webdav_file_route(file_path: str, service: FileStorageService = Depends(fs_service)):
    return await service.get_file_by_path(file_path)