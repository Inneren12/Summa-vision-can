import 'package:freezed_annotation/freezed_annotation.dart';

part 'kpi_data.g.dart';
part 'kpi_data.freezed.dart';

/// Domain model matching the backend [KPIResponse] schema.
///
/// All field names use `@JsonKey(name: ...)` for snake_case mapping
/// from the Python backend.
@freezed
class KPIData with _$KPIData {
  const factory KPIData({
    // Publications
    @JsonKey(name: 'total_publications') required int totalPublications,
    @JsonKey(name: 'published_count') required int publishedCount,
    @JsonKey(name: 'draft_count') required int draftCount,

    // Leads
    @JsonKey(name: 'total_leads') required int totalLeads,
    @JsonKey(name: 'b2b_leads') required int b2bLeads,
    @JsonKey(name: 'education_leads') required int educationLeads,
    @JsonKey(name: 'isp_leads') required int ispLeads,
    @JsonKey(name: 'b2c_leads') required int b2cLeads,
    @JsonKey(name: 'esp_synced_count') required int espSyncedCount,
    @JsonKey(name: 'esp_failed_permanent_count')
    required int espFailedPermanentCount,

    // Download funnel
    @JsonKey(name: 'emails_sent') required int emailsSent,
    @JsonKey(name: 'tokens_created') required int tokensCreated,
    @JsonKey(name: 'tokens_activated') required int tokensActivated,
    @JsonKey(name: 'tokens_exhausted') required int tokensExhausted,

    // Jobs
    @JsonKey(name: 'total_jobs') required int totalJobs,
    @JsonKey(name: 'jobs_succeeded') required int jobsSucceeded,
    @JsonKey(name: 'jobs_failed') required int jobsFailed,
    @JsonKey(name: 'jobs_queued') required int jobsQueued,
    @JsonKey(name: 'jobs_running') required int jobsRunning,
    @JsonKey(name: 'failed_by_type') required Map<String, int> failedByType,

    // System
    @JsonKey(name: 'catalog_syncs') required int catalogSyncs,
    @JsonKey(name: 'data_contract_violations')
    required int dataContractViolations,

    // Period
    @JsonKey(name: 'period_start') required DateTime periodStart,
    @JsonKey(name: 'period_end') required DateTime periodEnd,
  }) = _KPIData;

  factory KPIData.fromJson(Map<String, dynamic> json) =>
      _$KPIDataFromJson(json);
}
