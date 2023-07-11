import json

from sqlalchemy import Column, UUID, String, ForeignKey, Index, func, select
from sqlalchemy.orm import aliased, column_property, relationship, Mapped
from sqlalchemy.dialects.postgresql import array


from app.db.core import Base

ZERO_UUID = "00000000-0000-0000-0000-000000000000"


def repr_func(data):
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


class Item(Base):
    __tablename__ = "item"

    item_id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String, nullable=False)
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("item.item_id", ondelete="CASCADE", onupdate="CASCADE"),
    )
    type = Column(String(1), nullable=False)
    path = Column(String)

    __table_args__ = (
        Index("uix_item_id_name", item_id, name, unique=True),
        Index(
            "uix_folder_name_parent_id_1",
            name,
            func.coalesce(parent_id, ZERO_UUID),
            unique=True,
        ),
    )
