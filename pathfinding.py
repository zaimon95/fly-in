import parser as pa


def find(map_path: str) -> list[str]:
    graph = pa.parse_map(map_path)
    path: list[str] = [graph.start.name]
    # mettre les conditions de pathfinding, par ex. :
    # path.append(graph.start.name)
    # for neighbour, connection in graph.neighbours(graph.start):
    #     ...
    return path


if __name__ == "__main__":
    print(find("maps/easy/01_linear_path.txt"))
