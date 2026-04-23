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

CI runs (from repository root):

```bash
cd frontend
flutter gen-l10n
git diff --exit-code lib/l10n/generated/
```

If the diff is non-empty, the PR is out of sync with its ARB files. Fix locally,
regenerate, commit, push.

## Why committed (not regenerated in CI only)

- Stable review UX: reviewers see exact Dart output in PR diff
- Deterministic across developer machines without relying on identical tooling state
- Chosen repository convention for deterministic review and CI sync (both commit and
  regenerate-on-build are valid patterns in Flutter community; this repo picks commit
  for review UX)


## ARB metadata convention

- `@@locale` required in every ARB file
- `@key.description` entries live ONLY in `app_en.arb` (template ARB)
- `app_ru.arb` (and any future locale ARB) does NOT duplicate descriptions
- This follows `flutter_localizations` codegen defaults; descriptions are documentation
  aid for translators and don't need per-locale copies

When adding a new key:
1. Add `"keyName": "English text"` to `app_en.arb`
2. Add `"@keyName": { "description": "..." }` to `app_en.arb`
3. Add `"keyName": "Translation"` to `app_ru.arb` (no `@keyName` block)
