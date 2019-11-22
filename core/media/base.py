import logging
from PIL import Image

logger = logging.getLogger("gifendore")


def is_black(img):
    try:
        threshold = 1.0
        r, g, b = img.resize((1, 1), Image.ANTIALIAS).getpixel((0, 0))
        average = (r + g + b) / 3
        logger.debug("average color is {}.".format(average))
        if average <= threshold:
            logger.info('Image too dark.')
        return average <= threshold
    except Exception as e:
        logger.exception(e)
        return False
