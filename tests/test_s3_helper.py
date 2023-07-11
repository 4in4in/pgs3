import asyncio

import pytest
import pytest_asyncio

from app.s3_connector.connector import S3Connector
from app.settings import get_settings

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def connector():
    settings = get_settings()
    conn = S3Connector(
        bucket_name=settings.S3_BUCKET_NAME,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        endpoint_url=settings.S3_ENDPOINT,
    )
    async with conn:
        await conn.create_bucket(settings.S3_BUCKET_NAME)
        yield conn
        await conn.delete_bucket(settings.S3_BUCKET_NAME)


async def test_upload_file(connector: S3Connector):
    _id = "kjlasdf"
    assert await connector.upload_file(_id, b"") is None
    assert await connector.remove_items([_id]) is None
