from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils import timezone
import uuid
from datetime import datetime


class FormLockedError(ValidationError):
    """Raised when an attempt is made to change an EFIOVA form that already has submissions."""


class Organisation(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


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

    INSTRUMENT_CHOICES = [
        ('EPA', 'Operating Conditions Pulse'),
        ('WDAI', 'Work Demand Assessment'),
        ('OCEI', 'Operating Capacity Assessment'),
        ('CRI', 'Operating Culture Risk Assessment'),
        ('CPDA', 'Capacity-Performance Dynamics Assessment'),
        ('EILL', 'Executive Operating System Assessment'),
        ('ESS', 'Workforce Connection Survey'),
    ]

    RESPONDENT_ROLE_CHOICES = [
        ('employee', 'Employee'),
        ('visibility_staff', 'Employees or managers with visibility'),
        ('process_owner', 'Process owner / operations lead'),
        ('executive', 'Executive / senior operating leader'),
        ('invited_employee', 'Invited employee'),
    ]

    SCALE_CHOICES = [
        ('agreement', 'Agreement'),
        ('frequency', 'Frequency'),
    ]

    NA_OPTION_CHOICES = [
        ('none', 'None'),
        ('NE', 'Not enough experience'),
        ('NV', 'Not enough visibility'),
        ('NDV', 'Not enough data/visibility'),
    ]

    # Fields that define what a respondent sees; frozen once an EFIOVA form has submissions.
    FROZEN_FIELDS = [
        'title', 'description', 'type', 'instrument_code', 'instrument_name', 'version',
        'respondent_role', 'reference_period', 'instructions', 'privacy_notice',
        'scale_type', 'na_option', 'is_attributable',
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    form_type = models.CharField(max_length=20, choices=FORM_TYPES, default='survey')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='sub')
    code = models.CharField(max_length=50, null=True, blank=True)
    min_score = models.IntegerField(default=0)
    max_score = models.IntegerField(default=100)
    order = models.PositiveIntegerField(default=1, help_text='Display order within form type (1, 2, 3, etc.)')
    # SET_NULL, not CASCADE: deleting a user must never delete the forms they created.
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='forms')
    created_at = models.DateTimeField(auto_now_add=True)

    # EFIOVA instrument metadata. Package tier is derived from `type` (sub = full), see package_tier.
    instrument_code = models.CharField(max_length=10, choices=INSTRUMENT_CHOICES, blank=True, default='')
    instrument_name = models.CharField(max_length=255, blank=True)
    version = models.CharField(max_length=20, blank=True)
    respondent_role = models.CharField(max_length=20, choices=RESPONDENT_ROLE_CHOICES, blank=True)
    reference_period = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    privacy_notice = models.TextField(blank=True)
    scale_type = models.CharField(max_length=20, choices=SCALE_CHOICES, blank=True)
    na_option = models.CharField(max_length=10, choices=NA_OPTION_CHOICES, default='none')
    is_attributable = models.BooleanField(
        default=False,
        help_text='True where the respondent pool is too small to be anonymous (CPDA, EILL).',
    )

    def __str__(self):
        return self.title

    @property
    def is_efiova(self):
        return bool(self.instrument_code)

    @property
    def package_tier(self):
        return 'full' if self.type == 'sub' else 'pilot'

    def has_submissions(self):
        return self.pk is not None and self.submissions.exists()

    @property
    def is_locked(self):
        """EFIOVA forms with submissions are immutable; changes need a new version."""
        return self.is_efiova and self.has_submissions()

    def save(self, *args, **kwargs):
        if self.pk and self.is_locked:
            original = Form.objects.get(pk=self.pk)
            changed = [f for f in self.FROZEN_FIELDS if getattr(original, f) != getattr(self, f)]
            if changed:
                raise FormLockedError(
                    f'Form "{original}" has submissions; {", ".join(changed)} cannot change. '
                    'Create a new Form with a new version instead.'
                )
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['form_type', 'type', 'order', '-created_at']
        unique_together = ['form_type', 'type', 'order']  # Ensures unique order within each form type and type combination
        constraints = [
            models.UniqueConstraint(
                fields=['instrument_code', 'version', 'type'],
                condition=~models.Q(instrument_code=''),
                name='unique_instrument_version_tier',
            ),
        ]


