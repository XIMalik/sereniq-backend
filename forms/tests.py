from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from .models import (
    AccessKey, Answer, AssessmentCampaign, Form, FormLockedError, Organisation,
    Question, QuestionOption, Submission,
)

User = get_user_model()


class EfiovaModelTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('admin@example.com', 'pw', name='Admin', role='admin')

    def make_form(self, code='EPA', version='2.1', type_='sub', attributable=False, order=101):
        form = Form.objects.create(
            title=f'{code} {version}', form_type='assessment', type=type_, order=order,
            instrument_code=code, version=version, scale_type='agreement',
            is_attributable=attributable, created_by=self.user,
        )
        q = Question.objects.create(form=form, question_text='Q1', question_type='likert', item_number=1,
                                    item_code=f'{code}-F-01', polarity='positive', required=True)
        QuestionOption.objects.create(question=q, value='Agree', numeric_value=4)
        return form, q


class VersioningRuleTests(EfiovaModelTestBase):
    def test_unique_instrument_version_tier(self):
        self.make_form()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_form(order=102)
        # a different version or tier is fine
        self.make_form(version='2.2', order=103)
        self.make_form(type_='pilot', order=104)

    def test_legacy_forms_exempt_from_unique_constraint(self):
        for order in (1, 2):
            Form.objects.create(title='Legacy', form_type='survey', type='sub', order=order, created_by=self.user)

    def test_package_tier_derived_from_type(self):
        self.assertEqual(self.make_form()[0].package_tier, 'full')
        self.assertEqual(self.make_form(type_='pilot', order=102)[0].package_tier, 'pilot')

    def test_form_with_submissions_is_locked(self):
        form, q = self.make_form()
        # editable before any submission
        q.question_text = 'Edited'
        q.save()
        Submission.objects.create(form=form)

        q.question_text = 'Edited again'
        with self.assertRaises(FormLockedError):
            q.save()
        with self.assertRaises(FormLockedError):
            Question.objects.create(form=form, question_text='New', question_type='likert')
        with self.assertRaises(FormLockedError):
            QuestionOption.objects.create(question=q, value='Disagree', numeric_value=2)
        # pre_delete runs inside Django's atomic block, so isolate each in a savepoint
        with self.assertRaises(FormLockedError), transaction.atomic():
            q.options.first().delete()
        with self.assertRaises(FormLockedError), transaction.atomic():
            q.delete()
        form.version = '2.2'
        with self.assertRaises(FormLockedError):
            form.save()
        with self.assertRaises(FormLockedError), transaction.atomic():
            Form.objects.filter(pk=form.pk).delete()
        self.assertTrue(Form.objects.filter(pk=form.pk).exists())
        self.assertEqual(form.questions.count(), 1)

    def test_legacy_form_with_submissions_stays_editable(self):
        form = Form.objects.create(title='Legacy', form_type='survey', created_by=self.user)
        q = Question.objects.create(form=form, question_text='Q', question_type='text')
        Submission.objects.create(form=form)
        q.question_text = 'Edited'
        q.save()
        form.title = 'Renamed'
        form.save()


class AnswerConstraintTests(EfiovaModelTestBase):
    def test_numeric_value_range_and_na_exclusive(self):
        form, q = self.make_form()
        sub = Submission.objects.create(form=form)
        for kwargs in ({'numeric_value': 0}, {'numeric_value': 6}, {'numeric_value': 3, 'is_not_applicable': True}):
            with self.assertRaises(IntegrityError), transaction.atomic():
                Answer.objects.create(submission=sub, question=q, answer_text='x', **kwargs)
        Answer.objects.create(submission=sub, question=q, answer_text='N/A', is_not_applicable=True)


class PrivacyTests(EfiovaModelTestBase):
    def test_non_attributable_submission_stores_no_identity_and_coarse_time(self):
        form, _ = self.make_form(code='EPA')
        sub = Submission.objects.create(form=form, submitted_by=self.user)
        sub.refresh_from_db()
        self.assertIsNone(sub.submitted_by)
        self.assertEqual((sub.submitted_at.hour, sub.submitted_at.minute, sub.submitted_at.second), (0, 0, 0))

    def test_submission_model_has_no_key_ip_or_user_agent_fields(self):
        names = {f.name for f in Submission._meta.get_fields()}
        self.assertFalse(names & {'access_key', 'key', 'ip_address', 'ip', 'user_agent'})

    def test_legacy_submission_unchanged(self):
        form = Form.objects.create(title='Legacy', form_type='survey', created_by=self.user)
        sub = Submission.objects.create(form=form, submitted_by=self.user)
        self.assertEqual(sub.submitted_by, self.user)
        self.assertNotEqual(sub.submitted_at.time().replace(microsecond=0).isoformat(), '00:00:00')


