import pygame
import random
import os
import time  # Add this import for timing
from board import Board
from tile import Tile
from player import Player
from boneyard import Boneyard
import asyncio
# Base path helper (works in browser build, too)
BASE = os.path.dirname(__file__)
def P(*parts): return os.path.join(BASE, *parts)

# Simple caches
_IMG_CACHE = {}         # raw images by filename
_FACE_CACHE = {}        # scaled faces by (l, r, w, h)

# Define a consistent tile size for drawing
TILE_WIDTH = 40
TILE_HEIGHT = 80

def load_image_rel(path):
    """Load image relative to the project, cache by full path."""
    full = P(path)
    if full in _IMG_CACHE:
        return _IMG_CACHE[full]
    img = pygame.image.load(full).convert_alpha()
    _IMG_CACHE[full] = img
    return img

def load_card_face(left, right):
    """
    Load the domino face image. Try common variants so small naming differences
    don't break the web build. We prefer 'card_<l>-<r>.jpg' (lowercase).
    """
    candidates = [
        f"assets/Cards/card_{left}-{right}.jpg",
        f"assets/Cards/card_{left}-{right}.JPG",
        f"assets/Cards/card_{left}_{right}.jpg",   # underscore fallback
        f"assets/Cards/card_{left}_{right}.JPG",
        f"assets/Cards/card_{left}-{right}.png",   # png fallback
        f"assets/Cards/card_{left}_{right}.png",
    ]
    last_err = None
    for rel in candidates:
        try:
            return load_image_rel(rel)
        except Exception as e:
            last_err = e
    # Visible placeholder so game keeps running if missing
    print(f"[ASSET] Could not load face for {left}-{right}: {last_err}")
    ph = pygame.Surface((100, 200), pygame.SRCALPHA)
    ph.fill((0, 0, 0))  # black placeholder
    pygame.draw.rect(ph, (200, 200, 200), ph.get_rect(), 6)
    return ph

def get_face_scaled(left, right, w, h):
    """Return a scaled face Surface for (left,right) at size (w,h)."""
    key = (left, right, int(w), int(h))
    surf = _FACE_CACHE.get(key)
    if surf is None:
        base = load_card_face(left, right)
        surf = pygame.transform.smoothscale(base, (int(w), int(h)))
        _FACE_CACHE[key] = surf
    return surf

