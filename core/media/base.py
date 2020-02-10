import logging
from constants import DIR
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("gifendore")
WATERMARK_TEXT = "u/gifendore"


def is_black(img):
    """Check if the image is mostly black"""
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


def add_watermark(img):
    """Add watermark to image"""
    alpha = 128
    draw = ImageDraw.Draw(img, "RGBA")
    profile = Image.open(DIR + '/images/profile.png', 'r')
    font = ImageFont.truetype(DIR + "/fonts/font.otf", 16)
    h_img, w_img = img.size
    w_text, h_text = draw.textsize(WATERMARK_TEXT, font=font)
    profile = profile.resize((h_text, h_text))
    h_profile, w_profile = profile.size
    profile.putalpha(alpha)
    img.paste(profile, (0, h_img - h_profile), profile)
    draw.rectangle((h_text, h_img - h_text, w_text + h_text, h_img), fill=(0, 0, 0, alpha))
    draw.text((h_text, h_img - h_text), WATERMARK_TEXT, (255, 255, 255, alpha), font=font)
