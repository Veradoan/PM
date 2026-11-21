from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
import json
from django.http import JsonResponse
# Import các models theo cấu trúc dự án của bạn
# Thay đổi tên Model cho khớp với file models.py thực tế nếu cần
from .models import Document, Rate, Report, ModerationLog, CustomUser, Faculty, Course, Comment
from django.core.paginator import Paginator
from .decorators import admin_required, custom_admin_required
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth import logout as auth_logout
from django.db.models.functions import TruncMonth

User = get_user_model()


# Hàm kiểm tra quyền (giữ nguyên để tương thích ngược)
@admin_required
def is_admin(user):
    return user.is_authenticated and user.role == 'admin'


# ============================================================
# 1. ADMIN DASHBOARD (chính)
# ============================================================
@custom_admin_required
def admin_dashboard_view(request):
    """
    Trang Dashboard chính của Admin.
    Hiển thị:
      - 4 thẻ thống kê (Tổng user, Tài liệu đã duyệt, Chờ duyệt, Báo cáo vi phạm)
      - 2 biểu đồ (Tăng trưởng user 6 tháng, Trạng thái tài liệu)
      - Danh sách 5 hoạt động kiểm duyệt gần đây
    """
    # 1. THỐNG KÊ CÁC THẺ CARD
    total_users = CustomUser.objects.count()
    total_approved_docs = Document.objects.filter(status='approved').count()
    total_pending_docs = Document.objects.filter(status='pending').count()
    total_rejected_docs = Document.objects.filter(status='rejected').count()
    total_pending_reports = Report.objects.filter(resolved=False).count()

    # 2. DỮ LIỆU BIỂU ĐỒ TRẠNG THÁI TÀI LIỆU (Doughnut)
    doc_status_data = [
        total_approved_docs,
        total_pending_docs,
        total_rejected_docs,
    ]

    # 3. DỮ LIỆU BIỂU ĐỒ TĂNG TRƯỞNG NGƯỜI DÙNG (Line - 6 tháng)
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

    # 4. HOẠT ĐỘNG KIỂM DUYỆT GẦN ĐÂY (5 bản ghi mới nhất)
    recent_activities = (
        ModerationLog.objects
        .select_related('moderator', 'document')
        .order_by('-created_at')[:5]
    )

    # 5. GỬI DỮ LIỆU SANG TEMPLATE
    context = {
        'total_users': total_users,
        'total_approved_docs': total_approved_docs,
        'total_pending_docs': total_pending_docs,
        'total_pending_reports': total_pending_reports,
        'recent_activities': recent_activities,

        # Chart data
        'doc_status_data': json.dumps(doc_status_data),
        'user_growth_labels': json.dumps(user_growth_labels),
        'user_growth_values': json.dumps(user_growth_values),
    }

    return render(request, 'admin_panel/dashboard.html', context)