class CampaignAndKeyTests(EfiovaModelTestBase):
    def test_single_use_key_invalid_after_use(self):
        key = AccessKey.objects.create(is_single_use=True)
        self.assertTrue(key.is_valid())
        key.used_at = timezone.now()
        key.save()
        self.assertFalse(key.is_valid())

    def test_legacy_key_unaffected(self):
        key = AccessKey.objects.create(company_name='Acme')
        key.used_at = timezone.now()
        self.assertTrue(key.is_valid())

    def test_campaign_open_window_and_group_validation(self):
        org = Organisation.objects.create(name='Acme')
        today = timezone.localdate()
        c = AssessmentCampaign.objects.create(
            organisation=org, name='Pilot', package_tier='pilot', status='active',
            start_date=today - timedelta(days=1), end_date=today + timedelta(days=1),
            group_labels=['Ops', 'Sales'],
        )
        self.assertTrue(c.is_open())
        c.status = 'closed'
        self.assertFalse(c.is_open())
        c.status, c.group_labels = 'active', ['Ops', 'Ops']
        with self.assertRaises(Exception):
            c.full_clean()

    def test_submission_group_label_must_belong_to_campaign(self):
        org = Organisation.objects.create(name='Acme')
        form, _ = self.make_form()
        c = AssessmentCampaign.objects.create(organisation=org, name='C', package_tier='full', group_labels=['Ops'])
        c.forms.add(form)
        sub = Submission(form=form, campaign=c, group_label='Ops')
        sub.full_clean()
        sub.group_label = 'Unknown'
        with self.assertRaises(Exception):
            sub.full_clean()


# ---- seed_efiova ------------------------------------------------------------------------------
import copy
import json
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError

from .management.commands.seed_efiova import FIXTURE_PATH


class SeedEfiovaTests(EfiovaModelTestBase):
    def seed(self, **kwargs):
        out = StringIO()
        call_command('seed_efiova', stdout=out, **kwargs)
        return out.getvalue()

    def efiova(self):
        return Form.objects.exclude(instrument_code='')

    def test_seed_creates_14_forms_100_full_and_47_pilot_items(self):
        self.seed()
        self.assertEqual(self.efiova().count(), 14)
        self.assertEqual(Question.objects.filter(form__type='sub').exclude(form__instrument_code='').count(), 100)
        self.assertEqual(Question.objects.filter(form__type='pilot').exclude(form__instrument_code='').count(), 47)

    def test_seed_is_idempotent(self):
        self.seed()
        before = (Form.objects.count(), Question.objects.count(), QuestionOption.objects.count())
        ids = set(Question.objects.values_list('id', flat=True))
        out = self.seed()
        self.assertEqual(before, (Form.objects.count(), Question.objects.count(), QuestionOption.objects.count()))
        self.assertEqual(ids, set(Question.objects.values_list('id', flat=True)))  # rows untouched
        self.assertIn('14 unchanged', out)

    def test_options_and_metadata(self):
        self.seed()
        cri = Form.objects.get(instrument_code='CRI', type='sub')
        q = cri.questions.get(item_number=13)
        self.assertEqual(q.polarity, 'positive')
        self.assertEqual(q.construct_key, 'CRI-F-13')
        opts = list(q.options.order_by('id').values_list('value', 'numeric_value', 'is_not_applicable'))
        self.assertEqual(opts[0], ('Strongly Disagree', 1, False))
        self.assertEqual(opts[-1], ('Not enough visibility', None, True))
        epa_p = Form.objects.get(instrument_code='EPA', type='pilot')
        self.assertEqual(epa_p.questions.get(item_number=2).construct_key, 'EPA-F-03')
        self.assertEqual(epa_p.questions.get(item_number=2).polarity, 'negative')
        self.assertEqual(epa_p.questions.get(item_number=1).options.count(), 5)  # EPA has no N/A
        wdai = Form.objects.get(instrument_code='WDAI', type='sub')
        self.assertTrue(all(q.polarity == 'negative' for q in wdai.questions.all()))
        self.assertTrue(Form.objects.get(instrument_code='CPDA', type='pilot').is_attributable)
        self.assertFalse(Form.objects.get(instrument_code='ESS', type='pilot').is_attributable)

    def test_refuses_to_change_form_with_submissions(self):
        self.seed()
        form = Form.objects.get(instrument_code='EPA', type='sub')
        Submission.objects.create(form=form)

        data = json.loads(FIXTURE_PATH.read_text(encoding='utf-8'))
        for inst in data['instruments']:
            if inst['instrument_code'] == 'EPA' and inst['package_tier'] == 'full':
                inst['items'][0]['text'] = 'Changed wording.'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'f.json'
            path.write_text(json.dumps(data))
            with self.assertRaisesMessage(CommandError, 'already has submissions'):
                self.seed(fixture=str(path))
        self.assertNotEqual(form.questions.get(item_number=1).question_text, 'Changed wording.')

        self.assertIn('14 unchanged', self.seed())  # identical fixture is fine even with submissions

    def test_updates_form_without_submissions(self):
        self.seed()
        form = Form.objects.get(instrument_code='EPA', type='sub')
        q = form.questions.get(item_number=1)
        q.question_text = 'tampered'
        q.save()
        self.assertIn('1 updated', self.seed())
        self.assertNotEqual(form.questions.get(item_number=1).question_text, 'tampered')

    def test_fixture_count_mismatch_fails_loudly(self):
        data = json.loads(FIXTURE_PATH.read_text(encoding='utf-8'))
        broken = copy.deepcopy(data)
        broken['instruments'][0]['items'].pop()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'f.json'
            path.write_text(json.dumps(broken))
            with self.assertRaisesMessage(CommandError, 'expected 10 items, found 9'):
                self.seed(fixture=str(path))
        self.assertEqual(self.efiova().count(), 0)

    def test_requires_admin_user(self):
        User.objects.all().delete()
        with self.assertRaisesMessage(CommandError, 'No admin user'):
            self.seed()


