from __future__ import annotations

import re
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

    def costs(self) -> int:
        if self.zone == Zone.BLOCKED:
            return 0
        if self.zone == Zone.RESTRICTED:
            return 2
        return 1


class StartHub(Hub):
    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone: Zone = Zone.NORMAL,
        color: str | None = None,
        max_drones: int = 5,
    ) -> None:
        super().__init__(name, x, y, zone, color, max_drones)


class EndHub(Hub):
    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone: Zone = Zone.NORMAL,
        color: str | None = None,
        max_drones: int = 5,
    ) -> None:
        super().__init__(name, x, y, zone, color, max_drones)


class Connection:
    def __init__(self,
                 hub1: str,
                 hub2: str,
                 max_link_capacity: int = 1) -> None:
        self.hub1 = hub1
        self.hub2 = hub2
        self.max_link_capacity = max_link_capacity


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


_NB_DRONES_RE = re.compile(r"(\w+): (\d+)$")
_HUB_RE = re.compile(r"(\w+): (\w+) (-?\d+) (-?\d+)(?: \[(.+)])?$")
_CONNECTION_RE = re.compile(r"(\w+): (\w+)-(\w+)(?: \[(.+)])?$")

_HUB_CLASSES: dict[str, type[Hub]] = {
    "start_hub": StartHub,
    "hub": Hub,
    "end_hub": EndHub,
}


def _apply_options(
    options: str | None,
    color: str | None,
    zone: Zone,
    max_drones: int,
) -> tuple[str | None, Zone, int]:
    if options is None:
        return color, zone, max_drones
    for option in options.split(" "):
        key, _, value = option.partition("=")
        if key == "color":
            color = value
        elif key == "zone":
            zone = Zone[value.upper()]
        elif key == "max_drones":
            max_drones = int(value)
    return color, zone, max_drones


def parse_map(path: str) -> tuple[list[Hub], list[Connection]]:
    hubs: list[Hub] = []
    hubs_by_name: dict[str, Hub] = {}
    connections: list[Connection] = []
    nb_drones = 1
    with open(path, "r") as f:
        lines = f.readlines()
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        nb_drones_match = _NB_DRONES_RE.match(line)
        if nb_drones_match:
            if nb_drones_match.group(1) == "nb_drones":
                nb_drones = int(nb_drones_match.group(2))
            continue
        hub_match = _HUB_RE.match(line)
        if hub_match:
            kind, name, x_str, y_str, options = hub_match.groups()
            hub_class = _HUB_CLASSES.get(kind)
            if hub_class is None:
                raise MapParseError(f"unknown hub type: {kind!r}")
            default_max_drones = nb_drones if hub_class is not Hub else 1
            color, zone, max_drones = _apply_options(
                options, None, Zone.NORMAL, default_max_drones
            )
            hub = hub_class(name, int(x_str),
                            int(y_str),
                            zone,
                            color,
                            max_drones)

            hubs.append(hub)
            hubs_by_name[name] = hub
            continue
        connection_match = _CONNECTION_RE.match(line)
        if connection_match:
            kind, name1, name2, options = connection_match.groups()
            if kind != "connection":
                raise MapParseError(f"unexpected line: {line!r}")
            if name1 not in hubs_by_name:
                raise MapParseError(f"connection references"
                                    f"unknown hub: {name1!r}")
            if name2 not in hubs_by_name:
                raise MapParseError(f"connection references"
                                    f"unknown hub: {name2!r}")

            max_link_capacity = 1
            if options is not None:
                for option in options.split(" "):
                    if option.startswith("max_link_capacity="):
                        max_link_capacity = int(option.split("=")[1])

            connections.append(Connection(name1, name2, max_link_capacity))
            continue

        raise MapParseError(f"unrecognized line: {line!r}")

    return hubs, connections


if __name__ == "__main__":
    parsed_hubs, parsed_connections = parse_map("maps/easy/01_linear_path.txt")
