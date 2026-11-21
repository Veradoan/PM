import hashlib
import mimetypes

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Avg, Count, F, Q
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from User.decorators import role_required
from User.models import CustomUser
from User.permissions import IsModeratorOrAdmin

from .decorators import custom_admin_required
from .forms import DocumentForm, ReportForm
from .models import Comment, Course, Document, Faculty, ModerationLog, Rate, Report


def contact(request):
    """Trang liên hệ: hiển thị form và xử lý gửi tin nhắn."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()

        if not name or not email or not subject or not message:
            messages.error(
                request,
                'Please fill in all fields before sending.'
            )
        else:
            full_message = (
                f'New contact message\n'
                f'-------------------\n'
                f'Name:    {name}\n'
                f'Email:   {email}\n'
                f'Subject: {subject}\n\n'
                f'{message}\n'
            )
            try:
                if getattr(settings, 'EMAIL_HOST', None):
                    send_mail(
                        subject=f'[AcademicShare Contact] {subject}',
                        message=full_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[getattr(settings, 'CONTACT_EMAIL', 'admin@acadshare.local')],
                        fail_silently=True,
                    )
            except Exception:
                pass

            messages.success(
                request,
                'Thank you! Your message has been sent. '
                'We will get back to you soon.'
            )
            return redirect('contact')

    return render(request, 'Blog/contact.html')


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


@ensure_csrf_cookie
def document_detail(request, id):
    document = get_object_or_404(
        Document,
        id=id,
        status='approved'
    )

    avg_rate = Rate.objects.filter(
        document=document
    ).aggregate(
        avg=Avg('rate'),
        count=Count('id')
    )

    avg = avg_rate['avg']
    if avg is None:
        avg = 0
    else:
        avg = round(avg, 1)

    rate_count = avg_rate['count'] or 0

    avg_full = int(avg)
    avg_frac = avg - avg_full
    avg_half = 0
    if avg_frac >= 0.75:
        avg_full += 1
    elif avg_frac >= 0.25:
        avg_half = 1

    user_rate = 0
    if request.user.is_authenticated:
        rate_obj = Rate.objects.filter(
            document=document,
            user=request.user
        ).first()
        if rate_obj:
            user_rate = rate_obj.rate

    parent_comments = Comment.objects.filter(
        document=document,
        parent__isnull=True
    ).order_by('-id')

    child_comments = Comment.objects.filter(
        document=document,
        parent__isnull=False
    ).order_by('created_at', 'id')

    replies_by_parent = {}
    for c in child_comments:
        replies_by_parent.setdefault(c.parent_id, []).append(c)

    comment_threads = [
        {
            'parent': p,
            'replies': replies_by_parent.get(p.id, [])
        }
        for p in parent_comments
    ]

    return render(
        request,
        'Blog/blog_detail.html',
        {
            'document': document,
            'avg': avg,
            'avg_full': avg_full,
            'avg_half': avg_half,
            'rate_count': rate_count,
            'user_rate': user_rate,
            'comment': parent_comments,
            'comment_threads': comment_threads,
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

    if keyword:
        documents = documents.filter(
            Q(title__icontains=keyword) |
            Q(description__icontains=keyword)
        )

    if faculty_id:
        documents = documents.filter(faculty_id=faculty_id)

    if course_id:
        documents = documents.filter(course_id=course_id)

    if doc_type:
        documents = documents.filter(doc_type=doc_type)

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
    """Xử lý đánh giá bằng AJAX (không reload trang)."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request'})

    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Vui lòng đăng nhập để đánh giá'})

    document_id = request.POST.get('document_id')
    rate = request.POST.get('rate')

    try:
        rate = int(rate)
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Điểm không hợp lệ'})

    if rate < 1 or rate > 5:
        return JsonResponse({'success': False, 'error': 'Điểm phải từ 1 đến 5'})

    try:
        document = Document.objects.get(id=document_id, status='approved')

        old_rate = Rate.objects.filter(
            document=document,
            user=request.user
        ).first()

        if old_rate:
            saved_rate = old_rate.rate
            message = 'Bạn đã đánh giá tài liệu này rồi, điểm được giữ nguyên.'
        else:
            Rate.objects.create(
                document=document,
                rate=rate,
                user=request.user
            )
            saved_rate = rate
            message = 'Cảm ơn bạn đã đánh giá!'

        avg_rate = Rate.objects.filter(
            document=document
        ).aggregate(
            avg=Avg('rate'),
            count=Count('id')
        )

        return JsonResponse({
            'success': True,
            'message': message,
            'saved_rate': saved_rate,
            'avg': round(avg_rate['avg'] or 0, 1),
            'rate_count': avg_rate['count'] or 0,
        })

    except Document.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Document not found'})


