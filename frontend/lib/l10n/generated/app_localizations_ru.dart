// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Russian (`ru`).
class AppLocalizationsRu extends AppLocalizations {
  AppLocalizationsRu([String locale = 'ru']) : super(locale);

  @override
  String get appTitle => 'Summa Vision Admin';

  @override
  String get navQueue => 'Очередь брифов';

  @override
  String get navCubes => 'Кубы';

  @override
  String get navJobs => 'Задания';

  @override
  String get navExceptions => 'Исключения';

  @override
  String get navKpi => 'KPI';

  @override
  String get commonLoading => 'Загрузка...';

  @override
  String get commonRetryVerb => 'Повторить';

  @override
  String get commonCancelVerb => 'Отменить';

  @override
  String get languageLabel => 'Язык';

  @override
  String get languageEnglish => 'English';

  @override
  String get languageRussian => 'Русский';

  @override
  String get queueTitle => 'Очередь брифов';

  @override
  String get queueRefreshTooltip => 'Обновить очередь';

  @override
  String queueLoadError(String error) {
    return 'Не удалось загрузить очередь\\n$error';
  }

  @override
  String get queueEmptyState =>
      'В очереди нет брифов.\\nНажмите «Обновить», чтобы загрузить новые.';

  @override
  String get queueRejectVerb => 'Отклонить';

  @override
  String get queueApproveVerb => 'Одобрить';

  @override
  String get editorErrorAppBarTitle => 'Редактор';

  @override
  String get editorNotFoundAppBarTitle => 'Редактор';

  @override
  String editorLoadBriefError(String error) {
    return 'Не удалось загрузить бриф: $error';
  }

  @override
  String get editorBriefNotFound => 'Бриф не найден';

  @override
  String editorEditBriefTitle(int id) {
    return 'Редактирование брифа №$id';
  }

  @override
  String get editorResetVerb => 'Сбросить';

  @override
  String get editorViralityScoreLabel => 'Оценка виральности';

  @override
  String get editorHeadlineLabel => 'Заголовок';

  @override
  String get editorHeadlineHint => 'Введите заголовок...';

  @override
  String get editorBackgroundPromptLabel => 'Промпт фона';

  @override
  String get editorBackgroundPromptHint =>
      'Опишите желаемое фоновое изображение...';

  @override
  String get editorChartTypeLabel => 'Тип графика';

  @override
  String get editorPreviewBackgroundButton => 'Предпросмотр фона';

  @override
  String get editorGenerateGraphicButton => 'Сгенерировать графику';

  @override
  String editorActionError(String error) {
    return 'Не удалось выполнить действие в редакторе: $error';
  }

  @override
  String get previewAppBarTitle => 'Генерация графики';

  @override
  String get generationStatusSubmitting => 'Отправка задачи на генерацию...';

  @override
  String generationStatusPolling(int current, int total) {
    return 'Генерация... ($current/$total)';
  }

  @override
  String get previewEtaText => 'Это может занять до 2 минут.';

  @override
  String get generationStatusTimeout => 'Время генерации истекло.';

  @override
  String get generationStatusFailed => 'Не удалось сгенерировать графику.';

  @override
  String get generationStatusSucceeded => 'Генерация завершена.';

  @override
  String get previewDownloadButton => 'Скачать';

  @override
  String previewDownloadSaved(String path) {
    return 'Сохранено: $path';
  }

  @override
  String previewDownloadFailed(String error) {
    return 'Не удалось скачать: $error';
  }

  @override
  String get chartConfigAppBarTitle => 'Настройка графика';

  @override
  String get chartConfigDataSourceStatcan => 'Куб StatCan';

  @override
  String get chartConfigDataSourceUpload => 'Загрузить данные';

  @override
  String get chartConfigCustomDataSectionTitle => 'Пользовательские данные';

  @override
  String get chartConfigDatasetLabel => 'Набор данных';

  @override
  String chartConfigProductIdLabel(String productId) {
    return 'ID продукта: $productId';
  }

  @override
  String get chartConfigSizePresetLabel => 'Формат публикации';

  @override
  String get chartConfigBackgroundCategoryLabel => 'Категория фона';

  @override
  String get chartConfigHeadlineLabel => 'Заголовок графика';

