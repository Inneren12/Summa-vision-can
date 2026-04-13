import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import '../../domain/cube_catalog_entry.dart';

/// A single cube entry in the search results list.
class CubeSearchTile extends StatelessWidget {
  const CubeSearchTile({
    super.key,
    required this.entry,
    required this.onTap,
  });

  final CubeCatalogEntry entry;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).extension<SummaTheme>()!;
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Top row: badges
              Row(
                children: [
                  // Frequency badge
                  _Badge(
                    label: entry.frequency,
                    color: theme.accent,
                  ),
                  if (entry.archiveStatus) ...[
                    const SizedBox(width: 8),
                    _Badge(
                      label: 'Archived',
                      color: theme.textMuted,
                    ),
                  ],
                  const Spacer(),
                  // Product ID muted
                  Text(
                    entry.productId,
                    style: TextStyle(
                      color: theme.textSecondary,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              // Title
              Text(
                entry.titleEn,
                style: TextStyle(
                  color: theme.textPrimary,
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 6),
              // Subject tag
              Text(
                entry.subjectEn,
                style: TextStyle(
                  color: theme.textSecondary,
                  fontSize: 13,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Badge extends StatelessWidget {
  const _Badge({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color, width: 1),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: 11,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
