from django.db import migrations


def drop_legacy_blog_columns(apps, schema_editor):
    """Xóa cột legacy `blog_id` còn sót trong DB thật.

    Migration 0002 đã xóa field `blog` khỏi Rate/Comment bằng
    SeparateDatabaseAndState(database_operations=[]) nên STATE Django
    đã đúng, nhưng DB thật vẫn còn cột `blog_id NOT NULL` + index của nó.
    Hậu quả: mọi INSERT vào table `rate` / `Blog_comment` đều fail
    `NOT NULL constraint failed: rate.blog_id` -> tính năng đánh giá
    không lưu được điểm.

    Fix: xóa index của cột trước (bắt buộc trên SQLite), sau đó DROP COLUMN.
    An toàn vì dữ liệu cũ đã được copy sang `document_id` từ migration 0002.
    """
    connection = schema_editor.connection

    def table_columns(table):
        with connection.cursor() as cursor:
            cursor.execute(f'PRAGMA table_info("{table}")')
            return [row[1] for row in cursor.fetchall()]

    with connection.cursor() as cursor:
        if 'blog_id' in table_columns('rate'):
            cursor.execute('DROP INDEX IF EXISTS "rate_blog_id_1019ae64"')
            cursor.execute('ALTER TABLE "rate" DROP COLUMN "blog_id"')

        if 'blog_id' in table_columns('Blog_comment'):
            cursor.execute('DROP INDEX IF EXISTS "Blog_comment_blog_id_9e9c0c78"')
            cursor.execute('ALTER TABLE "Blog_comment" DROP COLUMN "blog_id"')


def restore_legacy_blog_columns(apps, schema_editor):
    """Reverse: không thể khôi phục dữ liệu đã bỏ, noop cho an toàn."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('Blog', '0002_course_faculty_remove_comment_blog_document_and_more'),
    ]

    operations = [
        migrations.RunPython(drop_legacy_blog_columns, restore_legacy_blog_columns),
    ]
