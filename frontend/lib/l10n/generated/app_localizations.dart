import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_ru.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'generated/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('ru'),
  ];

  /// Application title shown in window chrome and admin app shell header
  ///
  /// In en, this message translates to:
  /// **'Summa Vision Admin'**
  String get appTitle;

  /// Navigation label for the brief queue screen
  ///
  /// In en, this message translates to:
  /// **'Brief Queue'**
  String get navQueue;

  /// Navigation label for the StatCan cubes search/detail screens
  ///
  /// In en, this message translates to:
  /// **'Cubes'**
  String get navCubes;

  /// Navigation label for the async jobs monitoring screen
  ///
  /// In en, this message translates to:
  /// **'Jobs'**
  String get navJobs;

  /// AppDrawer navigation label for the /exceptions screen (operator inbox showing failed exports + zombie jobs).
  ///
  /// In en, this message translates to:
  /// **'Exceptions'**
  String get navExceptions;

  /// AppDrawer navigation label for the /semantic-mappings admin CRUD screen (Phase 3.1b).
  ///
  /// In en, this message translates to:
  /// **'Semantic mappings'**
  String get navSemanticMappings;

  /// Backend error: generic semantic-mapping validation failure.
  ///
  /// In en, this message translates to:
  /// **'The mapping does not match StatCan cube metadata.'**
  String get errorBackendMetadataValidationFailed;

  /// Backend error: dimension key missing from cube.
  ///
  /// In en, this message translates to:
  /// **'Dimension not found in cube metadata.'**
  String get errorBackendDimensionNotFound;

  /// Backend error: member missing from dimension.
  ///
  /// In en, this message translates to:
  /// **'Member not found in dimension.'**
  String get errorBackendMemberNotFound;

  /// Backend error: cube_id ↔ product_id mismatch.
  ///
  /// In en, this message translates to:
  /// **'Cube ID and product ID do not match cached metadata.'**
  String get errorBackendCubeProductMismatch;

  /// Backend error: cube metadata not cached.
  ///
  /// In en, this message translates to:
  /// **'Cube metadata is not available — please retry shortly.'**
  String get errorBackendCubeNotInCache;

  /// Backend error: optimistic concurrency mismatch on save.
  ///
  /// In en, this message translates to:
  /// **'Version conflict — this mapping was modified by another user. Reload to see the latest version.'**
  String get errorBackendVersionConflict;

  /// Backend error: bulk semantic-mapping upsert failed validation.
  ///
  /// In en, this message translates to:
  /// **'Some mappings could not be validated. No changes were saved. Fix the errors below and retry.'**
  String get errorBackendBulkValidationFailed;

  /// Navigation label for the KPI monitoring screen
  ///
  /// In en, this message translates to:
  /// **'KPI'**
  String get navKpi;

  /// Generic 'Loading...' label. RESERVED common vocabulary — currently unused in lib/ (AsyncValue.loading branches use CircularProgressIndicator directly in Queue/Editor; Graphics uses generationStatusSubmitting/generationStatusPolling). Preserved for future feature use without requiring a new ARB round-trip. See Phase 3 Slice 3.11 recon for dead-key policy.
  ///
  /// In en, this message translates to:
  /// **'Loading...'**
  String get commonLoading;

  /// Retry action button label
  ///
  /// In en, this message translates to:
  /// **'Retry'**
  String get commonRetryVerb;

  /// Cancel action button label
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get commonCancelVerb;

  /// Label preceding the language switcher control
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get languageLabel;

  /// Name of the English locale in the language switcher
  ///
  /// In en, this message translates to:
  /// **'English'**
  String get languageEnglish;

  /// Name of the Russian locale in the language switcher
  ///
  /// In en, this message translates to:
  /// **'Russian'**
  String get languageRussian;

  /// AppBar title on the Queue screen. Semantically identical to navQueue but used as screen title rather than nav label; kept separate to allow divergent tuning per §3l migration rule.
  ///
  /// In en, this message translates to:
  /// **'Brief Queue'**
  String get queueTitle;

  /// Tooltip on the Queue screen refresh IconButton
  ///
  /// In en, this message translates to:
  /// **'Refresh queue'**
  String get queueRefreshTooltip;

  /// Error message shown when /api/v1/admin/queue request fails. The {error} placeholder receives the backend error detail or exception message as-is.
  ///
  /// In en, this message translates to:
  /// **'Failed to load queue\\n{error}'**
  String queueLoadError(String error);

  /// Empty state message on the Queue screen when no DRAFT briefs are available for review
  ///
  /// In en, this message translates to:
  /// **'No briefs in queue.\\nTap refresh to fetch new ones.'**
  String get queueEmptyState;

  /// Queue item action button — reject the brief (does not advance to PUBLISHED)
  ///
  /// In en, this message translates to:
  /// **'Reject'**
  String get queueRejectVerb;

  /// Queue item action button — approve the brief (advances to PUBLISHED)
  ///
  /// In en, this message translates to:
  /// **'Approve'**
  String get queueApproveVerb;

  /// AppBar title shown on the Editor screen in error-state (failed to load brief). Distinct from editorEditBriefTitle because brief context is unavailable.
  ///
  /// In en, this message translates to:
  /// **'Editor'**
  String get editorErrorAppBarTitle;

  /// AppBar title shown on the Editor screen when requested brief is not found. Distinct from editorEditBriefTitle because brief ID is invalid.
  ///
  /// In en, this message translates to:
  /// **'Editor'**
  String get editorNotFoundAppBarTitle;

  /// Error message when GET /admin/publications/{id} fails. {error} placeholder receives the backend error detail verbatim (may remain in source language).
  ///
  /// In en, this message translates to:
  /// **'Failed to load brief: {error}'**
  String editorLoadBriefError(String error);

  /// Shown when the editor is asked to load a brief ID that does not exist on the backend (404).
  ///
  /// In en, this message translates to:
  /// **'Brief not found'**
  String get editorBriefNotFound;

  /// AppBar title on the Editor screen with brief loaded. {id} is brief.id (integer) injected via UI chrome — the brief ID itself is backend payload, the wrapper is localized chrome per §3j.
  ///
  /// In en, this message translates to:
  /// **'Edit Brief #{id}'**
  String editorEditBriefTitle(int id);

  /// Reset button label in the editor — reverts field edits to the last loaded brief state.
  ///
  /// In en, this message translates to:
  /// **'Reset'**
  String get editorResetVerb;

  /// Label for the read-only AI-generated virality score (0.0–10.0) shown in the editor.
  ///
  /// In en, this message translates to:
  /// **'Virality Score'**
  String get editorViralityScoreLabel;

  /// Label for the headline TextField in the editor.
  ///
  /// In en, this message translates to:
  /// **'Headline'**
  String get editorHeadlineLabel;

  /// Placeholder text shown inside the empty headline TextField.
  ///
  /// In en, this message translates to:
  /// **'Enter headline...'**
  String get editorHeadlineHint;

  /// Label for the AI background-image prompt TextField in the editor.
  ///
  /// In en, this message translates to:
  /// **'Background Prompt'**
  String get editorBackgroundPromptLabel;

  /// Placeholder text shown inside the empty background prompt TextField.
  ///
  /// In en, this message translates to:
  /// **'Describe the AI background image...'**
  String get editorBackgroundPromptHint;

  /// Label above the chart type dropdown in the editor. Note: dropdown values themselves (Line, Bar, etc.) are EN-kept per §3k Category D — see docs/phase-3-slice-5-recon.md §6.
  ///
  /// In en, this message translates to:
  /// **'Chart Type'**
  String get editorChartTypeLabel;

  /// Secondary action button that triggers a background-image preview generation (without advancing to full graphic generation).
  ///
  /// In en, this message translates to:
  /// **'Preview Background'**
  String get editorPreviewBackgroundButton;

  /// Primary CTA button that navigates to Preview/Graphics generation route with the current brief.
  ///
  /// In en, this message translates to:
  /// **'Generate Graphic'**
  String get editorGenerateGraphicButton;

  /// Generic wrapper for editor backend action errors (PATCH /publications/{id}, publish, unpublish). Placeholder {error} receives backend detail or exception message as-is. RESERVED — not currently rendered; editor endpoints still lack structured error_codes (DEBT-030). Will be activated when backend admin_publications endpoints emit stable error_code values and the backend_errors.dart mapper is extended accordingly.
  ///
  /// In en, this message translates to:
  /// **'Editor action failed: {error}'**
  String editorActionError(String error);

  /// AppBar title on the Preview/Generation screen. Shown while generation is in flight.
  ///
  /// In en, this message translates to:
  /// **'Generating Graphic'**
  String get previewAppBarTitle;

  /// Status label shown while the generation task is being submitted to the backend. Used by both preview_screen and chart_config_screen via local phase->key mappers.
  ///
  /// In en, this message translates to:
  /// **'Submitting generation task...'**
  String get generationStatusSubmitting;

  /// Status label shown while polling for generation completion. {current} is current poll attempt, {total} is max polls. Used by both preview and chart config screens.
  ///
  /// In en, this message translates to:
  /// **'Generating... ({current}/{total})'**
  String generationStatusPolling(int current, int total);

  /// Informational helper text shown below the polling status on the Preview screen.
  ///
  /// In en, this message translates to:
  /// **'This may take up to 2 minutes.'**
  String get previewEtaText;

  /// Status label when generation exceeds the max poll window. Used by both screens.
  ///
  /// In en, this message translates to:
  /// **'Generation timed out.'**
  String get generationStatusTimeout;

  /// Status label when generation fails. Used as fallback when error_message is null. Used by both screens.
  ///
  /// In en, this message translates to:
  /// **'Generation failed.'**
  String get generationStatusFailed;

  /// Status label when generation succeeds. Covers both 'completed' phase (preview_screen) and 'success' phase (chart_config_screen). Per DEBT-031, the underlying enum divergence is out of i18n scope. RESERVED — not currently rendered in either screen: both success paths transition directly to a result view without showing the status label. Retained for parity with other generationStatus* keys and for future UX that may show a completion confirmation before the result view.
  ///
  /// In en, this message translates to:
  /// **'Generation completed.'**
  String get generationStatusSucceeded;

  /// Download button label on Preview screen after successful generation.
  ///
  /// In en, this message translates to:
  /// **'Download'**
  String get previewDownloadButton;

  /// Snackbar shown after successful download. {path} is the local file path — passed through as Category C payload.
  ///
  /// In en, this message translates to:
  /// **'Saved: {path}'**
  String previewDownloadSaved(String path);

  /// Snackbar shown when download fails. {error} is backend/exception detail interpolated verbatim.
  ///
  /// In en, this message translates to:
  /// **'Download failed: {error}'**
  String previewDownloadFailed(String error);

  /// AppBar title on the chart configuration screen.
  ///
  /// In en, this message translates to:
  /// **'Chart Configuration'**
  String get chartConfigAppBarTitle;

  /// Segmented control label for StatCan Cube data source.
  ///
  /// In en, this message translates to:
  /// **'StatCan Cube'**
  String get chartConfigDataSourceStatcan;

  /// Segmented control label for user-uploaded data source.
  ///
  /// In en, this message translates to:
  /// **'Upload Data'**
  String get chartConfigDataSourceUpload;

  /// Section heading for custom/uploaded data source configuration.
  ///
  /// In en, this message translates to:
  /// **'Custom Data'**
  String get chartConfigCustomDataSectionTitle;

  /// Dataset card heading in the chart config screen.
  ///
  /// In en, this message translates to:
  /// **'Dataset'**
  String get chartConfigDatasetLabel;

  /// Label displaying the StatCan product ID as UI chrome wrapping a backend-provided ID string.
  ///
  /// In en, this message translates to:
  /// **'Product ID: {productId}'**
  String chartConfigProductIdLabel(String productId);

  /// Label above size preset selector (Instagram/Twitter/Reddit aspect ratios). Note: preset VALUES themselves are EN-kept Category D per §3k.
  ///
  /// In en, this message translates to:
  /// **'Size Preset'**
  String get chartConfigSizePresetLabel;

  /// Label above background category selector. Values are localized per founder Decision 1 via backgroundCategory* keys.
  ///
  /// In en, this message translates to:
  /// **'Background Category'**
  String get chartConfigBackgroundCategoryLabel;

  /// Label for chart headline TextField in config screen. Distinct from editor's Headline field — disambiguated with 'Chart' prefix.
  ///
  /// In en, this message translates to:
  /// **'Chart Headline'**
  String get chartConfigHeadlineLabel;

  /// Placeholder text inside the empty chart headline TextField.
  ///
  /// In en, this message translates to:
  /// **'Enter chart headline...'**
  String get chartConfigHeadlineHint;

  /// Form validation message when chart headline field is empty.
  ///
  /// In en, this message translates to:
  /// **'Headline is required'**
  String get chartConfigHeadlineRequired;

  /// Form validation message when chart headline exceeds 200 characters. Static count, no placeholder.
  ///
  /// In en, this message translates to:
  /// **'Maximum 200 characters'**
  String get chartConfigHeadlineMaxChars;

  /// ETA text shown during polling. {seconds} is integer seconds remaining.
  ///
  /// In en, this message translates to:
  /// **'Estimated time remaining: ~{seconds}s'**
  String chartConfigEtaRemaining(int seconds);

  /// Success-state metadata chip showing publication ID. {id} is backend result payload.
  ///
  /// In en, this message translates to:
  /// **'Publication #{id}'**
  String chartConfigPublicationChip(int id);

  /// Success-state metadata chip showing version. {version} is backend result payload; 'v' prefix kept as technical token in both locales.
  ///
  /// In en, this message translates to:
  /// **'v{version}'**
  String chartConfigVersionChip(String version);

  /// Success-state action button: download the generated preview image.
  ///
  /// In en, this message translates to:
  /// **'Download Preview'**
  String get chartConfigDownloadPreviewButton;

  /// Success-state action button: start a new generation with current config.
  ///
  /// In en, this message translates to:
  /// **'Generate Another'**
  String get chartConfigGenerateAnotherButton;

  /// Success-state navigation button back to the preview screen.
  ///
  /// In en, this message translates to:
  /// **'Back to Preview'**
  String get chartConfigBackToPreviewButton;

  /// Failure-state retry button. Distinct from commonRetryVerb to allow divergent tuning per §3l; the timeout branch reuses commonRetryVerb.
  ///
  /// In en, this message translates to:
  /// **'Try Again'**
  String get chartConfigTryAgainButton;

  /// Validation message when user attempts generation without uploading a data file.
  ///
  /// In en, this message translates to:
  /// **'Upload a JSON or CSV file first.'**
  String get chartConfigUploadMissingError;

  /// File picker button label in data upload widget.
  ///
  /// In en, this message translates to:
  /// **'Upload JSON / CSV'**
  String get chartConfigUploadPickButton;

  /// Selected file display label after upload. {name} is user's local filename (Category C payload).
  ///
  /// In en, this message translates to:
  /// **'File: {name}'**
  String chartConfigUploadFileLabel(String name);

  /// Error when uploaded file cannot be parsed as JSON/CSV. {error} is parse exception detail.
  ///
  /// In en, this message translates to:
  /// **'Failed to parse file: {error}'**
  String chartConfigUploadParseError(String error);

  /// Parsed-data summary. {rows} is row count, {columns} is column count. Both integers; no plural forms per founder decision (compact numeric display).
  ///
  /// In en, this message translates to:
  /// **'{rows} rows × {columns} columns'**
  String chartConfigUploadSummary(int rows, int columns);

  /// Table truncation info. {shown} = visible row count, {total} = full dataset row count.
  ///
  /// In en, this message translates to:
  /// **'Showing {shown} of {total} rows'**
  String chartConfigTableShowingRows(int shown, int total);

  /// Edit dialog title. {column} = column name (user/backend content), {row} = row index (int).
  ///
  /// In en, this message translates to:
  /// **'Edit {column} [row {row}]'**
  String chartConfigTableEditCellTitle(String column, int row);

  /// Generic Save action button label. Paired with commonCancelVerb in dialogs.
  ///
  /// In en, this message translates to:
  /// **'Save'**
  String get commonSaveVerb;

  /// Background category label for housing-related content. Localized per §3j as UI taxonomy (not industry-standard chart terminology).
  ///
  /// In en, this message translates to:
  /// **'Housing'**
  String get backgroundCategoryHousing;

  /// Background category label for inflation-related content.
  ///
  /// In en, this message translates to:
  /// **'Inflation'**
  String get backgroundCategoryInflation;

  /// Background category label for employment-related content.
  ///
  /// In en, this message translates to:
  /// **'Employment'**
  String get backgroundCategoryEmployment;

  /// Background category label for trade-related content.
  ///
  /// In en, this message translates to:
  /// **'Trade'**
  String get backgroundCategoryTrade;

  /// Background category label for energy-related content.
  ///
  /// In en, this message translates to:
  /// **'Energy'**
  String get backgroundCategoryEnergy;

  /// Background category label for demographics-related content.
  ///
  /// In en, this message translates to:
  /// **'Demographics'**
  String get backgroundCategoryDemographics;

  /// Mapped from backend error_code CHART_EMPTY_DF. Shown when the dataset used for generation is empty.
  ///
  /// In en, this message translates to:
  /// **'No data to chart.'**
  String get errorChartEmptyData;

  /// Mapped from backend error_code CHART_INSUFFICIENT_COLUMNS. Shown when dataset lacks the columns needed for the requested chart type.
  ///
  /// In en, this message translates to:
  /// **'Not enough columns to build the chart.'**
  String get errorChartInsufficientColumns;

  /// Mapped from backend error_code UNHANDLED_ERROR. Runner fallback when no more specific code applies.
  ///
  /// In en, this message translates to:
  /// **'Unexpected error while processing the job.'**
  String get errorJobUnhandled;

  /// Mapped from backend error_code COOL_DOWN_ACTIVE. Rate limit between generation requests.
  ///
  /// In en, this message translates to:
  /// **'Please wait before starting another generation.'**
  String get errorJobCoolDown;

  /// Mapped from backend error_code NO_HANDLER_REGISTERED. Dispatcher error — operator should rarely see this.
  ///
  /// In en, this message translates to:
  /// **'Unsupported operation.'**
  String get errorJobNoHandler;

  /// Mapped from backend error_code INCOMPATIBLE_PAYLOAD_VERSION. Client/server schema drift.
  ///
  /// In en, this message translates to:
  /// **'Version mismatch between client and server payload.'**
  String get errorJobIncompatiblePayload;

  /// Mapped from backend error_code UNKNOWN_JOB_TYPE. Dispatcher error — operator should rarely see this.
  ///
  /// In en, this message translates to:
  /// **'Unknown job type.'**
  String get errorJobUnknownType;

  /// Banner above data table showing how many cells changed since last view
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =0 {No cells changed since last view} =1 {1 cell changed since last view} other {# cells changed since last view}}'**
  String dataPreviewDiffStatusLabel(int count);

  /// Banner when this is the first time viewing this cube
  ///
  /// In en, this message translates to:
  /// **'First view — no comparison available'**
  String get dataPreviewDiffNoBaseline;

  /// Banner when columns differ from previous snapshot
  ///
  /// In en, this message translates to:
  /// **'Schema changed since last view — diff unavailable'**
  String get dataPreviewDiffSchemaChanged;

  /// Banner when storage_key has no parseable product_id (non-StatCan path)
  ///
  /// In en, this message translates to:
  /// **'This data has no diff tracking'**
  String get dataPreviewDiffNoProductId;

  /// Title of the /exceptions screen showing failed exports and zombie jobs.
  ///
  /// In en, this message translates to:
  /// **'Exceptions'**
  String get exceptionsTitle;

  /// Tooltip for the refresh icon in the /exceptions AppBar.
  ///
  /// In en, this message translates to:
  /// **'Refresh exceptions'**
  String get exceptionsRefreshTooltip;

  /// Filter chip label: show all exception types.
  ///
  /// In en, this message translates to:
  /// **'All'**
  String get exceptionsFilterAll;

  /// Filter chip label: show only failed graphics_generate jobs.
  ///
  /// In en, this message translates to:
  /// **'Failed Exports'**
  String get exceptionsFilterFailedExports;

  /// Filter chip label: show only running jobs that exceed the 10-minute stale threshold.
  ///
  /// In en, this message translates to:
  /// **'Zombie Jobs'**
  String get exceptionsFilterZombieJobs;

  /// Error state copy when /exceptions fails to fetch rows.
  ///
  /// In en, this message translates to:
  /// **'Failed to load exceptions\\n{error}'**
  String exceptionsLoadError(String error);

  /// Empty state copy when /exceptions has zero rows under the current filter.
  ///
  /// In en, this message translates to:
  /// **'No exceptions to review.\\nTap refresh to fetch new ones.'**
  String get exceptionsEmptyState;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'ru'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'ru':
      return AppLocalizationsRu();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
