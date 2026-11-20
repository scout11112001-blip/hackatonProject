"""Views for the petitions app."""

import logging
import re

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Prefetch
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET
from django.views.generic import DetailView, FormView, ListView, TemplateView, View

from accounts.access import StaffRequiredMixin, StudentRequiredMixin, get_profile_for_role
from accounts.models import User
from petitions.forms import PetitionForm, StaffCommentForm, TransitionForm
from petitions.models import (
    STATUS_VALUES,
    Petition,
    PetitionComment,
    PetitionStatus,
    PetitionStatusChange,
    RequestKind,
    RequestType,
)
from petitions.selectors import attachments_visible_to, petitions_visible_to
from petitions.services import add_staff_comment, change_status, submit_petition
from petitions.workflow import ACTION_LABELS, OPEN_STATUSES, allowed_transitions

logger = logging.getLogger(__name__)

_TYPE_ID_RE = re.compile(r"[0-9]{1,18}")


class CatalogView(StudentRequiredMixin, TemplateView):
    template_name = "petitions/catalog.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        types = RequestType.objects.filter(is_active=True).order_by("subject_required", "name")
        context["certificates"] = types.filter(kind=RequestKind.CERTIFICATE)
        context["applications"] = types.filter(kind=RequestKind.APPLICATION)
        return context


class SubmitPetitionView(StudentRequiredMixin, FormView):
    template_name = "petitions/form.html"
    form_class = PetitionForm

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        self.profile = get_profile_for_role(request.user, User.Role.STUDENT)
        self.request_type = get_object_or_404(
            RequestType, pk=self.kwargs["type_id"], is_active=True
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request_type"] = self.request_type
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["request_type"] = self.request_type
        return context

    def form_valid(self, form):
        try:
            petition = submit_petition(
                self.profile,
                self.request_type,
                form.cleaned_data["comment"],
                form.cleaned_data["files"],
                subject=form.cleaned_data.get("subject", ""),
            )
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)
        return redirect("petitions:submitted", public_id=petition.public_id)


class SubmittedView(StudentRequiredMixin, DetailView):
    model = Petition
    template_name = "petitions/submitted.html"
    slug_field = "public_id"
    slug_url_kwarg = "public_id"

    def get_queryset(self):
        return petitions_visible_to(self.request.user)


class MyPetitionsView(StudentRequiredMixin, ListView):
    template_name = "petitions/my_list.html"
    context_object_name = "petitions"

    def get_queryset(self):
        return petitions_visible_to(self.request.user).order_by("-created_at")


class StudentPetitionDetailView(StudentRequiredMixin, DetailView):
    model = Petition
    template_name = "petitions/detail.html"
    slug_field = "public_id"
    slug_url_kwarg = "public_id"

    def get_queryset(self):
        return petitions_visible_to(self.request.user).prefetch_related(
            Prefetch(
                "history",
                queryset=PetitionStatusChange.objects.select_related("actor__staff_profile"),
            ),
            Prefetch(
                "staff_comments",
                queryset=PetitionComment.objects.select_related("author__staff_profile"),
            ),
            "attachments",
        )


class StaffQueueView(StaffRequiredMixin, ListView):
    template_name = "petitions/staff_queue.html"
    context_object_name = "petitions"

    def get_queryset(self):
        qs = petitions_visible_to(self.request.user)
        status = self.request.GET.get("status", "open")
        if status == "open":
            qs = qs.filter(status__in=OPEN_STATUSES)
        elif status == "all":
            pass
        elif status in STATUS_VALUES:
            qs = qs.filter(status=status)
        else:
            qs = qs.filter(status__in=OPEN_STATUSES)
        type_id = self.request.GET.get("type", "")
        # At most 18 digits: always inside the 64-bit id range of the database (PT1-F8).
        if _TYPE_ID_RE.fullmatch(type_id):
            qs = qs.filter(request_type_id=int(type_id))
        return qs.order_by("created_at").annotate(attachment_count=Count("attachments"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = [("open", "Открытые"), ("all", "Все")] + list(
            PetitionStatus.choices
        )
        context["selected_status"] = self.request.GET.get("status", "open")
        context["selected_type"] = self.request.GET.get("type", "")
        context["types"] = RequestType.objects.all()
        return context


class StaffPetitionDetailView(StaffRequiredMixin, DetailView):
    model = Petition
    template_name = "petitions/staff_detail.html"
    slug_field = "public_id"
    slug_url_kwarg = "public_id"

    def get_queryset(self):
        return (
            petitions_visible_to(self.request.user)
            .select_related("student__user")
            .prefetch_related(
                Prefetch(
                    "history",
                    queryset=PetitionStatusChange.objects.select_related("actor__staff_profile"),
                ),
                Prefetch(
                    "staff_comments",
                    queryset=PetitionComment.objects.select_related("author__staff_profile"),
                ),
                "attachments",
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        petition = self.object
        context["actions"] = [
            (status, ACTION_LABELS[status]) for status in allowed_transitions(petition.status)
        ]
        context["transition_form"] = TransitionForm(initial={"expected_status": petition.status})
        context["comment_form"] = StaffCommentForm()
        return context


def _flatten_form_errors(form) -> list[str]:
    return [str(err) for errors in form.errors.values() for err in errors]


class StaffTransitionView(StaffRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        petition = get_object_or_404(
            petitions_visible_to(request.user), public_id=kwargs["public_id"]
        )
        form = TransitionForm(request.POST)
        if not form.is_valid():
            messages.error(request, " ".join(_flatten_form_errors(form)))
            return redirect("petitions:staff_detail", public_id=petition.public_id)
        try:
            new = change_status(
                petition,
                request.user,
                form.cleaned_data["expected_status"],
                form.cleaned_data["new_status"],
                form.cleaned_data["comment"],
            )
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
            return redirect("petitions:staff_detail", public_id=petition.public_id)
        messages.success(request, f"Статус изменён: {dict(PetitionStatus.choices)[new.status]}.")
        return redirect("petitions:staff_detail", public_id=petition.public_id)


class StaffCommentView(StaffRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        petition = get_object_or_404(
            petitions_visible_to(request.user), public_id=kwargs["public_id"]
        )
        form = StaffCommentForm(request.POST)
        if not form.is_valid():
            messages.error(request, " ".join(_flatten_form_errors(form)))
            return redirect("petitions:staff_detail", public_id=petition.public_id)
        try:
            add_staff_comment(petition, request.user, form.cleaned_data["text"])
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("petitions:staff_detail", public_id=petition.public_id)


@require_GET
def download_attachment(request: HttpRequest, public_id, file_id) -> HttpResponse:
    att = get_object_or_404(
        attachments_visible_to(request.user).select_related("petition"),
        public_id=file_id,
        petition__public_id=public_id,
    )
    try:
        handle = att.file.open("rb")
    except FileNotFoundError:
        logger.warning("Attachment file is missing on disk (attachment %s).", att.public_id)
        raise Http404("Файл не найден.") from None
    response = FileResponse(
        handle,
        as_attachment=True,
        filename=att.original_name,
        content_type="application/pdf",
    )
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    return response
