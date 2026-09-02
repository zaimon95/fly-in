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
    with open("maps/easy/01_linear_path.txt", "r") as f:
        file = f.readlines()
    for line in file:
        clean_line = line.strip()
        var = re.match(
            r"(\w+): (\w+) (\d+) " + r"(\d+)(?: \[(.+)])?", clean_line
        )
        if var:
            groups = var.groups()
            match groups[0]:
                case "nb_drones":
                    nb_drones = int(groups[1])
                    print(nb_drones)
                case "start_hub":
                    name_sh = groups[1]
                    x_sh = int(groups[2])
                    y_sh = int(groups[3])
                    color_sh = None
                    zone_sh = Zone["normal".upper()]
                    max_drones_sh = 1
                    if len(groups) == 5:
                        try:
                            if groups[4].split("=")[0] == "color":
                                color_sh = (
                                    groups[4].split(" ")[0].split("=")[1]
                                )
                        except IndexError:
                            color_sh = None
                        try:
                            if groups[4].split("=")[0] == "zone":
                                zone_sh = Zone[
                                    groups[4]
                                    .split(" ")[1]
                                    .split("=")[1]
                                    .upper()
                                ]
                        except IndexError:
                            zone_sh = Zone["normal".upper()]
                        try:
                            if groups[4].split("=")[0] == "max_drones":
                                max_drones_sh = int(
                                    groups[4].split(" ")[2].split("=")[1]
                                )
                        except IndexError:
                            max_drones_sh = 1
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
                    if len(groups) == 5:
                        try:
                            if groups[4].split("=")[0] == "color":
                                color_h = groups[4].split(" ")[0].split("=")[1]
                        except IndexError:
                            color_h = None
                        try:
                            if groups[4].split("=")[0] == "zone":
                                zone_h = Zone[
                                    groups[4]
                                    .split(" ")[1]
                                    .split("=")[1]
                                    .upper()
                                ]
                        except IndexError:
                            zone_h = Zone["normal".upper()]
                        try:
                            if groups[4].split("=")[0] == "max_drones":
                                max_drones_h = int(
                                    groups[4].split(" ")[2].split("=")[1]
                                )
                        except IndexError:
                            max_drones_h = 1
                    hub = Hub(name_h, x_h, y_h, zone_h, color_h, max_drones_h)
                    hubs.append(hub)
                case "end_hub":
                    name_eh = groups[1]
                    x_eh = int(groups[2])
                    y_eh = int(groups[3])
                    color_eh = None
                    zone_eh = Zone["normal".upper()]
                    max_drones_eh = 1
                    if len(groups) == 5:
                        try:
                            if groups[4].split("=")[0] == "color":
                                color_eh = (
                                    groups[4].split(" ")[0].split("=")[1]
                                )
                        except IndexError:
                            color_eh = None
                        try:
                            if groups[4].split("=")[0] == "zone":
                                zone_eh = Zone[
                                    groups[4]
                                    .split(" ")[1]
                                    .split("=")[1]
                                    .upper()
                                ]
                        except IndexError:
                            zone_eh = Zone["normal".upper()]
                        try:
                            if groups[4].split("=")[0] == "max_drones":
                                max_drones_eh = int(
                                    groups[4].split(" ")[2].split("=")[1]
                                )
                        except IndexError:
                            max_drones_eh = 1
                    end_hub = EndHub(
                        name_eh, x_eh, y_eh, zone_eh, color_eh, max_drones_eh
                    )
                    hubs.append(end_hub)
    return hubs


if __name__ == "__main__":
    print(parse_hub())
