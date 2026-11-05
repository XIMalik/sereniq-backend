import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from forms.models import Form, Question, QuestionOption

User = get_user_model()

FIXTURE_PATH = Path(__file__).resolve().parents[2] / 'fixtures' / 'efiova' / 'instruments.json'

# Expected item counts live here, not in the fixture, so a bad fixture cannot redefine them.
EXPECTED_FULL = {'EPA': 10, 'WDAI': 18, 'OCEI': 12, 'CRI': 18, 'CPDA': 12, 'EILL': 18, 'ESS': 12}
EXPECTED_PILOT = {'EPA': 7, 'WDAI': 6, 'OCEI': 8, 'CRI': 6, 'CPDA': 8, 'EILL': 6, 'ESS': 6}
EXPECTED_PILOT_VERSIONS = {'EPA': '1.2', 'WDAI': '1.1', 'OCEI': '1.1', 'CRI': '1.1', 'CPDA': '1.1', 'EILL': '1.2', 'ESS': '1.1'}
FULL_VERSION = '2.1'
INSTRUMENT_ORDER = ['EPA', 'WDAI', 'OCEI', 'CRI', 'CPDA', 'EILL', 'ESS']
ORDER_BASE = 100  # EFIOVA forms are ordered 101-107 within each type

TIER_TO_TYPE = {'full': 'sub', 'pilot': 'pilot'}
TIER_LABEL = {'full': 'Full', 'pilot': 'Pilot'}
POLARITIES = {'positive', 'negative'}


def validate_fixture(data):
    """Fail loudly if the fixture does not have exactly the expected instruments and item counts."""
    instruments = data.get('instruments')
    if not isinstance(instruments, list):
        raise CommandError('Fixture has no "instruments" list.')

    seen = {}
    for inst in instruments:
        key = (inst['instrument_code'], inst['package_tier'])
        if key in seen:
            raise CommandError(f'Duplicate instrument in fixture: {key}')
        seen[key] = inst

    expected_keys = {(c, 'full') for c in EXPECTED_FULL} | {(c, 'pilot') for c in EXPECTED_PILOT}
    if set(seen) != expected_keys:
        raise CommandError(
            f'Fixture instruments do not match expected set. Missing: {sorted(expected_keys - set(seen))}; '
            f'unexpected: {sorted(set(seen) - expected_keys)}'
        )

    errors = []
    for (code, tier), inst in seen.items():
        expected = (EXPECTED_FULL if tier == 'full' else EXPECTED_PILOT)[code]
        expected_version = FULL_VERSION if tier == 'full' else EXPECTED_PILOT_VERSIONS[code]
        items = inst['items']
        label = f'{code} {tier}'
        if len(items) != expected:
            errors.append(f'{label}: expected {expected} items, found {len(items)}')
        if inst['version'] != expected_version:
            errors.append(f'{label}: expected version {expected_version}, found {inst["version"]}')
        if [i['item_number'] for i in items] != list(range(1, len(items) + 1)):
            errors.append(f'{label}: item numbers are not 1..{len(items)}')
        letter = 'F' if tier == 'full' else 'P'
        for item in items:
            if item['item_code'] != f'{code}-{letter}-{item["item_number"]:02d}':
                errors.append(f'{label}: bad item_code {item["item_code"]}')
            if item['polarity'] not in POLARITIES:
                errors.append(f'{item["item_code"]}: bad polarity {item["polarity"]!r}')
            if not item['text'].strip() or not item['dimension']:
                errors.append(f'{item["item_code"]}: missing text or dimension')
        numeric = [o['numeric_value'] for o in inst['options'] if not o['is_not_applicable']]
        if numeric != [1, 2, 3, 4, 5]:
            errors.append(f'{label}: options must be numeric 1-5, found {numeric}')
        has_na = any(o['is_not_applicable'] for o in inst['options'])
        if has_na != (inst['na_option'] != 'none'):
            errors.append(f'{label}: N/A option does not match na_option={inst["na_option"]}')

    # pilot construct keys must point at a real full item, and share its dimension and polarity
    full_items = {i['item_code']: i for (c, t), inst in seen.items() if t == 'full' for i in inst['items']}
    for (code, tier), inst in seen.items():
        if tier != 'pilot':
            continue
        for item in inst['items']:
            full = full_items.get(item['construct_key'])
            if full is None or not item['construct_key'].startswith(f'{code}-F-'):
                errors.append(f'{item["item_code"]}: construct_key {item["construct_key"]} is not a {code} full item')
            elif (full['dimension'], full['polarity']) != (item['dimension'], item['polarity']):
                errors.append(f'{item["item_code"]}: dimension/polarity differ from {item["construct_key"]}')
    for (code, tier), inst in seen.items():
        if tier == 'full':
            for item in inst['items']:
                if item['construct_key'] != item['item_code']:
                    errors.append(f'{item["item_code"]}: full items must use their own code as construct_key')

    full_total = sum(len(i['items']) for (c, t), i in seen.items() if t == 'full')
    pilot_total = sum(len(i['items']) for (c, t), i in seen.items() if t == 'pilot')
    if (full_total, pilot_total) != (100, 47):
        errors.append(f'Expected 100 full + 47 pilot items, found {full_total} + {pilot_total}')

    if errors:
        raise CommandError('Fixture validation failed:\n  ' + '\n  '.join(errors))
    return seen


