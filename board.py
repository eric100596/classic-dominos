import pygame
import math
import random

class Board:
    def __init__(self, screen_width, screen_height):
        self.tiles = []
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # RESTORED ORIGINAL MARGINS - prevents UI overlap
        left_margin   = 140
        right_margin  = 140
        top_margin    = 160
        bottom_margin = 140

        self.play_area_rect = pygame.Rect(
            left_margin,
            top_margin,
            screen_width  - left_margin - right_margin,
            screen_height - top_margin  - bottom_margin
        )
        
        print(f"[BOARD] Screen: {screen_width}x{screen_height}")
        print(f"[BOARD] Play area: {self.play_area_rect.width}x{self.play_area_rect.height}")
        
        self.center_x = self.play_area_rect.centerx
        self.center_y = self.play_area_rect.centery

        # Main-line tracking
        self.current_direction = 'horizontal'
        self.exposed_branch_ends = []
        self.left_end_direction = 'horizontal'
        self.right_end_direction = 'horizontal'
        
        # Tile count and spinner
        self.tile_count = 0
        self.max_tiles = 28
        self.spinner_tile = None
        self.scoring_mode = 'spinner_stays_12'
        
        # Standard tile sizes
        self.tile_width = 40
        self.tile_height = 80

    def will_exceed_boundary(self, x, y, tile_width, tile_height):
        """Standard boundary checking within play area."""
        return (x < self.play_area_rect.left or
                y < self.play_area_rect.top or
                x + tile_width > self.play_area_rect.right or
                y + tile_height > self.play_area_rect.bottom)

    def _position_occupied(self, x, y, width, height):
        new_rect = pygame.Rect(x, y, width, height)
        tolerance = 2
        for existing in self.tiles:
            existing_rect = existing.rect
            # Check with small tolerance for overlap
            test_rect = pygame.Rect(new_rect.x + tolerance, new_rect.y + tolerance,
                                  max(1, new_rect.width - 2*tolerance), max(1, new_rect.height - 2*tolerance))
            existing_test_rect = pygame.Rect(existing_rect.x + tolerance, existing_rect.y + tolerance,
                                           max(1, existing_rect.width - 2*tolerance), max(1, existing_rect.height - 2*tolerance))
            if test_rect.colliderect(existing_test_rect):
                return True
        return False

    def _place_tile_in_direction(self, tile, direction, target_tile, connection_value):
        """
        Internal method to handle the logic of placing a tile in a specified direction.
        Returns a tuple: (success, reason_string)
        """
        # Set initial rotation and position
        self._set_tile_rotation(tile, direction, connection_value)
        new_x, new_y = self._calculate_initial_position(tile, target_tile, direction)
        w, h = tile.rect.width, tile.rect.height

        # Check if straight placement is within bounds and not a collision
        if self.play_area_rect.collidepoint(new_x, new_y) and self.play_area_rect.collidepoint(new_x + w, new_y + h):
            if not self._position_occupied(new_x, new_y, w, h):
                tile.rect.x, tile.rect.y = new_x, new_y
                self.tiles.append(tile)
                print(f"[BOARD] Tile successfully placed at ({new_x}, {new_y}) in {direction} direction")
                return True, "success"
        
        # --- Handle Boundary Conditions with Clamping ---
        else:
            clamped_x, clamped_y = self._clamp_to_play_area(new_x, new_y, w, h)
            if not self._position_occupied(clamped_x, clamped_y, w, h):
                tile.rect.x, tile.rect.y = clamped_x, clamped_y
                self.tiles.append(tile)
                print(f"[BOARD] Edge-clamped placement at ({clamped_x}, {clamped_y}) in {direction} direction")
                return True, "success"
            else:
                # If clamping failed due to collision, proceed to corner turns
                print("Straight placement (clamped) failed due to collision. Trying corner turn...")
                
        # --- Handle Corner Turns as Fallback ---
        turn_found = False
        for turn_direction in self._get_corner_turn_directions(target_tile, direction, tile):
            # Recalculate and re-evaluate placement for the new direction
            self._set_tile_rotation(tile, turn_direction, connection_value)
            turned_x, turned_y = self._calculate_initial_position(tile, target_tile, turn_direction)
            turned_w, turned_h = tile.rect.width, tile.rect.height

            # Check if the turned tile is within bounds and not a collision
            if self.play_area_rect.collidepoint(turned_x, turned_y) and self.play_area_rect.collidepoint(turned_x + turned_w, turned_y + turned_h):
                if not self._position_occupied(turned_x, turned_y, turned_w, turned_h):
                    tile.rect.x, tile.rect.y = turned_x, turned_y
                    self.tiles.append(tile)
                    print(f"[BOARD] Tile successfully placed via corner turn to {turn_direction}.")
                    turn_found = True
                    break
            else:
                # If the turned tile is also out of bounds, try to clamp it
                clamped_turned_x, clamped_turned_y = self._clamp_to_play_area(turned_x, turned_y, turned_w, turned_h)
                if not self._position_occupied(clamped_turned_x, clamped_turned_y, turned_w, turned_h):
                    tile.rect.x, tile.rect.y = clamped_turned_x, clamped_turned_y
                    self.tiles.append(tile)
                    print(f"[BOARD] Tile successfully placed via clamped corner turn to {turn_direction}.")
                    turn_found = True
                    break

        if turn_found:
            return True, "success"
        
        # --- FINAL FALLBACK: Try all possible directions with aggressive clamping ---
        print("[BOARD] Corner turns failed. Trying all directions with aggressive clamping...")
        all_directions = ['left', 'right', 'top', 'bottom']
        for fallback_dir in all_directions:
            self._set_tile_rotation(tile, fallback_dir, connection_value)
            fb_x, fb_y = self._calculate_initial_position(tile, target_tile, fallback_dir)
            fb_w, fb_h = tile.rect.width, tile.rect.height
            
            clamped_fb_x, clamped_fb_y = self._clamp_to_play_area(fb_x, fb_y, fb_w, fb_h)
            if not self._position_occupied(clamped_fb_x, clamped_fb_y, fb_w, fb_h):
                tile.rect.x, tile.rect.y = clamped_fb_x, clamped_fb_y
                self.tiles.append(tile)
                print(f"[BOARD] Tile placed via aggressive fallback to {fallback_dir} at ({clamped_fb_x}, {clamped_fb_y})")
                return True, "success"
        
        print("[BOARD] Tile placement failed: No valid position found even with aggressive fallback.")
        return False, "boundary_or_collision_error"

    def _set_tile_rotation(self, tile, direction, connection_value):
        # Your existing _set_tile_rotation logic here...
        if tile.is_double():
            if direction in ['left', 'right']:
                tile.set_rotation(0)
            else:
                tile.set_rotation(90)
        else:
            if direction == 'left':
                tile.set_rotation(270 if connection_value == tile.value1 else 90)
            elif direction == 'right':
                tile.set_rotation(90 if connection_value == tile.value1 else 270)
            elif direction == 'top':
                tile.set_rotation(180 if connection_value == tile.value1 else 0)
            elif direction == 'bottom':
                tile.set_rotation(0 if connection_value == tile.value1 else 180)
    
    def _calculate_initial_position(self, tile, target_tile, direction):
        """
        Calculates the initial position (x, y) for a new tile
        based on the target tile and the play direction.
        """
        if target_tile is None:
            # First tile placed at the center of the board
            return (self.center_x - tile.rect.width / 2,
                    self.center_y - tile.rect.height / 2)

        spacing = 2  # <<< keep a hairline gap so abutting tiles don't "collide"

        if direction == 'left':
            new_x = target_tile.rect.left - tile.rect.width - spacing
            new_y = target_tile.rect.centery - tile.rect.height // 2
        elif direction == 'right':
            new_x = target_tile.rect.right + spacing
            new_y = target_tile.rect.centery - tile.rect.height // 2
        elif direction == 'top':
            new_x = target_tile.rect.centerx - tile.rect.width // 2
            new_y = target_tile.rect.top - tile.rect.height - spacing
        elif direction == 'bottom':
            new_x = target_tile.rect.centerx - tile.rect.width // 2
            new_y = target_tile.rect.bottom + spacing
        else:
            return 0, 0

        return new_x, new_y
        
    def _can_place_tile_directly(self, new_tile, direction, target_tile, connection_value):
        """
        Check if we can place the tile directly in the given direction without hitting boundaries.
        This is more accurate than the previous space-based calculation.
        """
        # Temporarily set up the tile for this placement to get accurate dimensions
        original_rotation = getattr(new_tile, 'rotation', 0)
        
        # Determine rotation for this placement
        if new_tile.is_double():
            if direction in ['left', 'right']:
                test_rotation = 0   # vertical for left/right branches
            else:
                test_rotation = 90  # horizontal for top/bottom branches
        else:
            if direction == 'left':
                test_rotation = 270 if connection_value == new_tile.value1 else 90
            elif direction == 'right':
                test_rotation = 90  if connection_value == new_tile.value1 else 270
            elif direction == 'top':
                test_rotation = 180 if connection_value == new_tile.value1 else 0
            elif direction == 'bottom':
                test_rotation = 0   if connection_value == new_tile.value1 else 180
            else:
                return False
        
        # Temporarily apply rotation to get correct dimensions
        new_tile.set_rotation(test_rotation)
        
        # Calculate position
        target_rect = target_tile.rect
        spacing = 2
        
        if direction == 'left':
            new_x = target_rect.left - new_tile.rect.width - spacing
            new_y = target_rect.centery - new_tile.rect.height // 2
        elif direction == 'right':
            new_x = target_rect.right + spacing
            new_y = target_rect.centery - new_tile.rect.height // 2
        elif direction == 'top':
            new_x = target_rect.centerx - new_tile.rect.width // 2
            new_y = target_rect.top - new_tile.rect.height - spacing
        elif direction == 'bottom':
            new_x = target_rect.centerx - new_tile.rect.width // 2
            new_y = target_rect.bottom + spacing
        else:
            return False
        
        # Check if this position would be within bounds
        can_place = not self.will_exceed_boundary(new_x, new_y, new_tile.rect.width, new_tile.rect.height)
        
        # Restore original rotation
        new_tile.set_rotation(original_rotation)
        
        return can_place

    def _remaining_space_pixels(self, target_tile, direction):
        """
        Calculates the remaining space in pixels on the board from the given target tile
        in the specified direction.
        """
        if direction == 'left':
            return target_tile.rect.left - self.play_area_rect.left
        elif direction == 'right':
            return self.play_area_rect.right - (target_tile.rect.left + target_tile.rect.width)
        elif direction == 'top':
            return target_tile.rect.top - self.play_area_rect.top
        elif direction == 'bottom':
            return self.play_area_rect.bottom - (target_tile.rect.top + target_tile.rect.height)
        return 0
        
    def _has_room_for_at_least_n_tiles(self, target_tile, direction, n=1):
        """
        Quick feasibility check: use the actual dimension needed in the placement direction.
        Prevents premature corner turns when there's sufficient space to continue straight.
        """
        # pixels available from target_tile to the play-area border in this direction
        runway = self._remaining_space_pixels(target_tile, direction)

        # When extending left/right, placed tiles are horizontal (rotated),
        # so the "width" they consume along the branch is tile_height.
        # When extending top/bottom, they consume tile_height vertically as well.
        if direction in ['left', 'right']:
            needed_span = self.tile_height    # ~80px
        else:  # 'top' or 'bottom'
            needed_span = self.tile_height    # ~80px

        need = n * needed_span
        return runway >= need
    
    def _get_corner_turn_directions(self, target_tile, original_direction, next_tile):
        """
        Determines if a corner turn is required and returns the possible turn directions.
        This function is crucial for preventing tiles from turning too soon.
        """
        
        spacing = 2  # This can be changed to whatever spacing you prefer
        
        # Calculate the required space for the next tile based on its orientation
        if original_direction in ['left', 'right']:
            # Horizontal placement: next tile will be horizontal. Width is tile_height.
            if next_tile.is_double():
                needed_span = self.tile_height + spacing
            else:
                needed_span = self.tile_height + spacing
        else: # original_direction is 'top' or 'bottom'
            # Vertical placement: next tile will be vertical. Height is tile_height.
            if next_tile.is_double():
                needed_span = self.tile_height + spacing
            else:
                needed_span = self.tile_height + spacing

        # Get the remaining space in the original direction
        space_in_original_dir = self._remaining_space_pixels(target_tile, original_direction)

        # Only return turn directions if there is not enough space for a straight placement
        if space_in_original_dir < needed_span:
            # Not enough runway, time to turn the corner.
            if original_direction in ['left', 'right']:
                return ['top', 'bottom']
            else: # 'top' or 'bottom'
                return ['left', 'right']
        else:
            # Enough runway, no corner turn is needed.
            return []

    def _clamp_to_play_area(self, x, y, w, h):
        """Clamp a rect (x,y,w,h) to stay fully inside the play area."""
        pa = self.play_area_rect
        clamped_x = max(pa.left, min(x, pa.right - w))
        clamped_y = max(pa.top,  min(y, pa.bottom - h))
        return clamped_x, clamped_y

    def _try_placement_in_direction_with_reason(self, new_tile, direction, target_tile, connection_value):
        """Attempt to place a tile in the specified direction, with gentle edge-clamping."""
        # --- orientation ---
        if new_tile.is_double():
            # Doubles: placed perpendicular to branch direction
            if direction in ['left', 'right']:
                new_tile.set_rotation(0)   # vertical for left/right branches
            else:
                new_tile.set_rotation(90)  # horizontal for top/bottom branches
        else:
            # Regular tiles must face the matching side toward the join
            if direction == 'left':
                new_tile.set_rotation(270 if connection_value == new_tile.value1 else 90)
            elif direction == 'right':
                new_tile.set_rotation(90  if connection_value == new_tile.value1 else 270)
            elif direction == 'top':
                new_tile.set_rotation(180 if connection_value == new_tile.value1 else 0)
            elif direction == 'bottom':
                new_tile.set_rotation(0   if connection_value == new_tile.value1 else 180)
            else:
                return False, "invalid_direction"

        # --- initial position next to target ---
        target_rect = target_tile.rect
        spacing = 2
        if direction == 'left':
            new_x = target_rect.left - new_tile.rect.width - spacing
            new_y = target_rect.centery - new_tile.rect.height // 2
        elif direction == 'right':
            new_x = target_rect.right + spacing
            new_y = target_rect.centery - new_tile.rect.height // 2
        elif direction == 'top':
            new_x = target_rect.centerx - new_tile.rect.width // 2
            new_y = target_rect.top - new_tile.rect.height - spacing
        elif direction == 'bottom':
            new_x = target_rect.centerx - new_tile.rect.width // 2
            new_y = target_rect.bottom + spacing
        else:
            return False, "invalid_direction"

        w, h = new_tile.rect.width, new_tile.rect.height
        
        # DEBUG: Show exactly what's happening with boundary checking
        print(f"[DEBUG BOUNDARY] Direction: {direction}")
        print(f"[DEBUG BOUNDARY] Target tile at: ({target_rect.x}, {target_rect.y}, {target_rect.width}x{target_rect.height})")
        print(f"[DEBUG BOUNDARY] New tile size: {w}x{h}")
        print(f"[DEBUG BOUNDARY] Calculated position: ({new_x}, {new_y})")
        print(f"[DEBUG BOUNDARY] Play area: ({self.play_area_rect.x}, {self.play_area_rect.y}, {self.play_area_rect.width}x{self.play_area_rect.height})")
        
        # Check each boundary condition separately
        exceeds_left = new_x < self.play_area_rect.left
        exceeds_top = new_y < self.play_area_rect.top
        exceeds_right = new_x + w > self.play_area_rect.right
        exceeds_bottom = new_y + h > self.play_area_rect.bottom
        
        print(f"[DEBUG BOUNDARY] Exceeds left: {exceeds_left} (new_x={new_x} < play_left={self.play_area_rect.left})")
        print(f"[DEBUG BOUNDARY] Exceeds top: {exceeds_top} (new_y={new_y} < play_top={self.play_area_rect.top})")
        print(f"[DEBUG BOUNDARY] Exceeds right: {exceeds_right} (new_x+w={new_x+w} > play_right={self.play_area_rect.right})")
        print(f"[DEBUG BOUNDARY] Exceeds bottom: {exceeds_bottom} (new_y+h={new_y+h} > play_bottom={self.play_area_rect.bottom})")

        # --- boundary & collision checks (with one-time edge clamp) ---
        if self.will_exceed_boundary(new_x, new_y, w, h):
            print(f"[DEBUG BOUNDARY] Boundary exceeded, trying edge clamp")
            # Try clamping back inside the play area once before failing
            clamped_x, clamped_y = self._clamp_to_play_area(new_x, new_y, w, h)
            print(f"[DEBUG BOUNDARY] Clamped position: ({clamped_x}, {clamped_y})")
            if (clamped_x, clamped_y) != (new_x, new_y):
                if not self._position_occupied(clamped_x, clamped_y, w, h):
                    new_tile.rect.x, new_tile.rect.y = clamped_x, clamped_y
                    self.tiles.append(new_tile)
                    print(f"[BOARD] Edge-clamped placement at ({clamped_x}, {clamped_y}) in {direction} direction")
                    return True, "success"
            print(f"[DEBUG BOUNDARY] Edge clamp failed, returning boundary error")
            return False, "boundary"

        if self._position_occupied(new_x, new_y, w, h):
            return False, "collision"

        # --- commit placement ---
        new_tile.rect.x, new_tile.rect.y = new_x, new_y
        self.tiles.append(new_tile)
        print(f"[BOARD] Tile successfully placed at ({new_x}, {new_y}) in {direction} direction")
        return True, "success"

    def get_best_strategic_move(self, available_tiles, scoring_enabled=True):
        """
        Pick the best placement option across all tiles in 'available_tiles'.
        Returns a placement option tuple: (direction, target_tile, end_value),
        or None if nothing is playable.
        """
        current_total = self.get_board_ends_total() or 0
        print(f"[BOARD] AI evaluating moves. Current board total: {current_total}")

        best_option = None
        best_tile_for_log = None
        best_score = float("-inf")
        best_tiebreak = (-1, -1)  # (pip_sum, is_double)

        for tile in available_tiles:
            options = self.get_valid_placement_options(tile, require_runway=False)
            if not options:
                continue

            for option in options:
                direction, target_tile, end_value = option
                # Correct call: pass 4 args (tile, direction, target_tile, end_value)
                projected_total = self._calculate_projected_total(tile, direction, target_tile, end_value)

                move_score = self._score_move(
                    projected_total,
                    current_total,
                    scoring_enabled=scoring_enabled
                )

                print(f"[BOARD] Move: {tile.value1}|{tile.value2} {direction}, "
                      f"projected total: {projected_total}, score: {move_score}")

                pip_sum = tile.value1 + tile.value2
                is_double = 1 if tile.is_double() else 0
                tiebreak = (pip_sum, is_double)

                if (move_score > best_score) or (move_score == best_score and tiebreak > best_tiebreak):
                    best_score = move_score
                    best_tiebreak = tiebreak
                    best_option = option
                    best_tile_for_log = tile

        if best_option is not None:
            if scoring_enabled:
                print(f"[BOARD] Best move selected: "
                      f"{best_tile_for_log.value1}|{best_tile_for_log.value2} "
                      f"{best_option[0]} for {best_score} points")
            else:
                print(f"[BOARD] Best move selected (race mode): "
                      f"{best_tile_for_log.value1}|{best_tile_for_log.value2} "
                      f"{best_option[0]} with heuristic score {best_score}")
        else:
            print("[BOARD] No strategic move available")

        return best_option
        
    def _calculate_projected_total(self, tile, direction, target_tile, end_value):
        """
        Compute the board-ends total *after* hypothetically placing `tile`
        at (direction, target_tile, end_value) WITHOUT mutating board state.
        Matches the rules used by get_board_ends_total(), including spinner behavior.
        """

        # --- First tile case -------------------------------------------------------
        if not self.tiles:
            return tile.value1 * 2 if tile.is_double() else (tile.value1 + tile.value2)

        # Helper to get the "other pip" or double contribution for the *new* end
        def _new_end_contrib_for_tile(t, match_val):
            if t.is_double():
                return t.value1 * 2  # e.g., 5|5 contributes 10
            # non-double: exposed end is the side that did NOT match
            return t.value2 if t.value1 == match_val else t.value1

        # Helper to get contribution for an existing end tile
        def _contrib_of_existing_end_tile(end_tile):
            if not end_tile:
                return 0
            if end_tile.is_double():
                return end_tile.value1 * 2
            v = self._get_regular_tile_end_value(end_tile)
            return v if v is not None else 0

        # --- Spinner present --------------------------------------------------------
        if self.spinner_tile:
            spinner = self.spinner_tile

            has_left   = self._is_tile_connected_to_side(spinner, 'left')
            has_right  = self._is_tile_connected_to_side(spinner, 'right')
            has_top    = self._is_tile_connected_to_side(spinner, 'top')
            has_bottom = self._is_tile_connected_to_side(spinner, 'bottom')

            # Branch presence AFTER the hypothetical move
            has_left_after   = has_left   or (target_tile is spinner and direction == 'left')
            has_right_after  = has_right  or (target_tile is spinner and direction == 'right')
            has_top_after    = has_top    or (target_tile is spinner and direction == 'top')
            has_bottom_after = has_bottom or (target_tile is spinner and direction == 'bottom')

            def _branch_contrib_after(dir_name):
                """Contribution of a branch end AFTER this hypothetical placement."""
                if target_tile is spinner and direction == dir_name:
                    # The new end is the placed tile itself
                    return _new_end_contrib_for_tile(tile, end_value)
                # Otherwise, unchanged branch: use current end tile
                end_tile = self._follow_branch_to_end_from_spinner(dir_name)
                return _contrib_of_existing_end_tile(end_tile)

            # Spinner contribution rule:
            # If you use the "spinner stays double until both L&R exist" rule,
            # keep counting the spinner until both left and right branches exist.
            spinner_counts = (
                getattr(self, "scoring_mode", "") == "spinner_stays_12"
                and not (has_left_after and has_right_after)
            )
            total = (spinner.value1 * 2) if spinner_counts else 0

            if has_left_after:
                total += _branch_contrib_after('left')
            if has_right_after:
                total += _branch_contrib_after('right')
            if has_top_after:
                total += _branch_contrib_after('top')
            if has_bottom_after:
                total += _branch_contrib_after('bottom')

            return total

        # --- No spinner: main line left/right only ---------------------------------
        # Compute contributions for each end AFTER this move
        left_end_tile  = self._find_leftmost_main_line_tile()
        right_end_tile = self._find_rightmost_main_line_tile()

        # Start with current ends
        left_contrib  = _contrib_of_existing_end_tile(left_end_tile)
        right_contrib = 0
        if right_end_tile is not None:
            # In a one-tile case, left_end_tile == right_end_tile; after placement
            # there will be two distinct ends, but using existing right end value is fine.
            if right_end_tile is not left_end_tile:
                right_contrib = _contrib_of_existing_end_tile(right_end_tile)
            else:
                right_contrib = _contrib_of_existing_end_tile(right_end_tile)

        # Replace the side we are extending with the contribution from the placed tile
        if direction == 'left':
            left_contrib = _new_end_contrib_for_tile(tile, end_value)
        elif direction == 'right':
            right_contrib = _new_end_contrib_for_tile(tile, end_value)
        else:
            # 'top'/'bottom' should not occur without a spinner; fall back to current total
            return self.get_board_ends_total()

        return (left_contrib + right_contrib)
    
    def _score_move(self, projected_total, current_total, scoring_enabled=True):
        if not scoring_enabled:
            # neutralize the "by 5" bias; keep a tiny defensive nudge
            score = 0
            if projected_total < current_total:
                score += 1
            return score
        # existing logic:
        score = 0
        if projected_total % 5 == 0 and projected_total > 0:
            score += projected_total
        remainder = projected_total % 5
        if remainder in [1, 4]:
            score += 2
        if projected_total < current_total:
            score += 1
        return score

    def _is_tile_connected_to_side(self, tile, direction):
        tile_rect = tile.rect
        buffer = 8
        for other_tile in self.tiles:
            if other_tile is tile:
                continue
            other_rect = other_tile.rect
            if direction == 'top':
                if abs(other_rect.bottom - tile_rect.top) < buffer and abs(other_rect.centerx - tile_rect.centerx) < buffer:
                    return True
            elif direction == 'bottom':
                if abs(other_rect.top - tile_rect.bottom) < buffer and abs(other_rect.centerx - tile_rect.centerx) < buffer:
                    return True
            elif direction == 'left':
                if abs(other_rect.right - tile_rect.left) < buffer and abs(other_rect.centery - tile_rect.centery) < buffer:
                    return True
            elif direction == 'right':
                if abs(other_rect.left - tile_rect.right) < buffer and abs(other_rect.centery - tile_rect.centery) < buffer:
                    return True
        return False

    def _neighbor_on(self, tile, direction):
        tile_rect = tile.rect
        buffer = 8
        for other_tile in self.tiles:
            if other_tile is tile:
                continue
            other_rect = other_tile.rect
            if direction == 'top' and abs(other_rect.bottom - tile_rect.top) < buffer and abs(other_rect.centerx - tile_rect.centerx) < buffer:
                return other_tile
            if direction == 'bottom' and abs(other_rect.top - tile_rect.bottom) < buffer and abs(other_rect.centerx - tile_rect.centerx) < buffer:
                return other_tile
            if direction == 'left' and abs(other_rect.right - tile_rect.left) < buffer and abs(other_rect.centery - tile_rect.centery) < buffer:
                return other_tile
            if direction == 'right' and abs(other_rect.left - tile_rect.right) < buffer and abs(other_rect.centery - tile_rect.centery) < buffer:
                return other_tile
        return None

    def _follow_branch_to_end(self, start_tile, came_from_tile):
        """Follow a branch from start_tile to its end, avoiding came_from_tile."""
        if not start_tile:
            return None
            
        current = start_tile
        prev = came_from_tile
        buffer = 8
        
        while True:
            # Find all tiles connected to current tile
            connected = []
            current_rect = current.rect
            
            for tile in self.tiles:
                if tile is current or tile is prev:
                    continue
                    
                tile_rect = tile.rect
                
                # Check if tiles are adjacent (connected)
                if ((abs(tile_rect.left - current_rect.right) < buffer and abs(tile_rect.centery - current_rect.centery) < buffer) or
                    (abs(tile_rect.right - current_rect.left) < buffer and abs(tile_rect.centery - current_rect.centery) < buffer) or
                    (abs(tile_rect.top - current_rect.bottom) < buffer and abs(tile_rect.centerx - current_rect.centerx) < buffer) or
                    (abs(tile_rect.bottom - current_rect.top) < buffer and abs(tile_rect.centerx - current_rect.centerx) < buffer)):
                    connected.append(tile)
            
            # If no more connections, we've reached the end
            if not connected:
                return current
                
            # Move to the next tile in the chain
            prev = current
            current = connected[0]  # Take first connected tile (should only be one in a proper domino chain)
        
        return current
    
    def _follow_branch_to_end_from_spinner(self, direction):
        """Follow a branch from the spinner in the given direction to its end."""
        if not self.spinner_tile:
            return None
            
        # Find the first tile connected to the spinner in this direction
        first_tile = self._neighbor_on(self.spinner_tile, direction)
        if not first_tile:
            return None
            
        # Follow the branch to its end
        return self._follow_branch_to_end(first_tile, self.spinner_tile)

    def play(self, tile, placement_option=None):
        """Play a tile on the board."""
        print(f"[BOARD] Playing tile {self.tile_count + 1}/28: ({tile.value1}, {tile.value2})")
        tile.update_size(self.tile_width, self.tile_height)
        
        if not self.tiles or (placement_option and placement_option[0] == 'center'):
            if tile.is_double():
                self.spinner_tile = tile
                tile.set_rotation(0)
                print(f"[BOARD] Spinner set: ({tile.value1}, {tile.value2})")
            else:
                tile.set_rotation(90)
            tile.set_position(self.center_x - tile.rect.width // 2,
                              self.center_y - tile.rect.height // 2)
            self.tiles.append(tile)
            self.tile_count += 1
            print(f"[BOARD] First tile placed")
            return True

        if tile.is_double() and self.spinner_tile is None:
            self.spinner_tile = tile
            print(f"[BOARD] First double played, setting as spinner: ({tile.value1}, {tile.value2})")

        if not placement_option:
            print("[BOARD] ERROR: No placement option provided")
            return False

        direction, target_tile, connection_value = placement_option
        if connection_value not in [tile.value1, tile.value2]:
            print(f"[BOARD] ERROR: Tile cannot connect to value {connection_value}")
            return False

        # FIXED: Properly handle the return value from _place_tile_in_direction
        success, reason = self._place_tile_in_direction(tile, direction, target_tile, connection_value)
        if success:
            self.tile_count += 1
            print(f"[BOARD] Tile count now: {self.tile_count}/28")
            return True
        else:
            print(f"[BOARD] Tile placement failed: {reason}")
            return False
        
    def _find_leftmost_main_line_tile(self):
        """Find the leftmost tile that can have a left-extending play."""
        if not self.tiles:
            return None
        
        # Find tiles that are part of the horizontal main line (connected left/right)
        main_line_tiles = []
        for tile in self.tiles:
            if (self._is_tile_connected_to_side(tile, 'left') or
                self._is_tile_connected_to_side(tile, 'right')):
                main_line_tiles.append(tile)
        
        if not main_line_tiles:
            # No main line yet, return the first tile
            return self.tiles[0] if self.tiles else None
        
        # Return the leftmost tile from the main line
        leftmost = min(main_line_tiles, key=lambda t: t.rect.x)
        return leftmost

    def _find_rightmost_main_line_tile(self):
        """Find the rightmost tile that can have a right-extending play."""
        if not self.tiles:
            return None
        
        # Find tiles that are part of the horizontal main line (connected left/right)
        main_line_tiles = []
        for tile in self.tiles:
            if (self._is_tile_connected_to_side(tile, 'left') or
                self._is_tile_connected_to_side(tile, 'right')):
                main_line_tiles.append(tile)
        
        if not main_line_tiles:
            # No main line yet, return the first tile
            return self.tiles[0] if self.tiles else None
        
        # Return the rightmost tile from the main line
        rightmost = max(main_line_tiles, key=lambda t: t.rect.x)
        return rightmost

    def left_end_value(self):
        left_tile = self._find_leftmost_main_line_tile()
        return self._get_regular_tile_end_value(left_tile)

    def right_end_value(self):
        right_tile = self._find_rightmost_main_line_tile()
        return self._get_regular_tile_end_value(right_tile)

    def _get_regular_tile_end_value(self, tile):
        """Get the exposed end value for a tile."""
        if tile is None:
            return None

        # Handle doubles - they always show their value regardless of connections
        if tile.is_double():
            return tile.value1

        # For regular tiles, find the unconnected side and return its value
        connected_sides = []
        for direction in ['top', 'bottom', 'left', 'right']:
            if self._is_tile_connected_to_side(tile, direction):
                connected_sides.append(direction)
        
        # Find the first unconnected side and get its value
        for direction in ['top', 'bottom', 'left', 'right']:
            if direction not in connected_sides:
                value = self._get_tile_connection_value_for_direction(tile, direction)
                if value is not None:
                    return value
        
        return None

    def _get_tile_connection_value_for_direction(self, tile, direction):
        """Get the value that would connect in the specified direction."""
        if tile.is_double():
            return tile.value1
        
        # The tile placement logic uses this rotation scheme:
        # 0°   -> top=value1,    bottom=value2
        # 180° -> top=value2,    bottom=value1
        # 90°  -> left=value1,   right=value2
        # 270° -> left=value2,   right=value1
        
        if tile.rotation == 0:  # vertical
            if direction == 'top':
                return tile.value1
            elif direction == 'bottom':
                return tile.value2
        elif tile.rotation == 180:  # vertical, flipped
            if direction == 'top':
                return tile.value2
            elif direction == 'bottom':
                return tile.value1
        elif tile.rotation == 90:  # horizontal
            if direction == 'left':
                return tile.value1
            elif direction == 'right':
                return tile.value2
        elif tile.rotation == 270:  # horizontal, flipped
            if direction == 'left':
                return tile.value2
            elif direction == 'right':
                return tile.value1
        
        return None

    def _can_branch_in_direction(self, tile, direction):
        """Check if a tile can have a new branch in the given direction."""
        # If already connected in this direction, it's not available
        if self._is_tile_connected_to_side(tile, direction):
            return False
        
        # Special spinner rules
        if tile == self.spinner_tile:
            has_left = self._is_tile_connected_to_side(tile, 'left')
            has_right = self._is_tile_connected_to_side(tile, 'right')
            
            # Always allow left/right if not occupied
            if direction in ['left', 'right']:
                return True
                
            # Only allow top/bottom after both left and right are established
            if direction in ['top', 'bottom']:
                return has_left and has_right
        
        # For non-spinner tiles: they can connect on any open side
        return True

    # Replace the get_board_ends_total method in board.py:

    def get_board_ends_total(self):
        """Return the sum of exposed ends for scoring."""
        if not self.tiles:
            return 0

        # One tile only
        if len(self.tiles) == 1:
            t = self.tiles[0]
            return t.value1 * 2 if t.is_double() else (t.value1 + t.value2)

        # Spinner present
        if self.spinner_tile:
            spinner = self.spinner_tile
            has_left   = self._is_tile_connected_to_side(spinner, 'left')
            has_right  = self._is_tile_connected_to_side(spinner, 'right')
            has_top    = self._is_tile_connected_to_side(spinner, 'top')
            has_bottom = self._is_tile_connected_to_side(spinner, 'bottom')

            def branch_end_value(direction):
                end_tile = self._follow_branch_to_end_from_spinner(direction)
                if not end_tile:
                    return 0
                if end_tile.is_double():
                    return end_tile.value1 * 2
                val = self._get_regular_tile_end_value(end_tile)
                return val if val is not None else 0

            # Spinner stays at its DOUBLE VALUE until both left & right exist
            if getattr(self, "scoring_mode", "") == "spinner_stays_12" and not (has_left and has_right):
                base = spinner.value1 * 2   # 6|6->12, 0|0->0, 5|5->10, etc.
                total = base
                if has_left:
                    total += branch_end_value('left')
                if has_right:
                    total += branch_end_value('right')
                return total

            # After L & R exist: only count actually started branches
            total = 0
            if has_left:
                total += branch_end_value('left')
            if has_right:
                total += branch_end_value('right')
            if has_top:
                total += branch_end_value('top')
            if has_bottom:
                total += branch_end_value('bottom')
            return total

        # -------- No spinner yet: sum the two main-line ends --------
        total = 0
        left_tile  = self._find_leftmost_main_line_tile()
        right_tile = self._find_rightmost_main_line_tile()

        if left_tile:
            if left_tile.is_double():
                total += left_tile.value1 * 2
            else:
                v = self._get_regular_tile_end_value(left_tile)
                if v is not None:
                    total += v

        if right_tile and right_tile is not left_tile:
            if right_tile.is_double():
                total += right_tile.value1 * 2
            else:
                v = self._get_regular_tile_end_value(right_tile)
                if v is not None:
                    total += v

        return total
    
    def get_playable_ends(self, require_runway: bool = True):
        """
        Return a list of (direction, target_tile, exposed_value) that are currently playable.
        `direction` is the direction you would extend FROM the returned `target_tile`.
        If a branch has turned a corner, we report the *actual* open direction at its end.
        """
        ends = []
        if not self.tiles:
            return [('center', None, None)]

        spinner = self.spinner_tile
        if not spinner:
            # No spinner yet: expose the two ends of the main horizontal line
            left_end  = self._find_leftmost_main_line_tile()
            right_end = self._find_rightmost_main_line_tile()

            if left_end:
                open_dir = self._find_actual_open_direction(left_end, require_runway=require_runway)
                if open_dir:
                    v = self._get_tile_connection_value_for_direction(left_end, open_dir)
                    if v is not None:
                        ends.append((open_dir, left_end, v))

            if right_end and right_end != left_end:  # Avoid duplicate if they're the same tile
                open_dir = self._find_actual_open_direction(right_end, require_runway=require_runway)
                if open_dir:
                    v = self._get_tile_connection_value_for_direction(right_end, open_dir)
                    if v is not None:
                        ends.append((open_dir, right_end, v))
            
            return ends

        # Spinner present
        has_left   = self._is_tile_connected_to_side(spinner, 'left')
        has_right  = self._is_tile_connected_to_side(spinner, 'right')
        has_top    = self._is_tile_connected_to_side(spinner, 'top')
        has_bottom = self._is_tile_connected_to_side(spinner, 'bottom')

        # LEFT branch (new or existing)
        if not has_left and self._can_branch_in_direction(spinner, 'left'):
            v = self._get_tile_connection_value_for_direction(spinner, 'left')
            if v is not None:
                ends.append(('left', spinner, v))
        elif has_left:
            end_tile = self._follow_branch_to_end_from_spinner('left')
            if end_tile:
                open_dir = self._find_actual_open_direction(end_tile, require_runway=require_runway)
                if open_dir:
                    v = self._get_tile_connection_value_for_direction(end_tile, open_dir)
                    if v is not None:
                        ends.append((open_dir, end_tile, v))

        # RIGHT branch
        if not has_right and self._can_branch_in_direction(spinner, 'right'):
            v = self._get_tile_connection_value_for_direction(spinner, 'right')
            if v is not None:
                ends.append(('right', spinner, v))
        elif has_right:
            end_tile = self._follow_branch_to_end_from_spinner('right')
            if end_tile:
                open_dir = self._find_actual_open_direction(end_tile, require_runway=require_runway)
                if open_dir:
                    v = self._get_tile_connection_value_for_direction(end_tile, open_dir)
                    if v is not None:
                        ends.append((open_dir, end_tile, v))

        # TOP and BOTTOM are offered once left & right exist
        if has_left and has_right:
            # TOP branch
            if not has_top and self._can_branch_in_direction(spinner, 'top'):
                v = self._get_tile_connection_value_for_direction(spinner, 'top')
                if v is not None:
                    ends.append(('top', spinner, v))
            elif has_top:
                end_tile = self._follow_branch_to_end_from_spinner('top')
                if end_tile:
                    open_dir = self._find_actual_open_direction(end_tile, require_runway=require_runway)
                    if open_dir:
                        v = self._get_tile_connection_value_for_direction(end_tile, open_dir)
                        if v is not None:
                            ends.append((open_dir, end_tile, v))

            # BOTTOM branch
            if not has_bottom and self._can_branch_in_direction(spinner, 'bottom'):
                v = self._get_tile_connection_value_for_direction(spinner, 'bottom')
                if v is not None:
                    ends.append(('bottom', spinner, v))
            elif has_bottom:
                end_tile = self._follow_branch_to_end_from_spinner('bottom')
                if end_tile:
                    open_dir = self._find_actual_open_direction(end_tile, require_runway=require_runway)
                    if open_dir:
                        v = self._get_tile_connection_value_for_direction(end_tile, open_dir)
                        if v is not None:
                            ends.append((open_dir, end_tile, v))

        # De-dupe
        seen, deduped = set(), []
        for item in ends:
            if item not in seen:
                deduped.append(item)
                seen.add(item)
        
        return deduped

    def _can_place_tile_directly_check(self, target_tile, new_tile, direction, is_double_placement=False):
        """
        Checks if a new tile can be placed directly adjacent to a target tile
        in the specified direction without going out of bounds.
        """
        
        spacing = 2  # Spacing between tiles
        
        # Calculate the size of the new tile based on direction and if it's a double
        if new_tile.is_double() or is_double_placement:
            # Double tiles are always square (40x40 in the original log, but let's assume 80x80 here)
            # The log says a double is 40x80, but that seems to be a non-double tile.
            # We'll use the consistent 80x40/40x80 for non-doubles and 80x80 for doubles.
            needed_width = self.tile_height + spacing if direction in ['left', 'right'] else self.tile_width
            needed_height = self.tile_height + spacing if direction in ['top', 'bottom'] else self.tile_width
        elif direction in ['left', 'right']:
            # Normal tile placed horizontally
            needed_width = self.tile_height + spacing
            needed_height = self.tile_width
        else:
            # Normal tile placed vertically
            needed_width = self.tile_width
            needed_height = self.tile_height + spacing

        # Calculate the new tile's position based on the target tile and direction
        if direction == 'left':
            new_x = target_tile.rect.x - needed_width
            new_y = target_tile.rect.y
        elif direction == 'right':
            new_x = target_tile.rect.x + target_tile.rect.width + spacing
            new_y = target_tile.rect.y
        elif direction == 'top':
            new_x = target_tile.rect.x
            new_y = target_tile.rect.y - needed_height
        elif direction == 'bottom':
            new_x = target_tile.rect.x
            new_y = target_tile.rect.y + target_tile.rect.height + spacing
        
        # Check if the new position is within the play area
        is_within_bounds = (
            self.play_area_rect.left <= new_x and
            new_x + needed_width <= self.play_area_rect.right and
            self.play_area_rect.top <= new_y and
            new_y + needed_height <= self.play_area_rect.bottom
        )
        
        # Log the boundary check for debugging
        print(f"[DEBUG BOUNDARY] Check for tile {new_tile.value1}|{new_tile.value2} at calculated position ({new_x}, {new_y}) with size {needed_width}x{needed_height}")
        print(f"[DEBUG BOUNDARY] Is within bounds: {is_within_bounds}")
        
        return is_within_bounds
        
    def _opposite_dir(self, d):
        return {'left':'right','right':'left','top':'bottom','bottom':'top'}.get(d, None)

    def _find_actual_open_direction(self, tile, require_runway=True):
        """Prefer continuing the current chain; only turn if out of runway."""
        connected = [d for d in ['top','bottom','left','right']
                     if self._is_tile_connected_to_side(tile, d)]

        # Prefer horizontal continuation if the tile is in a horizontal chain
        if 'left' in connected or 'right' in connected:
            primary = 'left' if 'left' not in connected else ('right' if 'right' not in connected else None)
            if primary:
                if not require_runway or self._has_room_for_at_least_n_tiles(tile, primary, n=1):
                    return primary
                # out of runway: pick the vertical side with more space
                up = self._remaining_space_pixels(tile, 'top')
                down = self._remaining_space_pixels(tile, 'bottom')
                return 'top' if up >= down else 'bottom'

        # Prefer vertical continuation if the tile is in a vertical chain
        if 'top' in connected or 'bottom' in connected:
            primary = 'top' if 'top' not in connected else ('bottom' if 'bottom' not in connected else None)
            if primary:
                if not require_runway or self._has_room_for_at_least_n_tiles(tile, primary, n=1):
                    return primary
                # out of runway: pick the horizontal side with more space
                left = self._remaining_space_pixels(tile, 'left')
                right = self._remaining_space_pixels(tile, 'right')
                return 'left' if left >= right else 'right'

        # Isolated/ambiguous: pick the side with the most space
        candidates = ['left','right','top','bottom']
        return max(candidates, key=lambda d: self._remaining_space_pixels(tile, d))
        
    def _follow_chain_to_end(self, direction):
        """Follow the main chain to its end in the given direction."""
        if direction == 'left':
            return self._find_leftmost_main_line_tile()
        elif direction == 'right':
            return self._find_rightmost_main_line_tile()
        return None
    
    def can_play_tile(self, tile):
        if not self.tiles:
            return True
        for side, target, value in self.get_playable_ends():
            if value is not None and (value == tile.value1 or value == tile.value2):
                return True
        return False

    def _calculate_board_total(self):
        """Calculates the sum of the values of the exposed ends of the domino branches."""
        total = 0
        for _, _, value in self.exposed_branch_ends:
            total += value
        return total

    def _check_collision_with_border(self, target_tile, direction, tile_to_check):
        """
        Checks if placing a tile in a given direction would cause it to
        go outside the play area's horizontal or vertical bounds.
        Returns True if a collision would occur, False otherwise.
        """
        tile_to_check_copy = tile_to_check.copy()
        self._set_tile_rotation(tile_to_check_copy, direction, target_tile.value1 if direction in ['top', 'bottom'] else target_tile.value2)
        new_x, new_y = self._calculate_initial_position(tile_to_check_copy, target_tile, direction)
        
        if new_x < self.play_area_rect.left or \
           new_x + tile_to_check_copy.rect.width > self.play_area_rect.right or \
           new_y < self.play_area_rect.top or \
           new_y + tile_to_check_copy.rect.height > self.play_area_rect.bottom:
            return True
        return False

    def get_valid_placement_options(self, tile_to_check, require_runway=False):
        """
        Generates a list of all valid placement options for a given tile.
        This version uses the same logic as get_playable_ends.
        """
        if not self.tiles:
            return [('center', None, None)]

        options = []
        playable_ends = self.get_playable_ends(require_runway=require_runway)
        
        for direction, target_tile, end_value in playable_ends:
            # Check if this tile can connect to this end
            if end_value is not None and (end_value == tile_to_check.value1 or end_value == tile_to_check.value2):
                options.append((direction, target_tile, end_value))
        
        print(f"[DEBUG] get_valid_placement_options for {tile_to_check.value1}|{tile_to_check.value2}: found {len(options)} options")
        return options
    
    def get_valid_placement_options_with_scoring(self, tile_to_check, require_runway: bool = True):
        """Same as above, with scoring metadata."""
        if not self.tiles:
            return [('center', None, None, {'scores': False, 'points': 0})]

        options = []
        current_total = self.get_board_ends_total()
        for direction, target_tile, end_value in self.get_playable_ends(require_runway=require_runway):
            if end_value is not None and (end_value == tile_to_check.value1 or end_value == tile_to_check.value2):
                projected_total = self._calculate_projected_total(tile_to_check, direction, target_tile, end_value)
                options.append((
                    direction, target_tile, end_value,
                    {
                        'direction': direction,
                        'target_tile': target_tile,
                        'end_value': end_value,
                        'current_total': current_total,
                        'projected_total': projected_total,
                        'scores': projected_total % 5 == 0 and projected_total > 0,
                        'points': projected_total if (projected_total % 5 == 0 and projected_total > 0) else 0
                    }
                ))
        return options

    def reset_board(self):
        self.tiles = []
        self.tile_count = 0
        self.exposed_branch_ends = []
        self.left_end_direction = 'horizontal'
        self.right_end_direction = 'horizontal'
        self.spinner_tile = None
        print(f"[BOARD] Board reset - tile count: {self.tile_count}, spinner reset")

    def get_tile_count(self):
        return self.tile_count

    def draw(self, screen, show_board_total=None):
        """
        Draw the table and all placed tiles.

        `show_board_total` is accepted for API compatibility with game.py.
        The board itself does not render the total; Game._draw_info_text
        (or your HUD) should handle that.
        """
        import pygame

        # Table / play area
        pygame.draw.rect(screen, (70, 120, 90), self.play_area_rect)   # table color
        pygame.draw.rect(screen, (255, 255, 255), self.play_area_rect, 2)  # border

        # Tiles
        for tile in self.tiles:
            tile.draw(screen)
 
    def draw_overlay(self, surface, lines, title="",
                     subline="Click anywhere to continue"):
        import pygame
        # Dim the play area
        overlay = pygame.Surface(self.play_area_rect.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))  # semi-transparent black
        surface.blit(overlay, self.play_area_rect.topleft)

        # Fonts (reuse existing if you have them)
        big  = getattr(self, "font_big",  None) or pygame.font.SysFont(None, 40)
        mid  = getattr(self, "font_mid",  None) or pygame.font.SysFont(None, 28)
        tiny = getattr(self, "font_tiny", None) or pygame.font.SysFont(None, 22)

        cx = self.play_area_rect.centerx
        y  = self.play_area_rect.top + 40

        if title:
            ts = big.render(title, True, (255, 255, 255))
            rect = ts.get_rect(center=(cx, y))
            surface.blit(ts, rect)
            y += 40

        for line in lines:
            rs = mid.render(line, True, (255, 255, 255))
            rect = rs.get_rect(center=(cx, y))
            surface.blit(rs, rect)
            y += 32

        y += 18
        hs = tiny.render(subline, True, (210, 210, 210))
        rect = hs.get_rect(center=(cx, y))
        surface.blit(hs, rect)

