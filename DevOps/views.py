from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from .models import Project
from .forms import ProjectCreateForm, ProjectEditForm

class ProjectListView(LoginRequiredMixin, ListView):
    """List all projects for the current user (owned + collaborated)"""
    model = Project
    template_name = 'DevOps/project_list.html'
    context_object_name = 'projects'
    paginate_by = 10
    login_url = reverse_lazy('login')

    def get_queryset(self):
        # Include projects owned by user and projects where user is a collaborator
        return Project.objects.filter(
            Q(owner=self.request.user) | Q(collaborators__user=self.request.user),
            is_active=True
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add role information for each project
        projects_with_roles = []
        for project in context['projects']:
            project_data = {
                'project': project,
                'user_role': 'owner' if project.owner == self.request.user else 'viewer',
                'can_edit': False,
                'can_delete': False,
                'can_manage_team': False
            }
            
            if project.owner == self.request.user:
                project_data['user_role'] = 'owner'
                project_data['can_edit'] = True
                project_data['can_delete'] = True
                project_data['can_manage_team'] = True
            else:
                # Get collaborator role
                try:
                    collaborator = project.collaborators.get(user=self.request.user)
                    project_data['user_role'] = collaborator.role
                    project_data['can_edit'] = collaborator.role in ['admin', 'contributor']
                    project_data['can_delete'] = collaborator.role == 'admin'
                    project_data['can_manage_team'] = collaborator.role == 'admin'
                except:
                    project_data['user_role'] = 'viewer'
                    project_data['can_edit'] = False
                    project_data['can_delete'] = False
                    project_data['can_manage_team'] = False
            
            projects_with_roles.append(project_data)
        
        context['projects_with_roles'] = projects_with_roles
        return context

class ProjectDetailView(LoginRequiredMixin, DetailView):
    """View details of a specific project"""
    model = Project
    template_name = 'DevOps/project_detail.html'
    context_object_name = 'project'
    login_url = reverse_lazy('login')

    def get_queryset(self):
        # Allow access to projects owned by user or where user is a collaborator
        return Project.objects.filter(
            Q(owner=self.request.user) | Q(collaborators__user=self.request.user)
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_object()
        
        # Add user's role information
        if project.owner == self.request.user:
            context['user_role'] = 'owner'
            context['can_edit'] = True
            context['can_delete'] = True
        else:
            # Get collaborator role
            try:
                collaborator = project.collaborators.get(user=self.request.user)
                context['user_role'] = collaborator.role
                context['can_edit'] = collaborator.role in ['admin', 'contributor']
                context['can_delete'] = collaborator.role == 'admin'
            except:
                context['user_role'] = 'viewer'
                context['can_edit'] = False
                context['can_delete'] = False
        
        return context
    
class ServerCodeView(LoginRequiredMixin, DetailView):
    """View server code of a specific project"""
    model = Project
    template_name = 'DevOps/server_code.html'
    context_object_name = 'project'
    login_url = reverse_lazy('login')

    def get_queryset(self):
        # Allow access to projects owned by user or where user is a collaborator
        return Project.objects.filter(
            Q(owner=self.request.user) | Q(collaborators__user=self.request.user)
        ).distinct()

class ProjectCreateView(LoginRequiredMixin, CreateView):
    """Create a new project"""
    model = Project
    form_class = ProjectCreateForm
    template_name = 'DevOps/project_create.html'
    success_url = reverse_lazy('devops:project_list')
    login_url = reverse_lazy('login')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, 'Project created successfully!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing project"""
    model = Project
    form_class = ProjectEditForm
    template_name = 'DevOps/project_edit.html'
    success_url = reverse_lazy('devops:project_list')
    login_url = reverse_lazy('login')

    def get_queryset(self):
        # Only allow editing by owner or admin/contributor collaborators
        user = self.request.user
        return Project.objects.filter(
            Q(owner=user) | 
            Q(collaborators__user=user, collaborators__role__in=['admin', 'contributor'])
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_object()
        
        # Check if user has edit permissions
        if project.owner == self.request.user:
            context['user_role'] = 'owner'
        else:
            try:
                collaborator = project.collaborators.get(user=self.request.user)
                context['user_role'] = collaborator.role
            except:
                context['user_role'] = 'viewer'
        
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Project updated successfully!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a project (soft delete by setting is_active=False)"""
    model = Project
    template_name = 'DevOps/project_delete.html'
    success_url = reverse_lazy('devops:project_list')
    login_url = reverse_lazy('login')

    def get_queryset(self):
        # Only allow deletion by owner or admin collaborators
        user = self.request.user
        return Project.objects.filter(
            Q(owner=user) | 
            Q(collaborators__user=user, collaborators__role='admin')
        ).distinct()

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Soft delete
        self.object.is_active = False
        self.object.save()
        messages.success(request, f'Project "{self.object.project_name}" has been deleted.')
        return redirect(self.success_url)

@login_required
def dashboard_view(request):
    """Dashboard showing project statistics"""
    # Include both owned and collaborated projects
    user_projects = Project.objects.filter(
        Q(owner=request.user) | Q(collaborators__user=request.user),
        is_active=True
    ).distinct()
    
    owned_projects = Project.objects.filter(owner=request.user, is_active=True)
    collaborated_projects = Project.objects.filter(
        collaborators__user=request.user, 
        is_active=True
    ).exclude(owner=request.user).distinct()
    
    context = {
        'total_projects': user_projects.count(),
        'owned_projects': owned_projects.count(),
        'collaborated_projects': collaborated_projects.count(),
        'deployed_projects': user_projects.filter(deployment_status='deployed').count(),
        'pending_projects': user_projects.filter(deployment_status='pending').count(),
        'failed_projects': user_projects.filter(deployment_status='failed').count(),
        'recent_projects': user_projects.order_by('-created_at')[:5],
    }
    
    return render(request, 'DevOps/dashboard.html', context)

# Debug/Test Views
@login_required
def debug_project_access(request, project_id):
    """Debug view to check project access permissions"""
    try:
        project = Project.objects.get(id=project_id)
        
        # Check if user is owner
        is_owner = project.owner == request.user
        
        # Check if user is collaborator
        is_collaborator = False
        collaborator_role = None
        try:
            collaborator = project.collaborators.get(user=request.user)
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
            'current_user': request.user.email,
            'is_owner': is_owner,
            'is_collaborator': is_collaborator,
            'collaborator_role': collaborator_role,
            'can_edit': can_edit,
            'project_is_active': project.is_active,
        }
        
    except Project.DoesNotExist:
        debug_info = {
            'project_exists': False,
            'project_id': project_id,
            'current_user': request.user.email,
        }
    
    return JsonResponse(debug_info, json_dumps_params={'indent': 2})

@login_required
def list_user_projects_debug(request):
    """Debug view to list all projects accessible to current user"""
    user = request.user
    
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
    
    return JsonResponse(debug_info, json_dumps_params={'indent': 2})