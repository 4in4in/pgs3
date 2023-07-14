from enum import Enum

from pydantic import UUID4, BaseModel, Field, validator

from app.db.repositories.storage import ItemType


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
    bind_count: int

    @validator("type_", pre=True)
    def v(cls, v):
        return type_mapping[v]


class CreateFolderSchema(BaseModel):
    name: str
    parent_id: UUID4 | None = None


class MoveItemSchema(BaseModel):
    id_: UUID4 = Field(..., alias="id")
    new_parent_id: UUID4 | None = None


class PathResponseItem(BaseModel):
    id_: UUID4 | None = Field(None, alias="id")
    path: str


class Page(BaseModel):
    current_page: int
    items: list[FileStorageItemSchema]
    path: list[PathResponseItem]
    all_page: int
    total: int


class DeleteItemStatusCode(int, Enum):
    OK = 0
    ERROR = 1


class DeleteItemResponse(BaseModel):
    statusCode: DeleteItemStatusCode
    datas: list[PathResponseItem] | Page

class PageWithHighlidtedItem(Page):
    highlighted_item_id: UUID4