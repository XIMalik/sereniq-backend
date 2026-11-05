from datetime import timedelta

from django.db.models import ProtectedError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from users.permissions import IsAdmin, IsStaffOrAdmin
from .exports import build_rows, write_csv
from .models import AccessKey, AssessmentCampaign, Form, Organisation
from .scoring import (
    SCORING_CONFIG, ReportSuppressed, aggregate_campaign_form, aggregate_organisation_form, compare_tiers,
)
from .serializers import AssessmentCampaignSerializer, BulkAccessKeySerializer, OrganisationSerializer

ATTRIBUTABLE_ADMIN_ONLY = 'Results for this instrument are attributable and visible to administrators only.'


def _is_admin(user):
    return user.is_authenticated and user.role == 'admin'


class OrganisationViewSet(viewsets.ModelViewSet):
    queryset = Organisation.objects.all()
    serializer_class = OrganisationSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'results'):
            return [IsStaffOrAdmin()]
        return [IsAdmin()]

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            from rest_framework.exceptions import ValidationError
            raise ValidationError('This organisation has campaigns and cannot be deleted.')

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Organisation-wide total for one form (?form=<id>) across all its campaigns. No group breakdown."""
        organisation = self.get_object()
        form = get_object_or_404(Form.objects.exclude(instrument_code=''), pk=request.query_params.get('form'))
        if form.is_attributable and not _is_admin(request.user):
            return Response({'error': ATTRIBUTABLE_ADMIN_ONLY}, status=status.HTTP_403_FORBIDDEN)
        return Response(aggregate_organisation_form(organisation, form))


class CampaignViewSet(viewsets.ModelViewSet):
    queryset = AssessmentCampaign.objects.select_related('organisation').prefetch_related('forms')
    serializer_class = AssessmentCampaignSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy', 'issue_keys'):
            return [IsAdmin()]
        return [IsStaffOrAdmin()]

    def get_queryset(self):
        queryset = super().get_queryset()
        organisation = self.request.query_params.get('organisation')
        if organisation:
            queryset = queryset.filter(organisation_id=organisation)
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            from rest_framework.exceptions import ValidationError
            raise ValidationError('This campaign has submissions and cannot be deleted.')

    # ---- access keys ----

    @action(detail=True, methods=['get', 'post'], url_path='access-keys')
    def issue_keys(self, request, pk=None):
        """
        POST: bulk-issue single-use keys for one form (+ optional group label).
        GET: list keys with used/unused status only. Used timestamps are deliberately not exposed.
        """
        campaign = self.get_object()
        if request.method == 'GET':
            keys = campaign.access_keys.select_related('form')
            return Response([
                {'key': str(k.key), 'form': k.form_id, 'instrument_code': k.form.instrument_code,
                 'group_label': k.group_label, 'used': k.used_at is not None, 'expires_at': k.expires_at}
                for k in keys
            ])

        if not _is_admin(request.user):
            return Response({'detail': 'Admin only.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = BulkAccessKeySerializer(data=request.data, context={'campaign': campaign})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        expires_at = timezone.now() + timedelta(days=data['expires_in_days']) if data['expires_in_days'] else None
        keys = AccessKey.objects.bulk_create([
            AccessKey(
                campaign=campaign, form=data['form'], group_label=data['group_label'], is_single_use=True,
                company_name=campaign.organisation.name, expires_at=expires_at,
                has_pilot_access=campaign.package_tier == 'pilot', has_sub_access=campaign.package_tier == 'full',
            )
            for _ in range(data['count'])
        ])
        return Response(
            {'count': len(keys), 'form': data['form'].id, 'group_label': data['group_label'],
             'keys': [str(k.key) for k in keys]},
            status=status.HTTP_201_CREATED)

    # ---- reporting ----

    def _forms_for_request(self, request, campaign):
        form_id = request.query_params.get('form')
        if form_id:
            return [get_object_or_404(campaign.forms, pk=form_id)]
        return list(campaign.forms.order_by('order'))

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Aggregate results per form and group, with small-group suppression. Optional ?form=<id>."""
        campaign = self.get_object()
        explicit = bool(request.query_params.get('form'))
        results = []
        for form in self._forms_for_request(request, campaign):
            if form.is_attributable and not _is_admin(request.user):
                if explicit:
                    return Response({'error': ATTRIBUTABLE_ADMIN_ONLY}, status=status.HTTP_403_FORBIDDEN)
                results.append({'form': {'id': form.id, 'instrument_code': form.instrument_code},
                                'attributable': True, 'restricted': True, 'reason': ATTRIBUTABLE_ADMIN_ONLY})
                continue
            results.append(aggregate_campaign_form(campaign, form))
        return Response({
            'scoring_status': SCORING_CONFIG['status'],
            'campaign': {'id': campaign.id, 'name': campaign.name, 'package_tier': campaign.package_tier,
                         'organisation': campaign.organisation.name},
            'results': results,
        })

    @action(detail=True, methods=['get'])
    def compare(self, request, pk=None):
        """Compare this campaign with a campaign of the other tier: ?with=<campaign id>&instrument=<code>."""
        campaign = self.get_object()
        other = get_object_or_404(AssessmentCampaign, pk=request.query_params.get('with'))
        code = request.query_params.get('instrument', '')
        if campaign.package_tier == other.package_tier:
            return Response({'error': 'Compare a pilot campaign with a full campaign.'}, status=status.HTTP_400_BAD_REQUEST)
        pilot_campaign, full_campaign = (campaign, other) if campaign.package_tier == 'pilot' else (other, campaign)
        pilot_form = get_object_or_404(pilot_campaign.forms, instrument_code=code)
        full_form = get_object_or_404(full_campaign.forms, instrument_code=code)
        if pilot_form.is_attributable and not _is_admin(request.user):
            return Response({'error': ATTRIBUTABLE_ADMIN_ONLY}, status=status.HTTP_403_FORBIDDEN)
        return Response(compare_tiers(
            pilot_form, aggregate_campaign_form(pilot_campaign, pilot_form),
            full_form, aggregate_campaign_form(full_campaign, full_form)))

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """Anonymised raw answers as CSV for one form (?form=<id>). No key or submission identifiers."""
        campaign = self.get_object()
        form = get_object_or_404(campaign.forms, pk=request.query_params.get('form'))
        if form.is_attributable and not _is_admin(request.user):
            return Response({'error': ATTRIBUTABLE_ADMIN_ONLY}, status=status.HTTP_403_FORBIDDEN)
        try:
            header, rows = build_rows(campaign, form)
        except ReportSuppressed as exc:
            return Response({'error': str(exc)}, status=status.HTTP_409_CONFLICT)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{form.instrument_code}_{form.version}_campaign_{campaign.pk}.csv"'
        write_csv(response, header, rows)
        return response
