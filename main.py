import pygame
import sys
import random
import time
import math
import string
import os

# =========================
#  SETUP
# =========================
pygame.init()
WIDTH, HEIGHT = 400, 600
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Flappy Capy 🐹")

# =========================
#  AUDIO & MUTE SETUP
# =========================
import sys as _sys

SOUND_ENABLED = True
try:
    # more reliable on iOS/web
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.mixer.init()
except Exception as e:
    SOUND_ENABLED = False

MUSIC_VOLUME = 0.6
SFX_VOLUME   = 0.8
is_muted = False
MUSIC_STARTED = False  # start only after first user gesture
IS_WEB = (_sys.platform == "emscripten")

# On web: avoid pygame.mixer.music streaming; loop a Sound on a channel instead
MUSIC_CHANNEL = None
MUSIC_BG = None  # background loop as Sound on web; None on desktop

SFX_REWARD = None
SFX_GAMEOVER = None

def _apply_mute_state():
    if not SOUND_ENABLED:
        return
    music_vol = 0.0 if is_muted else MUSIC_VOLUME
    sfx_vol   = 0.0 if is_muted else SFX_VOLUME
    # desktop music stream
    if not IS_WEB:
        try: pygame.mixer.music.set_volume(music_vol)
        except Exception: pass
    # web music channel
    if IS_WEB and MUSIC_CHANNEL is not None:
        try: MUSIC_CHANNEL.set_volume(music_vol)
        except Exception: pass
    # sfx
    try:
        if SFX_REWARD:   SFX_REWARD.set_volume(sfx_vol)
        if SFX_GAMEOVER: SFX_GAMEOVER.set_volume(sfx_vol)
    except Exception:
        pass

def _first_existing_sound(basename, exts):
    """Return the first existing path for basename among given extensions."""
    for ext in exts:
        p = basename + ext
        if os.path.exists(p):
            return p
    return None

# Load sounds (do NOT autoplay the music yet)
if SOUND_ENABLED:
    # On web prefer .wav/.ogg (pygbag forbids mp3/m4a). Desktop can try mp3/m4a too.
    music_path  = _first_existing_sound("flappy_capy_smooth_loop",
                                        (".wav", ".ogg") if IS_WEB else (".ogg", ".wav", ".mp3", ".m4a"))
    reward_path = _first_existing_sound("reward_ding",
                                        (".wav", ".ogg") if IS_WEB else (".ogg", ".wav", ".mp3", ".m4a"))
    over_path   = _first_existing_sound("game_over_wah",
                                        (".wav", ".ogg") if IS_WEB else (".ogg", ".wav", ".mp3", ".m4a"))

    try:
        if IS_WEB:
            # Use Sound on a dedicated channel for background loop
            if music_path:
                MUSIC_BG = pygame.mixer.Sound(music_path)
        else:
            # Desktop: stream via mixer.music
            if music_path:
                pygame.mixer.music.load(music_path)
                pygame.mixer.music.set_volume(MUSIC_VOLUME)
    except Exception:
        pass

    try:
        if reward_path:
            SFX_REWARD = pygame.mixer.Sound(reward_path)
            SFX_REWARD.set_volume(SFX_VOLUME)
        if over_path:
            SFX_GAMEOVER = pygame.mixer.Sound(over_path)
            SFX_GAMEOVER.set_volume(SFX_VOLUME)
    except Exception:
        SFX_REWARD = SFX_REWARD or None
        SFX_GAMEOVER = SFX_GAMEOVER or None
else:
    MUSIC_BG = None
    SFX_REWARD = None
    SFX_GAMEOVER = None

def maybe_start_music():
    """Start looping music after a user gesture (required on iOS)."""
    global MUSIC_STARTED, MUSIC_CHANNEL
    if not SOUND_ENABLED or MUSIC_STARTED:
        return
    try:
        if IS_WEB:
            if MUSIC_BG is not None:
                # Reserve channel 0 for background music
                if MUSIC_CHANNEL is None:
                    pygame.mixer.set_num_channels(max(8, pygame.mixer.get_num_channels()))
                    MUSIC_CHANNEL = pygame.mixer.Channel(0)
                MUSIC_CHANNEL.play(MUSIC_BG, loops=-1)
                MUSIC_CHANNEL.set_volume(0.0 if is_muted else MUSIC_VOLUME)
        else:
            pygame.mixer.music.play(-1)
            _apply_mute_state()
        MUSIC_STARTED = True
    except Exception:
        pass

