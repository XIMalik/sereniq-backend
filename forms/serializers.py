from rest_framework import serializers
from .models import Form, Question, QuestionOption, Submission, Answer, AccessKey


class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ['id', 'value', 'score']


class QuestionSerializer(serializers.ModelSerializer):
    options = QuestionOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'question_text', 'question_type', 'required', 'order', 'reverse_scored', 'min_value', 'max_value', 'options']


class FormSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)
    accessible = serializers.SerializerMethodField()

    class Meta:
        model = Form
        fields = ['id', 'title', 'description', 'form_type', 'type', 'code', 'min_score', 'max_score', 'order', 'created_by', 'created_at', 'questions', 'accessible']
        read_only_fields = ['id', 'created_at']
    
    def get_accessible(self, obj):
        # This will be set by the view based on access key
        return getattr(obj, '_accessible', True)


class AnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.question_text', read_only=True)

    class Meta:
        model = Answer
        fields = ['id', 'question', 'question_text', 'answer_text', 'score']


class SubmissionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True)
    form_title = serializers.CharField(source='form.title', read_only=True)

    class Meta:
        model = Submission
        fields = ['id', 'form', 'form_title', 'submitted_at', 'raw_score', 'normalized_score', 'category', 'answers']
        read_only_fields = ['id', 'form', 'submitted_at', 'raw_score', 'normalized_score', 'category']

    def create(self, validated_data):
        answers_data = validated_data.pop('answers')
        submission = Submission.objects.create(**validated_data)
        for answer_data in answers_data:
            Answer.objects.create(submission=submission, **answer_data)
        return submission


class QuestionCreateSerializer(serializers.ModelSerializer):
    options = QuestionOptionSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = ['question_text', 'question_type', 'required', 'order', 'options']

    def create(self, validated_data):
        options_data = validated_data.pop('options', [])
        question = Question.objects.create(**validated_data)
        for option_data in options_data:
            QuestionOption.objects.create(question=question, **option_data)
        return question


class AccessKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessKey
        fields = ['key', 'has_pilot_access', 'has_sub_access', 'is_active', 'company_name', 'created_at', 'expires_at']
        read_only_fields = ['key', 'created_at']


class AccessKeyAdminSerializer(serializers.ModelSerializer):
    is_expired = serializers.SerializerMethodField()
    expires_in_days = serializers.SerializerMethodField()
    access_level = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = AccessKey
        fields = [
            'id', 'key', 'company_name', 'has_pilot_access', 'has_sub_access', 
            'is_active', 'created_at', 'expires_at', 'is_expired', 
            'expires_in_days', 'access_level', 'status'
        ]
        read_only_fields = ['id', 'key', 'created_at', 'is_expired', 'expires_in_days', 'access_level', 'status']
    
    def get_is_expired(self, obj):
        if not obj.expires_at:
            return False
        from django.utils import timezone
        return obj.expires_at < timezone.now()
    
    def get_expires_in_days(self, obj):
        if not obj.expires_at:
            return None
        from django.utils import timezone
        delta = obj.expires_at - timezone.now()
        return delta.days if delta.days >= 0 else 0
    
    def get_access_level(self, obj):
        if obj.has_sub_access:
            return 'Full Access'
        elif obj.has_pilot_access:
            return 'Pilot Only'
        else:
            return 'No Access'
    
    def get_status(self, obj):
        if not obj.is_active:
            return 'Inactive'
        elif self.get_is_expired(obj):
            return 'Expired'
        elif obj.expires_at and self.get_expires_in_days(obj) <= 7:
            return 'Expiring Soon'
        else:
            return 'Active'