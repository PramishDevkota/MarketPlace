from django import template

register = template.Library()


@register.filter
def npr(value):
    try:
        return f"Rs. {float(value):,.2f}"
    except (ValueError, TypeError):
        return value
