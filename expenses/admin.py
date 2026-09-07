from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Member


@admin.register(Member)
class MemberAdmin(UserAdmin):
    list_display = ['username', 'name', 'email', 'is_active', 'is_staff']
    list_filter = ['is_active', 'is_staff', 'is_superuser']
    search_fields = ['username', 'name', 'email']
    ordering = ['name']

    fieldsets = [
        (None, {'fields': ['username', 'password']}),
        ('Personal info', {'fields': ['name', 'email']}),
        (
            'Permissions',
            {
                'fields': [
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                ]
            },
        ),
        ('Important dates', {'fields': ['last_login', 'date_joined']}),
    ]

    add_fieldsets = [
        (
            None,
            {
                'classes': ['wide'],
                'fields': ['username', 'name', 'password1', 'password2'],
            },
        ),
    ]
