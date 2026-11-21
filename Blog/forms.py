from django import forms
from .models import Document, Faculty, Course, Report


class DocumentForm(forms.ModelForm):

    def clean_file(self):
        file = self.cleaned_data.get('file')

        if not file:
            return file

        if file.size > 50 * 1024 * 1024:
            raise forms.ValidationError(
                'File size must not exceed 50MB.'
            )

        allowed_extensions = ['pdf', 'docx', 'pptx']

        file_name = file.name.lower()
        extension = file_name.split('.')[-1]

        if extension not in allowed_extensions:
            raise forms.ValidationError(
                'Only PDF, DOCX and PPTX files are allowed.'
            )

        return file

    class Meta:
        model = Document

        fields = [
            'title',
            'description',
            'faculty',
            'course',
            'doc_type',
            'file',
        ]

        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter document title'
            }),

            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter document description'
            }),

            'faculty': forms.Select(attrs={
                'class': 'form-control'
            }),

            'course': forms.Select(attrs={
                'class': 'form-control'
            }),

            'doc_type': forms.Select(attrs={
                'class': 'form-control'
            }),

            'file': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
        }


class ReportForm(forms.ModelForm):

    class Meta:
        model = Report

        fields = [
            'report_type',
            'description',
        ]

        widgets = {
            'report_type': forms.Select(attrs={
                'class': 'form-control'
            }),

            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Please describe the problem...'
            }),
        }