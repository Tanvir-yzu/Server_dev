import logging
import time
from functools import wraps
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied, ValidationError
from .models import Project
from .forms import ProjectCreateForm, ProjectEditForm

# Configure logger for DevOps app
logger = logging.getLogger('devops')

def log_user_action(action_type):
    """Decorator to log user actions with timing and context"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            request = None
            user = None
            
            # Extract request and user from args
            if hasattr(args[0], 'request'):
                request = args[0].request
                user = request.user
            elif hasattr(args[0], 'user'):
                request = args[0]
                user = request.user
            
            # Log action start
            logger.info(f"[{action_type}] Started - User: {user.email if user and user.is_authenticated else 'Anonymous'}")
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Log successful completion
                logger.info(f"[{action_type}] Completed successfully - User: {user.email if user and user.is_authenticated else 'Anonymous'} - Time: {execution_time:.2f}s")
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                # Log error
                logger.error(f"[{action_type}] Failed - User: {user.email if user and user.is_authenticated else 'Anonymous'} - Error: {str(e)} - Time: {execution_time:.2f}s")
                raise
                
        return wrapper
    return decorator

class ProjectListView(LoginRequiredMixin, ListView):
    """List all projects for the current user (owned + collaborated)"""
    model = Project
    template_name = 'DevOps/project_list.html'
    context_object_name = 'projects'
    paginate_by = 10
    login_url = reverse_lazy('login')

    @log_user_action("PROJECT_LIST_VIEW")
    def get_queryset(self):
        user = self.request.user
        logger.debug(f"Fetching project list for user: {user.email}")
        
        # Include projects owned by user and projects where user is a collaborator
        queryset = Project.objects.filter(
            Q(owner=user) | Q(collaborators__user=user),
            is_active=True
        ).distinct()
        
        project_count = queryset.count()
        logger.info(f"User {user.email} has access to {project_count} projects")
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        logger.debug(f"Building context data for project list - User: {user.email}")
        
        # Add role information for each project
        projects_with_roles = []
        for project in context['projects']:
            try:
                project_data = {
                    'project': project,
                    'user_role': 'owner' if project.owner == user else 'viewer',
                    'can_edit': False,
                    'can_delete': False,
                    'can_manage_team': False
                }
                
                if project.owner == user:
                    project_data['user_role'] = 'owner'
                    project_data['can_edit'] = True
                    project_data['can_delete'] = True
                    project_data['can_manage_team'] = True
                    logger.debug(f"User {user.email} is owner of project {project.project_name}")
                else:
                    # Get collaborator role
                    try:
                        collaborator = project.collaborators.get(user=user)
                        project_data['user_role'] = collaborator.role
                        project_data['can_edit'] = collaborator.role in ['admin', 'contributor']
                        project_data['can_delete'] = collaborator.role == 'admin'
                        project_data['can_manage_team'] = collaborator.role == 'admin'
                        logger.debug(f"User {user.email} is {collaborator.role} of project {project.project_name}")
                    except Exception as e:
                        project_data['user_role'] = 'viewer'
                        project_data['can_edit'] = False
                        project_data['can_delete'] = False
                        project_data['can_manage_team'] = False
                        logger.warning(f"Could not determine role for user {user.email} in project {project.project_name}: {str(e)}")
                
                projects_with_roles.append(project_data)
                
            except Exception as e:
                logger.error(f"Error processing project {project.id} for user {user.email}: {str(e)}")
                continue
        
        context['projects_with_roles'] = projects_with_roles
        logger.info(f"Context data built successfully for {len(projects_with_roles)} projects")
        
        return context

class ProjectDetailView(LoginRequiredMixin, DetailView):
    """View details of a specific project"""
    model = Project
    template_name = 'DevOps/project_detail.html'
    context_object_name = 'project'
    login_url = reverse_lazy('login')

    @log_user_action("PROJECT_DETAIL_VIEW")
    def get_queryset(self):
        user = self.request.user
        logger.debug(f"Fetching project detail queryset for user: {user.email}")
        
        # Allow access to projects owned by user or where user is a collaborator
        return Project.objects.filter(
            Q(owner=user) | Q(collaborators__user=user)
        ).distinct()

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        
        logger.info(f"User {user.email} accessing project detail: {obj.project_name} (ID: {obj.id})")
        
        # Check if user has access
        has_access = (obj.owner == user) or obj.collaborators.filter(user=user).exists()
        if not has_access:
            logger.warning(f"Access denied: User {user.email} attempted to access project {obj.project_name} (ID: {obj.id})")
            raise PermissionDenied("You don't have permission to access this project")
        
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_object()
        user = self.request.user
        
        logger.debug(f"Building context for project detail: {project.project_name} - User: {user.email}")
        
        # Add user's role information
        if project.owner == user:
            context['user_role'] = 'owner'
            context['can_edit'] = True
            context['can_delete'] = True
            logger.debug(f"User {user.email} is owner of project {project.project_name}")
        else:
            # Get collaborator role
            try:
                collaborator = project.collaborators.get(user=user)
                context['user_role'] = collaborator.role
                context['can_edit'] = collaborator.role in ['admin', 'contributor']
                context['can_delete'] = collaborator.role == 'admin'
                logger.debug(f"User {user.email} has role {collaborator.role} in project {project.project_name}")
            except Exception as e:
                context['user_role'] = 'viewer'
                context['can_edit'] = False
                context['can_delete'] = False
                logger.warning(f"Could not determine role for user {user.email} in project {project.project_name}: {str(e)}")
        
        return context
    
class ServerCodeView(LoginRequiredMixin, DetailView):
    """View server code of a specific project"""
    model = Project
    template_name = 'DevOps/server_code.html'
    context_object_name = 'project'
    login_url = reverse_lazy('login')

    @log_user_action("SERVER_CODE_VIEW")
    def get_queryset(self):
        user = self.request.user
        logger.debug(f"Fetching server code view queryset for user: {user.email}")
        
        # Allow access to projects owned by user or where user is a collaborator
        return Project.objects.filter(
            Q(owner=user) | Q(collaborators__user=user)
        ).distinct()

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        
        logger.info(f"User {user.email} accessing server code for project: {obj.project_name} (ID: {obj.id})")
        
        return obj

class ProjectCreateView(LoginRequiredMixin, CreateView):
    """Create a new project"""
    model = Project
    form_class = ProjectCreateForm
    template_name = 'DevOps/project_create.html'
    success_url = reverse_lazy('devops:project_list')
    login_url = reverse_lazy('login')

    @log_user_action("PROJECT_CREATE_VIEW")
    def get(self, request, *args, **kwargs):
        logger.info(f"User {request.user.email} accessing project creation form")
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        user = self.request.user
        project_name = form.cleaned_data.get('project_name', 'Unknown')
        
        logger.info(f"User {user.email} attempting to create project: {project_name}")
        
        try:
            form.instance.owner = user
            result = super().form_valid(form)
            
            logger.info(f"Project created successfully: {project_name} (ID: {form.instance.id}) by user {user.email}")
            messages.success(self.request, 'Project created successfully!')
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to create project {project_name} for user {user.email}: {str(e)}")
            messages.error(self.request, 'Failed to create project. Please try again.')
            raise

    def form_invalid(self, form):
        user = self.request.user
        logger.warning(f"Invalid form submission for project creation by user {user.email}: {form.errors}")
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing project"""
    model = Project
    form_class = ProjectEditForm
    template_name = 'DevOps/project_edit.html'
    success_url = reverse_lazy('devops:project_list')
    login_url = reverse_lazy('login')

    @log_user_action("PROJECT_UPDATE_VIEW")
    def get_queryset(self):
        user = self.request.user
        logger.debug(f"Fetching editable projects for user: {user.email}")
        
        # Only allow editing by owner or admin/contributor collaborators
        queryset = Project.objects.filter(
            Q(owner=user) | 
            Q(collaborators__user=user, collaborators__role__in=['admin', 'contributor'])
        ).distinct()
        
        logger.debug(f"User {user.email} can edit {queryset.count()} projects")
        return queryset

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        
        logger.info(f"User {user.email} accessing edit form for project: {obj.project_name} (ID: {obj.id})")
        
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_object()
        user = self.request.user
        
        # Check if user has edit permissions
        if project.owner == user:
            context['user_role'] = 'owner'
            logger.debug(f"User {user.email} editing project {project.project_name} as owner")
        else:
            try:
                collaborator = project.collaborators.get(user=user)
                context['user_role'] = collaborator.role
                logger.debug(f"User {user.email} editing project {project.project_name} as {collaborator.role}")
            except Exception as e:
                context['user_role'] = 'viewer'
                logger.warning(f"User {user.email} has no valid role for editing project {project.project_name}: {str(e)}")
        
        return context

    def form_valid(self, form):
        user = self.request.user
        project = self.get_object()
        
        logger.info(f"User {user.email} attempting to update project: {project.project_name} (ID: {project.id})")
        
        try:
            # Log changes
            changed_fields = []
            for field_name, field in form.fields.items():
                if field_name in form.changed_data:
                    old_value = getattr(project, field_name, None)
                    new_value = form.cleaned_data.get(field_name)
                    changed_fields.append(f"{field_name}: '{old_value}' -> '{new_value}'")
            
            if changed_fields:
                logger.info(f"Project {project.project_name} changes by {user.email}: {', '.join(changed_fields)}")
            
            result = super().form_valid(form)
            
            logger.info(f"Project updated successfully: {project.project_name} (ID: {project.id}) by user {user.email}")
            messages.success(self.request, 'Project updated successfully!')
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to update project {project.project_name} for user {user.email}: {str(e)}")
            messages.error(self.request, 'Failed to update project. Please try again.')
            raise

    def form_invalid(self, form):
        user = self.request.user
        project = self.get_object()
        logger.warning(f"Invalid form submission for project update by user {user.email} for project {project.project_name}: {form.errors}")
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a project (soft delete by setting is_active=False)"""
    model = Project
    template_name = 'DevOps/project_delete.html'
    success_url = reverse_lazy('devops:project_list')
    login_url = reverse_lazy('login')

    @log_user_action("PROJECT_DELETE_VIEW")
    def get_queryset(self):
        user = self.request.user
        logger.debug(f"Fetching deletable projects for user: {user.email}")
        
        # Only allow deletion by owner or admin collaborators
        queryset = Project.objects.filter(
            Q(owner=user) | 
            Q(collaborators__user=user, collaborators__role='admin')
        ).distinct()
        
        logger.debug(f"User {user.email} can delete {queryset.count()} projects")
        return queryset

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        
        logger.info(f"User {user.email} accessing delete confirmation for project: {obj.project_name} (ID: {obj.id})")
        
        return obj

    def delete(self, request, *args, **kwargs):
        user = request.user
        self.object = self.get_object()
        project_name = self.object.project_name
        project_id = self.object.id
        
        logger.warning(f"User {user.email} attempting to delete project: {project_name} (ID: {project_id})")
        
        try:
            # Soft delete
            self.object.is_active = False
            self.object.save()
            
            logger.info(f"Project soft-deleted successfully: {project_name} (ID: {project_id}) by user {user.email}")
            messages.success(request, f'Project "{project_name}" has been deleted.')
            
            return redirect(self.success_url)
            
        except Exception as e:
            logger.error(f"Failed to delete project {project_name} for user {user.email}: {str(e)}")
            messages.error(request, 'Failed to delete project. Please try again.')
            raise

@login_required
@log_user_action("DASHBOARD_VIEW")
def dashboard_view(request):
    """Dashboard showing project statistics"""
    user = request.user
    logger.info(f"User {user.email} accessing dashboard")
    
    try:
        # Include both owned and collaborated projects
        user_projects = Project.objects.filter(
            Q(owner=user) | Q(collaborators__user=user),
            is_active=True
        ).distinct()
        
        owned_projects = Project.objects.filter(owner=user, is_active=True)
        collaborated_projects = Project.objects.filter(
            collaborators__user=user, 
            is_active=True
        ).exclude(owner=user).distinct()
        
        # Calculate statistics
        stats = {
            'total_projects': user_projects.count(),
            'owned_projects': owned_projects.count(),
            'collaborated_projects': collaborated_projects.count(),
            'deployed_projects': user_projects.filter(deployment_status='deployed').count(),
            'pending_projects': user_projects.filter(deployment_status='pending').count(),
            'failed_projects': user_projects.filter(deployment_status='failed').count(),
        }
        
        logger.info(f"Dashboard stats for {user.email}: {stats}")
        
        context = {
            **stats,
            'recent_projects': user_projects.order_by('-created_at')[:5],
        }
        
        logger.debug(f"Dashboard context prepared for user {user.email}")
        return render(request, 'DevOps/dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error loading dashboard for user {user.email}: {str(e)}")
        messages.error(request, 'Error loading dashboard. Please try again.')
        raise

# Debug/Test Views
@login_required
@log_user_action("DEBUG_PROJECT_ACCESS")
def debug_project_access(request, project_id):
    """Debug view to check project access permissions"""
    user = request.user
    logger.info(f"Debug project access requested by {user.email} for project ID: {project_id}")
    
    try:
        project = Project.objects.get(id=project_id)
        
        # Check if user is owner
        is_owner = project.owner == user
        
        # Check if user is collaborator
        is_collaborator = False
        collaborator_role = None
        try:
            collaborator = project.collaborators.get(user=user)
            is_collaborator = True
            collaborator_role = collaborator.role
        except:
            pass
        
        # Check edit permissions
        can_edit = is_owner or (is_collaborator and collaborator_role in ['admin', 'contributor'])
        
        debug_info = {
            'project_exists': True,
            'project_id': project.id,
            'project_name': project.project_name,
            'project_owner': project.owner.email,
            'current_user': user.email,
            'is_owner': is_owner,
            'is_collaborator': is_collaborator,
            'collaborator_role': collaborator_role,
            'can_edit': can_edit,
            'project_is_active': project.is_active,
        }
        
        logger.info(f"Debug info generated for project {project_id}: {debug_info}")
        
    except Project.DoesNotExist:
        debug_info = {
            'project_exists': False,
            'project_id': project_id,
            'current_user': user.email,
        }
        
        logger.warning(f"Debug access requested for non-existent project {project_id} by user {user.email}")
    
    except Exception as e:
        logger.error(f"Error in debug project access for project {project_id} by user {user.email}: {str(e)}")
        debug_info = {
            'error': str(e),
            'project_id': project_id,
            'current_user': user.email,
        }
    
    return JsonResponse(debug_info, json_dumps_params={'indent': 2})

@login_required
@log_user_action("DEBUG_USER_PROJECTS")
def list_user_projects_debug(request):
    """Debug view to list all projects accessible to current user"""
    user = request.user
    logger.info(f"Debug user projects list requested by {user.email}")
    
    try:
        # All projects user owns
        owned_projects = Project.objects.filter(owner=user)
        
        # All projects user collaborates on
        collaborated_projects = Project.objects.filter(collaborators__user=user)
        
        # Projects user can edit
        editable_projects = Project.objects.filter(
            Q(owner=user) | 
            Q(collaborators__user=user, collaborators__role__in=['admin', 'contributor'])
        ).distinct()
        
        debug_info = {
            'current_user': user.email,
            'owned_projects': [
                {
                    'id': p.id,
                    'name': p.project_name,
                    'is_active': p.is_active
                } for p in owned_projects
            ],
            'collaborated_projects': [
                {
                    'id': p.id,
                    'name': p.project_name,
                    'role': p.collaborators.get(user=user).role,
                    'is_active': p.is_active
                } for p in collaborated_projects
            ],
            'editable_projects': [
                {
                    'id': p.id,
                    'name': p.project_name,
                    'is_active': p.is_active
                } for p in editable_projects
            ],
        }
        
        logger.info(f"Debug user projects info generated for {user.email}: {len(debug_info['owned_projects'])} owned, {len(debug_info['collaborated_projects'])} collaborated, {len(debug_info['editable_projects'])} editable")
        
    except Exception as e:
        logger.error(f"Error in debug user projects for user {user.email}: {str(e)}")
        debug_info = {
            'error': str(e),
            'current_user': user.email,
        }
    
    return JsonResponse(debug_info, json_dumps_params={'indent': 2})