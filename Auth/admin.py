from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.safestring import mark_safe
from .models import CustomUser, Profile

class CustomUserAdmin(UserAdmin):
    """
    Custom admin for CustomUser model
    """
    model = CustomUser
    list_display = ('email', 'username', 'full_name', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_active', 'date_joined')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('username', 'full_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'password1', 'password2'),
        }),
        ('Optional', {
            'classes': ('wide',),
            'fields': ('username',),
        }),
    )
    search_fields = ('email', 'username', 'full_name')
    ordering = ('email',)

class ProfileAdmin(admin.ModelAdmin):
    """
    Admin configuration for Profile model
    """
    list_display = ('user', 'photo_preview', 'created_at', 'updated_at', 'is_active')
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = ('user__email', 'user__full_name', 'bio')
    readonly_fields = ('created_at', 'updated_at', 'photo_preview')
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Profile Details', {
            'fields': ('photo', 'photo_preview', 'bio', 'github_link')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def photo_preview(self, obj):
        """Display a small preview of the profile photo"""
        if obj.photo:
            try:
                return mark_safe(
                    f'<img src="{obj.photo.url}" width="50" height="50" '
                    f'style="object-fit: cover; border-radius: 50%; border: 1px solid #ddd;" />'
                )
            except (ValueError, AttributeError):
                return 'Photo file not found'
        return 'No photo'
    photo_preview.short_description = 'Profile Photo'

# Register your models here.
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Profile, ProfileAdmin)