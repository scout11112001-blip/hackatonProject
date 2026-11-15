"""Chat views: student dialog, staff inbox, and polling fragments."""

import re
import uuid

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView, View

from accounts.access import StaffRequiredMixin, StudentRequiredMixin

from .constants import (
    HISTORY_LIMIT,
    POLL_INTERVAL_SECONDS,
    POLL_MAX_ERRORS,
)
from .forms import MessageForm
from .models import Dialog
from .selectors import dialogs_visible_to, staff_dialog_list
from .services import (
    load_history,
    mark_read,
    messages_after,
    send_staff_message,
    send_student_message,
)

EMPTY_TEXT = "Сообщений пока нет. Напишите вопрос — ответит сотрудник деканата вашего факультета."

_AFTER_RE = re.compile(r"^\d{1,18}$")


def _history_context(dialog, viewer_is_student, poll_url, refresh_url) -> dict:
    messages, truncated = load_history(dialog)
    return {
        "messages": messages,
        "truncated": truncated,
        "poll_url": poll_url,
        "poll_ms": POLL_INTERVAL_SECONDS * 1000,
        "poll_max_errors": POLL_MAX_ERRORS,
        "history_limit": HISTORY_LIMIT,
        "viewer_is_student": viewer_is_student,
        "student_name": dialog.student.full_name,
        "client_token": uuid.uuid4(),
        "refresh_url": refresh_url,
    }


def _empty_history(viewer_is_student, poll_url, refresh_url, student_name="") -> dict:
    return {
        "messages": [],
        "truncated": False,
        "poll_url": poll_url,
        "poll_ms": POLL_INTERVAL_SECONDS * 1000,
        "poll_max_errors": POLL_MAX_ERRORS,
        "history_limit": HISTORY_LIMIT,
        "viewer_is_student": viewer_is_student,
        "student_name": student_name,
        "client_token": uuid.uuid4(),
        "refresh_url": refresh_url,
    }


@method_decorator(never_cache, name="dispatch")
class StudentChatView(StudentRequiredMixin, TemplateView):
    template_name = "chat/student.html"
    http_method_names = ["get", "post"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dialog = Dialog.objects.filter(student=self.profile).first()
        poll_url = reverse("chat:student_updates")
        refresh_url = reverse("chat:student")
        if dialog is not None:
            context.update(_history_context(dialog, True, poll_url, refresh_url))
        else:
            context.update(_empty_history(True, poll_url, refresh_url, self.profile.full_name))
        context["dialog"] = dialog
        context["form"] = MessageForm()
        context["faculty_name"] = self.profile.group.program.faculty.name
        context["form_action"] = reverse("chat:student")
        context["form_label"] = "Сообщение"
        context["empty_text"] = EMPTY_TEXT
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        dialog = context["dialog"]
        if dialog is not None and context["messages"]:
            mark_read(dialog.pk, "student", context["messages"][-1].pk)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        form = MessageForm(request.POST)
        if form.is_valid():
            try:
                send_student_message(
                    self.profile, form.cleaned_data["text"], form.cleaned_data["client_token"]
                )
            except ValidationError as exc:
                form.add_error(None, ValidationError(exc.messages))
            else:
                return redirect(reverse("chat:student") + "#chat-form")
        context = self.get_context_data(**kwargs)
        context["form"] = form
        return self.render_to_response(context)


@method_decorator(never_cache, name="dispatch")
class StudentChatUpdatesView(StudentRequiredMixin, View):
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        after = request.GET.get("after", "")
        if not _AFTER_RE.fullmatch(after):
            return HttpResponseBadRequest()
        dialog = Dialog.objects.filter(student=self.profile).first()
        if dialog is None:
            return HttpResponse(status=204)
        rows = messages_after(dialog, int(after))
        if not rows:
            return HttpResponse(status=204)
        mark_read(dialog.pk, "student", rows[-1].pk)
        response = render(
            request, "chat/_messages.html", {"messages": rows, "viewer_is_student": True}
        )
        response["X-Chat-Fragment"] = "1"
        response["Content-Type"] = "text/html; charset=utf-8"
        return response


@method_decorator(never_cache, name="dispatch")
class StaffChatListView(StaffRequiredMixin, TemplateView):
    template_name = "chat/staff_list.html"
    http_method_names = ["get"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dialogs"] = staff_dialog_list(self.request.user)
        return context


@method_decorator(never_cache, name="dispatch")
class StaffDialogView(StaffRequiredMixin, TemplateView):
    template_name = "chat/staff_dialog.html"
    http_method_names = ["get", "post"]

    def get_object(self):
        return get_object_or_404(
            dialogs_visible_to(self.request.user).select_related(
                "student__group__program__faculty"
            ),
            public_id=self.kwargs["public_id"],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dialog = self.get_object()
        poll_url = reverse("chat:staff_updates", args=[dialog.public_id])
        refresh_url = reverse("chat:staff_dialog", args=[dialog.public_id])
        context["dialog"] = dialog
        context.update(_history_context(dialog, False, poll_url, refresh_url))
        context["form"] = MessageForm()
        context["form_action"] = refresh_url
        context["form_label"] = "Ответ"
        context["empty_text"] = ""
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if context["messages"]:
            mark_read(context["dialog"].pk, "staff", context["messages"][-1].pk)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        dialog = self.get_object()
        form = MessageForm(request.POST)
        if form.is_valid():
            try:
                send_staff_message(
                    dialog,
                    request.user,
                    form.cleaned_data["text"],
                    form.cleaned_data["client_token"],
                )
            except (ValidationError, PermissionDenied) as exc:
                if isinstance(exc, ValidationError):
                    form.add_error(None, ValidationError(exc.messages))
                else:
                    raise
            else:
                return redirect(
                    reverse("chat:staff_dialog", args=[dialog.public_id]) + "#chat-form"
                )
        context = self.get_context_data(**kwargs)
        context["form"] = form
        return self.render_to_response(context)


@method_decorator(never_cache, name="dispatch")
class StaffDialogUpdatesView(StaffRequiredMixin, View):
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        after = request.GET.get("after", "")
        if not _AFTER_RE.fullmatch(after):
            return HttpResponseBadRequest()
        dialog = get_object_or_404(dialogs_visible_to(request.user), public_id=kwargs["public_id"])
        rows = messages_after(dialog, int(after))
        if not rows:
            return HttpResponse(status=204)
        mark_read(dialog.pk, "staff", rows[-1].pk)
        response = render(
            request,
            "chat/_messages.html",
            {
                "messages": rows,
                "viewer_is_student": False,
                "student_name": dialog.student.full_name,
            },
        )
        response["X-Chat-Fragment"] = "1"
        response["Content-Type"] = "text/html; charset=utf-8"
        return response
