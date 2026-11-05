from django.contrib.auth import get_user_model
from django.test import TestCase

from forms.models import Form, Question
from services.models import Booking, Service
from services.serializers import ServiceSerializer

User = get_user_model()


class UserDeletionTests(TestCase):
    def test_deleting_provider_keeps_services_and_bookings(self):
        provider = User.objects.create_user('p@sereniqhq.com', 'pw', name='P', role='admin')
        service = Service.objects.create(name='S', description='d', duration=1, price=10, provider=provider)
        Booking.objects.create(service=service)
        provider.delete()

        service.refresh_from_db()
        self.assertIsNone(service.provider)
        self.assertEqual(Booking.objects.filter(service=service).count(), 1)
        data = ServiceSerializer(service).data
        self.assertIsNone(data['provider'])
        self.assertIsNone(data['provider_id'])

    def test_deleting_user_keeps_everything_they_touched(self):
        user = User.objects.create_user('u@sereniqhq.com', 'pw', name='U', role='admin')
        form = Form.objects.create(title='F', form_type='survey', created_by=user)
        Question.objects.create(form=form, question_text='Q', question_type='text')
        service = Service.objects.create(name='S', description='d', duration=1, price=10, provider=user)
        Booking.objects.create(service=service, customer=user)
        user.delete()
        self.assertEqual((Form.objects.count(), Question.objects.count(), Service.objects.count(), Booking.objects.count()),
                         (1, 1, 1, 1))
