# Directed WVAN Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Inline execution and local merge are pre-approved.

**Goal:** Compile the supplied WVAN into an authoritative directed graph and switch Scenic Navigator active routing/rerouting to it while preserving the existing UI/overlay/POI features.

**Architecture:** Python parses/compiles WVAN to a bundled gzip JSON graph. Browser `directed_nav.js` builds spatial/transition indexes, map matches telemetry, runs A*, and exposes reroute state. `app.js` uses LabsGG only for road overlay and POI ordering.

**Tech Stack:** Python stdlib, vanilla ES modules, Node test runner, pytest.

**Spec:** `docs/superpowers/specs/2026-08-28-directed-wvan-integration-design.md`

## Tasks
- [ ] Parse WVAN nav-points, sections, metadata string tables and evidence; validate all references.
- [ ] Build directed segments/transitions; compile deterministic `fh6-navgraph-v1.json.gz` with source SHA/capabilities.
- [ ] Add server `/api/navgraph` serving bundled gzip/JSON fail-closed.
- [ ] Add browser runtime: indexes, matcher, A*, geometry/maneuvers, reroute state.
- [ ] Replace active guidance in `app.js`; keep LabsGG overlay/POI optimizer only.
- [ ] Add UI routing status/fail-closed messages and docs.
- [ ] Run Python/JS/real-asset/server/clean-ZIP verification; merge locally to master.
