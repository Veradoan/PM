
from django.urls import path
from . import views, views_admin


urlpatterns = [
    # ==================== DOCUMENT ====================
    path('list/', views.document_list, name='document_list'),
    path('search/', views.search_view, name='search'),
    path('detail/<int:id>/', views.document_detail, name='document_detail'),

    # ==================== RATING & COMMENT ====================
    path('rate/', views.save_rating, name='save_rating'),
    path('comment/', views.save_comment, name='save_comment'),

    # ==================== UPLOAD & COURSE ====================
    path('upload/', views.upload_document, name='upload_document'),
    path('get-courses/', views.get_courses, name='get_courses'),
    path('my-uploads/', views.my_uploads, name='my_uploads'),

    # ==================== DOWNLOAD & PREVIEW ====================
    path('download/<int:id>/', views.download_document, name='download_document'),
    path('preview/<int:id>/', views.preview_document, name='preview_document'),

    # ==================== MODERATOR ====================
    path('moderator/pending/', views.pending_documents, name='pending_documents'),
    path('moderator/approve/<int:id>/', views.approve_document, name='approve_document'),
    path('moderator/reject/<int:id>/', views.reject_document, name='reject_document'),

    # ==================== REPORT ====================
    path('report/<int:id>/', views.report_document, name='report_document'),
    path('moderator/reports/', views.pending_reports, name='pending_reports'),
    path('moderator/reports/resolve/<int:id>/', views.resolve_report, name='resolve_report'),

    # ==================== MODERATOR API + WORKSPACE ====================
    path(
        'api/moderation/documents/<int:id>/approve/',
        views.approve_document,
        name='api_approve_document'
    ),
    path(
        'api/moderation/documents/<int:id>/reject/',
        views.reject_document,
        name='api_reject_document'
    ),
    path('moderator/workspace/', views.moderator_dashboard, name='moderator_dashboard'),
    path('moderator/history/', views.moderation_history, name='moderation_history'),
    path('moderator/my-activity/', views.my_activity, name='my_activity'),

    # ==================== ADMIN DASHBOARD & MANAGEMENT ====================
    # URL duy nhất cho Admin Dashboard
    path('dashboard/admin/', views_admin.admin_dashboard_view, name='admin_dashboard'),

    # Quản lý người dùng
    path('dashboard/admin/users/', views_admin.user_management, name='user_management'),
    path('dashboard/admin/users/add/', views_admin.admin_add_user, name='admin_add_user'),
    path(
        'dashboard/admin/users/change-role/<int:user_id>/',
        views_admin.change_user_role,
        name='change_user_role'
    ),

    # Quản lý khoa
    path('dashboard/admin/faculties/', views_admin.admin_faculties, name='admin_faculties'),

    # Quản lý môn học
    path('dashboard/admin/courses/', views_admin.admin_courses, name='admin_courses'),

    # Quản lý tài liệu
    path('dashboard/admin/documents/', views_admin.admin_documents, name='admin_documents'),

    # Báo cáo vi phạm
    path('dashboard/admin/reports/', views_admin.admin_reports, name='admin_reports'),

    # Thống kê đánh giá
    path('dashboard/admin/statistics/', views_admin.admin_statistics, name='admin_statistics'),

    # Cài đặt hệ thống
    path('dashboard/admin/settings/', views_admin.admin_settings, name='admin_settings'),

    # Đăng xuất admin
    path('dashboard/admin/logout/', views_admin.admin_logout, name='admin_logout'),
]
