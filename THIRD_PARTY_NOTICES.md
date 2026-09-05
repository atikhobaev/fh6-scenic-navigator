# Third-party notices / references

This project is an independent utility and does not bundle raw Forza Horizon 6 navigation files or map tile sets. It does bundle a compiled graph derived from game navigation data and third-party road/catalog snapshots; these have separate provenance and are not covered by a future original-code license.

Technical references used for interoperability:

- TheBanHammer/fh6-tel — MIT licensed FH6 telemetry dashboard. Reference for FH6 Car Dash telemetry and MapGenie tile conventions: https://github.com/TheBanHammer/fh6-tel
- nottherealtar/FH6-Oversight-Dashboard — public FH6 interactive dashboard. Reference for FH6 world-position telemetry and map calibration: https://github.com/nottherealtar/FH6-Oversight-Dashboard
- Elgeryy1/forza-drive — MIT licensed (© 2026 Gerard Alvear). Reference for the ForzaLabs road-graph format, per-surface routing modes, turn-guidance concepts, Dijkstra road routing, and Labs-image → MapGenie calibration: https://github.com/Elgeryy1/forza-drive
- ForzaLabs interactive map — source provenance for the bundled FH6 road/route-node snapshot used by the legacy road overlay. Normal Navigator runtime does not download this dataset: https://forza.labsgg.com/interactive-map
- Forza Horizon Hub — public FH6 map/checklist inventory reference used to reproduce the 796-marker / 38-category catalog structure. Where exact coordinates were not retained locally, this release uses a deterministic ForzaLabs-road proxy rather than claiming an exact Hub/MapGenie position: https://forzahorizonhub.com/map/checklist
- DamnModz FH6 map pages — source reference for the 24 hidden-car (Barn Find / Treasure Car) records whose published coordinates are retained exactly in the bundled snapshot: https://damnmodz.com/wiki/forza-horizon-6/map/
- ForzaHorizon.app — community discovery reference used only by the build-time evidence/import pipeline. Runtime community records are emitted only after independent FH6 world-coordinate/WVAN validation, and any screenshot used by a future release must be cached as a local asset with provenance metadata: https://forzahorizon.app/
- MapGenie — map tile service. Tiles are fetched/cache on demand and are not bundled.

Forza Horizon and related marks are property of their respective owners. This project is not affiliated with or endorsed by Microsoft, Xbox, Playground Games, ForzaLabs, Forza Horizon Hub, ForzaHorizon.app, or MapGenie.

See [the provenance review](docs/PROVENANCE_REVIEW.md) for scope and unresolved permissions. Full reference-code notices are included in [fh6-tel MIT](static/licenses/fh6-tel-MIT.txt), [ForzaDrive MIT](static/licenses/forza-drive-MIT.txt), and [Go runtime](static/licenses/Go.txt). The embedded CPython runtime retains its own LICENSE.txt.
