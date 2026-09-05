# Provenance review — Public Preview

Reviewed 2026-09-05 from main `45f6f0d9955352fc095ec2df8a7aedc5954dd28b`. This is a source/provenance assessment, not an assertion that all redistribution permissions have been obtained. No root LICENSE has been selected.

## Recommendation for the owner's decision

**MIT for the original code**, subject to confirming authorship and resolving the data questions below. It is a simple permissive choice compatible with the MIT references identified here. LGPL is not justified merely because Rat Vision uses it. MIT would grant reuse rights only for code the owner controls; it cannot license third-party map imagery, databases or game-derived geometry. If stronger patent terms are preferred, Apache-2.0 is an alternative, but it does not resolve those data rights either.

Before adding LICENSE, the owner should confirm that the identified original modules were authored for this project and approve the license scope. Keep “source available” / “free public project” until then.

## Code and dependencies

| Component | Evidence / classification | Action |
| --- | --- | --- |
| Python server, planner services/database/importers; JS DRIVE/PLAN; Go native launcher | Project-specific implementation and tests. Reviewed module boundaries and attribution comments; complete historical authorship cannot be proven from comments alone. | Candidate original code, pending owner confirmation. |
| [TheBanHammer/fh6-tel](https://github.com/TheBanHammer/fh6-tel/tree/7ffeb0812f9f240653620ed3ecb0d2266b8d94ab) | MIT, copyright 2025 BanHammer. `telemetry.py` explicitly references community packet layout; upstream is Rust/Svelte, while this parser is a small Python implementation. | Preserve attribution and full MIT notice in `static/licenses/fh6-tel-MIT.txt`. No upstream application bundled. |
| [FH6-Oversight-Dashboard](https://github.com/nottherealtar/FH6-Oversight-Dashboard/tree/6f659d1b8a2a8fadd32ae270731529b3cfb5a6ca) | No root LICENSE found in the checked revision. Public visibility is not a license. Compared its telemetry parser and the local minimal parser: shared protocol offsets/helper concepts, different application implementation. | Treat as protocol/calibration reference only. Owner must identify any copied expressive code; obtain permission or replace such code if found. Do not attribute an MIT grant to Oversight. |
| [Elgeryy1/forza-drive](https://github.com/Elgeryy1/forza-drive/tree/a5f0db216d3617fdccb8e1bf17ecee1a35250311) | MIT, copyright 2026 Gerard Alvear. `static/routing.js` explicitly acknowledges its calibration reference; local constants reproduce the transformation. Routing concepts and road format are also cited. | Preserve attribution and full MIT notice in `static/licenses/forza-drive-MIT.txt`. Its courtesy contact request is expressly not a license condition. |
| Go runtime | Go 1.23.2 standard library; go.mod has no third-party module requirements. | BSD-style Go notice in `static/licenses/Go.txt`, included in the embedded payload. |
| CPython | Official 3.13.5 x64 embeddable ZIP, pinned SHA-256 `7d2650fd9d1b9d002d4a315d5f354247fd6a44f30517c7ef577b08f57a0fb6d9`. | Retain ZIP's LICENSE.txt, including its bundled-component notices, in the extracted runtime. |
| Tailwind | Build-time dependency declared in package.json; runtime uses a checked-in standalone stylesheet and the project's offline compiler. | Review generated CSS provenance if regenerating with the Tailwind CLI; retain applicable MIT notices for distributed portions. |

## Data and reference material — separate from a code license

| Source / files | What is actually distributed | Remaining question |
| --- | --- | --- |
| [ForzaLabs map](https://forza.labsgg.com/interactive-map), `static/data/fh6_roads.json` | Bundled legacy road/route-node snapshot, not merely a link. | No redistribution grant established by this review. Public access and attribution alone are insufficient evidence. |
| [Forza Horizon Hub checklist](https://forzahorizonhub.com/map/checklist), `builtin_places.json` | Catalog structure/categories inspired by the public 796-marker inventory. Local metadata records **772 road_network_proxy** and **24 source_exact** positions. | Confirm rights for any retained names/descriptions/database selection. Clearly disclose proxy accuracy to users. |
| [DamnModz map](https://damnmodz.com/wiki/forza-horizon-6/map/) | Source-exact coordinates for 24 hidden-car entries, as recorded in local provenance metadata. | Permission for extraction/redistribution has not been established. “Exact” describes fidelity to the source, not independent in-game validation. |
| [ForzaHorizon.app](https://forzahorizon.app/) | Build-time community evidence metadata; runtime community catalog is currently empty. | Contributor content/screenshots need explicit provenance and appropriate permission before inclusion. No community screenshots added here. |
| [MapGenie](https://mapgenie.io/) | Map tiles are fetched/cached on demand, not shipped as a tile set. Application documentation screenshots include rendered map imagery. | Review service terms and screenshot use; this review could not retrieve the terms page. Do not imply a map-data redistribution license. |
| `static/data/scenic_catalog.json`, `static/route.json` | Project's curated itinerary and anchors derived from map/game coordinates. | Curation and underlying data have separate provenance. |
| `static/data/fh6_navgraph_v1.json.gz` | **Bundled derivative of game WVAN data**: 38,473 points, 71,222 directed segments, 75,626 transitions; source SHA-256 `f06b4b958e60af5e52bc456173a5ba2b3ce6c900c732c8c5d96bd426498f5dbb`. | Not raw game files, but still game-derived data. Distribution rights must be reviewed separately; a code license does not clear them. |
| `place_names.json` / localization importer | Cached localization metadata and local-game StringTables processing. | Owner should review any already-bundled names/cache separately from the importer code. |

## Game-owned files intentionally excluded

Raw `.nav`, `.owt`, `.oww`, `.owbs`, game executables and raw StringTables are not release inputs. Repository hygiene rejects raw navigation assets. This exclusion must not be summarized as “contains no game-derived data”: the compiled graph above is distributed. Map tiles cached during smoke tests must stay outside Git and the embedded payload.

## Scope and next decision

Reviewed declared references, upstream license files at the pinned revisions, packet/calibration implementations, local data metadata, embedded-payload selection, and runtime dependencies. This is not a forensic audit of every historical commit or a permission clearance. No blanket license was added. The owner should resolve data redistribution scope and approve the proposed MIT code license before advertising the whole repository as open source.
