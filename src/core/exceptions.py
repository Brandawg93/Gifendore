class Error(Exception):
    pass


class InvalidHostError(Error):
    pass


class InvalidURLError(Error):
    pass


class ParseError(Error):
    pass


class UploadError(Error):
    pass


class VideoNotFoundError(Error):
    pass
