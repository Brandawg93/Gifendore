from core.inbox import InboxItem
from core.config import config
from core.hosts import Host, upload_video, upload_image
from PIL import Image
from os import path, remove


def create_host(comment_id, subject='username mention'):
    """Create a host from a comment"""
    comment = config.r.comment(comment_id)
    comment.subject = subject
    inbox_item = InboxItem(comment)
    return Host(inbox_item)


def test_set_media_details_one():
    """Gfycat"""
    vid_url = 'https://giant.gfycat.com/PeacefulPotableHochstettersfrog.mp4'
    name = 'PeacefulPotableHochstettersfrog'
    host = create_host('f87u2bi')
    host.set_media_details()
    assert host.vid_url == vid_url and not host.gif_url and not host.img_url and host.name == name


def test_set_media_details_one_alt():
    """Gfycat"""
    vid_url = 'https://giant.gfycat.com/PeacefulPotableHochstettersfrog.mp4'
    name = 'PeacefulPotableHochstettersfrog'
    host = create_host('f87u2bi')
    _ = host.inbox_item.submission.preview
    delattr(host.inbox_item.submission, 'preview')
    host.set_media_details()
    assert host.vid_url == vid_url and not host.gif_url and not host.img_url and host.name == name


def test_set_media_details_two():
    """vReddit"""
    vid_url = 'https://v.redd.it/g9nttzcty1031/DASH_480?source=fallback'
    name = 'bsbhhm'
    host = create_host('f55shpf')
    host.set_media_details()
    assert host.vid_url == vid_url and not host.gif_url and not host.img_url and host.name == name


def test_set_media_details_three():
    """iReddit"""
    vid_url = 'https://preview.redd.it/q6r8gnhkiym21.gif?format=mp4&s=066d0f888ac3fca23de912e6f2268ac3cfcef066'
    gif_url = 'https://i.redd.it/q6r8gnhkiym21.gif'
    name = 'b2pbl5'
    host = create_host('ez7yphl')
    host.set_media_details()
    assert host.vid_url == vid_url and host.gif_url == gif_url and not host.img_url and host.name == name


def test_set_media_details_four():
    """Imgur"""
    vid_url = 'https://i.imgur.com/v0iFRq1.mp4'
    name = 'v0iFRq1'
    host = create_host('ez7y6dd')
    host.set_media_details()
    assert host.vid_url == vid_url and not host.gif_url and not host.img_url and host.name == name


def test_set_media_details_four_alt():
    """Imgur"""
    vid_url = 'https://i.imgur.com/v0iFRq1.mp4'
    name = 'v0iFRq1'
    host = create_host('ez7y6dd')
    _ = host.inbox_item.submission.preview
    delattr(host.inbox_item.submission, 'preview')
    host.set_media_details()
    assert host.vid_url == vid_url and not host.gif_url and not host.img_url and host.name == name


def test_set_media_details_five():
    """Streamable"""
    name = 'agccr'
    host = create_host('fgpd8ug')
    host.set_media_details()
    assert 'video/mp4/agccr.mp4' in host.vid_url and not host.gif_url and not host.img_url and host.name == name


def test_set_media_details_six():
    """Youtube"""
    img_url = "https://img.youtube.com/vi/ebHqWaaLVdw/maxresdefault.jpg"
    name = 'ebHqWaaLVdw'
    host = create_host('f4rrsvj')
    host.set_media_details()
    assert not host.vid_url and not host.gif_url and host.img_url == img_url and host.name == name


def test_set_media_details_seven():
    """Generic"""
    vid_url = "https://external-preview.redd.it/D-jCWANkdTRqKk3I8BaAMQq9MIGR_S5_1h39EcBEuDA.gif?format=mp4&s=447f2485db3e767f1fe72834d30a4c4c7e0fb309"
    name = 'http:__www.slate.com_content_dam_slate_blogs_the_vault_2014_06_17_newmap.gif'
    host = create_host('f0phdv0')
    host.set_media_details()
    assert host.vid_url == vid_url and not host.gif_url and not host.img_url and host.name == name


