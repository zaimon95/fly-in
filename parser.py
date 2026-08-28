from enum import Enum


class Zone(Enum):
    normal = 1
    blocked = 2
    restricted = 3
    priority = 4


class Hub:

    def __init__(self,
                 name: str,
                 x: int,
                 y: int,
                 zone: Zone = Zone.normal,
                 color: str | None = None,
                 max_drones: int = 1) -> None:
        self.name = name
        self.x = x
        self.y = y
        self.zone = zone
        self.color = color
        self.max_drones = max_drones

    def costs(self) -> int:
        if self.zone == Zone.blocked:
            return 0
        elif self.zone == Zone.restricted:
            return 2
        return 1


class StartHub(Hub):
    def __init__(self,
                 name: str,
                 x: int,
                 y: int,
                 zone: Zone = Zone.normal,
                 color: str | None = None,
                 max_drones: int = 5) -> None:
        # faire un split sur le fichier de map pour avoir le nombre de drones
        super().__init__(name, x, y, zone, color, max_drones)


class EndHub(Hub):
    def __init__(self,
                 name: str,
                 x: int,
                 y: int,
                 zone: Zone = Zone.normal,
                 color: str | None = None,
                 max_drones: int = 5) -> None:
        # faire un split sur le fichier de map pour avoir le nombre de drones
        super().__init__(name, x, y, zone, color, max_drones)


class Connection:

    def __init__(self,
                 hub1: str,
                 hub2: str,
                 max_link_capacity: int = 1) -> None:
        self.hub1 = hub1
        self.hub2 = hub2
        self.max_link_capacity = max_link_capacity


class Drones:

    def __init__(self,
                 name: str,
                 x: int,
                 y: int,
                 hub: Hub,
                 arrived: bool = False,
                 in_hub: bool = True) -> None:
        self.name = name
        self.x = x
        self.y = y
        self.hub = hub
        self._arrived = arrived
        self.in_hub = in_hub

    def is_arrived(self) -> None:
        if isinstance(self.hub, EndHub):
            self._arrived = True

