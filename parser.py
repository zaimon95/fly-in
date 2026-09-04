from enum import Enum
import re


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
        elif self.zone == Zone.RESTRICTED:
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
        # faire un split sur le fichier de map pour avoir le nombre de drones
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
        # faire un split sur le fichier de map pour avoir le nombre de drones
        super().__init__(name, x, y, zone, color, max_drones)


class Connection:
    def __init__(
        self, hub1: str, hub2: str, max_link_capacity: int = 1
    ) -> None:
        self.hub1 = hub1
        self.hub2 = hub2
        self.max_link_capacity = max_link_capacity


class Drones:
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

    def is_arrived(self) -> None:
        if isinstance(self.hub, EndHub):
            self._arrived = True


def parse_hub() -> list[Hub]:
    hubs: list[Hub] = []
    nb_drones: int = 1
    with open("maps/easy/01_linear_path.txt", "r") as f:
        file = f.readlines()
    for line in file:
        clean_line = line.strip()
        nb_drones_var = re.match(r"(\w+): (\d)", clean_line)
        if nb_drones_var:
            groups_drone = nb_drones_var.groups()
            if groups_drone[0] == "nb_drones":
                nb_drones = int(groups_drone[1])
        hub_var = re.match(
            r"(\w+): (\w+) (\d+) (\d+)(?: \[(.+)])?", clean_line
        )
        if hub_var:
            groups = hub_var.groups()
            match groups[0]:
                case "start_hub":
                    name_sh = groups[1]
                    x_sh = int(groups[2])
                    y_sh = int(groups[3])
                    color_sh = None
                    zone_sh = Zone["normal".upper()]
                    max_drones_sh = nb_drones
                    options = groups[4]
                    if options is not None:
                        for md in options.split(" "):
                            key, _, value = md.partition("=")
                            if key == "color":
                                color_sh = value
                            elif key == "zone":
                                zone_sh = Zone[value.upper()]
                            elif key == "max_drones":
                                max_drones_sh = int(value)
                    start_hub = StartHub(
                        name_sh, x_sh, y_sh, zone_sh, color_sh, max_drones_sh
                    )
                    hubs.append(start_hub)
                case "hub":
                    name_h = groups[1]
                    x_h = int(groups[2])
                    y_h = int(groups[3])
                    color_h = None
                    zone_h = Zone["normal".upper()]
                    max_drones_h = 1
                    options = groups[4]
                    if options is not None:
                        for md in options.split(" "):
                            key, _, value = md.partition("=")
                            if key == "color":
                                color_h = value
                            elif key == "zone":
                                zone_h = Zone[value.upper()]
                            elif key == "max_drones":
                                max_drones_h = int(value)
                    hub = Hub(name_h, x_h, y_h, zone_h, color_h, max_drones_h)
                    hubs.append(hub)
                case "end_hub":
                    name_eh = groups[1]
                    x_eh = int(groups[2])
                    y_eh = int(groups[3])
                    color_eh = None
                    zone_eh = Zone["normal".upper()]
                    max_drones_eh = nb_drones
                    options = groups[4]
                    if options is not None:
                        for md in options.split(" "):
                            key, _, value = md.partition("=")
                            if key == "color":
                                color_eh = value
                            elif key == "zone":
                                zone_eh = Zone[value.upper()]
                            elif key == "max_drones":
                                max_drones_eh = int(value)
                    end_hub = EndHub(
                        name_eh, x_eh, y_eh, zone_eh, color_eh, max_drones_eh
                    )
                    hubs.append(end_hub)
    return hubs


def parse_connection() -> list[Connection]:
    connections: list[Connection] = []
    with open("maps/easy/01_linear_path.txt", "r") as f:
        file = f.readlines()
    for line in file:
        clean_line = line.strip()
        var = re.match(r"(\w+): (\w+)-(\w+)(\[(.+)])?", clean_line)
        if var:
            groups = var.groups()
            try:
                if groups[0] == "connection":
                    hub1 = groups[1]
                    # verifier que le nom
                    # représente bien un hub existant
                    hub2 = groups[2]
                    # verifier que le nom
                    # représente bien un hub existant
                    max_link_capacity = 1
                    options = groups[4]
                    if options is not None:
                        for md in options.split(" "):
                            if md.startswith("max_link_capacity="):
                                max_link_capacity = int(
                                    md.split("=")[1]
                                )
                    connection = Connection(hub1, hub2, max_link_capacity)
                    connections.append(connection)
            except Exception as e:
                print(e)
    return connections


if __name__ == "__main__":
    parse_hub()
    parse_connection()
