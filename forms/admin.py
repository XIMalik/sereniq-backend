from django import forms as django_forms
from django.contrib import admin, messages
from django.db.models import Count
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe
from .models import (
    Form, Question, QuestionOption, Submission, Answer, AccessKey, Organisation, AssessmentCampaign,
)


class LockedFormInlineMixin:
    """Questions and options of an EFIOVA form with submissions are read-only."""

    def _locked(self, obj):
        return obj is not None and obj.is_locked

    def has_add_permission(self, request, obj=None):
        return not self._locked(obj) and super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return not self._locked(obj) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return not self._locked(obj) and super().has_delete_permission(request, obj)


class QuestionInline(LockedFormInlineMixin, admin.TabularInline):
    model = Question
    extra = 1
    fields = ['item_number', 'item_code', 'question_text', 'question_type', 'required', 'order', 'dimension', 'construct_key', 'polarity']


class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 1
    fields = ['value', 'score', 'numeric_value', 'is_not_applicable']

    def _locked(self, obj):
        # `obj` here is the Question being edited
        return obj is not None and obj.form.is_locked

    def has_add_permission(self, request, obj=None):
        return not self._locked(obj) and super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return not self._locked(obj) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return not self._locked(obj) and super().has_delete_permission(request, obj)


@admin.register(Form)
class FormAdmin(admin.ModelAdmin):
    list_display = ['title', 'instrument_code', 'version', 'form_type', 'type', 'order', 'created_by', 'created_at']
    list_filter = ['form_type', 'type', 'instrument_code', 'created_at']
    search_fields = ['title', 'description']
    list_editable = ['order']
    inlines = [QuestionInline]
    
    fieldsets = (
        ('Form Information', {
            'fields': ('title', 'description', 'form_type', 'type', 'code')
        }),
        ('EFIOVA instrument', {
            'fields': ('instrument_code', 'instrument_name', 'version', 'respondent_role', 'scale_type', 'na_option',
                       'is_attributable', 'reference_period', 'instructions', 'privacy_notice'),
            'description': 'Locked once the form has submissions. To change wording or items, create a new Form with a new version.'
        }),
        ('Scoring', {
            'fields': ('min_score', 'max_score')
        }),
        ('Display', {
            'fields': ('order',),
            'description': 'Order within the form type and type combination (e.g., Assessment #1, Assessment #2, etc.)'
        }),
        ('Meta', {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('form_type', 'type', 'order')

    def get_readonly_fields(self, request, obj=None):
        if obj is not None and obj.is_locked:
            return list(Form.FROZEN_FIELDS)
        return super().get_readonly_fields(request, obj)

    def has_delete_permission(self, request, obj=None):
        return not (obj is not None and obj.is_locked) and super().has_delete_permission(request, obj)

    def delete_queryset(self, request, queryset):
        locked = [f for f in queryset if f.is_locked]
        if locked:
            self.message_user(request, f'{len(locked)} form(s) have submissions and were not deleted.', messages.ERROR)
            queryset = queryset.exclude(pk__in=[f.pk for f in locked])
        super().delete_queryset(request, queryset)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'form', 'item_code', 'question_type', 'required', 'order']
    list_filter = ['question_type', 'required', 'form__form_type', 'form']
    search_fields = ['question_text', 'item_code']
    inlines = [QuestionOptionInline]

    def _locked(self, obj):
        return obj is not None and obj.form.is_locked

    def get_readonly_fields(self, request, obj=None):
        if self._locked(obj):
            return [f.name for f in Question._meta.fields]
        return super().get_readonly_fields(request, obj)

    def has_delete_permission(self, request, obj=None):
        return not self._locked(obj) and super().has_delete_permission(request, obj)


@admin.register(QuestionOption)
class QuestionOptionAdmin(admin.ModelAdmin):
    list_display = ['value', 'question', 'numeric_value', 'is_not_applicable', 'score']
    list_filter = ['is_not_applicable', 'question__form']
    search_fields = ['value', 'question__question_text']

    def _locked(self, obj):
        return obj is not None and obj.question.form.is_locked

    def get_readonly_fields(self, request, obj=None):
        if self._locked(obj):
            return [f.name for f in QuestionOption._meta.fields]
        return super().get_readonly_fields(request, obj)

    def has_delete_permission(self, request, obj=None):
        return not self._locked(obj) and super().has_delete_permission(request, obj)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['form', 'campaign', 'group_label', 'submitted_by', 'submitted_at', 'raw_score', 'normalized_score']
    list_filter = ['submitted_at', 'form__form_type', 'form', 'campaign']
    search_fields = ['form__title']
    readonly_fields = ['submitted_at']

    # EFIOVA submissions are anonymous data: never edited, and never deleted (deleting would unlock the form).
    def has_change_permission(self, request, obj=None):
        return not (obj is not None and obj.form.is_efiova) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return not (obj is not None and obj.form.is_efiova) and super().has_delete_permission(request, obj)

    def delete_queryset(self, request, queryset):
        protected = queryset.exclude(form__instrument_code='')
        if protected.exists():
            self.message_user(request, f'{protected.count()} EFIOVA submission(s) were not deleted.', messages.ERROR)
            queryset = queryset.filter(form__instrument_code='')
        super().delete_queryset(request, queryset)


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['submission', 'question', 'answer_text', 'numeric_value', 'is_not_applicable', 'score']
    list_filter = ['submission__form__form_type', 'submission__form']
    search_fields = ['answer_text']

    def has_change_permission(self, request, obj=None):
        return not (obj is not None and obj.submission.form.is_efiova) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return not (obj is not None and obj.submission.form.is_efiova) and super().has_delete_permission(request, obj)


@admin.register(AccessKey)
class AccessKeyAdmin(admin.ModelAdmin):
    list_display = ['key', 'company_name', 'campaign', 'form', 'group_label', 'has_pilot_access', 'has_sub_access',
                    'is_active', 'used', 'created_at', 'expires_at']
    list_filter = ['has_pilot_access', 'has_sub_access', 'is_active', 'is_single_use', 'campaign', 'created_at']
    search_fields = ['company_name', 'key']
    # used_at is deliberately not shown anywhere: it must not be matchable to a submission timestamp.
    readonly_fields = ['key', 'created_at', 'used']

    fieldsets = (
        ('Access Key Information', {
            'fields': ('key', 'company_name')
        }),
        ('Permissions', {
            'fields': ('has_pilot_access', 'has_sub_access', 'is_active')
        }),
        ('EFIOVA campaign', {
            'fields': ('campaign', 'form', 'group_label', 'is_single_use', 'used')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'expires_at')
        }),
    )

    @admin.display(boolean=True, description='Used')
    def used(self, obj):
        return obj.used_at is not None


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']


class AccessKeyInline(admin.TabularInline):
    """Issue keys for a saved campaign. Existing keys are immutable; deactivate them in the AccessKey admin."""
    model = AccessKey
    extra = 0
    fields = ['key', 'form', 'group_label', 'expires_at', 'used']
    readonly_fields = ['key', 'used']

    def has_add_permission(self, request, obj=None):
        return obj is not None and super().has_add_permission(request, obj)  # campaign must exist first

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'form':
            campaign_id = (request.resolver_match.kwargs or {}).get('object_id')
            kwargs['queryset'] = Form.objects.filter(campaigns__pk=campaign_id) if campaign_id else Form.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(boolean=True, description='Used')
    def used(self, obj):
        return obj.used_at is not None


class CampaignAdminForm(django_forms.ModelForm):
    class Meta:
        model = AssessmentCampaign
        fields = '__all__'

    def clean(self):
        cleaned = super().clean()
        tier = cleaned.get('package_tier') or self.instance.package_tier  # read-only once submissions exist
        for form in cleaned.get('forms') or []:
            if form.package_tier != tier:
                self.add_error('forms', f'{form.title} is a {form.package_tier} form but the campaign is {tier}.')
        instance = self.instance
        if instance.pk and instance.submissions.exists():
            if cleaned.get('min_group_size') is not None and cleaned['min_group_size'] < instance.min_group_size:
                self.add_error('min_group_size', 'Cannot be lowered after submissions exist.')
        return cleaned


@admin.register(AssessmentCampaign)
class AssessmentCampaignAdmin(admin.ModelAdmin):
    form = CampaignAdminForm
    list_display = ['name', 'organisation', 'package_tier', 'status', 'start_date', 'end_date', 'min_group_size', 'total_submissions']
    list_filter = ['package_tier', 'status', 'organisation']
    search_fields = ['name', 'organisation__name']
    filter_horizontal = ['forms']
    readonly_fields = ['submission_counts', 'created_at']
    inlines = [AccessKeyInline]

    fieldsets = (
        (None, {'fields': ('organisation', 'name', 'package_tier', 'status', 'forms')}),
        ('Schedule', {'fields': ('start_date', 'end_date')}),
        ('Groups and privacy', {
            'fields': ('group_labels', 'min_group_size'),
            'description': 'Group labels are the only groups respondents can be assigned to. '
                           'Groups smaller than the minimum are suppressed in all reports.',
        }),
        ('Source', {'fields': ('pilot_request', 'created_by'), 'classes': ('collapse',)}),
        ('Submissions', {'fields': ('submission_counts', 'created_at')}),
    )

    @admin.display(description='Submissions')
    def total_submissions(self, obj):
        return obj.submissions.count()

    @admin.display(description='Submissions per form and group (counts only)')
    def submission_counts(self, obj):
        if not obj.pk:
            return '-'
        rows = (obj.submissions.values_list('form__instrument_code', 'form__version', 'group_label')
                .annotate(n=Count('id')).order_by('form__instrument_code', 'group_label'))
        if not rows:
            return 'No submissions yet.'
        return format_html_join(
            mark_safe('<br>'), '{} v{} / {}: {}',
            ((code, version, label or '(unassigned)', n) for code, version, label, n in rows))

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj is not None and obj.submissions.exists():
            fields.append('package_tier')
        return fields

    def save_formset(self, request, form, formset, change):
        if formset.model is not AccessKey:
            return super().save_formset(request, form, formset, change)
        campaign = form.instance
        for key in formset.save(commit=False):
            key.campaign = campaign
            key.is_single_use = True
            key.company_name = campaign.organisation.name
            key.has_pilot_access = campaign.package_tier == 'pilot'
            key.has_sub_access = campaign.package_tier == 'full'
            key.save()
        formset.save_m2m()
