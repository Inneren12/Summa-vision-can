import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/features/kpi/domain/kpi_data.dart';

/// Full KPI JSON matching the backend KPIResponse schema.
const _fullJson = <String, dynamic>{
  'total_publications': 45,
  'published_count': 42,
  'draft_count': 3,
  'total_leads': 156,
  'b2b_leads': 38,
  'education_leads': 12,
  'isp_leads': 8,
  'b2c_leads': 98,
  'esp_synced_count': 140,
  'esp_failed_permanent_count': 4,
  'emails_sent': 120,
  'tokens_created': 120,
  'tokens_activated': 89,
  'tokens_exhausted': 12,
  'total_jobs': 156,
  'jobs_succeeded': 142,
  'jobs_failed': 8,
  'jobs_queued': 3,
  'jobs_running': 1,
  'failed_by_type': {'graphics_generate': 3, 'cube_fetch': 4, 'catalog_sync': 1},
  'catalog_syncs': 28,
  'data_contract_violations': 2,
  'period_start': '2026-03-13T00:00:00.000Z',
  'period_end': '2026-04-12T00:00:00.000Z',
};

void main() {
  group('KPIData.fromJson', () {
    test('parses full JSON with all fields including failedByType map', () {
      final data = KPIData.fromJson(_fullJson);

      expect(data.totalPublications, 45);
      expect(data.publishedCount, 42);
      expect(data.draftCount, 3);
      expect(data.totalLeads, 156);
      expect(data.b2bLeads, 38);
      expect(data.educationLeads, 12);
      expect(data.ispLeads, 8);
      expect(data.b2cLeads, 98);
      expect(data.espSyncedCount, 140);
      expect(data.espFailedPermanentCount, 4);
      expect(data.emailsSent, 120);
      expect(data.tokensCreated, 120);
      expect(data.tokensActivated, 89);
      expect(data.tokensExhausted, 12);
      expect(data.totalJobs, 156);
      expect(data.jobsSucceeded, 142);
      expect(data.jobsFailed, 8);
      expect(data.jobsQueued, 3);
      expect(data.jobsRunning, 1);
      expect(data.catalogSyncs, 28);
      expect(data.dataContractViolations, 2);
      expect(data.periodStart, DateTime.utc(2026, 3, 13));
      expect(data.periodEnd, DateTime.utc(2026, 4, 12));

      // Map field
      expect(data.failedByType, isA<Map<String, int>>());
      expect(data.failedByType['graphics_generate'], 3);
      expect(data.failedByType['cube_fetch'], 4);
      expect(data.failedByType['catalog_sync'], 1);
      expect(data.failedByType.length, 3);
    });

    test('parses with empty failed_by_type map', () {
      final json = Map<String, dynamic>.from(_fullJson);
      json['failed_by_type'] = <String, dynamic>{};

      final data = KPIData.fromJson(json);

      expect(data.failedByType, isEmpty);
      expect(data.failedByType, isA<Map<String, int>>());
    });
  });

  group('KPIData.toJson', () {
    test('round-trips through JSON', () {
      final original = KPIData.fromJson(_fullJson);
      final json = original.toJson();
      final restored = KPIData.fromJson(json);

      expect(restored, equals(original));
    });
  });
}
