import logging

from pydantic import UUID4

logging.basicConfig(level=logging.DEBUG)

from fastapi import FastAPI, Depends

from app.db.core import session_factory
from app.db.repo import StorageRepository
from app.service import FileStorageService

from app.schemas import CreateFolderSchema, MoveItemSchema

app = FastAPI()


async def dep():
    async with session_factory() as session:
        repo = StorageRepository(session)
        service = FileStorageService(repo)
        yield service


@app.get("/files")
async def get_files_route(
    folder_id: UUID4 | None = None,
    page: int = 1,
    per_page: int = 50,
    service: FileStorageService = Depends(dep),
):
    return await service.list_folder_items(folder_id, page=page, per_page=per_page)


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
