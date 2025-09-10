# === imports ===
import pygame
import sys, random, time, math, string, os
import json as _json
from pathlib import Path
from typing import Optional

# =========================
# --- Messaging hooks for Supabase leaderboard ---
import sys
IS_WEB = (sys.platform == "emscripten")
try:
    import js
except Exception:
    js = None


def _dbg_log(text: str):
    if not IS_WEB:
        return
    try:
        if js is not None:
            js.console.log(str(text))
        elif emscripten is not None:
            emscripten.run_script(f"console.log({_json.dumps(str(text))})")
    except Exception:
        pass

# --- robust postMessage helper (JSON -> plain JS object) ---
def _post_to_parent(msg: dict):
    if not IS_WEB:
        return
    try:
        payload = _json.dumps(msg)  # JSON string
    except Exception:
        return

    # Prefer direct js bridge
    try:
        js.window.top.postMessage(js.JSON.parse(payload), "*")
        return
    except Exception:
        pass
    try:
        js.window.parent.postMessage(js.JSON.parse(payload), "*")
        return
    except Exception:
        pass

    # Fallback via emscripten (quote JSON string in JS)
    if emscripten is not None:
        try:
            q = _json.dumps(payload)
            emscripten.run_script(f"window.top.postMessage(JSON.parse({q}), '*')")
            return
        except Exception:
            try:
                emscripten.run_script(f"window.parent.postMessage(JSON.parse({q}), '*')")
            except Exception:
                pass

# --- sync "my real best" from parent / localStorage into high_score ---
def _poll_parent_best():
    if not IS_WEB or js is None:
        return
    v = None
    # 1) direct bridge variable
    try:
        v = js.window.__sm_my_best
    except Exception:
        v = None
    # 2) fallback: localStorage
    if v in (None, 0, "0"):
        try:
            s = js.window.localStorage.getItem("sm_my_best")
            if s is not None:
                v = int(s)
        except Exception:
            v = None
    # 3) apply if higher
    try:
        if v is not None:
            v = int(v)
            global high_score
            if v > high_score:
                high_score = v
    except Exception:
        pass


_RUN_STARTED = False
score_sent = False  # ensure SCORE is sent once per run

def notify_run_start():
    """Call once when the player starts a run (first tap/space)."""
    global _RUN_STARTED
    if not _RUN_STARTED:
        _RUN_STARTED = True
        _dbg_log("notify_run_start()")
        _post_to_parent({"type": "RUN_START"})

def notify_score(score: int):
    """Call once on game over with the final score (int)."""
    global score_sent
    if score_sent:
        return
    score_sent = True
    _dbg_log(f"notify_score({int(score)})")
    _post_to_parent({"type": "SCORE", "score": int(score)})

def reset_run_flag():
    """Call when resetting to title/ready state."""
    global _RUN_STARTED, score_sent
    _RUN_STARTED = False
    score_sent = False

def notify_checkpoint(score: int):
    """Call whenever score increments, to prove progress."""
    _dbg_log(f"notify_checkpoint({int(score)})")   # <-- visible in page console
    try:
        _post_to_parent({"type": "SCORE_TICK", "score": int(score)})
    except Exception:
        pass

# =========================
#  SETUP
# =========================
pygame.init()
WIDTH, HEIGHT = 400, 600
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Flappy Bara 🐹")
# --- Game version (shown only on the start screen) ---
GAME_VERSION = "v0.2.6"


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

# =========================
#  ASSET HELPERS (new)
# =========================
BASE    = Path(__file__).parent          # /game
ASSETS  = BASE / "assets"
IMG_DIRS = [ASSETS / "imgs", ASSETS / "img", ASSETS]
SND_DIRS = [ASSETS / "sound", ASSETS / "audio", ASSETS]

def _resolve_path(name: str, dirs: list[Path]) -> Path:
    """
    Find 'name' by checking:
      1) absolute path
      2) BASE/name
      3) each dir / basename
      4) current working directory (legacy)
    """
    p = Path(name)
    if p.is_absolute() and p.exists():
        return p
    # direct relative to the game folder
    cand = BASE / p
    if cand.exists():
        return cand
    # search within preferred asset dirs (use just the filename)
    for d in dirs:
        q = d / p.name
        if q.exists():
            return q
    # legacy: whatever the process CWD is
    if p.exists():
        return p
    raise FileNotFoundError(f"Asset not found: {name} (searched: {', '.join(map(str, dirs))})")

