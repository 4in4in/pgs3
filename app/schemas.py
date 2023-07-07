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
    bind_count: int = 0  # bindings count
    path: str  # normal path to item

    @validator("type_", pre=True)
    def v(cls, v):
        return type_mapping[v]
