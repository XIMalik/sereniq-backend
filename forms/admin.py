from django.contrib import admin
from .models import Form, Question, QuestionOption, Submission, Answer, AccessKey


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    fields = ['question_text', 'question_type', 'required', 'order']


class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 1


@admin.register(Form)
class FormAdmin(admin.ModelAdmin):
    list_display = ['title', 'form_type', 'type', 'order', 'created_by', 'created_at']
    list_filter = ['form_type', 'type', 'created_at']
    search_fields = ['title', 'description']
    list_editable = ['order']
    inlines = [QuestionInline]
    
    fieldsets = (
        ('Form Information', {
            'fields': ('title', 'description', 'form_type', 'type', 'code')
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


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'form', 'question_type', 'required', 'order']
    list_filter = ['question_type', 'required', 'form__form_type', 'form']
    search_fields = ['question_text']
    list_editable = ['order']
    inlines = [QuestionOptionInline]


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['form', 'submitted_by', 'submitted_at', 'raw_score', 'normalized_score']
    list_filter = ['submitted_at', 'form__form_type', 'form']
    search_fields = ['form__title']
    readonly_fields = ['submitted_at']


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['submission', 'question', 'answer_text', 'score']
    list_filter = ['submission__form__form_type', 'submission__form']
    search_fields = ['answer_text']


@admin.register(AccessKey)
class AccessKeyAdmin(admin.ModelAdmin):
    list_display = ['key', 'company_name', 'has_pilot_access', 'has_sub_access', 'is_active', 'created_at', 'expires_at']
    list_filter = ['has_pilot_access', 'has_sub_access', 'is_active', 'created_at']
    search_fields = ['company_name', 'key']
    readonly_fields = ['key', 'created_at']
    
    fieldsets = (
        ('Access Key Information', {
            'fields': ('key', 'company_name')
        }),
        ('Permissions', {
            'fields': ('has_pilot_access', 'has_sub_access', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'expires_at')
        }),
    )