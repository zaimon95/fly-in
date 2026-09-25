"""Choice of the routes to use and assignment of drones to them."""

from dataclasses import dataclass, field

from data import EndHub, Graph, Hub, StartHub
from pathfinding import BfsNetwork


@dataclass
class Route:
    """A route from start to end, and the drones that will follow it.

    Attributes:
        hubs: Hubs of the route, from start to end.
        length: Number of turns needed to go through the route.
        bottleneck: Lowest capacity along the route, i.e. how many
            drones can move through its tightest point together.
        drone_ids: Numbers of the drones assigned to this route.
    """

    hubs: list[Hub]
    length: int
    bottleneck: int
    drone_ids: list[int] = field(default_factory=list)

    def finish_time_for_next_drone(self) -> int:
        """Estimate the turn at which one more drone would arrive."""
        return self.length + len(self.drone_ids) // self.bottleneck


@dataclass
class Plan:
    """The routes chosen, with their drones, and the estimated turns.

    Attributes:
        routes: The routes used.
        makespan: Estimated number of turns to deliver every drone.
    """

    routes: list[Route]
    makespan: int


class Planner:
    """Decides how many routes to use and which drone goes where.

    Every number of routes k is tried. For each k, the drones are
    assigned greedily to the route that would deliver them soonest.
    The k with the lowest estimated makespan is kept. The estimate
    ignores interactions between routes; the Simulator gives the real
    number of turns.
    """

    def __init__(self, graph: Graph) -> None:
        """Create a planner.

        Args:
            graph: The parsed map.
        """
        self._graph = graph

    def plan(self) -> Plan:
        """Compute the best plan.

        Returns:
            The plan with the lowest estimated makespan.

        Raises:
            ValueError: If no path links the start to the end.
        """
        best: Plan | None = None
        for k in range(1, self._graph.nb_drones + 1):
            candidate = self._plan_for_k(k)
            if candidate is None:
                break
            if best is None or candidate.makespan < best.makespan:
                best = candidate
        if best is None:
            raise ValueError("no path exists from start to end")
        return best

    def _plan_for_k(self, k: int) -> Plan | None:
        """Build a plan using exactly k routes.

        Args:
            k: Number of routes wanted.

        Returns:
            The plan, or None if fewer than k routes exist.
        """
        network = BfsNetwork(self._graph)
        if len(network.max_flow_paths(k)) < k:
            return None
        routes = [self._make_route(names)
                  for names in network.decompose_routes()]
        self._assign_drones(routes)
        makespan = max(
            route.length + (len(route.drone_ids) - 1) // route.bottleneck
            for route in routes
            if route.drone_ids
        )
        return Plan(routes=routes, makespan=makespan)

    def _make_route(self, names: list[str]) -> Route:
        """Build a Route from a list of hub names."""
        hubs: list[Hub] = []
        for name in names:
            hub = self._graph.get_hub(name)
            assert hub is not None
            hubs.append(hub)
        length = sum(hub.cost() for hub in hubs[1:])
        return Route(hubs=hubs, length=length,
                     bottleneck=self._bottleneck(hubs))

    def _bottleneck(self, hubs: list[Hub]) -> int:
        """Return the lowest zone or link capacity along a route."""
        capacities = [self._graph.nb_drones]
        for hub in hubs:
            if not isinstance(hub, (StartHub, EndHub)):
                capacities.append(hub.max_drones)
        for src, dst in zip(hubs, hubs[1:]):
            connection = self._graph.connection_between(src, dst)
            assert connection is not None
            capacities.append(connection.max_link_capacity)
        return min(capacities)

    def _assign_drones(self, routes: list[Route]) -> None:
        """Give each drone to the route that would deliver it soonest."""
        for drone_id in range(1, self._graph.nb_drones + 1):
            best_route = min(
                routes, key=lambda r: r.finish_time_for_next_drone()
            )
            best_route.drone_ids.append(drone_id)
