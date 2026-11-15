from django import template

from chat.constants import CHAT_BADGE_CAP
from chat.selectors import student_unread_count

register = template.Library()


@register.simple_tag(takes_context=True)
def chat_unread_badge(context) -> str:
    request = context.get("request")
    if request is None:
        return ""
    count = student_unread_count(request.user)
    if count == 0:
        return ""
    if count > CHAT_BADGE_CAP:
        return f"{CHAT_BADGE_CAP}+"
    return str(count)
