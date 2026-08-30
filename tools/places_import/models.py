from __future__ import annotations
from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class SourceRef:
    provider: str
    source_id: str
    url: str | None = None
    retrieved_at: str | None = None


@dataclass(frozen=True)
class RawPlace:
    provider: str
    source_id: str
    name: str
    category: str
    map_x: float | None = None
    map_y: float | None = None
    world_x: float | None = None
    world_y: float | None = None
    world_z: float | None = None
    aliases: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()
    region: str | None = None
    sources: tuple[SourceRef, ...] = ()

    def __post_init__(self):
        if not self.sources:
            url = self.provenance[0] if self.provenance else None
            object.__setattr__(self, "sources", (SourceRef(self.provider, self.source_id, url),))
