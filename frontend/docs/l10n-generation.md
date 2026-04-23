# l10n code generation policy

## Committed generated files

`lib/l10n/generated/*.dart` is committed to the repository. Regeneration is
deterministic given:
- Flutter SDK version (pinned in project)
- `flutter_localizations` package version (from SDK)
- `intl` package version (from SDK)
- ARB file content

## When to regenerate

Any time `lib/l10n/*.arb` changes:

```bash
cd frontend
flutter gen-l10n
git add lib/l10n/generated/
```

The same PR that touches ARB files must commit the regenerated Dart code. CI verifies
this (see CI verification).

## CI verification

CI runs:

```bash
flutter gen-l10n
git diff --exit-code lib/l10n/generated/
```

If the diff is non-empty, the PR is out of sync with its ARB files. Fix locally,
regenerate, commit, push.

## Why committed (not regenerated in CI only)

- Stable review UX: reviewers see exact Dart output in PR diff
- Deterministic across developer machines without relying on identical tooling state
- Standard Flutter project convention
