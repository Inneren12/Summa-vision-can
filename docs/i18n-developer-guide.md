# i18n Developer Guide — Summa Vision

One-page reference for adding translations to the Next.js admin/editor.
For full policy details see `i18n-recon-slice2-inspector-validation.md`.

## TL;DR — Adding a new translated string

1. Add the key + EN value to `frontend-public/messages/en.json`.
2. Add the same key + RU translation to `frontend-public/messages/ru.json`.
3. In your component:
   ```tsx
   import { useTranslations } from 'next-intl';
   // or for Server Components:
   import { getTranslations } from 'next-intl/server';

   function MyComponent() {
     const t = useTranslations('my_namespace');
     return <button>{t('my_key')}</button>;
   }
   ```
4. If your component has tests, assertions should use the mock contract:
   ```ts
   expect(screen.getByText('my_namespace.my_key')).toBeInTheDocument();
   ```

## Test mock contract

`src/__mocks__/next-intl/index.ts` returns `"namespace.key"` format, NOT translated values.
This is intentional — tests assert on stable key identifiers, not locale-specific strings.

- Writing tests → assert on `"namespace.key"` format
- Need locale-coupled test → wrap in `NextIntlClientProvider` with real messages in that
  specific test file. Do NOT modify the global mock.

## EN-kept policy (quick reference)

Some strings stay EN in both locales. Do NOT "fix" these:

- **Tech abbreviations:** `QA`
- **Dev-facing:** `debug.overlay.*`, `inspector.meta.*`
- **Short toolbar tokens:** `SAVE`, `IMPORT`, `EXPORT`, `DBG`, `Tpl`, `Blk`, `Thm`
- **Data-viz terminology:** `Small Multiples`, template family names

Full list with rationale: `i18n-recon-slice2-inspector-validation.md` → "Consolidated EN-kept policy".

## Checklist — adding a new admin route

Any new admin page (e.g. `/admin/leads`, `/admin/jobs`) must be i18n-aware from day one.

- [ ] Page uses `useTranslations` or `getTranslations` — no hardcoded EN UI strings
- [ ] `generateMetadata` uses `getTranslations` for page title
- [ ] All button / label / placeholder / `aria-label` / `title` attrs go through translator
- [ ] Status badges reuse existing `*.status` keys (e.g. `draft.status`, `published.status`)
- [ ] Date/number formatting uses locale-aware formatters (`Intl.DateTimeFormat`,
      `Intl.NumberFormat`, `useFormatter` from next-intl) — NOT hardcoded formats
- [ ] New translation keys added to both `en.json` and `ru.json` in same PR
- [ ] Tests assert on `namespace.key` format, not literal text

## Checklist — adding a new block type or control

- [ ] BREG entry has `name` field (EN, for dev reference and fallback)
- [ ] `block.type.{type}.name` added to both `en.json` and `ru.json`
- [ ] For each `ctrl` entry: `block.field.{k}.{labelKind}` added to both catalogs
- [ ] For each `ctrl.opts` value: `block.option.{k}.{opt}` added to both catalogs
- [ ] `tests/i18n/catalog-coverage.test.ts` still passes

## Pluralization

Russian has 3 plural forms (`one` / `few` / `many`) plus `other` fallback. Use ICU plural
syntax in ru.json:

```json
"unresolved_comments": "{count, plural, one {# нерешённый комментарий} few {# нерешённых комментария} many {# нерешённых комментариев} other {# нерешённых комментариев}}"
```

EN version is simpler:

```json
"unresolved_comments": "{count, plural, one {# unresolved comment} other {# unresolved comments}}"
```

Call site:

```tsx
t('unresolved_comments', { count: n })
```

## Linting (heuristic)

`npm run lint:i18n` runs `eslint-plugin-i18next` with the `no-literal-string` rule elevated
to error level. It catches many hardcoded UI strings in admin/editor paths.

**Limitations — this is a heuristic, not proof of full i18n coverage:**
- `markupOnly: true` scopes detection to JSX markup. Literal strings in helper return values,
  inline config objects, and some attribute constructions may not be caught.
- Test-related attributes (`data-testid`, `className`, `id`, `role`, `key`, `type`, `name`,
  `value`) are ignored because they contain identifiers, not UI text.
- The rule cannot distinguish kept-EN policy exceptions (SAVE, DBG, etc.) from accidental
  leaks — reviewers verify against the EN-kept policy list.

The real regression prevention is `tests/i18n/catalog-coverage.test.ts` (catches missing
translations for BREG entries) plus `tests/integration/i18n-ru-mode.test.tsx` (catches
EN leaks at render time in a real provider). The ESLint rule is a fast feedback loop for
developers while editing.

**Workflow:**
1. Run `npm run lint:i18n` locally — fix warnings that are real hardcoded strings
2. Coverage test runs in CI — guards against BREG drift
3. Integration test runs in CI — guards against provider wiring / runtime regressions

## When in doubt

- Check `docs/i18n-glossary.md` for canonical translations
- Check `docs/i18n-recon-slice*.md` for specific inventory decisions
- Ask before inventing a translation for a domain-specific term
