# main.py (pygbag-friendly, fixed)
import asyncio
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

# ---------------- Helpers (async: yield each frame) ----------------
async def show_starting(screen, text):
    font = pygame.font.SysFont(None, 40)
    for _ in range(30):  # ~0.5s at 60fps
        screen.fill((10, 30, 10))
        t = font.render(text, True, (255, 255, 255))
        screen.blit(t, t.get_rect(center=(screen.get_width()//2, screen.get_height()//2)))
        pygame.display.flip()
        await asyncio.sleep(0)

async def show_player_select(screen):
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
        await asyncio.sleep(0)  # yield

async def ask_human_players(screen, total_players):
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
        await asyncio.sleep(0)  # yield

async def ask_game_mode(screen):
    font  = pygame.font.SysFont(None, 52)
    small = pygame.font.SysFont(None, 28)
    sw, sh = screen.get_width(), screen.get_height()

    btn_scoring = pygame.Rect(0, 0, 360, 80)
    btn_race    = pygame.Rect(0, 0, 360, 80)
    btn_scoring.center = (sw // 2, sh // 2 - 40)
    btn_race.center    = (sw // 2, sh // 2 + 60)

    while True:
        mouse = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return None
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_q):
                return None
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_1):
                print("[UI] Game mode selected: scoring (keyboard)")
                return "scoring"
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_2,):
                print("[UI] Game mode selected: race (keyboard)")
                return "race"
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                print(f"[UI] click @ {ev.pos}")
                if btn_scoring.collidepoint(ev.pos):
                    print("[UI] Game mode selected: scoring (mouse)")
                    return "scoring"
                if btn_race.collidepoint(ev.pos):
                    print("[UI] Game mode selected: race (mouse)")
                    return "race"

        screen.fill((8, 60, 40))
        title = font.render("Choose Game Mode", True, (255, 255, 255))
        screen.blit(title, title.get_rect(center=(sw // 2, sh // 2 - 130)))

        # hover effect
        def draw_btn(rect, base_color, label):
            hovered = rect.collidepoint(mouse)
            col = tuple(min(255, c + (25 if hovered else 0)) for c in base_color)
            pygame.draw.rect(screen, col, rect, border_radius=14)
            txt = small.render(label, True, (255, 255, 255))
            screen.blit(txt, txt.get_rect(center=rect.center))

        draw_btn(btn_scoring, (30,120,60), "Classic Scoring (to 150, score by 5s)")
        draw_btn(btn_race,    (60, 90,150), "Race Mode (no points) — first out wins")

        pygame.display.flip()
        await asyncio.sleep(0)  # yield

# ---------------- Main loop (async) ----------------
async def main_async():
    screen = initialize_maximized_game()

    while True:
        num_players = await show_player_select(screen)
        if num_players is None:
            break

        num_humans = await ask_human_players(screen, num_players)
        if num_humans is None:
            break

        game_mode = await ask_game_mode(screen)
        if game_mode is None:
            break

        await show_starting(screen, f"Starting {game_mode} game...")

        print(f"[MAIN] Starting game with {num_players} players "
              f"({num_humans} human, {num_players - num_humans} AI)")
        print(f"[MAIN] Window size: {screen.get_width()}x{screen.get_height()}")

        # Prefer async run if present
        game = Game(screen, num_players, num_humans, game_mode=game_mode)
        if hasattr(game, "run_async"):
            result = await game.run_async()
        else:
            result = game.run()

        if result == "RETURN_TO_MENU":
            continue
        elif result == "EXIT":
            break
        else:
            continue

    pygame.quit()

def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        pygame.quit()

if __name__ == "__main__":
    main()
