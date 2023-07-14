from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


class BindingsRepositoryProtocol(Protocol):
    async def get_file_binds(
        self, files_paths: list[str] | None = None
    ) -> tuple[dict[str, int], Any]:
        ...


class BindingsRepositoryMock:
    async def get_file_binds(
        self, files_paths: list[str] | None = None
    ) -> tuple[dict[str, int], Any]:
        print(self.get_file_binds.__name__, "REQUESTED WITH ARGS:", files_paths)
        return {}, ...


class BindingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_file_binds(
        self, files_paths: list[str] | None = None
    ) -> tuple[dict[str, int], Any]:
        query = text("SELECT fmadmin.get_file_binds(:files)")
        raw_res = await self.session.execute(query, {"files": files_paths or []})
        result = raw_res.scalars().one() or {}
        return result, None
