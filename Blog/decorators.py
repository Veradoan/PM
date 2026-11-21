from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from functools import wraps
from django.contrib.auth.views import redirect_to_login
from django.contrib import messages
from django.shortcuts import redirect

# LƯU Ý: Không sử dụng @user_passes_test ở đây.
def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Lúc này 'request' chắc chắn là HTTP Request chuẩn của Django
        if not request.user.is_authenticated:
            messages.error(request, "Vui lòng đăng nhập để tiếp tục.")
            return redirect('login') # Đổi 'login' thành name của URL đăng nhập trong dự án của bạn
        
        # Kiểm tra quyền Admin
        if getattr(request.user, 'role', None) == 'admin' or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Từ chối nếu là Student hoặc Moderator
        raise PermissionDenied("Bạn không có quyền truy cập trang quản trị này.")
    return _wrapped_view
def custom_admin_required(view_func):
    """
    Decorator kiểm tra quyền truy cập Admin Dashboard riêng của AcademicShare.
    Chỉ cho phép tài khoản đang active và có role='admin' (hoặc is_superuser).
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 1. Kiểm tra đăng nhập
        if not request.user.is_authenticated:
            messages.error(request, "Vui lòng đăng nhập để truy cập hệ thống.")
            return redirect('login') # Thay 'login' bằng tên URL đăng nhập thực tế của bạn

        # 2. Kiểm tra trạng thái tài khoản
        if not request.user.is_active:
            messages.error(request, "Tài khoản của bạn đã bị khóa.")
            return redirect('login')

        # 3. Kiểm tra quyền Admin (Dựa vào trường 'role' trong CustomUser hoặc is_superuser)
        # Lưu ý: Điều chỉnh 'admin' (viết thường hoặc IN HOA) cho khớp với choices trong model CustomUser của bạn
        is_admin_role = getattr(request.user, 'role', None) == 'admin'
        
        if is_admin_role or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Nếu là Student hoặc Moderator thì từ chối truy cập
        messages.error(request, "Bạn không có quyền truy cập vào trang Quản trị viên.")
        return redirect('index') # Trả về trang chủ hoặc trang dashboard của user/moderator

    return _wrapped_view