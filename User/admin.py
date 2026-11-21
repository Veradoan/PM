from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Country, CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'username',
        'email',
        'role',
        'get_level',
        'first_name',
        'last_name',
        'is_active',
        'is_staff',
    )

    search_fields = (
        'username',
        'email',
        'first_name',
        'last_name',
    )

    list_filter = (
        'is_superuser',
        'is_staff',
        'is_active',
    )

    fieldsets = UserAdmin.fieldsets + (
        ('Thông tin phân quyền', {'fields': ('role',)}),
    )

    def get_level(self, obj):
        if obj.is_superuser:
            return 'ADMIN'
        return 'MEMBER'

    get_level.short_description = 'Level'


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)