class Metadata:

    def __init__(self, cond: str, value: str | int) -> None:
        self.cond = cond
        self.value = value


class Hub:

    def __init__(self, name: str, x: int, y: int, meta: Metadata) -> None:
        self.name = name
        self.x = x
        self.y = y
        self.meta = meta


class Connection:

    def __init__(self, hub1: str, hub2: str, meta: Metadata) -> None:
        self.hub1 = hub1
        self.hub2 = hub2
        self.meta = meta


class Drones:

    def __init__(self,
                 name: str,
                 x: int,
                 y: int,
                 arrived: bool,
                 inHub: bool) -> None:
        self.name = name
        self.x = x
        self.y = y
        self.arrived = False
        self.inHub = True
