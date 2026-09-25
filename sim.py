"""Turn-by-turn simulation of a Plan, producing the subject's output.

Rules implemented, and the interpretation chosen where the subject
leaves room for one:

- Drones in transit toward a restricted zone always land first, since
  they may not wait on the connection.
- The other drones are handled from the closest to the end to the
  farthest, so that a drone leaving a zone frees it for the drone
  behind it during the same turn.
- Starting a transit toward a restricted zone reserves a place in it
  at once, which guarantees the mandatory landing is always legal.
- A connection's capacity counts the drones that start crossing it
  during the turn. A drone ending its transit frees it.
- A turn without any movement while drones remain is a deadlock,
  reported as a SimulationError instead of looping forever.
"""

from data import Connection, EndHub, Graph, Hub, StartHub, Zone
from planner import Plan

# Where a drone is: (hub it is in, hub it is flying to if in transit).
Position = tuple[Hub, Hub | None]
Snapshot = dict[int, Position]


class SimulationError(RuntimeError):
    """Raised when the simulation cannot complete."""


class Drone:
    """State of one drone during the simulation.

    Attributes:
        drone_id: Number of the drone, shown as D<id>.
        route: Hubs the drone goes through, from start to end.
        position: Index in route of the hub the drone is in, or is
            leaving when in transit.
        in_transit: True while on a connection toward a restricted zone.
        delivered: True once the drone has reached the end.
    """

    def __init__(self, drone_id: int, route: list[Hub]) -> None:
        """Create a drone waiting at the start of its route.

        Args:
            drone_id: Number of the drone.
            route: Hubs the drone will go through.
        """
        self.drone_id = drone_id
        self.route = route
        self.position = 0
        self.in_transit = False
        self.delivered = False

    @property
    def name(self) -> str:
        """Name of the drone in the output, e.g. ``D3``."""
        return f"D{self.drone_id}"

    def current_hub(self) -> Hub:
        """Return the hub the drone is in."""
        return self.route[self.position]

    def next_hub(self) -> Hub:
        """Return the next hub on the drone's route."""
        return self.route[self.position + 1]

    def remaining_turns(self) -> int:
        """Return the number of turns left to reach the end."""
        return sum(hub.cost() for hub in self.route[self.position + 1:])

    def where(self) -> Position:
        """Return the drone's position, for the visual replay."""
        if self.in_transit:
            return (self.current_hub(), self.next_hub())
        return (self.current_hub(), None)


class Simulator:
    """Runs a Plan turn by turn while enforcing the subject's rules."""

    def __init__(self, graph: Graph, plan: Plan,
                 max_turns: int = 10000) -> None:
        """Prepare the simulation.

        Args:
            graph: The parsed map.
            plan: The routes and their drones.
            max_turns: Safety limit on the number of turns.
        """
        self._graph = graph
        self._max_turns = max_turns
        self._occupancy: dict[Hub, int] = {}
        self._drones: list[Drone] = []
        self._snapshots: list[Snapshot] = []
        for route in plan.routes:
            for drone_id in route.drone_ids:
                self._drones.append(Drone(drone_id, route.hubs))
        self._drones.sort(key=lambda d: d.drone_id)

    @property
    def snapshots(self) -> list[Snapshot]:
        """Position of every drone before the first turn and after each.

        Filled by run(): snapshots[0] is the initial state, and
        snapshots[i] the state after turn i.
        """
        return self._snapshots

    def run(self) -> list[str]:
        """Simulate until every drone is delivered.

        Returns:
            One output line per turn, in the subject's format.

        Raises:
            SimulationError: On a deadlock or if max_turns is exceeded.
        """
        lines: list[str] = []
        self._snapshots = [self._snapshot()]
        while any(not drone.delivered for drone in self._drones):
            if len(lines) >= self._max_turns:
                raise SimulationError(
                    f"simulation exceeded {self._max_turns} turns"
                )
            moves = self._step()
            if not moves:
                raise SimulationError(
                    f"deadlock at turn {len(lines) + 1}: no drone can move"
                )
            moves.sort(key=lambda move: move[0])
            lines.append(" ".join(text for _, text in moves))
            self._snapshots.append(self._snapshot())
        return lines

    def _snapshot(self) -> Snapshot:
        """Return the current position of every drone."""
        return {drone.drone_id: drone.where() for drone in self._drones}

    def _step(self) -> list[tuple[int, str]]:
        """Play one turn.

        Returns:
            The moves of the turn, as (drone id, output text) pairs.
        """
        moves: list[tuple[int, str]] = []
        moved: set[int] = set()
        link_usage: dict[Connection, int] = {}

        for drone in self._drones:
            if drone.in_transit:
                self._land(drone)
                moves.append((drone.drone_id,
                              f"{drone.name}-{drone.current_hub().name}"))
                moved.add(drone.drone_id)

        waiting = [d for d in self._drones
                   if not d.delivered and d.drone_id not in moved]
        waiting.sort(key=lambda d: (d.remaining_turns(), d.drone_id))
        for drone in waiting:
            text = self._try_move(drone, link_usage)
            if text is not None:
                moves.append((drone.drone_id, text))
        return moves

    def _land(self, drone: Drone) -> None:
        """End a drone's transit in its restricted zone.

        The place was reserved when the transit started, so no
        capacity check is needed.
        """
        drone.in_transit = False
        drone.position += 1
        if isinstance(drone.current_hub(), EndHub):
            drone.delivered = True

    def _try_move(
        self, drone: Drone, link_usage: dict[Connection, int]
    ) -> str | None:
        """Move a drone to its next hub if capacities allow it.

        Args:
            drone: The drone to move.
            link_usage: Drones already crossing each connection this
                turn, updated in place.

        Returns:
            The output text of the move, or None if the drone waits.

        Raises:
            SimulationError: If the route uses a missing connection.
        """
        src, dst = drone.current_hub(), drone.next_hub()
        connection = self._graph.connection_between(src, dst)
        if connection is None:
            raise SimulationError(f"no connection {src.name}-{dst.name}")
        if link_usage.get(connection, 0) >= connection.max_link_capacity:
            return None
        if not self._has_room(dst):
            return None

        link_usage[connection] = link_usage.get(connection, 0) + 1
        self._leave(src)
        self._enter(dst)
        if dst.zone is Zone.RESTRICTED:
            drone.in_transit = True
            link_name = f"{connection.hub1.name}-{connection.hub2.name}"
            return f"{drone.name}-{link_name}"
        drone.position += 1
        if isinstance(dst, EndHub):
            drone.delivered = True
        return f"{drone.name}-{dst.name}"

    @staticmethod
    def _is_unlimited(hub: Hub) -> bool:
        """Return True for the start and end hubs, which have no limit."""
        return isinstance(hub, (StartHub, EndHub))

    def _has_room(self, hub: Hub) -> bool:
        """Return True if one more drone can enter the hub."""
        if self._is_unlimited(hub):
            return True
        return self._occupancy.get(hub, 0) < hub.max_drones

    def _leave(self, hub: Hub) -> None:
        """Record a drone leaving a hub."""
        if not self._is_unlimited(hub):
            self._occupancy[hub] -= 1

    def _enter(self, hub: Hub) -> None:
        """Record a drone entering (or reserving a place in) a hub."""
        if not self._is_unlimited(hub):
            self._occupancy[hub] = self._occupancy.get(hub, 0) + 1
