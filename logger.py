import logging
from sentry_sdk import configure_scope, capture_exception


def _set_scope(inbox_item, level='error'):
    with configure_scope() as scope:
        scope.set_level(level)
        if inbox_item:
            scope.set_user({"username": inbox_item.item.author.name, "id": inbox_item.item.author.id})
            scope.set_extra("subreddit", inbox_item.item.submission.subreddit.display_name)
            scope.set_extra("submission", inbox_item.submission.shortlink)
            scope.set_extra("mention", inbox_item.item.body)


class MyLogger(logging.Logger):
    def __init__(self, name, level=logging.NOTSET):
        """Initialize custom logger."""
        super(MyLogger, self).__init__(name, level)

    def warning(self, msg, *args, inbox_item=None, **kwargs):
        _set_scope(inbox_item, level='warning')
        capture_exception(msg)

        return super(MyLogger, self).warning(msg, *args, **kwargs)

    def exception(self, msg, *args, exc_info=True, inbox_item=None, **kwargs):
        _set_scope(inbox_item)
        capture_exception(msg)

        return super(MyLogger, self).exception(msg, *args, exc_info=exc_info, **kwargs)
