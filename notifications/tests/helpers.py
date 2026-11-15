"""Test helpers for the notifications app (reuse accounts helpers)."""

from types import SimpleNamespace

from django.utils import timezone

from accounts.models import User
from accounts.tests.helpers import make_faculty, make_group, make_staff, make_student
from notifications.models import Announcement, NotificationState


def make_announcement(
    author,
    *,
    audience,
    faculty=None,
    group=None,
    title="Объявление",
    body="Текст объявления",
    deadline=None,
    published_at=None,
    is_published=True,
) -> Announcement:
    ts = published_at or timezone.now()
    kwargs = {
        "author": author,
        "audience": audience,
        "faculty": faculty,
        "group": group,
        "title": title,
        "body": body,
        "deadline": deadline,
        "published_at": ts,
        "is_published": is_published,
    }
    if not is_published:
        kwargs["unpublished_at"] = ts
        kwargs["unpublished_by"] = author
    return Announcement.objects.create(**kwargs)


def set_seen(user, when) -> None:
    NotificationState.objects.update_or_create(user=user, defaults={"seen_until": when})


def make_world() -> SimpleNamespace:
    fx = make_faculty("FX")
    fy = make_faculty("FY")
    gx1 = make_group(fx, "GX1")
    gx2 = make_group(fx, "GX2")
    gy1 = make_group(fy, "GY1")
    ax = make_student("ax", gx1, "ST-AX-1")
    bx = make_student("bx", gx1, "ST-BX-1")
    cx = make_student("cx", gx2, "ST-CX-1")
    ay = make_student("ay", gy1, "ST-AY-1")
    sx = make_staff("sx", fx)
    sy = make_staff("sy", fy)
    root = User.objects.create_superuser("root", password="Super-Pass-2026!")
    return SimpleNamespace(
        fx=fx,
        fy=fy,
        gx1=gx1,
        gx2=gx2,
        gy1=gy1,
        ax=ax,
        bx=bx,
        cx=cx,
        ay=ay,
        sx=sx,
        sy=sy,
        root=root,
        ax_profile=ax.student_profile,
        bx_profile=bx.student_profile,
        cx_profile=cx.student_profile,
        ay_profile=ay.student_profile,
        sx_profile=sx.staff_profile,
        sy_profile=sy.staff_profile,
    )
