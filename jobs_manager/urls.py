"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from typing import Iterable, cast

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import RedirectView

urlpatterns = [
    path(
        "login",
        RedirectView.as_view(
            url=settings.FRONT_END_URL.rstrip("/") + "/login", permanent=False
        ),
        name="backend-login-redirect",
    ),
    path("admin/", admin.site.urls),
    path("", include("apps.workflow.urls")),
    path("job/", include("apps.job.urls", namespace="jobs")),
    path("accounts/", include("apps.accounts.urls")),
    path("timesheets/", include("apps.timesheet.urls")),
    path("quoting/", include(("apps.quoting.urls", "quoting"), namespace="quoting")),
    path("clients/", include("apps.client.urls", namespace="clients")),
    path("purchasing/", include("apps.purchasing.urls", namespace="purchasing")),
    path("accounting/", include("apps.accounting.urls", namespace="accounting")),
]

if settings.DEBUG:
    urlpatterns += cast(
        Iterable, static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    )
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
