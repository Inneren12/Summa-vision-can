import 'package:flutter/widgets.dart';

/// Resolved app-level state at bootstrap time.
///
/// Currently contains only the resolved locale. Can be extended with other
/// bootstrap-level resolved values (theme preference, feature flags, etc.)
/// without changing the consumer API.
class AppBootstrapState {
  final Locale locale;

  const AppBootstrapState({required this.locale});

  AppBootstrapState copyWith({Locale? locale}) {
    return AppBootstrapState(locale: locale ?? this.locale);
  }
}