# ---- scoring, suppression and reporting ---------------------------------------------------------
from rest_framework.test import APIClient

from .scoring import (
    NA, REASON_COMPLEMENTARY, REASON_SMALL, aggregate_campaign_form, aggregate_organisation_form,
    dimension_score, item_risk_score, plan_suppression,
)


class ReportingTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user('admin@example.com', 'pw', name='Admin', role='admin')
        cls.staff = User.objects.create_user('staff@example.com', 'pw', name='Staff', role='staff')
        call_command('seed_efiova', stdout=StringIO())
        cls.org = Organisation.objects.create(name='Acme')
        cls.epa = Form.objects.get(instrument_code='EPA', type='sub')
        cls.wdai_full = Form.objects.get(instrument_code='WDAI', type='sub')
        cls.wdai_pilot = Form.objects.get(instrument_code='WDAI', type='pilot')
        cls.cpda = Form.objects.get(instrument_code='CPDA', type='sub')

    def campaign(self, forms, tier='full', min_size=5, labels=('A', 'B', 'C'), **kwargs):
        c = AssessmentCampaign.objects.create(
            organisation=self.org, name=f'{tier} campaign', package_tier=tier, min_group_size=min_size,
            group_labels=list(labels), status='active', **kwargs)
        c.forms.set(forms)
        return c

    def submit(self, form, campaign, group, values=None, default=3):
        """Create a submission. `values` maps item_number -> 1..5 or 'NA'."""
        values = values or {}
        sub = Submission.objects.create(form=form, campaign=campaign, group_label=group, consent_acknowledged=True)
        rows = []
        for q in form.questions.all():
            v = values.get(q.item_number, default)
            na = v == 'NA'
            rows.append(Answer(submission=sub, question=q, answer_text='NA' if na else str(v),
                               numeric_value=None if na else v, is_not_applicable=na))
        Answer.objects.bulk_create(rows)
        return sub

    def submit_many(self, form, campaign, group, n, **kwargs):
        for _ in range(n):
            self.submit(form, campaign, group, **kwargs)

    @staticmethod
    def item(result_cell, code):
        return next(i for i in result_cell['items'] if i['item_code'] == code)

    @staticmethod
    def group(result, label):
        return next(g for g in result['groups'] if g['group_label'] == label)


class ScoringRuleTests(ReportingTestBase):
    def test_polarity_flip_and_na_excluded(self):
        self.assertEqual(item_risk_score('positive', 4), 2)
        self.assertEqual(item_risk_score('positive', 1), 5)
        self.assertEqual(item_risk_score('negative', 4), 4)
        self.assertEqual(item_risk_score('negative', 1), 1)
        self.assertIsNone(item_risk_score('positive', None))

    def test_dimension_score_null_below_half_answered(self):
        self.assertIsNone(dimension_score([4], 3))              # 1 of 3 answered
        self.assertIsNone(dimension_score([None, None, 2], 3))  # N/A does not count as answered
        self.assertEqual(dimension_score([4, None], 2), 4)      # exactly 50% is enough
        self.assertEqual(dimension_score([2, 4, 3], 3), 3)

    def test_item_and_dimension_aggregates(self):
        c = self.campaign([self.epa])
        # EPA item 1 is positive (agree = healthy), item 3 negative; item 1 & 4 form the "capacity" dimension
        for v in (1, 2, 4, 5, 5):
            self.submit(self.epa, c, 'A', {1: v, 3: v})
        result = aggregate_campaign_form(c, self.epa)
        self.assertEqual(result['scoring_status'], 'provisional')
        total = result['total']
        self.assertEqual(total['n_submissions'], 5)
        i1, i3 = self.item(total, 'EPA-F-01'), self.item(total, 'EPA-F-03')
        # positive item: risk = 6 - raw -> 5,4,2,1,1  mean 2.6
        self.assertEqual(i1['mean'], 2.6)
        self.assertEqual(i1['pct_unfavourable'], 40.0)   # risk >= 4: two of five
        self.assertEqual(i1['distribution'], {'1': 1, '2': 1, '3': 0, '4': 1, '5': 2})
        # negative item: risk = raw -> 1,2,4,5,5 mean 3.4
        self.assertEqual(i3['mean'], 3.4)
        self.assertEqual(i3['pct_unfavourable'], 60.0)
        self.assertEqual(i1['sd'], round(statistics_sd([5, 4, 2, 1, 1]), 2))
        cap = next(d for d in total['dimensions'] if d['dimension'] == 'capacity')
        self.assertEqual(cap['n'], 5)
        self.assertEqual(cap['item_count'], 2)

    def test_na_excluded_from_item_stats_and_counted(self):
        ocei = Form.objects.get(instrument_code='OCEI', type='sub')
        c = self.campaign([ocei], min_size=2)  # 4 answered would otherwise fall under the default minimum of 5
        for v in (2, 3, 4, 5, 'NA', 'NA'):
            self.submit(ocei, c, 'A', {1: v})
        item = self.item(aggregate_campaign_form(c, ocei)['total'], 'OCEI-F-01')
        self.assertEqual((item['n'], item['na_count'], item['mean']), (4, 2, 3.5))

    def test_dimension_insufficient_answers_excluded(self):
        c = self.campaign([self.wdai_full], min_size=2)
        # cognitive_load = items 1-3; two respondents answer only one item (N/A for 2 and 3)
        self.submit_many(self.wdai_full, c, 'A', 5, values={2: 'NA', 3: 'NA'})
        self.submit_many(self.wdai_full, c, 'A', 2)
        dim = next(d for d in aggregate_campaign_form(c, self.wdai_full)['total']['dimensions']
                   if d['dimension'] == 'cognitive_load')
        self.assertEqual(dim['n'], 2)
        self.assertEqual(dim['insufficient_answers'], 5)

    def test_no_individual_level_data_in_results(self):
        c = self.campaign([self.epa])
        self.submit_many(self.epa, c, 'A', 6)
        blob = json.dumps(aggregate_campaign_form(c, self.epa))
        for word in ('submission_id', 'respondent', 'user', 'key'):
            self.assertNotIn(word, blob.replace('construct_key', ''))


