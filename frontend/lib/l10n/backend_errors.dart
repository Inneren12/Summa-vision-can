import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

/// Maps a backend `error_code` string to a localized error message.
///
/// Returns null if `error_code` is null or not recognized. Caller should
/// fall back to `error_message` (passthrough) or a generic wrapper.
///
/// First realization of Appendix D (frontend/docs/phase-3-plan.md) — the
/// plan left signature open; chosen here as simple string-returning switch
/// because all current codes are static (no parameters). When a future
/// backend code requires parameters (e.g., CHART_ROW_LIMIT_EXCEEDED with
/// limit count), extend the signature then.
String? mapBackendErrorCode(String? errorCode, AppLocalizations l10n) {
  if (errorCode == null) return null;
  return switch (errorCode) {
    'CHART_EMPTY_DF' => l10n.errorChartEmptyData,
    'CHART_INSUFFICIENT_COLUMNS' => l10n.errorChartInsufficientColumns,
    'UNHANDLED_ERROR' => l10n.errorJobUnhandled,
    'COOL_DOWN_ACTIVE' => l10n.errorJobCoolDown,
    'NO_HANDLER_REGISTERED' => l10n.errorJobNoHandler,
    'INCOMPATIBLE_PAYLOAD_VERSION' => l10n.errorJobIncompatiblePayload,
    'UNKNOWN_JOB_TYPE' => l10n.errorJobUnknownType,
    // Phase 3.1ab + 3.1b — semantic-mapping admin save flow.
    // See DEBT-056: this PR backfills only the seven semantic-mapping
    // codes; a comprehensive sweep over KNOWN_BACKEND_ERROR_CODES (TS)
    // is deferred work.
    'METADATA_VALIDATION_FAILED' => l10n.errorBackendMetadataValidationFailed,
    'DIMENSION_NOT_FOUND' => l10n.errorBackendDimensionNotFound,
    'MEMBER_NOT_FOUND' => l10n.errorBackendMemberNotFound,
    'CUBE_PRODUCT_MISMATCH' => l10n.errorBackendCubeProductMismatch,
    'CUBE_NOT_IN_CACHE' => l10n.errorBackendCubeNotInCache,
    'VERSION_CONFLICT' => l10n.errorBackendVersionConflict,
    'BULK_VALIDATION_FAILED' => l10n.errorBackendBulkValidationFailed,
    _ => null,
  };
}