def load_img(name: str) -> pygame.Surface:
    path = _resolve_path(name, IMG_DIRS)
    return pygame.image.load(str(path)).convert_alpha()

def _first_existing_sound(basename: str, exts: tuple[str, ...]) -> Optional[str]:
    """
    Return the first existing path for 'basename' among exts, searching
    BASE and SND_DIRS. Example: basename='music_loop', exts=('.wav','.ogg')
    """
    # if caller passed a full filename with extension, respect it
    base_path = Path(basename)
    if base_path.suffix:
        try:
            return str(_resolve_path(basename, SND_DIRS))
        except FileNotFoundError:
            return None

    # try BASE then each SND_DIR with each extension
    search_dirs = [BASE] + SND_DIRS
    for d in search_dirs:
        for ext in exts:
            cand = d / f"{basename}{ext}"
            if cand.exists():
                return str(cand)
    # last chance: process CWD
    for ext in exts:
        cand = Path(f"{basename}{ext}")
        if cand.exists():
            return str(cand)
    return None

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

def load_audio_assets():
    """(Re)load all audio assets after mixer init. Keeps globals up to date."""
    global MUSIC_BG, SFX_REWARD, SFX_GAMEOVER
    MUSIC_BG = None
    SFX_REWARD = None
    SFX_GAMEOVER = None
    if not SOUND_ENABLED:
        return

    # Prefer WAV on web/iOS, fall back to OGG; desktop can also try mp3/m4a
    exts_web     = (".wav", ".ogg")
    exts_desktop = (".ogg", ".wav", ".mp3", ".m4a")
    preferred = exts_web if IS_WEB else exts_desktop

    music_path  = _first_existing_sound("flappy_capy_smooth_loop", preferred)
    reward_path = _first_existing_sound("reward_ding",             preferred)
    over_path   = _first_existing_sound("game_over_wah",           preferred)

    try:
        if IS_WEB:
            if music_path:
                MUSIC_BG = pygame.mixer.Sound(music_path)
        else:
            if music_path:
                pygame.mixer.music.load(music_path)
                pygame.mixer.music.set_volume(MUSIC_VOLUME)
    except Exception:
        pass

    try:
        if reward_path:
            SFX_REWARD = pygame.mixer.Sound(reward_path);  SFX_REWARD.set_volume(SFX_VOLUME)
        if over_path:
            SFX_GAMEOVER = pygame.mixer.Sound(over_path);  SFX_GAMEOVER.set_volume(SFX_VOLUME)
    except Exception:
        pass

def hard_resume_audio():
    """Re-init mixer AFTER a user gesture, then reload assets and start music."""
    global SOUND_ENABLED, MUSIC_STARTED, MUSIC_CHANNEL
    try:
        pygame.mixer.quit()
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.mixer.init()
        SOUND_ENABLED = True
    except Exception:
        SOUND_ENABLED = False
        return

    load_audio_assets()
    MUSIC_STARTED = False
    # start music immediately (we're inside a gesture)
    try:
        if IS_WEB:
            if MUSIC_BG is not None:
                if MUSIC_CHANNEL is None:
                    pygame.mixer.set_num_channels(max(8, pygame.mixer.get_num_channels()))
                    MUSIC_CHANNEL = pygame.mixer.Channel(0)
                MUSIC_CHANNEL.play(MUSIC_BG, loops=-1)
                MUSIC_CHANNEL.set_volume(0.0 if is_muted else MUSIC_VOLUME)
        else:
            pygame.mixer.music.play(-1)
        MUSIC_STARTED = True
        _apply_mute_state()
    except Exception:
        pass

