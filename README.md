*This project has been created as part of the 42 curriculum by sla-gran.*

# Fly-in

Drones are interesting.

## Description

Fly-in is an object-oriented drone routing simulator. Given a map made of
connected zones (a graph), it routes a fleet of drones from a unique
**start** zone to a unique **end** zone in the fewest possible simulation
turns, while respecting:

- **Zone types** with different movement costs (`normal`, `restricted`,
  `priority`, `blocked`).
- **Occupancy limits**, both per zone (`max_drones`) and per connection
  (`max_link_capacity`).
- **Turn-by-turn, conflict-free movement**: every drone's move for a turn
  is decided from the state at the start of that turn, and all capacity
  constraints are enforced simultaneously.

The program parses the map itself (no graph library is used, as required by
the subject), computes a set of routes and a drone-to-route assignment with
a max-flow / shortest-path algorithm, then replays the plan turn by turn
through a simulation engine that is the single source of truth for
correctness. The result is printed as the turn-by-turn move list required
by the subject, and can optionally be replayed in a graphical window.

## Instructions

### Requirements

- Python 3.10 or later.
- A virtual environment is created automatically by the `Makefile`
  (dependencies: `flake8`, `mypy`, `pygame` — see `requirements.txt`).

### Setup and usage

```sh
make install   # creates .venv and installs dependencies
make run       # solves the map from config.txt and prints/replays it
```

The map to solve and whether to open the graphical replay are set in
`config.txt`:

```
map_path: maps/hard/03_ultimate_challenge.txt
visual: true
```

To solve a different map, either edit `config.txt` or pass another
configuration file on the command line:

```sh
.venv/bin/python3 fly-in.py path/to/other_config.txt
```

### Other Makefile targets

| Target        | Purpose                                                       |
|---------------|----------------------------------------------------------------|
| `install`     | Create the virtual environment and install dependencies.       |
| `run`         | Run `fly-in.py` (optionally `make run CONFIG=<file>`).          |
| `debug`       | Run `fly-in.py` under Python's `pdb` debugger.                  |
| `lint`        | Run `flake8` and `mypy` with the flags required by the subject. |
| `lint-strict` | Same, with `mypy --strict`.                                    |
| `clean`       | Remove caches (`__pycache__`, `.mypy_cache`, ...).              |
| `fclean`      | `clean`, plus remove the virtual environment.                   |

If `pygame` cannot be imported (e.g. no display available), the program
still prints the textual result and simply skips the graphical replay
instead of crashing; set `visual: false` in the config file to disable it
explicitly.

## Algorithm and implementation strategy

The project is split into small, single-purpose classes:

- **`data.py`** — the graph model: `Zone` (the four zone types and their
  movement cost), `Hub`/`StartHub`/`EndHub`, `Connection`, and `Graph`
  (adjacency and lookups). This is the only place that knows what a map
  "means".
- **`parser.py`** (`MapParser`) — turns a map file into a `Graph`,
  rejecting anything that does not match the subject's syntax with a
  precise, line-numbered error.
- **`pathfinding.py`** (`BfsNetwork`) — builds a **flow network** from the
  graph:
  - Every hub is split into an *in* node and an *out* node joined by an
    internal edge carrying the hub's `max_drones` capacity, so occupancy
    limits become a flow-capacity problem.
  - Every connection becomes an edge with the connection's
    `max_link_capacity`.
  - A connection leading into a `restricted` zone is split through a
    transit node so that it costs 2 turns instead of 1, matching the
    subject's movement rules.
  - Shortest augmenting paths are found with a **0-1 BFS** (a deque-based
    BFS suited to graphs whose edge weights are only 0 or 1), which runs
    in `O(V + E)` per path instead of the `O(E log V)` of a generic
    Dijkstra. Among equally short paths, the one crossing the most
    `priority` zones is preferred, as requested by the subject.
  - Pushing up to *k* units of flow and decomposing the result into *k*
    disjoint/overlapping routes (Edmonds-Karp style) gives up to *k*
    concurrent paths, respecting every zone and link capacity by
    construction.
- **`planner.py`** (`Planner`, `Route`, `Plan`) — decides **how many**
  routes to use. It tries every route count `k` from 1 up to the number of
  drones, greedily assigns each drone to the route that would deliver it
  soonest given the route's length and bottleneck capacity, and keeps the
  `k` with the lowest *estimated* makespan. This estimate deliberately
  ignores interactions between routes (it is `O(k)` per candidate, not a
  full simulation) so that many values of `k` can be explored cheaply; the
  `Simulator` is what guarantees the real, conflict-free result.
