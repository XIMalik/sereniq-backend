from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FormViewSet, QuestionViewSet, SubmissionViewSet, HealthCheck, AccessKeyViewSet
from .admin_views import AdminDashboardViewSet
from .admin_access_key_views import AccessKeyAdminViewSet

router = DefaultRouter()
router.register(r'forms', FormViewSet, basename='form')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'submissions', SubmissionViewSet, basename='submission')
router.register(r'access-keys', AccessKeyViewSet, basename='access-key')
router.register(r'admin/access-keys', AccessKeyAdminViewSet, basename='admin-access-key')
router.register(r'admin/dashboard', AdminDashboardViewSet, basename='admin-dashboard')

urlpatterns = [
    path('', include(router.urls)),
    path('health/', HealthCheck.as_view(), name='health-check'),
]
