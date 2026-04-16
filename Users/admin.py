from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin interface for User model
    """
    list_display = [
        'username', 'email', 'first_name', 'last_name',
        'is_verified', 'consensus_score', 'learning_level',
        'is_staff', 'created_at'
    ]
    
    list_filter = [
        'is_staff', 'is_superuser', 'is_active', 'is_verified',
        'gender_identity', 'learning_level', 'created_at'
    ]
    
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
    ordering = ['-created_at']
    
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'last_login',
        'total_reels_watched', 'total_votes_cast'
    ]
    
    fieldsets = (
        (None, {
            'fields': ('id', 'email', 'username', 'password')
        }),
        (_('Personal Info'), {
            'fields': (
                'first_name', 'last_name', 'date_of_birth',
                'gender_identity', 'gender_identity_custom',
                'profile_picture', 'bio', 'phone_number'
            )
        }),
        (_('Verification & Security'), {
            'fields': ('is_verified', 'is_active')
        }),
        (_('Permissions'), {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        (_('Gamification & Stats'), {
            'fields': (
                'consensus_score', 'learning_level',
                'total_reels_watched', 'total_votes_cast'
            )
        }),
        (_('Settings'), {
            'fields': ('notification_preferences', 'privacy_settings'),
            'classes': ('collapse',)
        }),
        (_('Important Dates'), {
            'fields': ('last_login', 'created_at', 'updated_at')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'username', 'password1', 'password2',
                'first_name', 'last_name', 'is_staff', 'is_verified'
            ),
        }),
    )