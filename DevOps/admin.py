from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Project

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for Project model with comprehensive features
    """
    
    # List display configuration
    list_display = [
        'project_name',
        'owner',
        'github_username',
        'deployment_status',  # Changed from deployment_status_badge to allow editing
        'domain_link',
        'is_active',
        'created_at',
        'updated_at'
    ]
    
    # List filters
    list_filter = [
        'deployment_status',
        'is_active',
        'created_at',
        'updated_at',
        ('owner', admin.RelatedOnlyFieldListFilter),
    ]
    
    # Search functionality
    search_fields = [
        'project_name',
        'github_username',
        'domain_name',
        'database_name',
        'owner__username',
        'owner__email',
        'project_details'
    ]
    
    # Ordering
    ordering = ['-created_at']
    
    # Date hierarchy
    date_hierarchy = 'created_at'
    
    # Read-only fields
    readonly_fields = [
        'created_at',
        'updated_at',
        'github_repo_name_display',
        'deployment_url_display',
        'project_stats',
        'deployment_status_badge'  # Keep the badge as read-only field
    ]
    
    # Fields organization
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'project_name',
                'owner',
                'project_details'
            ),
            'classes': ('wide',)
        }),
        ('GitHub Configuration', {
            'fields': (
                'github_username',
                'project_github_link',
                'github_repo_name_display'
            ),
            'classes': ('collapse',)
        }),
        ('Deployment Configuration', {
            'fields': (
                'domain_name',
                'database_name',
                'deployment_status',
                'deployment_status_badge',  # Show badge in form as well
                'deployment_url_display'
            ),
            'classes': ('wide',)
        }),
        ('Status & Metadata', {
            'fields': (
                'is_active',
                'created_at',
                'updated_at',
                'project_stats'
            ),
            'classes': ('collapse',)
        })
    )
    
    # Actions
    actions = [
        'mark_as_deployed',
        'mark_as_pending',
        'mark_as_failed',
        'activate_projects',
        'deactivate_projects'
    ]
    
    # List per page
    list_per_page = 25
    
    # Custom methods for display
    def deployment_status_badge(self, obj):
        """Display deployment status with colored badge"""
        colors = {
            'pending': '#fbbf24',      # yellow
            'in_progress': '#3b82f6',  # blue
            'deployed': '#10b981',     # green
            'failed': '#ef4444',       # red
            'maintenance': '#8b5cf6'   # purple
        }
        color = colors.get(obj.deployment_status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_deployment_status_display()
        )
    deployment_status_badge.short_description = 'Status Badge'
    
    def domain_link(self, obj):
        """Display domain as clickable link"""
        if obj.domain_name:
            url = obj.deployment_url
            return format_html(
                '<a href="{}" target="_blank" style="color: #3b82f6; text-decoration: none;">'
                '{} <span style="font-size: 10px;">↗</span></a>',
                url,
                obj.domain_name
            )
        return '-'
    domain_link.short_description = 'Domain'
    domain_link.admin_order_field = 'domain_name'
    
    def github_repo_name_display(self, obj):
        """Display GitHub repository name with link"""
        if obj.github_repo_name and obj.project_github_link:
            return format_html(
                '<a href="{}" target="_blank" style="color: #3b82f6;">{}</a>',
                obj.project_github_link,
                obj.github_repo_name
            )
        return obj.github_repo_name or '-'
    github_repo_name_display.short_description = 'Repository Name'
    
    def deployment_url_display(self, obj):
        """Display deployment URL as clickable link"""
        url = obj.deployment_url
        return format_html(
            '<a href="{}" target="_blank" style="color: #10b981; font-weight: bold;">'
            '{} <span style="font-size: 10px;">↗</span></a>',
            url,
            url
        )
    deployment_url_display.short_description = 'Deployment URL'
    
    def project_stats(self, obj):
        """Display project statistics"""
        stats = []
        stats.append(f"Created: {obj.created_at.strftime('%Y-%m-%d %H:%M')}")
        stats.append(f"Updated: {obj.updated_at.strftime('%Y-%m-%d %H:%M')}")
        stats.append(f"Status: {obj.get_deployment_status_display()}")
        stats.append(f"Active: {'Yes' if obj.is_active else 'No'}")
        
        return format_html('<br>'.join(stats))
    project_stats.short_description = 'Project Statistics'
    
    # Custom actions
    def mark_as_deployed(self, request, queryset):
        """Mark selected projects as deployed"""
        updated = queryset.update(deployment_status='deployed')
        self.message_user(
            request,
            f'{updated} project(s) marked as deployed.'
        )
    mark_as_deployed.short_description = "Mark selected projects as deployed"
    
    def mark_as_pending(self, request, queryset):
        """Mark selected projects as pending"""
        updated = queryset.update(deployment_status='pending')
        self.message_user(
            request,
            f'{updated} project(s) marked as pending.'
        )
    mark_as_pending.short_description = "Mark selected projects as pending"
    
    def mark_as_failed(self, request, queryset):
        """Mark selected projects as failed"""
        updated = queryset.update(deployment_status='failed')
        self.message_user(
            request,
            f'{updated} project(s) marked as failed.'
        )
    mark_as_failed.short_description = "Mark selected projects as failed"
    
    def activate_projects(self, request, queryset):
        """Activate selected projects"""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} project(s) activated.'
        )
    activate_projects.short_description = "Activate selected projects"
    
    def deactivate_projects(self, request, queryset):
        """Deactivate selected projects"""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} project(s) deactivated.'
        )
    deactivate_projects.short_description = "Deactivate selected projects"
    
    # Custom queryset optimization
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('owner')
    
    # Custom form validation
    def get_form(self, request, obj=None, **kwargs):
        """Customize form based on user permissions"""
        form = super().get_form(request, obj, **kwargs)
        
        # If not superuser, limit owner field to current user
        if not request.user.is_superuser:
            if 'owner' in form.base_fields:
                form.base_fields['owner'].queryset = form.base_fields['owner'].queryset.filter(
                    id=request.user.id
                )
                form.base_fields['owner'].initial = request.user
        
        return form
    
    # Custom save method
    def save_model(self, request, obj, form, change):
        """Custom save logic"""
        if not change and not obj.owner_id:
            # Set current user as owner for new projects
            obj.owner = request.user
        super().save_model(request, obj, form, change)
    
    # Custom list display links
    list_display_links = ['project_name']
    
    # Enable bulk editing - Fixed to match list_display fields
    list_editable = ['deployment_status', 'is_active']
    
    # Custom CSS and JS
    class Media:
        css = {
            'all': ('admin/css/custom_project_admin.css',)
        }
        js = ('admin/js/custom_project_admin.js',)

# Optional: Custom admin site configuration
admin.site.site_header = "DevOps Project Management"
admin.site.site_title = "DevOps Admin"
admin.site.index_title = "Welcome to DevOps Project Administration"