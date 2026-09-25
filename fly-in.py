"""Entry point of Fly-in: solves a map and prints the simulation."""

import sys

from config import Config, ConfigError
from data import Graph, MapParseError
from parser import MapParser
from planner import Planner
from sim import SimulationError, Simulator, Snapshot


class FlyIn:
    """Runs the whole program: config, parsing, planning, simulation."""

    def __init__(self, config_path: str) -> None:
        """Create the program.

        Args:
            config_path: Path to the configuration file.
        """
        self._config_path = config_path

    def run(self) -> int:
        """Solve the configured map, print it, then replay it visually.

        Every expected error is caught and reported, so the program
        never stops on an unhandled exception.

        Returns:
            The exit status: 0 on success, 1 on error.
        """
        try:
            config = Config.load(self._config_path)
            graph = MapParser().parse_map(config.map_path)
            plan = Planner(graph).plan()
            simulator = Simulator(graph, plan)
            lines = simulator.run()
        except (OSError, ConfigError, MapParseError,
                SimulationError, ValueError) as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
        for line in lines:
            print(line)
        print(f"Total turns: {len(lines)}", file=sys.stderr)
        if config.visual:
            return self._show(graph, simulator.snapshots, lines)
        return 0

    @staticmethod
    def _show(graph: Graph, snapshots: list[Snapshot],
              lines: list[str]) -> int:
        """Open the graphical replay.

        pygame is imported here only, so that the text mode keeps
        working on a machine without pygame or without a display.

        Returns:
            The exit status: 0 on success, 1 if the replay failed.
        """
        try:
            from visualizer import Visualizer, VisualizerError
        except ImportError as error:
            print(f"Error: cannot load pygame ({error}). Run 'make "
                  "install', or set 'visual: false' in the config file",
                  file=sys.stderr)
            return 1
        try:
            Visualizer(graph, snapshots, lines).run()
        except VisualizerError as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
        return 0


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "config.txt"
    sys.exit(FlyIn(path).run())