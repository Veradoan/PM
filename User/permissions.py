from rest_framework.permissions import BasePermission
from rest_framework import permissions

class IsModeratorOrAdmin(BasePermission):
    """
    Chỉ cho phép Moderator hoặc Admin truy cập.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['moderator', 'admin']
        )


class IsModeratorOrAdmin(permissions.BasePermission):
    # Dòng thông báo lỗi sẽ trả về khi sinh viên cố tình truy cập (Lỗi 403)
    message = "Bạn không có quyền duyệt bài. Chỉ dành cho Moderator hoặc Admin."

    def has_permission(self, request, view):
        # Cho phép đi tiếp NẾU: đã đăng nhập VÀ có role là moderator hoặc admin
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['moderator', 'admin']
        )
class IsAdmin(BasePermission):
    """
    Chỉ cho phép Admin truy cập.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'admin'
        )