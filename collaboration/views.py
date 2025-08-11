import logging
import time
from functools import wraps
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponseForbidden
from django.core.exceptions import ValidationError, PermissionDenied
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

from .models import ProjectInvitation, ProjectCollaborator
from DevOps.models import Project

User = get_user_model()

# Configure logger for Collaboration app
logger = logging.getLogger('collaboration')

def log_collaboration_action(action_type):
    """Decorator to log collaboration actions with timing and context"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            request = None
            user = None
            project_id = None
            
            # Extract request and user from args
            if hasattr(args[0], 'request'):
                request = args[0].request
                user = request.user
                # Try to get project_id from kwargs or view
                project_id = kwargs.get('project_id')
                if not project_id and hasattr(args[0], 'project'):
                    # If project is a model instance, get its id
                    project = getattr(args[0], 'project')
                    if hasattr(project, 'id'):
                        project_id = project.id
            elif hasattr(args[0], 'user'):
                request = args[0]
                user = request.user
                project_id = kwargs.get('project_id')
            
            # Log action start
            logger.info(f"[{action_type}] Started - User: {user.email if user and user.is_authenticated else 'Anonymous'} - Project: {project_id}")
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Log successful completion
                logger.info(f"[{action_type}] Completed successfully - User: {user.email if user and user.is_authenticated else 'Anonymous'} - Project: {project_id} - Time: {execution_time:.2f}s")
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                # Log error
                logger.error(f"[{action_type}] Failed - User: {user.email if user and user.is_authenticated else 'Anonymous'} - Project: {project_id} - Error: {str(e)} - Time: {execution_time:.2f}s")
                raise
                
        return wrapper
    return decorator

class ProjectCollaboratorMixin:
    """Mixin to check if user has permission to manage project collaborators"""
    
    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=kwargs.get('project_id'))
        
        logger.debug(f"ProjectCollaboratorMixin dispatch - User: {request.user.email} - Project: {self.project.project_name} (ID: {self.project.id})")
        
        # Check if user is project owner or admin collaborator
        if not self.has_permission(request.user):
            logger.warning(f"Permission denied for user {request.user.email} to manage collaborators in project {self.project.project_name} (ID: {self.project.id})")
            raise PermissionDenied("You don't have permission to manage this project's collaborators")
        
        logger.debug(f"Permission granted for user {request.user.email} to manage collaborators in project {self.project.project_name}")
        return super().dispatch(request, *args, **kwargs)
    
    def has_permission(self, user):
        """Check if user has permission to manage collaborators"""
        # First check if user is authenticated
        if not user.is_authenticated:
            logger.debug("User not authenticated for collaborator management")
            return False
            
        if self.project.owner == user:
            logger.debug(f"User {user.email} is owner of project {self.project.project_name}")
            return True
        
        try:
            collaborator = ProjectCollaborator.objects.get(project=self.project, user=user)
            has_admin_role = collaborator.role == 'admin'
            logger.debug(f"User {user.email} has role {collaborator.role} in project {self.project.project_name} - Admin access: {has_admin_role}")
            return has_admin_role
        except ProjectCollaborator.DoesNotExist:
            logger.debug(f"User {user.email} is not a collaborator in project {self.project.project_name}")
            return False


# Project Invitation Views
class ProjectInvitationListView(LoginRequiredMixin, ListView):
    """List all invitations for a project"""
    model = ProjectInvitation
    template_name = 'collaboration/projectinvitation_list.html'
    context_object_name = 'invitations'
    paginate_by = 20
    
    @log_collaboration_action("INVITATION_LIST_VIEW")
    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=kwargs.get('project_id'))
        
        logger.debug(f"ProjectInvitationListView dispatch - User: {request.user.email} - Project: {self.project.project_name} (ID: {self.project.id})")
        
        # Check if user has access to view invitations (more permissive than managing)
        if not self.has_view_permission(request.user):
            logger.warning(f"Permission denied for user {request.user.email} to view invitations in project {self.project.project_name} (ID: {self.project.id})")
            raise PermissionDenied("You don't have permission to view this project's invitations")
        
        return super().dispatch(request, *args, **kwargs)
    
    def has_view_permission(self, user):
        """Check if user can view invitations - same as collaborator list view"""
        # First check if user is authenticated
        if not user.is_authenticated:
            return False
            
        if self.project.owner == user:
            return True
        
        try:
            ProjectCollaborator.objects.get(project=self.project, user=user)
            return True
        except ProjectCollaborator.DoesNotExist:
            return False
    
    def get_queryset(self):
        queryset = ProjectInvitation.objects.filter(
            project=self.project
        ).select_related('inviter', 'invitee').order_by('-created_at')
        
        invitation_count = queryset.count()
        logger.info(f"Retrieved {invitation_count} invitations for project {self.project.project_name} - User: {self.request.user.email}")
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        
        queryset = self.get_queryset()
        pending_count = queryset.filter(status='pending').count()
        accepted_count = queryset.filter(status='accepted').count()
        
        context['pending_count'] = pending_count
        context['accepted_count'] = accepted_count
        
        # Add permission context for template
        context['can_manage'] = self.has_manage_permission(self.request.user)
        
        logger.debug(f"Invitation list context - Project: {self.project.project_name} - Pending: {pending_count} - Accepted: {accepted_count} - Can manage: {context['can_manage']}")
        
        return context
    
    def has_manage_permission(self, user):
        """Check if user can manage invitations (create/cancel)"""
        # First check if user is authenticated
        if not user.is_authenticated:
            return False
            
        if self.project.owner == user:
            return True
        
        try:
            collaborator = ProjectCollaborator.objects.get(project=self.project, user=user)
            return collaborator.role == 'admin'
        except ProjectCollaborator.DoesNotExist:
            return False


class ProjectInvitationCreateView(LoginRequiredMixin, ProjectCollaboratorMixin, CreateView):
    """Create a new project invitation"""
    model = ProjectInvitation
    template_name = 'collaboration/invitation_form.html'
    fields = ['email', 'invitee', 'expires_at']
    
    @log_collaboration_action("INVITATION_CREATE")
    def form_valid(self, form):
        form.instance.project = self.project
        form.instance.inviter = self.request.user
        
        recipient_info = form.instance.email or (form.instance.invitee.email if form.instance.invitee else 'Unknown')
        logger.info(f"Creating invitation for project {self.project.project_name} - Inviter: {self.request.user.email} - Recipient: {recipient_info}")
        
        try:
            response = super().form_valid(form)
            
            # Send invitation email
            self.send_invitation_email(form.instance)
            
            logger.info(f"Invitation created successfully - ID: {form.instance.id} - Project: {self.project.project_name} - Recipient: {form.instance.recipient_display}")
            
            messages.success(
                self.request, 
                f'Invitation sent successfully to {form.instance.recipient_display}'
            )
            return response
            
        except ValidationError as e:
            logger.warning(f"Validation error creating invitation for project {self.project.project_name} - User: {self.request.user.email} - Error: {str(e)}")
            
            # Fix: Handle ValidationError properly
            if hasattr(e, 'message_dict'):
                # Handle field-specific errors
                for field, errors in e.message_dict.items():
                    for error in errors:
                        form.add_error(field, error)
            else:
                # Handle non-field errors
                error_messages = e.messages if hasattr(e, 'messages') else [str(e)]
                for error_message in error_messages:
                    form.add_error(None, error_message)
            return self.form_invalid(form)
    
    def send_invitation_email(self, invitation):
        """Send invitation email to the recipient"""
        recipient_email = invitation.email if invitation.email else invitation.invitee.email
        
        logger.debug(f"Sending invitation email - Invitation ID: {invitation.id} - Recipient: {recipient_email}")
        
        try:
            subject = f'Invitation to collaborate on {invitation.project.project_name}'
            
            # Create invitation URL
            invitation_url = self.request.build_absolute_uri(
                reverse('collaboration:accept_invitation', kwargs={'token': invitation.token})
            )
            
            # Render email template
            html_message = render_to_string('collaboration/emails/invitation.html', {
                'invitation': invitation,
                'invitation_url': invitation_url,
                'project': invitation.project,
                'inviter': invitation.inviter,
            })
            
            send_mail(
                subject=subject,
                message=f'You have been invited to collaborate on {invitation.project.project_name}. Visit: {invitation_url}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Invitation email sent successfully - Invitation ID: {invitation.id} - Recipient: {recipient_email}")
            
        except Exception as e:
            logger.error(f"Failed to send invitation email - Invitation ID: {invitation.id} - Recipient: {recipient_email} - Error: {str(e)}")
            messages.warning(
                self.request, 
                f'Invitation created but email could not be sent: {str(e)}'
            )
    
    def get_success_url(self):
        return reverse('collaboration:invitation_list', kwargs={'project_id': self.project.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        return context


@login_required
@log_collaboration_action("INVITATION_ACCEPT")
def accept_invitation(request, token):
    """Accept a project invitation"""
    logger.info(f"User {request.user.email} attempting to accept invitation with token: {token}")
    
    invitation = get_object_or_404(ProjectInvitation, token=token)
    
    logger.debug(f"Found invitation - ID: {invitation.id} - Project: {invitation.project.project_name} - Status: {invitation.status}")
    
    # Check if invitation is valid
    if invitation.status != 'pending':
        logger.warning(f"Invalid invitation status - ID: {invitation.id} - Status: {invitation.status} - User: {request.user.email}")
        messages.error(request, 'This invitation is no longer valid.')
        return redirect('devops:project_list')
    
    if invitation.is_expired:
        logger.warning(f"Expired invitation - ID: {invitation.id} - User: {request.user.email}")
        messages.error(request, 'This invitation has expired.')
        return redirect('devops:project_list')
    
    try:
        # Accept the invitation
        invitation.accept(user=request.user)
        
        # Create collaborator record
        collaborator = ProjectCollaborator.objects.create(
            project=invitation.project,
            user=request.user,
            role='viewer',  # Default role
            added_by=invitation.inviter
        )
        
        logger.info(f"Invitation accepted successfully - ID: {invitation.id} - User: {request.user.email} - Project: {invitation.project.project_name} - Collaborator ID: {collaborator.id}")
        
        messages.success(
            request, 
            f'You have successfully joined {invitation.project.project_name} as a collaborator!'
        )
        
        return redirect('devops:project_detail', pk=invitation.project.pk)
        
    except ValidationError as e:
        logger.error(f"Failed to accept invitation - ID: {invitation.id} - User: {request.user.email} - Error: {str(e)}")
        messages.error(request, str(e))
        return redirect('devops:project_list')


@login_required
@log_collaboration_action("INVITATION_DECLINE")
def decline_invitation(request, token):
    """Decline a project invitation"""
    logger.info(f"User {request.user.email} attempting to decline invitation with token: {token}")
    
    invitation = get_object_or_404(ProjectInvitation, token=token)
    
    logger.debug(f"Found invitation to decline - ID: {invitation.id} - Project: {invitation.project.project_name} - Status: {invitation.status}")
    
    if invitation.status != 'pending':
        logger.warning(f"Cannot decline non-pending invitation - ID: {invitation.id} - Status: {invitation.status} - User: {request.user.email}")
        messages.error(request, 'This invitation is no longer valid.')
        return redirect('devops:project_list')
    
    invitation.decline()
    
    logger.info(f"Invitation declined successfully - ID: {invitation.id} - User: {request.user.email} - Project: {invitation.project.project_name}")
    
    messages.info(request, f'You have declined the invitation to {invitation.project.project_name}.')
    
    return redirect('devops:project_list')


# Project Collaborator Views
class ProjectCollaboratorListView(LoginRequiredMixin, ListView):
    """List all collaborators for a project"""
    model = ProjectCollaborator
    template_name = 'collaboration/collaborator_list.html'
    context_object_name = 'collaborators'
    paginate_by = 20
    
    @log_collaboration_action("COLLABORATOR_LIST_VIEW")
    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=kwargs.get('project_id'))
        
        logger.debug(f"ProjectCollaboratorListView dispatch - User: {request.user.email} - Project: {self.project.project_name} (ID: {self.project.id})")
        
        # Check if user has access to view collaborators
        if not self.has_view_permission(request.user):
            logger.warning(f"Permission denied for user {request.user.email} to view collaborators in project {self.project.project_name} (ID: {self.project.id})")
            raise PermissionDenied("You don't have permission to view this project's collaborators")
        
        return super().dispatch(request, *args, **kwargs)
    
    def has_view_permission(self, user):
        """Check if user can view collaborators"""
        # First check if user is authenticated
        if not user.is_authenticated:
            return False
            
        if self.project.owner == user:
            return True
        
        try:
            ProjectCollaborator.objects.get(project=self.project, user=user)
            return True
        except ProjectCollaborator.DoesNotExist:
            return False
    
    def get_queryset(self):
        queryset = ProjectCollaborator.objects.filter(
            project=self.project
        ).select_related('user', 'added_by').order_by('-added_at')
        
        collaborator_count = queryset.count()
        logger.info(f"Retrieved {collaborator_count} collaborators for project {self.project.project_name} - User: {self.request.user.email}")
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        context['is_owner'] = self.project.owner == self.request.user
        context['user_role'] = self.get_user_role()
        context['can_manage'] = self.can_manage_collaborators()
        
        logger.debug(f"Collaborator list context - Project: {self.project.project_name} - User role: {context['user_role']} - Can manage: {context['can_manage']}")
        
        return context
    
    def get_user_role(self):
        """Get current user's role in the project"""
        # First check if user is authenticated
        if not self.request.user.is_authenticated:
            return None
            
        if self.project.owner == self.request.user:
            return 'owner'
        
        try:
            collaborator = ProjectCollaborator.objects.get(
                project=self.project, 
                user=self.request.user
            )
            return collaborator.role
        except ProjectCollaborator.DoesNotExist:
            return None
    
    def can_manage_collaborators(self):
        """Check if user can manage collaborators"""
        user_role = self.get_user_role()
        return user_role in ['owner', 'admin']


