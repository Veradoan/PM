from rest_framework import serializers

from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.PrimaryKeyRelatedField(read_only=True)
    file_hash = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    ai_summary = serializers.CharField(read_only=True)

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'description', 'file', 'file_hash',
            'faculty', 'course', 'doc_type', 'status', 'review_note',
            'ai_summary', 'download_count', 'created_at', 'uploaded_by',
        ]
        read_only_fields = [
            'id', 'file_hash', 'status', 'review_note', 'ai_summary',
            'download_count', 'created_at', 'uploaded_by',
        ]
