from rest_framework import serializers
from .models import Form, Question, QuestionOption, Submission, Answer


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

    class Meta:
        model = Form
        fields = ['id', 'title', 'description', 'form_type', 'code', 'min_score', 'max_score', 'created_by', 'created_at', 'questions']
        read_only_fields = ['id', 'created_at']


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
