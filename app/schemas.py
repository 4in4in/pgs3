from enum import Enum

from pydantic import UUID4, BaseModel, Field, validator

from app.db.repo import ItemType


class ItemTypeHR(str, Enum):
    FOLDER = "folder"
    FILE = "file"


type_mapping = {ItemType.FILE: ItemTypeHR.FILE, ItemType.FOLDER: ItemTypeHR.FOLDER}


class FileStorageItemSchema(BaseModel):
    title: str  # file/folder name
    id_: UUID4 = Field(..., alias="id")
    type_: ItemTypeHR = Field(..., alias="type")
    src: str  # strange path to item
    path: str  # normal path to item

    @validator("type_", pre=True)
    def v(cls, v):
        return type_mapping[v]


class CreateFolderSchema(BaseModel):
    name: str
    parent_id: UUID4 | None = None

class PathResponseItem(BaseModel):
    id_: UUID4 | None = Field(None, alias="id")
    path: str

class Page(BaseModel):
    current_page: int
    items: list[FileStorageItemSchema]
    path: list[PathResponseItem]
    all_page: int