class Game:
    def __init__(self, screen, num_players, num_humans, game_mode="scoring"):
        self.game_mode = game_mode
        self.scoring_enabled = (game_mode == "scoring")
        self.screen = screen
        self.num_players = num_players
        self.num_humans = num_humans
        self.players = []
        for i in range(num_players):
            self.players.append(Player(i, is_human=(i < self.num_humans)))
        self.current_player_index = 0
        self.board = Board(screen.get_width(), screen.get_height())
        self.selected_tile = None
        self.boneyard = None
        self.game_over = False
        self.font = pygame.font.SysFont(None, 36)
        self.button_font = pygame.font.SysFont(None, 24)
        self.phase = "playing"           # "playing" | "hand_summary" | "game_over"
        self.overlay_lines = []
        self.overlay_title = ""
        self.overlay_next = None         # "next_hand" | "new_game"
        
        self.show_all_hands = False
        self.show_all_hands_start_time = 0.0
        self.show_all_hands_duration = 6.0
        self.show_winner_info = None

        # Game state for tile placement choice
        self.waiting_for_placement_choice = False
        self.tile_to_place = None
        self.placement_options = []

        # New state variables for round management
        self.last_round_winner_index = None
        self.can_start_any_tile = False
        self.must_play_tile = None
        self.return_to_menu_requested = False   # set when user clicks after final Game Over
        self.exiting = False
        
        # ADD THIS: Flag to prevent double point awards
        self.round_ended = False
        self.cached_board_total = 0

        # AI timing variables
        self.ai_turn_start_time = None
        self.ai_delay = 1.5  # 1.5 seconds delay for AI moves
        self.waiting_for_ai_delay = False
        
        # AI message display
        self.ai_message = None
        self.ai_message_start_time = None
        self.ai_message_duration = 2.0

        # Buttons
        button_width = 150
        button_height = 40
        padding = 10
        
        self.exit_button_rect = pygame.Rect(padding, self.screen.get_height() - button_height - padding, button_width, button_height)
        self.repeat_button_rect = pygame.Rect(padding, self.screen.get_height() - (button_height * 2) - (padding * 2), button_width, button_height)
        self.draw_button_rect = pygame.Rect(self.screen.get_width() - 120, self.screen.get_height() - 100, 100, 40)
        self.pass_button_rect = pygame.Rect(self.screen.get_width() - 120, self.screen.get_height() - 50, 100, 40)

    def _layout_ui(self):
        sw, sh = self.screen.get_width(), self.screen.get_height()
        button_width = 150
        button_height = 40
        padding = 10

        self.exit_button_rect   = pygame.Rect(padding, sh - button_height - padding, button_width, button_height)
        self.repeat_button_rect = pygame.Rect(padding, sh - (button_height * 2) - (padding * 2), button_width, button_height)
        self.draw_button_rect   = pygame.Rect(sw - 120, sh - 100, 100, 40)
        self.pass_button_rect   = pygame.Rect(sw - 120, sh - 50,  100, 40)
        
    def run(self):
            self._deal_initial_hands()
            self.current_player_index = self._determine_starting_player()
            if self.current_player_index is None:
                self.current_player_index = 0
                print("No suitable starting tile found, defaulting to Player 1.")
            
            # Start AI timer if first player is AI
            current_player = self.players[self.current_player_index]
            if not current_player.is_human:
                self.ai_turn_start_time = time.time()
                self.waiting_for_ai_delay = True
            
            running = True
            while running:
                self._layout_ui()
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                        self.game_over = True
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        self._handle_mouse_click(event.pos)
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_f:
                            if self.selected_tile:
                                self.selected_tile.flip()
                                
                self.screen.fill((30, 80, 50))

                # Draw everything
                self.board.draw(self.screen, show_board_total=self.scoring_enabled)

                play_area_rect = self.board.play_area_rect

                for i, player in enumerate(self.players):
                    # Show all hands if the flag is set (during round end display)
                    show_this_hand = player.is_human or (hasattr(self, 'show_all_hands') and self.show_all_hands)

                    if show_this_hand:
                        player.draw_hand(self.screen, play_area_rect)  # face-up; no score line here
                    else:
                        # ↓↓↓ THIS IS THE IMPORTANT CHANGE ↓↓↓
                        self.draw_back_of_hand(self.screen, play_area_rect, i, show_score=self.scoring_enabled)

                self._draw_info_text()
                self._draw_buttons()

                if self.waiting_for_placement_choice:
                    self._draw_placement_buttons()

                message_is_blocking = self._draw_ai_message()
                pygame.display.flip()


                self._check_game_end_conditions()

                if self.game_over:
                    running = False
                    break

                # Handle AI turns with timing delay AND message blocking check
                if not self.waiting_for_placement_choice and not message_is_blocking:
                    current_player = self.players[self.current_player_index]
                    if not current_player.is_human:
                        if self.waiting_for_ai_delay:
                            # Check if enough time has passed
                            if time.time() - self.ai_turn_start_time >= self.ai_delay:
                                self.waiting_for_ai_delay = False
                                self._handle_player_turn()
                        else:
                            # This shouldn't happen, but handle it just in case
                            self._handle_player_turn()

            print("Game Over. Final Scores:")
            for player in self.players:
                print(f"Player {player.index + 1}: {player.score} points")

            # DO NOT quit here—let main.py decide what to do next.
            if getattr(self, "return_to_menu_requested", False):
                return "RETURN_TO_MENU"
            if getattr(self, "exiting", False):
                return "EXIT"
            return "GAME_OVER"
        
    async def run_async(self):
        """Browser-friendly loop: same logic as run(), but yields each frame."""
        self._deal_initial_hands()
        self.current_player_index = self._determine_starting_player() or 0

        # Start AI timer if first player is AI
        current_player = self.players[self.current_player_index]
        if not current_player.is_human:
            self.ai_turn_start_time = time.time()
            self.waiting_for_ai_delay = True

        running = True
        clock = pygame.time.Clock()

        while running:
            self._layout_ui()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    self.game_over = True
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_mouse_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_f and self.selected_tile:
                        self.selected_tile.flip()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    print(f"[CLICK] {event.pos}")
                    self._handle_mouse_click(event.pos)

            self.screen.fill((30, 80, 50))

            # Draw everything
            self.board.draw(self.screen, show_board_total=self.scoring_enabled)
            play_area_rect = self.board.play_area_rect

            for i, player in enumerate(self.players):
                # show humans face-up; AIs face-down unless "reveal all"
                show_this_hand = player.is_human or (hasattr(self, 'show_all_hands') and self.show_all_hands)
                if show_this_hand:
                    player.draw_hand(self.screen, play_area_rect)
                else:
                    self.draw_back_of_hand(self.screen, play_area_rect, i, show_score=self.scoring_enabled)

            self._draw_info_text()
            self._draw_buttons()
            if self.waiting_for_placement_choice:
                self._draw_placement_buttons()

            message_is_blocking = self._draw_ai_message()
            pygame.display.flip()

            # End-of-hand checks
            self._check_game_end_conditions()
            if self.game_over:
                running = False
                break

            # AI turns (with delay), unless a toast/overlay is blocking
            if not self.waiting_for_placement_choice and not message_is_blocking:
                current_player = self.players[self.current_player_index]
                if not current_player.is_human:
                    if self.waiting_for_ai_delay:
                        if time.time() - self.ai_turn_start_time >= self.ai_delay:
                            self.waiting_for_ai_delay = False
                            self._handle_player_turn()
                    else:
                        self._handle_player_turn()

            clock.tick(60)
            # CRUCIAL in browsers: yield once per frame
            await asyncio.sleep(0)

        print("Game Over. Final Scores:")
        for player in self.players:
            print(f"Player {player.index + 1}: {player.score} points")

        if getattr(self, "return_to_menu_requested", False):
            return "RETURN_TO_MENU"
        if getattr(self, "exiting", False):
            return "EXIT"
        return "GAME_OVER"

    def _deal_initial_hands(self):
        """Centralized logic for creating and dealing tiles for a new round/game."""
        self.all_tiles = [Tile(i, j) for i in range(7) for j in range(i, 7)]
        random.shuffle(self.all_tiles)

        hand_size = 9 if self.num_players in [2, 3] else 7
        for player in self.players:
            player.hand = [self.all_tiles.pop() for _ in range(hand_size)]
        self.boneyard = Boneyard(self.all_tiles)
        print("Hands dealt.")

    def _determine_starting_player(self):
        """Determines the starting player based on game state."""
        # SPECIAL CASE: After blocked game, find player with 6|6
        if hasattr(self, 'blocked_game_restart') and self.blocked_game_restart:
            print("Blocked game restart: Looking for player with 6|6 tile...")
            self.blocked_game_restart = False  # Reset flag
            
            for i, player in enumerate(self.players):
                for tile in player.hand:
                    if tile.value1 == 6 and tile.value2 == 6:
                        print(f"Player {i + 1} has the 6|6 tile and will start.")
                        self.must_play_tile = tile
                        self.can_start_any_tile = False
                        return i
            
            # Fallback if no 6|6 found (shouldn't happen)
            print("Warning: No 6|6 tile found! Defaulting to Player 1.")
            self.must_play_tile = None
            self.can_start_any_tile = False
            return 0
        
        # If this is a new round and we have a previous round winner, they start
        if hasattr(self, 'last_round_winner_index') and self.last_round_winner_index is not None:
            print(f"Player {self.last_round_winner_index + 1} (previous round winner) starts this round and can play ANY tile.")
            self.can_start_any_tile = True
            self.must_play_tile = None  # Round winner can play any tile
            return self.last_round_winner_index
        
        # Otherwise, this is the first round - find player with highest double
        highest_double_value = -1
        starting_player_index = None
        starting_tile = None
        
        # Check all players for their highest double
        for i, player in enumerate(self.players):
            player_highest_double = -1
            player_highest_tile = None
            
            # Find this player's highest double
            for tile in player.hand:
                if tile.is_double() and tile.value1 > player_highest_double:
                    player_highest_double = tile.value1
                    player_highest_tile = tile
            
            # Check if this player has the overall highest double so far
            if player_highest_double > highest_double_value:
                highest_double_value = player_highest_double
                starting_player_index = i
                starting_tile = player_highest_tile
        
        if starting_player_index is not None:
            print(f"Player {starting_player_index + 1} starts with the highest double: {highest_double_value}|{highest_double_value}")
            # Store the tile that must be played first (only for first round)
            self.must_play_tile = starting_tile
            self.can_start_any_tile = False
            return starting_player_index
        else:
            # If no doubles at all, default to Player 1 (index 0)
            print("No doubles found in any hand. Player 1 starts.")
            self.must_play_tile = None
            self.can_start_any_tile = False
            return 0

    def _draw_game_screen(self):
        # clear background
        self.screen.fill((14, 70, 45))

        # draw board (let board decide whether to show board total)
        self.board.draw(self.screen, show_board_total=self.scoring_enabled)

        # draw AI backs around the play area; hide scores in Race mode
        play_area_rect = self.board.play_area_rect
        for i in range(1, self.num_players):
            self.draw_back_of_hand(self.screen, play_area_rect, i, show_score=self.scoring_enabled)

        # draw the human hand; hide score in Race mode
        self._draw_human_hand(show_score=self.scoring_enabled)

        # draw buttons, banners, messages, etc.
        self._draw_ui()

        pygame.display.flip()
    
    def _play_tile_and_check_scoring(self, tile, placement_option, current_player):
        """Centralized method to play a tile and handle scoring exactly once."""
        success = self.board.play(tile, placement_option)
        if success:
            current_player.remove_tile(tile)
            self.cached_board_total = self.board.get_board_ends_total()
            
            # Check if player has won the round
            if not current_player.hand:
                print(f"[GAME] Player {current_player.index + 1} played their last tile!")
                if not self.scoring_enabled:
                    # Race mode → this ends the entire game now
                    self.overlay_title = "Game Over"
                    self.overlay_lines = [
                        f"Player {current_player.index + 1} played their last tile.",
                        f"Player {current_player.index + 1} is the winner!",
                        "Click anywhere to continue",
                    ]
                    self.phase = "game_over"
                    self.show_all_hands = True
                    # Let the click handler return to the menu
                    return True
                else:
                    # Classic (points) → end the hand and award points
                    self._end_round_with_winner(current_player)
                    return True
            
            # Clear special first-tile flags
            self.can_start_any_tile = False
            self.must_play_tile = None
            
            # SINGLE SCORING CHECK - only called here
            self._check_for_scoring()

            # Only advance if the scoring didn’t just end the game/hand
            if self.phase != "game_over" and not getattr(self, "round_ended", False):
                self._next_turn()
            return True

        else:
            print("[GAME] Failed to place tile")
            # FIXED: Reset UI state when placement fails so player can try again
            self.waiting_for_placement_choice = False
            self.tile_to_place = None
            self.placement_options = []
            self.selected_tile = None  # Deselect the tile so they can reselect
            return False
            
    def _show_immediate_winner_overlay(self, winner):
        # Freeze play behind a blocking overlay; the click handler will return to menu.
        self.overlay_title = "Game Over"
        self.overlay_lines = [
            f"Player {winner.index + 1} scored {winner.score} points.",
            f"Player {winner.index + 1} is the winner!",
            "Click anywhere to continue",
        ]
        self.phase = "game_over"
        self.show_all_hands = True
        self.waiting_for_placement_choice = False
        self.ai_message = None

