import pytest
from core.inbox import InboxItem
from core.config import config
from core.hosts import Host


def create_host(comment_id, subject='username mention'):
    """Create a host from a comment"""
    comment = config.r.comment(comment_id)
    comment.subject = subject
    inbox_item = InboxItem(comment)
    return Host(inbox_item)


@pytest.mark.asyncio
async def test_set_media_details_one():
    """Gfycat"""
    vid_url = 'https://v.redd.it/plisrak5t9431/DASH_360'
    name = 'PeacefulPotableHochstettersfrog'
    host = create_host('f87u2bi')
    await host.set_media_details()
    assert host.vid_url == vid_url and not host.gif_url and not host.img_url and host.name == name


@pytest.mark.asyncio
async def test_set_media_details_two():
    """vReddit"""
    vid_url = 'https://v.redd.it/g9nttzcty1031/DASH_480?source=fallback'
    name = 'bsbhhm'
    host = create_host('f55shpf')
    await host.set_media_details()
    assert host.vid_url == vid_url and not host.gif_url and not host.img_url and host.name == name


@pytest.mark.asyncio
async def test_set_media_details_three():
    """iReddit"""
    vid_url = 'https://preview.redd.it/qpmq6jpb7pq21.gif?format=mp4&s=907f91fc3433d42c4a21df7382621ac542a77b00'
    gif_url = 'https://i.redd.it/qpmq6jpb7pq21.gif'
    name = 'bab7s1'
    host = create_host('ekaavid')
    await host.set_media_details()
    assert host.vid_url == vid_url and host.gif_url == gif_url and not host.img_url and host.name == name


@pytest.mark.asyncio
async def test_set_media_details_four():
    """Imgur"""
    vid_url = 'https://v.redd.it/es93vjo7h5s21/DASH_480'
    name = 'v0iFRq1'
    host = create_host('ekjl1ar')
    await host.set_media_details()
    assert host.vid_url == vid_url and not host.gif_url and not host.img_url and host.name == name


@pytest.mark.asyncio
async def test_set_media_details_five():
    """Streamable"""
    name = 'agccr'
    host = create_host('fgpd8ug')
    await host.set_media_details()
    assert 'video/mp4/agccr.mp4' in host.vid_url and not host.gif_url and not host.img_url and host.name == name


@pytest.mark.asyncio
async def test_set_media_details_six():
    """Youtube"""
    img_url = "https://img.youtube.com/vi/ebHqWaaLVdw/maxresdefault.jpg"
    name = 'ebHqWaaLVdw'
    host = create_host('f4rrsvj')
    await host.set_media_details()
    assert not host.vid_url and not host.gif_url and host.img_url == img_url and host.name == name
