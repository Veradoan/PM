from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
import mimetypes
from django.core.paginator import Paginator
from django.http import JsonResponse, FileResponse
from django.db.models import Avg, Q, F
from User.models import CustomUser
from .models import Document, Rate, Comment, Course, Faculty, Report, ModerationLog
import hashlib

from django.contrib import messages
from django.shortcuts import redirect
from User.decorators import role_required

from .forms import DocumentForm, ReportForm
#from rest_framework.decorators import api_view, permission_classes
#from rest_framework.response import Response
from django.utils import timezone
from User.permissions import IsModeratorOrAdmin
from django.views.decorators.http import require_POST
from .decorators import custom_admin_required

def document_list(request):
    documents = Document.objects.filter(
        status='approved'
    ).order_by('-id')

    paginator = Paginator(documents, 3)

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'Blog/index.html',
        {
            'documents': page_obj,
            'page_obj': page_obj,
            'paginator': paginator,
        }
    )


def document_detail(request, id):

    document = get_object_or_404(
        Document,
        id=id,
        status='approved'
    )

    avg_rate = Rate.objects.filter(
        document=document
    ).aggregate(
        Avg('rate')
    )

    avg = avg_rate['rate__avg']

    if avg is None:
        avg = 0
    else:
        avg = round(avg)

    user_rate = 0

    if request.user.is_authenticated:

        rate_obj = Rate.objects.filter(
            document=document,
            user=request.user
        ).first()

        if rate_obj:
            user_rate = rate_obj.rate

    comments = Comment.objects.filter(
        document=document,
        level=0
    ).order_by('-id')

    return render(
        request,
        'Blog/blog_detail.html',
        {
            'document': document,
            'avg': avg,
            'user_rate': user_rate,
            'comment': comments,
        }
    )


def search_view(request):
    keyword = request.GET.get('name', '').strip()
    faculty_id = request.GET.get('faculty')
    course_id = request.GET.get('course')
    doc_type = request.GET.get('doc_type')

    documents = Document.objects.filter(
        status='approved'
    )

    # Tìm theo từ khóa
    if keyword:
        documents = documents.filter(
            Q(title__icontains=keyword) |
            Q(description__icontains=keyword)
        )

    # Lọc theo Faculty
    if faculty_id:
        documents = documents.filter(
            faculty_id=faculty_id
        )

    # Lọc theo Course
    if course_id:
        documents = documents.filter(
            course_id=course_id
        )

    # Lọc theo Document Type
    if doc_type:
        documents = documents.filter(
            doc_type=doc_type
        )

    paginator = Paginator(documents, 3)

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'Blog/search.html',
        {
            'documents': page_obj,
            'page_obj': page_obj,
            'keyword': keyword,
            'faculties': Faculty.objects.all(),
            'courses': Course.objects.all(),
            'selected_faculty': faculty_id,
            'selected_course': course_id,
            'selected_doc_type': doc_type,
        }
    )

def save_rating(request):

    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Invalid request'
        })

    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Vui long dang nhap'
        })

    document_id = request.POST.get('document_id')
    rate = request.POST.get('rate')

    try:
        document = Document.objects.get(
            id=document_id,
            status='approved'
        )

        old_rate = Rate.objects.filter(
            document=document,
            user=request.user
        ).first()

        if old_rate:
            old_rate.rate = int(rate)
            old_rate.save()

        else:
            Rate.objects.create(
                document=document,
                rate=int(rate),
                user=request.user
            )

        avg = Rate.objects.filter(
            document=document
        ).aggregate(
            Avg('rate')
        )

        return JsonResponse({
            'success': True,
            'avg': round(avg['rate__avg'], 1)
        })

    except Document.DoesNotExist:

        return JsonResponse({
            'success': False,
            'error': 'Document not found'
        })


