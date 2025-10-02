# tile.py  — web/pygbag-friendly image loading for domino tiles
import os
import pygame

# Resolve paths in a way that works in pygbag (browser) and desktop
BASE_DIR = os.path.dirname(__file__)
def R(*parts: str) -> str:
    """Join path parts relative to this file (and also try plain relative)."""
    return os.path.join(BASE_DIR, *parts)

class Tile:
    def __init__(self, value1: int, value2: int):
        self.value1 = value1
        self.value2 = value2

        # Keep the same visual size you’ve been using
        self.current_width = 40
        self.current_height = 80

        self.image = self._load_image()
        self.rect = self.image.get_rect()           # default vertical rect
        self.rotation = 0                           # 0=vertical, 90=horizontal

        self.original_width = self.current_width
        self.original_height = self.current_height

    # ---------- loading helpers ----------

    def _surface_from_path(self, rel_path: str) -> pygame.Surface | None:
        """
        Try to load an image by a relative path. We attempt both
        '<BASE_DIR>/<rel_path>' and just '<rel_path>' so it works in
        both desktop and pygbag’s packaged FS.
        """
        for p in (R(rel_path), rel_path):
            try:
                surf = pygame.image.load(p)
                # convert_alpha only if a display exists already
                return (surf.convert_alpha()
                        if pygame.display.get_surface()
                        else surf.convert())
            except Exception:
                pass
        return None

    def _load_face_surface(self, a: int, b: int) -> pygame.Surface:
        """
        Accept several filename variants to be robust to case/underscore/dash
        differences. Preferred is: assets/Cards/card_<min>-<max>.jpg
        """
        a, b = sorted((a, b))
        candidates = [
            f"assets/Cards/card_{a}-{b}.jpg",
            f"assets/Cards/card_{a}-{b}.JPG",
            f"assets/Cards/card_{a}_{b}.jpg",
            f"assets/Cards/card_{a}_{b}.JPG",
            f"assets/Cards/card_{a}-{b}.png",
            f"assets/Cards/card_{a}_{b}.png",
        ]

        for rel in candidates:
            surf = self._surface_from_path(rel)
            if surf:
                return surf

        # Fallback placeholder so the game still runs if an asset is missing
        print(f"[ASSET] Missing image for tile {a}-{b}; using placeholder.")
        ph = pygame.Surface((self.current_width, self.current_height), pygame.SRCALPHA)
        ph.fill((0, 0, 0))
        pygame.draw.rect(ph, (200, 200, 200), ph.get_rect(), 6)
        return ph

    def _load_image(self) -> pygame.Surface:
        """
        Load the face image (normalizing to min-max naming) and scale to 40x80.
        """
        a, b = sorted((self.value1, self.value2))
        # Normalize stored values to match canonical filename order
        if (self.value1, self.value2) != (a, b):
            self.value1, self.value2 = a, b

        face = self._load_face_surface(self.value1, self.value2)
        return pygame.transform.smoothscale(face, (self.current_width, self.current_height))

    # ---------- public API used by the rest of your game ----------

    def update_size(self, new_width: int, new_height: int):
        # Intentional no-op (keeps spacing consistent with your current UI)
        pass

    def is_double(self) -> bool:
        return self.value1 == self.value2

    def swap_values(self):
        """Swap values and reload image so filename order stays correct."""
        self.value1, self.value2 = self.value2, self.value1
        self.image = self._load_image()

    def orient_to_match(self, target_value: int, side: str = "right"):
        """
        Keep your semantics:
        - Doubles: vertical; orientation doesn’t matter for matching.
        - Non-doubles: horizontal; ensure the matching value faces the join.
        """
        if self.is_double():
            return

        if side == "left":
            # Right side of this tile (value1) meets the board → value1 must match
            if self.value1 != target_value:
                self.swap_values()
        elif side == "right":
            # Left side (value2) meets the board → value2 must match
            if self.value2 != target_value:
                self.swap_values()
        elif side == "perpendicular":
            # Connecting to a spinner; either value can match (do nothing)
            if self.value1 != target_value and self.value2 != target_value:
                pass

    def set_rotation(self, angle: int):
        if self.rotation != angle:
            self.rotation = angle
            self._update_rect_after_rotation(angle)

    def _update_rect_after_rotation(self, angle: int):
        old_center = getattr(self.rect, "center", (0, 0))
        if angle in (90, 270):   # horizontal
            self.rect = pygame.Rect(0, 0, self.current_height, self.current_width)
        else:                     # vertical
            self.rect = pygame.Rect(0, 0, self.current_width, self.current_height)
        if old_center != (0, 0):
            self.rect.center = old_center

    def set_position(self, x: int, y: int):
        self.rect.topleft = (x, y)

    def draw(self, screen: pygame.Surface):
        rotated = pygame.transform.rotate(self.image, self.rotation)
        screen.blit(rotated, rotated.get_rect(center=self.rect.center))

    def flip(self):
        self.swap_values()

    def __contains__(self, value: int) -> bool:
        return value == self.value1 or value == self.value2

    def __eq__(self, other) -> bool:
        return isinstance(other, Tile) and {self.value1, self.value2} == {other.value1, other.value2}

    def __hash__(self) -> int:
        return hash(frozenset((self.value1, self.value2)))

    def __str__(self) -> str:
        return f"({self.value1}-{self.value2})"