- **`sim.py`** (`Simulator`, `Drone`) — replays the plan turn by turn and
  is the authority on correctness:
  - Drones already flying toward a restricted zone land first (they
    cannot wait mid-connection), then the remaining drones are moved
    closest-to-goal first, so a drone leaving a zone frees the space for
    the drone behind it during the very same turn (e.g. a single-file
    queue can all advance together).
  - Zone and connection occupancy are checked before any move is
    committed, so two drones can never violate a capacity limit.
  - A turn in which no drone can move while drones remain undelivered is
    detected and reported as a deadlock instead of looping forever; a
    disconnected start/end is detected the same way, before any turn is
    simulated.
  - Every turn's state is recorded as a `Snapshot` (each drone's current
    hub, and the hub it is flying to if in transit), which the visualizer
    later replays.

**Complexity**: for a map with `V` zones/nodes and `E` connections, finding
one shortest augmenting path is `O(V + E)` (0-1 BFS), and the planner
explores at most `nb_drones` values of `k`, each requiring at most `k`
augmenting paths — so building the plan is `O(D² · (V + E))` in the worst
case for `D` drones, which stays fast for the map sizes used here (up to 25
drones). No path is recomputed at simulation time: the simulator only
replays the fixed routes decided by the planner, so its cost is
`O(turns · drones)`. Memory usage is linear in the size of the map (nodes
and edges of the flow network) plus one route per drone.

## Visual representation

Two complementary outputs are produced, matching the subject's
requirement for visual feedback:

- **Text output** (always shown): one line per simulation turn on stdout,
  in the exact `D<id>-<zone>` / `D<id>-<connection>` format required by
  the subject, followed by the total number of turns on stderr.
- **Graphical replay** (`visualizer.py`, opt-out via `visual: false`): a
  `pygame` window that smoothly animates every drone between the
  positions recorded turn by turn by the `Simulator`. It shows:
  - Each hub at its map coordinates, in its declared `color` (or a
    default gray), with a distinct outline per zone type — a gold ring
    for `priority`, a double red ring for `restricted`, a black cross for
    `blocked`.
  - Each hub's current occupancy as `count/max_drones` (or just `count`
    for the unlimited start/end zones).
  - Connections drawn thicker for a higher `max_link_capacity`.
  - Drones as labelled discs, spread on a ring around a crowded hub (or
    merged into a single `x<n>` marker when too many share the same
    space), and positioned mid-link while in transit toward a restricted
    zone.
  - A HUD showing the current turn, how many drones have been delivered,
    and the moves about to happen.
  - Interactive controls: `Space` play/pause, `Left`/`Right` step one
    turn, `+`/`-` change the playback speed, `R` restart, `Esc` quit, and
    hovering a hub with the mouse shows its name.

This makes it possible to both check the raw output format required for
grading and to visually confirm — at a glance — that occupancy, capacity
and restricted-zone rules are respected.

## Example

Given `maps/easy/02_simple_fork.txt` (4 drones, a start zone splitting into
two parallel one-zone paths that both rejoin at the end zone):

```
nb_drones: 4

start_hub: start 0 0 [color=green]
hub: junction 1 0 [color=yellow max_drones=2]
hub: path_a 2 1 [color=blue]
hub: path_b 2 -1 [color=blue]
end_hub: goal 3 0 [color=red]

connection: start-junction [max_link_capacity=2]
connection: junction-path_a
connection: junction-path_b
connection: path_a-goal
connection: path_b-goal
```

running `make run` with this map configured (and `visual: false`) prints:

```
D1-junction D2-junction
D1-path_a D2-path_b D3-junction D4-junction
D1-goal D2-goal D3-path_a D4-path_b
D3-goal D4-goal
```

`Total turns: 4` is then reported on stderr, which matches this map's
documented optimum (see `maps/README.md`).

## Resources

- [PEP 257 — Docstring Conventions](https://peps.python.org/pep-0257/)
- [PEP 484 / the `typing` module](https://docs.python.org/3/library/typing.html)
  and the [mypy documentation](https://mypy.readthedocs.io/)
- [flake8 documentation](https://flake8.pycqa.org/)
- [pygame documentation](https://www.pygame.org/docs/)
- [0-1 BFS (deque-based shortest paths on 0/1-weighted graphs)](https://cp-algorithms.com/graph/01_bfs.html)
- [Edmonds–Karp algorithm (max flow via shortest augmenting paths)](https://en.wikipedia.org/wiki/Edmonds%E2%80%93Karp_algorithm)
- Cormen, Leiserson, Rivest, Stein — *Introduction to Algorithms* (chapters
  on graph traversal and network flow)
- w3schools.com — for general concepts

**AI usage**: an AI assistant was used as a design and debugging aid, not
as a code generator. It was consulted to discuss and compare candidate
approaches for modeling zone/connection capacities and restricted-zone
travel time as a flow network (leading to the split in/out node and
transit-node design in `pathfinding.py`), and to help track down specific
bugs during development (e.g. turn-scheduling edge cases around
simultaneous moves and restricted-zone transits in `sim.py`). All code was
written and is understood by the author; this `README.md` itself was
drafted with AI assistance based on the project's source code and the
subject's requirements.
