from __future__ import annotations

import re
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

    def validate(self) -> None:
        if self._start is None:
            raise MapParseError("map defines no start_hub zone")
        if self._end is None:
            raise MapParseError("map defines no end_hub zone")

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


_NB_DRONES_RE = re.compile(r"nb_drones: (\d+)$")
_HUB_RE = re.compile(r"(\w+): (\w+) (-?\d+) (-?\d+)(?: \[(.+)])?$")
_CONNECTION_RE = re.compile(r"connection: (\w+)-(\w+)(?: \[(.+)])?$")

_HUB_CLASSES: dict[str, type[Hub]] = {
    "start_hub": StartHub,
    "hub": Hub,
    "end_hub": EndHub,
}

_ZONE_METADATA_KEYS = {"color", "zone", "max_drones"}
_CONNECTION_METADATA_KEYS = {"max_link_capacity"}


def _positive_int(value: str, what: str, line_no: int) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise MapParseError(
            f"line {line_no}: {what} must be an integer, got {value!r}"
        ) from None
    if parsed <= 0:
        raise MapParseError(
            f"line {line_no}: {what} must be a positive integer, "
            f"got {parsed}"
        )
    return parsed


def _parse_zone_options(
    options: str | None, line_no: int
) -> tuple[str | None, Zone, int | None]:
    color: str | None = None
    zone = Zone.NORMAL
    max_drones: int | None = None
    if options is None:
        return color, zone, max_drones
    for option in options.split(" "):
        key, sep, value = option.partition("=")
        if not sep or key not in _ZONE_METADATA_KEYS:
            raise MapParseError(
                f"line {line_no}: invalid zone metadata: {option!r}"
            )
        if key == "color":
            color = value
        elif key == "zone":
            try:
                zone = Zone[value.upper()]
            except KeyError:
                raise MapParseError(
                    f"line {line_no}: invalid zone type: {value!r}"
                ) from None
        elif key == "max_drones":
            max_drones = _positive_int(value, "max_drones", line_no)
    return color, zone, max_drones


def _parse_connection_options(
    options: str | None, line_no: int
) -> int:
    if options is None:
        return 1
    capacity = 1
    for option in options.split(" "):
        key, sep, value = option.partition("=")
        if not sep or key not in _CONNECTION_METADATA_KEYS:
            raise MapParseError(
                f"line {line_no}: invalid connection metadata: {option!r}"
            )
        capacity = _positive_int(value, "max_link_capacity", line_no)
    return capacity


def _parse_hub_line(line: str, line_no: int) -> Hub:
    match = _HUB_RE.match(line)
    if match is None:
        raise MapParseError(f"line {line_no}: unrecognized line: {line!r}")
    kind, name, x_str, y_str, options = match.groups()
    hub_class = _HUB_CLASSES.get(kind)
    if hub_class is None:
        raise MapParseError(f"line {line_no}: unknown zone type: {kind!r}")
    color, zone, max_drones = _parse_zone_options(options, line_no)
    if hub_class is Hub:
        return Hub(name, int(x_str), int(y_str), zone, color,
                   max_drones if max_drones is not None else 1)
    # max_drones is meaningless on start_hub/end_hub: silently ignored,
    # as required by the subject (not a validation error)
    return hub_class(name, int(x_str), int(y_str), zone, color)


def parse_map(path: str) -> Graph:
    with open(path, "r") as f:
        lines = f.readlines()

    nb_drones: int | None = None
    graph: Graph | None = None

    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if nb_drones is None:
            match = _NB_DRONES_RE.match(line)
            if match is None:
                raise MapParseError(
                    f"line {line_no}: the first line must be "
                    f"'nb_drones: <positive_integer>'"
                )
            nb_drones = _positive_int(match.group(1), "nb_drones", line_no)
            assert nb_drones is not None
            graph = Graph(nb_drones)
            continue

        assert graph is not None

        if _HUB_RE.match(line):
            graph.add_hub(_parse_hub_line(line, line_no))
            continue

        connection_match = _CONNECTION_RE.match(line)
        if connection_match:
            name1, name2, options = connection_match.groups()
            capacity = _parse_connection_options(options, line_no)
            graph.add_connection(name1, name2, capacity)
            continue

        raise MapParseError(f"line {line_no}: unrecognized line: {line!r}")

    if nb_drones is None or graph is None:
        raise MapParseError("empty map file: missing 'nb_drones' line")

    graph.validate()
    return graph
