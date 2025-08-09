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


class ProjectCollaboratorMixin:
    """Mixin to check if user has permission to manage project collaborators"""
    
    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=kwargs.get('project_id'))
        
        # Check if user is project owner or admin collaborator
        if not self.has_permission(request.user):
            raise PermissionDenied("You don't have permission to manage this project's collaborators")
        
        return super().dispatch(request, *args, **kwargs)
    
    def has_permission(self, user):
        """Check if user has permission to manage collaborators"""
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


# Project Invitation Views
class ProjectInvitationListView(LoginRequiredMixin, ListView):
    """List all invitations for a project"""
    model = ProjectInvitation
    template_name = 'collaboration/projectinvitation_list.html'
    context_object_name = 'invitations'
    paginate_by = 20
    
    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=kwargs.get('project_id'))
        
        # Check if user has access to view invitations (more permissive than managing)
        if not self.has_view_permission(request.user):
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
        return ProjectInvitation.objects.filter(
            project=self.project
        ).select_related('inviter', 'invitee').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        context['pending_count'] = self.get_queryset().filter(status='pending').count()
        context['accepted_count'] = self.get_queryset().filter(status='accepted').count()
        
        # Add permission context for template
        context['can_manage'] = self.has_manage_permission(self.request.user)
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
    
    def form_valid(self, form):
        form.instance.project = self.project
        form.instance.inviter = self.request.user
        
        try:
            response = super().form_valid(form)
            
            # Send invitation email
            self.send_invitation_email(form.instance)
            
            messages.success(
                self.request, 
                f'Invitation sent successfully to {form.instance.recipient_display}'
            )
            return response
            
        except ValidationError as e:
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
            
            recipient_email = invitation.email if invitation.email else invitation.invitee.email
            
            send_mail(
                subject=subject,
                message=f'You have been invited to collaborate on {invitation.project.project_name}. Visit: {invitation_url}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                html_message=html_message,
                fail_silently=False,
            )
            
        except Exception as e:
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
def accept_invitation(request, token):
    """Accept a project invitation"""
    invitation = get_object_or_404(ProjectInvitation, token=token)
    
    # Check if invitation is valid
    if invitation.status != 'pending':
        messages.error(request, 'This invitation is no longer valid.')
        return redirect('devops:project_list')
    
    if invitation.is_expired:
        messages.error(request, 'This invitation has expired.')
        return redirect('devops:project_list')
    
    try:
        # Accept the invitation
        invitation.accept(user=request.user)
        
        # Create collaborator record
        ProjectCollaborator.objects.create(
            project=invitation.project,
            user=request.user,
            role='viewer',  # Default role
            added_by=invitation.inviter
        )
        
        messages.success(
            request, 
            f'You have successfully joined {invitation.project.project_name} as a collaborator!'
        )
        
        return redirect('devops:project_detail', pk=invitation.project.pk)
        
    except ValidationError as e:
        messages.error(request, str(e))
        return redirect('devops:project_list')


@login_required
def decline_invitation(request, token):
    """Decline a project invitation"""
    invitation = get_object_or_404(ProjectInvitation, token=token)
    
    if invitation.status != 'pending':
        messages.error(request, 'This invitation is no longer valid.')
        return redirect('devops:project_list')
    
    invitation.decline()
    messages.info(request, f'You have declined the invitation to {invitation.project.project_name}.')
    
    return redirect('devops:project_list')


