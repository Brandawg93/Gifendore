from core.hosts import get_img_from_url
from core.media.base import is_black


def test_is_black_one():
    """Black image"""
    img = get_img_from_url('https://i.imgur.com/ZDNqE6p.png')
    assert is_black(img)


def test_is_black_two():
    """Non-black image"""
    img = get_img_from_url('https://i.imgur.com/3q8XLDP.png')
    assert not is_black(img)