#    def _get_hand_info_string(self):
#        """
#        Creates a descriptive string of each player's remaining hand and scores.
#        """
#        hand_info = ""
#        winner_name = self.players[self.last_round_winner_index].name
#        winner_score_from_hand = 0
#
#        # Calculate remaining hand totals and build the string for each player
#        for i, player in enumerate(self.players):
#            if i != self.last_round_winner_index:
#                remaining_tiles = player.hand.get_tiles()
#                if remaining_tiles:
#                    tile_strings = [str(t) for t in remaining_tiles]
#                    hand_sum = sum(t.value1 + t.value2 for t in remaining_tiles)
#                    # Round up to the nearest multiple of 5
#                    points_awarded = math.ceil(hand_sum / 5) * 5
#                    winner_score_from_hand += points_awarded
#                    hand_info += f"{player.name}'s remaining tile(s): ({', '.join(tile_strings)}) Total = {hand_sum} ~ {points_awarded}\n"
#
#        # Add the total points received by the winner
#        hand_info += f"{winner_name} receives {winner_score_from_hand} points.\n"
#        
#        # Add the current total score for all players
#        for player in self.players:
#            hand_info += f"{player.name} Total = {player.score} points\n"
#
#        # Add the next starting player
#        next_starter_name = self.players[self.last_round_winner_index].name
#        hand_info += f"{next_starter_name} plays first in the next hand!"
#
#        return hand_info

    # ------------------------- Overlay drawing helpers --------------------------
    def _has_playable_move(self, player) -> bool:
        """True if any tile in player's hand can be placed, allowing corner turns."""
        playable_ends = self.board.get_playable_ends(require_runway=False)
        
        for tile in player.hand:
            for direction, target_tile, end_value in playable_ends:
                if end_value is not None and (end_value == tile.value1 or end_value == tile.value2):
                    return True
        return False

    def _end_round_with_winner(self, winner):
        # Prevent double-scoring / double-reset
        if getattr(self, "round_ended", False):
            return

        # Mark the round as ended to stop normal turn processing
        self.round_ended = True

        # The winner of a normal (non-blocked) round starts next time
        self.last_round_winner_index = winner.index

        # Award points and prime the overlay state
        points = self._award_end_round_points(winner)
        self._show_hand_result_overlay(winner, points, blocked=False)

    def reset_game(self):
        """Resets the entire game for a fresh start, including scores."""
        self.players = [Player(i, is_human=(i < self.num_humans)) for i in range(self.num_players)]
        for player in self.players:
            player.score = 0
        
        # Reset ALL round tracking variables
        self.last_round_winner_index = None
        self.can_start_any_tile = False
        self.must_play_tile = None
        self.round_ended = False  # RESET FLAG
        self.game_over = False
        self.selected_tile = None
        self.waiting_for_placement_choice = False
        self.tile_to_place = None
        self.placement_options = []
        self.cached_board_total = 0
        
        # Reset AI timing
        self.ai_turn_start_time = None
        self.waiting_for_ai_delay = False
        
        # Reset AI messages
        self.ai_message = None
        self.ai_message_start_time = None
        
        # COMPATIBLE: Use the board's reset method
        self.board.reset_board()
        
        # Deal initial hands and determine starting player (will use highest double logic)
        self._deal_initial_hands()
        self.current_player_index = self._determine_starting_player() or 0
        
        # Start AI timer if first player is AI
        current_player = self.players[self.current_player_index]
        if not current_player.is_human:
            self.ai_turn_start_time = time.time()
            self.waiting_for_ai_delay = True
        
        print("New game started!")

    def _check_game_end_conditions(self):
        """Only handles blocked-hand resolution. A player going out is handled
        immediately in _play_tile_and_check_scoring()."""
        # If a hand just ended or we’re already showing Game Over, do nothing.
        if self.round_ended or self.phase == "game_over":
            return

        # Nothing to check until the board has tiles.
        if not self.board.tiles:
            return

        # Is the hand blocked? (nobody can play), and the boneyard is empty.
        can_any = any(self._has_playable_move(p) for p in self.players)
        if (not can_any) and self.boneyard.is_empty():
            print("Game is locked! No player can make a move and boneyard is empty. Round Over.")
            self.round_ended = True

            # Winner = fewest pips
            pip_totals = [(i, sum(t.value1 + t.value2 for t in p.hand)) for i, p in enumerate(self.players)]
            pip_totals.sort(key=lambda x: x[1])
            winner_idx, best_pips = pip_totals[0]
            winner = self.players[winner_idx]

            # In blocked games the next round restarts with 6|6 (classic only)
            self.last_round_winner_index = None
            self.blocked_game_restart = True

            if not self.scoring_enabled:
                # Race mode: blocked → fewest pips wins the WHOLE game
                self.overlay_title = "Game Over"
                self.overlay_lines = [
                    "The hand is blocked.",
                    f"Player {winner.index + 1} wins with the fewest pips ({best_pips}).",
                    "Click anywhere to continue",
                ]
                self.phase = "game_over"
                self.show_all_hands = True
                return

            # Classic mode: award points and show the hand summary
            points = self._award_end_round_points(winner)
            self._show_hand_result_overlay(winner, points, blocked=True)

    def _award_end_round_points(self, round_winner_player):
        """Awards points to the player who ended the round (or won a locked game) from opponents' remaining tiles."""
        points_this_round = 0
        
        print(f"\n=== ROUND END POINT CALCULATION ===")
        print(f"Round winner: Player {round_winner_player.index + 1}")
        
        for player in self.players:
            if player != round_winner_player:
                player_hand_points = 0
                print(f"Player {player.index + 1} remaining tiles:")
                for tile in player.hand:
                    tile_points = tile.value1 + tile.value2
                    player_hand_points += tile_points
                    print(f"  {tile.value1}|{tile.value2} = {tile_points} points")
                print(f"  Player {player.index + 1} total: {player_hand_points} points")
                points_this_round += player_hand_points
        
        print(f"Total points from all opponents: {points_this_round}")
        
        # Round to the nearest multiple of 5
        rounded_points = round(points_this_round / 5) * 5
        round_winner_player.add_score(rounded_points)
        print(f"Player {round_winner_player.index + 1} awarded {rounded_points} points!")
        print("=== END CALCULATION ===\n")
        return rounded_points

    def _end_round_and_reset_board(self):
        """Resets the board and redeals for a new round."""
        print("Ending round and resetting board...")
        
        # Collect all tiles back into all_tiles list
        self.all_tiles = []
        for player in self.players:
            self.all_tiles.extend(player.hand)
            player.hand = []
        self.all_tiles.extend(self.board.tiles)
        
        if self.boneyard:
            self.all_tiles.extend(self.boneyard.tiles)
        
        # COMPATIBLE: Use the board's reset method
        self.board.reset_board()
        self.cached_board_total = 0
        
        random.shuffle(self.all_tiles)

        # Redeal tiles
        hand_size = 9 if self.num_players in [2, 3] else 7
        for player in self.players:
            player.hand = [self.all_tiles.pop() for _ in range(hand_size)]
        
        self.boneyard = Boneyard(self.all_tiles)

        # The round winner starts the next round and can play any tile
        if self.last_round_winner_index is not None:
            self.current_player_index = self.last_round_winner_index
            self.can_start_any_tile = True  # Winner can play any tile
            self.must_play_tile = None      # No restriction on which tile
            print(f"Player {self.current_player_index + 1} (round winner) starts and can play any tile.")
        else:
            # Fallback (shouldn't happen in normal gameplay)
            self.current_player_index = self._determine_starting_player() or 0
            self.can_start_any_tile = False

        # Reset game state
        self.selected_tile = None
        self.waiting_for_placement_choice = False
        self.tile_to_place = None
        self.placement_options = []
        self.round_ended = False  # RESET FLAG FOR NEW ROUND
        
        # Start AI timer if next player is AI
        current_player = self.players[self.current_player_index]
        if not current_player.is_human:
            self.ai_turn_start_time = time.time()
            self.waiting_for_ai_delay = True

    def _next_turn(self):
        self.current_player_index = (self.current_player_index + 1) % self.num_players
        self.selected_tile = None
        print(f"It's now Player {self.current_player_index + 1}'s turn.")
        
        # Start AI delay timer if next player is AI
        current_player = self.players[self.current_player_index]
        if not current_player.is_human:
            self.ai_turn_start_time = time.time()
            self.waiting_for_ai_delay = True

    def _check_for_scoring(self):
        if not self.scoring_enabled:
            return
        score = self.board.get_board_ends_total()
        self.cached_board_total = score
        print(f"[GAME] Board total calculated as: {score}")

        if score > 0 and score % 5 == 0:
            current = self.players[self.current_player_index]
            current.add_score(score)
            print(f"Player {current.index + 1} scored {score} points! Total: {current.score}")
            self._show_ai_message(f"Player {current.index + 1} scored {score} points!")

            # NEW: immediate game over on 150+
            if current.score >= 150:
                self._show_immediate_winner_overlay(current)
                self.overlay_lines.append("Click anywhere to return to the main menu.")
                return  # phase is now "game_over"; keep loop running until user clicks
        else:
            print(f"[GAME] No scoring: {score} is not divisible by 5")

    # --------------------------- Human input (corner-aware) ----------------------
    
    def _handle_mouse_click(self, mouse_pos):
        current_player = self.players[self.current_player_index]

        # --- Click-to-continue overlays ------------------------------------------
        if self.phase == "hand_summary":
            # If someone reached 150+, show a winner announcement
            if any(p.score >= 150 for p in self.players):
                winner = max(self.players, key=lambda p: p.score)
                self.overlay_title = "Game Over"
                # inside _handle_mouse_click when phase == "hand_summary" and someone has 150+
                self.overlay_lines = [
                    f"Player {winner.index + 1} scored {winner.score} points.",
                    f"Player {winner.index + 1} is the winner!",
                    "Click anywhere to return to the main menu."
                ]
                self.phase = "game_over"
                return

            # Otherwise, start the next hand now
            self.show_all_hands = False
            self.overlay_lines = []
            self.overlay_title = ""
            self._end_round_and_reset_board()   # redeal & next starter already handled here
            self.phase = "playing"
            return

        if self.phase == "game_over":
            self.return_to_menu_requested = True
            self.game_over = True
            return
            
        if self.repeat_button_rect.collidepoint(mouse_pos):
            print("[UI] New Game clicked")
            self.reset_game()
            return

        # --- Cancel placement choice if clicking outside buttons ------------------
        if self.waiting_for_placement_choice:
            clicked_on_button = False
            for option, rect in self.placement_options:
                if rect.collidepoint(mouse_pos):
                    clicked_on_button = True
                    break

            if not clicked_on_button:
                print("[GAME] Canceling placement choice")
                self.waiting_for_placement_choice = False
                self.tile_to_place = None
                self.placement_options = []
                self.selected_tile = None
                return

        # --- Draw Tile button -----------------------------------------------------
        if self.draw_button_rect.collidepoint(mouse_pos):
            if not current_player.is_human:
                print("Only human players can click draw.")
                return

            # Don’t allow drawing if you can already play
            if self._has_playable_move(current_player):
                self._show_ai_message("You already have a playable tile.")
                return

            drew_any = False
            # Draw until playable or boneyard is empty
            while (not self._has_playable_move(current_player)) and (not self.boneyard.is_empty()):
                drawn_tile = self.boneyard.draw_tile()
                current_player.add_tile(drawn_tile)
                drew_any = True
                print(f"Player {current_player.index + 1} drew a tile: ({drawn_tile.value1}, {drawn_tile.value2})")
                self._show_ai_message(f"Player {current_player.index + 1} drew {drawn_tile.value1}|{drawn_tile.value2}.")

            # If you can play now, keep the turn (no auto-pass)
            if self._has_playable_move(current_player):
                # clear any pending UI state
                self.selected_tile = None
                self.waiting_for_placement_choice = False
                self.tile_to_place = None
                self.placement_options = []
                self._show_ai_message("You can play now.")
                return

            # Boneyard empty and still no move → pass
            next_player_index = (self.current_player_index + 1) % self.num_players
            if drew_any or self.boneyard.is_empty():
                self._show_ai_message(
                    f"No tiles to draw. Play passes to Player {next_player_index + 1}."
                )
                # clear any pending UI state, then pass
                self.selected_tile = None
                self.waiting_for_placement_choice = False
                self.tile_to_place = None
                self.placement_options = []
                self._next_turn()
            else:
                # (Shouldn’t happen: drew_any False but boneyard not empty)
                self._show_ai_message("Please draw a tile.")
            return

        # --- Pass button ----------------------------------------------------------
        if self.pass_button_rect.collidepoint(mouse_pos):
            if not current_player.is_human:
                print("Only human players can click pass.")
                return

            if self._has_playable_move(current_player):
                self._show_ai_message("You have a playable tile and cannot pass.")
                return

            if not self.boneyard.is_empty():
                # Must draw when tiles remain
                self._show_ai_message('Please click the "Draw Tile" button')
                return

            # Allowed to pass: no playable tiles and boneyard is empty
            print(f"Player {current_player.index + 1} passed their turn.")
            next_player_index = (self.current_player_index + 1) % self.num_players
            self._show_ai_message(
                f"Player {current_player.index + 1} passed. "
                f"Play passes to Player {next_player_index + 1}."
            )
            self.selected_tile = None
            self._next_turn()
            return

        # --- New Game button ------------------------------------------------------
        if self.repeat_button_rect.collidepoint(mouse_pos):
            print("Starting a new game.")
            self.reset_game()
            return

        # --- Exit button ----------------------------------------------------------
        if self.exit_button_rect.collidepoint(mouse_pos):
            print("Exiting game.")
            self.exiting = True
            self.game_over = True
            return

        # --- Placement-choice buttons (when multiple ends are available) ----------
        if self.waiting_for_placement_choice:
            for option, rect in self.placement_options:
                if rect.collidepoint(mouse_pos):
                    # Cancel
                    if option == 'cancel':
                        print("[GAME] Player canceled tile placement")
                        self.waiting_for_placement_choice = False
                        self.tile_to_place = None
                        self.placement_options = []
                        self.selected_tile = None
                        return

                    # Normal placement
                    self._play_tile_and_check_scoring(self.tile_to_place, option, current_player)
                    self.waiting_for_placement_choice = False
                    self.tile_to_place = None
                    self.placement_options = []
                    self.selected_tile = None
                    return

        # --- Tile selection (human only) ------------------------------------------
        if current_player.is_human and not self.waiting_for_placement_choice:
            for tile in current_player.hand:
                if tile.rect.collidepoint(mouse_pos):
                    print(f"[GAME] Player clicked on tile ({tile.value1}, {tile.value2})")

                    # Deselect if clicked again
                    if self.selected_tile == tile:
                        print(f"[GAME] Deselecting tile ({tile.value1}, {tile.value2})")
                        self.selected_tile = None
                        return

                    playable_options = []

                    # First tile of the round?
                    if not self.board.tiles:
                        if hasattr(self, 'must_play_tile') and self.must_play_tile:
                            if tile != self.must_play_tile:
                                print(f"You must play the {self.must_play_tile.value1}|{self.must_play_tile.value2} tile first!")
                                return
                            playable_options = [('center', None, None)]
                            print(f"Playing required starting tile: {tile.value1}|{tile.value2}")
                        elif self.can_start_any_tile:
                            playable_options = [('center', None, None)]
                            print(f"Round winner can play any tile: {tile.value1}|{tile.value2}")
                    else:
                        # Corner-aware option discovery for humans
                        playable_options = self.board.get_valid_placement_options(
                            tile, require_runway=False
                        )
                        print(f"[GAME] Found {len(playable_options)} valid placement options for tile ({tile.value1}, {tile.value2})")

                    if not playable_options:
                        print(f"[GAME] That tile ({tile.value1}, {tile.value2}) cannot be played.")
                        self.selected_tile = None
                        return

                    # Always select the tile
                    self.selected_tile = tile
                    self.tile_to_place = tile

                    # First tile: play immediately
                    if not self.board.tiles and len(playable_options) == 1 and playable_options[0][0] == 'center':
                        print(f"[GAME] Playing first tile immediately")
                        self._play_tile_and_check_scoring(tile, playable_options[0], current_player)
                        self.selected_tile = None
                        self.tile_to_place = None
                        return

                    # One option → play immediately; multiple → show choice buttons
                    if len(playable_options) == 1 and playable_options[0][0] != 'center':
                        self._play_tile_and_check_scoring(tile, playable_options[0], current_player)
                        self.selected_tile = None
                        self.tile_to_place = None
                    else:
                        self.placement_options = self._create_placement_buttons(playable_options)
                        self.waiting_for_placement_choice = True
                    return

    # ----------------------------- AI turn (corner-aware) -----------------------

    def _handle_player_turn(self):
        """Handles the automatic turn logic for AI players."""
        if self.game_over or self.waiting_for_placement_choice:
            return

        current_player = self.players[self.current_player_index]
        print(f"[GAME] Player {self.current_player_index + 1} ({'Human' if current_player.is_human else 'AI'}) turn")

        if not current_player.is_human:
            # Show ends for debugging (unchanged)
            available_ends = self.board.get_playable_ends()
            print(f"[DEBUG] Available ends before AI move: {available_ends}")
            for direction, target, value in available_ends:
                if target:
                    print(f"[DEBUG] Can play on {direction} of tile ({target.value1},{target.value2}) matching value {value}")
                else:
                    print(f"[DEBUG] Can play {direction} (no target tile)")

            # --- Special first-tile cases (unchanged) ---
            if hasattr(self, 'must_play_tile') and self.must_play_tile and not self.board.tiles:
                if self.must_play_tile in current_player.hand:
                    print(f"[GAME] AI must play required starting tile: ({self.must_play_tile.value1}, {self.must_play_tile.value2})")
                    self._play_tile_and_check_scoring(self.must_play_tile, ('center', None, None), current_player)
                    return

            elif self.can_start_any_tile and self.current_player_index == current_player.index and not self.board.tiles:
                if current_player.hand:
                    # Prefer doubles / higher totals for very first play (unchanged)
                    best_starting_tile = None
                    best_score = -1
                    for tile in current_player.hand:
                        tile_score = (20 if tile.is_double() else 0) + (tile.value1 + tile.value2)
                        if tile_score > best_score:
                            best_score = tile_score
                            best_starting_tile = tile
                    if best_starting_tile:
                        print(f"[GAME] AI (last round winner) strategically selected starting tile ({best_starting_tile.value1}, {best_starting_tile.value2})")
                        self._play_tile_and_check_scoring(best_starting_tile, ('center', None, None), current_player)
                        return

            # --- MAIN STRATEGIC LOGIC with loop guard (unchanged) ---
            tried = set()  # (tile_id, direction, target_id)
            max_attempts = max(4, len(current_player.hand) * 4)

            attempts = 0
            while attempts < max_attempts:
                attempts += 1

                best_strategic_move = self.board.get_best_strategic_move(current_player.hand)
                if not best_strategic_move:
                    print("[GAME] No strategic move found, falling back to random selection")
                    break

                direction, target_tile, connection_value = best_strategic_move

                # Find a tile that matches this exact move and verify its option exists
                selected_tile = None
                for tile in current_player.hand:
                    if connection_value in (tile.value1, tile.value2):
                        # Strategy may be runway-only; we verify with standard options first
                        tile_options = self.board.get_valid_placement_options(tile)
                        for tile_direction, tile_target, tile_value in tile_options:
                            if (tile_direction == direction and tile_target == target_tile and tile_value == connection_value):
                                selected_tile = tile
                                break
                    if selected_tile:
                        break

                move_key = (id(selected_tile) if selected_tile else None,
                            direction,
                            id(target_tile) if target_tile else 0)

                if selected_tile is None:
                    # Strategy pointed to something we can't actually execute; exit to fallback
                    print("[GAME] Could not match a tile for the strategic move; falling back")
                    break

                if move_key in tried:
                    # We already tried this exact placement and it failed—avoid looping
                    print("[GAME] Already tried this strategic placement; breaking to fallback")
                    break

                print(f"[GAME] AI using strategic move: tile ({selected_tile.value1}, {selected_tile.value2}) {direction}")
                if self._play_tile_and_check_scoring(selected_tile, best_strategic_move, current_player):
                    return  # Success ends AI's turn
                else:
                    print("[GAME] Strategic move failed to place, will try a different option")
                    tried.add(move_key)
                    continue  # Ask strategy again; if it returns the same, the guard will break

            # --- FALLBACK: try any playable tile/options (CORNER-AWARE) ---
            playable_tiles = []
            for tile in current_player.hand:
                options = self.board.get_valid_placement_options(tile, require_runway=False)
                if options:
                    playable_tiles.append((tile, options))

            if playable_tiles:
                placement_succeeded = False

                for tile_to_play, placement_options in playable_tiles:
                    if placement_succeeded:
                        break

                    for chosen_option in placement_options:
                        print(f"[GAME] AI trying fallback tile ({tile_to_play.value1}, {tile_to_play.value2}) with option {chosen_option}")
                        if self._play_tile_and_check_scoring(tile_to_play, chosen_option, current_player):
                            placement_succeeded = True
                            break
                        else:
                            print(f"[GAME] AI failed to place fallback tile ({tile_to_play.value1}, {tile_to_play.value2})")

                if not placement_succeeded:
                    print("[GAME] AI failed to place any tile with any option")
                    self._next_turn()
            else:
                # No playable tiles → draw until playable or empty, else pass
                if not playable_tiles:
                    if not self.boneyard.is_empty():
                        drew_any = False
                        # Keep drawing until a move exists or the boneyard is empty
                        while (not any(self.board.get_valid_placement_options(t, require_runway=False)
                                       for t in current_player.hand)) and (not self.boneyard.is_empty()):
                            drawn_tile = self.boneyard.draw_tile()
                            current_player.add_tile(drawn_tile)
                            drew_any = True
                            print(f"[GAME] AI drew a tile: ({drawn_tile.value1}, {drawn_tile.value2})")
                            self._show_ai_message(f"Player {current_player.index + 1} drew a tile from the boneyard.")

                        # If drawing produced a legal move, let the AI act on its next tick
                        if any(self.board.get_valid_placement_options(t, require_runway=False) for t in current_player.hand):
                            return  # stay on same player's turn; next call will try to play

                        # Still no move (boneyard must be empty or all draws unplayable) → pass
                        print("[GAME] AI still no moves after drawing, passing")
                        next_player_index = (self.current_player_index + 1) % self.num_players
                        self._show_ai_message(
                            f"Player {current_player.index + 1} cannot play. Play passes to Player {next_player_index + 1}."
                        )
                        self._next_turn()
                    else:
                        print("[GAME] AI cannot play and boneyard is empty, passing")
                        next_player_index = (self.current_player_index + 1) % self.num_players
                        self._show_ai_message(
                            f"Player {current_player.index + 1} cannot play. Play passes to Player {next_player_index + 1}."
                        )
                        self._next_turn()
                else:
                    print("[GAME] AI cannot play and boneyard is empty, passing")
                    next_player_index = (self.current_player_index + 1) % self.num_players
                    self._show_ai_message(f"Player {current_player.index + 1} cannot play. Play passes to Player {next_player_index + 1}.")
                    self._next_turn()

    # -------------------------- Messaging & overlays ----------------------------

    def _show_ai_message(self, message):
        """Display a message about player actions to the user for a few seconds"""
        # Set up the message display
        self.ai_message = message
        self.ai_message_start_time = time.time()
        
        # Use 2 seconds for drawing/scoring messages, 5 seconds for others
        if "drew a tile" in message or "scored" in message:
            self.ai_message_duration = 2.0
        else:
            self.ai_message_duration = 5.0
        
        print(f"[AI MESSAGE] Showing: {message}")  # Debug print

    def _draw_ai_message(self):
        """
        Draws persistent overlays (hand result / game over) and the transient toast.
        While an overlay is on screen, return True to block AI/human turn logic.
        """
        # 1) Persistent overlays ----------------------------------------------------
        if self.phase in ("hand_summary", "game_over"):
            # show all hands during overlays
            self.show_all_hands = True
            title = self.overlay_title or ("Game Over" if self.phase == "game_over" else "Hand Result")
            lines = self.overlay_lines or []
            # Renders a dimmed panel with our title/lines and "Click anywhere to continue"
            self.board.draw_overlay(self.screen, lines, title)
            return True  # overlays are blocking

        # 2) Toast message (short, non-blocking unless visible) --------------------
        if getattr(self, 'ai_message', None):
            now = time.time()
            if now - self.ai_message_start_time < self.ai_message_duration:
                message_font = pygame.font.SysFont(None, 36)
                text_surface = message_font.render(self.ai_message, True, (255, 255, 255))
                text_rect = text_surface.get_rect(center=(self.screen.get_width() // 2,
                                                          self.screen.get_height() // 2))
                padding = 30
                background_rect = pygame.Rect(
                    text_rect.left - padding, text_rect.top - padding,
                    text_rect.width + 2 * padding, text_rect.height + 2 * padding
                )
                bg = pygame.Surface((background_rect.width, background_rect.height))
                bg.set_alpha(220)
                bg.fill((0, 0, 0))
                pygame.draw.rect(bg, (255, 255, 0), bg.get_rect(), 3)
                self.screen.blit(bg, background_rect)
                self.screen.blit(text_surface, text_rect)
                return True
            else:
                self.ai_message = None

        return False

    # ------------------------------ UI helpers ---------------------------------

    def _draw_info_text(self):
        current_player = self.players[self.current_player_index]
        text_player = self.font.render(f"Current Player: {current_player.index + 1}", True, (255, 255, 255))
        self.screen.blit(text_player, (10, 10))

        # Only show Board Total in Classic (scoring) mode
        if self.scoring_enabled:
            text_total = self.font.render(f"Board Total: {self.cached_board_total}", True, (255, 255, 255))
            self.screen.blit(text_total, (10, 10 + text_player.get_height() + 5))

    def _draw_buttons(self):
        # Draw "Draw Tile" button
        pygame.draw.rect(self.screen, (0, 150, 0), self.draw_button_rect)
        draw_text = self.button_font.render("Draw Tile", True, (255, 255, 255))
        draw_text_rect = draw_text.get_rect(center=self.draw_button_rect.center)
        self.screen.blit(draw_text, draw_text_rect)

        # Draw "Pass" button
        pygame.draw.rect(self.screen, (150, 0, 0), self.pass_button_rect)
        pass_text = self.button_font.render("Pass", True, (255, 255, 255))
        pass_text_rect = pass_text.get_rect(center=self.pass_button_rect.center)
        self.screen.blit(pass_text, pass_text_rect)

        # Draw "New Game" button
        pygame.draw.rect(self.screen, (0, 0, 150), self.repeat_button_rect)
        repeat_text = self.button_font.render("New Game", True, (255, 255, 255))
        repeat_text_rect = repeat_text.get_rect(center=self.repeat_button_rect.center)
        self.screen.blit(repeat_text, repeat_text_rect)

        # Draw "Exit" button
        pygame.draw.rect(self.screen, (150, 150, 0), self.exit_button_rect)
        exit_text = self.button_font.render("Exit", True, (0, 0, 0))
        exit_text_rect = exit_text.get_rect(center=self.exit_button_rect.center)
        self.screen.blit(exit_text, exit_text_rect)

    def _draw_placement_buttons(self):
        # Display placement options as buttons
        for option, rect in self.placement_options:
            # Different color for cancel button
            if option == 'cancel':
                pygame.draw.rect(self.screen, (150, 50, 50), rect)  # Red for cancel
                button_text = "Cancel"
            else:
                pygame.draw.rect(self.screen, (50, 50, 200), rect)  # Blue for placement buttons
                
                if option[0] == 'left':
                    button_text = f"Left ({option[2]})"
                elif option[0] == 'right':
                    button_text = f"Right ({option[2]})"
                elif option[0] == 'top':
                    button_text = f"Top ({option[2]})"
                elif option[0] == 'bottom':
                    button_text = f"Bottom ({option[2]})"
                elif option[0] == 'center':
                    button_text = "Center"
                else:
                    button_text = str(option[0])

            text_surf = self.button_font.render(button_text, True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=rect.center)
            self.screen.blit(text_surf, text_rect)
            
    def _create_placement_buttons(self, playable_options):
        """
        Build button rects for each placement option and (when there is only one
        option) add a 'Cancel' button so the player can change their mind.
        Returns: list[(option, pygame.Rect)]
                 where option is either ('left'|'right'|'top'|'bottom'|'center', target_tile, end_value)
                 or the string 'cancel'.
        """
        buttons = []

        button_width = 120
        button_height = 40
        gap = 10

        add_cancel = (len(playable_options) == 1)
        num_buttons = len(playable_options) + (1 if add_cancel else 0)

        start_x = self.screen.get_width() // 2 - (num_buttons * button_width + (num_buttons - 1) * gap) // 2
        y = self.screen.get_height() // 2

        # One button per placement option
        for i, option in enumerate(playable_options):
            x = start_x + i * (button_width + gap)
            rect = pygame.Rect(x, y, button_width, button_height)
            buttons.append((option, rect))

        # Optional Cancel button
        if add_cancel:
            x = start_x + (num_buttons - 1) * (button_width + gap)
            rect = pygame.Rect(x, y, button_width, button_height)
            buttons.append(('cancel', rect))

        return buttons

    def draw_back_of_hand(self, screen, play_area_rect, player_index, *, show_score=True):
        """
        Draw the back of a player's hand around the play area.
        player_index: 0=bottom, 1=left, 2=top, 3=right
        show_score: when False (Race mode), the 'Score:' label is hidden
        """
        import os
        import pygame

        # --- sizing ---
        tw = getattr(self.board, "tile_width", 60)
        th = getattr(self.board, "tile_height", 120)
        spacing = 10
        gap_from_area = 20
        gap_text_to_tiles = 12
        text_pad = 8

        # --- card back (cached by size) ---
        if not hasattr(self, "_tile_back_img_cache"):
            self._tile_back_img_cache = {}
        key = (tw, th)
        if key not in self._tile_back_img_cache:
            base = None
            for name in ("card_back.jpg", "card_back.JPG"):  # try both, web is case-sensitive
                try:
                    p = os.path.join("assets", "Cards", name)
                    base = pygame.image.load(p).convert_alpha()
                    break
                except Exception as e:
                    print(f"[ASSET] Could not load {name}: {e}")
            if base is None:
                # visible placeholder so the game keeps running
                base = pygame.Surface((tw, th), pygame.SRCALPHA)
                base.fill((180, 180, 180, 255))
            self._tile_back_img_cache[key] = pygame.transform.smoothscale(base, (tw, th))
        back = self._tile_back_img_cache[key]
        back_left  = pygame.transform.rotate(back, 90)
        back_right = pygame.transform.rotate(back, 270)

        # --- text surfaces ---
        font_lbl = pygame.font.SysFont(None, 24)
        font_scr = pygame.font.SysFont(None, 20)
        name_surf = font_lbl.render(f"Player {player_index + 1}", True, (240, 240, 240))
        score_surf = None
        if show_score:
            score_val = getattr(self.players[player_index], "score", 0)
            score_surf = font_scr.render(f"Score: {score_val}", True, (255, 215, 0))

        num = len(self.players[player_index].hand)
        sw, sh = screen.get_width(), screen.get_height()

        # helpers
        def blit_h_center(x_center, y_base):
            if score_surf:
                total_w = name_surf.get_width() + 10 + score_surf.get_width()
                x = x_center - total_w // 2
                screen.blit(name_surf, (x, y_base))
                screen.blit(score_surf, (x + name_surf.get_width() + 10, y_base))
            else:
                x = x_center - name_surf.get_width() // 2
                screen.blit(name_surf, (x, y_base))

        def blit_v_stack(x_left, y_center, rotate_deg):
            ns = pygame.transform.rotate(name_surf, rotate_deg)
            if score_surf:
                ss = pygame.transform.rotate(score_surf, rotate_deg)
                total_h = ss.get_height() + text_pad + ns.get_height()
                top = y_center - total_h // 2
                screen.blit(ss, (x_left, top))
                screen.blit(ns, (x_left, top + ss.get_height() + text_pad))
                return max(ns.get_width(), ss.get_width())
            else:
                top = y_center - ns.get_height() // 2
                screen.blit(ns, (x_left, top))
                return ns.get_width()

        # --- positions by side ---
        if player_index == 0:
            # bottom (human)
            y = play_area_rect.bottom + gap_from_area
            total_w = max(0, num * tw + max(0, num - 1) * spacing)
            start_x = play_area_rect.centerx - total_w // 2
            for i in range(num):
                screen.blit(back, (start_x + i * (tw + spacing), y))
            blit_h_center(play_area_rect.centerx, y + th + 6)

        elif player_index == 2:
            # top
            y = play_area_rect.top - th - gap_from_area
            total_w = max(0, num * tw + max(0, num - 1) * spacing)
            start_x = play_area_rect.centerx - total_w // 2
            blit_h_center(play_area_rect.centerx, y - name_surf.get_height() - 6)
            for i in range(num):
                screen.blit(back, (start_x + i * (tw + spacing), y))

        elif player_index == 1:
            # left (vertical)
            w, h = back_left.get_width(), back_left.get_height()
            total_h = max(0, num * h + max(0, num - 1) * spacing)
            start_y = play_area_rect.centery - total_h // 2

            # Tiles stack to the left of play area
            tiles_x = play_area_rect.left - gap_from_area - w
            for i in range(num):
                screen.blit(back_left, (tiles_x, start_y + i * (h + spacing)))

            # Rotated label widths (to right-align against the tiles)
            r_name = pygame.transform.rotate(name_surf, 90)
            if score_surf:
                r_score = pygame.transform.rotate(score_surf, 90)
                max_text_w = max(r_name.get_width(), r_score.get_width())
            else:
                max_text_w = r_name.get_width()

            # Put text between the screen edge and tiles; clamp to screen (≥8px)
            text_x = max(8, tiles_x - gap_text_to_tiles - max_text_w)
            blit_v_stack(text_x, play_area_rect.centery, 90)

        else:
            # right (vertical)
            w, h = back_right.get_width(), back_right.get_height()
            total_h = max(0, num * h + max(0, num - 1) * spacing)
            start_y = play_area_rect.centery - total_h // 2

            tiles_x = play_area_rect.right + gap_from_area
            for i in range(num):
                screen.blit(back_right, (tiles_x, start_y + i * (h + spacing)))

            # Rotated label widths to clamp into the right margin
            r_name = pygame.transform.rotate(name_surf, 270)
            if score_surf:
                r_score = pygame.transform.rotate(score_surf, 270)
                max_text_w = max(r_name.get_width(), r_score.get_width())
            else:
                max_text_w = r_name.get_width()

            # Place text to the right of tiles; clamp so it fits on-screen (≤ sw-8)
            text_x = min(sw - max_text_w - 8, tiles_x + w + gap_text_to_tiles)
            blit_v_stack(text_x, play_area_rect.centery, 270)
            
    def _blit_player_caption(self, surface, x, y, player_index, *, rotate=None):
        """Draws 'Player N' and (optionally) 'Score: S' depending on game mode."""
        import pygame
        font = pygame.font.SysFont(None, 24)
        font_small = pygame.font.SysFont(None, 20)

        name_surf = font.render(f"Player {player_index + 1}", True, (240, 240, 240))

        if self.scoring_enabled:
            score = getattr(self.players[player_index], "score", 0)
            score_surf = font_small.render(f"Score: {score}", True, (255, 215, 0))
        else:
            score_surf = None

        if rotate in (90, 270):
            name_surf = pygame.transform.rotate(name_surf, rotate)
            if score_surf:
                score_surf = pygame.transform.rotate(score_surf, rotate)

        # Stack vertically for rotated labels, side-by-side for horizontal
        if rotate in (90, 270):
            h = name_surf.get_height() + (score_surf.get_height() + 4 if score_surf else 0)
            top = y - h // 2
            if score_surf:
                surface.blit(score_surf, (x, top))
                surface.blit(name_surf, (x, top + score_surf.get_height() + 4))
            else:
                surface.blit(name_surf, (x, y - name_surf.get_height() // 2))
        else:
            if score_surf:
                total_w = name_surf.get_width() + 10 + score_surf.get_width()
                left = x - total_w // 2
                surface.blit(name_surf, (left, y))
                surface.blit(score_surf, (left + name_surf.get_width() + 10, y))
            else:
                surface.blit(name_surf, (x - name_surf.get_width() // 2, y))

    def _show_hand_result_overlay(self, winner, points_awarded, *, blocked=False):
        self.overlay_title = "Hand Result"
        if blocked:
            line1 = f"Player {winner.index + 1} wins blocked hand (lowest pips)."
            next_line = "Player holding 6|6 plays first in the next hand"
        else:
            line1 = f"Player {winner.index + 1} played their last tile."
            next_line = f"Player {winner.index + 1} plays first in the next hand"

        lines = [line1]
        if self.scoring_enabled:
            lines.append(f"Player {winner.index + 1} receives {points_awarded} points from the other players' hands.")
            scoreboard = "   ".join([f"Player {p.index + 1}: {p.score} points" for p in self.players])
            lines.append(scoreboard)
        lines.append(next_line)

        self.overlay_lines = lines
        self.phase = "hand_summary"
        self.show_all_hands = True



