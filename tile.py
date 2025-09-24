import pygame
import os

class Tile:
    def __init__(self, value1, value2):
        self.value1 = value1
        self.value2 = value2
        
        # FIXED SIZE - no more adaptive scaling to prevent gaps
        self.current_width = 40
        self.current_height = 80
        
        self.image = self.load_image()
        # Initial rect is based on the loaded image in its default orientation (vertical)
        self.rect = self.image.get_rect()
        self.rotation = 0  # Degrees: 0 for vertical, 90 for horizontal
        
        # Store original dimensions assuming vertical orientation.
        self.original_width = self.current_width
        self.original_height = self.current_height

    def load_image(self):
        """Load image using canonical naming and ensure values match image orientation."""
        min_val = min(self.value1, self.value2)
        max_val = max(self.value1, self.value2)
        
        name = f"card_{min_val}-{max_val}.JPG"
        path = os.path.join("assets", "Cards", name)
        
        if os.path.exists(path):
            img = pygame.image.load(path).convert_alpha()
            
            # Ensure our values match what the canonical image actually shows
            # If we loaded card_2-6.jpg, make sure value1=2, value2=6 (assuming smaller at top)
            if self.value1 != min_val:
                self.value1, self.value2 = min_val, max_val
            
            return pygame.transform.smoothscale(img, (self.current_width, self.current_height))
        
        print(f"[Tile Missing] No image found for tile ({self.value1}, {self.value2})")
        return pygame.Surface((self.current_width, self.current_height))

    def update_size(self, new_width, new_height):
        """COMPATIBILITY: Board may still call this, but we ignore size changes to prevent gaps"""
        # Do nothing - keep tiles at fixed size to prevent spacing issues
        pass

    def is_double(self):
        return self.value1 == self.value2

    def swap_values(self):
        """Swaps the value1 and value2 of the tile and reloads image to match."""
        self.value1, self.value2 = self.value2, self.value1
        self.image = self.load_image()
    
    def orient_to_match(self, target_value, side='right'):
        """
        Ensures the tile is oriented so the correct value faces the board end.
        
        For domino rules:
        - Doubles (same values): Always vertical, orientation doesn't matter for matching
        - Non-doubles: Always horizontal
          * When horizontal (90°): value1 is on RIGHT side, value2 is on LEFT side
        
        The goal is to make sure the matching value is on the side that will connect to the board.
        """

        # If it's a double, orientation doesn't matter for matching since both values are the same
        if self.is_double():
            return

        # For non-doubles that are horizontal (90°):
        # value2 is on the LEFT, value1 is on the RIGHT
        
        if side == 'left':
            # We are placing this tile to the LEFT of the board
            # So the RIGHT side of this tile (value1) will connect to the board
            # We want value1 to equal target_value
            if self.value1 != target_value:
                self.swap_values()
        
        elif side == 'right':
            # We are placing this tile to the RIGHT of the board
            # So the LEFT side of this tile (value2) will connect to the board
            # We want value2 to equal target_value
            if self.value2 != target_value:
                self.swap_values()

        elif side == 'perpendicular':
            # This is for connecting to a double acting as a spinner
            # We need one of our values to match the double's value
            # Since we're connecting perpendicularly, we can use either end
            if self.value1 != target_value and self.value2 != target_value:
                # Neither value matches, this shouldn't happen if the tile was validly selected
                pass
            elif self.value2 == target_value:
                # value2 matches, which will be on the left side when horizontal
                # This is fine for perpendicular placement
                pass
            elif self.value1 == target_value:
                # value1 matches, which will be on the right side when horizontal
                # We might want to swap so the matching value is on the connecting side
                # For simplicity, let's leave it as is since perpendicular can connect either way
                pass

    def set_rotation(self, angle):
        """Sets the rotation and updates the rect to reflect new dimensions."""
        if self.rotation != angle:
            self.rotation = angle
            self.update_rect_after_rotation(angle)

    def update_rect_after_rotation(self, angle):
        """
        Updates the tile's rect dimensions and position based on rotation.
        Uses fixed current_width and current_height.
        """
        # Store current center if rect exists
        old_center = self.rect.center if hasattr(self, 'rect') else (0, 0)
        
        if angle == 90 or angle == 270: # Horizontal
            self.rect = pygame.Rect(0, 0, self.current_height, self.current_width) # width becomes height, height becomes width
        else: # Vertical (0 or 180)
            self.rect = pygame.Rect(0, 0, self.current_width, self.current_height) # normal dimensions
        
        # Restore center position
        if old_center != (0, 0):
            self.rect.center = old_center

    def set_position(self, x, y):
        """Sets the top-left position of the tile's rectangle."""
        self.rect.topleft = (x, y)

    def draw(self, screen):
        """
        Draws the tile on the screen, applying its current rotation.
        The rotated image is blitted such that its center aligns with the tile's rect center.
        """
        rotated = pygame.transform.rotate(self.image, self.rotation)
        rotated_rect = rotated.get_rect(center=self.rect.center)
        screen.blit(rotated, rotated_rect)

    def flip(self):
        """Flip the tile by swapping values - useful for user interaction"""
        self.swap_values()

    def __contains__(self, value):
        """Checks if a given value is present on either half of the tile."""
        return value == self.value1 or value == self.value2

    def __eq__(self, other):
        """
        Compares two Tile objects for equality. Tiles are considered equal if
        they have the same two values, regardless of their order (e.g., 1-2 is equal to 2-1).
        """
        if not isinstance(other, Tile):
            return False
        return {self.value1, self.value2} == {other.value1, other.value2}

    def __hash__(self):
        """
        Returns a hash value for the Tile, allowing it to be used in sets or as dictionary keys.
        The hash is based on the frozenset of its values, making 1-2 and 2-1 hash to the same value.
        """
        return hash(frozenset({self.value1, self.value2}))

    def __str__(self):
        return f"({self.value1}-{self.value2})"
