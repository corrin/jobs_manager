from django.urls import path
from .views.time_entry_view import TimesheetEntryView, autosave_timesheet_view
from .views.time_overview_view import TimesheetOverviewView, TimesheetDailyView

app_name = 'timesheet'

urlpatterns = [
    # Timesheet Overview (Weekly View)
    path('overview/', 
         TimesheetOverviewView.as_view(), 
         name='timesheet_overview'),
         
    path('overview/<str:start_date>/',
         TimesheetOverviewView.as_view(), 
         name='timesheet_overview_with_date'),
    
    # Export to IMS
    path('export_to_ims/',
         TimesheetOverviewView.as_view(), 
         name='timesheet_export_to_ims'),
    
    # Daily Overview
    path('day/<str:date>/',
         TimesheetDailyView.as_view(), 
         name='timesheet_daily_view'),
    
    # Individual Timesheet Entry
    path('day/<str:date>/<uuid:staff_id>/',
         TimesheetEntryView.as_view(),
         name='timesheet_entry'),
    
    # Autosave endpoint
    path('autosave/',
         autosave_timesheet_view, 
         name='autosave_timesheet'),
]
