# boneyard.py
import pygame

class Boneyard:
    def __init__(self, tiles):
        self.tiles = tiles

    def draw_tile(self):
        if self.tiles:
            return self.tiles.pop()
        else:
            return None

    def tile_count(self):
        return len(self.tiles)

    def is_empty(self):
        return len(self.tiles) == 0

    def draw(self, screen, position):
        font = pygame.font.SysFont(None, 36)
        text = f"Boneyard: {self.tile_count()}"
        label = font.render(text, True, (255, 255, 255))
        screen.blit(label, position)
