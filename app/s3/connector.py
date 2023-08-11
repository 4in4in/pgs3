import asyncio
from io import BytesIO
import aioboto3


class S3Connector:
    def __init__(
        self,
        bucket_name: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        endpoint_url: str,
        verify: bool = True,
        debug: bool = False,
    ) -> None:
        self._session = aioboto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )
        self._client_params = dict(
            service_name="s3",
            endpoint_url=endpoint_url,
            verify=verify,
        )
        self._client = None
        self._bucket_name = bucket_name
        self.debug = debug

    async def __aenter__(self):
        self._client = await self._session.client(**self._client_params).__aenter__()
        return self

    async def __aexit__(self, *args, **kwargs):
        if self._client:
            await self._client.__aexit__(*args, **kwargs)

    async def create_bucket(self, bucket_name: str) -> None:
        if self.debug:
            print("CALLED", self.create_bucket.__name__, bucket_name)
            return
        await self._client.create_bucket(Bucket=bucket_name)

    async def delete_bucket(self, bucket_name: str) -> None:
        if self.debug:
            print("CALLED", self.delete_bucket.__name__, bucket_name)
            return
        await self._client.delete_bucket(Bucket=bucket_name)

    async def upload_file(self, key: str, raw_content: bytes) -> None:
        if self.debug:
            print("CALLED", self.upload_file.__name__, key, len(raw_content))
            return
        file_like = BytesIO(raw_content)
        await self._client.upload_fileobj(file_like, self._bucket_name, key)

    async def download_file(self, key: str):
        if self.debug:
            print("CALLED", self.download_file.__name__, key)
            return
        response = await self._client.get_object(Bucket=self._bucket_name, Key=key)
        return response["Body"]

    async def remove_items(self, keys: list[str], batch_count=50) -> None:
        if self.debug:
            print("CALLED", self.remove_items.__name__, keys, batch_count)
            return

        def divide_chunks(l, n):
            for i in range(0, len(l), n):
                yield l[i : i + n]

        for keys_chunk in divide_chunks(keys, batch_count):
            delete_arg = {"Objects": [{"Key": key} for key in keys_chunk]}
            await self._client.delete_objects(
                Bucket=self._bucket_name, Delete=delete_arg
            )
