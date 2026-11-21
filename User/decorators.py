from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_required(*allowed_roles):
    """Allow access only to authenticated users with one of the given roles."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url='login')
        def wrapper(request, *args, **kwargs):
            if request.user.role not in allowed_roles:
                messages.error(
                    request,
                    'Bạn không có quyền thực hiện chức năng này.'
                )
                return redirect('document_list')
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
