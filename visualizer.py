"""Graphical replay of a simulation with pygame.

The visualizer holds no simulation rule: it only replays the positions
recorded by the Simulator after each turn, moving every drone smoothly
from one recorded position to the next.
"""

import math

import pygame

from data import EndHub, Graph, Hub, StartHub, Zone
from sim import Position, Snapshot

Point = tuple[float, float]

WIDTH, HEIGHT = 1200, 800
HUD_HEIGHT = 120
MARGIN = 70
BACKGROUND = (24, 26, 32)
LINK_COLOR = (110, 115, 130)
TEXT_COLOR = (230, 230, 235)
DRONE_COLOR = (250, 250, 250)
DEFAULT_HUB_COLOR = (150, 150, 150)
PRIORITY_OUTLINE = (255, 200, 40)
RESTRICTED_OUTLINE = (230, 60, 60)


class VisualizerError(RuntimeError):
    """Raised when the graphical display cannot be used."""


class Visualizer:
    """Window replaying a simulation turn by turn.

    Controls: space plays or pauses, left and right step one turn,
    + and - change the speed, R restarts, Escape quits.
    """

    def __init__(self, graph: Graph, snapshots: list[Snapshot],
                 lines: list[str]) -> None:
        """Prepare the replay.

        Args:
            graph: The parsed map.
            snapshots: Drone positions before the first turn and after
                each turn, as recorded by the Simulator.
            lines: The output line of each turn.
        """
        self._graph = graph
        self._snapshots = snapshots
        self._lines = lines
        self._hubs = [h for h in graph.hubs()]
        self._turn = 0
        self._progress = 0.0
        self._playing = False
        self._turn_duration = 0.8
        self._screen: pygame.Surface | None = None
        self._font: pygame.font.Font | None = None
        self._small_font: pygame.font.Font | None = None
        self._positions: dict[str, Point] = {}
        self._hub_radius = 20.0
        self._mouse: Point | None = None

    def run(self) -> None:
        """Open the window and replay until it is closed.

        Raises:
            VisualizerError: If pygame cannot open a window.
        """
        try:
            self._open((WIDTH, HEIGHT))
            clock = pygame.time.Clock()
            running = True
            while running:
                elapsed = clock.tick(60) / 1000
                for event in pygame.event.get():
                    running = self._handle_event(event) and running
                self._advance(elapsed)
                self._mouse = (pygame.mouse.get_pos()
                               if pygame.mouse.get_focused() else None)
                self.draw_frame()
                pygame.display.flip()
        except pygame.error as error:
            raise VisualizerError(f"cannot display the window: {error}")
        finally:
            pygame.quit()

    def _open(self, size: tuple[int, int]) -> None:
        """Initialize pygame, the window, the fonts and the layout."""
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_caption("Fly-in")
        self._screen = pygame.display.set_mode(size)
        self._font = pygame.font.SysFont(None, 26)
        self._small_font = pygame.font.SysFont(None, 20)
        self._layout(size)

    def _handle_event(self, event: pygame.event.Event) -> bool:
        """React to a keyboard or window event.

        Returns:
            False if the window must close, True otherwise.
        """
        if event.type == pygame.QUIT:
            return False
        if event.type != pygame.KEYDOWN:
            return True
        if event.key == pygame.K_ESCAPE:
            return False
        if event.key == pygame.K_SPACE:
            self._playing = not self._playing
        elif event.key == pygame.K_RIGHT:
            self._playing = False
            self._set_turn(self._turn + 1)
        elif event.key == pygame.K_LEFT:
            self._playing = False
            self._set_turn(self._turn - 1)
        elif event.key == pygame.K_r:
            self._set_turn(0)
            self._playing = True
        elif event.key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
            self._turn_duration = max(0.1, self._turn_duration / 1.5)
        elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self._turn_duration = min(5.0, self._turn_duration * 1.5)
        return True

    def _set_turn(self, turn: int) -> None:
        """Jump to the start of a turn, without animation."""
        self._turn = max(0, min(turn, len(self._lines)))
        self._progress = 0.0

    def _advance(self, elapsed: float) -> None:
        """Move the animation forward by elapsed seconds when playing."""
        if not self._playing:
            return
        if self._turn >= len(self._lines):
            self._playing = False
            return
        self._progress += elapsed / self._turn_duration
        if self._progress >= 1.0:
            self._turn += 1
            self._progress = 0.0

    def _layout(self, size: tuple[int, int]) -> None:
        """Map every hub to a point of the window and size the hubs.

        Map coordinates are scaled to fill the area above the HUD, with
        the y axis pointing up as in usual map coordinates.
        """
        width, height = size[0], size[1] - HUD_HEIGHT
        xs = [hub.x for hub in self._hubs]
        ys = [hub.y for hub in self._hubs]
        span_x = max(max(xs) - min(xs), 1)
        span_y = max(max(ys) - min(ys), 1)
        scale = min((width - 2 * MARGIN) / span_x,
                    (height - 2 * MARGIN) / span_y)
        offset_x = (width - span_x * scale) / 2
        offset_y = (height - span_y * scale) / 2
        for hub in self._hubs:
            px = offset_x + (hub.x - min(xs)) * scale
            py = height - (offset_y + (hub.y - min(ys)) * scale)
            self._positions[hub.name] = (px, py)
        self._hub_radius = self._fit_radius()

    def _fit_radius(self) -> float:
        """Choose a hub radius small enough for hubs not to overlap."""
        points = list(self._positions.values())
        closest = float(WIDTH)
        for i, a in enumerate(points):
            for b in points[i + 1:]:
                closest = min(closest, math.dist(a, b))
        return max(14.0, min(34.0, closest * 0.3))

    def draw_frame(self) -> None:
        """Draw the current state of the animation on the window."""
        screen = self._require_screen()
        screen.fill(BACKGROUND)
        self._draw_links(screen)
        start, end = self._current_snapshots()
        self._draw_hubs(screen, end if self._progress > 0.5 else start)
        self._draw_drones(screen, start, end)
        self._draw_hover_name(screen)
        self._draw_hud(screen)

    def _require_screen(self) -> pygame.Surface:
        """Return the window surface, which must be open."""
        if self._screen is None:
            raise VisualizerError("the window is not open")
        return self._screen

    def _current_snapshots(self) -> tuple[Snapshot, Snapshot]:
        """Return the states the animation goes from and to."""
        start = self._snapshots[self._turn]
        if self._turn + 1 < len(self._snapshots):
            return start, self._snapshots[self._turn + 1]
        return start, start

    def _draw_links(self, screen: pygame.Surface) -> None:
        """Draw every connection, thicker for higher capacities."""
        seen: set[frozenset[str]] = set()
        for hub in self._hubs:
            for _, connection in self._graph.neighbors(hub):
                key = connection.endpoints()
                if key in seen:
                    continue
                seen.add(key)
                width = 2 + 2 * min(connection.max_link_capacity, 4)
                pygame.draw.line(
                    screen, LINK_COLOR,
                    self._positions[connection.hub1.name],
                    self._positions[connection.hub2.name], width)

    def _draw_hubs(self, screen: pygame.Surface, snapshot: Snapshot) -> None:
        """Draw every hub with its zone style and its occupancy."""
        occupancy: dict[str, int] = {}
        for hub, target in snapshot.values():
            if target is None:
                occupancy[hub.name] = occupancy.get(hub.name, 0) + 1
        radius = self._hub_radius
        for hub in self._hubs:
            center = self._positions[hub.name]
            pygame.draw.circle(screen, self._hub_color(hub), center, radius)
            self._draw_zone_outline(screen, hub, center, radius)
            count = occupancy.get(hub.name, 0)
            if isinstance(hub, (StartHub, EndHub)):
                info = f"{count}"
            else:
                info = f"{count}/{hub.max_drones}"
            self._draw_label(screen, info,
                             (center[0], center[1] + radius + 12), True)

    @staticmethod
    def _hub_color(hub: Hub) -> pygame.Color:
        """Return the hub's color, or a default one if unknown."""
        if hub.color is not None:
            try:
                return pygame.Color(hub.color)
            except ValueError:
                pass
        return pygame.Color(DEFAULT_HUB_COLOR)

    @staticmethod
    def _draw_zone_outline(screen: pygame.Surface, hub: Hub,
                           center: Point, radius: float) -> None:
        """Draw the outline that shows the zone type."""
        if hub.zone is Zone.PRIORITY:
            pygame.draw.circle(screen, PRIORITY_OUTLINE, center, radius, 4)
        elif hub.zone is Zone.RESTRICTED:
            pygame.draw.circle(screen, RESTRICTED_OUTLINE, center,
                               radius, 3)
            pygame.draw.circle(screen, RESTRICTED_OUTLINE, center,
                               radius + 5, 2)
        elif hub.zone is Zone.BLOCKED:
            side = radius * 0.7
            x, y = center
            pygame.draw.line(screen, (0, 0, 0), (x - side, y - side),
                             (x + side, y + side), 4)
            pygame.draw.line(screen, (0, 0, 0), (x - side, y + side),
                             (x + side, y - side), 4)
        else:
            pygame.draw.circle(screen, (0, 0, 0), center, radius, 2)

    def _draw_drones(self, screen: pygame.Surface, start: Snapshot,
                     end: Snapshot) -> None:
        """Draw each drone between its two positions.

        Drones drawn at exactly the same point (a crowded hub) are
        merged into a single disc labelled with their count.
        """
        points_start = self._drone_points(start)
        points_end = self._drone_points(end)
        t = self._progress
        t = t * t * (3 - 2 * t)
        stacks: dict[tuple[int, int], list[int]] = {}
        for drone_id, (sx, sy) in points_start.items():
            ex, ey = points_end.get(drone_id, (sx, sy))
            center = (round(sx + (ex - sx) * t), round(sy + (ey - sy) * t))
            stacks.setdefault(center, []).append(drone_id)
        for center, drone_ids in stacks.items():
            if len(drone_ids) == 1:
                label = str(drone_ids[0])
            else:
                label = f"x{len(drone_ids)}"
            self._draw_drone(screen, center, label)

    def _draw_drone(self, screen: pygame.Surface, center: Point,
                    label: str) -> None:
        """Draw one drone disc with its label."""
        radius = self._drone_radius()
        pygame.draw.circle(screen, DRONE_COLOR, center, radius)
        pygame.draw.circle(screen, (20, 20, 20), center, radius, 1)
        self._draw_label(screen, label, center, True, (20, 20, 20))

    def _drone_radius(self) -> float:
        """Return the radius of a drone disc."""
        return max(9.0, self._hub_radius * 0.42)

    def _drone_points(self, snapshot: Snapshot) -> dict[int, Point]:
        """Place every drone of a snapshot on the window.

        Drones sharing a hub are spread on a small ring around its
        center when they fit on it, and gathered at the center
        otherwise. Drones in transit stand in the middle of their link.
        """
        groups: dict[str, list[int]] = {}
        points: dict[int, Point] = {}
        for drone_id, position in sorted(snapshot.items()):
            hub, target = position
            if target is not None:
                points[drone_id] = self._midpoint(position)
            else:
                groups.setdefault(hub.name, []).append(drone_id)
        ring = self._hub_radius * 0.6
        fit = int(2 * math.pi * ring / (2 * self._drone_radius()))
        for name, drone_ids in groups.items():
            cx, cy = self._positions[name]
            if len(drone_ids) == 1 or len(drone_ids) > fit:
                for drone_id in drone_ids:
                    points[drone_id] = (cx, cy)
                continue
            for index, drone_id in enumerate(drone_ids):
                angle = 2 * math.pi * index / len(drone_ids)
                points[drone_id] = (cx + ring * math.cos(angle),
                                    cy + ring * math.sin(angle))
        return points

    def _midpoint(self, position: Position) -> Point:
        """Return the middle of the link a drone is flying along."""
        hub, target = position
        ax, ay = self._positions[hub.name]
        if target is None:
            return (ax, ay)
        bx, by = self._positions[target.name]
        return ((ax + bx) / 2, (ay + by) / 2)

    def _hovered_hub(self) -> Hub | None:
        """Return the hub under the mouse pointer, if any.

        When hubs overlap, the one whose center is closest wins.
        """
        if self._mouse is None:
            return None
        best: Hub | None = None
        best_distance = self._hub_radius
        for hub in self._hubs:
            distance = math.dist(self._mouse, self._positions[hub.name])
            if distance <= best_distance:
                best, best_distance = hub, distance
        return best

    def _draw_hover_name(self, screen: pygame.Surface) -> None:
        """Show the name of the hovered hub, above everything else.

        The hub gets a white ring, and its name is drawn in a dark box
        above it, kept inside the window.
        """
        hub = self._hovered_hub()
        if hub is None or self._font is None:
            return
        cx, cy = self._positions[hub.name]
        pygame.draw.circle(screen, (255, 255, 255), (cx, cy),
                           self._hub_radius + 8, 2)
        text = self._font.render(hub.name, True, TEXT_COLOR)
        box = text.get_rect().inflate(14, 8)
        box.midbottom = (round(cx), round(cy - self._hub_radius - 12))
        box.clamp_ip(screen.get_rect())
        pygame.draw.rect(screen, (10, 10, 14), box, border_radius=6)
        pygame.draw.rect(screen, (255, 255, 255), box, 1, border_radius=6)
        screen.blit(text, text.get_rect(center=box.center))

    def _draw_hud(self, screen: pygame.Surface) -> None:
        """Draw the turn counter, the current moves and the controls."""
        top = HEIGHT - HUD_HEIGHT
        pygame.draw.rect(screen, (36, 39, 48), (0, top, WIDTH, HUD_HEIGHT))
        snapshot = self._snapshots[self._turn]
        delivered = sum(1 for hub, target in snapshot.values()
                        if target is None and isinstance(hub, EndHub))
        total = len(self._lines)
        state = "playing" if self._playing else "paused"
        self._draw_text(screen, f"Turn {self._turn}/{total}   "
                        f"Delivered {delivered}/{self._graph.nb_drones}"
                        f"   ({state})", (20, top + 15))
        if self._turn < total:
            moves = f"Next: {self._lines[self._turn]}"
        else:
            moves = "All drones delivered"
        self._draw_text(screen, moves[:140], (20, top + 48))
        self._draw_text(screen, "Space play/pause   Left/Right step   "
                        "+/- speed   R restart   Esc quit",
                        (20, top + 82), True)

    def _draw_label(self, screen: pygame.Surface, text: str,
                    center: Point, small: bool = False,
                    color: tuple[int, int, int] = TEXT_COLOR) -> None:
        """Draw text centered on a point."""
        font = self._small_font if small else self._font
        if font is None:
            return
        surface = font.render(text, True, color)
        screen.blit(surface, surface.get_rect(center=center))

    def _draw_text(self, screen: pygame.Surface, text: str,
                   top_left: tuple[int, int], small: bool = False) -> None:
        """Draw text from its top-left corner."""
        font = self._small_font if small else self._font
        if font is None:
            return
        screen.blit(font.render(text, True, TEXT_COLOR), top_left)

    def save_frame(self, turn: int, progress: float, path: str,
                   mouse: Point | None = None) -> None:
        """Render one frame to an image file, without any window.

        Args:
            turn: Turn to show.
            progress: Position within the turn, from 0.0 to 1.0.
            path: Image file to write.
            mouse: Simulated mouse position, to render a hovered hub.
        """
        self._open((WIDTH, HEIGHT))
        self._set_turn(turn)
        self._progress = progress
        self._mouse = mouse
        self.draw_frame()
        pygame.image.save(self._require_screen(), path)
        pygame.quit()