def form_fields(inst):
    code, tier = inst['instrument_code'], inst['package_tier']
    return {
        'title': f'{inst["instrument_name"]} ({code}) – {TIER_LABEL[tier]}',
        'description': inst['intro'],
        'form_type': 'assessment',
        'type': TIER_TO_TYPE[tier],
        'code': code,
        'order': ORDER_BASE + INSTRUMENT_ORDER.index(code) + 1,
        'instrument_code': code,
        'instrument_name': inst['instrument_name'],
        'version': inst['version'],
        'respondent_role': inst['respondent_role'],
        'reference_period': inst['reference_period'],
        'instructions': f'Who should complete this: {inst["who_should_complete"]}\n\n{inst["how_to_respond"]}',
        'privacy_notice': inst['privacy_notice'],
        'scale_type': inst['scale_type'],
        'na_option': inst['na_option'],
        'is_attributable': inst['is_attributable'],
    }


def question_fields(item):
    return {
        'question_text': item['text'],
        'question_type': 'likert',
        'required': True,
        'order': item['item_number'],
        'reverse_scored': False,
        'min_value': 1,
        'max_value': 5,
        'item_number': item['item_number'],
        'item_code': item['item_code'],
        'dimension': item['dimension'],
        'construct_key': item['construct_key'],
        'polarity': item['polarity'],
    }


def option_rows(inst):
    return [
        (o['label'], o['numeric_value'] or 0, o['numeric_value'], o['is_not_applicable'])
        for o in inst['options']
    ]


FORM_FIELD_NAMES = [
    'title', 'description', 'form_type', 'type', 'code', 'order', 'instrument_code', 'instrument_name', 'version',
    'respondent_role', 'reference_period', 'instructions', 'privacy_notice', 'scale_type', 'na_option', 'is_attributable',
]
QUESTION_FIELD_NAMES = [
    'question_text', 'question_type', 'required', 'order', 'reverse_scored', 'min_value', 'max_value',
    'item_number', 'item_code', 'dimension', 'construct_key', 'polarity',
]


def desired_snapshot(inst):
    return {
        'form': form_fields(inst),
        'questions': [
            {**question_fields(item), 'options': option_rows(inst)} for item in inst['items']
        ],
    }


def current_snapshot(form):
    form_snapshot = {name: getattr(form, name) for name in FORM_FIELD_NAMES}
    questions = []
    for q in form.questions.order_by('order', 'id'):
        row = {name: getattr(q, name) for name in QUESTION_FIELD_NAMES}
        row['options'] = [
            (o.value, o.score, o.numeric_value, o.is_not_applicable) for o in q.options.order_by('id')
        ]
        questions.append(row)
    return {'form': form_snapshot, 'questions': questions}


class Command(BaseCommand):
    help = (
        'Creates or updates the 14 EFIOVA forms (7 full + 7 pilot) from forms/fixtures/efiova/instruments.json. '
        'Idempotent; refuses to change any form that already has submissions.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--fixture', default=str(FIXTURE_PATH), help='Path to the instruments fixture.')
        parser.add_argument('--created-by', help='Email of the user recorded as form creator (default: first admin).')

    def handle(self, *args, **options):
        path = Path(options['fixture'])
        if not path.exists():
            raise CommandError(f'Fixture not found: {path}')
        data = json.loads(path.read_text(encoding='utf-8'))
        instruments = validate_fixture(data)

        creator = self._creator(options.get('created_by'))

        counts = {'created': 0, 'updated': 0, 'unchanged': 0}
        # One transaction: if any form is refused, nothing is written.
        with transaction.atomic():
            for code in INSTRUMENT_ORDER:
                for tier in ('full', 'pilot'):
                    outcome = self._sync(instruments[(code, tier)], creator)
                    counts[outcome] += 1

        self.stdout.write(self.style.SUCCESS(
            f'EFIOVA seed complete: {counts["created"]} created, {counts["updated"]} updated, '
            f'{counts["unchanged"]} unchanged.'
        ))

    def _creator(self, email):
        if email:
            user = User.objects.filter(email=email).first()
            if not user:
                raise CommandError(f'No user with email {email}.')
            return user
        user = User.objects.filter(role='admin').order_by('id').first()
        if not user:
            raise CommandError('No admin user exists. Create one or pass --created-by <email>.')
        return user

    def _sync(self, inst, creator):
        code, tier = inst['instrument_code'], inst['package_tier']
        label = f'{code} v{inst["version"]} ({tier})'
        form = Form.objects.filter(
            instrument_code=code, version=inst['version'], type=TIER_TO_TYPE[tier]
        ).first()
        desired = desired_snapshot(inst)

        if form is None:
            self._write(None, desired, creator)
            self.stdout.write(f'  created   {label}')
            return 'created'

        if current_snapshot(form) == desired:
            self.stdout.write(f'  unchanged {label}')
            return 'unchanged'

        if form.has_submissions():
            raise CommandError(
                f'{label} already has submissions and differs from the fixture. Refusing to change it. '
                'Publish the change as a new version instead.'
            )
        self._write(form, desired, creator)
        self.stdout.write(f'  updated   {label}')
        return 'updated'

    def _write(self, form, desired, creator):
        if form is None:
            form = Form.objects.create(created_by=creator, **desired['form'])
        else:
            for name, value in desired['form'].items():
                setattr(form, name, value)
            form.save()
            form.questions.all().delete()  # safe: the form has no submissions

        for row in desired['questions']:
            row = dict(row)
            options = row.pop('options')
            question = Question.objects.create(form=form, **row)
            QuestionOption.objects.bulk_create([
                QuestionOption(question=question, value=v, score=s, numeric_value=n, is_not_applicable=na)
                for v, s, n, na in options
            ])
