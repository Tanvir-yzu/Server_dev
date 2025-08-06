from django import forms
from .models import Project

class ProjectCreateForm(forms.ModelForm):
    """Form for creating a new project"""
    
    class Meta:
        model = Project
        fields = [
            'project_name', 
            'github_username', 
            'database_name', 
            'domain_name', 
            'project_github_link', 
            'project_details'
        ]
        widgets = {
            'project_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-400 focus:border-transparent',
                'placeholder': 'Enter project name'
            }),
            'github_username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-400 focus:border-transparent',
                'placeholder': 'Enter GitHub username'
            }),
            'database_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-400 focus:border-transparent',
                'placeholder': 'Enter database name'
            }),
            'domain_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-400 focus:border-transparent',
                'placeholder': 'example.com'
            }),
            'project_github_link': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-400 focus:border-transparent',
                'placeholder': 'https://github.com/username/repository'
            }),
            'project_details': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-400 focus:border-transparent',
                'rows': 5,
                'placeholder': 'Describe your project...'
            })
        }

class ProjectEditForm(forms.ModelForm):
    """Form for editing an existing project"""
    
    class Meta:
        model = Project
        fields = [
            'project_name', 
            'github_username', 
            'database_name', 
            'domain_name', 
            'project_github_link', 
            'project_details',
            'deployment_status'
        ]
        widgets = {
            'project_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-400 focus:border-transparent'
            }),
            'github_username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-400 focus:border-transparent'
            }),
            'database_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-400 focus:border-transparent'
            }),
            'domain_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-400 focus:border-transparent'
            }),
            'project_github_link': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-400 focus:border-transparent'
            }),
            'project_details': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-400 focus:border-transparent',
                'rows': 5
            }),
            'deployment_status': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-400 focus:border-transparent'
            })
        }