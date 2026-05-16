from django import template

register = template.Library()


@register.filter
def hours_to_dh(value):
    """Format decimal hours as 'Xd Y,ZZh'. E.g. 39.15 → '4d 7,15h'."""
    try:
        h = float(value)
    except (TypeError, ValueError):
        return value
    if h <= 0:
        return '0h'
    days = int(h // 8)
    frac = round(h % 8, 2)
    frac_str = f'{frac:.2f}'.replace('.', ',')
    if days == 0:
        return f'{frac_str}h'
    if frac < 0.005:
        return f'{days}d'
    return f'{days}d {frac_str}h'