def test_get_image_one():
    """vid_url"""
    vid_url = 'https://preview.redd.it/qpmq6jpb7pq21.gif?format=mp4&s=907f91fc3433d42c4a21df7382621ac542a77b00'
    host = create_host('ekaavid')
    seconds = '1.2'
    host.vid_url = vid_url
    img, seconds = host.get_image(seconds)
    assert isinstance(img, Image.Image) and seconds == 1.2


def test_get_image_two():
    """gif_url"""
    gif_url = 'https://i.redd.it/q6r8gnhkiym21.gif'
    host = create_host('ez7yphl')
    host.gif_url = gif_url
    seconds = None
    img, seconds = host.get_image(seconds)
    assert isinstance(img, Image.Image)


def test_get_image_three():
    """img_url"""
    img_url = "https://img.youtube.com/vi/ebHqWaaLVdw/maxresdefault.jpg"
    host = create_host('f4rrsvj')
    seconds = None
    host.img_url = img_url
    img, seconds = host.get_image(seconds)
    assert isinstance(img, Image.Image)


def test_get_image_with_upload():
    """Image with upload"""
    vid_url = 'https://preview.redd.it/qpmq6jpb7pq21.gif?format=mp4&s=907f91fc3433d42c4a21df7382621ac542a77b00'
    host = create_host('ekaavid')
    host.vid_url = vid_url
    seconds = None
    img, seconds = host.get_image(seconds)
    url = upload_image(img)
    assert 'imgur' in url and seconds == 0.0


def test_get_slo_mo():
    """Slow mo"""
    vid_url = 'https://preview.redd.it/qpmq6jpb7pq21.gif?format=mp4&s=907f91fc3433d42c4a21df7382621ac542a77b00'
    host = create_host('ekaavid')
    host.vid_url = vid_url
    speed = None
    filename, speed = host.get_slo_mo(speed)
    worked = path.isfile(filename)
    remove(filename)
    assert worked and speed == 2.0


def test_get_freeze():
    """Freeze"""
    vid_url = 'https://preview.redd.it/qpmq6jpb7pq21.gif?format=mp4&s=907f91fc3433d42c4a21df7382621ac542a77b00'
    host = create_host('ekaavid')
    host.vid_url = vid_url
    filename = host.get_freeze()
    worked = path.isfile(filename)
    remove(filename)
    assert worked


def test_get_reverse():
    """Reverse"""
    vid_url = 'https://preview.redd.it/qpmq6jpb7pq21.gif?format=mp4&s=907f91fc3433d42c4a21df7382621ac542a77b00'
    host = create_host('ekaavid')
    host.vid_url = vid_url
    filename = host.get_reverse()
    worked = path.isfile(filename)
    remove(filename)
    assert worked


def test_get_reverse_with_upload():
    """Reverse with upload"""
    vid_url = 'https://preview.redd.it/qpmq6jpb7pq21.gif?format=mp4&s=907f91fc3433d42c4a21df7382621ac542a77b00'
    host = create_host('ekaavid')
    host.vid_url = vid_url
    filename = host.get_reverse()
    url = upload_video(filename, host.inbox_item)
    assert 'gfycat' in url


def test_get_section_one():
    """Section"""
    vid_url = 'https://preview.redd.it/qpmq6jpb7pq21.gif?format=mp4&s=907f91fc3433d42c4a21df7382621ac542a77b00'
    host = create_host('ekaavid')
    host.vid_url = vid_url
    section = ('*', '2.2')
    filename = host.get_section(section)
    worked = path.isfile(filename)
    remove(filename)
    assert worked


def test_get_section_two():
    """Section"""
    vid_url = 'https://preview.redd.it/qpmq6jpb7pq21.gif?format=mp4&s=907f91fc3433d42c4a21df7382621ac542a77b00'
    host = create_host('ekaavid')
    host.vid_url = vid_url
    section = ('2.2', '*')
    filename = host.get_section(section)
    worked = path.isfile(filename)
    remove(filename)
    assert worked