  @override
  String get chartConfigHeadlineHint => 'Введите заголовок графика...';

  @override
  String get chartConfigHeadlineRequired => 'Требуется заголовок';

  @override
  String get chartConfigHeadlineMaxChars => 'Не более 200 символов';

  @override
  String chartConfigEtaRemaining(int seconds) {
    return 'Оценочное оставшееся время: ~$seconds c';
  }

  @override
  String chartConfigPublicationChip(int id) {
    return 'Публикация №$id';
  }

  @override
  String chartConfigVersionChip(String version) {
    return 'v$version';
  }

  @override
  String get chartConfigDownloadPreviewButton => 'Скачать предпросмотр';

  @override
  String get chartConfigGenerateAnotherButton => 'Сгенерировать ещё';

  @override
  String get chartConfigBackToPreviewButton => 'Назад к предпросмотру';

  @override
  String get chartConfigTryAgainButton => 'Попробовать снова';

  @override
  String get chartConfigUploadMissingError =>
      'Сначала загрузите файл JSON или CSV.';

  @override
  String get chartConfigUploadPickButton => 'Загрузить JSON / CSV';

  @override
  String chartConfigUploadFileLabel(String name) {
    return 'Файл: $name';
  }

  @override
  String chartConfigUploadParseError(String error) {
    return 'Не удалось разобрать файл: $error';
  }

  @override
  String chartConfigUploadSummary(int rows, int columns) {
    return '$rows строк × $columns столбцов';
  }

  @override
  String chartConfigTableShowingRows(int shown, int total) {
    return 'Показано $shown из $total строк';
  }

  @override
  String chartConfigTableEditCellTitle(String column, int row) {
    return 'Изменить $column [строка $row]';
  }

  @override
  String get commonSaveVerb => 'Сохранить';

  @override
  String get backgroundCategoryHousing => 'Жильё';

  @override
  String get backgroundCategoryInflation => 'Инфляция';

  @override
  String get backgroundCategoryEmployment => 'Занятость';

  @override
  String get backgroundCategoryTrade => 'Торговля';

  @override
  String get backgroundCategoryEnergy => 'Энергетика';

  @override
  String get backgroundCategoryDemographics => 'Демография';

  @override
  String get errorChartEmptyData => 'Нет данных для построения графика.';

  @override
  String get errorChartInsufficientColumns =>
      'Недостаточно столбцов для построения графика.';

  @override
  String get errorJobUnhandled =>
      'Непредвиденная ошибка при обработке задания.';

  @override
  String get errorJobCoolDown => 'Подождите перед повторной генерацией.';

  @override
  String get errorJobNoHandler => 'Операция не поддерживается.';

  @override
  String get errorJobIncompatiblePayload => 'Несовместимая версия данных.';

  @override
  String get errorJobUnknownType => 'Неизвестный тип задания.';

  @override
  String dataPreviewDiffStatusLabel(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '# ячеек изменилось с прошлого раза',
      many: '# ячеек изменилось с прошлого раза',
      few: '# ячейки изменились с прошлого раза',
      one: '1 ячейка изменилась с прошлого раза',
      zero: 'Ничего не изменилось с прошлого раза',
    );
    return '$_temp0';
  }

  @override
  String get dataPreviewDiffNoBaseline =>
      'Первый просмотр — сравнение недоступно';

  @override
  String get dataPreviewDiffSchemaChanged =>
      'Структура данных изменилась — сравнение недоступно';

  @override
  String get dataPreviewDiffNoProductId =>
      'Для этих данных отслеживание изменений недоступно';

  @override
  String get exceptionsTitle => 'Исключения';

  @override
  String get exceptionsRefreshTooltip => 'Обновить список исключений';

  @override
  String get exceptionsFilterAll => 'Все';

  @override
  String get exceptionsFilterFailedExports => 'Неудачные экспорты';

  @override
  String get exceptionsFilterZombieJobs => 'Зависшие задачи';

  @override
  String exceptionsLoadError(String error) {
    return 'Не удалось загрузить список исключений\\n$error';
  }

  @override
  String get exceptionsEmptyState =>
      'Нет исключений для проверки.\\nНажмите «Обновить», чтобы получить новые.';
}