def save_comment(request):
    """Xử lý bình luận bằng AJAX (không reload trang)."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request'})

    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Vui lòng đăng nhập để bình luận.'})

    comment_text = (request.POST.get('comment') or '').strip()
    document_id = request.POST.get('document_id')
    parent_id = request.POST.get('parent_id')

    if not comment_text:
        return JsonResponse({'success': False, 'error': 'Nội dung bình luận không được để trống.'})

    document = get_object_or_404(Document, id=document_id, status='approved')

    level = 0
    parent = None

    if parent_id:
        parent = get_object_or_404(Comment, id=parent_id, document=document)
        if parent.parent_id:
            parent = parent.parent
        level = 1

    new_comment = Comment.objects.create(
        document=document,
        comment=comment_text,
        user=request.user,
        level=level,
        parent=parent
    )

    if request.user.avatar:
        avatar_url = request.user.avatar.url
    else:
        avatar_url = static('global/images/avatar-default.png')

    return JsonResponse({
        'success': True,
        'data': {
            'id': new_comment.id,
            'comment': new_comment.comment,
            'author_name': request.user.username,
            'author_id': request.user.id,
            'avatar': avatar_url,
            'level': new_comment.level,
            'parent_id': parent.id if parent else None,
            'created_at': timezone.localtime(new_comment.created_at).strftime('%H:%M %d/%m/%Y'),
        }
    })


@login_required
def upload_document(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)

        if form.is_valid():
            uploaded_file = request.FILES['file']

            sha256 = hashlib.sha256()
            for chunk in uploaded_file.chunks():
                sha256.update(chunk)
            file_hash = sha256.hexdigest()

            if Document.objects.filter(file_hash=file_hash).exists():
                messages.error(request, 'This document already exists.')
                return render(request, 'Blog/upload_document.html', {'form': form})

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

    return render(request, 'Blog/upload_document.html', {'form': form})


def get_courses(request):
    faculty_id = request.GET.get('faculty_id')
    courses = Course.objects.filter(faculty_id=faculty_id).values('id', 'name')
    return JsonResponse(list(courses), safe=False)


@role_required('moderator', 'admin')
def pending_documents(request):
    """Trang kiểm duyệt tổng quan: Hiển thị thống kê và danh sách chờ duyệt."""
    documents = Document.objects.filter(status='pending').order_by('-created_at')
    pending_docs_count = documents.count()
    pending_reports_count = Report.objects.filter(resolved=False).count()

    context = {
        'documents': documents,
        'pending_docs_count': pending_docs_count,
        'pending_reports_count': pending_reports_count,
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

            ModerationLog.objects.create(
                moderator=request.user,
                action='approve',
                document=document,
                reason='Tài liệu đạt yêu cầu'
            )
            messages.success(request, f"Đã duyệt tài liệu '{document.title}'.")

    except Document.DoesNotExist:
        messages.error(request, "Không tìm thấy tài liệu.")

    return redirect('pending_documents')


@require_POST
@role_required('moderator', 'admin')
def reject_document(request, id):
    document = get_object_or_404(Document, id=id)

    if document.status != 'pending':
        messages.error(request, 'Chỉ có thể từ chối tài liệu đang chờ xử lý.')
        return redirect('pending_documents')

    reason = request.POST.get('reason', '').strip()
    if not reason:
        messages.error(request, 'Vui lòng nhập lý do từ chối.')
        return redirect('pending_documents')

    document.status = 'rejected'
    document.review_note = reason
    document.reviewed_by = request.user
    document.reviewed_at = timezone.now()
    document.save()

    ModerationLog.objects.create(
        moderator=request.user,
        action='reject',
        document=document,
        reason=reason
    )

    messages.success(request, f"Đã từ chối tài liệu '{document.title}'.")
    return redirect('pending_documents')


# ==============================================================
# QUẢN LÝ BÁO CÁO (HTML VIEWS)
# ==============================================================
@role_required('student', 'moderator', 'admin')
def report_document(request, id):
    document = get_object_or_404(Document, id=id, status='approved')

    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.document = document
            report.user = request.user
            report.save()

            messages.success(request, 'Your report has been submitted successfully.')
            return redirect('document_detail', id=document.id)
    else:
        form = ReportForm()

    return render(
        request,
        'Blog/report_document.html',
        {'form': form, 'document': document}
    )


@role_required('moderator', 'admin')
def pending_reports(request):
    reports = Report.objects.filter(resolved=False).order_by('-created_at')
    return render(request, 'Blog/pending_reports.html', {'reports': reports})


@require_POST
@role_required('moderator', 'admin')
def resolve_report(request, id):
    report = get_object_or_404(Report, id=id)

    report.resolved = True
    report.save()

    ModerationLog.objects.create(
        moderator=request.user,
        action='resolve_report',
        report=report,
        reason='Đã xử lý báo cáo'
    )

    messages.success(request, 'Report resolved successfully.')
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
    return render(request, 'admin_panel/users.html', context)


@custom_admin_required
def change_user_role(request, user_id):
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
    return render(request, 'Blog/my_uploads.html', {'documents': documents})


@login_required
def download_document(request, id):
    document = get_object_or_404(Document, id=id, status='approved')

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
    document = get_object_or_404(Document, id=id, status='approved')

    if not document.file:
        messages.error(request, 'File not found.')
        return redirect('document_detail', id=document.id)

    return FileResponse(
        document.file.open('rb'),
        as_attachment=False,
        content_type='application/pdf'
    )


@role_required('moderator', 'admin')
def moderator_dashboard(request):
    """Trang không gian làm việc và thống kê cho Moderator."""
    pending_docs_count = Document.objects.filter(status='pending').count()
    pending_reports_count = Report.objects.filter(resolved=False).count()

    context = {
        'pending_docs_count': pending_docs_count,
        'pending_reports_count': pending_reports_count,
    }
    return render(request, 'Blog/moderator_dashboard.html', context)


@role_required('moderator', 'admin')
def moderation_history(request):
    """Trang xem toàn bộ lịch sử kiểm duyệt của hệ thống (History)."""
    logs = ModerationLog.objects.all()
    return render(request, 'Blog/moderation_history.html', {'logs': logs})


@role_required('moderator', 'admin')
def my_activity(request):
    """Trang xem hoạt động cá nhân của Moderator đang đăng nhập (My Activity)."""
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