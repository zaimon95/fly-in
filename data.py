from __future__ import annotations

from collections.abc import Iterator
from enum import Enum


class Zone(Enum):
    NORMAL = 0
    BLOCKED = 1
    RESTRICTED = 2
    PRIORITY = 3


class Hub:
    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone: Zone = Zone.NORMAL,
        color: str | None = None,
        max_drones: int = 1,
    ) -> None:
        self.name = name
        self.x = x
        self.y = y
        self.zone = zone
        self.color = color
        self.max_drones = max_drones

    def cost(self) -> int:
        if self.zone == Zone.BLOCKED:
            return 0
        if self.zone == Zone.RESTRICTED:
            return 2
        return 1

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.name!r})"


class StartHub(Hub):
    # max_drones fixed at 0, used internally as an "unlimited" marker
    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone: Zone = Zone.NORMAL,
        color: str | None = None,
    ) -> None:
        super().__init__(name, x, y, zone, color, max_drones=0)


class EndHub(Hub):
    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone: Zone = Zone.NORMAL,
        color: str | None = None,
    ) -> None:
        super().__init__(name, x, y, zone, color, max_drones=0)


class Connection:
    def __init__(
        self,
        hub1: Hub,
        hub2: Hub,
        max_link_capacity: int = 1,
    ) -> None:
        self.hub1 = hub1
        self.hub2 = hub2
        self.max_link_capacity = max_link_capacity

    def other_end(self, hub: Hub) -> Hub:
        if hub is self.hub1:
            return self.hub2
        if hub is self.hub2:
            return self.hub1
        raise ValueError(f"{hub.name!r} is not an endpoint of this link")

    def endpoints(self) -> frozenset[str]:
        return frozenset((self.hub1.name, self.hub2.name))

    def __repr__(self) -> str:
        return f"Connection({self.hub1.name}-{self.hub2.name})"


class Drone:
    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        hub: Hub,
        arrived: bool = False,
        in_hub: bool = True,
    ) -> None:
        self.name = name
        self.x = x
        self.y = y
        self.hub = hub
        self._arrived = arrived
        self.in_hub = in_hub

    def is_arrived(self) -> bool:
        if isinstance(self.hub, EndHub):
            self._arrived = True
        return self._arrived


class MapParseError(ValueError):
    pass


class Graph:
    def __init__(self, nb_drones: int) -> None:
        self.nb_drones = nb_drones
        self._by_name: dict[str, Hub] = {}
        self._adjacency: dict[Hub, list[Connection]] = {}
        self._seen_links: set[frozenset[str]] = set()
        self._start: StartHub | None = None
        self._end: EndHub | None = None

    @property
    def start(self) -> StartHub:
        if self._start is None:
            raise MapParseError("map defines no start_hub zone")
        return self._start

    @property
    def end(self) -> EndHub:
        if self._end is None:
            raise MapParseError("map defines no end_hub zone")
        return self._end

    def validate(self) -> None:
        _ = self.start
        _ = self.end

    def hubs(self) -> Iterator[Hub]:
        return iter(self._by_name.values())

    def get_hub(self, name: str) -> Hub | None:
        return self._by_name.get(name)

    def add_hub(self, hub: Hub) -> None:
        if hub.name in self._by_name:
            raise MapParseError(f"duplicate zone name: {hub.name!r}")
        if isinstance(hub, StartHub):
            if self._start is not None:
                raise MapParseError("more than one start_hub zone")
            self._start = hub
        elif isinstance(hub, EndHub):
            if self._end is not None:
                raise MapParseError("more than one end_hub zone")
            self._end = hub
        self._by_name[hub.name] = hub
        self._adjacency[hub] = []

    def add_connection(
        self, name1: str, name2: str, max_link_capacity: int = 1
    ) -> None:
        hub1 = self._by_name.get(name1)
        hub2 = self._by_name.get(name2)
        if hub1 is None:
            raise MapParseError(f"connection references unknown "
                                f"zone: {name1!r}")
        if hub2 is None:
            raise MapParseError(f"connection references unknown "
                                f"zone: {name2!r}")
        connection = Connection(hub1, hub2, max_link_capacity)
        key = connection.endpoints()
        if key in self._seen_links:
            raise MapParseError(f"duplicate connection: {name1}-{name2}")
        self._seen_links.add(key)
        self._adjacency[hub1].append(connection)
        self._adjacency[hub2].append(connection)

    def neighbours(self, hub: Hub) -> Iterator[tuple[Hub, Connection]]:
        for connection in self._adjacency[hub]:
            yield connection.other_end(hub), connection