def maybe_start_music():
    """Start looping music after a user gesture (needed on iOS)."""
    global MUSIC_STARTED, MUSIC_CHANNEL
    if MUSIC_STARTED:
        return
    # Try normal start first
    try:
        if IS_WEB:
            if MUSIC_BG is not None:
                if MUSIC_CHANNEL is None:
                    pygame.mixer.set_num_channels(max(8, pygame.mixer.get_num_channels()))
                    MUSIC_CHANNEL = pygame.mixer.Channel(0)
                MUSIC_CHANNEL.play(MUSIC_BG, loops=-1)
                MUSIC_CHANNEL.set_volume(0.0 if is_muted else MUSIC_VOLUME)
                MUSIC_STARTED = True
        else:
            pygame.mixer.music.play(-1)
            MUSIC_STARTED = True
        _apply_mute_state()
        return
    except Exception:
        pass
    # If that didn’t work (suspended context), do a hard mixer re-init now
    hard_resume_audio()

# Load sounds once at boot (will be reloaded by hard_resume_audio on iOS if needed)
load_audio_assets()

MUTE_BTN_SIZE = 36
mute_button_rect = pygame.Rect(WIDTH - MUTE_BTN_SIZE - 10, 10, MUTE_BTN_SIZE, MUTE_BTN_SIZE)

