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
                project_id = kwargs.get('project_id') or getattr(args[0], 'project', {}).get('id', None)
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
            f'Updated {form.instance.user.full_name}\'s role to {form.instance.get_role_display()}'
        )
        return result
    
    def get_success_url(self):
        return reverse('collaboration:collaborator_list', kwargs={'project_id': self.project.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
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
        user_name = collaborator.user.full_name
        user_email = collaborator.user.email
        
        logger.warning(f"Removing collaborator - User: {user_email} ({user_name}) - Project: {self.project.project_name} - Removed by: {request.user.email}")
        
        response = super().delete(request, *args, **kwargs)
        
        logger.info(f"Collaborator removed successfully - User: {user_email} ({user_name}) - Project: {self.project.project_name}")
        
        messages.success(
            request, 
            f'{user_name} has been removed from the project'
        )
        
        return response
    
    def get_success_url(self):
        return reverse('collaboration:collaborator_list', kwargs={'project_id': self.project.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        return context


# AJAX Views
@login_required
@log_collaboration_action("INVITATION_RESEND_AJAX")
def resend_invitation_ajax(request, invitation_id):
    """Resend an invitation via AJAX"""
    logger.info(f"AJAX resend invitation request - ID: {invitation_id} - User: {request.user.email}")
    
    if request.method != 'POST':
        logger.warning(f"Invalid method for resend invitation - Method: {request.method} - User: {request.user.email}")
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    invitation = get_object_or_404(ProjectInvitation, pk=invitation_id)
    
    logger.debug(f"Resending invitation - ID: {invitation.id} - Project: {invitation.project.project_name} - Status: {invitation.status}")
    
    # Check permissions
    if not (invitation.project.owner == request.user or 
            ProjectCollaborator.objects.filter(
                project=invitation.project, 
                user=request.user, 
                role='admin'
            ).exists()):
        logger.warning(f"Permission denied for resend invitation - ID: {invitation_id} - User: {request.user.email}")
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if invitation.status != 'pending':
        logger.warning(f"Cannot resend non-pending invitation - ID: {invitation_id} - Status: {invitation.status}")
        return JsonResponse({'success': False, 'error': 'Invitation is not pending'})
    
    try:
        # Update expiration date
        invitation.expires_at = timezone.now() + timezone.timedelta(days=30)
        invitation.save()
        
        logger.info(f"Invitation resent successfully - ID: {invitation_id} - New expiration: {invitation.expires_at}")
        
        # Resend email (implement email sending logic here)
        # send_invitation_email(invitation)
        
        return JsonResponse({
            'success': True, 
            'message': 'Invitation resent successfully'
        })
        
    except Exception as e:
        logger.error(f"Failed to resend invitation - ID: {invitation_id} - Error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@log_collaboration_action("INVITATION_CANCEL_AJAX")
def cancel_invitation_ajax(request, invitation_id):
    """Cancel an invitation via AJAX"""
    logger.info(f"AJAX cancel invitation request - ID: {invitation_id} - User: {request.user.email}")
    
    if request.method != 'POST':
        logger.warning(f"Invalid method for cancel invitation - Method: {request.method} - User: {request.user.email}")
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    invitation = get_object_or_404(ProjectInvitation, pk=invitation_id)
    
    logger.debug(f"Cancelling invitation - ID: {invitation.id} - Project: {invitation.project.project_name} - Status: {invitation.status}")
    
    # Check permissions
    if not (invitation.project.owner == request.user or 
            ProjectCollaborator.objects.filter(
                project=invitation.project, 
                user=request.user, 
                role='admin'
            ).exists()):
        logger.warning(f"Permission denied for cancel invitation - ID: {invitation_id} - User: {request.user.email}")
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if invitation.status != 'pending':
        logger.warning(f"Cannot cancel non-pending invitation - ID: {invitation_id} - Status: {invitation.status}")
        return JsonResponse({'success': False, 'error': 'Invitation is not pending'})
    
    try:
        invitation.status = 'expired'
        invitation.save()
        
        logger.info(f"Invitation cancelled successfully - ID: {invitation_id}")
        
        return JsonResponse({
            'success': True, 
            'message': 'Invitation cancelled successfully'
        })
        
    except Exception as e:
        logger.error(f"Failed to cancel invitation - ID: {invitation_id} - Error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@log_collaboration_action("COLLABORATOR_ROLE_UPDATE_AJAX")
def update_collaborator_role_ajax(request, collaborator_id):
    """Update collaborator role via AJAX"""
    logger.info(f"AJAX update collaborator role request - ID: {collaborator_id} - User: {request.user.email}")
    
    if request.method != 'POST':
        logger.warning(f"Invalid method for update collaborator role - Method: {request.method} - User: {request.user.email}")
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    collaborator = get_object_or_404(ProjectCollaborator, pk=collaborator_id)
    new_role = request.POST.get('role')
    old_role = collaborator.role
    
    logger.debug(f"Updating collaborator role via AJAX - Collaborator: {collaborator.user.email} - Old role: {old_role} - New role: {new_role} - Project: {collaborator.project.project_name}")
    
    if new_role not in ['viewer', 'contributor', 'admin']:
        logger.warning(f"Invalid role specified - Role: {new_role} - Collaborator ID: {collaborator_id}")
        return JsonResponse({'success': False, 'error': 'Invalid role'})
    
    # Check permissions
    if not (collaborator.project.owner == request.user or 
            ProjectCollaborator.objects.filter(
                project=collaborator.project, 
                user=request.user, 
                role='admin'
            ).exists()):
        logger.warning(f"Permission denied for update collaborator role - ID: {collaborator_id} - User: {request.user.email}")
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    try:
        collaborator.role = new_role
        collaborator.save()
        
        logger.info(f"Collaborator role updated via AJAX - Collaborator: {collaborator.user.email} - Old role: {old_role} - New role: {new_role} - Project: {collaborator.project.project_name}")
        
        return JsonResponse({
            'success': True, 
            'message': f'Role updated to {collaborator.get_role_display()}'
        })
        
    except Exception as e:
        logger.error(f"Failed to update collaborator role via AJAX - ID: {collaborator_id} - Error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


# Dashboard Views
@login_required
@log_collaboration_action("MY_INVITATIONS_VIEW")
def my_invitations(request):
    """View user's received invitations"""
    logger.info(f"User {request.user.email} accessing my invitations")
    
    invitations = ProjectInvitation.objects.filter(
        Q(invitee=request.user) | Q(email=request.user.email),
        status='pending'
    ).select_related('project', 'inviter').order_by('-created_at')
    
    invitation_count = invitations.count()
    logger.info(f"User {request.user.email} has {invitation_count} pending invitations")
    
    return render(request, 'collaboration/my_invitations.html', {
        'invitations': invitations
    })


@login_required
@log_collaboration_action("MY_COLLABORATIONS_VIEW")
def my_collaborations(request):
    """View user's collaborations"""
    logger.info(f"User {request.user.email} accessing my collaborations")
    
    collaborations = ProjectCollaborator.objects.filter(
        user=request.user
    ).select_related('project', 'added_by').order_by('-added_at')
    
    collaboration_count = collaborations.count()
    logger.info(f"User {request.user.email} is collaborating on {collaboration_count} projects")
    
    return render(request, 'collaboration/my_collaborations.html', {
        'collaborations': collaborations
    })


# Utility Views
@login_required
@log_collaboration_action("SEARCH_USERS_AJAX")
def search_users_ajax(request):
    """Search users for invitation via AJAX"""
    query = request.GET.get('q', '').strip()
    
    logger.debug(f"AJAX user search request - Query: '{query}' - User: {request.user.email}")
    
    if len(query) < 2:
        logger.debug(f"Query too short for user search - Query: '{query}'")
        return JsonResponse({'users': []})
    
    users = User.objects.filter(
        Q(email__icontains=query) | Q(full_name__icontains=query)
    ).exclude(id=request.user.id)[:10]
    
    user_data = [{
        'id': user.id,
        'email': user.email,
        'full_name': user.full_name,
        'display_name': f"{user.full_name} ({user.email})"
    } for user in users]
    
    logger.info(f"User search completed - Query: '{query}' - Results: {len(user_data)} users - Requested by: {request.user.email}")
    
    return JsonResponse({'users': user_data})

# Debug/Test Views
@login_required
@log_collaboration_action("DEBUG_COLLABORATION_ACCESS")
def debug_collaboration_access(request, project_id):
    """Debug view to check collaboration access permissions"""
    logger.info(f"Debug collaboration access requested by {request.user.email} for project ID: {project_id}")
    
    try:
        project = Project.objects.get(id=project_id)
        
        # Check if user is owner
        is_owner = project.owner == request.user
        
        # Check if user is collaborator
        is_collaborator = False
        collaborator_role = None
        collaborator_id = None
        try:
            collaborator = ProjectCollaborator.objects.get(project=project, user=request.user)
            is_collaborator = True
            collaborator_role = collaborator.role
            collaborator_id = collaborator.id
        except ProjectCollaborator.DoesNotExist:
            pass
        
        # Check permissions
        can_view_invitations = is_owner or is_collaborator
        can_manage_invitations = is_owner or (is_collaborator and collaborator_role == 'admin')
        can_view_collaborators = is_owner or is_collaborator
        can_manage_collaborators = is_owner or (is_collaborator and collaborator_role == 'admin')
        
        # Get invitation and collaborator counts
        invitation_count = ProjectInvitation.objects.filter(project=project).count()
        collaborator_count = ProjectCollaborator.objects.filter(project=project).count()
        pending_invitations = ProjectInvitation.objects.filter(project=project, status='pending').count()
        
        debug_info = {
            'project_exists': True,
            'project_id': project.id,
            'project_name': project.project_name,
            'project_owner': project.owner.email,
            'current_user': request.user.email,
            'is_owner': is_owner,
            'is_collaborator': is_collaborator,
            'collaborator_role': collaborator_role,
            'collaborator_id': collaborator_id,
            'can_view_invitations': can_view_invitations,
            'can_manage_invitations': can_manage_invitations,
            'can_view_collaborators': can_view_collaborators,
            'can_manage_collaborators': can_manage_collaborators,
            'invitation_count': invitation_count,
            'collaborator_count': collaborator_count,
            'pending_invitations': pending_invitations,
            'project_is_active': project.is_active,
        }
        
        logger.info(f"Debug collaboration info generated for project {project_id}: {debug_info}")
        
    except Project.DoesNotExist:
        debug_info = {
            'project_exists': False,
            'project_id': project_id,
            'current_user': request.user.email,
        }
        
        logger.warning(f"Debug collaboration access requested for non-existent project {project_id} by user {request.user.email}")
    
    except Exception as e:
        logger.error(f"Error in debug collaboration access for project {project_id} by user {request.user.email}: {str(e)}")
        debug_info = {
            'error': str(e),
            'project_id': project_id,
            'current_user': request.user.email,
        }
    
    return JsonResponse(debug_info, json_dumps_params={'indent': 2})

@login_required
@log_collaboration_action("DEBUG_USER_COLLABORATIONS")
def list_user_collaborations_debug(request):
    """Debug view to list all collaborations for current user"""
    logger.info(f"Debug user collaborations list requested by {request.user.email}")
    
    try:
        # All projects user owns
        owned_projects = Project.objects.filter(owner=request.user)
        
        # All projects user collaborates on
        collaborations = ProjectCollaborator.objects.filter(user=request.user).select_related('project')
        
        # All invitations user has received
        received_invitations = ProjectInvitation.objects.filter(
            Q(invitee=request.user) | Q(email=request.user.email)
        ).select_related('project', 'inviter')
        
        # All invitations user has sent
        sent_invitations = ProjectInvitation.objects.filter(
            inviter=request.user
        ).select_related('project', 'invitee')
        
        debug_info = {
            'current_user': request.user.email,
            'owned_projects': [
                {
                    'id': p.id,
                    'name': p.project_name,
                    'is_active': p.is_active
                } for p in owned_projects
            ],
            'collaborations': [
                {
                    'id': c.id,
                    'project_id': c.project.id,
                    'project_name': c.project.project_name,
                    'role': c.role,
                    'added_at': c.added_at.isoformat(),
                    'added_by': c.added_by.email if c.added_by else None,
                    'project_is_active': c.project.is_active
                } for c in collaborations
            ],
            'received_invitations': [
                {
                    'id': i.id,
                    'project_id': i.project.id,
                    'project_name': i.project.project_name,
                    'status': i.status,
                    'inviter': i.inviter.email,
                    'created_at': i.created_at.isoformat(),
                    'expires_at': i.expires_at.isoformat() if i.expires_at else None,
                    'is_expired': i.is_expired
                } for i in received_invitations
            ],
            'sent_invitations': [
                {
                    'id': i.id,
                    'project_id': i.project.id,
                    'project_name': i.project.project_name,
                    'status': i.status,
                    'recipient': i.email or (i.invitee.email if i.invitee else None),
                    'created_at': i.created_at.isoformat(),
                    'expires_at': i.expires_at.isoformat() if i.expires_at else None,
                    'is_expired': i.is_expired
                } for i in sent_invitations
            ],
        }
        
        logger.info(f"Debug user collaborations info generated for {request.user.email}: {len(debug_info['owned_projects'])} owned, {len(debug_info['collaborations'])} collaborations, {len(debug_info['received_invitations'])} received invitations, {len(debug_info['sent_invitations'])} sent invitations")
        
    except Exception as e:
        logger.error(f"Error in debug user collaborations for user {request.user.email}: {str(e)}")
        debug_info = {
            'error': str(e),
            'current_user': request.user.email,
        }
    
    return JsonResponse(debug_info, json_dumps_params={'indent': 2})