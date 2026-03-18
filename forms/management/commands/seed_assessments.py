from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from forms.models import Form, Question, QuestionOption

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds all assessment forms and questions into the database'

    def handle(self, *args, **kwargs):
        # Get or create admin user for form creation
        admin_user, _ = User.objects.get_or_create(
            email='admin@sereniq.com',
            defaults={'name': 'System Admin', 'role': 'admin', 'is_staff': True}
        )
        if not admin_user.password:
            admin_user.set_password('admin123')
            admin_user.save()

        self.stdout.write('Seeding assessment forms...')

        # Clear existing assessment forms
        Form.objects.filter(form_type='assessment').delete()

        # Seed all forms
        self.seed_pli(admin_user)
        self.seed_ess(admin_user)
        self.seed_cri(admin_user)
        self.seed_pulses(admin_user)
        self.seed_eill(admin_user)

        self.stdout.write(self.style.SUCCESS('Successfully seeded all assessment forms!'))

    def seed_pli(self, user):
        """Psychological Load Index"""
        form = Form.objects.create(
            title='Psychological Load Index (PLI)',
            description='Measures workforce strain, fatigue accumulation, and recovery breakdown.',
            form_type='assessment',
            code='PLI',
            min_score=0,
            max_score=72,
            created_by=user
        )

        questions = [
            # Workload & Pressure Load
            'My workload feels heavier than I can reasonably sustain.',
            'I often feel like I am working in constant urgency.',
            'I am expected to deliver more than my capacity allows.',
            'My work pace feels relentless rather than healthy.',
            # Cognitive & Mental Fatigue
            'I feel mentally drained before the workday ends.',
            'I struggle to concentrate because of exhaustion.',
            'I feel like my brain never fully switches off from work.',
            'I feel decision-fatigued even with small tasks.',
            # Emotional Depletion
            'I feel emotionally worn out by my work demands.',
            'I feel close to burnout even if I continue performing.',
            'I feel like I am operating on pressure rather than energy.',
            'I feel less resilient than I used to.',
            # Recovery Breakdown
            'Rest does not restore me the way it used to.',
            'I do not feel I have enough recovery time between workdays.',
            'My sleep quality has declined because of work stress.',
            'I often start the week already exhausted.',
            # Burnout Masking Indicators
            'I appear productive externally but internally I feel depleted.',
            'I worry that my performance is becoming unsustainable.',
        ]

        for idx, q_text in enumerate(questions, 1):
            question = Question.objects.create(
                form=form,
                question_text=q_text,
                question_type='likert',
                required=True,
                order=idx,
                reverse_scored=False,
                min_value=0,
                max_value=4
            )
            # Create options
            for score, label in [(0, 'Not at all'), (1, 'Slightly'), (2, 'Moderately'), (3, 'Very'), (4, 'Extremely')]:
                QuestionOption.objects.create(question=question, value=label, score=score)

        self.stdout.write(f'  ✓ Created PLI with {len(questions)} questions')

    def seed_ess(self, user):
        """Engagement & Sentiment Survey"""
        form = Form.objects.create(
            title='Engagement & Sentiment Survey (ESS)',
            description='Measures employee engagement, motivation, and organizational sentiment.',
            form_type='assessment',
            code='ESS',
            min_score=15,
            max_score=75,
            created_by=user
        )

        questions_data = [
            # Meaning & Motivation
            ('I feel motivated to contribute my best work.', False),
            ('My work feels meaningful and valuable.', False),
            ('I feel proud to be part of this organization.', False),
            # Trust & Leadership Confidence
            ('I trust leadership to make responsible decisions.', False),
            ('Communication from leadership feels clear and reliable.', False),
            ('I feel leadership understands workforce realities.', False),
            # Belonging & Team Stability
            ('I feel connected to my team.', False),
            ('I feel supported by colleagues in my work.', False),
            ('I feel respected in this organization.', False),
            # Engagement Volatility
            ('My engagement has been declining recently.', True),  # Reverse
            ('I often feel emotionally checked out.', True),  # Reverse
            ('I feel energized by my work environment.', False),
            # Retention & Advocacy
            ('I would recommend this organization as a workplace.', False),
            ('I see myself working here long term.', False),
            ('I feel morale is stable across the workforce.', False),
        ]

        for idx, (q_text, reverse) in enumerate(questions_data, 1):
            question = Question.objects.create(
                form=form,
                question_text=q_text,
                question_type='likert',
                required=True,
                order=idx,
                reverse_scored=reverse,
                min_value=1,
                max_value=5
            )
            for score, label in [(1, 'Strongly Disagree'), (2, 'Disagree'), (3, 'Neutral'), (4, 'Agree'), (5, 'Strongly Agree')]:
                QuestionOption.objects.create(question=question, value=label, score=score)

        self.stdout.write(f'  ✓ Created ESS with {len(questions_data)} questions')

    def seed_cri(self, user):
        """Culture Risk Index"""
        form = Form.objects.create(
            title='Culture Risk Index (CRI)',
            description='Assesses psychological safety, trust, and cultural health indicators.',
            form_type='assessment',
            code='CRI',
            min_score=20,
            max_score=100,
            created_by=user
        )

        questions_data = [
            # Psychological Safety
            ('I feel safe speaking honestly at work.', False),
            ('People can raise concerns without fear.', False),
            ('Mistakes are treated as learning not punishment.', False),
            ('Difficult conversations are handled respectfully.', False),
            # Silence & Fear Patterns
            ('People often stay silent to avoid consequences.', False),
            ('Speaking up can negatively affect your standing.', False),
            ('Employees avoid reporting issues openly.', False),
            ('Fear influences behavior here.', False),
            # Toxicity Normalization
            ('Stress and overload are treated as normal.', False),
            ('Unhealthy behavior is tolerated if performance is high.', False),
            ('Conflict is often unresolved.', False),
            ('There are unspoken tensions in teams.', False),
            # Trust & Integrity
            ('Leadership behavior feels consistent and fair.', False),
            ('Employees trust management intentions.', False),
            ('People feel psychologically protected here.', False),
            # Escalation Risk
            ('Problems are addressed early not ignored.', False),
            ('Workplace culture feels fragile right now.', True),  # Reverse
            ('Attrition risk is rising due to culture strain.', True),  # Reverse
            ('People feel emotionally unsafe in this environment.', True),  # Reverse
            ('This culture could become a reputational risk if ignored.', True),  # Reverse
        ]

        for idx, (q_text, reverse) in enumerate(questions_data, 1):
            question = Question.objects.create(
                form=form,
                question_text=q_text,
                question_type='likert',
                required=True,
                order=idx,
                reverse_scored=reverse,
                min_value=1,
                max_value=5
            )
            for score, label in [(1, 'Strongly Disagree'), (2, 'Disagree'), (3, 'Neutral'), (4, 'Agree'), (5, 'Strongly Agree')]:
                QuestionOption.objects.create(question=question, value=label, score=score)

        self.stdout.write(f'  ✓ Created CRI with {len(questions_data)} questions')

    def seed_pulses(self, user):
        """Weekly Micro-Pulses"""
        pulses = [
            ('Monday Load Pulse', 'PULSE_MONDAY', [
                ('My workload feels sustainable this week.', False),
                ('I feel mentally clear enough to perform well.', False),
                ('I have recovered adequately since last week.', False),
                ('My pace feels healthy not frantic.', False),
                ('I feel close to exhaustion.', True),  # Reverse
            ]),
            ('Wednesday Safety Pulse', 'PULSE_WEDNESDAY', [
                ('I feel safe speaking honestly.', False),
                ('Issues are handled fairly.', False),
                ('People can raise concerns without fear.', False),
                ('Leadership listens when problems are raised.', False),
                ('I prefer to stay silent even when something feels wrong.', True),  # Reverse
            ]),
            ('Friday Engagement Pulse', 'PULSE_FRIDAY', [
                ('I felt motivated this week.', False),
                ('My work felt meaningful.', False),
                ('I felt connected to my team.', False),
                ('I would recommend this workplace.', False),
                ('I felt emotionally checked out.', True),  # Reverse
            ]),
        ]

        for title, code, questions_data in pulses:
            form = Form.objects.create(
                title=title,
                description=f'Weekly pulse check: {title.split()[0]}',
                form_type='assessment',
                code=code,
                min_score=5,
                max_score=25,
                created_by=user
            )

            for idx, (q_text, reverse) in enumerate(questions_data, 1):
                question = Question.objects.create(
                    form=form,
                    question_text=q_text,
                    question_type='likert',
                    required=True,
                    order=idx,
                    reverse_scored=reverse,
                    min_value=1,
                    max_value=5
                )
                for score, label in [(1, 'Strongly Disagree'), (2, 'Disagree'), (3, 'Neutral'), (4, 'Agree'), (5, 'Strongly Agree')]:
                    QuestionOption.objects.create(question=question, value=label, score=score)

            self.stdout.write(f'  ✓ Created {title} with {len(questions_data)} questions')

    def seed_eill(self, user):
        """Executive Integrity & Leadership Lab"""
        # Self-Assessment
        form_self = Form.objects.create(
            title='Executive Integrity & Leadership Lab (EILL) - Self-Assessment',
            description='Executive self-assessment for leadership sustainability.',
            form_type='assessment',
            code='EILL_SELF',
            min_score=10,
            max_score=50,
            created_by=user
        )

        self_questions = [
            ('I feel my workload is sustainable.', False),
            ('I have adequate time for strategic thinking.', False),
            ('I feel emotionally depleted by my role.', True),  # Reverse (3)
            ('I struggle to disconnect from work.', True),  # Reverse (4)
            ('I feel supported by my peers.', False),
            ('I model healthy work boundaries.', False),
            ('I feel my decisions are becoming reactive.', False),
            ('I have time for personal recovery.', False),
            ('I feel isolated in my leadership role.', False),
            ('I worry about my long-term sustainability.', True),  # Reverse (10)
        ]

        for idx, (q_text, reverse) in enumerate(self_questions, 1):
            question = Question.objects.create(
                form=form_self,
                question_text=q_text,
                question_type='likert',
                required=True,
                order=idx,
                reverse_scored=reverse,
                min_value=1,
                max_value=5
            )
            for score, label in [(1, 'Strongly Disagree'), (2, 'Disagree'), (3, 'Neutral'), (4, 'Agree'), (5, 'Strongly Agree')]:
                QuestionOption.objects.create(question=question, value=label, score=score)

        # Direct Report Feedback
        form_report = Form.objects.create(
            title='Executive Integrity & Leadership Lab (EILL) - Direct Report Feedback',
            description='Direct report feedback on executive leadership.',
            form_type='assessment',
            code='EILL_REPORT',
            min_score=10,
            max_score=50,
            created_by=user
        )

        report_questions = [
            ('My leader appears sustainable in their role.', False),
            ('My leader seems overwhelmed.', True),  # Reverse (2)
            ('My leader is accessible when needed.', False),
            ('My leader appears emotionally exhausted.', True),  # Reverse (4)
            ('My leader models healthy boundaries.', False),
            ('My leader seems reactive rather than strategic.', True),  # Reverse (6)
            ('I trust my leader\'s decision-making.', False),
            ('My leader appears disconnected.', True),  # Reverse (8)
            ('My leader supports team wellbeing.', False),
            ('I worry about my leader\'s sustainability.', True),  # Reverse (10)
        ]

        for idx, (q_text, reverse) in enumerate(report_questions, 1):
            question = Question.objects.create(
                form=form_report,
                question_text=q_text,
                question_type='likert',
                required=True,
                order=idx,
                reverse_scored=reverse,
                min_value=1,
                max_value=5
            )
            for score, label in [(1, 'Strongly Disagree'), (2, 'Disagree'), (3, 'Neutral'), (4, 'Agree'), (5, 'Strongly Agree')]:
                QuestionOption.objects.create(question=question, value=label, score=score)

        self.stdout.write(f'  ✓ Created EILL Self-Assessment with {len(self_questions)} questions')
        self.stdout.write(f'  ✓ Created EILL Direct Report with {len(report_questions)} questions')
