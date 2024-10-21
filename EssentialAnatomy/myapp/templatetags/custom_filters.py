# myapp/templatetags/custom_filters.py

import urllib.parse
from django import template

register = template.Library()

@register.filter
def custom_slugify(value):
    value = value.replace('&', 'andsign').replace(',', 'comma').replace(' ', '-').replace('+', 'plus')
    return urllib.parse.quote_plus(value)
