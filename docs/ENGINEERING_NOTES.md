# Engineering Notes — how FH6 Scenic Navigator became road-legal

This document records the main engineering problems solved while building FH6 Scenic Navigator, with emphasis on the two areas that changed the project the most: **complex interchanges** and **one-way traffic legality**.

The short version is simple: a pretty polyline is not enough for navigation. A route can look correct on a map and still be impossible to drive if the graph ignores direction, ramps, forbidden transitions, or which carriageway the car is actually on.

## 1. The first routing model was not enough

The early navigator could build road-following paths from community road geometry. That worked well on ordinary roads, but it exposed a fundamental limitation around multilane junctions and motorway-style ramps.

If every nearby road segment is treated as bidirectional, a shortest-path solver may legally — from the graph's point of view — do things that are illegal in the game:

- enter a one-way ramp backwards;
- jump from one side of a divided road to the other;
- take a connection that visually crosses another road but is not actually connected;
- choose an impossible turn inside a stacked interchange;
- reverse immediately instead of following the legal loop around the junction.

This is why the project eventually separated **road geometry** from **traffic legality**.

## 2. Complex interchanges: geometry is not connectivity

### The problem

Complex interchanges are difficult because several road pieces can be extremely close in X/Z space while representing completely different legal paths. A top-down map can show two ramps crossing almost at the same position, but one may be above the other or connected only several hundred metres later.

A nearest-line or nearest-node algorithm therefore cannot be trusted to infer connectivity by distance alone.

### The solution: Directed WVAN as routing authority

The final routing authority is a compiled directed graph called `fh6-navgraph-v1`, derived from locally owned FH6 WVAN navigation data.

Instead of inventing connections from proximity, the compiler preserves the structure present in the game navigation data:

- ordered road/navigation sections;
- exact shared **NavPoint** identifiers for real connections;
- directed transitions between those points;
- `oneway_forward` directionality;
- explicit `no_right_turn` restrictions where available.

That changes the question from:

> "Which road line is closest to this one?"

into:

> "Which directed transition does the game's navigation structure actually allow?"

ForzaLabs/community road data is still useful for visual road geometry, map overlays, surface information and other presentation tasks. It is **not** the final authority for whether the car may legally travel from A to B. That responsibility belongs to Directed WVAN.

## 3. One-way roads and legal direction

A normal undirected graph stores a road connection as:

```text
A <-> B
```

For a one-way road, that is wrong. The correct graph may be only:

```text
A -> B
```

The WVAN compiler therefore preserves `oneway_forward` rather than automatically generating a reverse edge.

This matters most on:

- motorway ramps;
- divided urban roads;
- roundabout-like structures;
- slip roads;
- multi-level junctions;
- short connector roads inside larger interchanges.

The route planner can now find a slightly longer path that is actually drivable instead of a shorter path that requires driving against traffic.

## 4. Turn restrictions instead of geometric guessing

Direction alone does not solve every junction. Two directed roads may meet at the same NavPoint while a specific turn is still forbidden.

Where the source navigation data exposes an explicit restriction such as `no_right_turn`, the compiled graph carries that restriction into route legality.

The important design rule is conservative: **do not manufacture a transition just because the geometry appears to permit it**.

## 5. Why immediate U-turns are intentionally blocked

During reverse engineering, the numeric semantics of the WVAN `uturn` field were not proven strongly enough to use as authoritative traffic rules.

Rather than guess, the navigator uses a safer rule:

- immediate reverse / U-turn transitions are forbidden;
- a legal reversal through a loop, roundabout or interchange remains possible if the directed graph contains the normal sequence of legal transitions.

This is one example of the project's **fail-closed** philosophy: unknown traffic semantics should not silently turn into permissive routing.

## 6. Fail-closed routing

When Directed WVAN is available, active DRIVE/PLAN navigation does not fall back to a legacy bidirectional shortest-path route just to produce an answer.

If the graph cannot find a legal directed path, the correct result is effectively:

```text
No route found through allowed directions
```

That is better than showing a route that sends the driver backwards up a ramp.

This behavior is deliberately described as **fail-closed**.

