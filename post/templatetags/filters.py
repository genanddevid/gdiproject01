from django import template
import re

register = template.Library()

@register.filter
def tiktok_id(url):
    match = re.search(r'/video/(\d+)', url)
    return match.group(1) if match else ''


@register.filter
def fix_twitter_url(value):
    if value and "x.com" in value:
        return value.replace("x.com", "twitter.com")
    return value
