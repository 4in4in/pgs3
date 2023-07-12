import logging

from pydantic import UUID4

logging.basicConfig(level=logging.DEBUG)

from fastapi import FastAPI, Depends

from app.db.core import session_factory
from app.db.repo import StorageRepository
from app.service import FileStorageService

from app.schemas import CreateFolderSchema, MoveItemSchema, Page

from app.settings import get_settings

app = FastAPI()

settings = get_settings()


async def dep():
    async with session_factory() as session:
        repo = StorageRepository(session)
        service = FileStorageService(repo, src_prefix=settings.SRC_PREFIX)
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


@app.post("/folder")
async def post_folder_route(
    data: CreateFolderSchema, service: FileStorageService = Depends(dep)
):
    return await service.create_folder(data.name, data.parent_id)


@app.post("/move")
async def post_move_route(
    data: MoveItemSchema, service: FileStorageService = Depends(dep)
):
    await service.storage_repo.change_item_parent(data.id_, data.new_parent_id)
    await service.storage_repo.commit()
