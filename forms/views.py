from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Form, Question, QuestionOption, Submission
from .serializers import (
    FormSerializer, QuestionSerializer, QuestionCreateSerializer,
    SubmissionSerializer, QuestionOptionSerializer
)
from .permissions import IsAdminOrReadOnly, IsFormCreatorOrAdmin, CanViewSubmissions
from users.permissions import IsAdmin
from .services.scoring_engine import ScoringEngine


class FormViewSet(viewsets.ModelViewSet):
    queryset = Form.objects.all()
    serializer_class = FormSerializer
    permission_classes = [AllowAny]  # Forms are public

    def perform_create(self, serializer):
        # Only authenticated users can create forms
        if self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save(created_by=None)

    def get_permissions(self):
        # Only admin can create, update, or delete forms
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return [AllowAny()]

    @action(detail=True, methods=['get'], permission_classes=[IsAdmin])
    def submissions(self, request, pk=None):
        """Admin only: View all submissions for a form"""
        form = self.get_object()
        submissions = form.submissions.all()
        serializer = SubmissionSerializer(submissions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def submit(self, request, pk=None):
        """Anonymous form submission"""
        form = self.get_object()
        serializer = SubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submission = serializer.save(form=form)
        
        # Calculate score if it's an assessment
        if form.form_type == 'assessment':
            try:
                score_result = ScoringEngine.calculate_score(submission.id)
                return Response({
                    'submission': SubmissionSerializer(submission).data,
                    'score_result': score_result
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({
                    'submission': SubmissionSerializer(submission).data,
                    'error': f'Scoring failed: {str(e)}'
                }, status=status.HTTP_201_CREATED)
        
        return Response(SubmissionSerializer(submission).data, status=status.HTTP_201_CREATED)


class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [AllowAny]  # Questions are public

    def get_permissions(self):
        # Only admin can create, update, or delete questions
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.action == 'create':
            return QuestionCreateSerializer
        return QuestionSerializer

    def create(self, request, *args, **kwargs):
        form_id = request.data.get('form')
        if not form_id:
            return Response({'error': 'form field is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(form_id=form_id)
        return Response(QuestionSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)


class SubmissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    permission_classes = [IsAdmin]  # Only admin can view submissions

    def get_queryset(self):
        # Admin sees all submissions
        return super().get_queryset()
    
    @action(detail=True, methods=['get'], permission_classes=[IsAdmin])
    def results(self, request, pk=None):
        """Admin only: Get detailed scoring results for a submission"""
        submission = self.get_object()
        
        if submission.form.form_type != 'assessment':
            return Response({'error': 'This form is not an assessment'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Recalculate if needed
        if submission.normalized_score is None:
            try:
                score_result = ScoringEngine.calculate_score(submission.id)
            except Exception as e:
                return Response({'error': f'Scoring failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            score_result = {
                'submission_id': submission.id,
                'raw_score': submission.raw_score,
                'normalized_score': submission.normalized_score,
                'category': submission.category,
            }
        
        return Response({
            'submission': SubmissionSerializer(submission).data,
            'score_result': score_result
        })


class HealthCheck(APIView):
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'])
    def ping(self, request):
        return Response({'message': 'OK'}, status=status.HTTP_200_OK)