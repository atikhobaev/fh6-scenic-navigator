# FH6 Scenic Navigator v1.18 — Horizon Command UI + i18n Design

**Date:** 2026-08-30
**Status:** Approved in chat
**Base:** FH6 Scenic Navigator v1.17.2 FULL 796 UI FIXES

## Goal
Refactor DRIVE and PLAN into one stable AAA-style map-first UI system using Tailwind CSS v4 while preserving all routing, map, POI, popover, gesture, and offline behavior. Add runtime language switching for English, Simplified Chinese, Russian, and Latin American Spanish. Official POI display names use FH6 StringTables where exact matches are available and fall back to the English game name.

## Visual system
- Product direction: “Horizon Command” — restrained AAA companion-tool UI, graphite surfaces, precise hierarchy, high-contrast navigation accent, compact controls, minimal layout motion.
- Map remains visually dominant in PLAN and DRIVE.
- Controls have fixed heights/width reservations so labels and status changes do not shift neighboring controls.
- Shared tokens/components live in one Tailwind source; existing Planner map/marker geometry CSS may remain separate where it is tightly coupled to map behavior.
- Runtime ships precompiled local CSS; no Tailwind CDN and no network dependency for UI styling.

## i18n
Locales: `en-US`, `zh-CN`, `ru-RU`, `es-419`.
- One persisted locale shared by DRIVE and PLAN.
- All static and dynamic UI strings go through the same translation layer.
- Language can be switched without reload.
- Unknown/missing UI keys fall back to English.

## POI names
- Read-only build-time importer reads game StringTable archives: `EN.zip`, `CHS.zip`, `RU.zip`, `MX.zip`.
- Exact identity is established from a unique English StringTable value and preserved by table + hash lookup across locales.
- Ambiguous matches are skipped; no guessed or machine-translated official POI names.
- Runtime cache is `static/data/place_names.json`.
- Display fallback: selected locale official name → English official name → existing canonical English/game name.
- Community/user-created names are not automatically translated.

## Compatibility
- Directed WVAN remains authoritative for routing.
- No React/Vue rewrite; keep vanilla ES modules and existing API contracts.
- Existing element IDs required by Planner/Drive JS remain stable unless tests and call sites are migrated together.
- Existing 796-place catalog, offline media, clustering, marker gesture arbitration, route editor, built-in Grand Tour, and local startup remain intact.

## Acceptance
1. DRIVE and PLAN share a coherent Horizon Command visual system.
2. Toolbars do not jump when status/labels change.
3. Four locales switch live and persist.
4. Static and dynamic UI are localized.
5. POIs use exact FH6 localized names when available, with English fallback.
6. Tailwind is compiled locally and runtime has no Tailwind/CDN dependency.
7. Full Python + JS regression suites pass.
8. Clean ZIP excludes development caches, node_modules, Git metadata, and raw game assets.