class ProjectCollaboratorUpdateView(LoginRequiredMixin, ProjectCollaboratorMixin, UpdateView):
    """Update a collaborator's role"""
    model = ProjectCollaborator
    template_name = 'collaboration/collaborator_form.html'
    fields = ['role']
    
    def get_object(self):
        obj = get_object_or_404(
            ProjectCollaborator, 
            pk=self.kwargs['pk'], 
            project=self.project
        )
        
        logger.debug(f"ProjectCollaboratorUpdateView get_object - Collaborator: {obj.user.email} - Current role: {obj.role} - Project: {self.project.project_name}")
        
        return obj
    
    @log_collaboration_action("COLLABORATOR_UPDATE")
    def form_valid(self, form):
        collaborator = self.get_object()
        old_role = collaborator.role
        new_role = form.cleaned_data['role']
        
        logger.info(f"Updating collaborator role - User: {collaborator.user.email} - Project: {self.project.project_name} - Old role: {old_role} - New role: {new_role} - Updated by: {self.request.user.email}")
        
        result = super().form_valid(form)
        
        logger.info(f"Collaborator role updated successfully - User: {collaborator.user.email} - Project: {self.project.project_name} - New role: {new_role}")
        
        messages.success(
            self.request, 
            f'Updated {form.instance.user.get_full_name()}\'s role to {form.instance.get_role_display()}'
        )
        
        return result
    
    def get_success_url(self):
        return reverse('collaboration:collaborator_list', kwargs={'project_id': self.project.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        context['collaborator'] = self.get_object()
        return context


class ProjectCollaboratorDeleteView(LoginRequiredMixin, ProjectCollaboratorMixin, DeleteView):
    """Remove a collaborator from a project"""
    model = ProjectCollaborator
    template_name = 'collaboration/collaborator_confirm_delete.html'
    
    def get_object(self):
        obj = get_object_or_404(
            ProjectCollaborator, 
            pk=self.kwargs['pk'], 
            project=self.project
        )
        
        logger.debug(f"ProjectCollaboratorDeleteView get_object - Collaborator: {obj.user.email} - Role: {obj.role} - Project: {self.project.project_name}")
        
        return obj
    
    @log_collaboration_action("COLLABORATOR_DELETE")
    def delete(self, request, *args, **kwargs):
        collaborator = self.get_object()
        
        logger.info(f"Removing collaborator - User: {collaborator.user.email} - Project: {self.project.project_name} - Removed by: {request.user.email}")
        
        result = super().delete(request, *args, **kwargs)
        
        logger.info(f"Collaborator removed successfully - User: {collaborator.user.email} - Project: {self.project.project_name}")
        
        messages.success(
            request, 
            f'Removed {collaborator.user.get_full_name()} from {self.project.project_name}'
        )
        
        return result
    
    def get_success_url(self):
        return reverse('collaboration:collaborator_list', kwargs={'project_id': self.project.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        context['collaborator'] = self.get_object()
        return context


# AJAX Views for dynamic functionality
@login_required
@log_collaboration_action("INVITATION_CANCEL")
def cancel_invitation_ajax(request, project_id, invitation_id):
    """Cancel a project invitation via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    project = get_object_or_404(Project, pk=project_id)
    invitation = get_object_or_404(ProjectInvitation, pk=invitation_id, project=project)
    
    logger.debug(f"AJAX cancel invitation - User: {request.user.email} - Invitation ID: {invitation_id} - Project: {project.project_name}")
    
    # Check permissions
    if not (project.owner == request.user or 
            (hasattr(request.user, 'projectcollaborator_set') and 
             request.user.projectcollaborator_set.filter(project=project, role='admin').exists())):
        logger.warning(f"Permission denied for user {request.user.email} to cancel invitation {invitation_id} in project {project.project_name}")
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if invitation.status != 'pending':
        logger.warning(f"Cannot cancel non-pending invitation - ID: {invitation_id} - Status: {invitation.status}")
        return JsonResponse({'error': 'Cannot cancel this invitation'}, status=400)
    
    try:
        invitation.cancel()
        
        logger.info(f"Invitation cancelled successfully - ID: {invitation_id} - Project: {project.project_name} - Cancelled by: {request.user.email}")
        
        return JsonResponse({
            'success': True,
            'message': f'Invitation to {invitation.recipient_display} has been cancelled'
        })
        
    except Exception as e:
        logger.error(f"Failed to cancel invitation - ID: {invitation_id} - Error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@log_collaboration_action("COLLABORATOR_ROLE_UPDATE_AJAX")
def update_collaborator_role_ajax(request, project_id, collaborator_id):
    """Update collaborator role via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    project = get_object_or_404(Project, pk=project_id)
    collaborator = get_object_or_404(ProjectCollaborator, pk=collaborator_id, project=project)
    
    logger.debug(f"AJAX update collaborator role - User: {request.user.email} - Collaborator: {collaborator.user.email} - Project: {project.project_name}")
    
    # Check permissions
    if not (project.owner == request.user or 
            (hasattr(request.user, 'projectcollaborator_set') and 
             request.user.projectcollaborator_set.filter(project=project, role='admin').exists())):
        logger.warning(f"Permission denied for user {request.user.email} to update collaborator role in project {project.project_name}")
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    new_role = request.POST.get('role')
    if new_role not in ['viewer', 'editor', 'admin']:
        return JsonResponse({'error': 'Invalid role'}, status=400)
    
    try:
        old_role = collaborator.role
        collaborator.role = new_role
        collaborator.save()
        
        logger.info(f"Collaborator role updated via AJAX - User: {collaborator.user.email} - Project: {project.project_name} - Old role: {old_role} - New role: {new_role} - Updated by: {request.user.email}")
        
        return JsonResponse({
            'success': True,
            'message': f'Updated {collaborator.user.get_full_name()}\'s role to {collaborator.get_role_display()}',
            'new_role': new_role,
            'new_role_display': collaborator.get_role_display()
        })
        
    except Exception as e:
        logger.error(f"Failed to update collaborator role via AJAX - Collaborator: {collaborator.user.email} - Error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@log_collaboration_action("PROJECT_SEARCH_USERS")
def search_users_ajax(request, project_id):
    """Search for users to invite to a project via AJAX"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    project = get_object_or_404(Project, pk=project_id)
    
    # Check permissions
    if not (project.owner == request.user or 
            (hasattr(request.user, 'projectcollaborator_set') and 
             request.user.projectcollaborator_set.filter(project=project, role='admin').exists())):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'users': []})
    
    # Get existing collaborators and invitees to exclude
    existing_collaborators = ProjectCollaborator.objects.filter(project=project).values_list('user_id', flat=True)
    pending_invitations = ProjectInvitation.objects.filter(
        project=project, 
        status='pending'
    ).values_list('invitee_id', flat=True)
    
    exclude_ids = list(existing_collaborators) + list(pending_invitations) + [project.owner.id]
    
    # Search users
    users = User.objects.filter(
        Q(email__icontains=query) | 
        Q(first_name__icontains=query) | 
        Q(last_name__icontains=query)
    ).exclude(id__in=exclude_ids)[:10]
    
    user_data = []
    for user in users:
        user_data.append({
            'id': user.id,
            'email': user.email,
            'full_name': user.get_full_name(),
            'display_name': f"{user.get_full_name()} ({user.email})" if user.get_full_name() else user.email
        })
    
    logger.debug(f"User search - Query: '{query}' - Results: {len(user_data)} - Project: {project.project_name}")
    
    return JsonResponse({'users': user_data})


@login_required
@log_collaboration_action("COLLABORATION_DEBUG")
def debug_collaboration_view(request, project_id):
    """Debug view for collaboration system - only available in DEBUG mode"""
    if not settings.DEBUG:
        return HttpResponseForbidden("Debug view only available in DEBUG mode")
    
    project = get_object_or_404(Project, pk=project_id)
    
    # Gather debug information
    debug_info = {
        'project': {
            'id': project.id,
            'name': project.project_name,
            'owner': project.owner.email,
            'created_at': project.created_at.isoformat() if hasattr(project, 'created_at') else None,
        },
        'collaborators': [],
        'invitations': [],
        'user_permissions': {
            'is_owner': project.owner == request.user,
            'is_authenticated': request.user.is_authenticated,
            'user_email': request.user.email if request.user.is_authenticated else None,
        }
    }
    
    # Get collaborators
    collaborators = ProjectCollaborator.objects.filter(project=project).select_related('user', 'added_by')
    for collab in collaborators:
        debug_info['collaborators'].append({
            'id': collab.id,
            'user_email': collab.user.email,
            'role': collab.role,
            'added_by': collab.added_by.email if collab.added_by else None,
            'added_at': collab.added_at.isoformat(),
        })
    
    # Get invitations
    invitations = ProjectInvitation.objects.filter(project=project).select_related('inviter', 'invitee')
    for invitation in invitations:
        debug_info['invitations'].append({
            'id': invitation.id,
            'email': invitation.email,
            'invitee_email': invitation.invitee.email if invitation.invitee else None,
            'inviter_email': invitation.inviter.email,
            'status': invitation.status,
            'created_at': invitation.created_at.isoformat(),
            'expires_at': invitation.expires_at.isoformat() if invitation.expires_at else None,
            'is_expired': invitation.is_expired,
        })
    
    # Check user's role
    try:
        user_collab = ProjectCollaborator.objects.get(project=project, user=request.user)
        debug_info['user_permissions']['role'] = user_collab.role
    except ProjectCollaborator.DoesNotExist:
        debug_info['user_permissions']['role'] = None
    
    logger.info(f"Debug view accessed - User: {request.user.email} - Project: {project.project_name}")
    
    return JsonResponse(debug_info, json_dumps_params={'indent': 2})