MUTE_BTN_SIZE = 36
mute_button_rect = pygame.Rect(WIDTH - MUTE_BTN_SIZE - 10, 10, MUTE_BTN_SIZE, MUTE_BTN_SIZE)

def draw_mute_button():
    pygame.draw.rect(SCREEN, (0,0,0), mute_button_rect, border_radius=8)
    pygame.draw.rect(SCREEN, (220,220,220), mute_button_rect, width=2, border_radius=8)
    pad = 8
    x, y, w, h = mute_button_rect
    inner = pygame.Rect(x+pad, y+pad, w-2*pad, h-2*pad)
    head = pygame.Rect(inner.x, inner.y, inner.w, int(inner.h*0.55))
    pygame.draw.ellipse(SCREEN, (255,255,255), head, width=2)
    stem_h = int(inner.h*0.3)
    stem_y = head.bottom - 2
    stem = pygame.Rect(inner.centerx-3, stem_y, 6, stem_h)
    pygame.draw.rect(SCREEN, (255,255,255), stem, width=2)
    base_w = int(inner.w*0.6)
    base_rect = pygame.Rect(inner.centerx - base_w//2, stem.bottom-1, base_w, 3)
    pygame.draw.rect(SCREEN, (255,255,255), base_rect)
    if is_muted:
        pygame.draw.line(SCREEN, (230,60,60), (x+6, y+6), (x+w-6, y+h-6), 4)

def _point_in(rect, pos): return rect.collidepoint(pos)

CLOCK = pygame.time.Clock()
FONT = pygame.font.SysFont("Arial", 32)

# --- Game variables ---
gravity = 0.5
capy_movement = 0
game_state = "start"
score = 0
high_score = 0
gameover_time = 0
played_gameover_sound = False

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
capy_img = pygame.transform.scale(capy_img, (60, 45))
capy_rect = pygame.Rect(0, 0, 40, 30)
capy_rect.center = (100, HEIGHT // 2)

# =========================
#  PILLARS
# =========================
OBSTACLE_WIDTH = 60
SCROLL_SPEED   = 150
SPAWN_OFFSET_X = WIDTH + 60
OBSTACLE_SPACING_X = 130
SPACING_JITTER = 15
SPAWN_EDGE_GUARD = 40

obstacles = []
spawning_enabled = False
next_spacing_x = OBSTACLE_SPACING_X

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
                pygame.draw.rect(surf, coin_edge, (rect.left+4, band_top, rect.width-8, band_bottom-band_top))
            y += band_h
    draw_section(top_rect); draw_section(bottom_rect)
    gap_rect = pygame.Rect(0, gap_top, OBSTACLE_WIDTH, max(0, gap_bot - gap_top))
    if gap_rect.height > 0: surf.fill((0,0,0,0), gap_rect)
    return surf

def spawn_obstacle():
    if obstacles:
        last_x = obstacles[-1]["x"]
        if last_x > SPAWN_OFFSET_X - SPAWN_EDGE_GUARD: return
    gap_size = random.randint(150, 180)
    margin = 100
    gap_y = random.randint(margin, HEIGHT - margin)
    obstacles.append({"x": SPAWN_OFFSET_X,"gap_y": gap_y,"gap_size": gap_size,
                      "surf": make_pillar_surface(gap_y, gap_size),"scored": False})

def maybe_spawn_by_distance():
    global next_spacing_x
    if not spawning_enabled: return
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
        if ob["x"] + OBSTACLE_WIDTH > -50: alive.append(ob)
    return alive

def draw_obstacles():
    for ob in obstacles: SCREEN.blit(ob["surf"], (int(ob["x"]), 0))

def obstacle_hitboxes(ob):
    x = int(ob["x"]); gap_y = ob["gap_y"]; gap_size = ob["gap_size"]
    top_rect = pygame.Rect(x,0,OBSTACLE_WIDTH,gap_y-gap_size//2)
    bottom_rect = pygame.Rect(x,gap_y+gap_size//2,OBSTACLE_WIDTH,HEIGHT-(gap_y+gap_size//2))
    return top_rect, bottom_rect

def check_collision_single_column():
    for ob in obstacles:
        r1, r2 = obstacle_hitboxes(ob)
        if capy_rect.colliderect(r1) or capy_rect.colliderect(r2): return False
    if capy_rect.top <= -50 or capy_rect.bottom >= HEIGHT: return False
    return True

# =========================
#  HUMAN CHECK
# =========================
def next_challenge_increment(): return random.randint(5, 5)
next_challenge_at = next_challenge_increment()
challenge = {"code":"","typed":"","deadline":0.0,"active":False,"time_limit":9.5}

# Input rect for mobile keyboards (matches the overlay box)
CHALLENGE_INPUT_RECT = pygame.Rect(WIDTH//2 - 130, HEIGHT//2 - 40, 260, 80)

def random_code(n=4):
    alphabet = [c for c in string.ascii_uppercase if c not in ("O","I")]
    digits   = [d for d in "23456789"]
    pool = alphabet + digits
    return "".join(random.choice(pool) for _ in range(n))

def start_challenge():
    global game_state, challenge, spawning_enabled
    spawning_enabled = False
    challenge["code"] = random_code(4)
    challenge["typed"] = ""
    challenge["deadline"] = time.perf_counter() + challenge["time_limit"]
    challenge["active"] = True
    game_state = "challenge"
    # Mobile keyboards: start text input and anchor to the code box
    try:
        pygame.key.set_text_input_rect(CHALLENGE_INPUT_RECT)
        pygame.key.start_text_input()
    except Exception:
        pass

# =============== On-screen keypad for mobile (challenge) ===============
ALLOWED_CHARS = [d for d in "23456789"] + [c for c in string.ascii_uppercase if c not in ("O","I")]
KEYS_PER_ROW = 8
KEYPAD_KEYS = ALLOWED_CHARS[:]  # 32 keys (8x4)
KEYPAD_KEYS.append("←")         # Backspace key at the end

def get_keypad_layout():
    """Return list of (label, rect) for keypad buttons."""
    # Place keypad in lower 45% of the screen
    pad = 6
    rows = []
    total_rows = (len(KEYPAD_KEYS) + KEYS_PER_ROW - 1) // KEYS_PER_ROW
    # Ensure at least 3 rows visible nicely; clamp height
    avail_top = int(HEIGHT * 0.55)
    avail_bottom = HEIGHT - 10
    avail_h = max(120, avail_bottom - avail_top)
    key_h = (avail_h - (total_rows + 1) * pad) // total_rows
    key_w = (WIDTH - (KEYS_PER_ROW + 1) * pad) // KEYS_PER_ROW
    y = avail_top + pad
    idx = 0
    layout = []
    for r in range(total_rows):
        x = pad
        for c in range(KEYS_PER_ROW):
            if idx >= len(KEYPAD_KEYS):
                break
            rect = pygame.Rect(x, y, key_w, key_h)
            layout.append((KEYPAD_KEYS[idx], rect))
            x += key_w + pad
            idx += 1
        y += key_h + pad
    return layout

def draw_keypad():
    """Draw keypad; called only during challenge."""
    keys = get_keypad_layout()
    for label, rect in keys:
        pygame.draw.rect(SCREEN, (25, 25, 25), rect, border_radius=8)
        pygame.draw.rect(SCREEN, (210, 210, 210), rect, width=2, border_radius=8)
        txt = FONT.render(label, True, (240,240,240))
        SCREEN.blit(txt, (rect.centerx - txt.get_width()//2, rect.centery - txt.get_height()//2))

def handle_keypad_click(pos):
    """Process taps on keypad; returns True if it handled a key."""
    if game_state != "challenge":
        return False
    for label, rect in get_keypad_layout():
        if rect.collidepoint(pos):
            if label == "←":
                if challenge["typed"]:
                    challenge["typed"] = challenge["typed"][:-1]
            else:
                if len(challenge["typed"]) < 4 and label in ALLOWED_CHARS:
                    challenge["typed"] = challenge["typed"] + label
            return True
    return False

# =========================
#  UI HELPERS
# =========================
def draw_text_center(text, size, y, color=(255,255,255)):
    f = pygame.font.SysFont("Arial", size, bold=True)
    s = f.render(text, True, color)
    SCREEN.blit(s, (WIDTH//2 - s.get_width()//2, y))

def score_display(mode):
    if mode == "main":
        s = FONT.render(f"Score: {int(score)}", True, (255,255,255))
        SCREEN.blit(s, (10,10))
    elif mode == "game_over":
        s  = FONT.render(f"Score: {int(score)}", True, (255,255,255))
        hs = FONT.render(f"High Score: {int(high_score)}", True, (255,255,255))
        SCREEN.blit(s,  (WIDTH//2 - s.get_width()//2,  HEIGHT//2 - 40))
        SCREEN.blit(hs, (WIDTH//2 - hs.get_width()//2, HEIGHT//2))

def reset_game():
    global capy_movement, score, obstacles, next_challenge_at, challenge, spawning_enabled, next_spacing_x, played_gameover_sound
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
    played_gameover_sound = False
    _apply_mute_state()

def enter_play():
    global game_state, spawning_enabled, next_spacing_x
    game_state = "play"; spawning_enabled = True
    next_spacing_x = OBSTACLE_SPACING_X + random.randint(-SPACING_JITTER, SPACING_JITTER)

def draw_challenge_overlay():
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0,0,0,160)); SCREEN.blit(overlay, (0,0))
    draw_text_center("Quick Check!", 34, int(HEIGHT*0.22), (255,215,120))
    draw_text_center("Type this code to continue", 20, int(HEIGHT*0.32), (230,230,230))
    code = challenge["code"]; typed = challenge["typed"]
    box_w, box_h = 260, 80
    box_rect = pygame.Rect(WIDTH//2 - box_w//2, HEIGHT//2 - box_h//2, box_w, box_h)
    pygame.draw.rect(SCREEN, (30,30,30), box_rect, border_radius=10)
    pygame.draw.rect(SCREEN, (200,180,90), box_rect, width=3, border_radius=10)
    code_surf = FONT.render(code, True, (255,255,255))
    SCREEN.blit(code_surf, (WIDTH//2 - code_surf.get_width()//2, box_rect.y+8))
    typed_font = pygame.font.SysFont("Arial", 26)
    typed_surf = pygame.font.SysFont("Arial", 26).render(typed or " ", True, (180,220,255))
    SCREEN.blit(typed_surf, (WIDTH//2 - typed_surf.get_width()//2, box_rect.y+46))
    remaining = max(0.0, challenge["deadline"] - time.perf_counter())
    timer_font = pygame.font.SysFont("Arial", 20)
    timer_surf = timer_font.render(f"{remaining:.1f}s", True, (255,200,200) if remaining<3 else (200,255,200))
    SCREEN.blit(timer_surf, (WIDTH//2 - timer_surf.get_width()//2, int(HEIGHT*0.72)))
    # On-screen keypad (mobile-friendly)
    draw_keypad()

# =========================
#  MAIN LOOP
# =========================
last_time = time.perf_counter()

while True:
    now = time.perf_counter()
    dt = now - last_time
    last_time = now
    dt = max(0.0, min(dt, 0.030))
    game_active = (game_state == "play")
    paused_for_focus = game_active and (not pygame.display.get_active())

    for event in pygame.event.get():
        # --- MUTE BUTTON CLICK: consume the event so it doesn't trigger game actions ---
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if _point_in(mute_button_rect, event.pos):
                is_muted = not is_muted
                _apply_mute_state()
                maybe_start_music()  # if first tap is the mute, allow music later
                continue  # DO NOT propagate to gameplay click handling

        # Mobile/desktop: hotkey to toggle mute (disabled during challenge so typing 'M' doesn't mute)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_m and game_state != "challenge":
            is_muted = not is_muted
            _apply_mute_state()
            continue

        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit()

            if game_state in ("start","ready"):
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    maybe_start_music()
                    enter_play()

            elif game_state == "play":
                if not paused_for_focus and event.key == pygame.K_SPACE:
                    maybe_start_music()
                    try_flap()

            elif game_state == "challenge":
                # BACKSPACE still arrives as KEYDOWN on soft keyboards / desktop
                if event.key == pygame.K_BACKSPACE:
                    challenge["typed"] = challenge["typed"][:-1]

            elif game_state == "gameover":
                if time.time() - gameover_time > 1 and event.key == pygame.K_r:
                    reset_game(); game_state = "ready"

        # TEXTINPUT: soft keyboard characters for mobile / desktop IME
        if event.type == pygame.TEXTINPUT and game_state == "challenge":
            ch = event.text.upper()
            if ch and ch.isalnum() and ch not in ["O","I"]:
                if len(challenge["typed"]) < 4:
                    challenge["typed"] = (challenge["typed"] + ch)
            continue

        # Normal gameplay click handling (after consuming mute click above)
        if event.type == pygame.MOUSEBUTTONDOWN:
            # If user taps the challenge text box, re-focus text input on mobile
            if game_state == "challenge":
                # On-screen keypad tap?
                if handle_keypad_click(event.pos):
                    maybe_start_music()  # harmless
                    continue
                if CHALLENGE_INPUT_RECT.collidepoint(event.pos):
                    try:
                        pygame.key.set_text_input_rect(CHALLENGE_INPUT_RECT)
                        pygame.key.start_text_input()
                    except Exception:
                        pass

            if game_state in ("start","ready"):
                maybe_start_music()
                enter_play()
            elif game_state == "play" and not paused_for_focus:
                maybe_start_music()
                try_flap()
            elif game_state == "gameover":
                if time.time() - gameover_time > 1:
                    reset_game(); game_state = "ready"

    # Background
    SCREEN.blit(background_img, (0, 0))
    # (draw other things; mute button will be drawn last)

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
        capy_movement += gravity
        capy_rect.centery += capy_movement
        capy_angle = -capy_movement * 3
        capy_rotated = pygame.transform.rotate(capy_img, capy_angle)
        SCREEN.blit(capy_rotated, capy_rotated.get_rect(center=capy_rect.center))
        obstacles[:] = update_obstacles(dt)
        maybe_spawn_by_distance()
        draw_obstacles()
        if not check_collision_single_column():
            game_state = "gameover"; gameover_time = time.time(); spawning_enabled = False
            if SOUND_ENABLED and (not is_muted) and SFX_GAMEOVER:
                if not played_gameover_sound:
                    try: SFX_GAMEOVER.play()
                    except: pass
                    played_gameover_sound = True
        for ob in obstacles:
            if (not ob["scored"]) and (ob["x"]+OBSTACLE_WIDTH) < capy_rect.left:
                score += 1; ob["scored"] = True
                if SOUND_ENABLED and (not is_muted) and SFX_REWARD:
                    try: SFX_REWARD.play()
                    except: pass
        if score >= next_challenge_at: start_challenge()
        score_display("main")

    elif game_state == "play" and paused_for_focus:
        draw_obstacles(); SCREEN.blit(capy_img, capy_img.get_rect(center=capy_rect.center))
        score_display("main")
        draw_text_center("Paused (click tab to return)", 20, int(HEIGHT*0.15), (200,200,200))

    elif game_state == "challenge":
        draw_obstacles()
        SCREEN.blit(capy_img, capy_img.get_rect(center=capy_rect.center))
        score_display("main")
        draw_challenge_overlay()

        if challenge["typed"] == challenge["code"]:
            # Passed: clear course and go to READY
            try:
                pygame.key.stop_text_input()
            except Exception:
                pass
            challenge["active"] = False
            game_state = "ready"
            challenge["typed"] = ""
            challenge["code"] = ""
            challenge["deadline"] = 0.0
            obstacles.clear()
            capy_movement = 0
            next_spacing_x = OBSTACLE_SPACING_X + random.randint(-SPACING_JITTER, SPACING_JITTER)
            next_challenge_at = score + next_challenge_increment()
            spawning_enabled = False

        elif time.perf_counter() > challenge["deadline"]:
            # Failed challenge -> game over
            try:
                pygame.key.stop_text_input()
            except Exception:
                pass
            game_state = "gameover"
            gameover_time = time.time()
            spawning_enabled = False
            if SOUND_ENABLED and (not is_muted) and SFX_GAMEOVER:
                if not played_gameover_sound:
                    try: SFX_GAMEOVER.play()
                    except: pass
                    played_gameover_sound = True

    else:  # gameover
        draw_obstacles()
        SCREEN.blit(capy_img, capy_img.get_rect(center=capy_rect.center))
        if score > high_score:
            high_score = score
        draw_text_center("Game Over!", 42, HEIGHT//4, (255,80,80))
        score_display("game_over")
        if time.time() - gameover_time > 1:
            draw_text_center("Press R / Tap to Try Again", 22, int(HEIGHT*0.68))

    # --- Draw the mute button LAST so it stays on top of pillars/overlays ---
    draw_mute_button()

    pygame.display.update()
    CLOCK.tick(60)
