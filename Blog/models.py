from django.db import models
from django.utils import timezone
from User.models import CustomUser
from django.conf import settings


class Faculty(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Course(models.Model):
    name = models.CharField(max_length=100)
    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.CASCADE,
        related_name='courses'
    )

    def __str__(self):
        return self.name


class Document(models.Model):

    DOCUMENT_TYPE_CHOICES = (
        ('exam', 'Exam'),
        ('lecture_slide', 'Lecture Slide'),
        ('sample_project', 'Sample Project'),
        ('exercise', 'Exercise'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    title = models.CharField(max_length=200)

    description = models.TextField(
        blank=True
    )

    # Tạm cho phép null để chuyển dữ liệu Blog cũ
    file = models.FileField(
        upload_to='documents/',
        null=True,
        blank=True
    )

    # Tạm cho phép null để chuyển dữ liệu Blog cũ
    file_hash = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True
    )

    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents'
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents'
    )

    # Tạm cho phép null để chuyển dữ liệu Blog cũ
    doc_type = models.CharField(
        max_length=30,
        choices=DOCUMENT_TYPE_CHOICES,
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

   
    ai_summary = models.TextField(
        blank=True,
        null=True
    )

    download_count = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        default=timezone.now
    )

    uploaded_by = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='uploaded_documents'
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_documents',
        help_text="Moderator hoặc Admin đã xử lý tài liệu này"
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Thời gian xử lý (duyệt/từ chối)"
    )
    review_note = models.TextField(blank=True, null=True, help_text="Lý do từ chối")

    def __str__(self):
        return self.title


class Rate(models.Model):

    rate = models.IntegerField()

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE
    )

    # Tạm cho phép null để chuyển Rate cũ
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='rates'
    )

    created_at = models.DateTimeField(
        default=timezone.now
    )

    class Meta:
        db_table = "rate"
        unique_together = ('user', 'document')
        

    def __str__(self):
        return str(self.rate)


class Comment(models.Model):

    comment = models.TextField()

    # Tạm cho phép null để chuyển Comment cũ
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='comments'
    )

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE
    )

    level = models.IntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        default=timezone.now
    )

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )

    def __str__(self):
        return self.comment


class Report(models.Model):

    REPORT_TYPE_CHOICES = (
        ('incorrect_content', 'Incorrect Content'),
        ('duplicate_file', 'Duplicate File'),
        ('spam', 'Spam'),
    )

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='reports'
    )

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE
    )

    report_type = models.CharField(
        max_length=30,
        choices=REPORT_TYPE_CHOICES
    )

    description = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        default=timezone.now
    )

    resolved = models.BooleanField(
        default=False
    )

    def __str__(self):
        return f"{self.document.title} - {self.report_type}"
class ModerationLog(models.Model):
    ACTION_CHOICES = (
        ('approve', 'Duyệt tài liệu'),
        ('reject', 'Từ chối tài liệu'),
        ('resolve_report', 'Xử lý báo cáo'),
    )
    
    moderator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    document = models.ForeignKey('Document', on_delete=models.CASCADE, null=True, blank=True)
    report = models.ForeignKey('Report', on_delete=models.CASCADE, null=True, blank=True)
    reason = models.TextField(blank=True, null=True) # Dành cho lý do từ chối
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self):
        return f"{self.moderator.username} - {self.action} - {self.created_at}"