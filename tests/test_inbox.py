from core.inbox import InboxItem
from core.config import config


def create_item(comment_id, subject='username mention'):
    comment = config.r.comment(comment_id)
    comment.subject = subject
    return InboxItem(comment)


def test_should_send_pointers_one():
    inbox_item = create_item('evc54r3', subject='reply')
    assert inbox_item.should_send_pointers()


def test_should_send_pointers_two():
    inbox_item = create_item('fgn4skf', subject='reply')
    assert not inbox_item.should_send_pointers()


def test_get_seconds_one():
    inbox_item = create_item('fgno4pu')
    assert not inbox_item.get_seconds()


def test_get_seconds_two():
    inbox_item = create_item('fgno54m')
    assert inbox_item.get_seconds() == 2


def test_get_seconds_three():
    inbox_item = create_item('fgno5tv')
    assert inbox_item.get_seconds() == 2


def test_get_seconds_four():
    inbox_item = create_item('fgnqag5')
    assert inbox_item.get_seconds() == 2


def test_get_command_one():
    inbox_item = create_item('fgnod32')
    assert inbox_item.get_command() == 'reverse'


def test_get_command_two():
    inbox_item = create_item('fgnogp7')
    assert inbox_item.get_command() == 'slowmo'


def test_get_command_three():
    inbox_item = create_item('fgnoh8t')
    assert inbox_item.get_command() == 'freeze'


def test_get_section_one():
    inbox_item = create_item('fgnsbov')
    assert not inbox_item.get_section()


def test_get_section_two():
    inbox_item = create_item('fgnog34')
    assert inbox_item.get_section() == ('2', '4')


def test_get_section_three():
    inbox_item = create_item('fgo1kq9')
    assert inbox_item.get_section() == ('4', '*')
