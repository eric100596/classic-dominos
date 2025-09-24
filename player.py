import pygame

# Define a consistent tile size for drawing, assuming 40x80 is standard domino size
TILE_WIDTH = 40
TILE_HEIGHT = 80

class Player:
    def __init__(self, index, is_human=True):
        self.index = index
        self.hand = []
        self.is_human = is_human
        self.score = 0

    def add_tile(self, tile):
        self.hand.append(tile)

    def remove_tile(self, tile):
        if tile in self.hand:
            self.hand.remove(tile)
        else:
            print(f"Warning: Tile ({tile.value1}, {tile.value2}) not found in Player {self.index + 1}'s hand.")

    def add_score(self, points):
        self.score += points
        print(f"Player {self.index + 1} scored {points} points! Total: {self.score}")

    def draw_hand(self, screen, play_area):
        font = pygame.font.SysFont(None, 24)
        score_font = pygame.font.SysFont(None, 20)
        label = font.render(f"Player {self.index + 1}", True, (255, 255, 255))
        score_label = score_font.render(f"Score: {self.score}", True, (255, 255, 0))

        # Common variables for spacing
        tile_spacing = 10
        text_padding = 10

        if self.index == 0:  # Bottom Player (Human)
            effective_tile_width = TILE_WIDTH
            effective_tile_height = TILE_HEIGHT

            total_hand_width = len(self.hand) * effective_tile_width + (len(self.hand) - 1) * tile_spacing
            tiles_start_x = (screen.get_width() - total_hand_width) // 2

            # Start where you had it originally
            tiles_y_position = screen.get_height() - effective_tile_height - 40

            # --- Compute desired label position (below tiles) and clamp on-screen ---
            label_h = label.get_height()
            score_h = score_label.get_height()
            text_h = max(label_h, score_h)

            desired_text_y = tiles_y_position + effective_tile_height + text_padding
            safe_text_y    = screen.get_height() - text_h - 8  # keep 8px from the bottom

            if desired_text_y > safe_text_y:
                # Not enough room for text → slide tiles up just enough
                shift = desired_text_y - safe_text_y
                tiles_y_position -= shift
                desired_text_y = safe_text_y  # text will sit at the safe spot

            # Draw tiles (horizontal)
            for i, tile in enumerate(self.hand):
                tile.set_rotation(0)
                tile.set_position(tiles_start_x + i * (effective_tile_width + tile_spacing), tiles_y_position)
                tile.draw(screen)

            # Center the two texts together, placed BELOW the tiles (but clamped on-screen)
            combined_text_width = label.get_width() + score_label.get_width() + text_padding
            text_start_x = tiles_start_x + total_hand_width // 2 - combined_text_width // 2

            screen.blit(label, (text_start_x, desired_text_y))
            screen.blit(score_label, (text_start_x + label.get_width() + text_padding, desired_text_y))


        elif self.index == 1: # Left Player (Human) - Player 2
            # Tiles are vertical, so their visual width is TILE_HEIGHT, height is TILE_WIDTH
            effective_tile_width = TILE_HEIGHT # Visual width when rotated 90 degrees (80)
            effective_tile_height = TILE_WIDTH # Visual height when rotated 90 degrees (40)

            rotated_label = pygame.transform.rotate(label, 90)
            rotated_score = pygame.transform.rotate(score_label, 90)

            # Fixed position for text - 20px from left edge
            text_x_position = 10
            
            # Calculate combined height of rotated text
            combined_text_height = rotated_label.get_height() + rotated_score.get_height() + text_padding
            
            # Center text vertically on screen
            text_start_y = (screen.get_height() - combined_text_height) // 2

            # Position tiles 20px to the right of the text
            tiles_x_position = text_x_position + max(rotated_label.get_width(), rotated_score.get_width()) + 20
            
            # Calculate total hand height and center it vertically
            total_hand_height = len(self.hand) * effective_tile_height + (len(self.hand) - 1) * tile_spacing
            tiles_start_y = (screen.get_height() - total_hand_height) // 2

            for i, tile in enumerate(self.hand):
                tile.set_rotation(90) # Ensure vertical
                tile.set_position(tiles_x_position, tiles_start_y + i * (effective_tile_height + tile_spacing))
                tile.draw(screen)

            # Draw rotated text at fixed position
            screen.blit(rotated_score, (text_x_position, text_start_y))
            screen.blit(rotated_label, (text_x_position, text_start_y + rotated_score.get_height() + text_padding))

        elif self.index == 2: # Top Player (Human)
            # Tiles are horizontal
            effective_tile_width = TILE_WIDTH
            effective_tile_height = TILE_HEIGHT

            total_hand_width = len(self.hand) * effective_tile_width + (len(self.hand) - 1) * tile_spacing
            
            # Center hand horizontally
            tiles_start_x = (screen.get_width() - total_hand_width) // 2
            tiles_y_position = 40 # Position from top edge

            for i, tile in enumerate(self.hand):
                tile.set_rotation(0) # Ensure horizontal
                tile.set_position(tiles_start_x + i * (effective_tile_width + tile_spacing), tiles_y_position)
                tile.draw(screen)

            # Player label and score (centered above tiles)
            combined_text_width = label.get_width() + score_label.get_width() + text_padding
            text_start_x = tiles_start_x + total_hand_width // 2 - combined_text_width // 2
            text_y_position = tiles_y_position - label.get_height() - text_padding # Place above tiles

            screen.blit(label, (text_start_x, text_y_position))
            screen.blit(score_label, (text_start_x + label.get_width() + text_padding, text_y_position))

        elif self.index == 3: # Right Player (Human) - Player 4 (FIXED SPACING)
            # Tiles are vertical, so their visual width is TILE_HEIGHT, height is TILE_WIDTH
            effective_tile_width = TILE_HEIGHT # Visual width when rotated 90 degrees (80)
            effective_tile_height = TILE_WIDTH # Visual height when rotated 90 degrees (40)

            rotated_label = pygame.transform.rotate(label, 270)
            rotated_score = pygame.transform.rotate(score_label, 270)

            # Position text close to right edge
            text_width = max(rotated_label.get_width(), rotated_score.get_width())
            text_x_position = screen.get_width() - text_width - 10
            
            # Calculate combined height of rotated text
            combined_text_height = rotated_label.get_height() + rotated_score.get_height() + text_padding
            
            # Center text vertically on screen
            text_start_y = (screen.get_height() - combined_text_height) // 2

            # Position tiles to the left of text
            tiles_x_position = text_x_position - effective_tile_width - 20
            
            # FIXED: Calculate actual hand height and center properly
            actual_hand_height = len(self.hand) * effective_tile_height + (len(self.hand) - 1) * tile_spacing
            tiles_start_y = (screen.get_height() - actual_hand_height) // 2

            for i, tile in enumerate(self.hand):
                tile.set_rotation(90) # Ensure vertical
                tile.set_position(tiles_x_position, tiles_start_y + i * (effective_tile_height + tile_spacing))
                tile.draw(screen)

            # Draw rotated text at fixed position
            screen.blit(rotated_score, (text_x_position, text_start_y))
            screen.blit(rotated_label, (text_x_position, text_start_y + rotated_score.get_height() + text_padding))
