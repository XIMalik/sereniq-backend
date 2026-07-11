from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from forms.models import Form, Question, QuestionOption

User = get_user_model()

QUESTIONS = [
    # Module 1: Psychological Load Index (PLI)
    ('I am expected to manage multiple competing priorities simultaneously.', True),
    ('I frequently think about work-related issues outside working hours.', True),
    ('The mental demands of my role are sustainable.', False),
    ('I often feel mentally overloaded.', True),
    # Module 2: Workforce Stability
    ('My workload is manageable most weeks.', False),
    ('I have the resources necessary to perform effectively.', False),
    # Module 3: Burnout Exposure
    ('I recover adequately from work-related stress.', False),
    ('I feel energized when starting most workdays.', False),
    # Module 4: Leadership Confidence
    ("I trust my immediate manager's decisions.", False),
    ('Leadership communicates clearly during change.', False),
    # Module 5: Retention & Engagement
    ('I see myself working here one year from now.', False),
    ('I would recommend this organization as a workplace.', False),
]


class Command(BaseCommand):
    help = 'Seeds the Workforce Pulse Assessment V2 (pilot + subscription) forms'

    def handle(self, *args, **kwargs):
        admin_user, _ = User.objects.get_or_create(
            email='admin@sereniq.com',
            defaults={'name': 'System Admin', 'role': 'admin', 'is_staff': True}
        )

        self.stdout.write('Seeding Workforce Pulse Assessment V2 forms...')

        self._seed_variant(admin_user, type_='pilot', order=1)
        self._seed_variant(admin_user, type_='sub', order=5)

        self.stdout.write(self.style.SUCCESS(
            'Successfully seeded Workforce Pulse Assessment V2 (pilot + subscription)!'
        ))

    def _seed_variant(self, user, type_, order):
        # Idempotent: remove a prior run of this exact variant before recreating it
        Form.objects.filter(form_type='pulse', type=type_, code='WPA').delete()

        form = Form.objects.create(
            title='Workforce Pulse Assessment™ V2',
            description=(
                'Rapid bi-weekly detection of psychological load, burnout risk, '
                'workforce stability, retention risk, and leadership confidence.'
            ),
            form_type='pulse',
            type=type_,
            code='WPA',
            min_score=12,
            max_score=60,
            order=order,
            created_by=user,
        )

        for idx, (q_text, reverse) in enumerate(QUESTIONS, 1):
            question = Question.objects.create(
                form=form,
                question_text=q_text,
                question_type='likert',
                required=True,
                order=idx,
                reverse_scored=reverse,
                min_value=1,
                max_value=5,
            )
            for score, label in [(1, 'Strongly Disagree'), (2, 'Disagree'), (3, 'Neutral'), (4, 'Agree'), (5, 'Strongly Agree')]:
                QuestionOption.objects.create(question=question, value=label, score=score)

        self.stdout.write(f'  ✓ Created WPA ({type_}) with {len(QUESTIONS)} questions')
