// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'kpi_data.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

KPIData _$KPIDataFromJson(Map<String, dynamic> json) {
  return _KPIData.fromJson(json);
}

/// @nodoc
mixin _$KPIData {
  @JsonKey(name: 'total_publications')
  int get totalPublications => throw _privateConstructorUsedError;
  @JsonKey(name: 'published_count')
  int get publishedCount => throw _privateConstructorUsedError;
  @JsonKey(name: 'draft_count')
  int get draftCount => throw _privateConstructorUsedError;
  @JsonKey(name: 'total_leads')
  int get totalLeads => throw _privateConstructorUsedError;
  @JsonKey(name: 'b2b_leads')
  int get b2bLeads => throw _privateConstructorUsedError;
  @JsonKey(name: 'education_leads')
  int get educationLeads => throw _privateConstructorUsedError;
  @JsonKey(name: 'isp_leads')
  int get ispLeads => throw _privateConstructorUsedError;
  @JsonKey(name: 'b2c_leads')
  int get b2cLeads => throw _privateConstructorUsedError;
  @JsonKey(name: 'esp_synced_count')
  int get espSyncedCount => throw _privateConstructorUsedError;
  @JsonKey(name: 'esp_failed_permanent_count')
  int get espFailedPermanentCount => throw _privateConstructorUsedError;
  @JsonKey(name: 'emails_sent')
  int get emailsSent => throw _privateConstructorUsedError;
  @JsonKey(name: 'tokens_created')
  int get tokensCreated => throw _privateConstructorUsedError;
  @JsonKey(name: 'tokens_activated')
  int get tokensActivated => throw _privateConstructorUsedError;
  @JsonKey(name: 'tokens_exhausted')
  int get tokensExhausted => throw _privateConstructorUsedError;
  @JsonKey(name: 'total_jobs')
  int get totalJobs => throw _privateConstructorUsedError;
  @JsonKey(name: 'jobs_succeeded')
  int get jobsSucceeded => throw _privateConstructorUsedError;
  @JsonKey(name: 'jobs_failed')
  int get jobsFailed => throw _privateConstructorUsedError;
  @JsonKey(name: 'jobs_queued')
  int get jobsQueued => throw _privateConstructorUsedError;
  @JsonKey(name: 'jobs_running')
  int get jobsRunning => throw _privateConstructorUsedError;
  @JsonKey(name: 'failed_by_type')
  Map<String, int> get failedByType => throw _privateConstructorUsedError;
  @JsonKey(name: 'catalog_syncs')
  int get catalogSyncs => throw _privateConstructorUsedError;
  @JsonKey(name: 'data_contract_violations')
  int get dataContractViolations => throw _privateConstructorUsedError;
  @JsonKey(name: 'period_start')
  DateTime get periodStart => throw _privateConstructorUsedError;
  @JsonKey(name: 'period_end')
  DateTime get periodEnd => throw _privateConstructorUsedError;

  /// Serializes this KPIData to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of KPIData
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $KPIDataCopyWith<KPIData> get copyWith => throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $KPIDataCopyWith<$Res> {
  factory $KPIDataCopyWith(
    KPIData value,
    $Res Function(KPIData) then,
  ) = _$KPIDataCopyWithImpl<$Res, KPIData>;
  @useResult
  $Res call({
    @JsonKey(name: 'total_publications') int totalPublications,
    @JsonKey(name: 'published_count') int publishedCount,
    @JsonKey(name: 'draft_count') int draftCount,
    @JsonKey(name: 'total_leads') int totalLeads,
    @JsonKey(name: 'b2b_leads') int b2bLeads,
    @JsonKey(name: 'education_leads') int educationLeads,
    @JsonKey(name: 'isp_leads') int ispLeads,
    @JsonKey(name: 'b2c_leads') int b2cLeads,
    @JsonKey(name: 'esp_synced_count') int espSyncedCount,
    @JsonKey(name: 'esp_failed_permanent_count') int espFailedPermanentCount,
    @JsonKey(name: 'emails_sent') int emailsSent,
    @JsonKey(name: 'tokens_created') int tokensCreated,
    @JsonKey(name: 'tokens_activated') int tokensActivated,
    @JsonKey(name: 'tokens_exhausted') int tokensExhausted,
    @JsonKey(name: 'total_jobs') int totalJobs,
    @JsonKey(name: 'jobs_succeeded') int jobsSucceeded,
    @JsonKey(name: 'jobs_failed') int jobsFailed,
    @JsonKey(name: 'jobs_queued') int jobsQueued,
    @JsonKey(name: 'jobs_running') int jobsRunning,
    @JsonKey(name: 'failed_by_type') Map<String, int> failedByType,
    @JsonKey(name: 'catalog_syncs') int catalogSyncs,
    @JsonKey(name: 'data_contract_violations') int dataContractViolations,
    @JsonKey(name: 'period_start') DateTime periodStart,
    @JsonKey(name: 'period_end') DateTime periodEnd,
  });
}

/// @nodoc
class _$KPIDataCopyWithImpl<$Res, $Val extends KPIData>
    implements $KPIDataCopyWith<$Res> {
  _$KPIDataCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of KPIData
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? totalPublications = null,
    Object? publishedCount = null,
    Object? draftCount = null,
    Object? totalLeads = null,
    Object? b2bLeads = null,
    Object? educationLeads = null,
    Object? ispLeads = null,
    Object? b2cLeads = null,
    Object? espSyncedCount = null,
    Object? espFailedPermanentCount = null,
    Object? emailsSent = null,
    Object? tokensCreated = null,
    Object? tokensActivated = null,
    Object? tokensExhausted = null,
    Object? totalJobs = null,
    Object? jobsSucceeded = null,
    Object? jobsFailed = null,
    Object? jobsQueued = null,
    Object? jobsRunning = null,
    Object? failedByType = null,
    Object? catalogSyncs = null,
    Object? dataContractViolations = null,
    Object? periodStart = null,
    Object? periodEnd = null,
  }) {
    return _then(
      _value.copyWith(
            totalPublications: null == totalPublications
                ? _value.totalPublications
                : totalPublications as int,
            publishedCount: null == publishedCount
                ? _value.publishedCount
                : publishedCount as int,
            draftCount:
                null == draftCount ? _value.draftCount : draftCount as int,
            totalLeads:
                null == totalLeads ? _value.totalLeads : totalLeads as int,
            b2bLeads:
                null == b2bLeads ? _value.b2bLeads : b2bLeads as int,
            educationLeads: null == educationLeads
                ? _value.educationLeads
                : educationLeads as int,
            ispLeads:
                null == ispLeads ? _value.ispLeads : ispLeads as int,
            b2cLeads:
                null == b2cLeads ? _value.b2cLeads : b2cLeads as int,
            espSyncedCount: null == espSyncedCount
                ? _value.espSyncedCount
                : espSyncedCount as int,
            espFailedPermanentCount: null == espFailedPermanentCount
                ? _value.espFailedPermanentCount
                : espFailedPermanentCount as int,
            emailsSent:
                null == emailsSent ? _value.emailsSent : emailsSent as int,
            tokensCreated: null == tokensCreated
                ? _value.tokensCreated
                : tokensCreated as int,
            tokensActivated: null == tokensActivated
                ? _value.tokensActivated
                : tokensActivated as int,
            tokensExhausted: null == tokensExhausted
                ? _value.tokensExhausted
                : tokensExhausted as int,
            totalJobs:
                null == totalJobs ? _value.totalJobs : totalJobs as int,
            jobsSucceeded: null == jobsSucceeded
                ? _value.jobsSucceeded
                : jobsSucceeded as int,
            jobsFailed:
                null == jobsFailed ? _value.jobsFailed : jobsFailed as int,
            jobsQueued:
                null == jobsQueued ? _value.jobsQueued : jobsQueued as int,
            jobsRunning:
                null == jobsRunning ? _value.jobsRunning : jobsRunning as int,
            failedByType: null == failedByType
                ? _value.failedByType
                : failedByType as Map<String, int>,
            catalogSyncs: null == catalogSyncs
                ? _value.catalogSyncs
                : catalogSyncs as int,
            dataContractViolations: null == dataContractViolations
                ? _value.dataContractViolations
                : dataContractViolations as int,
            periodStart: null == periodStart
                ? _value.periodStart
                : periodStart as DateTime,
            periodEnd: null == periodEnd
                ? _value.periodEnd
                : periodEnd as DateTime,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$KPIDataImplCopyWith<$Res>
    implements $KPIDataCopyWith<$Res> {
  factory _$$KPIDataImplCopyWith(
    _$KPIDataImpl value,
    $Res Function(_$KPIDataImpl) then,
  ) = __$$KPIDataImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    @JsonKey(name: 'total_publications') int totalPublications,
    @JsonKey(name: 'published_count') int publishedCount,
    @JsonKey(name: 'draft_count') int draftCount,
    @JsonKey(name: 'total_leads') int totalLeads,
    @JsonKey(name: 'b2b_leads') int b2bLeads,
    @JsonKey(name: 'education_leads') int educationLeads,
    @JsonKey(name: 'isp_leads') int ispLeads,
    @JsonKey(name: 'b2c_leads') int b2cLeads,
    @JsonKey(name: 'esp_synced_count') int espSyncedCount,
    @JsonKey(name: 'esp_failed_permanent_count') int espFailedPermanentCount,
    @JsonKey(name: 'emails_sent') int emailsSent,
    @JsonKey(name: 'tokens_created') int tokensCreated,
    @JsonKey(name: 'tokens_activated') int tokensActivated,
    @JsonKey(name: 'tokens_exhausted') int tokensExhausted,
    @JsonKey(name: 'total_jobs') int totalJobs,
    @JsonKey(name: 'jobs_succeeded') int jobsSucceeded,
    @JsonKey(name: 'jobs_failed') int jobsFailed,
    @JsonKey(name: 'jobs_queued') int jobsQueued,
    @JsonKey(name: 'jobs_running') int jobsRunning,
    @JsonKey(name: 'failed_by_type') Map<String, int> failedByType,
    @JsonKey(name: 'catalog_syncs') int catalogSyncs,
    @JsonKey(name: 'data_contract_violations') int dataContractViolations,
    @JsonKey(name: 'period_start') DateTime periodStart,
    @JsonKey(name: 'period_end') DateTime periodEnd,
  });
}

/// @nodoc
class __$$KPIDataImplCopyWithImpl<$Res>
    extends _$KPIDataCopyWithImpl<$Res, _$KPIDataImpl>
    implements _$$KPIDataImplCopyWith<$Res> {
  __$$KPIDataImplCopyWithImpl(
    _$KPIDataImpl _value,
    $Res Function(_$KPIDataImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of KPIData
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? totalPublications = null,
    Object? publishedCount = null,
    Object? draftCount = null,
    Object? totalLeads = null,
    Object? b2bLeads = null,
    Object? educationLeads = null,
    Object? ispLeads = null,
    Object? b2cLeads = null,
    Object? espSyncedCount = null,
    Object? espFailedPermanentCount = null,
    Object? emailsSent = null,
    Object? tokensCreated = null,
    Object? tokensActivated = null,
    Object? tokensExhausted = null,
    Object? totalJobs = null,
    Object? jobsSucceeded = null,
    Object? jobsFailed = null,
    Object? jobsQueued = null,
    Object? jobsRunning = null,
    Object? failedByType = null,
    Object? catalogSyncs = null,
    Object? dataContractViolations = null,
    Object? periodStart = null,
    Object? periodEnd = null,
  }) {
    return _then(
      _$KPIDataImpl(
        totalPublications: null == totalPublications
            ? _value.totalPublications
            : totalPublications as int,
        publishedCount: null == publishedCount
            ? _value.publishedCount
            : publishedCount as int,
        draftCount:
            null == draftCount ? _value.draftCount : draftCount as int,
        totalLeads:
            null == totalLeads ? _value.totalLeads : totalLeads as int,
        b2bLeads: null == b2bLeads ? _value.b2bLeads : b2bLeads as int,
        educationLeads: null == educationLeads
            ? _value.educationLeads
            : educationLeads as int,
        ispLeads: null == ispLeads ? _value.ispLeads : ispLeads as int,
        b2cLeads: null == b2cLeads ? _value.b2cLeads : b2cLeads as int,
        espSyncedCount: null == espSyncedCount
            ? _value.espSyncedCount
            : espSyncedCount as int,
        espFailedPermanentCount: null == espFailedPermanentCount
            ? _value.espFailedPermanentCount
            : espFailedPermanentCount as int,
        emailsSent:
            null == emailsSent ? _value.emailsSent : emailsSent as int,
        tokensCreated: null == tokensCreated
            ? _value.tokensCreated
            : tokensCreated as int,
        tokensActivated: null == tokensActivated
            ? _value.tokensActivated
            : tokensActivated as int,
        tokensExhausted: null == tokensExhausted
            ? _value.tokensExhausted
            : tokensExhausted as int,
        totalJobs:
            null == totalJobs ? _value.totalJobs : totalJobs as int,
        jobsSucceeded: null == jobsSucceeded
            ? _value.jobsSucceeded
            : jobsSucceeded as int,
        jobsFailed:
            null == jobsFailed ? _value.jobsFailed : jobsFailed as int,
        jobsQueued:
            null == jobsQueued ? _value.jobsQueued : jobsQueued as int,
        jobsRunning:
            null == jobsRunning ? _value.jobsRunning : jobsRunning as int,
        failedByType: null == failedByType
            ? _value._failedByType
            : failedByType as Map<String, int>,
        catalogSyncs: null == catalogSyncs
            ? _value.catalogSyncs
            : catalogSyncs as int,
        dataContractViolations: null == dataContractViolations
            ? _value.dataContractViolations
            : dataContractViolations as int,
        periodStart: null == periodStart
            ? _value.periodStart
            : periodStart as DateTime,
        periodEnd:
            null == periodEnd ? _value.periodEnd : periodEnd as DateTime,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$KPIDataImpl implements _KPIData {
  const _$KPIDataImpl({
    @JsonKey(name: 'total_publications') required this.totalPublications,
    @JsonKey(name: 'published_count') required this.publishedCount,
    @JsonKey(name: 'draft_count') required this.draftCount,
    @JsonKey(name: 'total_leads') required this.totalLeads,
    @JsonKey(name: 'b2b_leads') required this.b2bLeads,
    @JsonKey(name: 'education_leads') required this.educationLeads,
    @JsonKey(name: 'isp_leads') required this.ispLeads,
    @JsonKey(name: 'b2c_leads') required this.b2cLeads,
    @JsonKey(name: 'esp_synced_count') required this.espSyncedCount,
    @JsonKey(name: 'esp_failed_permanent_count')
    required this.espFailedPermanentCount,
    @JsonKey(name: 'emails_sent') required this.emailsSent,
    @JsonKey(name: 'tokens_created') required this.tokensCreated,
    @JsonKey(name: 'tokens_activated') required this.tokensActivated,
    @JsonKey(name: 'tokens_exhausted') required this.tokensExhausted,
    @JsonKey(name: 'total_jobs') required this.totalJobs,
    @JsonKey(name: 'jobs_succeeded') required this.jobsSucceeded,
    @JsonKey(name: 'jobs_failed') required this.jobsFailed,
    @JsonKey(name: 'jobs_queued') required this.jobsQueued,
    @JsonKey(name: 'jobs_running') required this.jobsRunning,
    @JsonKey(name: 'failed_by_type')
    required final Map<String, int> failedByType,
    @JsonKey(name: 'catalog_syncs') required this.catalogSyncs,
    @JsonKey(name: 'data_contract_violations')
    required this.dataContractViolations,
    @JsonKey(name: 'period_start') required this.periodStart,
    @JsonKey(name: 'period_end') required this.periodEnd,
  }) : _failedByType = failedByType;

  factory _$KPIDataImpl.fromJson(Map<String, dynamic> json) =>
      _$$KPIDataImplFromJson(json);

  @override
  @JsonKey(name: 'total_publications')
  final int totalPublications;
  @override
  @JsonKey(name: 'published_count')
  final int publishedCount;
  @override
  @JsonKey(name: 'draft_count')
  final int draftCount;
  @override
  @JsonKey(name: 'total_leads')
  final int totalLeads;
  @override
  @JsonKey(name: 'b2b_leads')
  final int b2bLeads;
  @override
  @JsonKey(name: 'education_leads')
  final int educationLeads;
  @override
  @JsonKey(name: 'isp_leads')
  final int ispLeads;
  @override
  @JsonKey(name: 'b2c_leads')
  final int b2cLeads;
  @override
  @JsonKey(name: 'esp_synced_count')
  final int espSyncedCount;
  @override
  @JsonKey(name: 'esp_failed_permanent_count')
  final int espFailedPermanentCount;
  @override
  @JsonKey(name: 'emails_sent')
  final int emailsSent;
  @override
  @JsonKey(name: 'tokens_created')
  final int tokensCreated;
  @override
  @JsonKey(name: 'tokens_activated')
  final int tokensActivated;
  @override
  @JsonKey(name: 'tokens_exhausted')
  final int tokensExhausted;
  @override
  @JsonKey(name: 'total_jobs')
  final int totalJobs;
  @override
  @JsonKey(name: 'jobs_succeeded')
  final int jobsSucceeded;
  @override
  @JsonKey(name: 'jobs_failed')
  final int jobsFailed;
  @override
  @JsonKey(name: 'jobs_queued')
  final int jobsQueued;
  @override
  @JsonKey(name: 'jobs_running')
  final int jobsRunning;
  final Map<String, int> _failedByType;
  @override
  @JsonKey(name: 'failed_by_type')
  Map<String, int> get failedByType {
    if (_failedByType is EqualUnmodifiableMapView) return _failedByType;
    return EqualUnmodifiableMapView(_failedByType);
  }

  @override
  @JsonKey(name: 'catalog_syncs')
  final int catalogSyncs;
  @override
  @JsonKey(name: 'data_contract_violations')
  final int dataContractViolations;
  @override
  @JsonKey(name: 'period_start')
  final DateTime periodStart;
  @override
  @JsonKey(name: 'period_end')
  final DateTime periodEnd;

  @override
  String toString() {
    return 'KPIData(totalPublications: $totalPublications, publishedCount: $publishedCount, draftCount: $draftCount, totalLeads: $totalLeads, b2bLeads: $b2bLeads, educationLeads: $educationLeads, ispLeads: $ispLeads, b2cLeads: $b2cLeads, espSyncedCount: $espSyncedCount, espFailedPermanentCount: $espFailedPermanentCount, emailsSent: $emailsSent, tokensCreated: $tokensCreated, tokensActivated: $tokensActivated, tokensExhausted: $tokensExhausted, totalJobs: $totalJobs, jobsSucceeded: $jobsSucceeded, jobsFailed: $jobsFailed, jobsQueued: $jobsQueued, jobsRunning: $jobsRunning, failedByType: $failedByType, catalogSyncs: $catalogSyncs, dataContractViolations: $dataContractViolations, periodStart: $periodStart, periodEnd: $periodEnd)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$KPIDataImpl &&
            (identical(other.totalPublications, totalPublications) ||
                other.totalPublications == totalPublications) &&
            (identical(other.publishedCount, publishedCount) ||
                other.publishedCount == publishedCount) &&
            (identical(other.draftCount, draftCount) ||
                other.draftCount == draftCount) &&
            (identical(other.totalLeads, totalLeads) ||
                other.totalLeads == totalLeads) &&
            (identical(other.b2bLeads, b2bLeads) ||
                other.b2bLeads == b2bLeads) &&
            (identical(other.educationLeads, educationLeads) ||
                other.educationLeads == educationLeads) &&
            (identical(other.ispLeads, ispLeads) ||
                other.ispLeads == ispLeads) &&
            (identical(other.b2cLeads, b2cLeads) ||
                other.b2cLeads == b2cLeads) &&
            (identical(other.espSyncedCount, espSyncedCount) ||
                other.espSyncedCount == espSyncedCount) &&
            (identical(
                    other.espFailedPermanentCount, espFailedPermanentCount) ||
                other.espFailedPermanentCount == espFailedPermanentCount) &&
            (identical(other.emailsSent, emailsSent) ||
                other.emailsSent == emailsSent) &&
            (identical(other.tokensCreated, tokensCreated) ||
                other.tokensCreated == tokensCreated) &&
            (identical(other.tokensActivated, tokensActivated) ||
                other.tokensActivated == tokensActivated) &&
            (identical(other.tokensExhausted, tokensExhausted) ||
                other.tokensExhausted == tokensExhausted) &&
            (identical(other.totalJobs, totalJobs) ||
                other.totalJobs == totalJobs) &&
            (identical(other.jobsSucceeded, jobsSucceeded) ||
                other.jobsSucceeded == jobsSucceeded) &&
            (identical(other.jobsFailed, jobsFailed) ||
                other.jobsFailed == jobsFailed) &&
            (identical(other.jobsQueued, jobsQueued) ||
                other.jobsQueued == jobsQueued) &&
            (identical(other.jobsRunning, jobsRunning) ||
                other.jobsRunning == jobsRunning) &&
            const DeepCollectionEquality()
                .equals(other._failedByType, _failedByType) &&
            (identical(other.catalogSyncs, catalogSyncs) ||
                other.catalogSyncs == catalogSyncs) &&
            (identical(
                    other.dataContractViolations, dataContractViolations) ||
                other.dataContractViolations == dataContractViolations) &&
            (identical(other.periodStart, periodStart) ||
                other.periodStart == periodStart) &&
            (identical(other.periodEnd, periodEnd) ||
                other.periodEnd == periodEnd));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
        runtimeType,
        totalPublications,
        publishedCount,
        draftCount,
        totalLeads,
        b2bLeads,
        educationLeads,
        ispLeads,
        b2cLeads,
        espSyncedCount,
        espFailedPermanentCount,
        emailsSent,
        tokensCreated,
        tokensActivated,
        tokensExhausted,
        totalJobs,
        jobsSucceeded,
        jobsFailed,
        jobsQueued,
        Object.hash(
          jobsRunning,
          const DeepCollectionEquality().hash(_failedByType),
          catalogSyncs,
          dataContractViolations,
          periodStart,
          periodEnd,
        ),
      );

  /// Create a copy of KPIData
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$KPIDataImplCopyWith<_$KPIDataImpl> get copyWith =>
      __$$KPIDataImplCopyWithImpl<_$KPIDataImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$KPIDataImplToJson(this);
  }
}

abstract class _KPIData implements KPIData {
  const factory _KPIData({
    @JsonKey(name: 'total_publications') required final int totalPublications,
    @JsonKey(name: 'published_count') required final int publishedCount,
    @JsonKey(name: 'draft_count') required final int draftCount,
    @JsonKey(name: 'total_leads') required final int totalLeads,
    @JsonKey(name: 'b2b_leads') required final int b2bLeads,
    @JsonKey(name: 'education_leads') required final int educationLeads,
    @JsonKey(name: 'isp_leads') required final int ispLeads,
    @JsonKey(name: 'b2c_leads') required final int b2cLeads,
    @JsonKey(name: 'esp_synced_count') required final int espSyncedCount,
    @JsonKey(name: 'esp_failed_permanent_count')
    required final int espFailedPermanentCount,
    @JsonKey(name: 'emails_sent') required final int emailsSent,
    @JsonKey(name: 'tokens_created') required final int tokensCreated,
    @JsonKey(name: 'tokens_activated') required final int tokensActivated,
    @JsonKey(name: 'tokens_exhausted') required final int tokensExhausted,
    @JsonKey(name: 'total_jobs') required final int totalJobs,
    @JsonKey(name: 'jobs_succeeded') required final int jobsSucceeded,
    @JsonKey(name: 'jobs_failed') required final int jobsFailed,
    @JsonKey(name: 'jobs_queued') required final int jobsQueued,
    @JsonKey(name: 'jobs_running') required final int jobsRunning,
    @JsonKey(name: 'failed_by_type')
    required final Map<String, int> failedByType,
    @JsonKey(name: 'catalog_syncs') required final int catalogSyncs,
    @JsonKey(name: 'data_contract_violations')
    required final int dataContractViolations,
    @JsonKey(name: 'period_start') required final DateTime periodStart,
    @JsonKey(name: 'period_end') required final DateTime periodEnd,
  }) = _$KPIDataImpl;

  factory _KPIData.fromJson(Map<String, dynamic> json) =
      _$KPIDataImpl.fromJson;

  @override
  @JsonKey(name: 'total_publications')
  int get totalPublications;
  @override
  @JsonKey(name: 'published_count')
  int get publishedCount;
  @override
  @JsonKey(name: 'draft_count')
  int get draftCount;
  @override
  @JsonKey(name: 'total_leads')
  int get totalLeads;
  @override
  @JsonKey(name: 'b2b_leads')
  int get b2bLeads;
  @override
  @JsonKey(name: 'education_leads')
  int get educationLeads;
  @override
  @JsonKey(name: 'isp_leads')
  int get ispLeads;
  @override
  @JsonKey(name: 'b2c_leads')
  int get b2cLeads;
  @override
  @JsonKey(name: 'esp_synced_count')
  int get espSyncedCount;
  @override
  @JsonKey(name: 'esp_failed_permanent_count')
  int get espFailedPermanentCount;
  @override
  @JsonKey(name: 'emails_sent')
  int get emailsSent;
  @override
  @JsonKey(name: 'tokens_created')
  int get tokensCreated;
  @override
  @JsonKey(name: 'tokens_activated')
  int get tokensActivated;
  @override
  @JsonKey(name: 'tokens_exhausted')
  int get tokensExhausted;
  @override
  @JsonKey(name: 'total_jobs')
  int get totalJobs;
  @override
  @JsonKey(name: 'jobs_succeeded')
  int get jobsSucceeded;
  @override
  @JsonKey(name: 'jobs_failed')
  int get jobsFailed;
  @override
  @JsonKey(name: 'jobs_queued')
  int get jobsQueued;
  @override
  @JsonKey(name: 'jobs_running')
  int get jobsRunning;
  @override
  @JsonKey(name: 'failed_by_type')
  Map<String, int> get failedByType;
  @override
  @JsonKey(name: 'catalog_syncs')
  int get catalogSyncs;
  @override
  @JsonKey(name: 'data_contract_violations')
  int get dataContractViolations;
  @override
  @JsonKey(name: 'period_start')
  DateTime get periodStart;
  @override
  @JsonKey(name: 'period_end')
  DateTime get periodEnd;

  /// Create a copy of KPIData
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$KPIDataImplCopyWith<_$KPIDataImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