def statistics_sd(values):
    import statistics
    return statistics.stdev(values)


class SuppressionTests(ReportingTestBase):
    def test_plan_suppression_small_group_and_complementary(self):
        # one small group would be recoverable as total - visible, so the smallest visible group joins it
        supp, reasons, total = plan_suppression({'A': 3, 'B': 5, 'C': 8}, 5)
        self.assertEqual(supp, {'A', 'B'})
        self.assertEqual(reasons, {'A': REASON_SMALL, 'B': REASON_COMPLEMENTARY})
        self.assertFalse(total)

    def test_plan_suppression_no_complementary_when_pool_is_large_enough(self):
        supp, _, _ = plan_suppression({'A': 3, 'B': 3, 'C': 8}, 5)
        self.assertEqual(supp, {'A', 'B'})   # pooled residual of 6 is safe
        supp, _, _ = plan_suppression({'A': 5, 'B': 6}, 5)
        self.assertEqual(supp, set())

    def test_plan_suppression_total_too_small(self):
        supp, _, total = plan_suppression({'A': 2, 'B': 2}, 5)
        self.assertTrue(total)
        self.assertEqual(supp, {'A', 'B'})

    def test_suppressed_group_has_no_numbers(self):
        c = self.campaign([self.epa])
        self.submit_many(self.epa, c, 'A', 3)
        self.submit_many(self.epa, c, 'B', 6)
        self.submit_many(self.epa, c, 'C', 9)
        result = aggregate_campaign_form(c, self.epa)
        a, b, cc = (self.group(result, x) for x in 'ABC')
        self.assertEqual(a, {'group_label': 'A', 'suppressed': True, 'reason': REASON_SMALL})
        # B is the smallest visible group; hiding only A would let total - B - C recover A
        self.assertEqual(b, {'group_label': 'B', 'suppressed': True, 'reason': REASON_COMPLEMENTARY})
        self.assertFalse(cc['suppressed'])
        self.assertEqual(cc['n_submissions'], 9)
        self.assertEqual(result['total']['n_submissions'], 18)

    def test_complementary_case_cannot_recover_suppressed_group(self):
        """total - sum(visible groups) must never be a pool smaller than min_group_size."""
        c = self.campaign([self.epa])
        self.submit_many(self.epa, c, 'A', 2)
        self.submit_many(self.epa, c, 'B', 7)
        self.submit_many(self.epa, c, 'C', 5)
        result = aggregate_campaign_form(c, self.epa)
        visible = sum(g['n_submissions'] for g in result['groups'] if not g['suppressed'])
        residual = result['total']['n_submissions'] - visible
        self.assertGreaterEqual(residual, c.min_group_size)

    def test_total_suppressed_when_below_minimum(self):
        c = self.campaign([self.epa])
        self.submit_many(self.epa, c, 'A', 2)
        self.submit_many(self.epa, c, 'B', 2)
        result = aggregate_campaign_form(c, self.epa)
        self.assertEqual(result['total'], {'suppressed': True, 'reason': REASON_SMALL})
        self.assertTrue(all(g['suppressed'] for g in result['groups']))

    def test_item_level_suppression_with_complementary(self):
        ocei = Form.objects.get(instrument_code='OCEI', type='sub')
        c = self.campaign([ocei])
        # group A: 6 submissions but only 3 answer item 1; group B: 6 answer it
        for i in range(6):
            self.submit(ocei, c, 'A', {1: 'NA' if i < 3 else 3})
        self.submit_many(ocei, c, 'B', 6)
        result = aggregate_campaign_form(c, ocei)
        a_item = self.item(self.group(result, 'A'), 'OCEI-F-01')
        b_item = self.item(self.group(result, 'B'), 'OCEI-F-01')
        self.assertEqual(a_item['reason'], REASON_SMALL)
        self.assertTrue(b_item['suppressed'] and b_item['reason'] == REASON_COMPLEMENTARY)
        self.assertNotIn('mean', a_item)
        self.assertEqual(self.item(result['total'], 'OCEI-F-01')['n'], 9)
        # other items in the same groups are unaffected
        self.assertFalse(self.item(self.group(result, 'A'), 'OCEI-F-02')['suppressed'] if 'suppressed' in
                         self.item(self.group(result, 'A'), 'OCEI-F-02') else False)

    def test_organisation_total_pools_campaigns(self):
        c1 = self.campaign([self.epa])
        c2 = self.campaign([self.epa])
        self.submit_many(self.epa, c1, 'A', 3)
        self.submit_many(self.epa, c2, 'A', 3)
        result = aggregate_organisation_form(self.org, self.epa)
        self.assertNotIn('groups', result)
        self.assertEqual(result['total']['n_submissions'], 6)


