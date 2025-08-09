from django.urls import path
from . import views

app_name = 'collaboration'

urlpatterns = [
    # Project Invitation URLs
    path('projects/<int:project_id>/invitations/', 
         views.ProjectInvitationListView.as_view(), 
         name='invitation_list'),
    
    path('projects/<int:project_id>/invitations/create/', 
         views.ProjectInvitationCreateView.as_view(), 
         name='invitation_create'),
    
    path('invitations/<uuid:token>/accept/', 
         views.accept_invitation, 
         name='accept_invitation'),
    
    path('invitations/<uuid:token>/decline/', 
         views.decline_invitation, 
         name='decline_invitation'),
    
    # Project Collaborator URLs
    path('projects/<int:project_id>/collaborators/', 
         views.ProjectCollaboratorListView.as_view(), 
         name='collaborator_list'),
    
    path('projects/<int:project_id>/collaborators/<int:pk>/edit/', 
         views.ProjectCollaboratorUpdateView.as_view(), 
         name='collaborator_edit'),
    
    path('projects/<int:project_id>/collaborators/<int:pk>/remove/', 
         views.ProjectCollaboratorDeleteView.as_view(), 
         name='collaborator_remove'),
    
    # Dashboard URLs
    path('my-invitations/', 
         views.my_invitations, 
         name='my_invitations'),
    
    path('my-collaborations/', 
         views.my_collaborations, 
         name='my_collaborations'),
    
    # AJAX URLs
    path('ajax/invitations/<int:invitation_id>/resend/', 
         views.resend_invitation_ajax, 
         name='resend_invitation_ajax'),
    
    path('ajax/invitations/<int:invitation_id>/cancel/', 
         views.cancel_invitation_ajax, 
         name='cancel_invitation_ajax'),
    
    path('ajax/collaborators/<int:collaborator_id>/update-role/', 
         views.update_collaborator_role_ajax, 
         name='update_collaborator_role_ajax'),
    
    path('ajax/search-users/', 
         views.search_users_ajax, 
         name='search_users_ajax'),
]