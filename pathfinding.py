"""Flow network and BFS-based pathfinding over a Fly-in map.

Every hub is split into an "in" node and an "out" node, joined by an
internal edge that carries the hub's capacity (max_drones). This edge
is a capacity gate, not a move, so it costs 0 turns. A connection
leading into a restricted zone is split into two edges through a
transit node, so that it costs 2 turns. Every other connection costs
1 turn. Distances are computed with a 0-1 BFS, a deque-based BFS for
graphs whose weights are only 0 or 1.
"""

from collections import deque

from data import Connection, Graph, Hub, Zone

NodeId = tuple[str, str]  # (kind, name): kind is "in", "out" or "transit"


class Edge:
    """A directed edge of the residual network.

    Every forward edge is created together with a reverse edge of
    capacity 0. Pushing flow on one gives residual capacity to the
    other, which lets a later path cancel part of an earlier one.

    Attributes:
        target: Node the edge leads to.
        capacity: Maximum flow on the edge (0 for a reverse edge).
        weight: Number of turns the edge costs (0 or 1).
        flow: Current flow on the edge.
        reverse: The paired edge in the opposite direction.
    """

    def __init__(self, target: NodeId, capacity: int, weight: int) -> None:
        """Create an edge with no flow.

        Args:
            target: Node the edge leads to.
            capacity: Maximum flow on the edge.
            weight: Number of turns the edge costs.
        """
        self.target = target
        self.capacity = capacity
        self.weight = weight
        self.flow = 0
        self.reverse: Edge | None = None

    def residual_capacity(self) -> int:
        """Return how much more flow the edge can carry."""
        return self.capacity - self.flow

    def __repr__(self) -> str:
        """Return a debug representation of the edge."""
        return (f"Edge(-> {self.target}, cap={self.capacity}, "
                f"w={self.weight}, flow={self.flow})")


