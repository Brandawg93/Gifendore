import logging
from sentry_sdk import configure_scope


class MyLogger(logging.Logger):
    def __init__(self, name, level=logging.NOTSET):
        super(MyLogger, self).__init__(name, level)

    def warning(self, msg, *args, **kwargs):
        with configure_scope() as scope:
            scope.set_level('warning')

        return super(MyLogger, self).warning(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        with configure_scope() as scope:
            scope.set_level('debug')

        return super(MyLogger, self).debug(msg, *args, **kwargs)

    def exception(self, msg, *args, exc_info=True, inbox_item=None, **kwargs):
        with configure_scope() as scope:
            if inbox_item:
                scope.set_user({"username": inbox_item.item.author.name, "id": inbox_item.item.author.id})
                scope.set_extra("subreddit", inbox_item.item.submission.subreddit.display_name)
                scope.set_extra("submission", inbox_item.submission.shortlink)

        return super(MyLogger, self).exception(msg, *args, exc_info=exc_info, **kwargs)
