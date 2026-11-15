from django import template

from notifications.feed import badge_for_user

register = template.Library()


@register.simple_tag(takes_context=True)
def notifications_badge(context) -> str:
    request = context.get("request")
    if request is None:
        return ""
    return badge_for_user(request.user)
