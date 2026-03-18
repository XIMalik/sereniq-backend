from django.db import models
from django.conf import settings


class Form(models.Model):
    FORM_TYPES = [
        ('assessment', 'Assessment'),
        ('survey', 'Survey'),
        ('feedback', 'Feedback'),
    ]
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    form_type = models.CharField(max_length=20, choices=FORM_TYPES, default='survey')
    code = models.CharField(max_length=50, unique=True, null=True, blank=True)
    min_score = models.IntegerField(default=0)
    max_score = models.IntegerField(default=100)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='forms')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']


class Question(models.Model):
    QUESTION_TYPES = [
        ('text', 'Text'),
        ('long_text', 'Long Text'),
        ('email', 'Email'),
        ('number', 'Number'),
        ('select', 'Select'),
        ('likert', 'Likert Scale'),
    ]

    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    required = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    reverse_scored = models.BooleanField(default=False)
    min_value = models.IntegerField(null=True, blank=True)
    max_value = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.form.title} - {self.question_text[:50]}"

    class Meta:
        ordering = ['order']


class QuestionOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    value = models.CharField(max_length=255)
    score = models.IntegerField(default=0)

    def __str__(self):
        return self.value


class Submission(models.Model):
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name='submissions')
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='submissions')
    submitted_at = models.DateTimeField(auto_now_add=True)
    raw_score = models.FloatField(null=True, blank=True)
    normalized_score = models.FloatField(null=True, blank=True)
    category = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Submission for {self.form.title} at {self.submitted_at}"

    class Meta:
        ordering = ['-submitted_at']


class Answer(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.TextField()
    score = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"Answer to {self.question.question_text[:30]}"
