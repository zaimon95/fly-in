"""Parsing of Fly-in map files into a Graph."""

import re

from data import EndHub, Graph, Hub, MapParseError, StartHub, Zone


class MapParser:
    """Reads a map file and builds the corresponding Graph."""

    _NB_DRONES_RE = re.compile(r"nb_drones: (\d+)$")
    _HUB_RE = re.compile(r"(\w+): (\w+) (-?\d+) (-?\d+)(?: \[(.+)])?$")
    _CONNECTION_RE = re.compile(r"connection: (\w+)-(\w+)(?: \[(.+)])?$")

    _HUB_CLASSES: dict[str, type[Hub]] = {
        "start_hub": StartHub,
        "hub": Hub,
        "end_hub": EndHub,
    }

    _ZONE_METADATA_KEYS = {"color", "zone", "max_drones"}
    _CONNECTION_METADATA_KEYS = {"max_link_capacity"}

    def parse_map(self, path: str) -> Graph:
        """Parse a map file.

        Args:
            path: Path to the map file.

        Returns:
            The graph described by the file.

        Raises:
            OSError: If the file cannot be read.
            MapParseError: If the file is invalid. The message gives
                the line number and the cause.
        """
        with open(path, "r") as f:
            lines = f.readlines()

        nb_drones: int | None = None
        graph: Graph | None = None

        for line_no, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if nb_drones is None:
                match = self._NB_DRONES_RE.match(line)
                if match is None:
                    raise MapParseError(
                        f"line {line_no}: the first line must be "
                        f"'nb_drones: <positive_integer>'"
                    )
                nb_drones = self._positive_int(
                    match.group(1), "nb_drones", line_no
                )
                assert nb_drones is not None
                graph = Graph(nb_drones)
                continue

            assert graph is not None

            if self._HUB_RE.match(line):
                graph.add_hub(self._parse_hub_line(line, line_no))
                continue

            connection_match = self._CONNECTION_RE.match(line)
            if connection_match:
                name1, name2, options = connection_match.groups()
                capacity = self._parse_connection_options(options, line_no)
                graph.add_connection(name1, name2, capacity)
                continue

            raise MapParseError(
                f"line {line_no}: unrecognized line: {line!r}"
            )

        if nb_drones is None or graph is None:
            raise MapParseError("empty map file: missing 'nb_drones' line")

        graph.validate()
        return graph

    @staticmethod
    def _positive_int(value: str, what: str, line_no: int) -> int:
        """Convert a string to a strictly positive integer.

        Args:
            value: The text to convert.
            what: Name of the field, used in the error message.
            line_no: Line number, used in the error message.

        Returns:
            The parsed integer.

        Raises:
            MapParseError: If value is not an integer, or not positive.
        """
        try:
            parsed = int(value)
        except ValueError:
            raise MapParseError(
                f"line {line_no}: {what} must be an integer, got {value!r}"
            ) from None
        if parsed <= 0:
            raise MapParseError(
                f"line {line_no}: {what} must be a positive integer, "
                f"got {parsed}"
            )
        return parsed

    def _parse_zone_options(
        self, options: str | None, line_no: int
    ) -> tuple[str | None, Zone, int | None]:
        """Parse the metadata block of a hub line.

        Args:
            options: Content between the brackets, or None if absent.
            line_no: Line number, used in error messages.

        Returns:
            A (color, zone, max_drones) tuple. max_drones is None when
            not specified.

        Raises:
            MapParseError: On an unknown key, an invalid zone type or a
                non-positive capacity.
        """
        color: str | None = None
        zone = Zone.NORMAL
        max_drones: int | None = None
        if options is None:
            return color, zone, max_drones
        for option in options.split(" "):
            key, sep, value = option.partition("=")
            if not sep or key not in self._ZONE_METADATA_KEYS:
                raise MapParseError(
                    f"line {line_no}: invalid zone metadata: {option!r}"
                )
            if key == "color":
                color = value
            elif key == "zone":
                try:
                    zone = Zone[value.upper()]
                except KeyError:
                    raise MapParseError(
                        f"line {line_no}: invalid zone type: {value!r}"
                    ) from None
            elif key == "max_drones":
                max_drones = self._positive_int(
                    value, "max_drones", line_no
                )
        return color, zone, max_drones

    def _parse_connection_options(
        self, options: str | None, line_no: int
    ) -> int:
        """Parse the metadata block of a connection line.

        Args:
            options: Content between the brackets, or None if absent.
            line_no: Line number, used in error messages.

        Returns:
            The link capacity, 1 by default.

        Raises:
            MapParseError: On an unknown key or a non-positive capacity.
        """
        if options is None:
            return 1
        capacity = 1
        for option in options.split(" "):
            key, sep, value = option.partition("=")
            if not sep or key not in self._CONNECTION_METADATA_KEYS:
                raise MapParseError(
                    f"line {line_no}: invalid connection metadata: "
                    f"{option!r}"
                )
            capacity = self._positive_int(
                value, "max_link_capacity", line_no
            )
        return capacity

    def _parse_hub_line(self, line: str, line_no: int) -> Hub:
        """Build a Hub, StartHub or EndHub from a hub line.

        Args:
            line: The stripped line.
            line_no: Line number, used in error messages.

        Returns:
            The hub instance, of the class matching the line prefix.

        Raises:
            MapParseError: If the line or its metadata is invalid.
        """
        match = self._HUB_RE.match(line)
        if match is None:
            raise MapParseError(
                f"line {line_no}: unrecognized line: {line!r}"
            )
        kind, name, x_str, y_str, options = match.groups()
        hub_class = self._HUB_CLASSES.get(kind)
        if hub_class is None:
            raise MapParseError(
                f"line {line_no}: unknown zone type: {kind!r}"
            )
        color, zone, max_drones = self._parse_zone_options(options, line_no)
        if hub_class is Hub:
            return Hub(name, int(x_str), int(y_str), zone, color,
                       max_drones if max_drones is not None else 1)
        # max_drones is meaningless on start_hub/end_hub: silently
        # ignored, as required by the subject (not a validation error)
        return hub_class(name, int(x_str), int(y_str), zone, color)