class Question(models.Model):
    QUESTION_TYPES = [
        ('text', 'Text'),
        ('long_text', 'Long Text'),
        ('email', 'Email'),
        ('number', 'Number'),
        ('select', 'Select'),
        ('likert', 'Likert Scale'),
    ]

    POLARITY_CHOICES = [
        ('positive', 'Positive (agreeing / lower frequency is healthy)'),
        ('negative', 'Negative (higher response means more risk)'),
    ]

    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    required = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    reverse_scored = models.BooleanField(default=False)
    min_value = models.IntegerField(null=True, blank=True)
    max_value = models.IntegerField(null=True, blank=True)

    # EFIOVA item metadata
    item_number = models.PositiveIntegerField(null=True, blank=True)
    item_code = models.CharField(max_length=20, blank=True, help_text='e.g. EPA-F-03 (F = full, P = pilot)')
    dimension = models.SlugField(max_length=50, blank=True)
    construct_key = models.CharField(
        max_length=20, blank=True,
        help_text='Full-version item code shared by a pilot item and its full equivalent.',
    )
    polarity = models.CharField(max_length=10, choices=POLARITY_CHOICES, blank=True)

    def __str__(self):
        return f"{self.form.title} - {self.question_text[:50]}"

    def save(self, *args, **kwargs):
        _assert_form_unlocked(self.form)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['order']


class QuestionOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    value = models.CharField(max_length=255)
    score = models.IntegerField(default=0)
    # Numeric value 1-5 for EFIOVA scales; NULL for the "not applicable" option.
    numeric_value = models.PositiveSmallIntegerField(null=True, blank=True)
    is_not_applicable = models.BooleanField(default=False)

    def __str__(self):
        return self.value

    def save(self, *args, **kwargs):
        _assert_form_unlocked(self.question.form)
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(numeric_value__isnull=True) | models.Q(numeric_value__gte=1, numeric_value__lte=5),
                name='option_numeric_value_1_5',
            ),
            models.CheckConstraint(
                condition=~models.Q(is_not_applicable=True, numeric_value__isnull=False),
                name='option_na_has_no_numeric_value',
            ),
        ]


