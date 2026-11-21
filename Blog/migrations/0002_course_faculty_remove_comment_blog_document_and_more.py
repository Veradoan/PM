from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings


def migrate_old_blog_data(apps, schema_editor):
    """
    Chuyển dữ liệu từ Blog cũ sang Document mới.
    Đồng thời chuyển Comment.blog -> Comment.document
    và Rate.blog -> Rate.document.
    """

    Blog = apps.get_model('Blog', 'Blog')
    Document = apps.get_model('Blog', 'Document')
    Comment = apps.get_model('Blog', 'Comment')
    Rate = apps.get_model('Blog', 'Rate')

    db_alias = schema_editor.connection.alias

    # 1. Chuyển Blog -> Document
    for blog in Blog.objects.using(db_alias).all():

        Document.objects.using(db_alias).create(
            id=blog.id,
            title=blog.title,
            description=blog.description,
            file=None,
            file_hash=None,
            faculty=None,
            course=None,
            doc_type=None,

            # Blog cũ đã được đăng nên xem như đã được duyệt
            status='approved',

            review_note=None,
            ai_summary=None,
            download_count=0,

            created_at=blog.created_at,
            uploaded_by_id=blog.author_id,
        )

    # 2. Chuyển Comment từ Blog cũ sang Document
    for comment in Comment.objects.using(db_alias).all():
        if comment.blog_id is not None:
            comment.document_id = comment.blog_id
            comment.save(
                using=db_alias,
                update_fields=['document']
            )

    # 3. Chuyển Rate từ Blog cũ sang Document
    for rate in Rate.objects.using(db_alias).all():
        if rate.blog_id is not None:
            rate.document_id = rate.blog_id
            rate.save(
                using=db_alias,
                update_fields=['document']
            )


class Migration(migrations.Migration):

    dependencies = [
        ('Blog', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        # ==========================================
        # 1. TẠO FACULTY
        # ==========================================

        migrations.CreateModel(
            name='Faculty',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID'
                    )
                ),
                (
                    'name',
                    models.CharField(max_length=100)
                ),
            ],
        ),

        # ==========================================
        # 2. TẠO COURSE
        # ==========================================

        migrations.CreateModel(
            name='Course',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID'
                    )
                ),
                (
                    'name',
                    models.CharField(max_length=100)
                ),
            ],
        ),

        # ==========================================
        # 3. TẠO DOCUMENT
        # ==========================================

        migrations.CreateModel(
            name='Document',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID'
                    )
                ),

                (
                    'title',
                    models.CharField(max_length=200)
                ),

                (
                    'description',
                    models.TextField(blank=True)
                ),

                (
                    'file',
                    models.FileField(
                        upload_to='documents/',
                        null=True,
                        blank=True
                    )
                ),

                (
                    'file_hash',
                    models.CharField(
                        max_length=64,
                        unique=True,
                        null=True,
                        blank=True
                    )
                ),

                (
                    'doc_type',
                    models.CharField(
                        max_length=30,
                        choices=[
                            ('exam', 'Exam'),
                            ('lecture_slide', 'Lecture Slide'),
                            ('sample_project', 'Sample Project'),
                            ('exercise', 'Exercise'),
                        ],
                        null=True,
                        blank=True
                    )
                ),

                (
                    'status',
                    models.CharField(
                        max_length=20,
                        choices=[
                            ('pending', 'Pending'),
                            ('approved', 'Approved'),
                            ('rejected', 'Rejected'),
                        ],
                        default='pending'
                    )
                ),

                (
                    'review_note',
                    models.TextField(
                        blank=True,
                        null=True
                    )
                ),

                (
                    'ai_summary',
                    models.TextField(
                        blank=True,
                        null=True
                    )
                ),

                (
                    'download_count',
                    models.PositiveIntegerField(
                        default=0
                    )
                ),

                (
                    'created_at',
                    models.DateTimeField(
                        default=django.utils.timezone.now
                    )
                ),

                (
                    'course',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='documents',
                        to='Blog.course'
                    )
                ),

                (
                    'faculty',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='documents',
                        to='Blog.faculty'
                    )
                ),

                (
                    'uploaded_by',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='uploaded_documents',
                        to=settings.AUTH_USER_MODEL
                    )
                ),
            ],
        ),

        # ==========================================
        # 4. COURSE -> FACULTY
        # ==========================================

        migrations.AddField(
            model_name='course',
            name='faculty',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='courses',
                to='Blog.faculty'
            ),
        ),

        # ==========================================
        # 5. COMMENT -> DOCUMENT
        # ==========================================

        migrations.AddField(
            model_name='comment',
            name='document',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='comments',
                to='Blog.document'
            ),
        ),

        # ==========================================
        # 6. RATE -> DOCUMENT
        # ==========================================

        migrations.AddField(
            model_name='rate',
            name='document',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.CASCADE,
                related_name='rates',
                to='Blog.document'
            ),
        ),

        # ==========================================
        # 7. REPORT
        # ==========================================

        migrations.CreateModel(
            name='Report',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID'
                    )
                ),

                (
                    'report_type',
                    models.CharField(
                        max_length=30,
                        choices=[
                            (
                                'incorrect_content',
                                'Incorrect Content'
                            ),
                            (
                                'duplicate_file',
                                'Duplicate File'
                            ),
                            (
                                'spam',
                                'Spam'
                            ),
                        ]
                    )
                ),

                (
                    'description',
                    models.TextField(blank=True)
                ),

                (
                    'created_at',
                    models.DateTimeField(
                        default=django.utils.timezone.now
                    )
                ),

                (
                    'resolved',
                    models.BooleanField(default=False)
                ),

                (
                    'document',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='reports',
                        to='Blog.document'
                    )
                ),

                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL
                    )
                ),
            ],
        ),

        # ==========================================
        # 8. CHUYỂN DỮ LIỆU CŨ
        # ==========================================

        migrations.RunPython(
            migrate_old_blog_data,
            reverse_code=migrations.RunPython.noop
        ),

        # ==========================================
        # 9. SAU KHI ĐÃ CHUYỂN DỮ LIỆU
        #    MỚI XÓA BLOG FK CŨ
        # ==========================================

        migrations.AlterUniqueTogether(
    name='rate',
    unique_together={
        ('user', 'document')
    },
),

migrations.SeparateDatabaseAndState(
    database_operations=[],
    state_operations=[
        migrations.RemoveField(
            model_name='comment',
            name='blog',
        ),
        migrations.RemoveField(
            model_name='rate',
            name='blog',
        ),
        migrations.DeleteModel(
            name='Blog',
        ),
    ],
),    ]