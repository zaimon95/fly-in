"""Loading of the program's configuration file."""


class ConfigError(ValueError):
    """Raised when the configuration file is invalid."""


class Config:
    """Settings read from a "key: value" configuration file.

    Attributes:
        map_path: Path to the map file to solve.
        visual: Whether to open the graphical replay after solving.
    """

    _BOOLEANS = {"true": True, "yes": True, "false": False, "no": False}

    def __init__(self, map_path: str, visual: bool = True) -> None:
        """Create a configuration.

        Args:
            map_path: Path to the map file to solve.
            visual: Whether to open the graphical replay.
        """
        self.map_path = map_path
        self.visual = visual

    @classmethod
    def load(cls, path: str = "config.txt") -> "Config":
        """Read a configuration file.

        Args:
            path: Path to the configuration file.

        Returns:
            The loaded configuration. The "visual" key is optional and
            defaults to true.

        Raises:
            OSError: If the file cannot be read.
            ConfigError: If a line is malformed, a key is missing or a
                value is invalid.
        """
        values: dict[str, str] = {}
        with open(path, "r") as f:
            for line_no, raw_line in enumerate(f, start=1):
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                key, sep, value = line.partition(":")
                if not sep:
                    raise ConfigError(
                        f"{path}, line {line_no}: expected 'key: value', "
                        f"got {line!r}"
                    )
                values[key.strip()] = value.strip()

        map_path = values.get("map_path")
        if not map_path:
            raise ConfigError(f"{path} is missing 'map_path'")
        visual_text = values.get("visual", "true").lower()
        if visual_text not in cls._BOOLEANS:
            raise ConfigError(
                f"{path}: 'visual' must be true or false, "
                f"got {visual_text!r}"
            )
        return cls(map_path=map_path, visual=cls._BOOLEANS[visual_text])
