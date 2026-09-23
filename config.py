class ConfigError(ValueError):
    pass


class Config:
    def __init__(self, map_path: str, max_paths: int) -> None:
        self.map_path = map_path
        self.max_paths = max_paths

    @classmethod
    def load(cls, path: str = "config.txt") -> "Config":
        values: dict[str, str] = {}
        with open(path, "r") as f:
            for line_no, raw_line in enumerate(f, start=1):
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                key, sep, value = line.partition(":")
                if not sep:
                    raise ConfigError(
                        f"line {line_no}: expected 'key: value', got {line!r}"
                    )
                values[key.strip()] = value.strip()

        try:
            map_path = values["map_path"]
        except KeyError:
            raise ConfigError("config.txt is missing 'map_path'") from None

        try:
            max_paths = int(values["max_paths"])
        except KeyError:
            raise ConfigError("config.txt is missing 'max_paths'") from None
        except ValueError:
            raise ConfigError(
                f"max_paths must be an integer, got {values['max_paths']!r}"
            ) from None
        if max_paths <= 0:
            raise ConfigError("max_paths must be a positive integer")

        return cls(map_path=map_path, max_paths=max_paths)
