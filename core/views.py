from django.contrib.auth.decorators import login_not_required
from django.http import HttpRequest, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView


class HomeView(TemplateView):
    template_name = "core/home.html"


@login_not_required
@never_cache
@require_GET
def health(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})
