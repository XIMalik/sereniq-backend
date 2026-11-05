from rest_framework import serializers
from .models import Form, Question, QuestionOption, Submission, Answer, AccessKey, Organisation, AssessmentCampaign
from services.models import PilotRequest


class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ['id', 'value', 'score', 'numeric_value', 'is_not_applicable']


class QuestionSerializer(serializers.ModelSerializer):
    options = QuestionOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'question_text', 'question_type', 'required', 'order', 'reverse_scored', 'min_value', 'max_value',
                  'item_number', 'item_code', 'dimension', 'construct_key', 'polarity', 'options']


class FormSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)
    accessible = serializers.SerializerMethodField()
    package_tier = serializers.CharField(read_only=True)
    is_locked = serializers.BooleanField(read_only=True)

    class Meta:
        model = Form
        fields = ['id', 'title', 'description', 'form_type', 'type', 'code', 'min_score', 'max_score', 'order', 'created_by', 'created_at', 'questions', 'accessible',
                  'instrument_code', 'instrument_name', 'version', 'package_tier', 'respondent_role', 'reference_period',
                  'instructions', 'privacy_notice', 'scale_type', 'na_option', 'is_attributable', 'is_locked']
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
        fields = ['question_text', 'question_type', 'required', 'order', 'reverse_scored', 'min_value', 'max_value',
                  'item_number', 'item_code', 'dimension', 'construct_key', 'polarity', 'options']

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


class OrganisationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organisation
        fields = ['id', 'name', 'created_at']
        read_only_fields = ['id', 'created_at']


class AssessmentCampaignSerializer(serializers.ModelSerializer):
    organisation_name = serializers.CharField(source='organisation.name', read_only=True)
    forms = serializers.PrimaryKeyRelatedField(many=True, queryset=Form.objects.exclude(instrument_code=''), required=False)
    pilot_request = serializers.PrimaryKeyRelatedField(queryset=PilotRequest.objects.all(), required=False, allow_null=True)
    submission_count = serializers.SerializerMethodField()
    is_open = serializers.SerializerMethodField()

    class Meta:
        model = AssessmentCampaign
        fields = ['id', 'organisation', 'organisation_name', 'name', 'package_tier', 'forms', 'start_date', 'end_date',
                  'status', 'min_group_size', 'group_labels', 'pilot_request', 'submission_count', 'is_open', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_submission_count(self, obj):
        return obj.submissions.count()

    def get_is_open(self, obj):
        return obj.is_open()

    def validate_min_group_size(self, value):
        if value < 2:
            raise serializers.ValidationError('Must be at least 2.')
        return value

    def validate(self, attrs):
        instance = self.instance
        tier = attrs.get('package_tier', instance.package_tier if instance else None)
        start = attrs.get('start_date', instance.start_date if instance else None)
        end = attrs.get('end_date', instance.end_date if instance else None)
        if start and end and end < start:
            raise serializers.ValidationError({'end_date': 'End date cannot be before start date.'})

        if 'group_labels' in attrs:
            labels = [str(g).strip() for g in attrs['group_labels']]
            if not all(labels):
                raise serializers.ValidationError({'group_labels': 'Labels must be non-empty strings.'})
            if len(set(labels)) != len(labels):
                raise serializers.ValidationError({'group_labels': 'Labels must be unique.'})
            attrs['group_labels'] = labels

        for form in attrs.get('forms', []):
            if form.package_tier != tier:
                raise serializers.ValidationError(
                    {'forms': f'{form.title} is a {form.package_tier} form but the campaign is {tier}.'})

        if instance and instance.submissions.exists():
            # Once data exists, nothing may weaken or orphan it.
            if tier != instance.package_tier:
                raise serializers.ValidationError({'package_tier': 'Cannot change after submissions exist.'})
            if attrs.get('min_group_size', instance.min_group_size) < instance.min_group_size:
                raise serializers.ValidationError(
                    {'min_group_size': 'Cannot be lowered after submissions exist; it would expose suppressed groups.'})
            if 'forms' in attrs:
                used = set(instance.submissions.values_list('form_id', flat=True))
                if used - {f.id for f in attrs['forms']}:
                    raise serializers.ValidationError({'forms': 'Cannot remove a form that has submissions.'})
            if 'group_labels' in attrs:
                used = set(instance.submissions.exclude(group_label='').values_list('group_label', flat=True))
                if used - set(attrs['group_labels']):
                    raise serializers.ValidationError({'group_labels': 'Cannot remove a label that has submissions.'})
        return attrs


class BulkAccessKeySerializer(serializers.Serializer):
    form = serializers.PrimaryKeyRelatedField(queryset=Form.objects.exclude(instrument_code=''))
    count = serializers.IntegerField(min_value=1, max_value=500)
    group_label = serializers.CharField(required=False, allow_blank=True, default='')
    expires_in_days = serializers.IntegerField(required=False, min_value=1, allow_null=True, default=None)

    def validate(self, attrs):
        campaign = self.context['campaign']
        if not campaign.forms.filter(pk=attrs['form'].pk).exists():
            raise serializers.ValidationError({'form': 'This form is not part of the campaign.'})
        if attrs['group_label'] and attrs['group_label'] not in campaign.group_labels:
            raise serializers.ValidationError({'group_label': 'Not one of the campaign\'s group labels.'})
        return attrs
