# System/urls.py
from django.urls import path
from . import views

app_name = 'system'

urlpatterns = [
    # Admin logs view
    path('logs/', views.AdminLogsView.as_view(), name='admin_logs'),
    
    # AJAX endpoint for refreshing logs
    path('logs/refresh/', views.refresh_logs_ajax, name='refresh_logs_ajax'),
    
    # Download log file
    path('logs/download/<str:filename>/', views.download_log_file, name='download_log_file'),
    
    # System health monitoring
    path('health/', views.SystemHealthView.as_view(), name='system_health'),
]