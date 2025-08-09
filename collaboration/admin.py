from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q
from django.contrib import messages
from django.core.exceptions import ValidationError
from .models import ProjectInvitation, ProjectCollaborator


@admin.register(ProjectInvitation)
class ProjectInvitationAdmin(admin.ModelAdmin):
    list_display = [
        'project_name_link',
        'inviter_name',
        'recipient_display_admin',
        'status_badge',
        'created_at',
        'expires_at',
        'is_expired_display',
    ]
    
    list_filter = [
        'status',
        'created_at',
        'expires_at',
        ('project', admin.RelatedOnlyFieldListFilter),
        ('inviter', admin.RelatedOnlyFieldListFilter),
    ]
    
    search_fields = [
        'project__project_name',
        'inviter__email',
        'inviter__full_name',
        'invitee__email',
        'invitee__full_name',
        'email',
        'token',
    ]
    
    readonly_fields = [
        'token',
        'created_at',
        'accepted_at',
        'is_expired_display',
        'recipient_display_admin',
    ]
    
    fieldsets = (
        ('Invitation Details', {
            'fields': (
                'project',
                'inviter',
                'invitee',
                'email',
                'status',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'accepted_at',
                'expires_at',
            ),
            'classes': ('collapse',)
        }),
        ('System Fields', {
            'fields': (
                'token',
                'is_expired_display',
                'recipient_display_admin',
            ),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    actions = [
        'mark_as_expired',
        'extend_expiration',
        'resend_invitation',
    ]

    def project_name_link(self, obj):
        """Display project name as a link to the project admin page"""
        url = reverse('admin:DevOps_project_change', args=[obj.project.pk])
        return format_html('<a href="{}">{}</a>', url, obj.project.project_name)
    project_name_link.short_description = 'Project'
    project_name_link.admin_order_field = 'project__project_name'

    def inviter_name(self, obj):
        """Display inviter's name with email"""
        name = obj.inviter.get_full_name() or obj.inviter.email
        return format_html('<strong>{}</strong><br><small>{}</small>', name, obj.inviter.email)
    inviter_name.short_description = 'Inviter'
    inviter_name.admin_order_field = 'inviter__email'

    def recipient_display_admin(self, obj):
        """Display recipient information"""
        if obj.invitee:
            name = obj.invitee.get_full_name() or obj.invitee.email
            return format_html('<strong>{}</strong><br><small>{}</small>', name, obj.invitee.email)
        return format_html('<em>External: {}</em>', obj.email)
    recipient_display_admin.short_description = 'Recipient'

    def status_badge(self, obj):
        """Display status as a colored badge"""
        colors = {
            'pending': '#ffc107',
            'accepted': '#28a745',
            'declined': '#dc3545',
            'expired': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def is_expired_display(self, obj):
        """Display expiration status"""
        if obj.is_expired:
            return format_html('<span style="color: red;">✗ Expired</span>')
        elif obj.expires_at:
            days_left = (obj.expires_at - timezone.now()).days
            if days_left <= 3:
                return format_html('<span style="color: orange;">⚠ {} days left</span>', days_left)
            return format_html('<span style="color: green;">✓ {} days left</span>', days_left)
        return format_html('<span style="color: gray;">No expiration</span>')
    is_expired_display.short_description = 'Expiration Status'

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related(
            'project',
            'inviter',
            'invitee'
        )

    def mark_as_expired(self, request, queryset):
        """Admin action to mark invitations as expired"""
        updated = queryset.filter(status='pending').update(status='expired')
        self.message_user(request, f'{updated} invitations marked as expired.')
    mark_as_expired.short_description = 'Mark selected invitations as expired'

    def extend_expiration(self, request, queryset):
        """Admin action to extend invitation expiration by 30 days"""
        new_expiration = timezone.now() + timezone.timedelta(days=30)
        updated = queryset.filter(status='pending').update(expires_at=new_expiration)
        self.message_user(request, f'Extended expiration for {updated} invitations by 30 days.')
    extend_expiration.short_description = 'Extend expiration by 30 days'

    def resend_invitation(self, request, queryset):
        """Admin action to resend invitations (placeholder for future implementation)"""
        count = queryset.filter(status='pending').count()
        self.message_user(request, f'Resend action triggered for {count} invitations. (Implementation needed)')
    resend_invitation.short_description = 'Resend selected invitations'


@admin.register(ProjectCollaborator)
class ProjectCollaboratorAdmin(admin.ModelAdmin):
    list_display = [
        'project_name_link',
        'user_info',
        'role_badge',
        'added_at',
        'added_by_info',
    ]
    
    list_filter = [
        'role',
        'added_at',
        ('project', admin.RelatedOnlyFieldListFilter),
        ('added_by', admin.RelatedOnlyFieldListFilter),
    ]
    
    search_fields = [
        'project__project_name',
        'user__email',
        'user__username',
        'added_by__email',
        'added_by__username',
    ]
    
    readonly_fields = [
        'added_at',
    ]
    
    fieldsets = (
        ('Collaboration Details', {
            'fields': (
                'project',
                'user',
                'role',
            )
        }),
        ('Metadata', {
            'fields': (
                'added_by',
                'added_at',
            ),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'added_at'
    ordering = ['-added_at']
    
    actions = [
        'promote_to_admin',
        'demote_to_viewer',
        'remove_collaborators',
    ]

    def project_name_link(self, obj):
        """Display project name as a link to the project admin page"""
        try:
            url = reverse('admin:DevOps_project_change', args=[obj.project.pk])
            return format_html('<a href="{}">{}</a>', url, obj.project.project_name)
        except Exception:
            return obj.project.project_name
    project_name_link.short_description = 'Project'
    project_name_link.admin_order_field = 'project__project_name'

    def user_info(self, obj):
        """Display user information"""
        try:
            # Handle different user model configurations
            if hasattr(obj.user, 'get_full_name'):
                name = obj.user.get_full_name()
            elif hasattr(obj.user, 'full_name'):
                name = obj.user.full_name
            else:
                name = getattr(obj.user, 'first_name', '') + ' ' + getattr(obj.user, 'last_name', '')
                name = name.strip()
            
            display_name = name or obj.user.email or obj.user.username
            return format_html('<strong>{}</strong><br><small>{}</small>', display_name, obj.user.email)
        except Exception:
            return str(obj.user)
    user_info.short_description = 'User'
    user_info.admin_order_field = 'user__email'

    def role_badge(self, obj):
        """Display role as a colored badge"""
        colors = {
            'viewer': '#17a2b8',
            'contributor': '#ffc107',
            'admin': '#dc3545',
        }
        color = colors.get(obj.role, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_role_display()
        )
    role_badge.short_description = 'Role'
    role_badge.admin_order_field = 'role'

    def added_by_info(self, obj):
        """Display who added this collaborator"""
        if obj.added_by:
            try:
                # Handle different user model configurations
                if hasattr(obj.added_by, 'get_full_name'):
                    name = obj.added_by.get_full_name()
                elif hasattr(obj.added_by, 'full_name'):
                    name = obj.added_by.full_name
                else:
                    name = getattr(obj.added_by, 'first_name', '') + ' ' + getattr(obj.added_by, 'last_name', '')
                    name = name.strip()
                
                display_name = name or obj.added_by.email or obj.added_by.username
                return format_html('<small>{}</small>', display_name)
            except Exception:
                return format_html('<small>{}</small>', str(obj.added_by))
        return format_html('<small><em>System</em></small>')
    added_by_info.short_description = 'Added By'
    added_by_info.admin_order_field = 'added_by__email'

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related(
            'project',
            'user',
            'added_by'
        )

    def promote_to_admin(self, request, queryset):
        """Admin action to promote collaborators to admin role"""
        try:
            updated = queryset.exclude(role='admin').update(role='admin')
            if updated > 0:
                self.message_user(
                    request, 
                    f'{updated} collaborator(s) promoted to admin.', 
                    messages.SUCCESS
                )
            else:
                self.message_user(
                    request, 
                    'No collaborators were promoted (they may already be admins).', 
                    messages.WARNING
                )
        except Exception as e:
            self.message_user(
                request, 
                f'Error promoting collaborators: {str(e)}', 
                messages.ERROR
            )
    promote_to_admin.short_description = 'Promote to admin role'

    def demote_to_viewer(self, request, queryset):
        """Admin action to demote collaborators to viewer role"""
        try:
            updated = queryset.exclude(role='viewer').update(role='viewer')
            if updated > 0:
                self.message_user(
                    request, 
                    f'{updated} collaborator(s) demoted to viewer.', 
                    messages.SUCCESS
                )
            else:
                self.message_user(
                    request, 
                    'No collaborators were demoted (they may already be viewers).', 
                    messages.WARNING
                )
        except Exception as e:
            self.message_user(
                request, 
                f'Error demoting collaborators: {str(e)}', 
                messages.ERROR
            )
    demote_to_viewer.short_description = 'Demote to viewer role'

    def remove_collaborators(self, request, queryset):
        """Admin action to remove collaborators"""
        try:
            count = queryset.count()
            if count > 0:
                queryset.delete()
                self.message_user(
                    request, 
                    f'{count} collaborator(s) removed.', 
                    messages.SUCCESS
                )
            else:
                self.message_user(
                    request, 
                    'No collaborators selected for removal.', 
                    messages.WARNING
                )
        except Exception as e:
            self.message_user(
                request, 
                f'Error removing collaborators: {str(e)}', 
                messages.ERROR
            )
    remove_collaborators.short_description = 'Remove selected collaborators'

    def save_model(self, request, obj, form, change):
        """Override save_model to add validation and set added_by"""
        try:
            if not change and not obj.added_by:
                obj.added_by = request.user
            obj.full_clean()
            super().save_model(request, obj, form, change)
        except ValidationError as e:
            messages.error(request, f'Validation error: {e}')
            raise
        except Exception as e:
            messages.error(request, f'Error saving collaborator: {e}')
            raise


# Custom admin site configuration
admin.site.site_header = 'Server Dev Collaboration Admin'
admin.site.site_title = 'Collaboration Admin'
admin.site.index_title = 'Collaboration Management'