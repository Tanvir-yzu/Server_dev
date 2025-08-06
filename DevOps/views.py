from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Project
from .forms import ProjectCreateForm, ProjectEditForm

class ProjectListView(LoginRequiredMixin, ListView):
    """List all projects for the current user"""
    model = Project
    template_name = 'DevOps/project_list.html'
    context_object_name = 'projects'
    paginate_by = 10
    login_url = reverse_lazy('login')

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user, is_active=True)

class ProjectDetailView(LoginRequiredMixin, DetailView):
    """View details of a specific project"""
    model = Project
    template_name = 'DevOps/project_detail.html'
    context_object_name = 'project'
    login_url = reverse_lazy('login')

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)
    
class ServerCodeView(LoginRequiredMixin, DetailView):
    """View server code of a specific project"""
    model = Project
    template_name = 'DevOps/server_code.html'
    context_object_name = 'project'
    login_url = reverse_lazy('login')

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)

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
        return Project.objects.filter(owner=self.request.user)

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
        return Project.objects.filter(owner=self.request.user)

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
    user_projects = Project.objects.filter(owner=request.user, is_active=True)
    
    context = {
        'total_projects': user_projects.count(),
        'deployed_projects': user_projects.filter(deployment_status='deployed').count(),
        'pending_projects': user_projects.filter(deployment_status='pending').count(),
        'failed_projects': user_projects.filter(deployment_status='failed').count(),
        'recent_projects': user_projects.order_by('-created_at')[:5],
    }
    
    return render(request, 'DevOps/dashboard.html', context)