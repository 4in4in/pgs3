from typing import Any, Protocol


class BindingsRepositoryProtocol(Protocol):
    async def get_file_binds(
        self, files_paths: list[str] | None = None
    ) -> tuple[dict[str, int], Any]:
        ...


class BindingsRepository:
    async def get_file_binds(self, files_paths: list[str] | None = None) -> tuple[dict[str, int], Any]:
        print(self.get_file_binds.__name__, "REQUESTED WITH ARGS:", files_paths)
        return {}, ...