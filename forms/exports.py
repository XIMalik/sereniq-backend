"""Anonymised raw-answer CSV export. Rows carry no submission id, key or user, and are shuffled."""
import csv
import random

from .models import Answer, Submission
from .scoring import NA, UNASSIGNED, ReportSuppressed, plan_suppression

SUPPRESSED_LABEL = 'SUPPRESSED'
_RNG = random.SystemRandom()


def _safe(value):
    """Neutralise spreadsheet formula injection in free-text cells."""
    value = str(value)
    return "'" + value if value[:1] in ('=', '+', '-', '@', '\t', '\r') else value


def build_rows(campaign, form):
    """
    One row per submission: group, (process,) month and one column per item. Groups below the
    campaign's min_group_size (and any complementary group) are pooled under SUPPRESSED. If the
    total is itself below the minimum, nothing is exported.
    """
    submissions = list(Submission.objects.filter(campaign=campaign, form=form).values('id', 'group_label', 'process_name', 'submitted_at'))
    sizes = {}
    for s in submissions:
        sizes[s['group_label']] = sizes.get(s['group_label'], 0) + 1
    suppressed, _, total_suppressed = plan_suppression(sizes, campaign.min_group_size)
    if total_suppressed:
        raise ReportSuppressed(f'Fewer than {campaign.min_group_size} submissions; nothing can be exported.')

    questions = list(form.questions.order_by('item_number', 'order'))
    include_process = form.instrument_code == 'CPDA'
    header = ['group'] + (['process'] if include_process else []) + ['submitted_month'] + [q.item_code for q in questions]

    answers = {}
    for sid, qid, value, is_na in Answer.objects.filter(submission__campaign=campaign, submission__form=form).values_list(
            'submission_id', 'question_id', 'numeric_value', 'is_not_applicable'):
        answers.setdefault(sid, {})[qid] = NA if is_na else value

    rows = []
    for s in submissions:
        label = SUPPRESSED_LABEL if s['group_label'] in suppressed else (s['group_label'] or UNASSIGNED)
        row = [_safe(label)]
        if include_process:
            row.append(_safe(s['process_name']))
        row.append(s['submitted_at'].strftime('%Y-%m'))
        row += ['' if answers.get(s['id'], {}).get(q.id) is None else answers[s['id']][q.id] for q in questions]
        rows.append(row)
    _RNG.shuffle(rows)
    return header, rows


def write_csv(response, header, rows):
    writer = csv.writer(response)
    writer.writerow(header)
    writer.writerows(rows)
