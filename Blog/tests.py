from django.test import TestCase
from django.urls import reverse

from User.models import CustomUser
from .models import Document, Faculty, Course, Report


class DocumentPermissionTests(TestCase):
    def setUp(self):
        self.student = CustomUser.objects.create_user(
            username='student@example.com',
            email='student@example.com',
            password='TestPass123',
            role='student',
        )
        self.moderator = CustomUser.objects.create_user(
            username='moderator@example.com',
            email='moderator@example.com',
            password='TestPass123',
            role='moderator',
        )
        self.faculty = Faculty.objects.create(name='Computer Science')
        self.course = Course.objects.create(
            name='Software Testing',
            faculty=self.faculty,
        )
        self.document = Document.objects.create(
            title='Testing document',
            description='Test document',
            faculty=self.faculty,
            course=self.course,
            doc_type='exercise',
            status='approved',
            uploaded_by=self.student,
        )

    def test_student_can_report_approved_document(self):
        self.client.force_login(self.student)
        response = self.client.post(
            reverse('report_document', args=[self.document.id]),
            {
                'report_type': 'spam',
                'description': 'Test report',
            },
        )

        self.assertRedirects(
            response,
            reverse('document_detail', args=[self.document.id]),
        )
        self.assertTrue(
            Report.objects.filter(
                document=self.document,
                user=self.student,
            ).exists()
        )

    def test_anonymous_user_cannot_report_document(self):
        response = self.client.get(
            reverse('report_document', args=[self.document.id])
        )

        self.assertRedirects(
            response,
            f'{reverse("login")}?next={reverse("report_document", args=[self.document.id])}',
        )

    def test_moderator_can_open_pending_reports(self):
        self.client.force_login(self.moderator)
        response = self.client.get(reverse('pending_reports'))

        self.assertEqual(response.status_code, 200)
