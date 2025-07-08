from django.urls import path

from apps.accounting.views.kpi_view import KPICalendarAPIView, KPICalendarTemplateView

app_name = "accounting"


urlpatterns = [
    path(
        "api/reports/calendar/",
        KPICalendarAPIView.as_view(),
        name="api_kpi_calendar",
    ),
    path(
        "reports/calendar/",
        KPICalendarTemplateView.as_view(),
        name="kpi_calendar",
    ),
]
