# EFIOVA assessment instruments

EFIOVA instruments are delivered through the existing `forms` app. Everything is additive: legacy forms,
submissions and access keys behave as before.

## Models (`forms/models.py`)

| Model | Purpose |
|---|---|
| `Form` | One instrument at one version and tier. New fields: `instrument_code` (EPA, WDAI, OCEI, CRI, CPDA, EILL, ESS), `instrument_name`, `version`, `respondent_role`, `reference_period`, `instructions`, `privacy_notice`, `scale_type`, `na_option`, `is_attributable`. A form is EFIOVA when `instrument_code` is set. Tier is `Form.type` (`sub` = full, `pilot`); `package_tier` is derived from it. Unique on `(instrument_code, version, type)`. |
| `Question` | Adds `item_number`, `item_code` (e.g. `EPA-F-03`, `EPA-P-02`), `dimension`, `construct_key` (the FULL item code, shared by a pilot item and its full equivalent), `polarity`. |
| `QuestionOption` | Per question. Adds `numeric_value` (1-5, NULL for N/A) and `is_not_applicable`. |
| `Answer` | Adds `numeric_value` and `is_not_applicable`. Scoring reads only these, never `answer_text`. |
| `Organisation` | Minimal client entity (name). |
| `AssessmentCampaign` | One run for one organisation: tier, forms, dates, status, `min_group_size` (default 5), `group_labels` (JSON list), optional `pilot_request` link. |
| `AccessKey` | Adds `campaign`, `form`, `group_label`, `is_single_use`, `used_at`. |
| `Submission` | Adds `campaign`, `group_label`, `process_name` (CPDA only), `consent_acknowledged`. |

**Version freeze.** Once an EFIOVA form has submissions, its questions, options, and core fields cannot be
changed or deleted (model layer, API returns 409, admin is read-only). Publish a change as a new `Form`
with a new `version`. Bulk `QuerySet.update()` and raw SQL bypass this.

## Seeding

```
python manage.py migrate
python manage.py seed_efiova [--created-by admin@example.com]
```

Creates or updates 14 forms (7 full v2.1, 7 pilot) from `forms/fixtures/efiova/instruments.json`.
- Fails loudly unless counts match: full 10/18/12/18/12/18/12 = 100, pilot 7/6/8/6/8/6/6 = 47 (expected
  counts and versions are hardcoded in the command, not read from the fixture).
- Idempotent: unchanged forms are not touched. Runs in one transaction.
- Refuses to change a form that already has submissions (publish a new version instead).
- Forms are `form_type='assessment'`, `order` 101-107. "Who should complete this" is stored at the top of `instructions`.

The fixture wording was transcribed from the PDF packages. 17 of the 47 pilot items are worded slightly
differently from the full item they map to (see `wording_identical` in comparison output).

## Endpoints (token auth)

| Endpoint | Access |
|---|---|
| `/api/organisations/` (CRUD), `/api/organisations/{id}/results/?form=` | read: staff/admin, write: admin |
| `/api/campaigns/` (CRUD) | read: staff/admin, write: admin |
| `POST /api/campaigns/{id}/access-keys/` `{form, count<=500, group_label?, expires_in_days?}` | admin; issues single-use keys |
| `GET /api/campaigns/{id}/access-keys/` | admin; used/unused only, no timestamps |
| `GET /api/campaigns/{id}/results/?form=` | staff/admin |
| `GET /api/campaigns/{id}/compare/?with=<campaign>&instrument=<code>` | staff/admin; pilot vs full |
| `GET /api/campaigns/{id}/export/?form=` | staff/admin; anonymised CSV |

CPDA and EILL are **attributable**: their results, comparison and export are admin-only and labelled.

**Not implemented:** the public key-based respondent API (`/api/assessments/{key}/` and `/submit/`, Phase 3)
was deferred. Until it exists, nothing writes consent-checked EFIOVA submissions, and the legacy
`/api/forms/{id}/submit/` refuses EFIOVA forms. Campaign keys are also not yet restricted to their own
campaign in the legacy `/api/forms/` listing.

Existing quirk (unchanged): `FormViewSet` only finds forms the `X-ACCESS-KEY` header grants, even for admins.

## Privacy

- `Submission` has no key, IP or user-agent field. `submitted_by` is forced to NULL for non-attributable forms.
- Submission timestamps of non-attributable forms are coarsened to the day; keys expose only used/unused.
- No per-individual score is computed or exposed. Per-respondent dimension means exist only transiently
  while aggregating.
- Small groups (n < `min_group_size`) are suppressed with no numbers and pooled into the total.
  **Complementary suppression** hides the smallest visible group too when the pooled suppressed groups
  would otherwise be recoverable as `total - visible`. Applied at submission level and again for every
  item and dimension.
- CSV export: no ids, shuffled rows, month not day, small groups pooled as `SUPPRESSED`, 409 if the total is
  too small, spreadsheet-formula text neutralised.
- Limitation: the organisation-wide total is not reconciled with separately requested campaign reports;
  someone holding both could subtract one from the other. It uses the strictest `min_group_size` involved.
- Limitation: CPDA `process_name` is exported as given (attributable, admin-only form).

## Scoring: PROVISIONAL

All rules are placeholders until Sereniq supplies the official methodology, and every computed output carries
`"scoring_status": "provisional"`. They live in `SCORING_CONFIG` in `forms/scoring.py`.

- Item risk: negative polarity = raw value; positive polarity = 6 - raw. Higher = more risk. N/A excluded.
- Polarity: agreement items positive except EPA full 3, 7 and pilot 2, 5 (negative); all frequency items
  (WDAI, OCEI, CPDA) negative; CRI "do not" items stay positive.
- Dimension score (per respondent, internal only) = mean of answered items; null if < 50% of the dimension's
  items were answered.
- Aggregates per campaign x form x group, and total: `n`, `mean`, sample `sd`, response distribution,
  `na_count`, `pct_unfavourable` (risk >= 4). Dimension aggregates also report `insufficient_answers`.
- Dimension and item-to-dimension mapping, and the pilot-to-full item mapping, are in the fixture.
- Cross-tier comparison matches by `construct_key` and dimension and flags: versions differ (v1.x vs v2.1),
  pilot reference periods are looser, pilot dimensions use fewer items, and per-item `wording_identical`.
