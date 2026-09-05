# FH6 Scenic Navigator v1.20.0 — Public Preview

HUD-free navigation for Forza Horizon 6: keep the game screen clean and move navigation to a second monitor, tablet or phone.

- Live UDP telemetry: car position, speed and next-turn guidance.
- **DRIVE** follows your route while you cruise.
- **PLAN** lets you search the map, choose stops and save scenic journeys.
- **823 locations/catalog entries:** 796 game records and 27 curated destinations.
- Directed road-aware routing, including one-way roads and turn restrictions.
- Second-screen support through a browser on the same LAN.
- Portable Windows x64 EXE with embedded Python; no separate Python installation.

## Start driving

Run the EXE, click Start Navigator, then set FH6 Data Out to ON, the host IP shown by the launcher, and PORT 1234. Open DRIVE or build a route in PLAN.

## Preview limitations

772 game records have approximate road-network positions; 24 retain source-exact coordinates. This preview is not a precise collectible guide. Uncached map imagery requires internet. Original code is MIT licensed; third-party data redistribution review remains separate. See LICENSE_SCOPE.md and docs/PROVENANCE_REVIEW.md.

## Technical changes

Deterministic SQLite connection cleanup on Windows; full pytest collection with Windows CI; platform-scoped FIFO test; Win32 message memory copying compatible with go vet; refreshed screenshots and documentation.

## Verification status

Published on 2026-09-05 with owner approval. Automated regression, embedded-runtime integration and release integrity checks passed; both public EXE downloads match their SHA-256. Actual FH6 driving, physical LAN access, Firewall interaction and native GUI Start/normal Close remain unverified. VirusTotal is deferred by the owner; no scan result is claimed. See [the verification report](docs/release/VERIFICATION.md).
