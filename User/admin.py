from django.contrib import admin
from .models import Country, CustomUser
from django.contrib.auth.admin import UserAdmin

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # Đã GỘP list_display lại, vừa có get_level cũ, vừa có role mới
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
    
    # Bổ sung trường role vào giao diện chỉnh sửa chi tiết
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

# ĐÃ XÓA dòng admin.site.register ở đây vì đã dùng @admin.register ở trên