class BfsNetwork:
    """Flow network built from a Graph, solved with BFS."""

    def __init__(self, graph: Graph) -> None:
        """Build the network from a parsed graph.

        Args:
            graph: The parsed map. Blocked zones are left out.
        """
        self._graph = graph
        self._adjacency: dict[NodeId, list[Edge]] = {}
        self._priority_nodes: set[NodeId] = set()
        self._build()

    def _add_node(self, node: NodeId) -> None:
        """Register a node if it does not exist yet."""
        self._adjacency.setdefault(node, [])

    def _add_edge(
        self, source: NodeId, target: NodeId, capacity: int, weight: int
    ) -> None:
        """Add a forward edge and its paired reverse edge.

        Args:
            source: Start node.
            target: End node.
            capacity: Capacity of the forward edge.
            weight: Number of turns the edge costs.
        """
        forward = Edge(target, capacity, weight)
        backward = Edge(source, 0, weight)
        forward.reverse = backward
        backward.reverse = forward
        self._adjacency[source].append(forward)
        self._adjacency[target].append(backward)

    def _hub_capacity(self, hub: Hub) -> int:
        """Return the capacity of a hub's internal edge.

        Start and end hubs are unlimited (marker 0), which is bounded
        by the number of drones since no more flow can ever pass.
        """
        if hub.max_drones == 0:
            return self._graph.nb_drones
        return hub.max_drones

    def _build(self) -> None:
        """Create the nodes and edges of the network."""
        for hub in self._graph.hubs():
            if hub.zone is Zone.BLOCKED:
                continue
            node_in, node_out = ("in", hub.name), ("out", hub.name)
            self._add_node(node_in)
            self._add_node(node_out)
            self._add_edge(node_in, node_out, self._hub_capacity(hub), 0)
            if hub.zone is Zone.PRIORITY:
                self._priority_nodes.add(node_in)

        seen: set[frozenset[str]] = set()
        for hub in self._graph.hubs():
            if hub.zone is Zone.BLOCKED:
                continue
            for neighbour, connection in self._graph.neighbors(hub):
                if neighbour.zone is Zone.BLOCKED:
                    continue
                pair = connection.endpoints()
                if pair in seen:
                    continue
                seen.add(pair)
                self._add_directed_link(
                    connection.hub1, connection.hub2, connection
                )
                self._add_directed_link(
                    connection.hub2, connection.hub1, connection
                )

    def _add_directed_link(
        self, source: Hub, dest: Hub, connection: Connection
    ) -> None:
        """Add the edges for one direction of a connection.

        Args:
            source: Hub the drone leaves.
            dest: Hub the drone enters.
            connection: The connection, for its capacity.
        """
        out_node = ("out", source.name)
        in_node = ("in", dest.name)
        capacity = connection.max_link_capacity
        if dest.zone is Zone.RESTRICTED:
            transit: NodeId = ("transit", f"{source.name}->{dest.name}")
            self._add_node(transit)
            self._add_edge(out_node, transit, capacity, 1)
            self._add_edge(transit, in_node, capacity, 1)
        else:
            self._add_edge(out_node, in_node, capacity, 1)

    @property
    def source(self) -> NodeId:
        """Node where all flow starts: the start hub's "out" node."""
        return "out", self._graph.start.name

    @property
    def sink(self) -> NodeId:
        """Node where all flow ends: the end hub's "in" node."""
        return "in", self._graph.end.name

    def shortest_path(self) -> list[Edge] | None:
        """Find the shortest augmenting path in the residual network.

        Among paths with the same number of turns, the one crossing
        the most priority zones is chosen.

        Returns:
            The path as a list of edges, or None if the sink cannot be
            reached anymore.
        """
        dist, order = self._bfs_distances()
        if self.sink not in dist:
            return None
        return self._best_priority_path(dist, order)

    def _bfs_distances(self) -> tuple[dict[NodeId, int], list[NodeId]]:
        """Compute the distance of every reachable node (0-1 BFS).

        0-weight edges put their target at the front of the deque, so
        a node is only finalized once its shortest distance is known.

        Returns:
            The distance of each reachable node, and the order in which
            nodes were finalized.
        """
        dist: dict[NodeId, int] = {self.source: 0}
        finalized: set[NodeId] = set()
        order: list[NodeId] = []
        queue: deque[NodeId] = deque([self.source])

        while queue:
            node = queue.popleft()
            if node in finalized:
                continue
            finalized.add(node)
            order.append(node)
            for edge in self._adjacency.get(node, []):
                if edge.residual_capacity() <= 0:
                    continue
                new_dist = dist[node] + edge.weight
                if edge.target not in dist or new_dist < dist[edge.target]:
                    dist[edge.target] = new_dist
                    if edge.weight == 0:
                        queue.appendleft(edge.target)
                    else:
                        queue.append(edge.target)
        return dist, order

    def _best_priority_path(
        self, dist: dict[NodeId, int], order: list[NodeId]
    ) -> list[Edge]:
        """Rebuild the shortest path, preferring priority zones.

        Only edges lying on the shortest path are followed. Nodes are
        visited in finalization order, which is a valid order for
        those edges.

        Args:
            dist: Distances computed by the BFS.
            order: Finalization order of the nodes.

        Returns:
            The chosen path as a list of edges.
        """
        score: dict[NodeId, int] = {self.source: 0}
        prev_edge: dict[NodeId, Edge] = {}
        prev_node: dict[NodeId, NodeId] = {}

        for node in order:
            if node not in score:
                continue
            for edge in self._adjacency.get(node, []):
                if edge.residual_capacity() <= 0:
                    continue
                if dist.get(edge.target) != dist[node] + edge.weight:
                    continue
                candidate = score[node] + (
                    1 if edge.target in self._priority_nodes else 0
                )
                if candidate > score.get(edge.target, -1):
                    score[edge.target] = candidate
                    prev_edge[edge.target] = edge
                    prev_node[edge.target] = node

        path: list[Edge] = []
        node = self.sink
        while node != self.source:
            edge = prev_edge[node]
            path.append(edge)
            node = prev_node[node]
        path.reverse()
        return path

    @staticmethod
    def augment(path: list[Edge]) -> None:
        """Push one unit of flow along a path.

        Args:
            path: An augmenting path returned by shortest_path.
        """
        for edge in path:
            edge.flow += 1
            assert edge.reverse is not None
            edge.reverse.flow -= 1

    def max_flow_paths(self, max_k: int) -> list[list[Edge]]:
        """Push up to max_k units of flow (Edmonds-Karp).

        The returned paths are augmenting paths: they may use reverse
        edges, so they are not drone routes. Use decompose_routes to
        get the routes.

        Args:
            max_k: Maximum number of units to push.

        Returns:
            The augmenting paths found, fewer than max_k if the network
            becomes saturated.
        """
        results: list[list[Edge]] = []
        for _ in range(max_k):
            path = self.shortest_path()
            if path is None:
                break
            self.augment(path)
            results.append(path)
        return results

    def decompose_routes(self) -> list[list[str]]:
        """Split the final flow into drone routes.

        Starting from the source, a forward edge that still carries
        unused flow is followed until the sink. Flow conservation
        guarantees such an edge always exists.

        Returns:
            One route per unit of flow, as lists of hub names.
        """
        used: dict[int, int] = {}
        routes: list[list[str]] = []
        while True:
            names = self._walk_one_unit(used)
            if names is None:
                return routes
            routes.append(self._remove_loops(names))

    def _walk_one_unit(self, used: dict[int, int]) -> list[str] | None:
        """Follow one unit of flow from source to sink.

        Args:
            used: Flow already consumed on each edge, updated in place.

        Returns:
            The hub names visited, or None when no flow remains.
        """
        names = [self.source[1]]
        node = self.source
        while node != self.sink:
            edge = self._next_flow_edge(node, used)
            if edge is None:
                return None
            used[id(edge)] = used.get(id(edge), 0) + 1
            node = edge.target
            if node[0] == "in":
                names.append(node[1])
        return names

    def _next_flow_edge(
        self, node: NodeId, used: dict[int, int]
    ) -> Edge | None:
        """Return a forward edge of node with unused flow, if any."""
        for edge in self._adjacency.get(node, []):
            is_forward = edge.capacity > 0
            if is_forward and edge.flow - used.get(id(edge), 0) > 0:
                return edge
        return None

    @staticmethod
    def _remove_loops(names: list[str]) -> list[str]:
        """Cut any loop out of a route, keeping it valid and shorter."""
        result: list[str] = []
        for name in names:
            if name in result:
                del result[result.index(name) + 1:]
            else:
                result.append(name)
        return result
