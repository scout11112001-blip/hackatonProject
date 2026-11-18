from django.contrib.auth.decorators import login_not_required
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView

from notifications.feed import home_summary
from schedule.services import today_schedule


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        summary = home_summary(self.request.user, now)
        context["summary"] = summary
        if summary is not None:
            day, annotation = today_schedule(summary.student.group_id, now)
            context["day"] = day
            context["annotation"] = annotation
        return context


@login_not_required
@never_cache
@require_GET
def health(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})
