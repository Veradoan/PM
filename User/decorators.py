from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied


def role_required(*allowed_roles):
    """
    Decorator kiểm tra role của user trước khi cho phép truy cập View.
    Sử dụng: @role_required('moderator', 'admin')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url='login')
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
                
            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            else:
                # Trả về lỗi 403 Forbidden nếu không đủ quyền
                raise PermissionDenied("Bạn không có quyền truy cập chức năng này.")
        return _wrapped_view
    return decorator