def save_comment(request):

    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Invalid request'
        })

    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Vui long dang nhap'
        })

    document_id = request.POST.get('document_id')
    comment = request.POST.get('comment')
    level = request.POST.get('level', 0)
    parent_id = request.POST.get('parent_id')

    if not level:
        level = 0

    document = get_object_or_404(
        Document,
        id=document_id,
        status='approved'
    )

    new_comment = Comment.objects.create(
        document=document,
        comment=comment,
        user=request.user,
        level=level,
        parent_id=parent_id if parent_id else None
    )

    return JsonResponse({
        'success': True,
        'data': {
            'id': new_comment.id,
            'comment': new_comment.comment,
            'author_name': request.user.username,
            'author_id': request.user.id,
            'level': new_comment.level,
            'parent_id': parent_id,
        }
    })
@login_required
def upload_document(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)

        if form.is_valid():
            uploaded_file = request.FILES['file']

            # Tính SHA-256
            sha256 = hashlib.sha256()

            for chunk in uploaded_file.chunks():
                sha256.update(chunk)

            file_hash = sha256.hexdigest()

            # Kiểm tra file trùng
            if Document.objects.filter(file_hash=file_hash).exists():
                messages.error(
                    request,
                    'This document already exists.'
                )
                return render(
                    request,
                    'Blog/upload_document.html',
                    {'form': form}
                )

            document = form.save(commit=False)

            document.uploaded_by = request.user
            document.file_hash = file_hash
            document.status = 'pending'

            document.save()

            messages.success(
                request,
                'Document uploaded successfully and is waiting for approval.'
            )

            return redirect('document_list')

    else:
        form = DocumentForm()

    return render(
        request,
        'Blog/upload_document.html',
        {'form': form}
    )
def get_courses(request):
    faculty_id = request.GET.get('faculty_id')

    courses = Course.objects.filter(faculty_id=faculty_id).values('id', 'name')

    return JsonResponse(list(courses), safe=False)
@role_required('moderator', 'admin')
def pending_documents(request):
    """Trang kiểm duyệt tổng quan: Hiển thị thống kê và danh sách chờ duyệt"""
    # 1. Lấy danh sách tài liệu chờ duyệt
    documents = Document.objects.filter(status='pending').order_by('-created_at')
    
    # 2. Tính toán các con số thống kê
    pending_docs_count = documents.count() # Số tài liệu chờ duyệt
    pending_reports_count = Report.objects.filter(resolved=False).count() # Số báo cáo chờ xử lý
    
    # (Nếu bạn đã làm bước tạo ModerationLog, có thể thêm số lượng đã duyệt hôm nay)
    # approved_today = ModerationLog.objects.filter(action='approve', created_at__date=timezone.now().date()).count()
    
    context = {
        'documents': documents,
        'pending_docs_count': pending_docs_count,
        'pending_reports_count': pending_reports_count,
        # 'approved_today': approved_today,
    }
    
    return render(request, 'Blog/pending_documents.html', context)
# ==============================================================
# API DUYỆT / TỪ CHỐI TÀI LIỆU (POST)
# ==============================================================
@require_POST
@role_required('moderator', 'admin')
def approve_document(request, id):
    try:
        document = Document.objects.get(id=id)
        
        if document.status != 'pending':
            messages.error(request, "Chỉ có thể duyệt tài liệu đang chờ xử lý.")
        else:
            document.status = 'approved'
            document.reviewed_by = request.user
            document.reviewed_at = timezone.now()
            document.save()

            # --- CODE GHI LOG MỚI THÊM VÀO ĐÂY ---
        ModerationLog.objects.create(
            moderator=request.user,
            action='approve',
            document=document,
            reason='Tài liệu đạt yêu cầu' # Hoặc để trống tùy bạn
        )
        # -----------------------------------
        messages.success(request, f"Đã duyệt tài liệu '{document.title}'.")
            
    except Document.DoesNotExist:
        messages.error(request, "Không tìm thấy tài liệu.")
        
    # Thay vì trả về Response JSON, chuyển hướng user về lại trang danh sách
    return redirect('pending_documents')


