class Hub_Metadata:
    def __init__(self, cond: str, value: str | int) -> None:
        self.cond = cond
        self.value = value


class Hub:
    def __init__(self, name: str, x: int, y: int, meta: Hub_Metadata) -> None:
        self.name = name
        self.x = x
        self.y = y
        self.meta = meta


class Con_Metadata:
    def __init__(self, cond: str, value: int) -> None:
        self.cond = cond
        self.value = value


class Connection:
    def __init__(self, hub1: str, hub2: str, meta: Con_Metadata) -> None:
        self.hub1 = hub1
        self.hub2 = hub2
        self.meta = meta