# ============================================================
# 2. DASHBOARD CHART DATA (API JSON cho Chart.js khi cần fetch)
# ============================================================
@admin_required
def dashboard_chart_data(request):
    """Trả JSON cho Chart.js khi cần load động."""
    doc_distribution = Document.objects.values('status').annotate(total=Count('id'))
    status_labels = []
    status_data = []
    status_mapping = {'approved': 'Đã duyệt', 'pending': 'Chờ duyệt', 'rejected': 'Từ chối'}
    for item in doc_distribution:
        status_labels.append(status_mapping.get(item['status'], item['status']))
        status_data.append(item['total'])

    six_months_ago = timezone.now() - timedelta(days=180)
    user_growth = (
        CustomUser.objects
        .filter(date_joined__gte=six_months_ago)
        .annotate(month=TruncMonth('date_joined'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    growth_labels = [item['month'].strftime('%m/%Y') for item in user_growth if item['month']]
    growth_data = [item['count'] for item in user_growth if item['month']]

    return JsonResponse({
        'doc_status': {'labels': status_labels, 'data': status_data},
        'user_growth': {'labels': growth_labels, 'data': growth_data},
    })


# ============================================================
# 3. USER MANAGEMENT
# ============================================================
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
    Bắt buộc gọi qua POST để bảo mật.
    """
    if request.method == 'POST':
        user_to_change = get_object_or_404(CustomUser, id=user_id)

        # BẢO MẬT: Không cho phép Admin tự khóa/đổi quyền chính mình
        if user_to_change.id == request.user.id:
            messages.error(request, "Bạn không thể tự thay đổi quyền hoặc khóa tài khoản của chính mình!")
            return redirect('user_management')

        # Hành động 1: Khóa / Mở khóa tài khoản
        if 'toggle_active' in request.POST:
            user_to_change.is_active = not user_to_change.is_active
            user_to_change.save()
            status_msg = "mở khóa" if user_to_change.is_active else "khóa"
            messages.success(request, f"Đã {status_msg} tài khoản {user_to_change.username} thành công.")
            return redirect('user_management')

        # Hành động 2: Đổi Role
        elif 'new_role' in request.POST:
            new_role = request.POST.get('new_role')
            valid_roles = ['student', 'moderator', 'admin']
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
    """Thêm mới User từ trang Admin Dashboard."""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role', 'student')

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
                password=make_password(password),
                role=role,
                is_active=True,
            )
            messages.success(request, f"Đã thêm người dùng {username} thành công.")
        except Exception as e:
            messages.error(request, f"Có lỗi xảy ra: {str(e)}")

    return redirect('user_management')


# ============================================================
# 4. FACULTY MANAGEMENT (Quản lý Khoa)
# ============================================================
@custom_admin_required
def admin_faculties(request):
    """Danh sách Khoa + thêm/xóa nhanh."""
    faculties = Faculty.objects.all().annotate(
        course_count=Count('courses'),
        doc_count=Count('documents'),
    ).order_by('id')

    search_query = request.GET.get('search', '').strip()
    if search_query:
        faculties = faculties.filter(name__icontains=search_query)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            name = request.POST.get('name', '').strip()
            if not name:
                messages.error(request, "Tên khoa không được để trống.")
            elif Faculty.objects.filter(name__iexact=name).exists():
                messages.error(request, f"Khoa '{name}' đã tồn tại.")
            else:
                Faculty.objects.create(name=name)
                messages.success(request, f"Đã thêm khoa '{name}' thành công.")
            return redirect('admin_faculties')

        if action == 'delete':
            faculty_id = request.POST.get('faculty_id')
            faculty = get_object_or_404(Faculty, id=faculty_id)
            name = faculty.name
            faculty.delete()
            messages.success(request, f"Đã xóa khoa '{name}'.")
            return redirect('admin_faculties')

        if action == 'edit':
            faculty_id = request.POST.get('faculty_id')
            new_name = request.POST.get('name', '').strip()
            faculty = get_object_or_404(Faculty, id=faculty_id)
            if not new_name:
                messages.error(request, "Tên khoa không được để trống.")
            elif Faculty.objects.filter(name__iexact=new_name).exclude(id=faculty_id).exists():
                messages.error(request, f"Khoa '{new_name}' đã tồn tại.")
            else:
                faculty.name = new_name
                faculty.save()
                messages.success(request, f"Đã cập nhật khoa thành '{new_name}'.")
            return redirect('admin_faculties')

    context = {
        'faculties': faculties,
        'search_query': search_query,
    }
    return render(request, 'admin_panel/faculties.html', context)


# ============================================================
# 5. COURSE MANAGEMENT (Quản lý Môn học)
# ============================================================
@custom_admin_required
def admin_courses(request):
    """Danh sách Môn học + thêm/xóa."""
    courses = Course.objects.select_related('faculty').annotate(
        doc_count=Count('documents'),
    ).order_by('id')

    faculties = Faculty.objects.all().order_by('name')

    search_query = request.GET.get('search', '').strip()
    faculty_filter = request.GET.get('faculty', '').strip()
    if search_query:
        courses = courses.filter(name__icontains=search_query)
    if faculty_filter:
        courses = courses.filter(faculty_id=faculty_filter)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            name = request.POST.get('name', '').strip()
            faculty_id = request.POST.get('faculty_id')
            if not name or not faculty_id:
                messages.error(request, "Vui lòng nhập tên môn học và chọn khoa.")
            else:
                faculty = get_object_or_404(Faculty, id=faculty_id)
                Course.objects.create(name=name, faculty=faculty)
                messages.success(request, f"Đã thêm môn học '{name}' vào khoa '{faculty.name}'.")
            return redirect('admin_courses')

        if action == 'delete':
            course_id = request.POST.get('course_id')
            course = get_object_or_404(Course, id=course_id)
            name = course.name
            course.delete()
            messages.success(request, f"Đã xóa môn học '{name}'.")
            return redirect('admin_courses')

        if action == 'edit':
            course_id = request.POST.get('course_id')
            new_name = request.POST.get('name', '').strip()
            faculty_id = request.POST.get('faculty_id')
            course = get_object_or_404(Course, id=course_id)
            if not new_name or not faculty_id:
                messages.error(request, "Vui lòng nhập tên môn học và chọn khoa.")
            else:
                faculty = get_object_or_404(Faculty, id=faculty_id)
                course.name = new_name
                course.faculty = faculty
                course.save()
                messages.success(request, f"Đã cập nhật môn học thành '{new_name}'.")
            return redirect('admin_courses')

    context = {
        'courses': courses,
        'faculties': faculties,
        'search_query': search_query,
        'faculty_filter': faculty_filter,
    }
    return render(request, 'admin_panel/courses.html', context)


# ============================================================
# 6. DOCUMENT MANAGEMENT (Quản lý Tài liệu)
# ============================================================
@custom_admin_required
def admin_documents(request):
    """Danh sách toàn bộ tài liệu (mọi trạng thái) + xóa + đổi trạng thái."""
    documents = Document.objects.select_related(
        'uploaded_by', 'faculty', 'course'
    ).order_by('-created_at')

    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    if search_query:
        documents = documents.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(uploaded_by__username__icontains=search_query)
        )
    if status_filter:
        documents = documents.filter(status=status_filter)

    paginator = Paginator(documents, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('document_id')
        document = get_object_or_404(Document, id=doc_id)

        if action == 'delete':
            title = document.title
            document.delete()
            messages.success(request, f"Đã xóa tài liệu '{title}'.")
            return redirect('admin_documents')

        if action == 'approve':
            document.status = 'approved'
            document.reviewed_by = request.user
            document.reviewed_at = timezone.now()
            document.save()
            ModerationLog.objects.create(
                moderator=request.user,
                action='approve',
                document=document,
            )
            messages.success(request, f"Đã duyệt tài liệu '{document.title}'.")
            return redirect('admin_documents')

        if action == 'reject':
            reason = request.POST.get('reason', '').strip()
            document.status = 'rejected'
            document.reviewed_by = request.user
            document.reviewed_at = timezone.now()
            document.review_note = reason
            document.save()
            ModerationLog.objects.create(
                moderator=request.user,
                action='reject',
                document=document,
                reason=reason,
            )
            messages.success(request, f"Đã từ chối tài liệu '{document.title}'.")
            return redirect('admin_documents')

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    return render(request, 'admin_panel/documents.html', context)


# ============================================================
# 7. REPORTS MANAGEMENT (Báo cáo Vi phạm)
# ============================================================
@custom_admin_required
def admin_reports(request):
    """Danh sách toàn bộ báo cáo vi phạm + xử lý (resolve)."""
    reports = Report.objects.select_related(
        'document', 'user'
    ).order_by('-created_at')

    status_filter = request.GET.get('status', '').strip()
    if status_filter == 'pending':
        reports = reports.filter(resolved=False)
    elif status_filter == 'resolved':
        reports = reports.filter(resolved=True)

    paginator = Paginator(reports, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        action = request.POST.get('action')
        report_id = request.POST.get('report_id')
        report = get_object_or_404(Report, id=report_id)

        if action == 'resolve':
            report.resolved = True
            report.save()
            ModerationLog.objects.create(
                moderator=request.user,
                action='resolve_report',
                document=report.document,
                report=report,
            )
            messages.success(request, f"Đã xử lý báo cáo #{report.id}.")
            return redirect('admin_reports')

        if action == 'unresolve':
            report.resolved = False
            report.save()
            messages.success(request, f"Đã mở lại báo cáo #{report.id}.")
            return redirect('admin_reports')

        if action == 'delete_document':
            # Xóa luôn tài liệu bị báo cáo nhiều lần
            document = report.document
            title = document.title
            document.delete()
            messages.success(request, f"Đã xóa tài liệu '{title}' theo báo cáo #{report.id}.")
            return redirect('admin_reports')

    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
    }
    return render(request, 'admin_panel/reports.html', context)


# ============================================================
# 8. RATING STATISTICS (Thống kê Đánh giá)
# ============================================================
@custom_admin_required
def admin_statistics(request):
    """Trang thống kê đánh giá: top tài liệu, trung bình sao, phân bố điểm."""
    # Top 10 tài liệu được đánh giá cao nhất (tối thiểu 1 lượt)
    top_documents = (
        Document.objects
        .filter(status='approved', rates__isnull=False)
        .annotate(avg_rate=Avg('rates__rate'), rate_count=Count('rates'))
        .order_by('-avg_rate', '-rate_count')[:10]
    )

    # Top 10 tài liệu được tải nhiều nhất
    top_downloads = (
        Document.objects
        .filter(status='approved')
        .order_by('-download_count')[:10]
    )

    # Phân bố điểm đánh giá (1-5 sao)
    rate_distribution = (
        Rate.objects
        .values('rate')
        .annotate(count=Count('id'))
        .order_by('rate')
    )
    rate_labels = []
    rate_data = []
    for star in range(1, 6):
        match = next((item for item in rate_distribution if item['rate'] == star), None)
        rate_labels.append(f'{star} sao')
        rate_data.append(match['count'] if match else 0)

    # Số liệu tổng
    total_rates = Rate.objects.count()
    total_comments = Comment.objects.count()
    avg_global = Rate.objects.aggregate(avg=Avg('rate'))['avg'] or 0

    # Phân bố loại tài liệu
    doc_type_distribution = (
        Document.objects
        .values('doc_type')
        .annotate(count=Count('id'))
        .order_by('doc_type')
    )
    type_mapping = dict(Document.DOCUMENT_TYPE_CHOICES)
    type_labels = []
    type_data = []
    for item in doc_type_distribution:
        label = type_mapping.get(item['doc_type'], item['doc_type'] or 'Khác')
        type_labels.append(label)
        type_data.append(item['count'])

    context = {
        'top_documents': top_documents,
        'top_downloads': top_downloads,
        'rate_labels': json.dumps(rate_labels),
        'rate_data': json.dumps(rate_data),
        'type_labels': json.dumps(type_labels),
        'type_data': json.dumps(type_data),
        'total_rates': total_rates,
        'total_comments': total_comments,
        'avg_global': round(avg_global, 2),
    }
    return render(request, 'admin_panel/statistics.html', context)


# ============================================================
# 9. SETTINGS (Cài đặt hệ thống - thông tin tổng quan)
# ============================================================
@custom_admin_required
def admin_settings(request):
    """Trang cài đặt hệ thống: hiển thị thông tin cấu hình cơ bản."""
    from django.conf import settings as dj_settings
    from django.contrib.auth import get_user_model

    User = get_user_model()
    # Thông tin hệ thống
    system_info = {
        'django_version': dj_settings.DJANGO_VERSION if hasattr(dj_settings, 'DJANGO_VERSION') else None,
        'debug_mode': dj_settings.DEBUG,
        'time_zone': dj_settings.TIME_ZONE,
        'language_code': dj_settings.LANGUAGE_CODE,
        'total_users': User.objects.count(),
        'total_admins': User.objects.filter(role='admin').count(),
        'total_moderators': User.objects.filter(role='moderator').count(),
        'total_students': User.objects.filter(role='student').count(),
        'total_faculties': Faculty.objects.count(),
        'total_courses': Course.objects.count(),
        'total_documents': Document.objects.count(),
        'total_reports': Report.objects.count(),
    }
    context = {'system_info': system_info}
    return render(request, 'admin_panel/settings.html', context)


# ============================================================
# 10. LOGOUT (riêng cho admin)
# ============================================================
@custom_admin_required
def admin_logout(request):
    """Đăng xuất admin và chuyển về trang đăng nhập."""
    auth_logout(request)
    messages.success(request, "Bạn đã đăng xuất khỏi hệ thống quản trị.")
    return redirect('login')
