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
OBSTACLE_WIDTH = 60      # matches previous pipe width
SCROLL_SPEED   = 150     # px/second (uses dt for smooth movement)

# Each obstacle is a dict:
# {"x": float, "gap_y": int, "gap_size": int, "surf": Surface, "scored": bool}
obstacles = []

def make_pillar_surface(gap_y, gap_size):
    """
    Build a pillar surface that fills the entire screen height,
    with a fully transparent gap opening in the middle.
    Uses clipping so no pixels bleed into the gap.
    """
    surf = pygame.Surface((OBSTACLE_WIDTH, HEIGHT), pygame.SRCALPHA)

    # Colors (retro pixel vibe)
    coin_face = (245, 195, 50)
    coin_edge = (180, 115, 30)

    # Compute top/bottom solid sections
    gap_top = max(0, gap_y - gap_size // 2)
    gap_bot = min(HEIGHT, gap_y + gap_size // 2)

    top_rect    = pygame.Rect(0, 0, OBSTACLE_WIDTH, max(0, gap_top))
    bottom_rect = pygame.Rect(0, gap_bot, OBSTACLE_WIDTH, max(0, HEIGHT - gap_bot))

    def draw_section(rect):
        if rect.height <= 0:
            return
        # base fill + inset outline to avoid touching gap edge
        pygame.draw.rect(surf, coin_face, rect)
        inset = rect.inflate(-2, -2)
        if inset.width > 0 and inset.height > 0:
            pygame.draw.rect(surf, coin_edge, inset, width=2)

        # horizontal “coin bands” (clamped so they don't reach the gap edge)
        band_h = 22
        y = rect.top + 10
        while y < rect.bottom - 10:
            band_top = max(rect.top + 2, y)
            band_bottom = min(rect.bottom - 2, y + 6)
            if band_bottom > band_top:
                pygame.draw.rect(surf, coin_edge, (rect.left + 4, band_top, rect.width - 8, band_bottom - band_top))
            y += band_h

    draw_section(top_rect)
    draw_section(bottom_rect)

    # Punch out the gap so it's fully transparent
    gap_rect = pygame.Rect(0, gap_top, OBSTACLE_WIDTH, max(0, gap_bot - gap_top))
    if gap_rect.height > 0:
        surf.fill((0, 0, 0, 0), gap_rect)

    return surf

def spawn_obstacle():
    """Create one pillar with a random gap position/size."""
    gap_size = random.randint(150, 180)                 # difficulty range
    margin   = 100                                      # keep gap away from extreme edges
    gap_y    = random.randint(margin, HEIGHT - margin)
    obstacles.append({
        "x": WIDTH + 80,                                # start off right edge
        "gap_y": gap_y,
        "gap_size": gap_size,
        "surf": make_pillar_surface(gap_y, gap_size),
        "scored": False,                                # <- scoring flag
    })

def update_obstacles(dt):
    """Move obstacles left and cull off-screen ones."""
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
    """Return top/bottom rects for collision (aligned to current x)."""
    x = int(ob["x"])
    gap_y = ob["gap_y"]
    gap_size = ob["gap_size"]
    top_rect    = pygame.Rect(x, 0, OBSTACLE_WIDTH, gap_y - gap_size // 2)
    bottom_rect = pygame.Rect(x, gap_y + gap_size // 2, OBSTACLE_WIDTH, HEIGHT - (gap_y + gap_size // 2))
    return top_rect, bottom_rect

def check_collision_single_column():
    # obstacles
    for ob in obstacles:
        r1, r2 = obstacle_hitboxes(ob)
        if capy_rect.colliderect(r1) or capy_rect.colliderect(r2):
            return False
    # bounds
    if capy_rect.top <= -50 or capy_rect.bottom >= HEIGHT:
        return False
    return True

# Spawn timer
SPAWNPIPE = pygame.USEREVENT
pygame.time.set_timer(SPAWNPIPE, 1200)  # every 1.2s

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

    # Reflect state into a convenience bool for existing code paths
    game_active = (game_state == "play")

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:
            # Global shortcuts
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

            if game_state == "start":
                if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                    reset_game()
                    game_state = "play"

            elif game_state == "play":
                if event.key == pygame.K_SPACE:
                    capy_movement = -10  # flap

            elif game_state == "gameover":
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
                reset_game()
                game_state = "play"

        if event.type == SPAWNPIPE and game_active:
            spawn_obstacle()

    # Background
    SCREEN.blit(background_img, (0, 0))

    if game_state == "start":
        # Idle capy float
        capy_rect.centery = int(HEIGHT * 0.55 + 8 * math.sin(pygame.time.get_ticks() * 0.005))
        SCREEN.blit(capy_img, capy_img.get_rect(center=capy_rect.center))
        draw_text_center("Flappy Capy 🐹", 40, HEIGHT//4)
        draw_text_center("Press SPACE or TAP to Start", 22, HEIGHT//2)
        draw_text_center("SPACE to flap • ESC to quit", 18, int(HEIGHT*0.72))

    elif game_active:
        # Capy physics
        capy_movement += gravity
        capy_rect.centery += capy_movement

        # Tilted capy draw (based on velocity)
        capy_angle = -capy_movement * 3
        capy_rotated = pygame.transform.rotate(capy_img, capy_angle)
        capy_rotated_rect = capy_rotated.get_rect(center=capy_rect.center)
        SCREEN.blit(capy_rotated, capy_rotated_rect)

        # Obstacles
        obstacles[:] = update_obstacles(dt)
        draw_obstacles()

        # Collisions
        if not check_collision_single_column():
            game_state = "gameover"

        # --- SCORE WHEN PASSING A PILLAR ---
        # When the pillar's right edge passes the capy's left edge and not counted yet -> +1
        for ob in obstacles:
            if (not ob["scored"]) and (ob["x"] + OBSTACLE_WIDTH) < capy_rect.left:
                score += 1
                ob["scored"] = True

        # HUD
        score_display("main")

    else:  # gameover
        # Keep last frame visible (draw obstacles + capy at rest)
        draw_obstacles()
        SCREEN.blit(capy_img, capy_img.get_rect(center=capy_rect.center))

        # Update high score
        if score > high_score:
            high_score = score

        # Overlay
        draw_text_center("Game Over!", 42, HEIGHT//4, (255,80,80))
        score_display("game_over")
        draw_text_center("Press R to Try Again", 22, int(HEIGHT*0.68))
        draw_text_center("ESC to quit", 18, int(HEIGHT*0.78))

    pygame.display.update()
    CLOCK.tick(60)
