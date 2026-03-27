from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Form, Question, QuestionOption, Submission, AccessKey
from .serializers import (
    FormSerializer, QuestionSerializer, QuestionCreateSerializer,
    SubmissionSerializer, QuestionOptionSerializer, AccessKeySerializer
)
from .permissions import IsAdminOrReadOnly, IsFormCreatorOrAdmin, CanViewSubmissions
from users.permissions import IsAdmin
from .services.scoring_engine import ScoringEngine
from .utils import validate_access_key, get_accessible_forms

class FormViewSet(viewsets.ModelViewSet):
    serializer_class = FormSerializer
    permission_classes = [AllowAny]  # Forms are public

    def get_queryset(self):
        # Get access key from headers
        access_key_string = self.request.headers.get('X-ACCESS-KEY')
        access_key = None
        
        if access_key_string:
            access_key = validate_access_key(access_key_string)
        
        # Get accessible forms based on access key
        access_info = get_accessible_forms(access_key)
        queryset = access_info['forms']
        
        # Add accessibility info to each form for the serializer
        for form in queryset:
            if form.type == 'pilot':
                form._accessible = access_info['has_pilot_access']
            else:  # sub
                form._accessible = access_info['has_sub_access']
        
        # Filter by form type if specified
        form_type = self.request.query_params.get('form_type')
        if form_type:
            queryset = queryset.filter(form_type=form_type)
        
        # Filter by type if specified
        type_filter = self.request.query_params.get('type')
        if type_filter:
            queryset = queryset.filter(type=type_filter)
            
        return queryset.order_by('form_type', 'type', 'order')

    def perform_create(self, serializer):
        # Only authenticated users can create forms
        if self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            from users.models import User
            admin_user = User.objects.filter(role='admin').first()
            serializer.save(created_by=admin_user)

    def get_permissions(self):
        # Only admin can create, update, or delete forms
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return [AllowAny()]

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def by_type(self, request):
        """Get forms filtered by type (pilot/sub) with access key validation"""
        form_type = request.query_params.get('type', 'pilot')
        
        # Get access key from headers
        access_key_string = request.headers.get('X-ACCESS-KEY')
        access_key = None
        
        if access_key_string:
            access_key = validate_access_key(access_key_string)
        
        # Get accessible forms
        access_info = get_accessible_forms(access_key)
        queryset = access_info['forms'].filter(type=form_type).order_by('form_type', 'order')
        
        # Add accessibility info
        for form in queryset:
            if form.type == 'pilot':
                form._accessible = access_info['has_pilot_access']
            else:
                form._accessible = access_info['has_sub_access']
        
        serializer = FormSerializer(queryset, many=True)
        return Response({
            'forms': serializer.data,
            'access_info': {
                'has_pilot_access': access_info['has_pilot_access'],
                'has_sub_access': access_info['has_sub_access'],
                'key_valid': access_key is not None,
                'key_required': True  # Indicate that access key is required
            }
        })

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def validate_key(self, request):
        """Validate an access key"""
        key_string = request.data.get('access_key')
        if not key_string:
            return Response({'error': 'Access key is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        access_key = validate_access_key(key_string)
        if access_key:
            return Response({
                'valid': True,
                'has_pilot_access': access_key.has_pilot_access,
                'has_sub_access': access_key.has_sub_access,
                'company_name': access_key.company_name,
                'expires_at': access_key.expires_at
            })
        else:
            return Response({
                'valid': False,
                'has_pilot_access': False,
                'has_sub_access': False,
                'error': 'Invalid or expired access key'
            })

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

    def get(self, request):
        return Response({'message': 'OK'}, status=status.HTTP_200_OK)


class AccessKeyViewSet(viewsets.ModelViewSet):
    queryset = AccessKey.objects.all()
    serializer_class = AccessKeySerializer
    permission_classes = [IsAdmin]  # Only admin can manage access keys

    @action(detail=False, methods=['post'], permission_classes=[IsAdmin])
    def generate(self, request):
        """Generate a new access key"""
        from .utils import generate_access_key
        
        company_name = request.data.get('company_name')
        has_pilot_access = request.data.get('has_pilot_access', True)
        has_sub_access = request.data.get('has_sub_access', False)
        expires_in_days = request.data.get('expires_in_days')
        
        access_key = generate_access_key(
            company_name=company_name,
            has_pilot_access=has_pilot_access,
            has_sub_access=has_sub_access,
            expires_in_days=expires_in_days
        )
        
        return Response(AccessKeySerializer(access_key).data, status=status.HTTP_201_CREATED)