class AssessmentCampaign(models.Model):
    """One run of EFIOVA instruments for one client organisation."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed'),
    ]
    TIER_CHOICES = [
        ('full', 'Full'),
        ('pilot', 'Pilot'),
    ]

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name='campaigns')
    name = models.CharField(max_length=255)
    package_tier = models.CharField(max_length=10, choices=TIER_CHOICES)
    forms = models.ManyToManyField(Form, related_name='campaigns', blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    min_group_size = models.PositiveIntegerField(default=5, validators=[MinValueValidator(2)])
    group_labels = models.JSONField(
        default=list, blank=True,
        help_text='Allowed team / function / process-group labels for this campaign.',
    )
    pilot_request = models.ForeignKey(
        'services.PilotRequest', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assessment_campaigns',
        help_text='Optional reference to the originating pilot request (read-only use).',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assessment_campaigns',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.organisation} - {self.name}"

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({'end_date': 'End date cannot be before start date.'})
        if not isinstance(self.group_labels, list) or not all(isinstance(g, str) and g.strip() for g in self.group_labels):
            raise ValidationError({'group_labels': 'Must be a list of non-empty strings.'})
        if len(set(self.group_labels)) != len(self.group_labels):
            raise ValidationError({'group_labels': 'Group labels must be unique.'})

    def is_open(self, today=None):
        """Whether respondents may currently submit against this campaign."""
        if self.status != 'active':
            return False
        today = today or timezone.localdate()
        if self.start_date and today < self.start_date:
            return False
        if self.end_date and today > self.end_date:
            return False
        return True

    class Meta:
        ordering = ['-created_at']


class AccessKey(models.Model):
    key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    has_pilot_access = models.BooleanField(default=True)
    has_sub_access = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)

    # EFIOVA campaign keys. All null/blank/False for legacy keys.
    campaign = models.ForeignKey(AssessmentCampaign, on_delete=models.CASCADE, null=True, blank=True, related_name='access_keys')
    form = models.ForeignKey(Form, on_delete=models.CASCADE, null=True, blank=True, related_name='access_keys')
    group_label = models.CharField(max_length=100, blank=True)
    is_single_use = models.BooleanField(default=False)
    # Deliberately never linked to a Submission. For non-attributable forms it is set to midnight
    # of the day of use so it cannot be matched to a submission timestamp.
    used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.company_name or 'Anonymous'} - {str(self.key)[:8]}..."

    def clean(self):
        super().clean()
        if self.campaign_id:
            if not self.form_id:
                raise ValidationError({'form': 'Campaign keys must be tied to a form.'})
            if not self.campaign.forms.filter(pk=self.form_id).exists():
                raise ValidationError({'form': 'This form is not part of the campaign.'})
            if self.group_label and self.group_label not in self.campaign.group_labels:
                raise ValidationError({'group_label': 'Not one of the campaign\'s group labels.'})

    def is_valid(self):
        """Check if the access key is valid and not expired"""
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        if self.is_single_use and self.used_at:
            return False
        return True

    class Meta:
        ordering = ['-created_at']


class Submission(models.Model):
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name='submissions')
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='submissions')
    submitted_at = models.DateTimeField(auto_now_add=True)
    raw_score = models.FloatField(null=True, blank=True)
    normalized_score = models.FloatField(null=True, blank=True)
    category = models.CharField(max_length=100, blank=True)

    # EFIOVA fields. There is intentionally no access-key, IP or user-agent field on this model.
    campaign = models.ForeignKey(AssessmentCampaign, on_delete=models.PROTECT, null=True, blank=True, related_name='submissions')
    group_label = models.CharField(max_length=100, blank=True)
    process_name = models.CharField(max_length=255, blank=True, help_text='CPDA only.')
    consent_acknowledged = models.BooleanField(default=False)

    def __str__(self):
        return f"Submission for {self.form.title} at {self.submitted_at}"

    @property
    def is_anonymous_instrument(self):
        return self.form.is_efiova and not self.form.is_attributable

    def clean(self):
        super().clean()
        if self.process_name and self.form.instrument_code != 'CPDA':
            raise ValidationError({'process_name': 'Only CPDA submissions carry a process name.'})
        if self.campaign_id:
            if self.group_label and self.group_label not in self.campaign.group_labels:
                raise ValidationError({'group_label': 'Not one of the campaign\'s group labels.'})
            if not self.campaign.forms.filter(pk=self.form_id).exists():
                raise ValidationError({'form': 'This form is not part of the campaign.'})

    def save(self, *args, **kwargs):
        anonymous = self.is_anonymous_instrument
        if anonymous:
            self.submitted_by = None
        super().save(*args, **kwargs)
        if anonymous and self.submitted_at:
            # Coarsen to the day so a submission cannot be matched to an access key by timing.
            day = self.submitted_at.replace(hour=0, minute=0, second=0, microsecond=0)
            if self.submitted_at != day:
                type(self).objects.filter(pk=self.pk).update(submitted_at=day)
                self.submitted_at = day

    class Meta:
        ordering = ['-submitted_at']


class Answer(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.TextField()
    score = models.FloatField(null=True, blank=True)
    # Raw numeric response (1-5) or the N/A flag; EFIOVA scoring reads only these, never answer_text.
    numeric_value = models.PositiveSmallIntegerField(null=True, blank=True)
    is_not_applicable = models.BooleanField(default=False)

    def __str__(self):
        return f"Answer to {self.question.question_text[:30]}"

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(numeric_value__isnull=True) | models.Q(numeric_value__gte=1, numeric_value__lte=5),
                name='answer_numeric_value_1_5',
            ),
            models.CheckConstraint(
                condition=~models.Q(is_not_applicable=True, numeric_value__isnull=False),
                name='answer_na_has_no_numeric_value',
            ),
        ]


def _assert_form_unlocked(form):
    if form.is_locked:
        raise FormLockedError(
            f'Form "{form}" has submissions; its questions and options cannot change. '
            'Create a new Form with a new version instead.'
        )


@receiver(pre_delete, sender=Form)
def _block_locked_form_delete(sender, instance, **kwargs):
    _assert_form_unlocked(instance)


@receiver(pre_delete, sender=Question)
def _block_locked_question_delete(sender, instance, **kwargs):
    _assert_form_unlocked(instance.form)


@receiver(pre_delete, sender=QuestionOption)
def _block_locked_option_delete(sender, instance, **kwargs):
    _assert_form_unlocked(instance.question.form)
