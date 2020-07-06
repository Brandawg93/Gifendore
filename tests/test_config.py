from core.config import config


def test_init_reddit():
    assert config.r


def test_get_mods():
    user = config.r.user.me()
    assert user in config.moderators
