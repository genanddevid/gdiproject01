import base64
from django import template

register = template.Library()

@register.filter
def b64encode(file):
    return base64.b64encode(file).decode('utf-8')