class ReportingApiTests(ReportingTestBase):
    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def test_unauthenticated_and_nonstaff_blocked(self):
        c = self.campaign([self.epa])
        self.assertEqual(APIClient().get(f'/api/campaigns/{c.id}/results/').status_code, 401)
        member = User.objects.create_user('m@example.com', 'pw', name='M', role='team_member')
        self.assertEqual(self.client_for(member).get(f'/api/campaigns/{c.id}/results/').status_code, 403)

    def test_attributable_results_admin_only(self):
        c = self.campaign([self.epa, self.cpda])
        self.submit_many(self.cpda, c, 'A', 6)
        self.submit_many(self.epa, c, 'A', 6)
        staff, admin = self.client_for(self.staff), self.client_for(self.admin)

        listing = staff.get(f'/api/campaigns/{c.id}/results/').json()['results']
        restricted = [r for r in listing if r.get('restricted')]
        self.assertEqual([r['form']['instrument_code'] for r in restricted], ['CPDA'])
        self.assertTrue(any(r['form']['instrument_code'] == 'EPA' and 'total' in r for r in listing))
        self.assertEqual(staff.get(f'/api/campaigns/{c.id}/results/?form={self.cpda.id}').status_code, 403)
        self.assertEqual(staff.get(f'/api/campaigns/{c.id}/export/?form={self.cpda.id}').status_code, 403)

        full = admin.get(f'/api/campaigns/{c.id}/results/?form={self.cpda.id}').json()['results'][0]
        self.assertTrue(full['attributable'])
        self.assertIn('attributable_notice', full)
        self.assertEqual(full['scoring_status'], 'provisional')

    def test_only_admin_can_write(self):
        body = {'organisation': self.org.id, 'name': 'New', 'package_tier': 'full', 'forms': [self.epa.id],
                'group_labels': ['A', 'B']}
        self.assertEqual(self.client_for(self.staff).post('/api/campaigns/', body, format='json').status_code, 403)
        res = self.client_for(self.admin).post('/api/campaigns/', body, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()['min_group_size'], 5)

    def test_campaign_validation(self):
        admin = self.client_for(self.admin)
        base = {'organisation': self.org.id, 'name': 'X', 'package_tier': 'pilot', 'forms': [self.epa.id]}
        self.assertEqual(admin.post('/api/campaigns/', base, format='json').status_code, 400)  # full form in pilot campaign
        dupes = {**base, 'package_tier': 'full', 'group_labels': ['A', 'A']}
        self.assertEqual(admin.post('/api/campaigns/', dupes, format='json').status_code, 400)

    def test_cannot_weaken_campaign_after_submissions(self):
        c = self.campaign([self.epa])
        self.submit(self.epa, c, 'A')
        admin = self.client_for(self.admin)
        self.assertEqual(admin.patch(f'/api/campaigns/{c.id}/', {'min_group_size': 2}, format='json').status_code, 400)
        self.assertEqual(admin.patch(f'/api/campaigns/{c.id}/', {'group_labels': ['B', 'C']}, format='json').status_code, 400)
        self.assertEqual(admin.patch(f'/api/campaigns/{c.id}/', {'min_group_size': 8}, format='json').status_code, 200)
        self.assertEqual(admin.delete(f'/api/campaigns/{c.id}/').status_code, 400)  # protected by its submissions

    def test_bulk_key_issuance(self):
        c = self.campaign([self.epa])
        admin = self.client_for(self.admin)
        res = admin.post(f'/api/campaigns/{c.id}/access-keys/',
                         {'form': self.epa.id, 'count': 3, 'group_label': 'A', 'expires_in_days': 7}, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(len(res.json()['keys']), 3)
        keys = AccessKey.objects.filter(campaign=c)
        self.assertEqual(keys.count(), 3)
        self.assertTrue(all(k.is_single_use and k.group_label == 'A' and k.form_id == self.epa.id and k.expires_at
                            and k.has_sub_access and not k.has_pilot_access for k in keys))
        listing = admin.get(f'/api/campaigns/{c.id}/access-keys/').json()
        self.assertEqual({k['used'] for k in listing}, {False})
        self.assertNotIn('used_at', listing[0])
        # validation
        bad_group = admin.post(f'/api/campaigns/{c.id}/access-keys/', {'form': self.epa.id, 'count': 1, 'group_label': 'Z'}, format='json')
        bad_form = admin.post(f'/api/campaigns/{c.id}/access-keys/', {'form': self.wdai_full.id, 'count': 1}, format='json')
        too_many = admin.post(f'/api/campaigns/{c.id}/access-keys/', {'form': self.epa.id, 'count': 501}, format='json')
        self.assertEqual([bad_group.status_code, bad_form.status_code, too_many.status_code], [400, 400, 400])
        self.assertEqual(self.client_for(self.staff).post(
            f'/api/campaigns/{c.id}/access-keys/', {'form': self.epa.id, 'count': 1}, format='json').status_code, 403)

    def test_csv_export_is_anonymised_and_respects_suppression(self):
        c = self.campaign([self.epa])
        self.submit_many(self.epa, c, 'A', 2)
        self.submit_many(self.epa, c, 'B', 6)
        res = self.client_for(self.staff).get(f'/api/campaigns/{c.id}/export/?form={self.epa.id}')
        self.assertEqual(res.status_code, 200)
        lines = res.content.decode().strip().splitlines()
        header = lines[0].split(',')
        self.assertEqual(header[:2], ['group', 'submitted_month'])
        self.assertFalse({'id', 'submission_id', 'key', 'user', 'email', 'ip'} & set(header))
        self.assertEqual(len(lines) - 1, 8)
        groups = [l.split(',')[0] for l in lines[1:]]
        # A (2) is below the minimum and B (6) is complementary-hidden to keep the pool >= 5: both pooled
        self.assertEqual(set(groups), {'SUPPRESSED'})

    def test_csv_export_refused_when_total_too_small(self):
        c = self.campaign([self.epa])
        self.submit_many(self.epa, c, 'A', 3)
        res = self.client_for(self.admin).get(f'/api/campaigns/{c.id}/export/?form={self.epa.id}')
        self.assertEqual(res.status_code, 409)

    def test_csv_export_neutralises_formula_injection(self):
        from .exports import _safe
        self.assertEqual(_safe('=HYPERLINK("x")'), "'=HYPERLINK(\"x\")")
        self.assertEqual(_safe('Ops'), 'Ops')

    def test_cross_tier_comparison(self):
        pilot = self.campaign([self.wdai_pilot], tier='pilot')
        full = self.campaign([self.wdai_full], tier='full')
        self.submit_many(self.wdai_pilot, pilot, 'A', 6, default=4)
        self.submit_many(self.wdai_full, full, 'A', 6, default=2)
        res = self.client_for(self.staff).get(
            f'/api/campaigns/{pilot.id}/compare/?with={full.id}&instrument=WDAI')
        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()
        self.assertEqual(data['scoring_status'], 'provisional')
        self.assertTrue(any('Versions differ' in c and 'v1.1' in c and 'v2.1' in c for c in data['caveats']))
        self.assertTrue(any('Reference periods differ' in c for c in data['caveats']))
        self.assertEqual(len(data['items']), 6)
        row = next(i for i in data['items'] if i['pilot_item_code'] == 'WDAI-P-01')
        self.assertEqual(row['construct_key'], 'WDAI-F-02')
        self.assertFalse(row['wording_identical'])
        self.assertEqual(row['mean_difference'], 2.0)   # pilot risk 4 vs full risk 2
        dim = next(d for d in data['dimensions'] if d['dimension'] == 'time_pressure')
        self.assertEqual((dim['items_in_pilot'], dim['items_in_full']), (1, 3))
        # same-tier comparison is rejected
        other_full = self.campaign([self.wdai_full], tier='full')
        self.assertEqual(self.client_for(self.staff).get(
            f'/api/campaigns/{full.id}/compare/?with={other_full.id}&instrument=WDAI').status_code, 400)

    def test_organisation_results_endpoint(self):
        c = self.campaign([self.epa])
        self.submit_many(self.epa, c, 'A', 6)
        res = self.client_for(self.staff).get(f'/api/organisations/{self.org.id}/results/?form={self.epa.id}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['total']['n_submissions'], 6)
        self.assertEqual(self.client_for(self.staff).get(
            f'/api/organisations/{self.org.id}/results/?form={self.cpda.id}').status_code, 403)


# ---- legacy behaviour, admin and key validation ---------------------------------------------------
from django.contrib import admin as django_admin
from django.test import RequestFactory

from .admin import AccessKeyInline, AssessmentCampaignAdmin, QuestionInline, SubmissionAdmin


class LegacyFormsStillWorkTests(ReportingTestBase):
    """Non-EFIOVA forms, keys and submissions behave exactly as before."""

    def make_legacy_form(self):
        form = Form.objects.create(title='Legacy PLI', form_type='assessment', code='PLI', type='pilot', order=1,
                                   min_score=0, max_score=8, created_by=self.admin)
        for i in (1, 2):
            q = Question.objects.create(form=form, question_text=f'Q{i}', question_type='likert', required=True,
                                        order=i, min_value=1, max_value=5)
            for v in range(1, 6):
                QuestionOption.objects.create(question=q, value=f'{v} - label', score=v)
        return form

    def test_legacy_submit_and_scoring(self):
        form = self.make_legacy_form()
        questions = list(form.questions.all())
        payload = {'answers': [{'question': q.id, 'answer_text': '4 - label'} for q in questions]}
        res = APIClient().post(f'/api/forms/{form.id}/submit/', payload, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        body = res.json()
        self.assertEqual(body['score_result']['raw_score'], 8)
        sub = Submission.objects.get(pk=body['submission']['id'])
        self.assertIsNone(sub.campaign_id)
        self.assertEqual(sub.answers.count(), 2)
        self.assertIsNone(sub.answers.first().numeric_value)

    def test_legacy_access_key_flow(self):
        form = self.make_legacy_form()
        key = AccessKey.objects.create(company_name='Legacy Co', has_pilot_access=True)
        client = APIClient()
        valid = client.post('/api/forms/validate_key/', {'access_key': str(key.key)}, format='json').json()
        self.assertTrue(valid['valid'])
        listing = client.get('/api/forms/by_type/?type=pilot', HTTP_X_ACCESS_KEY=str(key.key)).json()
        self.assertIn(form.id, [f['id'] for f in listing['forms']])
        self.assertEqual(client.get('/api/forms/by_type/?type=pilot').json()['forms'], [])  # no key, no forms

    def test_legacy_submit_endpoint_refuses_efiova_forms(self):
        res = APIClient().post(f'/api/forms/{self.epa.id}/submit/', {'answers': []}, format='json')
        self.assertEqual(res.status_code, 403)
        self.assertEqual(Submission.objects.count(), 0)

    def test_legacy_question_edit_unaffected_but_efiova_edit_blocked_after_submission(self):
        legacy = self.make_legacy_form()
        Submission.objects.create(form=legacy)
        admin = APIClient()
        admin.force_authenticate(self.admin)
        q = legacy.questions.first()
        self.assertEqual(admin.patch(f'/api/questions/{q.id}/', {'question_text': 'edited'}, format='json').status_code, 200)

        c = self.campaign([self.epa])
        self.submit(self.epa, c, 'A')
        eq = self.epa.questions.first()
        res = admin.patch(f'/api/questions/{eq.id}/', {'question_text': 'edited'}, format='json')
        self.assertEqual(res.status_code, 409)
        eq.refresh_from_db()
        self.assertNotEqual(eq.question_text, 'edited')
        # FormViewSet only finds forms the X-ACCESS-KEY header grants, even for admins (existing behaviour)
        key = AccessKey.objects.create(has_sub_access=True)
        res = admin.patch(f'/api/forms/{self.epa.id}/', {'version': '9.9'}, format='json', HTTP_X_ACCESS_KEY=str(key.key))
        self.assertEqual(res.status_code, 409)
        self.epa.refresh_from_db()
        self.assertEqual(self.epa.version, '2.1')


class CampaignKeyValidationTests(ReportingTestBase):
    def test_key_must_match_campaign_form_and_labels(self):
        c = self.campaign([self.epa], labels=('A',))
        AccessKey(campaign=c, form=self.epa, group_label='A').full_clean()
        for kwargs in ({'form': self.wdai_full}, {'form': None}, {'form': self.epa, 'group_label': 'Z'}):
            with self.assertRaises(Exception):
                AccessKey(campaign=c, **{'group_label': '', **kwargs}).full_clean()

    def test_legacy_key_validation_unchanged(self):
        AccessKey(company_name='Acme').full_clean()


class AdminTests(ReportingTestBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.create_superuser('root@example.com', 'pw', name='Root')

    def setUp(self):
        self.client.force_login(self.superuser)

    def request(self):
        request = RequestFactory().get('/')
        request.user = self.superuser
        return request

    def test_admin_pages_render(self):
        c = self.campaign([self.epa])
        self.submit(self.epa, c, 'A')
        urls = [
            '/admin/forms/form/', f'/admin/forms/form/{self.epa.id}/change/',
            f'/admin/forms/form/{self.wdai_pilot.id}/change/',
            '/admin/forms/organisation/', '/admin/forms/assessmentcampaign/',
            '/admin/forms/assessmentcampaign/add/', f'/admin/forms/assessmentcampaign/{c.id}/change/',
            '/admin/forms/submission/', '/admin/forms/accesskey/',
            f'/admin/forms/question/{self.epa.questions.first().id}/change/',
        ]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_campaign_page_shows_counts_but_no_key_timestamps(self):
        c = self.campaign([self.epa])
        self.submit_many(self.epa, c, 'A', 3)
        self.submit_many(self.epa, c, 'B', 2)
        key = AccessKey.objects.create(campaign=c, form=self.epa, is_single_use=True, used_at=timezone.now())
        html = self.client.get(f'/admin/forms/assessmentcampaign/{c.id}/change/').content.decode()
        self.assertIn('EPA v2.1 / A: 3', html)
        self.assertIn('EPA v2.1 / B: 2', html)
        self.assertNotIn(key.used_at.strftime('%H:%M:%S'), html)
        key_html = self.client.get(f'/admin/forms/accesskey/{key.id}/change/').content.decode()
        self.assertNotIn('used_at', key_html)

    def test_locked_form_is_read_only_in_admin(self):
        request = self.request()
        form_admin = django_admin.site._registry[Form]
        question_inline = QuestionInline(Form, django_admin.site)
        self.assertTrue(question_inline.has_add_permission(request, self.epa))
        c = self.campaign([self.epa])
        self.submit(self.epa, c, 'A')
        self.assertFalse(question_inline.has_add_permission(request, self.epa))
        self.assertFalse(question_inline.has_change_permission(request, self.epa))
        self.assertFalse(question_inline.has_delete_permission(request, self.epa))
        self.assertFalse(form_admin.has_delete_permission(request, self.epa))
        self.assertIn('version', form_admin.get_readonly_fields(request, self.epa))
        self.assertNotIn('version', form_admin.get_readonly_fields(request, self.wdai_pilot))

    def test_efiova_submissions_cannot_be_changed_or_deleted_in_admin(self):
        c = self.campaign([self.epa])
        sub = self.submit(self.epa, c, 'A')
        legacy = Submission.objects.create(form=Form.objects.create(title='L', form_type='survey', created_by=self.admin))
        sub_admin = SubmissionAdmin(Submission, django_admin.site)
        request = self.request()
        self.assertFalse(sub_admin.has_change_permission(request, sub))
        self.assertFalse(sub_admin.has_delete_permission(request, sub))
        self.assertTrue(sub_admin.has_delete_permission(request, legacy))
        sub_admin.message_user = lambda *a, **k: None
        sub_admin.delete_queryset(request, Submission.objects.all())
        self.assertTrue(Submission.objects.filter(pk=sub.pk).exists())
        self.assertFalse(Submission.objects.filter(pk=legacy.pk).exists())

    def test_inline_key_issuance(self):
        c = self.campaign([self.epa], labels=('A',))
        campaign_admin = AssessmentCampaignAdmin(AssessmentCampaign, django_admin.site)
        inline = AccessKeyInline(AssessmentCampaign, django_admin.site)
        request = self.request()
        self.assertFalse(inline.has_add_permission(request, None))   # campaign must be saved first
        self.assertTrue(inline.has_add_permission(request, c))
        self.assertFalse(inline.has_delete_permission(request, c))

        class FakeFormset:
            model = AccessKey
            def save(self, commit=True):
                return [AccessKey(form=self_form, group_label='A')]
            def save_m2m(self):
                pass
        self_form = self.epa
        class FakeForm:
            instance = c
        campaign_admin.save_formset(request, FakeForm(), FakeFormset(), change=True)
        key = AccessKey.objects.get(campaign=c)
        self.assertTrue(key.is_single_use)
        self.assertTrue(key.has_sub_access and not key.has_pilot_access)
        self.assertEqual(key.company_name, 'Acme')

    def test_campaign_admin_form_rejects_tier_mismatch_and_weakening(self):
        from .admin import CampaignAdminForm
        data = {'organisation': self.org.id, 'name': 'X', 'package_tier': 'pilot', 'forms': [self.epa.id],
                'status': 'draft', 'min_group_size': 5, 'group_labels': '[]'}
        form = CampaignAdminForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('forms', form.errors)

        c = self.campaign([self.epa])
        self.submit(self.epa, c, 'A')
        data = {'organisation': self.org.id, 'name': c.name, 'package_tier': 'full', 'forms': [self.epa.id],
                'status': 'active', 'min_group_size': 2, 'group_labels': '["A", "B", "C"]'}
        form = CampaignAdminForm(data=data, instance=c)
        self.assertFalse(form.is_valid())
        self.assertIn('min_group_size', form.errors)


class UserDeletionTests(ReportingTestBase):
    def test_deleting_creator_keeps_forms_questions_and_submissions(self):
        creator = User.objects.create_user('creator@sereniqhq.com', 'pw', name='Creator', role='admin')
        legacy = Form.objects.create(title='Legacy', form_type='survey', created_by=creator)
        Question.objects.create(form=legacy, question_text='Q', question_type='text')
        Form.objects.filter(pk=self.epa.pk).update(created_by=creator)
        c = self.campaign([self.epa])
        self.submit(self.epa, c, 'A')
        counts = (Form.objects.count(), Question.objects.count(), QuestionOption.objects.count(),
                  Submission.objects.count(), Answer.objects.count())

        creator.delete()

        self.assertEqual(counts, (Form.objects.count(), Question.objects.count(), QuestionOption.objects.count(),
                                  Submission.objects.count(), Answer.objects.count()))
        self.assertIsNone(Form.objects.get(pk=legacy.pk).created_by)
        self.assertIsNone(Form.objects.get(pk=self.epa.pk).created_by)
