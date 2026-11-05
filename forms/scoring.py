"""
EFIOVA scoring and aggregate reporting.

PROVISIONAL: every rule below is a placeholder until Sereniq supplies the official scoring
methodology. All tunable values live in SCORING_CONFIG so they can be changed in one place.

Privacy:
  * No per-individual score is ever returned or stored. Per-respondent dimension scores exist only
    as an intermediate inside `_cell_stats` and are reduced to aggregates before leaving it.
  * Groups smaller than the campaign's min_group_size are suppressed (no numbers at all) and pooled
    into the next level up. Complementary suppression stops a suppressed cell being recovered by
    subtracting visible cells from the total (see `plan_suppression`).
"""
import statistics
from collections import defaultdict

from .models import Answer, Submission

SCORING_CONFIG = {
    'status': 'provisional',
    # Raw answers are 1..scale_max. Positive-polarity items are reversed (scale_max + 1 - raw)
    # so that a higher score always means more risk.
    'scale_max': 5,
    # An item/respondent dimension score at or above this risk score counts as "unfavourable".
    'unfavourable_threshold': 4,
    # A respondent's dimension score is null unless at least this share of the dimension's items was answered.
    'min_answered_fraction': 0.5,
}

UNASSIGNED = '(unassigned)'
NA = 'NA'  # sentinel for a "not applicable" answer inside the in-memory response dicts

REASON_SMALL = 'below_min_group_size'
REASON_COMPLEMENTARY = 'complementary_suppression'


class ReportSuppressed(Exception):
    """The whole result set is too small to release."""


# ---- Item and dimension scoring ---------------------------------------------------------------

def item_risk_score(polarity, raw):
    """Risk score for one answer. Higher always means more risk; N/A (None) is excluded."""
    if raw is None:
        return None
    if polarity == 'negative':
        return raw
    if polarity == 'positive':
        return SCORING_CONFIG['scale_max'] + 1 - raw
    raise ValueError(f'Unknown polarity {polarity!r}')


def dimension_score(risk_scores, total_items):
    """Mean of the answered items' risk scores, or None if too few of the dimension's items were answered."""
    answered = [r for r in risk_scores if r is not None]
    if not total_items or len(answered) < SCORING_CONFIG['min_answered_fraction'] * total_items:
        return None
    return sum(answered) / len(answered)


# ---- Suppression ------------------------------------------------------------------------------

def plan_suppression(group_n, min_size, forced=()):
    """
    Decide which cells may be shown.

    group_n: {cell: n}. Returns (suppressed_cells, reasons, total_suppressed).

    1. Cells with 0 < n < min_size are suppressed (plus any `forced` cells).
    2. Complementary suppression: the total is released alongside the visible cells, so the pooled
       suppressed cells could be recovered as total - sum(visible). If that residual is smaller than
       min_size, the smallest visible cell is also suppressed, repeatedly, until the residual is large
       enough to be a safe pooled figure.
    3. The total is suppressed if it is itself smaller than min_size.
    """
    sizes = {g: n for g, n in group_n.items() if n > 0}
    suppressed = {g for g, n in sizes.items() if n < min_size} | {g for g in forced if g in sizes}
    reasons = {g: REASON_SMALL for g in suppressed}

    def residual():
        return sum(sizes[g] for g in suppressed)

    while suppressed and residual() < min_size:
        candidates = [g for g in sizes if g not in suppressed]
        if not candidates:
            break
        smallest = min(candidates, key=lambda g: (sizes[g], str(g)))
        suppressed.add(smallest)
        reasons[smallest] = REASON_COMPLEMENTARY

    total_suppressed = sum(sizes.values()) < min_size
    return suppressed, reasons, total_suppressed


# ---- Cell statistics --------------------------------------------------------------------------

def _round(value, places=2):
    return None if value is None else round(value, places)


def _item_stats(question, answers):
    """answers: list of raw ints, or NA. Missing answers are simply absent."""
    raws = [a for a in answers if a != NA]
    na_count = sum(1 for a in answers if a == NA)
    risks = [item_risk_score(question.polarity, r) for r in raws]
    n = len(raws)
    threshold = SCORING_CONFIG['unfavourable_threshold']
    return {
        'n': n,
        'mean': _round(statistics.fmean(risks)) if n else None,
        'sd': _round(statistics.stdev(risks)) if n > 1 else None,
        'distribution': {str(v): raws.count(v) for v in range(1, SCORING_CONFIG['scale_max'] + 1)},
        'na_count': na_count,
        'pct_unfavourable': _round(100 * sum(1 for r in risks if r >= threshold) / n, 1) if n else None,
    }


