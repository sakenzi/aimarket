from django import template
from django.utils.safestring import mark_safe


register = template.Library()


@register.filter
def get_item(mapping, key):
    if not mapping:
        return ''
    return mapping.get(key, '')


@register.filter
def with_placeholder(bound_field, placeholder):
    return mark_safe(bound_field.as_widget(attrs={'placeholder': placeholder or ''}))
