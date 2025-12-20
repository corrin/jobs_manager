from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from django.views.generic.base import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView

urlpatterns = [
    path(
        "login",
        RedirectView.as_view(
            url=settings.FRONT_END_URL.rstrip("/") + "/login", permanent=False
        ),
        name="backend-login-redirect",
    ),
    path("", include("apps.workflow.urls")),
    path("job/", include("apps.job.urls", namespace="jobs")),
    path("accounts/", include("apps.accounts.urls")),
    path("timesheets/", include("apps.timesheet.urls")),
    path("quoting/", include(("apps.quoting.urls", "quoting"), namespace="quoting")),
    path("clients/", include("apps.client.urls_rest", namespace="clients")),
    path("purchasing/", include("apps.purchasing.urls", namespace="purchasing")),
    path("accounting/", include("apps.accounting.urls", namespace="accounting")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
