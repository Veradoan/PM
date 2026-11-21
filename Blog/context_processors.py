"""
Context processors cho admin panel.

Cung cấp dữ liệu chung (số báo cáo chờ xử lý, danh sách báo cáo gần đây)
cho tất cả template admin_panel/* thông qua template context,
tránh phải lặp lại trong từng view.
"""
from .models import Report


def admin_context(request):
    """Inject dữ liệu thông báo cho admin panel vào context."""
    data = {}
    # Chỉ nạp khi user đã đăng nhập và là admin (tránh query thừa cho user thường)
    if (
        getattr(request, 'user', None)
        and request.user.is_authenticated
        and (
            getattr(request.user, 'role', None) == 'admin'
            or getattr(request.user, 'is_superuser', False)
        )
    ):
        pending_qs = Report.objects.filter(resolved=False).select_related(
            'document', 'user'
        ).order_by('-created_at')
        data['pending_reports_count'] = pending_qs.count()
        data['recent_reports'] = list(pending_qs[:5])
    return data