def draw_mute_button():
    """Text button that says MUTE; when muted, draw a red slash across it."""
    r = mute_button_rect

    # Button chrome
    pygame.draw.rect(SCREEN, (0, 0, 0), r, border_radius=8)
    pygame.draw.rect(SCREEN, (220, 220, 220), r, width=2, border_radius=8)

    # Inner area for the text
    pad_x, pad_y = 6, 4
    inner = r.inflate(-2 * pad_x, -2 * pad_y)

    label = "MUTE"
    # Find the largest font that fits in the inner rect
    lo, hi = 8, max(12, inner.h)  # reasonable bounds
    best = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        f = pygame.font.SysFont("Arial", mid, bold=True)
        w, h = f.size(label)
        if w <= inner.w and h <= inner.h:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1

    # Render label (slightly dim if muted)
    f = pygame.font.SysFont("Arial", best, bold=True)
    col = (240, 240, 240) if not is_muted else (210, 210, 210)
    txt = f.render(label, True, col)
    SCREEN.blit(txt, (r.centerx - txt.get_width() // 2,
                      r.centery - txt.get_height() // 2))

    # Red slash when muted
    if is_muted:
        sw = max(3, r.w // 10)
        pygame.draw.line(
            SCREEN, (230, 60, 60),
            (r.left + 6, r.bottom - 6),   # bottom-left inside the border
            (r.right - 6, r.top + 6),     # top-right inside the border
            sw
        )



def _point_in(rect, pos): return rect.collidepoint(pos)

CLOCK = pygame.time.Clock()
FONT = pygame.font.SysFont("Arial", 32)
VERSION_FONT = pygame.font.SysFont("Arial", 14)


# --- Game variables ---
# Time-based physics (device independent)
GRAVITY = 1800.0        # pixels / s^2   (~0.5 per frame at 60 FPS)
FLAP_VELOCITY = -600.0  # pixels / s     (~-10 per frame at 60 FPS)
capy_movement = 0.0     # velocity (px/s)
capy_y = float(HEIGHT // 2)  # precise vertical position as float

game_state = "start"
score = 0
high_score = 0
gameover_time = 0
played_gameover_sound = False

# NEW: pull best from parent once at boot (if available)
_poll_parent_best()

# --- HARDEN: flap rate limit ---
MAX_FLAPS_PER_SEC = 12.0
MIN_FLAP_INTERVAL = 1.0 / MAX_FLAPS_PER_SEC
last_flap_time = 0.0

def try_flap():
    global capy_movement, last_flap_time
    t = time.perf_counter()
    if t - last_flap_time >= MIN_FLAP_INTERVAL:
        capy_movement = FLAP_VELOCITY
        last_flap_time = t

# =========================
#  ASSETS (uses new helpers)
# =========================
background_img = load_img("capy back.png").convert()
background_img = pygame.transform.scale(background_img, (WIDTH, HEIGHT))

capy_img = load_img("flappy capy.png")
capy_img = pygame.transform.scale(capy_img, (60, 45))
capy_rect = pygame.Rect(0, 0, 35, 25)
capy_rect.center = (100, HEIGHT // 2)

# =========================
#  PILLARS
# =========================
OBSTACLE_WIDTH = 60
OBSTACLE_HITBOX_INSET_X = 8   # pixels trimmed from each side for fair collisions
SCROLL_SPEED   = 150
SPAWN_OFFSET_X = WIDTH + 60
OBSTACLE_SPACING_X = 150   # phone-friendly spacing (was 130)
SPACING_JITTER = 15
SPAWN_EDGE_GUARD = 40

obstacles = []
spawning_enabled = False
next_spacing_x = OBSTACLE_SPACING_X

def make_pillar_surface(gap_y, gap_size):
    """
    Render each pillar section as a soft gold coin stack:
    - Left/right rim shading (horizontal gradient)
    - Soft specular highlight band
    - Subtle coin ridges (paired light/dark 1px lines)
    """
    surf = pygame.Surface((OBSTACLE_WIDTH, HEIGHT), pygame.SRCALPHA)

    # --- Gold palette (less cartoony / less bright) ---
    GOLD_SHADOW = (90, 70, 25)     # deep bronze
    GOLD_MID    = (170, 135, 40)   # muted gold
    GOLD_LIGHT  = (210, 190, 120)  # soft highlight (less bright)
    
    RIDGE_LIGHT  = (220, 200, 150, 80)# light ridge line (semi-transparent)
    RIDGE_DARK   = (80, 60, 30, 70)   # shadow ridge line (semi-transparent)
    BORDER_DARK  = (120, 85, 26, 180)   # inner border for definition

    gap_top = max(0, gap_y - gap_size // 2)
    gap_bot = min(HEIGHT, gap_y + gap_size // 2)
    top_rect    = pygame.Rect(0, 0, OBSTACLE_WIDTH, max(0, gap_top))
    bottom_rect = pygame.Rect(0, gap_bot, OBSTACLE_WIDTH, max(0, HEIGHT - gap_bot))

    def lerp(a, b, t): return a + (b - a) * t
    def lerp_color(c1, c2, t):
        return (int(lerp(c1[0], c2[0], t)),
                int(lerp(c1[1], c2[1], t)),
                int(lerp(c1[2], c2[2], t)))

    def fill_horizontal_gradient(target, rect, left_color, mid_color, right_color, mid_pos=0.38):
        """Left->mid->right three-stop gradient across the width."""
        w = rect.width
        if w <= 0 or rect.height <= 0: return
        for ix in range(w):
            x = ix / max(1, w - 1)
            if x <= mid_pos:
                t = x / max(1e-6, mid_pos)
                col = lerp_color(left_color, mid_color, t)
            else:
                t = (x - mid_pos) / max(1e-6, 1.0 - mid_pos)
                col = lerp_color(mid_color, right_color, t)
            pygame.draw.line(target, col, (rect.left + ix, rect.top), (rect.left + ix, rect.bottom - 1))

    def draw_coin_ridges(target, rect, step=16):
        # Two 1px lines (light then slight shadow) every 'step' pixels
        y = rect.top + 10
        while y < rect.bottom - 10:
            if rect.height <= 0: break
            pygame.draw.line(target, RIDGE_LIGHT, (rect.left + 5, y),  (rect.right - 6, y))
            y2 = y + 2
            if y2 < rect.bottom - 2:
                pygame.draw.line(target, RIDGE_DARK,  (rect.left + 5, y2), (rect.right - 6, y2))
            y += step

    def edge_sheen_and_border(target, rect):
        # Slight left/right rim darkening and a slim specular band
        pygame.draw.rect(target, (0, 0, 0, 60), (rect.left,        rect.top, 3, rect.height))  # left shadow
        pygame.draw.rect(target, (0, 0, 0, 70), (rect.right - 4,   rect.top, 4, rect.height))  # right shadow
        # Specular highlight band ~35% from the left
        band_w = max(2, rect.width // 10)
        band_x = rect.left + int(rect.width * 0.35)
        highlight = pygame.Surface((band_w, rect.height), pygame.SRCALPHA)
        for iy in range(rect.height):
            t = 1.0 - abs((iy / max(1, rect.height - 1)) - 0.5) * 2.0  # stronger in the middle
            a = int(20 + 20 * t)  # 20..40 alpha → much more subtle
            pygame.draw.line(highlight, (255, 255, 255, a), (0, iy), (band_w - 1, iy))
        target.blit(highlight, (band_x, rect.top))

        # Soft inner border for definition (rounded a touch)
        inset = rect.inflate(-2, -2)
        if inset.width > 0 and inset.height > 0:
            pygame.draw.rect(target, BORDER_DARK, inset, width=2, border_radius=6)

    def draw_section(rect):
        if rect.height <= 0: return
        # base fill with a 3-stop horizontal gradient (gives "cylinder" feel)
        fill_horizontal_gradient(surf, rect, GOLD_SHADOW, GOLD_LIGHT, GOLD_MID, mid_pos=0.40)
        draw_coin_ridges(surf, rect, step=24)     # subtle 1px coin edges
        edge_sheen_and_border(surf, rect)         # sheen + definition

    draw_section(top_rect)
    draw_section(bottom_rect)

    # carve out the gap as transparent
    gap_rect = pygame.Rect(0, gap_top, OBSTACLE_WIDTH, max(0, gap_bot - gap_top))
    if gap_rect.height > 0:
        surf.fill((0, 0, 0, 0), gap_rect)

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
    inset = OBSTACLE_HITBOX_INSET_X
    w = max(2, OBSTACLE_WIDTH - 2*inset)
    top_rect    = pygame.Rect(x + inset, 0, w, gap_y - gap_size//2)
    bottom_rect = pygame.Rect(x + inset, gap_y + gap_size//2, w, HEIGHT - (gap_y + gap_size//2))
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
def next_challenge_increment(): return random.randint(25, 45)
next_challenge_at = next_challenge_increment()

# Bot-hardening config
MIN_CHAR_INTERVAL = 0.12      # 120 ms between chars
MAX_STRIKES = 3               # wrong 4-char tries allowed
last_char_time = 0.0

challenge = {
    "code": "",
    "typed": "",
    "deadline": 0.0,
    "active": False,
    "time_limit": 15.0,   # 15 seconds
    "strikes": 0
}

# Input rect for mobile keyboards (matches the overlay box)
CHALLENGE_INPUT_RECT = pygame.Rect(WIDTH//2 - 130, HEIGHT//2 - 40, 260, 80)

# Allowed character set (matches code generation)
ALLOWED_CHARS = [d for d in "23456789"] + [c for c in string.ascii_uppercase if c not in ("O","I")]

def random_code(n=4):
    alphabet = [c for c in string.ascii_uppercase if c not in ("O","I")]
    digits   = [d for d in "23456789"]
    pool = alphabet + digits
    return "".join(random.choice(pool) for _ in range(n))

def start_challenge():
    global game_state, challenge, spawning_enabled, keyboard_mode
    spawning_enabled = False
    challenge["code"] = random_code(4)
    challenge["typed"] = ""
    challenge["deadline"] = time.perf_counter() + challenge["time_limit"]
    challenge["active"] = True
    challenge["strikes"] = 0
    keyboard_mode = "letters"  # start on letters

    game_state = "challenge"
    # Mobile keyboards: start text input and anchor to the code box
    try:
        pygame.key.set_text_input_rect(CHALLENGE_INPUT_RECT)
        pygame.key.start_text_input()
    except Exception:
        pass

# =============== Phone-style on-screen keyboard ===============
keyboard_mode = "letters"  # or 'numbers'

def _keyboard_rows_letters():
    # iOS-like three rows + bottom row with 123 and backspace
    rows = [
        list("QWERTYUIOP"),
        list("ASDFGHJKL"),
        list("ZXCVBNM")
    ]
    # Show I and O but disable them (not allowed in codes)
    disabled = set(["I","O"])
    return rows, disabled

def _keyboard_rows_numbers():
    # Only digits 2..9 (0 and 1 are not used in codes)
    rows = [
        list("2345"),
        list("6789")
    ]
    disabled = set()  # all shown numbers are valid
    return rows, disabled

def get_keyboard_layout():
    """
    Build phone-like keyboard geometry.
    Returns list of (label, rect, enabled, kind)
    kind in {"char","backspace","toggle","spacer"}
    """
    pad = 6
    # available area for the keyboard (bottom ~45% of screen)
    avail_top = int(HEIGHT * 0.55)
    avail_bottom = HEIGHT - 10

    # Build logical rows
    if keyboard_mode == "letters":
        rows, disabled = _keyboard_rows_letters()
        bottom = [["123"], [" "], ["←"]]  # spacer in middle
    else:
        rows, disabled = _keyboard_rows_numbers()
        bottom = [["ABC"], [" "], ["←"]]

    # Combine rows with bottom bar
    all_rows = rows + bottom

    # Compute geometry
    total_rows = len(all_rows)
    avail_h = max(140, avail_bottom - avail_top)
    key_h = (avail_h - (total_rows + 1) * pad) // total_rows

    y = avail_top + pad
    layout = []
    for r, row in enumerate(all_rows):
        # bottom row: three equal slots (toggle, spacer, backspace)
        if r == total_rows - 1:
            nkeys = 3
            key_w = (WIDTH - (nkeys + 1) * pad) // nkeys
            x = pad
            # left = toggle
            rect = pygame.Rect(x, y, key_w, key_h)
            layout.append(("TOGGLE", rect, True, "toggle")); x += key_w + pad
            # middle spacer
            rect = pygame.Rect(x, y, key_w, key_h)
            layout.append(("SPACE", rect, False, "spacer")); x += key_w + pad
            # right = backspace
            rect = pygame.Rect(x, y, key_w, key_h)
            layout.append(("BACK", rect, True, "backspace"))
        else:
            # center shorter rows
            nkeys = len(row)
            key_w = (WIDTH - (nkeys + 1) * pad) // nkeys
            x = pad
            for label in row:
                rect = pygame.Rect(x, y, key_w, key_h)
                kind = "char"
                enabled = (label in ALLOWED_CHARS)
                if keyboard_mode == "letters" and label in ("I","O"):
                    enabled = False
                layout.append((label, rect, enabled, kind))
                x += key_w + pad
        y += key_h + pad

    return layout

def draw_keyboard():
    keys = get_keyboard_layout()
    for label, rect, enabled, kind in keys:
        # style
        bg = (25,25,25) if enabled or kind in ("backspace","toggle") else (15,15,15)
        border = (210,210,210) if enabled or kind in ("backspace","toggle") else (90,90,90)
        pygame.draw.rect(SCREEN, bg, rect, border_radius=8)
        pygame.draw.rect(SCREEN, border, rect, width=2, border_radius=8)

        if kind == "spacer":
            continue

        txt_label = label
        if kind == "toggle":
            txt_label = "123" if keyboard_mode == "letters" else "ABC"
        elif kind == "backspace":
            txt_label = "←"

        color = (240,240,240) if (enabled or (kind in ("backspace","toggle"))) else (120,120,120)
        txt = FONT.render(txt_label, True, color)
        SCREEN.blit(txt, (rect.centerx - txt.get_width()//2, rect.centery - txt.get_height()//2))

def handle_keyboard_click(pos):
    global keyboard_mode, last_char_time
    keys = get_keyboard_layout()
    for label, rect, enabled, kind in keys:
        if rect.collidepoint(pos):
            if kind == "toggle":
                keyboard_mode = "numbers" if keyboard_mode == "letters" else "letters"
                return True
            if kind == "backspace":
                if challenge["typed"]:
                    challenge["typed"] = challenge["typed"][:-1]
                return True
            if kind == "char" and enabled and len(challenge["typed"]) < 4:
                t = time.perf_counter()
                if (t - last_char_time) >= MIN_CHAR_INTERVAL:
                    challenge["typed"] += label
                    last_char_time = t
                return True
            return True
    return False

# --- Slight anti-OCR distortion for the code text (deterministic) ---
def draw_distorted_code(code, y, color=(255,255,255)):
    rng = random.Random(code)  # deterministic per challenge
    glyphs = []
    spacing = 6
    total_w = 0
    for ch in code:
        surf = FONT.render(ch, True, color)
        angle = rng.uniform(-6, 6)   # small rotation
        rotated = pygame.transform.rotate(surf, angle)
        # tiny x jitter to break perfect alignment
        offset_x = rng.randint(-1, 1)
        glyphs.append((rotated, offset_x))
        total_w += rotated.get_width() + spacing
    total_w -= spacing
    x = WIDTH//2 - total_w//2
    for rotated, dx in glyphs:
        SCREEN.blit(rotated, (x + dx, y))
        x += rotated.get_width() + spacing

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
    try:
        reset_run_flag()
    except Exception:
        pass
    global score_sent
    global capy_movement, capy_y, score, obstacles, next_challenge_at, challenge, spawning_enabled, next_spacing_x, played_gameover_sound
    capy_rect.center = (100, HEIGHT // 2)
    capy_y = float(HEIGHT // 2)
    capy_movement = 0.0
    obstacles = []
    score = 0
    score_sent = False
    next_challenge_at = next_challenge_increment()
    challenge["active"] = False
    challenge["typed"] = ""
    challenge["code"] = ""
    challenge["deadline"] = 0.0
    challenge["strikes"] = 0
    spawning_enabled = False
    next_spacing_x = OBSTACLE_SPACING_X + random.randint(-SPACING_JITTER, SPACING_JITTER)
    played_gameover_sound = False
    _apply_mute_state()

def enter_play():
    global game_state, spawning_enabled, next_spacing_x, capy_y
    game_state = "play"; spawning_enabled = True
    next_spacing_x = OBSTACLE_SPACING_X + random.randint(-SPACING_JITTER, SPACING_JITTER)
    # Sync float position to current sprite position to avoid a jump
    capy_y = float(capy_rect.centery)

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
    # Distorted code (anti-OCR) — centered
    draw_distorted_code(code, box_rect.y + 8, (255,255,255))
    typed_font = pygame.font.SysFont("Arial", 26)
    typed_surf = typed_font.render(typed or " ", True, (180,220,255))
    SCREEN.blit(typed_surf, (WIDTH//2 - typed_surf.get_width()//2, box_rect.y+46))
    remaining = max(0.0, challenge["deadline"] - time.perf_counter())
    timer_font = pygame.font.SysFont("Arial", 20)
    timer_surf = timer_font.render(f"{remaining:.1f}s", True, (255,200,200) if remaining<3 else (200,255,200))
    SCREEN.blit(timer_surf, (WIDTH//2 - timer_surf.get_width()//2, int(HEIGHT*0.72)))
    # On-screen keyboard (mobile-friendly)
    draw_keyboard()

# =========================
#  MAIN LOOP
# =========================
last_time = time.perf_counter()

while True:
    now = time.perf_counter()
    dt = now - last_time
    last_time = now
    dt = max(0.0, min(dt, 0.10))
    # NEW: keep high_score synced from parent (Supabase value)
    _poll_parent_best()
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
                    try:
                        notify_run_start()
                    except Exception:
                        pass
                    enter_play()

            elif game_state == "play":
                if not paused_for_focus and event.key == pygame.K_SPACE:
                    maybe_start_music()
                    try_flap()

            elif game_state == "challenge":
                # BACKSPACE still arrives as KEYDOWN on soft keyboards / desktop
                if event.key == pygame.K_BACKSPACE:
                    if challenge["typed"]:
                        challenge["typed"] = challenge["typed"][:-1]

            elif game_state == "gameover":
                if time.time() - gameover_time > 1 and event.key in (pygame.K_r, pygame.K_SPACE):
                    reset_game(); game_state = "ready"

        # TEXTINPUT: soft keyboard characters for mobile / desktop IME
        if event.type == pygame.TEXTINPUT and game_state == "challenge":
            ch = event.text.upper()
            t = time.perf_counter()
            if ch in ALLOWED_CHARS:
                if (t - last_char_time) >= MIN_CHAR_INTERVAL and len(challenge["typed"]) < 4:
                    challenge["typed"] = (challenge["typed"] + ch)
                    last_char_time = t
            continue

        # Normal gameplay click handling (after consuming mute click above)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if game_state == "challenge":
                # On-screen phone keyboard tap?
                if handle_keyboard_click(event.pos):
                    maybe_start_music()  # harmless
                    continue
                # If user taps the code box, re-focus text input on mobile
                if CHALLENGE_INPUT_RECT.collidepoint(event.pos):
                    try:
                        pygame.key.set_text_input_rect(CHALLENGE_INPUT_RECT)
                        pygame.key.start_text_input()
                    except Exception:
                        pass

            if game_state in ("start","ready"):
                maybe_start_music()
                try:
                    notify_run_start()
                except Exception:
                    pass
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
            # Show version only on the start screen (bottom-right corner)
        _ver = VERSION_FONT.render(GAME_VERSION, True, (200, 200, 200))
        SCREEN.blit(_ver, (WIDTH - _ver.get_width() - 6, HEIGHT - _ver.get_height() - 6))


    elif game_state == "ready":
        capy_rect.centery = int(HEIGHT*0.55 + 8*math.sin(pygame.time.get_ticks()*0.005))
        SCREEN.blit(capy_img, capy_img.get_rect(center=capy_rect.center))
        draw_obstacles()
        draw_text_center("Get Ready!", 36, HEIGHT//4)
        draw_text_center("Press SPACE or TAP to continue", 22, HEIGHT//2)
        score_display("main")

    elif game_state == "play" and not paused_for_focus:
        # time-based physics
        capy_movement += GRAVITY * dt                # v += a*dt
        capy_y += capy_movement * dt                 # y += v*dt
        capy_rect.centery = int(capy_y)              # assign int to Rect
        capy_angle = -capy_movement * 0.05           # degrees; tuned to feel like before
        capy_rotated = pygame.transform.rotate(capy_img, capy_angle)
        SCREEN.blit(capy_rotated, capy_rotated.get_rect(center=capy_rect.center))

        obstacles[:] = update_obstacles(dt)
        maybe_spawn_by_distance()
        draw_obstacles()

        if not check_collision_single_column():
            game_state = "gameover"; gameover_time = time.time(); spawning_enabled = False
            if not score_sent:
                try:
                    notify_score(score)
                except Exception:
                    pass
                score_sent = True
            if SOUND_ENABLED and (not is_muted) and SFX_GAMEOVER:
                if not played_gameover_sound:
                    try: SFX_GAMEOVER.play()
                    except: pass
                    played_gameover_sound = True

        for ob in obstacles:
            if (not ob["scored"]) and (ob["x"]+OBSTACLE_WIDTH) < capy_rect.left:
                score += 1
                ob["scored"] = True
                try:
                    notify_checkpoint(score)
                except Exception:
                    pass
                if SOUND_ENABLED and (not is_muted) and SFX_REWARD:
                    try:
                        SFX_REWARD.play()
                    except:
                        pass



        if score >= next_challenge_at: start_challenge()
        score_display("main")

    elif game_state == "play" and paused_for_focus:
        draw_obstacles(); SCREEN.blit(capy_img, capy_img.get_rect(center=capy_rect.center))
        score_display("main")
        draw_text_center("Paused (click tab to return)", 20, int(HEIGHT*0.15), (200,200,200))

    elif game_state == "challenge":
        # Wrong full entry -> strike
        if len(challenge["typed"]) == 4 and challenge["typed"] != challenge["code"]:
            challenge["strikes"] += 1
            challenge["typed"] = ""

        draw_obstacles()
        SCREEN.blit(capy_img, capy_img.get_rect(center=capy_rect.center))
        score_display("main")
        draw_challenge_overlay()

        # Success
        if challenge["typed"] == challenge["code"]:
            try: pygame.key.stop_text_input()
            except Exception: pass
            challenge["active"] = False
            game_state = "ready"
            challenge["typed"] = ""
            challenge["code"] = ""
            challenge["deadline"] = 0.0
            challenge["strikes"] = 0
            obstacles.clear()
            capy_movement = 0.0
            next_spacing_x = OBSTACLE_SPACING_X + random.randint(-SPACING_JITTER, SPACING_JITTER)
            next_challenge_at = score + next_challenge_increment()
            spawning_enabled = False

        # Out of time or too many strikes -> game over
        elif time.perf_counter() > challenge["deadline"] or challenge["strikes"] >= MAX_STRIKES:
            try: pygame.key.stop_text_input()
            except Exception: pass
            game_state = "gameover"
            gameover_time = time.time()
            spawning_enabled = False
            if not score_sent:
                try:
                    notify_score(score)
                except Exception:
                    pass
                score_sent = True
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