# Project Collaborator Views
class ProjectCollaboratorListView(LoginRequiredMixin, ListView):
    """List all collaborators for a project"""
    model = ProjectCollaborator
    template_name = 'collaboration/collaborator_list.html'
    context_object_name = 'collaborators'
    paginate_by = 20
    
    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=kwargs.get('project_id'))
        
        # Check if user has access to view collaborators
        if not self.has_view_permission(request.user):
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
        return ProjectCollaborator.objects.filter(
            project=self.project
        ).select_related('user', 'added_by').order_by('-added_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        context['is_owner'] = self.project.owner == self.request.user
        context['user_role'] = self.get_user_role()
        context['can_manage'] = self.can_manage_collaborators()
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
        return get_object_or_404(
            ProjectCollaborator, 
            pk=self.kwargs['pk'], 
            project=self.project
        )
    
    def form_valid(self, form):
        messages.success(
            self.request, 
            f'Updated {form.instance.user.full_name}\'s role to {form.instance.get_role_display()}'
        )
        return super().form_valid(form)
    
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
        return get_object_or_404(
            ProjectCollaborator, 
            pk=self.kwargs['pk'], 
            project=self.project
        )
    
    def delete(self, request, *args, **kwargs):
        collaborator = self.get_object()
        user_name = collaborator.user.full_name
        
        response = super().delete(request, *args, **kwargs)
        
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
def resend_invitation_ajax(request, invitation_id):
    """Resend an invitation via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    invitation = get_object_or_404(ProjectInvitation, pk=invitation_id)
    
    # Check permissions
    if not (invitation.project.owner == request.user or 
            ProjectCollaborator.objects.filter(
                project=invitation.project, 
                user=request.user, 
                role='admin'
            ).exists()):
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if invitation.status != 'pending':
        return JsonResponse({'success': False, 'error': 'Invitation is not pending'})
    
    try:
        # Update expiration date
        invitation.expires_at = timezone.now() + timezone.timedelta(days=30)
        invitation.save()
        
        # Resend email (implement email sending logic here)
        # send_invitation_email(invitation)
        
        return JsonResponse({
            'success': True, 
            'message': 'Invitation resent successfully'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def cancel_invitation_ajax(request, invitation_id):
    """Cancel an invitation via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    invitation = get_object_or_404(ProjectInvitation, pk=invitation_id)
    
    # Check permissions
    if not (invitation.project.owner == request.user or 
            ProjectCollaborator.objects.filter(
                project=invitation.project, 
                user=request.user, 
                role='admin'
            ).exists()):
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if invitation.status != 'pending':
        return JsonResponse({'success': False, 'error': 'Invitation is not pending'})
    
    try:
        invitation.status = 'expired'
        invitation.save()
        
        return JsonResponse({
            'success': True, 
            'message': 'Invitation cancelled successfully'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def update_collaborator_role_ajax(request, collaborator_id):
    """Update collaborator role via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    collaborator = get_object_or_404(ProjectCollaborator, pk=collaborator_id)
    new_role = request.POST.get('role')
    
    if new_role not in ['viewer', 'contributor', 'admin']:
        return JsonResponse({'success': False, 'error': 'Invalid role'})
    
    # Check permissions
    if not (collaborator.project.owner == request.user or 
            ProjectCollaborator.objects.filter(
                project=collaborator.project, 
                user=request.user, 
                role='admin'
            ).exists()):
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    try:
        collaborator.role = new_role
        collaborator.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'Role updated to {collaborator.get_role_display()}'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# Dashboard Views
@login_required
def my_invitations(request):
    """View user's received invitations"""
    invitations = ProjectInvitation.objects.filter(
        Q(invitee=request.user) | Q(email=request.user.email),
        status='pending'
    ).select_related('project', 'inviter').order_by('-created_at')
    
    return render(request, 'collaboration/my_invitations.html', {
        'invitations': invitations
    })


@login_required
def my_collaborations(request):
    """View user's collaborations"""
    collaborations = ProjectCollaborator.objects.filter(
        user=request.user
    ).select_related('project', 'added_by').order_by('-added_at')
    
    return render(request, 'collaboration/my_collaborations.html', {
        'collaborations': collaborations
    })


# Utility Views
@login_required
def search_users_ajax(request):
    """Search users for invitation via AJAX"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
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
    
    return JsonResponse({'users': user_data})