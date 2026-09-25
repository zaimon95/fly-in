"""Data model of a Fly-in map: zones, hubs, connections and the graph."""

from collections.abc import Iterator
from enum import Enum


class Zone(Enum):
    """The four zone types a hub can have."""

    NORMAL = 0
    BLOCKED = 1
    RESTRICTED = 2
    PRIORITY = 3


class Hub:
    """A zone of the network that drones can occupy.

    Attributes:
        name: Unique name of the zone.
        x: Horizontal coordinate, used for display.
        y: Vertical coordinate, used for display.
        zone: Type of the zone, which sets its movement cost.
        color: Optional display color.
        max_drones: Maximum number of drones inside at the same time.
    """

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone: Zone = Zone.NORMAL,
        color: str | None = None,
        max_drones: int = 1,
    ) -> None:
        """Create a hub.

        Args:
            name: Unique name of the zone.
            x: Horizontal coordinate.
            y: Vertical coordinate.
            zone: Type of the zone.
            color: Optional display color.
            max_drones: Capacity of the zone.
        """
        self.name = name
        self.x = x
        self.y = y
        self.zone = zone
        self.color = color
        self.max_drones = max_drones

    def cost(self) -> int:
        """Return the number of turns needed to enter this zone.

        Returns:
            2 for a restricted zone, 0 for a blocked zone (never
            entered), 1 otherwise.
        """
        if self.zone == Zone.BLOCKED:
            return 0
        if self.zone == Zone.RESTRICTED:
            return 2
        return 1

    def __repr__(self) -> str:
        """Return a debug representation, e.g. ``Hub('roof1')``."""
        return f"{type(self).__name__}({self.name!r})"


class StartHub(Hub):
    """The unique zone where all drones begin.

    Its capacity is unlimited: max_drones is set to 0, used internally
    as an "unlimited" marker.
    """

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone: Zone = Zone.NORMAL,
        color: str | None = None,
    ) -> None:
        """Create the start hub.

        Args:
            name: Unique name of the zone.
            x: Horizontal coordinate.
            y: Vertical coordinate.
            zone: Type of the zone.
            color: Optional display color.
        """
        super().__init__(name, x, y, zone, color, max_drones=0)


class EndHub(Hub):
    """The unique zone where drones are delivered.

    Its capacity is unlimited: max_drones is set to 0, used internally
    as an "unlimited" marker.
    """

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone: Zone = Zone.NORMAL,
        color: str | None = None,
    ) -> None:
        """Create the end hub.

        Args:
            name: Unique name of the zone.
            x: Horizontal coordinate.
            y: Vertical coordinate.
            zone: Type of the zone.
            color: Optional display color.
        """
        super().__init__(name, x, y, zone, color, max_drones=0)


class Connection:
    """A bidirectional link between two hubs.

    Attributes:
        hub1: First endpoint, as written in the map file.
        hub2: Second endpoint, as written in the map file.
        max_link_capacity: Maximum number of drones crossing it at once.
    """

    def __init__(
        self,
        hub1: Hub,
        hub2: Hub,
        max_link_capacity: int = 1,
    ) -> None:
        """Create a connection.

        Args:
            hub1: First endpoint.
            hub2: Second endpoint.
            max_link_capacity: Capacity of the link.
        """
        self.hub1 = hub1
        self.hub2 = hub2
        self.max_link_capacity = max_link_capacity

    def other_end(self, hub: Hub) -> Hub:
        """Return the endpoint opposite to the given one.

        Args:
            hub: One of the two endpoints.

        Returns:
            The other endpoint.

        Raises:
            ValueError: If hub is not an endpoint of this connection.
        """
        if hub is self.hub1:
            return self.hub2
        if hub is self.hub2:
            return self.hub1
        raise ValueError(f"{hub.name!r} is not an endpoint of this link")

    def endpoints(self) -> frozenset[str]:
        """Return the endpoint names, independent of their order.

        Returns:
            A frozenset, so that a-b and b-a compare equal.
        """
        return frozenset((self.hub1.name, self.hub2.name))

    def __repr__(self) -> str:
        """Return a debug representation, e.g. ``Connection(a-b)``."""
        return f"Connection({self.hub1.name}-{self.hub2.name})"


class MapParseError(ValueError):
    """Raised when a map file or a map structure is invalid."""


class Graph:
    """The zone network: hubs, connections and their adjacency.

    Attributes:
        nb_drones: Number of drones to route.
    """

    def __init__(self, nb_drones: int) -> None:
        """Create an empty graph.

        Args:
            nb_drones: Number of drones to route.
        """
        self.nb_drones = nb_drones
        self._by_name: dict[str, Hub] = {}
        self._adjacency: dict[Hub, list[Connection]] = {}
        self._seen_links: set[frozenset[str]] = set()
        self._start: StartHub | None = None
        self._end: EndHub | None = None

    @property
    def start(self) -> StartHub:
        """The start hub.

        Raises:
            MapParseError: If the map defines no start hub.
        """
        if self._start is None:
            raise MapParseError("map defines no start_hub zone")
        return self._start

    @property
    def end(self) -> EndHub:
        """The end hub.

        Raises:
            MapParseError: If the map defines no end hub.
        """
        if self._end is None:
            raise MapParseError("map defines no end_hub zone")
        return self._end

    def validate(self) -> None:
        """Check that the graph has both a start and an end hub.

        Raises:
            MapParseError: If one of them is missing.
        """
        _ = self.start
        _ = self.end

    def hubs(self) -> Iterator[Hub]:
        """Iterate over every hub of the graph."""
        return iter(self._by_name.values())

    def get_hub(self, name: str) -> Hub | None:
        """Return the hub with the given name, or None if unknown."""
        return self._by_name.get(name)

    def add_hub(self, hub: Hub) -> None:
        """Register a hub.

        Args:
            hub: The hub to add.

        Raises:
            MapParseError: On a duplicate name, or on a second start or
                end hub.
        """
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
        """Link two existing hubs, in both directions.

        Args:
            name1: Name of the first hub.
            name2: Name of the second hub.
            max_link_capacity: Capacity of the link.

        Raises:
            MapParseError: If a name is unknown, or if the link already
                exists (a-b and b-a are the same link).
        """
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

    def neighbors(self, hub: Hub) -> Iterator[tuple[Hub, Connection]]:
        """Iterate over the neighbors of a hub.

        Args:
            hub: The hub whose neighbors are wanted.

        Yields:
            Pairs of (neighbor hub, connection leading to it).
        """
        for connection in self._adjacency[hub]:
            yield connection.other_end(hub), connection

    def connection_between(self, hub1: Hub, hub2: Hub) -> Connection | None:
        """Return the connection linking two hubs, or None if none."""
        for neighbour, connection in self.neighbors(hub1):
            if neighbour is hub2:
                return connection
        return None
