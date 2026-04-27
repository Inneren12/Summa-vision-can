import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter/widgets.dart';

import 'app_localizations_en.dart';
import 'app_localizations_ru.dart';

abstract class AppLocalizations {
  AppLocalizations(this.localeName);

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('ru'),
  ];

  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  String get appTitle;
  String get navQueue;
  String get navCubes;
  String get navJobs;
  String get navKpi;
  String get commonLoading;
  String get commonRetryVerb;
  String get commonCancelVerb;
  String get languageLabel;
  String get languageEnglish;
  String get languageRussian;
  String get queueTitle;
  String get queueRefreshTooltip;
  String queueLoadError(String error);
  String get queueEmptyState;
  String get queueRejectVerb;
  String get queueApproveVerb;
  String get editorErrorAppBarTitle;
  String get editorNotFoundAppBarTitle;
  String editorLoadBriefError(String error);
  String get editorBriefNotFound;
  String editorEditBriefTitle(int id);
  String get editorResetVerb;
  String get editorViralityScoreLabel;
  String get editorHeadlineLabel;
  String get editorHeadlineHint;
  String get editorBackgroundPromptLabel;
  String get editorBackgroundPromptHint;
  String get editorChartTypeLabel;
  String get editorPreviewBackgroundButton;
  String get editorGenerateGraphicButton;
  String editorActionError(String error);
  String get previewAppBarTitle;
  String get generationStatusSubmitting;
  String generationStatusPolling(int current, int total);
  String get previewEtaText;
  String get generationStatusTimeout;
  String get generationStatusFailed;
  String get generationStatusSucceeded;
  String get previewDownloadButton;
  String previewDownloadSaved(String path);
  String previewDownloadFailed(String error);
  String get chartConfigAppBarTitle;
  String get chartConfigDataSourceStatcan;
  String get chartConfigDataSourceUpload;
  String get chartConfigCustomDataSectionTitle;
  String get chartConfigDatasetLabel;
  String chartConfigProductIdLabel(String productId);
  String get chartConfigSizePresetLabel;
  String get chartConfigBackgroundCategoryLabel;
  String get chartConfigHeadlineLabel;
  String get chartConfigHeadlineHint;
  String get chartConfigHeadlineRequired;
  String get chartConfigHeadlineMaxChars;
  String chartConfigEtaRemaining(int seconds);
  String chartConfigPublicationChip(int id);
  String chartConfigVersionChip(String version);
  String get chartConfigDownloadPreviewButton;
  String get chartConfigGenerateAnotherButton;
  String get chartConfigBackToPreviewButton;
  String get chartConfigTryAgainButton;
  String get chartConfigUploadMissingError;
  String get chartConfigUploadPickButton;
  String chartConfigUploadFileLabel(String name);
  String chartConfigUploadParseError(String error);
  String chartConfigUploadSummary(int rows, int columns);
  String chartConfigTableShowingRows(int shown, int total);
  String chartConfigTableEditCellTitle(String column, int row);
  String get commonSaveVerb;
  String get backgroundCategoryHousing;
  String get backgroundCategoryInflation;
  String get backgroundCategoryEmployment;
  String get backgroundCategoryTrade;
  String get backgroundCategoryEnergy;
  String get backgroundCategoryDemographics;
  String get errorChartEmptyData;
  String get errorChartInsufficientColumns;
  String get errorJobUnhandled;
  String get errorJobCoolDown;
  String get errorJobNoHandler;
  String get errorJobIncompatiblePayload;
  String get errorJobUnknownType;
  String dataPreviewDiffStatusLabel(int count);
  String get dataPreviewDiffNoBaseline;
  String get dataPreviewDiffSchemaChanged;
  String get dataPreviewDiffNoProductId;
}

class _AppLocalizationsDelegate extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) => <String>['en', 'ru'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'ru':
      return AppLocalizationsRu();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale".',
  );
}
