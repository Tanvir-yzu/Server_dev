from django import forms
from django.core.exceptions import ValidationError
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
    
    def clean(self):
        cleaned_data = super().clean()
        project_name = cleaned_data.get('project_name')
        owner = self.instance.owner if hasattr(self.instance, 'owner') and self.instance.owner_id else None
        
        if project_name and owner:
            existing = Project.objects.filter(
                owner=owner,
                project_name=project_name
            ).exclude(pk=self.instance.pk if self.instance.pk else None)
            
            if existing.exists():
                self.add_error(
                    'project_name',
                    f'A project with the name "{project_name}" already exists for your account. Please use a different name.'
                )
        
        return cleaned_data

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
                'class': 'w-full px-4py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-400 focus:border-transparent'
            }),
            'database_name': forms.TextInput(attrs={
                'class': 'w-full px-4py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-400 focus:border-transparent'
            }),
            'domain_name': forms.TextInput(attrs={
                'class': 'w-full px-4py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-400 focus:border-transparent'
            }),
            'project_github_link': forms.URLInput(attrs={
                'class': 'w-full px-4py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-400 focus:border-transparent'
            }),
            'project_details': forms.Textarea(attrs={
                'class': 'w-full px-4py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-400 focus:border-transparent',
                'rows': 5
            }),
            'deployment_status': forms.Select(attrs={
                'class': 'w-full px-4py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-400 focus:border-transparent'
            })
        }
    
    def clean(self):
        cleaned_data = super().clean()
        project_name = cleaned_data.get('project_name')
        owner = self.instance.owner if hasattr(self.instance, 'owner') and self.instance.owner_id else None
        
        if project_name and owner and self.instance.pk:
            existing = Project.objects.filter(
                owner=owner,
                project_name=project_name
            ).exclude(pk=self.instance.pk)
            
            if existing.exists():
                self.add_error(
                    'project_name',
                    f'A project with the name "{project_name}" already exists for your account. Please use a different name.'
                )
        
        return cleaned_data