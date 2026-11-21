from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, Avg
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
import json
from django.http import JsonResponse
# Import các models theo cấu trúc dự án của bạn
# Thay đổi tên Model cho khớp với file models.py thực tế nếu cần
from .models import Document, Rate, Report, ModerationLog,CustomUser
from django.db.models import Q
from django.core.paginator import Paginator
from .decorators import admin_required
User = get_user_model()
from django.db.models.functions import TruncMonth
# Import Decorator vừa tạo
from .decorators import custom_admin_required
from django.contrib import messages
from django.contrib.auth.hashers import make_password


#@user_passes_test(admin_required)
@custom_admin_required
def admin_dashboard_view(request):
    # 1. THỐNG KÊ CÁC THẺ CARD (Sử dụng .count() tối ưu)
    total_users = CustomUser.objects.count()
    
    # Sửa: Chắc chắn status/resolved được khai báo đúng theo model của bạn
    total_approved_docs = Document.objects.filter(status='approved').count()
    total_pending_docs = Document.objects.filter(status='pending').count()
    total_rejected_docs = Document.objects.filter(status='rejected').count()
    total_pending_reports = Report.objects.filter(resolved=False).count()

    # 2. DỮ LIỆU BIỂU ĐỒ TRẠNG THÁI TÀI LIỆU
    doc_status_data = [
        total_approved_docs,
        total_pending_docs,
        total_rejected_docs
    ]

    # 3. DỮ LIỆU BIỂU ĐỒ TĂNG TRƯỞNG NGƯỜI DÙNG (6 tháng qua)
    six_months_ago = timezone.now() - timedelta(days=180)
    user_growth = (
        CustomUser.objects
        .filter(date_joined__gte=six_months_ago)
        .annotate(month=TruncMonth('date_joined'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )

    user_growth_labels = [item['month'].strftime('%m/%Y') for item in user_growth if item['month']]
    user_growth_values = [item['count'] for item in user_growth if item['month']]

    # 4. HOẠT ĐỘNG GẦN ĐÂY (Lấy 5 hoạt động mới nhất)
    # Cần select_related đúng ForeignKey của bảng (tùy thuộc vào việc bảng dùng 'moderator' hay 'user')
    # Ở đây giả sử model ModerationLog dùng field 'moderator' và 'document'
    recent_activities = ModerationLog.objects.select_related('moderator', 'document').order_by('-created_at')[:5]

    # 5. GỬI DỮ LIỆU SANG TEMPLATE
    context = {
        'total_users': total_users,
        'total_approved_docs': total_approved_docs,
        'total_pending_docs': total_pending_docs,
        'total_pending_reports': total_pending_reports,
        'recent_activities': recent_activities, # Gửi danh sách hoạt động
        
        # Chart data
        'doc_status_data': json.dumps(doc_status_data),
        'user_growth_labels': json.dumps(user_growth_labels),
        'user_growth_values': json.dumps(user_growth_values),
    }
    
    return render(request, 'admin_panel/dashboard.html', context)
# Hàm kiểm tra quyền
@admin_required
def is_admin(user):
    return user.is_authenticated and user.role == 'admin'

#@user_passes_test(is_admin, login_url='/')
@admin_required
@custom_admin_required
# --- Thêm Decorator phân quyền ở bước sau, tạm thời giữ nguyên hàm ---
def admin_dashboard_view(request):
    # 1. THỐNG KÊ CÁC THẺ CARD (Sử dụng .count() tối ưu)
    total_users = CustomUser.objects.count()
    
    # LƯU Ý: Django choices thường lưu giá trị ở database là chữ IN HOA (tùy cấu trúc model của bạn)
    # Ví dụ: 'PENDING', 'APPROVED', 'REJECTED'. Nếu model của bạn dùng chữ thường, hãy giữ nguyên chữ thường.
    total_approved_docs = Document.objects.filter(status='APPROVED').count()
    total_pending_docs = Document.objects.filter(status='PENDING').count()
    
    # SỬA LỖI MODEL: Audit cho thấy Model Report dùng trường `resolved`, không phải `is_resolved` hay `status`
    total_pending_reports = Report.objects.filter(resolved=False).count()

    # 2. DỮ LIỆU BIỂU ĐỒ TRẠNG THÁI TÀI LIỆU (Doughnut Chart)
    doc_status_data = [
        total_approved_docs,
        total_pending_docs,
        Document.objects.filter(status='REJECTED').count()
    ]

    # 3. DỮ LIỆU BIỂU ĐỒ TĂNG TRƯỞNG NGƯỜI DÙNG (Line Chart - 6 tháng)
    six_months_ago = timezone.now() - timedelta(days=180)
    user_growth = (
        CustomUser.objects
        .filter(date_joined__gte=six_months_ago)
        .annotate(month=TruncMonth('date_joined'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )

    # Tách dữ liệu thành 2 mảng cho Chart.js (Xử lý an toàn trường hợp month là None)
    user_growth_labels = [item['month'].strftime('%m/%Y') for item in user_growth if item['month']]
    user_growth_values = [item['count'] for item in user_growth if item['month']]

    # 4. GỬI DỮ LIỆU SANG TEMPLATE
    context = {
        # Card data
        'total_users': total_users,
        'total_approved_docs': total_approved_docs,
        'total_pending_docs': total_pending_docs,
        'total_pending_reports': total_pending_reports,
        
        # Chart data (json.dumps để tránh lỗi escape script trong HTML)
        'doc_status_data': json.dumps(doc_status_data),
        'user_growth_labels': json.dumps(user_growth_labels),
        'user_growth_values': json.dumps(user_growth_values),
    }
    
    return render(request, 'admin_panel/dashboard.html', context)

@user_passes_test(is_admin, login_url='/')
@admin_required
def dashboard_chart_data(request):
    # Dữ liệu 1: Phân bổ trạng thái tài liệu
    # Dùng .values().annotate() để tương đương với GROUP BY status trong SQL
    doc_distribution = Document.objects.values('status').annotate(total=Count('id'))
    
    status_labels = []
    status_data = []
    status_mapping = {'approved': 'Đã duyệt', 'pending': 'Chờ duyệt', 'rejected': 'Từ chối'}
    
    for item in doc_distribution:
        status_labels.append(status_mapping.get(item['status'], item['status']))
        status_data.append(item['total'])

    # Dữ liệu 2: Tăng trưởng người dùng 6 tháng qua
    six_months_ago = timezone.now() - timedelta(days=180)
    user_growth = (
        CustomUser.objects
        .filter(date_joined__gte=six_months_ago)
        .annotate(month=TruncMonth('date_joined')) # Nhóm theo tháng
        .values('month')
        .annotate(count=Count('id')) # Đếm số user mỗi tháng
        .order_by('month')
    )

    growth_labels = [item['month'].strftime('%m/%Y') for item in user_growth]
    growth_data = [item['count'] for item in user_growth]

    return JsonResponse({
        'doc_status': {
            'labels': status_labels,
            'data': status_data
        },
        'user_growth': {
            'labels': growth_labels,
            'data': growth_data
        }
    })
@custom_admin_required
def user_management(request):
    user_list = CustomUser.objects.all().order_by('id')

    # Nhận biến 'search' từ form HTML
    search_query = request.GET.get('search', '').strip()
    if search_query:
        user_list = user_list.filter(
            Q(username__icontains=search_query) | 
            Q(email__icontains=search_query)
        )

    # Nhận biến 'role' từ form HTML
    role_filter = request.GET.get('role', '')
    if role_filter:
        user_list = user_list.filter(role=role_filter)

    paginator = Paginator(user_list, 20) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
    }
    return render(request, 'admin_panel/users.html', context)
@custom_admin_required
def change_user_role(request, user_id):
    """
    Xử lý thao tác Khóa/Mở khóa hoặc đổi Role của người dùng.
    Bắt buộc gọi qua phương thức POST để bảo mật.
    """
    if request.method == 'POST':
        user_to_change = get_object_or_404(CustomUser, id=user_id)

        # BẢO MẬT: Không cho phép Admin tự khóa/đổi quyền chính mình
        if user_to_change.id == request.user.id:
            messages.error(request, "Bạn không thể tự thay đổi quyền hoặc khóa tài khoản của chính mình!")
            return redirect('user_management')

        # Hành động 1: Khóa / Mở khóa tài khoản (Toggle Active status)
        if 'toggle_active' in request.POST:
            user_to_change.is_active = not user_to_change.is_active
            status_msg = "mở khóa" if user_to_change.is_active else "khóa"
            user_to_change.save()
            messages.success(request, f"Đã {status_msg} tài khoản {user_to_change.username} thành công.")
            return redirect('user_management') # SỬA LỖI: Thêm return redirect ngay tại đây

        # Hành động 2: Đổi Role
        elif 'new_role' in request.POST:
            new_role = request.POST.get('new_role')
            # Kiểm tra cả giá trị viết thường và IN HOA để đảm bảo khớp với CSDL
            valid_roles = ['student', 'moderator', 'admin', 'STUDENT', 'MODERATOR', 'ADMIN']
            
            if new_role in valid_roles:
                user_to_change.role = new_role
                user_to_change.save()
                messages.success(request, f"Đã cập nhật quyền cho {user_to_change.username} thành {new_role}.")
            else:
                messages.error(request, f"Quyền không hợp lệ: {new_role}")
            return redirect('user_management')

    return redirect('user_management')


@custom_admin_required
def admin_add_user(request):
    """
    Xử lý thêm mới User từ trang Admin Dashboard.
    Chỉ cho phép POST.
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role', 'student') # Mặc định là student

        # 1. Validation cơ bản
        if not username or not email or not password:
            messages.error(request, "Vui lòng điền đầy đủ Username, Email và Password.")
            return redirect('user_management')
        
        # 2. Kiểm tra trùng lặp
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, f"Tên người dùng '{username}' đã tồn tại.")
            return redirect('user_management')
            
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, f"Email '{email}' đã tồn tại.")
            return redirect('user_management')

        # 3. Tạo User mới
        try:
            CustomUser.objects.create(
                username=username,
                email=email,
                password=make_password(password), # Quan trọng: Phải hash password
                role=role,
                is_active=True # Mặc định cho phép hoạt động
            )
            messages.success(request, f"Đã thêm người dùng {username} thành công.")
        except Exception as e:
            messages.error(request, f"Có lỗi xảy ra: {str(e)}")

    return redirect('user_management')