from django import template
import re
from urllib.parse import urlparse, parse_qs

register = template.Library()

@register.filter
def youtube_id(url):
    """
    Extract the YouTube video ID from various URL formats.
    Example:
    https://youtu.be/abc123 → abc123
    https://www.youtube.com/watch?v=abc123 → abc123
    """
    patterns = [
        r'youtu\.be/([^?&]+)',
        r'youtube\.com/watch\?v=([^?&]+)',
        r'youtube\.com/embed/([^?&]+)',
        r'youtube\.com/v/([^?&]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return ''
