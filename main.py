import os
import pygame
from game import Game

# ---------------- Window / bootstrap ----------------
def initialize_maximized_game():
    os.environ["SDL_VIDEO_CENTERED"] = "1"
    pygame.init()
    info = pygame.display.Info()
    screen_w, screen_h = info.current_w, info.current_h
    print(f"[GAME] Detected screen resolution: {screen_w}x{screen_h}")

    win_w = min(screen_w - 80, 1800)
    win_h = min(screen_h - 80, 1200)
    win_w = max(win_w, 1200)
    win_h = max(win_h, 800)

    print(f"[GAME] Using window size: {win_w}x{win_h}")
    screen = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)
    pygame.display.set_caption("Camino-6 - Maximized Domino Game")
    return screen

# ---------------- Menu helpers ----------------
def show_player_select(screen):
    """Pick number of players (2–4). Returns int or None if window closed."""
    font = pygame.font.SysFont(None, 48)
    big  = pygame.font.SysFont(None, 60)

    opts = [("2 Players", 2), ("3 Players", 3), ("4 Players", 4)]
    buttons = []
    sw, sh = screen.get_width(), screen.get_height()

    for i, (label, val) in enumerate(opts):
        surf = font.render(label, True, (255, 255, 255))
        rect = surf.get_rect(center=(sw // 2, sh // 2 - 60 + i * 80))
        buttons.append((surf, rect, val))

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return None
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                return None
            if ev.type == pygame.MOUSEBUTTONDOWN:
                for surf, rect, val in buttons:
                    if rect.collidepoint(ev.pos):
                        return val

        screen.fill((0, 100, 150))
        title = big.render("Select Number of Players", True, (255, 255, 0))
        screen.blit(title, title.get_rect(center=(sw // 2, sh // 2 - 140)))

        for surf, rect, _ in buttons:
            pygame.draw.rect(screen, (0, 0, 0), rect.inflate(24, 14))
            screen.blit(surf, rect)

        pygame.display.flip()

def ask_human_players(screen, total_players):
    """Pick how many humans (0..total_players). Returns int or None if closed."""
    font = pygame.font.SysFont(None, 48)
    small = pygame.font.SysFont(None, 32)
    sw, sh = screen.get_width(), screen.get_height()

    btn_w, btn_h, gap = 60, 50, 18
    total_w = total_players * (btn_w + gap) + btn_w
    start_x = (sw - total_w) // 2
    y = sh // 2 + 30

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return None
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                return None
            if ev.type == pygame.MOUSEBUTTONDOWN:
                for i in range(total_players + 1):
                    r = pygame.Rect(start_x + i * (btn_w + gap), y, btn_w, btn_h)
                    if r.collidepoint(ev.pos):
                        return i

        screen.fill((50, 50, 120))
        title = font.render(f"How many human players? (0–{total_players})", True, (255, 255, 255))
        hint  = small.render("Remaining seats will be AI", True, (210, 210, 210))
        screen.blit(title, title.get_rect(center=(sw // 2, sh // 2 - 60)))
        screen.blit(hint,  hint.get_rect(center=(sw // 2, sh // 2 - 20)))

        for i in range(total_players + 1):
            r = pygame.Rect(start_x + i * (btn_w + gap), y, btn_w, btn_h)
            pygame.draw.rect(screen, (230, 230, 230), r, border_radius=8)
            num = small.render(str(i), True, (0, 0, 0))
            screen.blit(num, num.get_rect(center=r.center))

        pygame.display.flip()

def ask_game_mode(screen):
    """Choose between Classic scoring and Race (first-out). Returns 'scoring' or 'race'."""
    font = pygame.font.SysFont(None, 52)
    small = pygame.font.SysFont(None, 28)
    sw, sh = screen.get_width(), screen.get_height()

    btn_scoring = pygame.Rect(0, 0, 360, 80)
    btn_race    = pygame.Rect(0, 0, 360, 80)
    btn_scoring.center = (sw // 2, sh // 2 - 40)
    btn_race.center    = (sw // 2, sh // 2 + 60)

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return None
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                return None
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if btn_scoring.collidepoint(ev.pos):
                    return "scoring"
                if btn_race.collidepoint(ev.pos):
                    return "race"

        screen.fill((8, 60, 40))
        title = font.render("Choose Game Mode", True, (255, 255, 255))
        screen.blit(title, title.get_rect(center=(sw // 2, sh // 2 - 130)))

        pygame.draw.rect(screen, (30, 120, 60), btn_scoring, border_radius=14)
        pygame.draw.rect(screen, (60, 90, 150), btn_race,    border_radius=14)

        t1 = small.render("Classic Scoring (to 150, score by 5s)", True, (255, 255, 255))
        t2 = small.render("Race Mode (no points) — first out wins", True, (255, 255, 255))
        screen.blit(t1, t1.get_rect(center=btn_scoring.center))
        screen.blit(t2, t2.get_rect(center=btn_race.center))

        pygame.display.flip()

# ---------------- Main loop ----------------
def main():
    screen = initialize_maximized_game()

    while True:
        num_players = show_player_select(screen)
        if num_players is None:
            break

        num_humans = ask_human_players(screen, num_players)
        if num_humans is None:
            break

        game_mode = ask_game_mode(screen)
        if game_mode is None:
            break

        print(f"[MAIN] Starting game with {num_players} players ({num_humans} human, {num_players - num_humans} AI)")
        print(f"[MAIN] Window size: {screen.get_width()}x{screen.get_height()}")

        # NOTE: game.py should accept game_mode (defaulting to 'scoring' if omitted)
        game = Game(screen, num_players, num_humans, game_mode=game_mode)
        result = game.run()

        # Game.run() should RETURN a status (do not quit pygame inside run())
        if result == "RETURN_TO_MENU":
            continue  # loop back to the menu
        elif result == "EXIT":
            break      # user hit Exit button
        else:
            # default: return to menu after any completed game or window close
            continue

    pygame.quit()

if __name__ == "__main__":
    main()