## 7. Map matching: knowing which ramp the car is on

Legal graph construction solves only half of the interchange problem. The navigator also has to decide which directed segment corresponds to the live car telemetry.

Using only nearest distance is unreliable when two ramps run side by side. Runtime map matching therefore combines several signals:

1. **X/Z distance** to candidate directed segments;
2. **yaw / bearing agreement** between the car and the segment direction;
3. **previous-segment continuity**, so the match prefers a plausible continuation instead of jumping between nearby parallel roads.

This is especially important around multilane junctions, flyovers and closely spaced entry/exit ramps.

## 8. Rerouting after leaving the legal corridor

A brief GPS/telemetry deviation should not immediately rebuild the route, but a genuine missed turn should.

The current logic treats a persistent off-route state beyond roughly **45 m** for **800 ms** as a rerouting trigger. The navigator then computes a new legal directed path to the same active destination.

The delay prevents noisy telemetry from causing constant route churn while still reacting quickly after a wrong exit.

## 9. How the routing layers are divided

The final architecture intentionally gives different data sources different jobs:

```text
ForzaLabs / community road geometry
        |
        +-- visual road shape
        +-- map overlay / presentation
        +-- surface/context metadata

FH6 WVAN navigation data
        |
        +-- true NavPoint connectivity
        +-- directed movement
        +-- one-way legality
        +-- turn restrictions
        +-- active routing authority
        |
        v
fh6-navgraph-v1
        |
        +-- PLAN route preview
        +-- DRIVE active guidance
        +-- map matching
        +-- rerouting
```

This separation is what finally made complicated junctions behave more like a real navigator instead of a generic line-following demo.

## 10. Other development problems solved

### Portable one-file launcher

The project originally depended on scripts and an external Python environment. The final Windows distribution embeds the application payload plus the official CPython 3.13.5 x64 embeddable runtime into one native Go/Win32 launcher.

The launcher exposes clear startup stages instead of leaving a console apparently frozen while large data is prepared.

### Orphan Python processes

A previous launcher could close while leaving the Python Navigator server running in the background. The final lifecycle design attaches the child process tree to a Windows Job Object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`.

Closing the launcher therefore tears down the managed process tree, including crash/forced-close scenarios where ordinary cleanup callbacks may never run.

Startup also contains conservative stale-process recovery: it only terminates an old process after identifying it as a Navigator-managed process, never an unrelated program that happens to use the same port.

### Win32 UI freezing

The native launcher once appeared as "Not Responding" after Start even while its child process was doing useful work. The message loop had to remain on the same Windows OS thread that created the window, so the Go launcher now locks that goroutine with `runtime.LockOSThread()` before Win32 initialization. Logging was also kept out of the paint critical path.

### Official POI localization

POI names are not blindly machine-translated. The navigator reads installed FH6 StringTables when they are available and uses a localized name only when a mapping can be proven. Unmatched entries fall back to the official/canonical English name.

### Offline-first catalog

Runtime POI scraping was removed from the normal startup path. The release bundles the catalog and routing data needed by DRIVE/PLAN so startup is deterministic and does not depend on community websites being online.

## 11. Engineering principles that emerged

Several rules became recurring design constraints during development:

- **Traffic legality beats visual shortest path.**
- **Exact source connectivity beats proximity guessing.**
- **Unknown navigation semantics fail closed.**
- **Direction matters during both routing and map matching.**
- **Community data can enrich the map without becoming routing authority.**
- **Offline release data should be reproducible and inspectable.**
- **The launcher must make long operations visibly progress instead of looking frozen.**
- **A clean shutdown must own the entire child-process lifetime.**

## Related technical documents

- [`docs/superpowers/specs/2026-08-28-directed-wvan-integration-design.md`](superpowers/specs/2026-08-28-directed-wvan-integration-design.md)
- [`GAME_NAV_PROBE_RU.md`](../GAME_NAV_PROBE_RU.md)
- [`NAV_BINARY_PROBE_RU.md`](../NAV_BINARY_PROBE_RU.md)
- [`README_RU.md`](../README_RU.md)
