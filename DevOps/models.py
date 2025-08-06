from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
import re

User = get_user_model()

def validate_github_username(value):
    """Validate GitHub username format"""
    if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]){0,38}$', value):
        raise ValidationError('Invalid GitHub username format')

def validate_domain_name(value):
    """Validate domain name format"""
    domain_pattern = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
    if not re.match(domain_pattern, value):
        raise ValidationError('Invalid domain name format')

def validate_database_name(value):
    """Validate database name format"""
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', value):
        raise ValidationError('Database name must start with a letter and contain only letters, numbers, and underscores')

class Project(models.Model):
    """Model to store DevOps project deployment information"""
    
    # Basic project information
    project_name = models.CharField(
        max_length=100,
        help_text="Name of the project"
    )
    
    github_username = models.CharField(
        max_length=39,  # GitHub username max length
        validators=[validate_github_username],
        help_text="GitHub username of the project owner"
    )
    
    database_name = models.CharField(
        max_length=63,  # PostgreSQL identifier max length
        validators=[validate_database_name],
        help_text="Database name for the project"
    )
    
    domain_name = models.CharField(
        max_length=253,  # Domain name max length
        validators=[validate_domain_name],
        help_text="Domain name for the project deployment"
    )
    
    project_github_link = models.URLField(
        max_length=500,
        help_text="GitHub repository URL for the project"
    )
    
    project_details = models.TextField(
        help_text="Detailed description of the project"
    )
    
    # Metadata
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='projects',
        help_text="User who owns this project"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Deployment status
    DEPLOYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('deployed', 'Deployed'),
        ('failed', 'Failed'),
        ('maintenance', 'Under Maintenance'),
    ]
    
    deployment_status = models.CharField(
        max_length=20,
        choices=DEPLOYMENT_STATUS_CHOICES,
        default='pending',
        help_text="Current deployment status"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the project is active"
    )
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['owner', 'project_name']
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'
    
    def __str__(self):
        return f"{self.project_name} ({self.github_username})"
    
    def clean(self):
        """Custom validation"""
        super().clean()
        
        # Validate GitHub link matches username
        if self.project_github_link and self.github_username:
            expected_pattern = f"https://github.com/{self.github_username}/"
            if not self.project_github_link.startswith(expected_pattern):
                raise ValidationError({
                    'project_github_link': f'GitHub link must belong to user {self.github_username}'
                })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def github_repo_name(self):
        """Extract repository name from GitHub link"""
        if self.project_github_link:
            parts = self.project_github_link.rstrip('/').split('/')
            if len(parts) >= 2:
                return parts[-1]
        return None
    
    @property
    def full_github_url(self):
        """Return the complete GitHub URL"""
        return self.project_github_link
    
    @property
    def deployment_url(self):
        """Return the deployment URL based on domain"""
        return f"https://{self.domain_name}"