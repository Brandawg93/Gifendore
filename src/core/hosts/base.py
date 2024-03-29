import re
import urllib.parse
import logging

logger = logging.getLogger("gifendore")


class BaseHost:
    def __init__(self, url_text, inbox_item, regex=r''):
        """Base host class."""
        self.url_text = url_text
        self.regex = re.compile(regex, re.I)
        self.inbox_item = inbox_item
        self.vid_url = None
        self.gif_url = None
        self.img_url = None
        self.name = None

    def is_host(self, url):
        """Return if the class is the correct host."""
        return self.url_text in url

    def get_info(self):
        """Get the media info."""
        return self.vid_url, self.gif_url, self.img_url, self.name

    def get_preview(self):
        """Get the preview url from reddit."""
        submission = self.inbox_item.submission
        fallback_url = None
        variant_url = None
        fallback_size = 0
        variant_size = 0
        if hasattr(submission, 'preview'):
            preview = submission.preview
            if 'reddit_video_preview' in preview:
                reddit_video_preview = preview['reddit_video_preview']
                if 'fallback_url' in reddit_video_preview and 'transcoding_status' in reddit_video_preview:
                    transcoding_status = reddit_video_preview['transcoding_status']
                    if transcoding_status == 'completed':
                        fallback_url = reddit_video_preview['fallback_url']
                        fallback_size = reddit_video_preview['width'] + reddit_video_preview['height']
            if 'images' in preview:
                images = preview['images']
                if len(images) > 0:
                    first = images[0]
                    if 'variants' in first:
                        variants = first['variants']
                        if 'mp4' in variants:
                            mp4 = variants['mp4']
                            if 'source' in mp4:
                                source = mp4['source']
                                if 'url' in source:
                                    variant_url = urllib.parse.unquote(source['url'])
                                    variant_size = source['width'] + source['height']
        if fallback_size == 0 and variant_size == 0:
            return None
        if fallback_size >= variant_size:
            logger.debug("getting media from fallback_url")
            return fallback_url
        else:
            logger.debug("getting media from variant")
            return variant_url

    def get_details(self, url):
        """Set the media info."""
        raise NotImplementedError('get_details has not been implemented')