def _dimension_stats(scores, na_count, insufficient):
    n = len(scores)
    top = SCORING_CONFIG['scale_max']
    distribution = {str(v): 0 for v in range(1, top + 1)}
    for s in scores:
        distribution[str(min(top, max(1, int(s + 0.5))))] += 1
    threshold = SCORING_CONFIG['unfavourable_threshold']
    return {
        'n': n,
        'mean': _round(statistics.fmean(scores)) if n else None,
        'sd': _round(statistics.stdev(scores)) if n > 1 else None,
        'distribution': distribution,  # respondents by rounded dimension risk score
        'na_count': na_count,
        'insufficient_answers': insufficient,
        'pct_unfavourable': _round(100 * sum(1 for s in scores if s >= threshold) / n, 1) if n else None,
    }


def _cell_stats(questions, dimensions, responses):
    """
    Aggregate statistics for one cell (a group, or the total).

    questions: ordered list of Question. dimensions: {dimension: [Question, ...]}.
    responses: list of {question_id: raw int | NA}, one per submission.
    Per-respondent dimension scores are computed here and discarded; only aggregates are returned.
    """
    items = {q.id: _item_stats(q, [r[q.id] for r in responses if q.id in r]) for q in questions}

    dims = {}
    for name, dim_questions in dimensions.items():
        scores, na_count, insufficient = [], 0, 0
        for r in responses:
            risks = []
            for q in dim_questions:
                value = r.get(q.id)
                if value == NA:
                    na_count += 1
                elif value is not None:
                    risks.append(item_risk_score(q.polarity, value))
            score = dimension_score(risks, len(dim_questions))
            if score is None:
                insufficient += 1
            else:
                scores.append(score)
        dims[name] = _dimension_stats(scores, na_count, insufficient)
    return {'items': items, 'dimensions': dims}


# ---- Data loading -----------------------------------------------------------------------------

def load_responses(form, submissions):
    """Return {group_label: [ {question_id: raw | NA}, ... ]} for the submissions of `form`."""
    submissions = submissions.filter(form=form)
    by_id = {}
    groups = defaultdict(list)
    for sid, label in submissions.values_list('id', 'group_label'):
        response = {}
        by_id[sid] = response
        groups[label].append(response)
    rows = Answer.objects.filter(submission_id__in=by_id.keys()).values_list(
        'submission_id', 'question_id', 'numeric_value', 'is_not_applicable')
    for sid, qid, value, is_na in rows:
        if is_na:
            by_id[sid][qid] = NA
        elif value is not None:
            by_id[sid][qid] = value
    return groups


# ---- Aggregation ------------------------------------------------------------------------------

def _suppressed_entry(reason, **extra):
    return {'suppressed': True, 'reason': reason, **extra}


def aggregate(form, responses_by_group, min_size, include_groups=True):
    """
    Aggregate responses for one form, per group and in total, applying small-group suppression.

    Returns a dict with `scoring_status: provisional`. Suppressed cells carry no numbers at all.
    """
    questions = list(form.questions.order_by('item_number', 'order'))
    dimensions = {}
    for q in questions:
        if q.dimension:
            dimensions.setdefault(q.dimension, []).append(q)

    all_responses = [r for rs in responses_by_group.values() for r in rs]
    group_stats = {g: _cell_stats(questions, dimensions, rs) for g, rs in responses_by_group.items()}
    total_stats = _cell_stats(questions, dimensions, all_responses)

    sub_suppressed, sub_reasons, total_sub_suppressed = plan_suppression(
        {g: len(rs) for g, rs in responses_by_group.items()}, min_size)

    # one suppression plan per metric, so item- and dimension-level cells are protected too
    plans = {}
    for q in questions:
        plans[('items', q.id)] = plan_suppression(
            {g: s['items'][q.id]['n'] for g, s in group_stats.items()}, min_size, forced=sub_suppressed)
    for name in dimensions:
        plans[('dimensions', name)] = plan_suppression(
            {g: s['dimensions'][name]['n'] for g, s in group_stats.items()}, min_size, forced=sub_suppressed)

    def item_meta(q):
        return {'item_code': q.item_code, 'item_number': q.item_number, 'dimension': q.dimension,
                'construct_key': q.construct_key, 'polarity': q.polarity}

    def render(stats, group=None):
        """Render items and dimensions for one cell (group=None means the total)."""
        items, dims = [], []
        for q in questions:
            supp, reasons, total_supp = plans[('items', q.id)]
            if group is None:
                hidden, reason = total_supp, REASON_SMALL
            else:
                hidden, reason = group in supp, reasons.get(group)
            items.append({**item_meta(q), **(_suppressed_entry(reason) if hidden else stats['items'][q.id])})
        for name, dim_questions in dimensions.items():
            supp, reasons, total_supp = plans[('dimensions', name)]
            if group is None:
                hidden, reason = total_supp, REASON_SMALL
            else:
                hidden, reason = group in supp, reasons.get(group)
            dims.append({
                'dimension': name, 'item_count': len(dim_questions),
                **(_suppressed_entry(reason) if hidden else stats['dimensions'][name]),
            })
        return {'items': items, 'dimensions': dims}

    result = {
        'scoring_status': SCORING_CONFIG['status'],
        'form': {
            'id': form.id, 'instrument_code': form.instrument_code, 'instrument_name': form.instrument_name,
            'version': form.version, 'package_tier': form.package_tier, 'reference_period': form.reference_period,
        },
        'attributable': form.is_attributable,
        'min_group_size': min_size,
    }
    if form.is_attributable:
        result['attributable_notice'] = (
            'The respondent pool for this instrument is small, so responses may be identifiable. '
            'Results are restricted to administrators.')

    if total_sub_suppressed:
        result['total'] = _suppressed_entry(REASON_SMALL)
    else:
        result['total'] = {'suppressed': False, 'n_submissions': len(all_responses), **render(total_stats)}

    if include_groups:
        groups = []
        for label in sorted(responses_by_group, key=lambda g: (g == '', g)):
            display = label or UNASSIGNED
            if label in sub_suppressed:
                groups.append({'group_label': display, **_suppressed_entry(sub_reasons[label])})
            else:
                groups.append({
                    'group_label': display, 'suppressed': False,
                    'n_submissions': len(responses_by_group[label]),
                    **render(group_stats[label], group=label),
                })
        result['groups'] = groups
    return result


