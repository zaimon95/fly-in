from collections import deque

from data import Connection, Graph, Hub, Zone

NodeId = tuple[str, str]  # (kind, identifier): kind is "in"/"out"/"transit"


class Edge:
    def __init__(self, target: NodeId, capacity: int) -> None:
        self.target = target
        self.capacity = capacity
        self.flow = 0
        self.reverse: Edge | None = None

    def residual_capacity(self) -> int:
        return self.capacity - self.flow

    def __repr__(self) -> str:
        return f"Edge(-> {self.target}, cap={self.capacity}, flow={self.flow})"


class BfsNetwork:
    def __init__(self, graph: Graph) -> None:
        self._graph = graph
        self._adjacency: dict[NodeId, list[Edge]] = {}
        self._priority_nodes: set[NodeId] = set()
        self._build()

    def _add_node(self, node: NodeId) -> None:
        self._adjacency.setdefault(node, [])

    def _add_edge(
        self, source: NodeId, target: NodeId, capacity: int
    ) -> None:
        forward = Edge(target, capacity)
        backward = Edge(source, 0)
        forward.reverse = backward
        backward.reverse = forward
        self._adjacency[source].append(forward)
        self._adjacency[target].append(backward)

    def _hub_capacity(self, hub: Hub) -> int:
        if hub.max_drones == 0:
            return self._graph.nb_drones
        return hub.max_drones

    def _build(self) -> None:
        for hub in self._graph.hubs():
            if hub.zone is Zone.BLOCKED:
                continue
            node_in, node_out = ("in", hub.name), ("out", hub.name)
            self._add_node(node_in)
            self._add_node(node_out)
            self._add_edge(node_in, node_out, self._hub_capacity(hub))
            if hub.zone is Zone.PRIORITY:
                self._priority_nodes.add(node_in)

        seen: set[frozenset[str]] = set()
        for hub in self._graph.hubs():
            if hub.zone is Zone.BLOCKED:
                continue
            for neighbour, connection in self._graph.neighbours(hub):
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
        out_node = ("out", source.name)
        in_node = ("in", dest.name)
        capacity = connection.max_link_capacity
        if dest.zone is Zone.RESTRICTED:
            transit: NodeId = ("transit", f"{source.name}->{dest.name}")
            self._add_node(transit)
            self._add_edge(out_node, transit, capacity)
            self._add_edge(transit, in_node, capacity)
        else:
            self._add_edge(out_node, in_node, capacity)

    @property
    def source(self) -> NodeId:
        return "out", self._graph.start.name

    @property
    def sink(self) -> NodeId:
        return "in", self._graph.end.name

    def shortest_path(self) -> list[Edge] | None:
        dist = self._bfs_distances()
        if self.sink not in dist:
            return None
        return self._best_priority_path(dist)

    def _bfs_distances(self) -> dict[NodeId, int]:
        dist: dict[NodeId, int] = {self.source: 0}
        queue: deque[NodeId] = deque([self.source])
        while queue:
            node = queue.popleft()
            for edge in self._adjacency.get(node, []):
                if edge.residual_capacity() <= 0:
                    continue
                if edge.target not in dist:
                    dist[edge.target] = dist[node] + 1
                    queue.append(edge.target)
        return dist

    def _best_priority_path(self, dist: dict[NodeId, int]) -> list[Edge]:
        by_layer: dict[int, list[NodeId]] = {}
        for node, depth in dist.items():
            by_layer.setdefault(depth, []).append(node)

        score: dict[NodeId, int] = {self.source: 0}
        prev_edge: dict[NodeId, Edge] = {}
        prev_node: dict[NodeId, NodeId] = {}

        for layer in range(dist[self.sink]):
            for node in by_layer.get(layer, []):
                if node not in score:
                    continue
                for edge in self._adjacency.get(node, []):
                    if edge.residual_capacity() <= 0:
                        continue
                    if dist.get(edge.target) != dist[node] + 1:
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
        for edge in path:
            edge.flow += 1
            assert edge.reverse is not None
            edge.reverse.flow -= 1

    def max_flow_paths(self, max_k: int) -> list[list[Edge]]:
        results: list[list[Edge]] = []
        for _ in range(max_k):
            path = self.shortest_path()
            if path is None:
                break
            self.augment(path)
            results.append(path)
        return results

    def path_hub_names(self, path: list[Edge]) -> list[str]:
        names = [self.source[1]]
        for edge in path:
            kind, ident = edge.target
            if kind == "in":
                names.append(ident)
        return names


def find(map_path: str, max_k: int) -> list[list[str]]:
    from parser import MapParser

    graph = MapParser().parse_map(map_path)
    network = BfsNetwork(graph)
    paths = network.max_flow_paths(max_k)
    return [network.path_hub_names(path) for path in paths]


if __name__ == "__main__":
    from config import Config

    config = Config.load()
    for hub_path in find(config.map_path, config.max_paths):
        print(hub_path)