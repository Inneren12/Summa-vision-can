import 'app_localizations.dart';

class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn() : super('en');

  @override
  String get appTitle => 'Summa Vision Admin';

  @override
  String get navQueue => 'Brief Queue';

  @override
  String get navCubes => 'Cubes';

  @override
  String get navJobs => 'Jobs';

  @override
  String get navKpi => 'KPI';

  @override
  String get commonLoading => 'Loading...';

  @override
  String get commonRetryVerb => 'Retry';

  @override
  String get commonCancelVerb => 'Cancel';

  @override
  String get languageLabel => 'Language';

  @override
  String get languageEnglish => 'English';

  @override
  String get languageRussian => 'Russian';

  @override
  String get queueTitle => 'Brief Queue';

  @override
  String get queueRefreshTooltip => 'Refresh queue';

  @override
  String queueLoadError(String error) {
    return 'Failed to load queue\n$error';
  }

  @override
  String get queueEmptyState => 'No briefs in queue.\nTap refresh to fetch new ones.';

  @override
  String get queueRejectVerb => 'Reject';

  @override
  String get queueApproveVerb => 'Approve';

  @override
  String get editorErrorAppBarTitle => 'Editor';

  @override
  String get editorNotFoundAppBarTitle => 'Editor';

  @override
  String editorLoadBriefError(String error) {
    return 'Failed to load brief: $error';
  }

  @override
  String get editorBriefNotFound => 'Brief not found';

  @override
  String editorEditBriefTitle(int id) {
    return 'Edit Brief #$id';
  }

  @override
  String get editorResetVerb => 'Reset';

  @override
  String get editorViralityScoreLabel => 'Virality Score';

  @override
  String get editorHeadlineLabel => 'Headline';

  @override
  String get editorHeadlineHint => 'Enter headline...';

  @override
  String get editorBackgroundPromptLabel => 'Background Prompt';

  @override
  String get editorBackgroundPromptHint => 'Describe the AI background image...';

  @override
  String get editorChartTypeLabel => 'Chart Type';

  @override
  String get editorPreviewBackgroundButton => 'Preview Background';

  @override
  String get editorGenerateGraphicButton => 'Generate Graphic';

  @override
  String editorActionError(String error) {
    return 'Editor action failed: $error';
  }

  @override
  String get previewAppBarTitle => 'Generating Graphic';

  @override
  String get generationStatusSubmitting => 'Submitting generation task...';

  @override
  String generationStatusPolling(int current, int total) {
    return 'Generating... ($current/$total)';
  }

  @override
  String get previewEtaText => 'This may take up to 2 minutes.';

  @override
  String get generationStatusTimeout => 'Generation timed out.';

  @override
  String get generationStatusFailed => 'Generation failed.';

  @override
  String get generationStatusSucceeded => 'Generation completed.';

  @override
  String get previewDownloadButton => 'Download';

  @override
  String previewDownloadSaved(String path) {
    return 'Saved: $path';
  }

  @override
  String previewDownloadFailed(String error) {
    return 'Download failed: $error';
  }

  @override
  String get chartConfigAppBarTitle => 'Chart Configuration';

  @override
  String get chartConfigDataSourceStatcan => 'StatCan Cube';

  @override
  String get chartConfigDataSourceUpload => 'Upload Data';

  @override
  String get chartConfigCustomDataSectionTitle => 'Custom Data';

  @override
  String get chartConfigDatasetLabel => 'Dataset';

  @override
  String chartConfigProductIdLabel(String productId) {
    return 'Product ID: $productId';
  }

  @override
  String get chartConfigSizePresetLabel => 'Size Preset';

  @override
  String get chartConfigBackgroundCategoryLabel => 'Background Category';

  @override
  String get chartConfigHeadlineLabel => 'Chart Headline';

  @override
  String get chartConfigHeadlineHint => 'Enter chart headline...';

  @override
  String get chartConfigHeadlineRequired => 'Headline is required';

  @override
  String get chartConfigHeadlineMaxChars => 'Maximum 200 characters';

  @override
  String chartConfigEtaRemaining(int seconds) {
    return 'Estimated time remaining: ~${seconds}s';
  }

  @override
  String chartConfigPublicationChip(int id) {
    return 'Publication #$id';
  }

  @override
  String chartConfigVersionChip(String version) {
    return 'v$version';
  }

  @override
  String get chartConfigDownloadPreviewButton => 'Download Preview';

  @override
  String get chartConfigGenerateAnotherButton => 'Generate Another';

  @override
  String get chartConfigBackToPreviewButton => 'Back to Preview';

  @override
  String get chartConfigTryAgainButton => 'Try Again';

  @override
  String get chartConfigUploadMissingError => 'Upload a JSON or CSV file first.';

  @override
  String get chartConfigUploadPickButton => 'Upload JSON / CSV';

  @override
  String chartConfigUploadFileLabel(String name) {
    return 'File: $name';
  }

  @override
  String chartConfigUploadParseError(String error) {
    return 'Failed to parse file: $error';
  }

  @override
  String chartConfigUploadSummary(int rows, int columns) {
    return '$rows rows × $columns columns';
  }

  @override
  String chartConfigTableShowingRows(int shown, int total) {
    return 'Showing $shown of $total rows';
  }

  @override
  String chartConfigTableEditCellTitle(String column, int row) {
    return 'Edit $column [row $row]';
  }

  @override
  String get commonSaveVerb => 'Save';

  @override
  String get backgroundCategoryHousing => 'Housing';

  @override
  String get backgroundCategoryInflation => 'Inflation';

  @override
  String get backgroundCategoryEmployment => 'Employment';

  @override
  String get backgroundCategoryTrade => 'Trade';

  @override
  String get backgroundCategoryEnergy => 'Energy';

  @override
  String get backgroundCategoryDemographics => 'Demographics';

  @override
  String get errorChartEmptyData => 'No data to chart.';

  @override
  String get errorChartInsufficientColumns => 'Not enough columns to build the chart.';

  @override
  String get errorJobUnhandled => 'Unexpected error while processing the job.';

  @override
  String get errorJobCoolDown => 'Please wait before starting another generation.';

  @override
  String get errorJobNoHandler => 'Unsupported operation.';

  @override
  String get errorJobIncompatiblePayload => 'Version mismatch between client and server payload.';

  @override
  String get errorJobUnknownType => 'Unknown job type.';
}
