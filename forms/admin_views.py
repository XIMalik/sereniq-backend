from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .models import Form, Question, Submission
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
        submissions = Submission.objects.all()
        serializer = SubmissionSerializer(submissions, many=True)
        return Response(serializer.data)

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