@require_POST
@role_required('moderator', 'admin')
def reject_document(request, id):
    document = get_object_or_404(Document, id=id)

    # Chỉ từ chối tài liệu đang chờ duyệt
    if document.status != 'pending':
        messages.error(
            request,
            'Chỉ có thể từ chối tài liệu đang chờ xử lý.'
        )
        return redirect('pending_documents')

    # Lấy lý do từ form
    reason = request.POST.get('reason', '').strip()

    if not reason:
        messages.error(
            request,
            'Vui lòng nhập lý do từ chối.'
        )
        return redirect('pending_documents')

    # Cập nhật trạng thái
    document.status = 'rejected'
    document.review_note = reason
    document.reviewed_by = request.user
    document.reviewed_at = timezone.now()
    document.save()
    # --- CODE GHI LOG MỚI THÊM VÀO ĐÂY ---
    ModerationLog.objects.create(
            moderator=request.user,
            action='approve',
            document=document,
            reason='Tài liệu đạt yêu cầu' # Hoặc để trống tùy bạn
        )
        # -----------------------------------

    messages.success(
        request,
        f"Đã từ chối tài liệu '{document.title}'."
    )

    return redirect('pending_documents')
    # ==============================================================
# QUẢN LÝ BÁO CÁO (HTML VIEWS)
# ==============================================================
@role_required('student', 'moderator', 'admin')
def report_document(request, id):
    document = get_object_or_404(
        Document,
        id=id,
        status='approved'
    )

    if request.method == 'POST':
        form = ReportForm(request.POST)

        if form.is_valid():
            report = form.save(commit=False)
            report.document = document
            report.user = request.user
            report.save()

            messages.success(
                request,
                'Your report has been submitted successfully.'
            )

            return redirect(
                'document_detail',
                id=document.id
            )
    else:
        form = ReportForm()

    return render(
        request,
        'Blog/report_document.html',
        {
            'form': form,
            'document': document,
        }
    )
@role_required('moderator', 'admin')
def pending_reports(request):

    reports = Report.objects.filter(
        resolved=False
    ).order_by('-created_at')

    return render(
        request,
        'Blog/pending_reports.html',
        {
            'reports': reports
        }
    )
@require_POST  # <--- BẮT BUỘC THÊM DÒNG NÀY ĐỂ CHỐNG LỖ HỔNG BẢO MẬT
@role_required('moderator', 'admin')
def resolve_report(request, id):
    report = get_object_or_404(Report, id=id)

    report.resolved = True
    report.save()
    # --- CODE GHI LOG MỚI THÊM VÀO ĐÂY ---
    ModerationLog.objects.create(
        moderator=request.user,
        action='resolve_report',
        report=report,
        reason='Đã xử lý báo cáo'
    )
    # -----------------------------------

    messages.success(
        request,
        'Report resolved successfully.'
    )

    return redirect('pending_reports')
# ==============================================================
# QUẢN TRỊ ADMIN (HTML VIEWS)
# ==============================================================
@custom_admin_required
def user_management(request):
    user_list = CustomUser.objects.all().order_by('-date_joined')

    search_query = request.GET.get('search', '').strip()
    if search_query:
        user_list = user_list.filter(
            Q(username__icontains=search_query) | 
            Q(email__icontains=search_query)
        )

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
    # CHÚ Ý ĐƯỜNG DẪN RENDER TỚI TEMPLATE NÀY
    return render(request, 'admin_panel/users.html', context)
