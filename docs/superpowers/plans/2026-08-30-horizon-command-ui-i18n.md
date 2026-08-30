# Horizon Command UI + i18n Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Inline execution and local merge are pre-approved.

**Goal:** Ship FH6 Scenic Navigator v1.18 with a stable Tailwind-based AAA UI, four runtime locales, and exact game-localized POI names where available.

**Architecture:** Keep routing/backend modules untouched. Add shared browser i18n/place-name modules, a read-only Python StringTable cache builder, and one compiled Tailwind stylesheet used by DRIVE and PLAN. Migrate dynamic UI rendering to translation/name helpers while preserving existing DOM IDs and API contracts.

**Tech Stack:** Python 3 stdlib, vanilla ES modules, node:test, Tailwind CSS v4 CLI, existing HTML/SVG/Canvas UI.

**Spec:** `docs/superpowers/specs/2026-08-30-horizon-command-ui-i18n-design.md`

## Global Constraints
- Directed WVAN remains authoritative; no routing algorithm changes.
- Runtime remains offline for app UI and POI media.
- Four locales are exactly `en-US`, `zh-CN`, `ru-RU`, `es-419`.
- Official POI localization is exact-match only; ambiguity falls back to English.
- No Tailwind CDN; ship compiled local CSS.
- Preserve the v1.17.2 catalog/gesture/popover functionality.

---

### Task 1: i18n core and exact FH6 POI localization
**Files:** create `static/i18n.js`, `static/place_locale.js`, `game_localization.py`, `tests/i18n_ui.test.mjs`, `tests/test_game_localization.py`; create/update `static/data/place_names.json`.
**Produces:** `t`, `translateForLocale`, `applyTranslations`, `bindLocaleSelect`, `localizedPlaceName`, StringTable parser/cache builder.
- [ ] Add tests for four locale set, translation fallback, exact POI locale fallback, StringTable table+hash matching, and ambiguity skip.
- [ ] Verify tests fail for missing integration/behavior.
- [ ] Implement/finish core modules and cache builder.
- [ ] Run targeted Python/JS tests.
- [ ] Commit.

### Task 2: Tailwind v4 Horizon Command shell
**Files:** modify `package.json`, create `scripts/build_tailwind.mjs`, `static/styles/app.css`, generate `static/styles/tailwind.css`, modify `static/index.html`, `static/planner/index.html`, adjust Planner legacy CSS only where needed.
**Produces:** fixed-size shared controls, shared DRIVE/PLAN shell, responsive breakpoints, reduced-motion turn alert styles.
- [ ] Add/modernize structure tests so they verify semantic behavior through external CSS and i18n attributes rather than legacy inline CSS/Russian literals.
- [ ] Verify RED against incomplete shell.
- [ ] Build local Tailwind output and finish shell CSS/HTML.
- [ ] Run UI structure tests.
- [ ] Commit.

### Task 3: PLAN runtime i18n + localized place names
**Files:** modify `static/planner/planner.js`, `static/planner/layers.js`, and small helpers if required.
**Produces:** live locale change, translated layers/actions/statuses/prompts, localized POI titles in search/popover/route UI.
- [ ] Add tests asserting Planner imports/binds i18n/name modules and no key user-facing hard-coded status strings remain in migrated flows.
- [ ] Verify RED.
- [ ] Implement imports, locale-change rerender, translations, and localized names.
- [ ] Run all Planner tests.
- [ ] Commit.

### Task 4: DRIVE runtime i18n + localized waypoint names
**Files:** modify `static/app.js`.
**Produces:** live locale change, translated toolbar/status/turn/routing/track strings, localized route/next waypoint names.
- [ ] Add tests for Drive i18n integration and localized waypoint rendering.
- [ ] Verify RED.
- [ ] Implement imports, bootstrap, locale-change rerender, dynamic string replacements, localized names.
- [ ] Run Drive/nav tests.
- [ ] Commit.

### Task 5: release verification and packaging
**Files:** update version/docs only where needed; create final ZIP outside repo.
- [ ] Build Tailwind production CSS.
- [ ] Run Python suite.
- [ ] Run complete JS suite.
- [ ] Run catalog validator and `git diff --check`.
- [ ] Scan runtime for accidental Tailwind CDN/external image dependencies and raw game assets.
- [ ] Use verification-before-completion and finishing-a-development-branch.
- [ ] Merge `feature/ui-refactor` to local `master`, rerun verification, create clean ZIP.
