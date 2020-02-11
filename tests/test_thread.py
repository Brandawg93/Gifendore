import pytest
from core.thread import process


@pytest.mark.asyncio
async def test_process():
    await process()
    assert True
