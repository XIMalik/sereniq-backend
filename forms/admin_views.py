import csv
import io

from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Answer, Form, Question, Submission
from .serializers import FormSerializer, QuestionSerializer, SubmissionSerializer
from users.serializers import UserSerializer
from users.permissions import IsAdmin

User = get_user_model()


class AdminDashboardViewSet(viewsets.ViewSet):
    """Admin-only dashboard endpoints for comprehensive data access"""
    permission_classes = [IsAdmin]

    @action(detail=False, methods=['get'])
    def all_forms(self, request):
        """Get all forms with their questions"""
        forms = Form.objects.all()
        serializer = FormSerializer(forms, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def all_submissions(self, request):
        """Get all form submissions"""
        submissions = Submission.objects.select_related('form').prefetch_related(
            Prefetch('answers', queryset=Answer.objects.select_related('question').order_by('question__order', 'id'))
        ).order_by('form__form_type', 'form__type', 'form__title', 'id', 'submitted_at')

        if request.query_params.get('format') == 'csv':
            csv_text = self._generate_submissions_csv(submissions)
            return self._csv_http_response(csv_text)

        serializer = SubmissionSerializer(submissions, many=True)
        return Response(serializer.data)

    def _generate_submissions_csv(self, submissions):
        """Generate CSV text from submissions queryset."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'form_title',
            'submission_id',
            'submitted_at',
            'question_id',
            'question_text',
            'answer_text',
            'score'
        ])

        for submission in submissions:
            answers = list(submission.answers.all())
            for answer in answers:
                writer.writerow([
                    submission.form.title,
                    submission.id,
                    submission.submitted_at.isoformat(),
                    answer.question.id,
                    answer.question.question_text,
                    answer.answer_text,
                    answer.score
                ])

        return output.getvalue()

    def _csv_http_response(self, csv_text, filename='all_submissions.csv'):
        """Generate HttpResponse for CSV download."""
        response = HttpResponse(csv_text, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    def _export_submissions_to_csv(self, submissions):
        csv_text = self._generate_submissions_csv(submissions)
        return self._csv_http_response(csv_text)

    @action(detail=False, methods=['post'])
    def send_submissions_report(self, request):
        """Generate submissions CSV and email it to abdulmalikawesu@gmail.com."""
        try:
            from mailapp.email_service import EmailService

            submissions = Submission.objects.select_related('form').prefetch_related(
                Prefetch('answers', queryset=Answer.objects.select_related('question').order_by('question__order', 'id'))
            ).order_by('form__form_type', 'form__type', 'form__title', 'id', 'submitted_at')

            csv_text = self._generate_submissions_csv(submissions)
            email_service = EmailService()
            email_service.send_submissions_csv_report(csv_text)

            return Response({
                'status': 'success',
                'message': 'Submissions CSV report generated and sent to abdulmalikawesu@gmail.com'
            })

        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Failed to generate and send report: {str(e)}'
            }, status=500)

    @action(detail=False, methods=['get'])
    def all_questions(self, request):
        """Get all questions across all forms"""
        questions = Question.objects.all()
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def all_users(self, request):
        """Get all registered users with their roles"""
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get dashboard statistics"""
        return Response({
            'total_users': User.objects.count(),
            'total_forms': Form.objects.count(),
            'total_submissions': Submission.objects.count(),
            'total_questions': Question.objects.count(),
            'users_by_role': {
                'admin': User.objects.filter(role='admin').count(),
                'staff': User.objects.filter(role='staff').count(),
                'team_member': User.objects.filter(role='team_member').count(),
            },
            'forms_by_type': {
                'assessment': Form.objects.filter(form_type='assessment').count(),
                'survey': Form.objects.filter(form_type='survey').count(),
                'feedback': Form.objects.filter(form_type='feedback').count(),
            }
        })
