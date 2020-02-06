import pytest
from core.hosts import get_img_from_url
from core.media.base import is_black


@pytest.mark.asyncio
async def test_is_black_one():
    img = await get_img_from_url('https://i.imgur.com/ZDNqE6p.png')
    assert is_black(img)


@pytest.mark.asyncio
async def test_is_black_two():
    img = await get_img_from_url('https://i.imgur.com/3q8XLDP.png')
    assert not is_black(img)
