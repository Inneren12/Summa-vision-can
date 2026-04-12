import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../theme/app_theme.dart';
import 'app_router.dart';

/// Shared navigation drawer shown on all top-level screens.
class AppDrawer extends StatelessWidget {
  const AppDrawer({super.key});

  @override
  Widget build(BuildContext context) {
    final currentPath = GoRouterState.of(context).matchedLocation;

    return Drawer(
      backgroundColor: AppTheme.backgroundDark,
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          DrawerHeader(
            decoration: const BoxDecoration(color: AppTheme.surfaceDark),
            child: const Text(
              'Summa Vision',
              style: TextStyle(
                color: AppTheme.neonGreen,
                fontSize: 22,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          _NavTile(
            icon: Icons.list_alt,
            label: 'Brief Queue',
            route: AppRoutes.queue,
            selected: currentPath == AppRoutes.queue,
          ),
          _NavTile(
            icon: Icons.storage,
            label: 'Cubes',
            route: AppRoutes.cubeSearch,
            selected: currentPath.startsWith('/cubes'),
          ),
          _NavTile(
            icon: Icons.bar_chart,
            label: 'KPI',
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
