import 'package:flutter/material.dart';

/// Summa Vision design system.
///
/// All colours pass WCAG AA contrast ratio (4.5:1) against the
/// [backgroundDark] base.
class AppTheme {
  AppTheme._();

  // Brand colours
  static const Color backgroundDark = Color(0xFF141414);
  static const Color surfaceDark = Color(0xFF1E1E1E);
  static const Color neonGreen = Color(0xFF00FF94);
  static const Color neonBlue = Color(0xFF00D4FF);
  static const Color neonPink = Color(0xFFFF006E);
  static const Color neonYellow = Color(0xFFFFB700);
  static const Color textPrimary = Color(0xFFFFFFFF);
  static const Color textSecondary = Color(0xFFB0B0B0);
  static const Color errorRed = Color(0xFFCF6679);

  static ThemeData get dark => ThemeData.dark().copyWith(
    scaffoldBackgroundColor: backgroundDark,
    colorScheme: const ColorScheme.dark(
      primary: neonGreen,
      secondary: neonBlue,
      error: errorRed,
      surface: surfaceDark,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: backgroundDark,
      foregroundColor: textPrimary,
      elevation: 0,
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: neonGreen,
        foregroundColor: backgroundDark,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(8)),
        ),
      ),
    ),
    textTheme: const TextTheme(
      bodyLarge: TextStyle(color: textPrimary, fontSize: 16),
      bodyMedium: TextStyle(color: textSecondary, fontSize: 14),
      titleLarge: TextStyle(
        color: textPrimary,
        fontSize: 20,
        fontWeight: FontWeight.bold,
      ),
    ),
    cardTheme: const CardThemeData(color: surfaceDark, elevation: 0),
  );
}
