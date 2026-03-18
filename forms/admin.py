from django.contrib import admin
from .models import Form, Question, QuestionOption, Submission, Answer


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1


class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 1


@admin.register(Form)
class FormAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'description']
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'form', 'question_type', 'required', 'order']
    list_filter = ['question_type', 'required']
    search_fields = ['question_text']
    inlines = [QuestionOptionInline]


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['form', 'submitted_by', 'submitted_at']
    list_filter = ['submitted_at']
    search_fields = ['form__title']


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['submission', 'question', 'answer_text']
    search_fields = ['answer_text']
