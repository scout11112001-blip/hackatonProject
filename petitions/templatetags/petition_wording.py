"""Template filters for kind-aware wording (TASK-017)."""

from django import template

from petitions import wording

register = template.Library()


@register.filter
def status_for(status: str, kind: str) -> str:
    """{{ petition.status|status_for:petition.request_type.kind }}"""
    return wording.status_label(status, kind)


@register.filter
def kind_text(kind: str, key: str) -> str:
    """{{ request_type.kind|kind_text:"submit" }}"""
    return wording.text(kind, key)
