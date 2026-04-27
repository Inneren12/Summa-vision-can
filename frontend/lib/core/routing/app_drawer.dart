import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:summa_vision_admin/core/shell/language_switcher.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

import '../theme/app_theme.dart';
import 'app_router.dart';

/// Shared navigation drawer shown on all top-level screens.
class AppDrawer extends StatelessWidget {
  const AppDrawer({super.key});

  @override
  Widget build(BuildContext context) {
    final currentPath = GoRouterState.of(context).matchedLocation;
    final loc = AppLocalizations.of(context)!;

    return Drawer(
      backgroundColor: AppTheme.backgroundDark,
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.fromLTRB(16, 48, 16, 16),
            color: AppTheme.surfaceDark,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  loc.appTitle,
                  style: const TextStyle(
                    color: AppTheme.neonGreen,
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 12),
                const LanguageSwitcher(),
              ],
            ),
          ),
          _NavTile(
            icon: Icons.list_alt,
            label: loc.navQueue,
            route: AppRoutes.queue,
            selected: currentPath == AppRoutes.queue,
          ),
          _NavTile(
            icon: Icons.storage,
            label: loc.navCubes,
            route: AppRoutes.cubeSearch,
            selected: currentPath.startsWith('/cubes'),
          ),
          _NavTile(
            icon: Icons.work_history,
            label: loc.navJobs,
            route: AppRoutes.jobs,
            selected: currentPath == AppRoutes.jobs,
          ),
          _NavTile(
            icon: Icons.report_problem,
            label: loc.navExceptions,
            route: AppRoutes.exceptions,
            selected: currentPath == AppRoutes.exceptions,
          ),
          _NavTile(
            icon: Icons.bar_chart,
            label: loc.navKpi,
            route: AppRoutes.kpi,
            selected: currentPath == AppRoutes.kpi,
          ),
        ],
      ),
    );
  }
}

class _NavTile extends StatelessWidget {
  const _NavTile({
    required this.icon,
    required this.label,
    required this.route,
    required this.selected,
  });

  final IconData icon;
  final String label;
  final String route;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(
        icon,
        color: selected ? AppTheme.neonGreen : AppTheme.textSecondary,
      ),
      title: Text(
        label,
        style: TextStyle(
          color: selected ? AppTheme.neonGreen : AppTheme.textPrimary,
          fontWeight: selected ? FontWeight.bold : FontWeight.normal,
        ),
      ),
      selected: selected,
      onTap: () {
        Navigator.pop(context); // close drawer
        if (!selected) {
          context.go(route);
        }
      },
    );
  }
}
