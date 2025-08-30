import pygame
import sys
import random
import time
import math
import string

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
game_state = "start"   # "start" | "ready" | "play" | "challenge" | "gameover"
score = 0
high_score = 0
gameover_time = 0

# --- HARDEN: flap rate limit ---
MAX_FLAPS_PER_SEC = 12.0
MIN_FLAP_INTERVAL = 1.0 / MAX_FLAPS_PER_SEC
last_flap_time = 0.0

def try_flap():
    global capy_movement, last_flap_time
    t = time.perf_counter()
    if t - last_flap_time >= MIN_FLAP_INTERVAL:
        capy_movement = -10
        last_flap_time = t

# =========================
#  ASSETS
# =========================
background_img = pygame.image.load("capy back.png").convert()
background_img = pygame.transform.scale(background_img, (WIDTH, HEIGHT))

capy_img = pygame.image.load("flappy capy.png").convert_alpha()
capy_img = pygame.transform.scale(capy_img, (60, 45))     # visual size
capy_rect = pygame.Rect(0, 0, 40, 30)                     # hitbox
capy_rect.center = (100, HEIGHT // 2)

# =========================
#  PILLARS (distance-based spawner)
# =========================
OBSTACLE_WIDTH = 60
SCROLL_SPEED   = 150

SPAWN_OFFSET_X        = WIDTH + 60   # where new pillars appear (off-screen to the right)
OBSTACLE_SPACING_X    = 130          # base horizontal spacing between pillars
SPACING_JITTER        = 15           # +/- pixels random variation each spawn
SPAWN_EDGE_GUARD      = 40           # guard to avoid same-frame overlap at spawn edge

obstacles = []
spawning_enabled = False   # turned on only in "play"
next_spacing_x = OBSTACLE_SPACING_X  # will be randomized each spawn

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
    # guard: don't double-spawn exactly at the edge in the same frame
    if obstacles:
        last_x = obstacles[-1]["x"]
        if last_x > SPAWN_OFFSET_X - SPAWN_EDGE_GUARD:
            return
    gap_size = random.randint(150, 180)
    margin   = 100
    gap_y    = random.randint(margin, HEIGHT - margin)
    obstacles.append({
        "x": SPAWN_OFFSET_X,
        "gap_y": gap_y,
        "gap_size": gap_size,
        "surf": make_pillar_surface(gap_y, gap_size),
        "scored": False,
    })

def maybe_spawn_by_distance():
    # new pillar spawns only after the last one moved far enough left
    global next_spacing_x
    if not spawning_enabled:
        return
    if not obstacles:
        spawn_obstacle()
        next_spacing_x = OBSTACLE_SPACING_X + random.randint(-SPACING_JITTER, SPACING_JITTER)
        return
    last_x = obstacles[-1]["x"]
    if last_x <= WIDTH - next_spacing_x:
        spawn_obstacle()
        next_spacing_x = OBSTACLE_SPACING_X + random.randint(-SPACING_JITTER, SPACING_JITTER)

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

# =========================
#  HUMAN CHECK
# =========================
def next_challenge_increment():
    return random.randint(25, 45)

next_challenge_at = next_challenge_increment()
challenge = {
    "code": "",
    "typed": "",
    "deadline": 0.0,
    "active": False,
    "time_limit": 9.5,  # seconds to answer
}

def random_code(n=4):
    alphabet = [c for c in string.ascii_uppercase if c not in ("O", "I")]
    digits   = [d for d in "23456789"]
    pool = alphabet + digits
    return "".join(random.choice(pool) for _ in range(n))

def start_challenge():
    global game_state, challenge, spawning_enabled
    spawning_enabled = False  # pause spawns
    challenge["code"] = random_code(4)
    challenge["typed"] = ""
    challenge["deadline"] = time.perf_counter() + challenge["time_limit"]
    challenge["active"] = True
    game_state = "challenge"

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
    global capy_movement, score, obstacles, next_challenge_at, challenge, spawning_enabled, next_spacing_x
    capy_rect.center = (100, HEIGHT // 2)
    capy_movement = 0
    obstacles = []
    score = 0
    next_challenge_at = next_challenge_increment()
    challenge["active"] = False
    challenge["typed"] = ""
    challenge["code"] = ""
    challenge["deadline"] = 0.0
    spawning_enabled = False
    next_spacing_x = OBSTACLE_SPACING_X + random.randint(-SPACING_JITTER, SPACING_JITTER)

# Helper: enter play state (from start/ready)
def enter_play():
    global game_state, spawning_enabled, next_spacing_x
    game_state = "play"
    spawning_enabled = True
    next_spacing_x = OBSTACLE_SPACING_X + random.randint(-SPACING_JITTER, SPACING_JITTER)

def draw_challenge_overlay():
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    SCREEN.blit(overlay, (0, 0))
    draw_text_center("Quick Check!", 34, int(HEIGHT * 0.22), (255, 215, 120))
    draw_text_center("Type this code to continue", 20, int(HEIGHT * 0.32), (230, 230, 230))
    code = challenge["code"]; typed = challenge["typed"]
    box_w, box_h = 260, 80
    box_rect = pygame.Rect(WIDTH//2 - box_w//2, HEIGHT//2 - box_h//2, box_w, box_h)
    pygame.draw.rect(SCREEN, (30, 30, 30), box_rect, border_radius=10)
    pygame.draw.rect(SCREEN, (200, 180, 90), box_rect, width=3, border_radius=10)
    code_surf = FONT.render(code, True, (255, 255, 255))
    SCREEN.blit(code_surf, (WIDTH//2 - code_surf.get_width()//2, box_rect.y + 8))
    typed_font = pygame.font.SysFont("Arial", 26)
    typed_surf = typed_font.render(typed or " ", True, (180, 220, 255))
    SCREEN.blit(typed_surf, (WIDTH//2 - typed_surf.get_width()//2, box_rect.y + 46))
    remaining = max(0.0, challenge["deadline"] - time.perf_counter())
    timer_font = pygame.font.SysFont("Arial", 20)
    timer_surf = timer_font.render(f"{remaining:.1f}s", True, (255,200,200) if remaining < 3 else (200,255,200))
    SCREEN.blit(timer_surf, (WIDTH//2 - timer_surf.get_width()//2, int(HEIGHT * 0.72)))

# =========================
#  MAIN LOOP
# =========================
last_time = time.perf_counter()

while True:
    now = time.perf_counter()
    dt = now - last_time
    last_time = now

    # HARDEN: clamp dt to avoid slow-motion advantages
    DT_MIN, DT_MAX = 0.0, 0.030
    dt = max(DT_MIN, min(dt, DT_MAX))

    game_active = (game_state == "play")
    paused_for_focus = game_active and (not pygame.display.get_active())

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit()

            if game_state in ("start", "ready"):
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    enter_play()

            elif game_state == "play":
                if not paused_for_focus and event.key == pygame.K_SPACE:
                    try_flap()

            elif game_state == "challenge":
                if event.key == pygame.K_BACKSPACE:
                    challenge["typed"] = challenge["typed"][:-1]
                else:
                    ch = event.unicode.upper()
                    if ch and ch.isalnum() and ch not in ["O", "I"]:
                        challenge["typed"] = (challenge["typed"] + ch)[:4]

            elif game_state == "gameover":
                if time.time() - gameover_time > 2 and event.key == pygame.K_r:
                    reset_game(); game_state = "ready"

        if event.type == pygame.MOUSEBUTTONDOWN:
            if game_state in ("start", "ready"):
                enter_play()
            elif game_state == "play" and not paused_for_focus:
                try_flap()
            elif game_state == "gameover":
                if time.time() - gameover_time > 2:
                    reset_game(); game_state = "ready"

    # Background
    SCREEN.blit(background_img, (0, 0))

    if game_state == "start":
        capy_rect.centery = int(HEIGHT*0.55 + 8*math.sin(pygame.time.get_ticks()*0.005))
        SCREEN.blit(capy_img, capy_img.get_rect(center=capy_rect.center))
        draw_text_center("Flappy Capy", 40, HEIGHT//4)
        draw_text_center("Press SPACE or TAP to Start", 22, HEIGHT//2)

    elif game_state == "ready":
        capy_rect.centery = int(HEIGHT*0.55 + 8*math.sin(pygame.time.get_ticks()*0.005))
        SCREEN.blit(capy_img, capy_img.get_rect(center=capy_rect.center))
        draw_obstacles()
        draw_text_center("Get Ready!", 36, HEIGHT//4)
        draw_text_center("Press SPACE or TAP to continue", 22, HEIGHT//2)
        score_display("main")

    elif game_state == "play" and not paused_for_focus:
        # Physics
        capy_movement += gravity
        capy_rect.centery += capy_movement
        capy_angle = -capy_movement * 3
        capy_rotated = pygame.transform.rotate(capy_img, capy_angle)
        SCREEN.blit(capy_rotated, capy_rotated.get_rect(center=capy_rect.center))

        # Move + spawn-by-distance (no timers → no bunching)
        obstacles[:] = update_obstacles(dt)
        maybe_spawn_by_distance()
        draw_obstacles()

        # Collisions
        if not check_collision_single_column():
            game_state = "gameover"
            gameover_time = time.time()
            spawning_enabled = False

        # Scoring
        for ob in obstacles:
            if (not ob["scored"]) and (ob["x"] + OBSTACLE_WIDTH) < capy_rect.left:
                score += 1
                ob["scored"] = True

        # Human check schedule
        if score >= next_challenge_at:
            start_challenge()

        score_display("main")

    elif game_state == "play" and paused_for_focus:
        draw_obstacles()
        SCREEN.blit(capy_img, capy_img.get_rect(center=capy_rect.center))
        score_display("main")
        draw_text_center("Paused (click tab to return)", 20, int(HEIGHT*0.15), (200,200,200))

    elif game_state == "challenge":
        # Frozen world
        draw_obstacles()
        SCREEN.blit(capy_img, capy_img.get_rect(center=capy_rect.center))
        score_display("main")
        draw_challenge_overlay()

        if challenge["typed"] == challenge["code"]:
            # Passed: clear the course and go to READY. Fresh spawns begin when player continues.
            challenge["active"] = False
            game_state = "ready"
            challenge["typed"] = ""
            challenge["code"] = ""
            challenge["deadline"] = 0.0

            obstacles.clear()     # PLAN A: clear all pillars
            capy_movement = 0     # remove momentum so resume is fair
            next_spacing_x = OBSTACLE_SPACING_X + random.randint(-SPACING_JITTER, SPACING_JITTER)
            next_challenge_at = score + next_challenge_increment()
            spawning_enabled = False  # stays off until player presses to continue

        elif time.perf_counter() > challenge["deadline"]:
            game_state = "gameover"
            gameover_time = time.time()
            spawning_enabled = False

    else:  # gameover
        draw_obstacles()
        SCREEN.blit(capy_img, capy_img.get_rect(center=capy_rect.center))
        if score > high_score:
            high_score = score
        draw_text_center("Game Over!", 42, HEIGHT//4, (255,80,80))
        score_display("game_over")
        if time.time() - gameover_time > 1:
            draw_text_center("Press R / Tap to Try Again", 22, int(HEIGHT*0.68))

    pygame.display.update()
    CLOCK.tick(60)