@custom_admin_required
def change_user_role(request, user_id): # PHẢI LÀ user_id
    if request.method == 'POST':
        user_to_change = get_object_or_404(CustomUser, id=user_id)

        if user_to_change.id == request.user.id:
            messages.error(request, "Bạn không thể tự thay đổi quyền hoặc khóa tài khoản của chính mình!")
            return redirect('user_management')

        if 'toggle_active' in request.POST:
            user_to_change.is_active = not user_to_change.is_active
            user_to_change.save()
            status_msg = "mở khóa" if user_to_change.is_active else "khóa"
            messages.success(request, f"Đã {status_msg} tài khoản {user_to_change.username}.")
            return redirect('user_management')

        elif 'new_role' in request.POST:
            new_role = request.POST.get('new_role')
            valid_roles = ['student', 'moderator', 'admin']
            
            if new_role in valid_roles:
                user_to_change.role = new_role
                user_to_change.save()
                messages.success(request, f"Đã cập nhật quyền cho {user_to_change.username} thành {new_role}.")
            else:
                messages.error(request, "Quyền không hợp lệ.")
            return redirect('user_management')

    return redirect('user_management')
@login_required
def my_uploads(request):
    documents = Document.objects.filter(
        uploaded_by=request.user
    ).order_by('-created_at')

    return render(
        request,
        'Blog/my_uploads.html',
        {'documents': documents}
    )
@login_required
def download_document(request, id):
    document = get_object_or_404(
        Document,
        id=id,
        status='approved'
    )

    if not document.file:
        messages.error(request, 'File not found.')
        return redirect('document_detail', id=document.id)

    Document.objects.filter(id=document.id).update(
        download_count=F('download_count') + 1
    )

    document.refresh_from_db()

    return FileResponse(
        document.file.open('rb'),
        as_attachment=True,
        filename=document.file.name.split('/')[-1]
    )
def preview_document(request, id):
    document = get_object_or_404(
        Document,
        id=id,
        status='approved'
    )

    if not document.file:
        messages.error(request, 'File not found.')
        return redirect('document_detail', id=document.id)

    return FileResponse(
        document.file.open('rb'),
        as_attachment=False,
        content_type='application/pdf'
    )
# Đảm bảo bạn đã import Document và Report từ .models
@role_required('moderator', 'admin')
def moderator_dashboard(request):
    """Trang không gian làm việc và thống kê cho Moderator"""
    pending_docs_count = Document.objects.filter(status='pending').count()
    pending_reports_count = Report.objects.filter(resolved=False).count()
    
    context = {
        'pending_docs_count': pending_docs_count,
        'pending_reports_count': pending_reports_count,
    }
    return render(request, 'Blog/moderator_dashboard.html', context)
@role_required('moderator', 'admin')
def moderation_history(request):
    """Trang xem toàn bộ lịch sử kiểm duyệt của hệ thống (History)"""
    # Lấy toàn bộ log, đã được sắp xếp giảm dần theo created_at nhờ class Meta
    logs = ModerationLog.objects.all()
    
    return render(request, 'Blog/moderation_history.html', {'logs': logs})

@role_required('moderator', 'admin')
def my_activity(request):
    """Trang xem hoạt động cá nhân của Moderator đang đăng nhập (My Activity)"""
    # Chỉ lấy các log do user hiện tại thực hiện
    logs = ModerationLog.objects.filter(moderator=request.user)
    
    return render(request, 'Blog/my_activity.html', {'logs': logs})

@role_required('admin')
def admin_users(request):
    users = CustomUser.objects.all().order_by('-id')
    return render(request, 'admin_panel/users.html', {'users': users})

@role_required('admin')
def admin_documents(request):
    documents = Document.objects.select_related('uploaded_by', 'faculty', 'course').all().order_by('-created_at')
    return render(request, 'admin_panel/documents.html', {'documents': documents})

@role_required('admin')
def admin_faculties(request):
    faculties = Faculty.objects.all()
    return render(request, 'admin_panel/faculties.html', {'faculties': faculties})

@role_required('admin')
def admin_courses(request):
    courses = Course.objects.select_related('faculty').all()
    return render(request, 'admin_panel/courses.html', {'courses': courses})

@role_required('admin')
def admin_reports(request):
    reports = Report.objects.select_related('document', 'user').all().order_by('-created_at')
    return render(request, 'admin_panel/reports.html', {'reports': reports})
