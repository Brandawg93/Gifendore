from core.inbox import InboxItem
from core.config import config


def test_should_send_pointers_good():
    comment = config.r.comment('evc54r3')
    comment.subject = 'reply'
    inbox_item = InboxItem(comment)
    assert inbox_item.should_send_pointers()


def test_should_send_pointers_bad():
    comment = config.r.comment('fgn4skf')
    comment.subject = 'reply'
    inbox_item = InboxItem(comment)
    assert not inbox_item.should_send_pointers()
