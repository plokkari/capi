import pygame
import sys
import random
import time
import math

# =========================
#  SETUP
# =========================
pygame.init()
WIDTH, HEIGHT = 400, 600
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Flappy Capy 🐹")

CLOCK = pygame.time.Clock()
FONT = pygame.font.SysFont("Arial", 32)

# --- Game variables ---
gravity = 0.5
capy_movement = 0
game_state = "start"   # "start" | "play" | "gameover"
score = 0
high_score = 0
gameover_time = 0      # <-- NEW: track when game over started

# =========================
#  ASSETS
# =========================
# Background
background_img = pygame.image.load("capy back.png").convert()
background_img = pygame.transform.scale(background_img, (WIDTH, HEIGHT))

# Capybara sprite (visual) and hitbox (old 40x30 size)
capy_img = pygame.image.load("flappy capy.png").convert_alpha()
capy_img = pygame.transform.scale(capy_img, (60, 45))     # visual size
capy_rect = pygame.Rect(0, 0, 40, 30)                     # hitbox
capy_rect.center = (100, HEIGHT // 2)

# =========================
#  SINGLE PILLAR WITH GAP
# =========================
OBSTACLE_WIDTH = 60
SCROLL_SPEED   = 150

obstacles = []

def make_pillar_surface(gap_y, gap_size):
    surf = pygame.Surface((OBSTACLE_WIDTH, HEIGHT), pygame.SRCALPHA)
    coin_face = (245, 195, 50)
    coin_edge = (180, 115, 30)
    gap_top = max(0, gap_y - gap_size // 2)
    gap_bot = min(HEIGHT, gap_y + gap_size // 2)
    top_rect    = pygame.Rect(0, 0, OBSTACLE_WIDTH, max(0, gap_top))
    bottom_rect = pygame.Rect(0, gap_bot, OBSTACLE_WIDTH, max(0, HEIGHT - gap_bot))

    def draw_section(rect):
        if rect.height <= 0: return
        pygame.draw.rect(surf, coin_face, rect)
        inset = rect.inflate(-2, -2)
        if inset.width > 0 and inset.height > 0:
            pygame.draw.rect(surf, coin_edge, inset, width=2)
        band_h = 22
        y = rect.top + 10
        while y < rect.bottom - 10:
            band_top = max(rect.top + 2, y)
            band_bottom = min(rect.bottom - 2, y + 6)
            if band_bottom > band_top:
                pygame.draw.rect(surf, coin_edge,
                                 (rect.left + 4, band_top, rect.width - 8, band_bottom - band_top))
            y += band_h

    draw_section(top_rect)
    draw_section(bottom_rect)
    gap_rect = pygame.Rect(0, gap_top, OBSTACLE_WIDTH, max(0, gap_bot - gap_top))
    if gap_rect.height > 0:
        surf.fill((0, 0, 0, 0), gap_rect)
    return surf

def spawn_obstacle():
    gap_size = random.randint(150, 180)
    margin   = 100
    gap_y    = random.randint(margin, HEIGHT - margin)
    obstacles.append({
        "x": WIDTH + 80,
        "gap_y": gap_y,
        "gap_size": gap_size,
        "surf": make_pillar_surface(gap_y, gap_size),
        "scored": False,
    })

def update_obstacles(dt):
    alive = []
    for ob in obstacles:
        ob["x"] -= SCROLL_SPEED * dt
        if ob["x"] + OBSTACLE_WIDTH > -50:
            alive.append(ob)
    return alive

def draw_obstacles():
    for ob in obstacles:
        SCREEN.blit(ob["surf"], (int(ob["x"]), 0))

def obstacle_hitboxes(ob):
    x = int(ob["x"])
    gap_y = ob["gap_y"]
    gap_size = ob["gap_size"]
    top_rect    = pygame.Rect(x, 0, OBSTACLE_WIDTH, gap_y - gap_size // 2)
    bottom_rect = pygame.Rect(x, gap_y + gap_size // 2, OBSTACLE_WIDTH, HEIGHT - (gap_y + gap_size // 2))
    return top_rect, bottom_rect

def check_collision_single_column():
    for ob in obstacles:
        r1, r2 = obstacle_hitboxes(ob)
        if capy_rect.colliderect(r1) or capy_rect.colliderect(r2):
            return False
    if capy_rect.top <= -50 or capy_rect.bottom >= HEIGHT:
        return False
    return True

SPAWNPIPE = pygame.USEREVENT

# ---- TINY EASING CHANGE: spawn a bit less frequently (side-to-side spacing) ----
SPAWN_INTERVAL_MS = 1300  # was 1200 (≈ +8% more horizontal spacing)
pygame.time.set_timer(SPAWNPIPE, SPAWN_INTERVAL_MS)

# =========================
#  UI HELPERS
# =========================
def draw_text_center(text, size, y, color=(255,255,255)):
    f = pygame.font.SysFont("Arial", size, bold=True)
    s = f.render(text, True, color)
    SCREEN.blit(s, (WIDTH // 2 - s.get_width() // 2, y))

def score_display(mode):
    if mode == "main":
        s = FONT.render(f"Score: {int(score)}", True, (255, 255, 255))
        SCREEN.blit(s, (10, 10))
    elif mode == "game_over":
        s  = FONT.render(f"Score: {int(score)}", True, (255, 255, 255))
        hs = FONT.render(f"High Score: {int(high_score)}", True, (255, 255, 255))
        SCREEN.blit(s,  (WIDTH // 2 - s.get_width() // 2,  HEIGHT // 2 - 40))
        SCREEN.blit(hs, (WIDTH // 2 - hs.get_width() // 2, HEIGHT // 2))

def reset_game():
    global capy_movement, score, obstacles
    capy_rect.center = (100, HEIGHT // 2)
    capy_movement = 0
    obstacles = []
    score = 0

# =========================
#  MAIN LOOP
# =========================
last_time = time.perf_counter()

while True:
    now = time.perf_counter()
    dt = now - last_time
    last_time = now
    game_active = (game_state == "play")

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

            if game_state == "start":
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    reset_game()
                    game_state = "play"

            elif game_state == "play":
                if event.key == pygame.K_SPACE:
                    capy_movement = -10

            elif game_state == "gameover":
                if time.time() - gameover_time > 2:   # <-- cooldown check
                    if event.key == pygame.K_r:
                        reset_game()
                        game_state = "play"

        if event.type == pygame.MOUSEBUTTONDOWN:
            if game_state == "start":
                reset_game()
                game_state = "play"
            elif game_state == "play":
                capy_movement = -10
            elif game_state == "gameover":
                if time.time() - gameover_time > 2:   # <-- cooldown check
                    reset_game()
                    game_state = "play"

        if event.type == SPAWNPIPE and game_active:
            spawn_obstacle()

    # Background
    SCREEN.blit(background_img, (0, 0))

    if game_state == "start":
        capy_rect.centery = int(HEIGHT * 0.55 + 8 * math.sin(pygame.time.get_ticks() * 0.005))
        SCREEN.blit(capy_img, capy_img.get_rect(center=capy_rect.center))
        draw_text_center("Flappy Capy 🐹", 40, HEIGHT//4)
        draw_text_center("Press SPACE or TAP to Start", 22, HEIGHT//2)
        draw_text_center("SPACE to flap • ESC to quit", 18, int(HEIGHT*0.72))

    elif game_active:
        capy_movement += gravity
        capy_rect.centery += capy_movement
        capy_angle = -capy_movement * 3
        capy_rotated = pygame.transform.rotate(capy_img, capy_angle)
        SCREEN.blit(capy_rotated, capy_rotated.get_rect(center=capy_rect.center))
        obstacles[:] = update_obstacles(dt)
        draw_obstacles()
        if not check_collision_single_column():
            game_state = "gameover"
            gameover_time = time.time()   # <-- mark time of game over
        for ob in obstacles:
            if (not ob["scored"]) and (ob["x"] + OBSTACLE_WIDTH) < capy_rect.left:
                score += 1
                ob["scored"] = True
        score_display("main")

    else:  # gameover
        draw_obstacles()
        SCREEN.blit(capy_img, capy_img.get_rect(center=capy_rect.center))
        if score > high_score:
            high_score = score
        draw_text_center("Game Over!", 42, HEIGHT//4, (255,80,80))
        score_display("game_over")
        if time.time() - gameover_time > 2:
            draw_text_center("Press R / Tap to Try Again", 22, int(HEIGHT*0.68))
        else:
            draw_text_center("...", 22, int(HEIGHT*0.68), (200,200,200))
        draw_text_center("ESC to quit", 18, int(HEIGHT*0.78))

    pygame.display.update()
    CLOCK.tick(60)
