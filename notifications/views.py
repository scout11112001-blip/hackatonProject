from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView, View

from accounts.access import StaffRequiredMixin, StudentRequiredMixin
from accounts.selectors import groups_visible_to

from .constants import DEADLINES_MAX_ITEMS, STAFF_LIST_MAX_ITEMS
from .feed import build_feed, student_context, upcoming_deadlines
from .forms import AnnouncementForm
from .models import Announcement
from .selectors import announcements_managed_by
from .services import create_announcement, mark_seen, unpublish_announcement


@method_decorator(never_cache, name="dispatch")
class NotificationsView(StudentRequiredMixin, TemplateView):
    template_name = "notifications/feed.html"
    http_method_names = ["get"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ctx = student_context(self.request.user)
        if ctx is None:
            raise PermissionDenied
        context["deadlines"] = upcoming_deadlines(ctx, DEADLINES_MAX_ITEMS)
        context["items"] = build_feed(ctx)
        mark_seen(ctx.user_id, ctx.now)
        return context


class StaffAnnouncementsView(StaffRequiredMixin, TemplateView):
    template_name = "notifications/staff_list.html"
    http_method_names = ["get", "post"]

    def _form(self, data=None):
        return AnnouncementForm(
            data,
            groups=list(groups_visible_to(self.request.user).order_by("name")),
            today=timezone.localdate(),
        )

    def _render(self, form):
        announcements = (
            announcements_managed_by(self.request.user)
            .select_related("faculty", "group")
            .order_by("-published_at", "-pk")[:STAFF_LIST_MAX_ITEMS]
        )
        return self.render_to_response(
            self.get_context_data(form=form, announcements=announcements)
        )

    def get(self, request, *args, **kwargs):
        return self._render(self._form())

    def post(self, request, *args, **kwargs):
        form = self._form(request.POST)
        if form.is_valid():
            try:
                create_announcement(
                    request.user,
                    title=form.cleaned_data["title"],
                    body=form.cleaned_data["body"],
                    audience=form.cleaned_data["audience"],
                    group=form.cleaned_data["group"],
                    deadline=form.cleaned_data["deadline"],
                )
            except ValidationError as exc:
                form.add_error(None, ValidationError(exc.messages))
            else:
                messages.success(request, "Объявление опубликовано.")
                return redirect("notifications:staff_announcements")
        return self._render(form)


class StaffUnpublishView(StaffRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, public_id):
        try:
            changed = unpublish_announcement(request.user, public_id)
        except Announcement.DoesNotExist:
            raise Http404 from None
        if changed:
            messages.success(request, "Объявление снято с публикации.")
        else:
            messages.info(request, "Объявление уже снято с публикации.")
        return redirect("notifications:staff_announcements")
