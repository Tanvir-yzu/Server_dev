from django.urls import path
from . import views

app_name = 'devops'

urlpatterns = [
    # Dashboard
    path('', views.dashboard_view, name='dashboard'),
    
    # Project CRUD operations
    path('projects/', views.ProjectListView.as_view(), name='project_list'),
    path('projects/create/', views.ProjectCreateView.as_view(), name='project_create'),
    path('projects/<int:pk>/', views.ProjectDetailView.as_view(), name='project_detail'),
    path('projects/<int:pk>/edit/', views.ProjectUpdateView.as_view(), name='project_edit'),
    path('projects/<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),
    path('projects/<int:pk>/code/', views.ServerCodeView.as_view(), name='server_code'),
    
    # Debug endpoints (remove in production)
    path('debug/project/<int:project_id>/', views.debug_project_access, name='debug_project_access'),
    path('debug/my-projects/', views.list_user_projects_debug, name='debug_user_projects'),
]