def aggregate_campaign_form(campaign, form):
    submissions = Submission.objects.filter(campaign=campaign)
    return aggregate(form, load_responses(form, submissions), campaign.min_group_size)


def aggregate_organisation_form(organisation, form):
    """
    Organisation-wide total for one form across all of the organisation's campaigns (no group breakdown).

    Limitation: this total is not reconciled with separately requested campaign reports. Someone
    holding both could subtract a campaign's visible total from this one to learn about the other
    campaigns. The threshold used is the strictest min_group_size among the contributing campaigns.
    """
    submissions = Submission.objects.filter(campaign__organisation=organisation)
    min_size = max(
        [c.min_group_size for c in organisation.campaigns.filter(submissions__form=form).distinct()] or [5])
    responses = load_responses(form, submissions)
    pooled = {'': [r for rs in responses.values() for r in rs]}
    return aggregate(form, pooled, min_size, include_groups=False)


# ---- Cross-tier comparison --------------------------------------------------------------------

def compare_tiers(pilot_form, pilot_result, full_form, full_result):
    """
    Compare a pilot result with a full-version result of the same instrument via construct_key and
    dimension. Uses campaign totals only. Suppressed cells on either side stay suppressed.
    """
    def pick(entry):
        if entry.get('suppressed'):
            return {'suppressed': True}
        return {k: entry[k] for k in ('n', 'mean', 'sd', 'pct_unfavourable')}

    def diff(a, b):
        if a.get('suppressed') or b.get('suppressed') or a['mean'] is None or b['mean'] is None:
            return None
        return round(a['mean'] - b['mean'], 2)

    pilot_total, full_total = pilot_result['total'], full_result['total']
    full_text = {q.item_code: q.question_text for q in full_form.questions.all()}
    pilot_by_code = {q.item_code: q for q in pilot_form.questions.all()}

    items, dimensions = [], []
    if not pilot_total['suppressed'] and not full_total['suppressed']:
        full_items = {i['item_code']: i for i in full_total['items']}
        for item in pilot_total['items']:
            full_item = full_items.get(item['construct_key'])
            if full_item is None:
                continue
            pilot, full = pick(item), pick(full_item)
            items.append({
                'construct_key': item['construct_key'],
                'dimension': item['dimension'],
                'pilot_item_code': item['item_code'],
                'wording_identical': pilot_by_code[item['item_code']].question_text == full_text.get(item['construct_key']),
                'pilot': pilot, 'full': full, 'mean_difference': diff(pilot, full),
            })
        full_dims = {d['dimension']: d for d in full_total['dimensions']}
        for dim in pilot_total['dimensions']:
            full_dim = full_dims.get(dim['dimension'])
            if full_dim is None:
                continue
            pilot, full = pick(dim), pick(full_dim)
            dimensions.append({
                'dimension': dim['dimension'],
                'items_in_pilot': dim['item_count'], 'items_in_full': full_dim['item_count'],
                'pilot': pilot, 'full': full, 'mean_difference': diff(pilot, full),
            })

    return {
        'scoring_status': SCORING_CONFIG['status'],
        'instrument_code': pilot_form.instrument_code,
        'caveats': [
            f'Versions differ: pilot v{pilot_form.version} vs full v{full_form.version}.',
            f'Reference periods differ: pilot "{pilot_form.reference_period}" vs full "{full_form.reference_period}". '
            'Pilot reference periods are looser.',
            'Pilot dimensions are built from fewer items than the full version.',
            'Items are matched by construct_key; check wording_identical, as some pilot items are worded slightly differently.',
        ],
        'pilot_total_suppressed': pilot_total['suppressed'],
        'full_total_suppressed': full_total['suppressed'],
        'items': items,
        'dimensions': dimensions,
    }
