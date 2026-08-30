from dataclasses import dataclass


@dataclass(frozen=True)
class RouteMutation:
    route_id: str
    revision: int
    action: str
