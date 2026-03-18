from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FormViewSet, QuestionViewSet, SubmissionViewSet
from .admin_views import AdminDashboardViewSet

router = DefaultRouter()
router.register(r'forms', FormViewSet, basename='form')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'submissions', SubmissionViewSet, basename='submission')
router.register(r'admin/dashboard', AdminDashboardViewSet, basename='admin-dashboard')

urlpatterns = [
    path('', include(router.urls)),
]
