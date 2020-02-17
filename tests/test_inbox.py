from core.inbox import InboxItem
from core.config import config


def create_item(item_id, subject='username mention', item_type='comment'):
    """Create an inbox item from a comment."""
    if item_type == 'comment':
        item = config.r.comment(item_id)
        item.subject = subject
    else:
        item = config.r.submission(item_id)
        item.subject = subject
    return InboxItem(item)


def test_should_send_pointers_one():
    """10 points to gifendore!"""
    inbox_item = create_item('evc54r3', subject='reply')
    assert inbox_item.should_send_pointers()


def test_should_send_pointers_two():
    """This shouldn't work"""
    inbox_item = create_item('fgn4skf', subject='reply')
    assert not inbox_item.should_send_pointers()


def test_get_seconds_one():
    """u/gifendore_testing"""
    inbox_item = create_item('fgno4pu')
    assert not inbox_item.get_seconds()


def test_get_seconds_two():
    """u/gifendore_testing 2"""
    inbox_item = create_item('fgno54m')
    assert inbox_item.get_seconds() == '2'


def test_get_seconds_three():
    """u/gifendore_testing -2"""
    inbox_item = create_item('fgno5tv')
    assert inbox_item.get_seconds() == '-2'


def test_get_seconds_four():
    """I think u/gifendore_testing 2 gets the second to last frame."""
    inbox_item = create_item('fgnqag5')
    assert inbox_item.get_seconds() == '2'


def test_get_seconds_five():
    """u/Gifendore_Testing -24"""
    inbox_item = create_item('fgp3zzo')
    assert inbox_item.get_seconds() == '-24'


def test_get_seconds_six():
    """Submission"""
    inbox_item = create_item('dmxo7i', item_type='submission')
    assert not inbox_item.get_seconds()


def test_get_seconds_seven():
    """u/gifendore_testing [-2]"""
    inbox_item = create_item('fgno5tv')
    assert inbox_item.get_seconds() == '-2'


def test_get_command_one():
    """u/gifendore_testing reverse"""
    inbox_item = create_item('fgnod32')
    assert inbox_item.get_command() == 'reverse'


def test_get_command_two():
    """u/gifendore_testing slowmo"""
    inbox_item = create_item('fgnogp7')
    assert inbox_item.get_command() == 'slowmo'


def test_get_command_three():
    """u/gifendore_testing freeze"""
    inbox_item = create_item('fgnoh8t')
    assert inbox_item.get_command() == 'freeze'


def test_get_command_four():
    """Can u/gifendore_testing freeze this for me?"""
    inbox_item = create_item('fgp3nk6')
    assert inbox_item.get_command() == 'freeze'


def test_get_command_five():
    """can u/gifendore_testing reverse this please?"""
    inbox_item = create_item('fgnoe72')
    assert inbox_item.get_command() == 'reverse'


def test_get_commands_footer():
    """can u/gifendore_testing reverse this please?"""
    inbox_item = create_item('fgnoe72')
    footer = inbox_item.get_commands_footer(inbox_item.item.id)
    assert footer


def test_get_message_command():
    """can u/gifendore_testing reverse this please?"""
    inbox_item = create_item('fgnoe72')
    inbox_item.item.subject = 'Edit test'
    command, comment = inbox_item.get_message_command()
    assert command == 'edit' and comment == 'test'


def test_get_section_one():
    """u/gifendore_testing section"""
    inbox_item = create_item('fgnsbov')
    assert not inbox_item.get_section()


def test_get_section_two():
    """u/gifendore_testing section 2-4"""
    inbox_item = create_item('fgnog34')
    assert inbox_item.get_section() == ('2', '4')


def test_get_section_three():
    """u/gifendore_testing section 4-* is what you're looking for."""
    inbox_item = create_item('fgo1kq9')
    assert inbox_item.get_section() == ('4', '*')
