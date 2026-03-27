from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid
from datetime import datetime


class AccessKey(models.Model):
    key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    has_pilot_access = models.BooleanField(default=True)
    has_sub_access = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.company_name or 'Anonymous'} - {str(self.key)[:8]}..."

    def is_valid(self):
        """Check if the access key is valid and not expired"""
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True

    class Meta:
        ordering = ['-created_at']


class Form(models.Model):
    FORM_TYPES = [
        ('assessment', 'Assessment'),
        ('survey', 'Survey'),
        ('feedback', 'Feedback'),
        ('pulse', 'Pulse'),  # Added pulse type
    ]
    
    TYPE_CHOICES = [
        ('pilot', 'Pilot'),
        ('sub', 'Subscription'),
    ]
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    form_type = models.CharField(max_length=20, choices=FORM_TYPES, default='survey')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='sub')
    code = models.CharField(max_length=50, null=True, blank=True)
    min_score = models.IntegerField(default=0)
    max_score = models.IntegerField(default=100)
    order = models.PositiveIntegerField(default=1, help_text='Display order within form type (1, 2, 3, etc.)')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='forms')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['form_type', 'type', 'order', '-created_at']
        unique_together = ['form_type', 'type', 'order']  # Ensures unique order within each form type and type combination


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