import pytest
from core.media import Video
from core.inbox import InboxItem
from core.config import config
from core.hosts import Host
from os import path, remove
from PIL import Image

COMMENT = 'fbvqfx0'


def create_item(comment_id, subject='username mention'):
    """Create an inbox item from a comment."""
    comment = config.r.comment(comment_id)
    comment.subject = subject
    return InboxItem(comment)


async def create_video():
    """Create a video object from a host."""
    host = Host(create_item(COMMENT))
    await host.set_media_details()
    return Video(host.vid_url)


@pytest.mark.asyncio
async def test_extract_frame():
    host = Host(create_item(COMMENT))
    await host.set_media_details()
    video = Video(host.vid_url)
    image, seconds = await video.extract_frame()
    assert isinstance(image, Image.Image) and seconds == 1.0


@pytest.mark.asyncio
async def test_section():
    video = await create_video()
    filename = await video.section('\\*', '2')
    worked = path.isfile(filename)
    remove(filename)
    assert worked


@pytest.mark.asyncio
async def test_slow_mo():
    video = await create_video()
    filename, speed = await video.slow_mo()
    worked = path.isfile(filename)
    remove(filename)
    assert worked and speed == 2.0


@pytest.mark.asyncio
async def test_freeze():
    video = await create_video()
    filename = await video.freeze()
    worked = path.isfile(filename)
    remove(filename)
    assert worked


@pytest.mark.asyncio
async def test_reverse():
    video = await create_video()
    filename = await video.reverse()
    worked = path.isfile(filename)
    remove(filename)
    assert worked
