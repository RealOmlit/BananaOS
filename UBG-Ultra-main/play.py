#!/usr/bin/env python3
"""
UBG Ultra — Local Game Server (Upgraded)
Double-click or run: python play.py

Serves the games folder, opens the UBG Ultra app, and provides:

  /proxy/<base64url>     Ultraviolet-style dynamic web proxy (rewrites HTML/CSS,
                         strips frame-busting + CSP so sites embed cleanly)
  /api/games             live game catalog (re-scans the games folder)
  /api/scan              POST to force a re-scan of the game library
  /api/saves             per-account cloud save sync (code-authenticated)
  /api/account           server-issued account codes (create / signin / rename)
  /api/ai/               local assistant (play / recommend / proxy / panic)
  /api/chat              live multi-user chat (SSE stream + POST messages)

Every response is hardened: no-referrer, nosniff, same-origin framing.
"""

import http.server
import socketserver
import webbrowser
import threading
import json
import os
import sys
import re
import time
import hmac
import hashlib
import traceback
import socket

import proxy as proxy_mod

BASE = os.path.dirname(os.path.abspath(__file__))

# Keep the content directory out of ordinary sight. The server exposes only
# the app routes and static assets it needs from this internal folder.
GAMES_FOLDER = os.path.join(BASE, ".ubg-content")
DATA_DIR = os.path.join(BASE, "server_data")

if GAMES_FOLDER not in sys.path:
    sys.path.insert(0, GAMES_FOLDER)
import generate_games

SECURITY_HEADERS = {
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cache-Control": "no-cache, no-store, must-revalidate",
}


# ---- chat store (in-memory, mirrored to server_data/chat.json) -------------
CHAT_FILE = os.path.join(DATA_DIR, "chat.json")
CHAT_LOCK = threading.Lock()
CHAT_SUBS = set()          # queue.Queue per live SSE subscriber
CHAT_MSGS = []             # list of {id, user, text, t}
CHAT_MAX = 200
CHAT_NEXT = [1]


def load_chat():
    global CHAT_MSGS
    try:
        with open(CHAT_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            CHAT_MSGS = data[-CHAT_MAX:]
            CHAT_NEXT[0] = max([m.get("id", 0) for m in CHAT_MSGS], default=0) + 1
    except Exception:
        CHAT_MSGS = []
        CHAT_NEXT[0] = 1


def save_chat():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(CHAT_FILE, "w", encoding="utf-8") as f:
            json.dump(CHAT_MSGS[-CHAT_MAX:], f)
    except Exception:
        pass


def chat_broadcast(payload):
    event = "data: %s\n\n" % json.dumps(payload)
    for q in list(CHAT_SUBS):
        try:
            q.put_nowait(event)
        except Exception:
            pass


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


# ---- live presence (who is online right now) -------------------------------
PRESENCE_FILE = os.path.join(DATA_DIR, "presence.json")
PRESENCE_LOCK = threading.RLock()
PRESENCE = {}                       # sid -> {"name": str, "ts": float, "typing": bool}
PRESENCE_TIMEOUT = 25               # seconds of silence before a user goes stale
PRESENCE_SUBS = set()               # queue.Queue per live SSE subscriber


def load_presence():
    global PRESENCE
    try:
        with open(PRESENCE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            now = time.time()
            PRESENCE = {k: v for k, v in data.items()
                        if isinstance(v, dict) and (now - float(v.get("ts", 0))) < PRESENCE_TIMEOUT}
    except Exception:
        PRESENCE = {}


def save_presence():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(PRESENCE_FILE, "w", encoding="utf-8") as f:
            json.dump(PRESENCE, f)
    except Exception:
        pass


def prune_presence():
    now = time.time()
    with PRESENCE_LOCK:
        for sid in [k for k, v in PRESENCE.items() if (now - float(v.get("ts", 0))) > PRESENCE_TIMEOUT]:
            del PRESENCE[sid]
        save_presence()
    broadcast_presence()


def touch_presence(name, sid, game=None):
    name = safe_user(name)[:24] or "Guest"
    sid = str(sid or "")[:64] or ("guest" + str(int(time.time())))
    game = (str(game or "")[:80] or None)
    with PRESENCE_LOCK:
        PRESENCE[sid] = {"name": name, "ts": time.time(), "typing": False, "game": game}
    save_presence()
    broadcast_presence()


def set_typing(name, typing):
    name = safe_user(name)[:24] or "Guest"
    with PRESENCE_LOCK:
        for v in PRESENCE.values():
            if v.get("name") == name:
                v["typing"] = bool(typing)
                v["ts"] = time.time()
    broadcast_presence()


def presence_summary():
    with PRESENCE_LOCK:
        users = sorted({v["name"] for v in PRESENCE.values() if v.get("name")})
        typing = sorted({v["name"] for v in PRESENCE.values() if v.get("typing")})
        games = {}
        for v in PRESENCE.values():
            g = v.get("game")
            if g:
                games[g] = games.get(g, 0) + 1
    return {"online": len(users), "users": users, "typing": typing, "games": games}


def broadcast_presence():
    payload = "data: %s\n\n" % json.dumps({"type": "presence", **presence_summary()})
    for q in list(PRESENCE_SUBS):
        try:
            q.put_nowait(payload)
        except Exception:
            pass


# ---- Society Ultra live world (shared 3D multiplayer sandbox) ---------------
SOCIETY_FILE = os.path.join(DATA_DIR, "society_world.json")
SOCIETY_LOCK = threading.RLock()
SOCIETY_PLAYERS = {}    # sid -> {"name", "x", "y", "z", "rot", "ts"}
SOCIETY_OBSTACLES = []  # [{"id", "x", "y", "z", "w", "h", "d", "color"}]
SOCIETY_TIMEOUT = 8     # seconds of silence before a player is dropped
SOCIETY_NEXT = [1]      # obstacle id counter


def load_society():
    global SOCIETY_OBSTACLES
    try:
        with open(SOCIETY_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("obstacles"), list):
            SOCIETY_OBSTACLES = [o for o in data["obstacles"] if isinstance(o, dict)]
            SOCIETY_NEXT[0] = max([int(o.get("id", 0)) for o in SOCIETY_OBSTACLES], default=0) + 1
    except Exception:
        SOCIETY_OBSTACLES = []
        SOCIETY_NEXT[0] = 1


def save_society():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SOCIETY_FILE, "w", encoding="utf-8") as f:
            json.dump({"obstacles": SOCIETY_OBSTACLES}, f)
    except Exception:
        pass


def prune_society():
    now = time.time()
    with SOCIETY_LOCK:
        for sid in [k for k, v in SOCIETY_PLAYERS.items()
                    if (now - float(v.get("ts", 0))) > SOCIETY_TIMEOUT]:
            del SOCIETY_PLAYERS[sid]


SOCIETY_EVENT_WINDOW = 600    # seconds between events
SOCIETY_EVENT_LENGTH = 75     # last seconds of each window the event is active
SOCIETY_EVENT_TITLES = ["Party Race", "Build Rush", "Block Hunt", "Free Build"]


def sanitize_app(app):
    if not isinstance(app, dict):
        return {}
    out = {}
    for k in ("shirt", "pants", "hat", "hair", "face"):
        v = app.get(k)
        if v is not None:
            out[k] = str(v)[:32]
    return out


def society_state():
    now = time.time()
    with SOCIETY_LOCK:
        for sid in [k for k, v in SOCIETY_PLAYERS.items()
                    if (now - float(v.get("ts", 0))) > SOCIETY_TIMEOUT]:
            del SOCIETY_PLAYERS[sid]
        players = []
        for sid, v in SOCIETY_PLAYERS.items():
            players.append({
                "id": sid,
                "name": v.get("name", "Guest"),
                "x": float(v.get("x", 0)),
                "y": float(v.get("y", 0)),
                "z": float(v.get("z", 0)),
                "rot": float(v.get("rot", 0)),
                "app": v.get("app") or {},
                "emote": v.get("emote") or "",
                "emoteUntil": float(v.get("emoteUntil", 0)),
            })
        obstacles = list(SOCIETY_OBSTACLES)
        window = int(now // SOCIETY_EVENT_WINDOW)
        within = now % SOCIETY_EVENT_WINDOW
        active = within > (SOCIETY_EVENT_WINDOW - SOCIETY_EVENT_LENGTH)
        event = {
            "title": SOCIETY_EVENT_TITLES[window % len(SOCIETY_EVENT_TITLES)],
            "active": active,
            "endsAt": int((window + 1) * SOCIETY_EVENT_WINDOW),
        }
    return {"online": len(players), "players": players, "obstacles": obstacles, "event": event}



# ---- account codes (server-issued, immutable) ------------------------------
ACCOUNTS_FILE = os.path.join(DATA_DIR, "accounts.json")
ACCOUNTS_LOCK = threading.RLock()
ACCOUNTS = {}                      # code -> {"name": str, "created": ts}
ACCOUNT_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O/1/I/L


def load_accounts():
    global ACCOUNTS
    try:
        with open(ACCOUNTS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            ACCOUNTS = data
    except Exception:
        ACCOUNTS = {}


def save_accounts():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            json.dump(ACCOUNTS, f)
    except Exception:
        pass


def new_account_code():
    import random as rnd
    for _ in range(2000):
        code = "".join(rnd.choice(ACCOUNT_ALPHABET) for _ in range(8))
        if code not in ACCOUNTS:
            return code
    return None


def account_token(code):
    return hashlib.sha256(("ubg-account:" + code).encode("utf-8")).hexdigest()


def safe_user(user):
    return re.sub(r"[^A-Za-z0-9_.-]", "", user or "")[:64]


# ---- social profiles, achievements, leaderboard, community wall -----------
SOCIAL_FILE = os.path.join(DATA_DIR, "social.json")
SOCIAL_LOCK = threading.RLock()
SOCIAL_PROFILES = {}       # lower(name) -> profile dict
WALL_FILE = os.path.join(DATA_DIR, "wall.json")
WALL_LOCK = threading.RLock()
WALL_MSGS = []             # [{id, user, text, t}], newest appended, cap 100
WALL_NEXT = [1]

ACHIEVEMENTS = {
    "first_play": {"name": "First Steps", "desc": "Play any game for the first time"},
    "play_10": {"name": "Getting Started", "desc": "Start 10 play sessions"},
    "play_50": {"name": "Regular", "desc": "Start 50 play sessions"},
    "hours_1": {"name": "Hour Mark", "desc": "Reach 1 hour of total playtime"},
    "hours_5": {"name": "Veteran", "desc": "Reach 5 hours of total playtime"},
    "builder_1": {"name": "Builder", "desc": "Place your first block in Society Ultra"},
    "builder_50": {"name": "Architect", "desc": "Place 50 blocks in Society Ultra"},
    "parkour_1": {"name": "Parkour Pro", "desc": "Finish the Society Ultra parkour course"},
    "wall_1": {"name": "Community Voice", "desc": "Post on the Community Wall"},
    "friend_1": {"name": "Socialite", "desc": "Add a friend"},
    "coin_100": {"name": "Hundred Club", "desc": "Earn 100 coins"},
    "coin_1000": {"name": "Coin Collector", "desc": "Earn 1,000 coins"},
    "daily_3": {"name": "Consistent", "desc": "Claim 3 daily bonuses"},
}


def load_social():
    global SOCIAL_PROFILES
    try:
        with open(SOCIAL_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("profiles"), dict):
            SOCIAL_PROFILES = data["profiles"]
    except Exception:
        SOCIAL_PROFILES = {}


def save_social():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SOCIAL_FILE, "w", encoding="utf-8") as f:
            json.dump({"profiles": SOCIAL_PROFILES}, f)
    except Exception:
        pass


def load_wall():
    global WALL_MSGS, WALL_NEXT
    try:
        with open(WALL_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("messages"), list):
            WALL_MSGS = [m for m in data["messages"] if isinstance(m, dict)]
            WALL_NEXT[0] = max([int(m.get("id", 0)) for m in WALL_MSGS], default=0) + 1
    except Exception:
        WALL_MSGS = []
        WALL_NEXT[0] = 1


def save_wall():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(WALL_FILE, "w", encoding="utf-8") as f:
            json.dump({"messages": WALL_MSGS[-100:]}, f)
    except Exception:
        pass


def social_profile(user):
    """Get (creating if needed) the profile for a username."""
    name = (user or "Guest").strip()[:24] or "Guest"
    key = name.lower()
    with SOCIAL_LOCK:
        p = SOCIAL_PROFILES.get(key)
        if p is None:
            p = {"name": name, "playtime": {}, "total": 0, "sessions": 0,
                 "streak": 0, "lastPlay": 0, "lastDaily": "", "dailyClaims": 0,
                 "coins": 0, "blocks": 0, "parkour": 0, "wallPosts": 0,
                 "achievements": [], "friends": []}
            SOCIAL_PROFILES[key] = p
        if not isinstance(p.get("playtime"), dict):
            p["playtime"] = {}
        if not isinstance(p.get("friends"), list):
            p["friends"] = []
        if not isinstance(p.get("achievements"), list):
            p["achievements"] = []
        return p


def social_check_ach(profile):
    """Return ids newly unlocked by the profile's current state."""
    total = profile.get("total", 0)
    coins = profile.get("coins", 0)
    earned = set(profile.get("achievements", []))
    checks = [
        ("first_play", profile.get("sessions", 0) >= 1),
        ("play_10", profile.get("sessions", 0) >= 10),
        ("play_50", profile.get("sessions", 0) >= 50),
        ("hours_1", total >= 3600),
        ("hours_5", total >= 18000),
        ("builder_1", profile.get("blocks", 0) >= 1),
        ("builder_50", profile.get("blocks", 0) >= 50),
        ("parkour_1", profile.get("parkour", 0) > 0),
        ("wall_1", profile.get("wallPosts", 0) >= 1),
        ("friend_1", len(profile.get("friends", [])) >= 1),
        ("coin_100", coins >= 100),
        ("coin_1000", coins >= 1000),
        ("daily_3", profile.get("dailyClaims", 0) >= 3),
    ]
    new = []
    for aid, done in checks:
        if done and aid not in earned:
            earned.add(aid)
            new.append(aid)
    profile["achievements"] = sorted(earned)
    return new


def social_add_play(user, game, secs):
    import datetime
    now = time.time()
    profile = social_profile(user)
    with SOCIAL_LOCK:
        game = (str(game or "Unknown")[:64]) or "Unknown"
        secs = int(secs or 0)
        if secs < 1:
            secs = 1
        if secs > 3600:
            secs = 3600
        profile["playtime"][game] = profile["playtime"].get(game, 0) + secs
        profile["total"] = profile.get("total", 0) + secs
        if not profile.get("lastPlay") or (now - float(profile.get("lastPlay", 0))) > 7200:
            profile["sessions"] = profile.get("sessions", 0) + 1
        today = datetime.date.today().isoformat()
        yday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        last = profile.get("streakDate", "")
        if last == yday:
            profile["streak"] = profile.get("streak", 0) + 1
        elif last != today:
            profile["streak"] = 1
        profile["streakDate"] = today
        profile["lastPlay"] = now
        profile["coins"] = profile.get("coins", 0) + max(1, secs // 10)
        new = social_check_ach(profile)
        save_social()
    return profile, new


def social_add_block(user):
    profile = social_profile(user)
    with SOCIAL_LOCK:
        profile["blocks"] = profile.get("blocks", 0) + 1
        profile["coins"] = profile.get("coins", 0) + 1
        new = social_check_ach(profile)
        save_social()
    return profile, new


def social_parkour(user, t):
    profile = social_profile(user)
    t = float(t or 0)
    if t <= 0 or t > 3600:
        return profile, []
    with SOCIAL_LOCK:
        improved = not profile.get("parkour") or t < profile["parkour"]
        new = []
        if improved:
            profile["parkour"] = round(t, 2)
            new = social_check_ach(profile)
            save_social()
    return profile, new


def social_claim_daily(user):
    import datetime
    profile = social_profile(user)
    today = datetime.date.today().isoformat()
    with SOCIAL_LOCK:
        if profile.get("lastDaily") == today:
            return profile, [], False
        bonus = 50
        profile["coins"] = profile.get("coins", 0) + bonus
        profile["lastDaily"] = today
        profile["dailyClaims"] = profile.get("dailyClaims", 0) + 1
        new = social_check_ach(profile)
        save_social()
    return profile, new, True


def social_friend(user, op, other):
    profile = social_profile(user)
    other = (other or "").strip()[:24]
    if not other or other.lower() == profile["name"].lower():
        return profile, []
    with SOCIAL_LOCK:
        friends = profile.get("friends", [])
        if op == "add":
            if other.lower() not in [f.lower() for f in friends]:
                friends.append(other)
                profile["friends"] = friends
        elif op == "remove":
            profile["friends"] = [f for f in friends if f.lower() != other.lower()]
        else:
            return profile, []
        new = social_check_ach(profile)
        save_social()
    return profile, new


def social_public(user):
    profile = social_profile(user)
    with SOCIAL_LOCK:
        top = sorted(profile.get("playtime", {}).items(), key=lambda kv: kv[1], reverse=True)[:5]
        return {
            "name": profile["name"],
            "total": profile.get("total", 0),
            "sessions": profile.get("sessions", 0),
            "streak": profile.get("streak", 0),
            "coins": profile.get("coins", 0),
            "blocks": profile.get("blocks", 0),
            "parkour": profile.get("parkour", 0),
            "achievements": profile.get("achievements", []),
            "friends": profile.get("friends", []),
            "dailyClaims": profile.get("dailyClaims", 0),
            "lastDaily": profile.get("lastDaily", ""),
            "topGames": [{"name": g, "secs": s} for g, s in top],
        }


def social_leaderboard(kind):
    kind = kind or "coins"
    rows = []
    with SOCIAL_LOCK:
        for p in SOCIAL_PROFILES.values():
            if kind == "coins":
                rows.append((p.get("name", "Guest"), int(p.get("coins", 0))))
            elif kind == "blocks":
                rows.append((p.get("name", "Guest"), int(p.get("blocks", 0))))
            elif kind == "parkour":
                pb = p.get("parkour", 0)
                if pb > 0:
                    rows.append((p.get("name", "Guest"), round(float(pb), 2)))
            else:
                rows.append((p.get("name", "Guest"),
                             int(p.get("playtime", {}).get("Society Ultra", 0))))
    rows.sort(key=lambda r: r[1], reverse=True)
    return [{"name": n, "value": v} for n, v in rows[:10]]


def wall_post(user, text):
    global WALL_MSGS, WALL_NEXT
    profile = social_profile(user)
    text = re.sub(r"<[^>]*>", "", text or "").strip()[:300]
    if not text:
        return None, None
    with WALL_LOCK:
        msg = {"id": WALL_NEXT[0], "user": profile["name"], "text": text, "t": int(time.time())}
        WALL_NEXT[0] += 1
        WALL_MSGS.append(msg)
        if len(WALL_MSGS) > 100:
            WALL_MSGS = WALL_MSGS[-100:]
        save_wall()
    with SOCIAL_LOCK:
        profile["wallPosts"] = profile.get("wallPosts", 0) + 1
        new = social_check_ach(profile)
        save_social()
    return msg, new


class Handler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    # Windows registry MIME mappings can label .htm as a binary download.
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".html": "text/html", ".htm": "text/html", ".html-a": "text/html",
                      ".js": "application/javascript", ".mjs": "application/javascript",
                      ".css": "text/css", ".wasm": "application/wasm",
                      ".json": "application/json", ".svg": "image/svg+xml",
                      ".webp": "image/webp", ".png": "image/png",
                      ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
                      ".ogg": "audio/ogg", ".mp3": "audio/mpeg", ".mp4": "video/mp4"}

    def translate_path(self, path):
        from urllib.parse import unquote, urlsplit
        clean = unquote(urlsplit(path).path)
        prefix = next((p for p in ("/library/", "/artwork/") if clean.startswith(p)), None)
        if prefix:
            folder = "html-main" if prefix == "/library/" else os.path.join("truffled-main", "public", "png", "games")
            root = os.path.realpath(os.path.join(BASE, folder))
            target = os.path.realpath(os.path.join(root, clean[len(prefix):]))
            if os.path.commonpath([root, target]) != root:
                return os.path.join(root, "__invalid_path__")
            return target
        return super().translate_path(path)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=GAMES_FOLDER, **kwargs)

    def log_message(self, fmt, *args):
        pass

    def list_directory(self, path):
        """Never expose a browsable file listing for the game directory."""
        self.send_error(403, "Directory browsing is disabled")
        return None

    def _is_direct_game_page(self):
        from urllib.parse import unquote, urlsplit
        parsed = urlsplit(self.path)
        clean = unquote(parsed.path)
        if "ultra=1" in parsed.query.split("&"):
            return False
        if clean.startswith(("/library/", "/artwork/", "/assets/", "/api/", "/proxy/", "/e/1/")):
            return False
        if clean in ("/", "/index.html") or not clean.lower().endswith((".html", ".htm")):
            return False
        # Game frames launched by the app carry the app page as their referrer.
        # A pasted direct URL or a file-manager/browser shortcut usually does not.
        referrer = self.headers.get("Referer", "")
        if not referrer:
            return True
        ref_path = urlsplit(referrer).path
        return ref_path not in ("", "/", "/index.html")

    # ---- inject security headers on everything -----------------------------
    def end_headers(self):
        for k, v in SECURITY_HEADERS.items():
            self.send_header(k, v)
        super().end_headers()

    # ---- routing ------------------------------------------------------------
    def do_GET(self):
        path = self.path
        if self._is_direct_game_page():
            self.send_error(403, "Launch games from UBG Ultra")
        elif path.startswith("/proxy/"):
            proxy_mod.handle(self, "/proxy/")
        elif path.startswith("/api/ping"):
            self._json(200, {"pong": int(time.time() * 1000)})
        elif path.startswith("/api/anime"):
            self.api_anime()
        elif path.startswith("/api/presence/stream"):
            self.api_presence_stream()
        elif path.startswith("/api/presence"):
            self.api_presence(method="GET")
        elif path.startswith("/api/games") or path.startswith("/api/catalog"):
            self.api_games()
        elif path.startswith("/api/saves"):
            self.api_saves(method="GET")
        elif path.startswith("/api/ai/"):
            self.api_ai(method="GET")
        elif path.startswith("/api/account"):
            self.send_error(405)
        elif path.startswith("/api/chat/stream"):
            self.api_chat_stream()
        elif path.startswith("/api/chat"):
            self.api_chat()
        elif path.startswith("/api/society/state"):
            self.api_society_state()
        elif path.startswith("/api/society"):
            self.api_society()
        elif path.startswith("/api/social/leaderboard"):
            self.api_social_leaderboard()
        elif path.startswith("/api/social"):
            self.api_social(method="GET")
        elif path.startswith("/api/wall"):
            self.api_wall(method="GET")
        elif path.startswith("/e/1/"):
            self.serve_game_dir()
        else:
            super().do_GET()

    def do_POST(self):
        path = self.path
        if path.startswith("/proxy/"):
            proxy_mod.handle(self, "/proxy/")
        elif path.startswith("/api/presence"):
            self.api_presence(method="POST")
        elif path.startswith("/api/scan"):
            self.api_rescan()
        elif path.startswith("/api/saves"):
            self.api_saves(method="POST")
        elif path.startswith("/api/ai/"):
            self.api_ai(method="POST")
        elif path.startswith("/api/account"):
            self.api_account()
        elif path.startswith("/api/chat"):
            self.api_chat_post()
        elif path.startswith("/api/society"):
            self.api_society()
        elif path.startswith("/api/social"):
            self.api_social(method="POST")
        elif path.startswith("/api/wall"):
            self.api_wall(method="POST")
        else:
            self.send_error(405)

    def do_HEAD(self):
        if self.path.startswith(("/proxy/", "/api/presence", "/api/")):
            self.send_error(405)
        else:
            super().do_HEAD()

    # ---- live game catalog --------------------------------------------------
    def api_games(self):
        catalog = generate_games.write_catalog(GAMES_FOLDER)
        self._json(200, {"count": len(catalog), "games": catalog})

    # ---- Anime info (now uses AniList API + VidPlus embed, no mirror needed)
    def api_anime(self):
        self._json(200, {
            "ok": True,
            "mode": "anilist-embed",
            "anilist_api": "https://graphql.anilist.co",
            "embed_host": "https://player.vidplus.to",
        })

    def api_rescan(self):
        catalog = generate_games.write_catalog(GAMES_FOLDER)
        self._json(200, {"ok": True, "count": len(catalog), "games": catalog})

    # ---- gfiles-style directory games (optional, /e/1/<slug>/...) -----------
    def serve_game_dir(self):
        import urllib.parse
        try:
            parsed = urllib.parse.urlsplit(self.path)
            parts = [p for p in parsed.path.split("/") if p]
            if len(parts) < 3 or parts[0] != "e" or parts[1] != "1":
                self.send_error(404)
                return
            rel = "/".join(parts[2:])
            candidate = os.path.join(BASE, "gfiles-master", rel)
            if not os.path.abspath(candidate).startswith(os.path.abspath(BASE)):
                self.send_error(403)
                return
            fs_path = candidate
            if os.path.isdir(fs_path):
                idx = os.path.join(fs_path, "index.html")
                fs_path = idx if os.path.isfile(idx) else None
            if not fs_path or not os.path.isfile(fs_path):
                self.send_error(404)
                return
            self.serve_static(fs_path, is_html=fs_path.lower().endswith((".html", ".htm")))
        except Exception:
            self.send_error(404)

    def serve_static(self, fs_path, is_html=False):
        import mimetypes
        ctype = mimetypes.guess_type(fs_path)[0] or "application/octet-stream"
        try:
            with open(fs_path, "rb") as f:
                data = f.read()
        except OSError:
            self.send_error(404)
            return
        if is_html and data:
            try:
                text = data.decode("utf-8", errors="replace")
                text = re.sub(
                    r'\b(?:src|href|data-src|poster)\s*=\s*["\']/(?!/)([^"\']*)["\']',
                    lambda m: m.group(0)[:m.group(0).index("=") + 1] + '"' + m.group(1) + '"',
                    text)
                data = text.encode("utf-8")
            except Exception:
                pass
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    # ---- local assistant ----------------------------------------------------
    def api_ai(self, method):
        try:
            if method == "GET":
                self._json(200, {"model": "local", "capabilities": [
                    "chat", "recommend", "play", "proxy", "panic", "help"]})
                return
            length = int(self.headers.get("Content-Length") or 0)
            if length > 64 * 1024:
                self._json(413, {"error": "Message too large."})
                return
            body = self.rfile.read(length) if length else b""
            data = json.loads(body.decode("utf-8")) if body else {}
            msg = (data.get("message") or "").strip()
            if not msg:
                self._json(400, {"error": "Missing message."})
                return
            self._json(200, self.ai_think(msg))
        except Exception as e:
            self._json(500, {"error": str(e)})

    def ai_think(self, msg):
        import random as rnd
        low = msg.lower()
        lib = generate_games.build_catalog(GAMES_FOLDER)

        def clean(n):
            n = re.sub(r"\.(html|htm)$", "", str(n or ""))
            n = re.sub(r"[_-]+", " ", n)
            n = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", n)
            return re.sub(r"[^a-z0-9 ]", "", n.lower()).strip()

        m = re.search(r"(?:play|launch|start|run)\s+(.+?)\s*$", low) or re.search(r"^open\s+(.+?)\s*$", low)
        if m:
            term = clean(m.group(1))
            cands = [g for g in lib if term and (term in clean(g.get("name", "")) or clean(g.get("name", "")).startswith(term[:4]))]
            if cands:
                best = cands[0]
                return {"reply": "Launching %s!" % best.get("name"), "action": "play", "payload": best}
            if re.search(r"[\w-]+(\.[\w-]+)+", m.group(1)):
                url = m.group(1).strip()
                if not url.lower().startswith(("http://", "https://")):
                    url = "https://" + url
                return {"reply": "Opening %s through the proxy - you're hidden now." % url, "action": "proxy", "payload": url}
            return {"reply": "Couldn't find a game matching '%s'. Try 'play minecraft' or browse the Games tab." % m.group(1).strip()}

        if any(w in low for w in ("recommend", "suggest a game", "what should i play", "random game")):
            for cat in ["Racing", "Shooter", "Puzzle", "Sport", "Horror", "Arcade"]:
                if cat.lower() in low:
                    pick = [g for g in lib if cat in (g.get("categories") or [])]
                    if pick:
                        g = rnd.choice(pick)
                        return {"reply": "Here's a great %s game: %s. Want me to launch it?" % (cat, g.get("name")), "action": "suggest", "payload": g}
            if lib:
                g = rnd.choice(lib)
                return {"reply": "How about %s? Say 'play %s' to launch it." % (g.get("name"), g.get("name")), "action": "suggest", "payload": g}

        if "how many" in low or "count" in low:
            return {"reply": "There are %d games in the UBG ULTRA library right now." % len(lib)}

        m = re.search(r"(?:proxy|browse|go to|open site|unblock|search)\s+(.+?)\s*$", low)
        if m and not any(w in low for w in ("play ", "game")):
            url = m.group(1).strip()
            if not url.lower().startswith(("http://", "https://")):
                url = "https://" + url
            return {"reply": "Opening %s through the proxy - you're hidden now." % url, "action": "proxy", "payload": url}

        if any(w in low for w in ("panic", "hide me", "teacher coming", "emergency")):
            return {"reply": "Panic! Sending you to your safe site now.", "action": "panic", "payload": None}

        if any(w in low for w in ("help", "hi", "hello", "hey", "features", "what can you")):
            return {"reply": ("I'm UBG ULTRA's assistant. Try:\n"
                              "  'play slope' — launch a game\n"
                              "  'recommend racing' — pick a game\n"
                              "  'open youtube.com' — proxy a site\n"
                              "  'panic' — quick safe exit\n"
                              "  'how many games' — library size")}

        return {"reply": "I can help you find games and stay hidden. Say 'help' to see what I can do."}

    # ---- accounts -----------------------------------------------------------
    def api_account(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length > 4096:
                self._json(413, {"error": "Payload too large."})
                return
            body = self.rfile.read(length) if length else b""
            data = json.loads(body.decode("utf-8")) if body else {}
            action = (data.get("action") or "").strip()
            if action == "create":
                name = safe_user(data.get("name", ""))[:24] or "Player"
                with ACCOUNTS_LOCK:
                    code = new_account_code()
                    if not code:
                        self._json(500, {"error": "Couldn't allocate a code."})
                        return
                    ACCOUNTS[code] = {"name": name, "created": int(time.time())}
                save_accounts()
                self._json(200, {"ok": True, "code": code, "name": name, "token": account_token(code)})
            elif action == "signin":
                code = safe_user(data.get("code", ""))
                with ACCOUNTS_LOCK:
                    rec = ACCOUNTS.get(code)
                if not rec:
                    self._json(404, {"error": "Unknown code."})
                    return
                self._json(200, {"ok": True, "code": code, "name": rec.get("name", "Player"), "token": account_token(code)})
            elif action == "rename":
                code = safe_user(data.get("code", ""))
                name = safe_user(data.get("name", ""))[:24] or "Player"
                with ACCOUNTS_LOCK:
                    rec = ACCOUNTS.get(code)
                    if not rec:
                        self._json(404, {"error": "Unknown code."})
                        return
                    rec["name"] = name
                save_accounts()
                self._json(200, {"ok": True, "name": name})
            else:
                self._json(400, {"error": "action must be create, signin or rename."})
        except Exception as e:
            self._json(500, {"error": str(e)})

    # ---- cloud saves --------------------------------------------------------
    def api_saves(self, method):
        try:
            qs = {}
            if "?" in self.path:
                from urllib.parse import parse_qs
                qs = {k: v[0] for k, v in parse_qs(self.path.split("?", 1)[1]).items()}
            user = safe_user(qs.get("user", ""))
            token = qs.get("token", "")
            if not user or not token:
                self._json(400, {"error": "user and token are required."})
                return
            os.makedirs(DATA_DIR, exist_ok=True)
            path = os.path.join(DATA_DIR, user + ".json")
            meta_path = os.path.join(DATA_DIR, user + ".meta")

            meta = {}
            if os.path.isfile(meta_path):
                try:
                    meta = json.load(open(meta_path, encoding="utf-8"))
                except Exception:
                    meta = {}
            expected = meta.get("token", "")
            if expected and not hmac.compare_digest(str(expected), str(token)):
                self._json(403, {"error": "Wrong account token."})
                return

            if method == "GET":
                if not os.path.isfile(path):
                    self._json(200, {"saves": {}, "created": 0})
                    return
                payload = json.load(open(path, encoding="utf-8"))
                self._json(200, {"saves": payload, "created": meta.get("created", 0)})
                return

            length = int(self.headers.get("Content-Length") or 0)
            if length > 8 * 1024 * 1024:
                self._json(413, {"error": "Save payload too large."})
                return
            body = self.rfile.read(length) if length else b""
            data = json.loads(body.decode("utf-8")) if body else {}
            if not expected:
                meta = {"token": token, "created": int(time.time())}
            meta["updated"] = int(time.time())
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f)
            self._json(200, {"ok": True, "updated": meta["updated"]})
        except Exception as e:
            self._json(500, {"error": str(e)})

    # ---- chat ---------------------------------------------------------------
    def api_chat(self):
        from urllib.parse import parse_qs
        qs = {}
        if "?" in self.path:
            qs = {k: v[0] for k, v in parse_qs(self.path.split("?", 1)[1]).items()}
        try:
            since = int(qs.get("since", "0") or 0)
        except ValueError:
            since = 0
        channel = (qs.get("channel") or "main")[:24] or "main"
        with CHAT_LOCK:
            msgs = [m for m in CHAT_MSGS
                    if m["id"] > since and m.get("channel", "main") == channel]
        self._json(200, {"messages": msgs, "online": len(CHAT_SUBS)})

    def api_chat_post(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length > 4096:
                self._json(413, {"error": "Message too large."})
                return
            body = self.rfile.read(length) if length else b""
            data = json.loads(body.decode("utf-8")) if body else {}
            user = safe_user(data.get("user", "")) or "Guest"
            text = (data.get("text") or "").strip()[:500]
            channel = (data.get("channel") or "main")[:24] or "main"
            if not text:
                self._json(400, {"error": "Message is empty."})
                return
            with CHAT_LOCK:
                msg = {"id": CHAT_NEXT[0], "channel": channel,
                       "user": user, "text": text, "t": int(time.time())}
                CHAT_NEXT[0] += 1
                CHAT_MSGS.append(msg)
                if len(CHAT_MSGS) > CHAT_MAX:
                    del CHAT_MSGS[:len(CHAT_MSGS) - CHAT_MAX]
            save_chat()
            chat_broadcast({"type": "message", "message": msg,
                            "online": len(CHAT_SUBS), "channel": channel})
            self._json(200, {"ok": True, "id": msg["id"]})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def api_chat_stream(self):
        import queue
        q = queue.Queue(maxsize=200)
        with CHAT_LOCK:
            CHAT_SUBS.add(q)
            initial = list(CHAT_MSGS)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        channels = {}
        for ch in sorted({m.get("channel", "main") for m in initial}):
            channels[ch] = [m for m in initial if m.get("channel", "main") == ch]
        try:
            self.wfile.write(("data: %s\n\n" % json.dumps(
                {"type": "init", "channels": channels, "online": len(CHAT_SUBS)})).encode("utf-8"))
            self.wfile.flush()
            while True:
                try:
                    event = q.get(timeout=15)
                except queue.Empty:
                    event = ": ping\n\n"
                try:
                    self.wfile.write(event.encode("utf-8"))
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    break
        finally:
            with CHAT_LOCK:
                CHAT_SUBS.discard(q)

    # ---- live presence (who is online right now) ----------------------------
    def api_presence(self, method):
        try:
            qs = {}
            if "?" in self.path:
                from urllib.parse import parse_qs
                qs = {k: v[0] for k, v in parse_qs(self.path.split("?", 1)[1]).items()}
            if method == "GET":
                prune_presence()
                self._json(200, presence_summary())
                return
            length = int(self.headers.get("Content-Length") or 0)
            if length > 4096:
                self._json(413, {"error": "Payload too large."})
                return
            body = self.rfile.read(length) if length else b""
            data = json.loads(body.decode("utf-8")) if body else {}
            action = (data.get("action") or "").strip()
            if action == "join":
                sid = str(data.get("sid") or "")[:64] or None
                touch_presence(data.get("user", ""), sid, data.get("game"))
                self._json(200, presence_summary())
            elif action == "typing":
                set_typing(data.get("user", ""), data.get("typing"))
                self._json(200, {"ok": True})
            elif action == "leave":
                # explicit leave is a no-op; staleness handles the rest
                self._json(200, presence_summary())
            else:
                self._json(400, {"error": "action must be join, typing or leave."})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def api_presence_stream(self):
        import queue
        q = queue.Queue(maxsize=200)
        with PRESENCE_LOCK:
            PRESENCE_SUBS.add(q)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            self.wfile.write(("data: %s\n\n" % json.dumps(
                {"type": "presence", **presence_summary()})).encode("utf-8"))
            self.wfile.flush()
            while True:
                try:
                    event = q.get(timeout=15)
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    continue
                try:
                    self.wfile.write(event.encode("utf-8"))
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    break
        finally:
            with PRESENCE_LOCK:
                PRESENCE_SUBS.discard(q)

    # ---- Society Ultra (shared 3D sandbox world) ----------------------------
    def api_society_state(self):
        self._json(200, society_state())

    def api_society(self):
        global SOCIETY_OBSTACLES
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length > 8192:
                self._json(413, {"error": "Payload too large."})
                return
            body = self.rfile.read(length) if length else b""
            data = json.loads(body.decode("utf-8")) if body else {}
            action = (data.get("action") or "").strip()
            sid = str(data.get("sid") or "")[:64] or None
            name = safe_user(data.get("name", ""))[:24] or "Guest"
            if action == "join":
                if not sid:
                    self._json(400, {"error": "sid required."})
                    return
                with SOCIETY_LOCK:
                    rec = SOCIETY_PLAYERS.setdefault(sid, {"name": name})
                    rec.update({
                        "name": name,
                        "x": float(data.get("x", rec.get("x", 0))),
                        "y": float(data.get("y", rec.get("y", 0))),
                        "z": float(data.get("z", rec.get("z", 0))),
                        "rot": float(data.get("rot", rec.get("rot", 0))),
                        "app": sanitize_app(data.get("app")),
                        "ts": time.time(),
                    })
                self._json(200, society_state())
            elif action == "pos":
                if not sid:
                    self._json(400, {"error": "sid required."})
                    return
                with SOCIETY_LOCK:
                    rec = SOCIETY_PLAYERS.get(sid)
                    if rec:
                        rec.update({
                            "name": name,
                            "x": float(data.get("x", rec.get("x", 0))),
                            "y": float(data.get("y", rec.get("y", 0))),
                            "z": float(data.get("z", rec.get("z", 0))),
                            "rot": float(data.get("rot", rec.get("rot", 0))),
                            "ts": time.time(),
                        })
                        if "emote" in data and data.get("emote"):
                            rec["emote"] = str(data["emote"])[:32]
                            rec["emoteUntil"] = time.time() + 3.0
                        elif "emote" in data and not data.get("emote"):
                            rec["emote"] = ""
                self._json(200, society_state())
            elif action == "leave":
                with SOCIETY_LOCK:
                    SOCIETY_PLAYERS.pop(sid, None)
                self._json(200, {"ok": True})
            elif action == "obstacle":
                op = data.get("op")
                valid = False
                with SOCIETY_LOCK:
                    if op == "add":
                        SOCIETY_OBSTACLES.append({
                            "id": SOCIETY_NEXT[0],
                            "x": float(data.get("x", 0)),
                            "y": float(data.get("y", 0)),
                            "z": float(data.get("z", 0)),
                            "w": float(data.get("w", 2)),
                            "h": float(data.get("h", 2)),
                            "d": float(data.get("d", 2)),
                            "color": str(data.get("color", "#8a6cff"))[:16],
                        })
                        SOCIETY_NEXT[0] += 1
                        valid = True
                        social_add_block(name)
                    elif op == "del":
                        try:
                            obid = int(data.get("id", -1))
                        except (TypeError, ValueError):
                            obid = -1
                        before = len(SOCIETY_OBSTACLES)
                        SOCIETY_OBSTACLES = [o for o in SOCIETY_OBSTACLES if o.get("id") != obid]
                        valid = before != len(SOCIETY_OBSTACLES)
                if not valid:
                    self._json(400, {"error": "op must be add or del."})
                    return
                save_society()
                self._json(200, society_state())
            else:
                self._json(400, {"error": "action must be join, pos, leave or obstacle."})
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        except Exception as e:
            try:
                self._json(500, {"error": str(e)})
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                pass

    def api_social(self, method):
        import urllib.parse
        try:
            if method == "GET":
                qs = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                user = (qs.get("user") or ["Guest"])[0]
                self._json(200, social_public(user))
                return
            length = int(self.headers.get("Content-Length") or 0)
            if length > 8192:
                self._json(413, {"error": "Payload too large."})
                return
            body = self.rfile.read(length) if length else b""
            data = json.loads(body.decode("utf-8")) if body else {}
            user = safe_user(data.get("user", ""))[:24] or "Guest"
            action = (data.get("action") or "").strip()
            if action == "play":
                profile, new = social_add_play(user, data.get("game"), data.get("secs"))
                self._json(200, {"ok": True, "coins": profile.get("coins", 0), "new": new})
            elif action == "claim":
                profile, new, claimed = social_claim_daily(user)
                self._json(200, {"ok": True, "claimed": claimed,
                                 "coins": profile.get("coins", 0), "new": new})
            elif action == "block":
                profile, new = social_add_block(user)
                self._json(200, {"ok": True, "blocks": profile.get("blocks", 0),
                                 "coins": profile.get("coins", 0), "new": new})
            elif action == "parkour":
                profile, new = social_parkour(user, data.get("time"))
                self._json(200, {"ok": True, "pb": profile.get("parkour", 0), "new": new})
            elif action == "friend":
                profile, new = social_friend(user, data.get("op"), data.get("name"))
                self._json(200, {"ok": True, "friends": profile.get("friends", []), "new": new})
            else:
                self._json(400, {"error": "action must be play, claim, block, parkour or friend."})
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        except Exception as e:
            try:
                self._json(500, {"error": str(e)})
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                pass

    def api_social_leaderboard(self):
        import urllib.parse
        qs = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        kind = (qs.get("kind") or ["coins"])[0]
        self._json(200, {"kind": kind, "rows": social_leaderboard(kind)})

    def api_wall(self, method):
        import urllib.parse
        try:
            if method == "GET":
                self._json(200, {"messages": list(reversed(WALL_MSGS[-100:]))})
                return
            length = int(self.headers.get("Content-Length") or 0)
            if length > 8192:
                self._json(413, {"error": "Payload too large."})
                return
            body = self.rfile.read(length) if length else b""
            data = json.loads(body.decode("utf-8")) if body else {}
            user = safe_user(data.get("user", ""))[:24] or "Guest"
            msg, new = wall_post(user, data.get("text"))
            if not msg:
                self._json(400, {"error": "Message empty."})
                return
            self._json(200, {"ok": True, "message": msg, "new": new})
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        except Exception as e:
            try:
                self._json(500, {"error": str(e)})
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                pass

    def _json(self, status, payload):
        data = json.dumps(payload).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass


def ensure_catalog():
    """Regenerate games.json if missing or stale (newer game files added)."""
    json_path = os.path.join(GAMES_FOLDER, "assets", "js", "games.json")
    if not os.path.isfile(json_path):
        generate_games.write_catalog(GAMES_FOLDER)
        return
    try:
        newest_game = 0.0
        for name in os.listdir(GAMES_FOLDER):
            if name.lower().endswith((".html", ".htm")) and name.lower() not in ("index.html",):
                newest_game = max(newest_game, os.path.getmtime(os.path.join(GAMES_FOLDER, name)))
        if os.path.getmtime(json_path) < newest_game:
            generate_games.write_catalog(GAMES_FOLDER)
    except Exception:
        pass


class HubServer(http.server.ThreadingHTTPServer):
    request_queue_size = 512


def main():
    if not os.path.isdir(GAMES_FOLDER):
        print("=" * 60)
        print("  ERROR: 'games' folder not found!")
        print(f"  Expected: {GAMES_FOLDER}")
        print("=" * 60)
        input("\nPress Enter to close...")
        return

    if not os.path.isfile(os.path.join(GAMES_FOLDER, "index.html")):
        print("=" * 60)
        print("  ERROR: index.html not found inside the 'games' folder!")
        print(f"  Expected: {os.path.join(GAMES_FOLDER, 'index.html')}")
        print("=" * 60)
        input("\nPress Enter to close...")
        return

    ensure_catalog()
    load_chat()
    load_accounts()
    load_presence()
    load_society()
    load_social()
    load_wall()

    def prune_loop():
        while True:
            time.sleep(10)
            try:
                prune_presence()
            except Exception:
                pass
            try:
                prune_society()
            except Exception:
                pass

    threading.Thread(target=prune_loop, daemon=True).start()

    PORT = None
    for try_port in [8080, 8081, 8082, 3000, 4000]:
        try:
            test = socketserver.TCPServer(("", try_port), Handler)
            test.server_close()
            PORT = try_port
            break
        except OSError:
            continue

    if PORT is None:
        print("ERROR: No available ports (tried 8080, 8081, 8082, 3000, 4000).")
        input("\nPress Enter to close...")
        return

    def open_browser():
        time.sleep(0.8)
        webbrowser.open(f"http://localhost:{PORT}/index.html")

    print()
    print("=" * 60)
    print("  UBG Ultra is running!")
    print(f"  Open this in your browser: http://localhost:{PORT}/index.html")
    ip = lan_ip()
    if ip and not ip.startswith("127."):
        print(f"  Share with friends on Wi-Fi: http://{ip}:{PORT}/index.html")
    print()
    print("  Proxy:    /proxy/<base64url>")
    print("  Anime:    AniList API + VidPlus embed (client-side)")
    print("  Cloud:    /api/saves?user=<name>&token=<hash>")
    print("  Library:  /api/games  (auto-registers new game files)")
    print("  Chat:     /api/chat  (live, multi-user via SSE)")
    print("  Presence: /api/presence  (live 'who is online' + SSE stream)")
    print("  Society:  /api/society  (Society Ultra shared world sync)")
    print()
    print("  Keep this window open while playing.")
    print("  Press Ctrl+C to stop the server.")
    print("=" * 60)
    print()

    threading.Thread(target=open_browser, daemon=True).start()

    with HubServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nServer stopped. Goodbye!")
    except Exception:
        # Double-clicking a .py file can close its console before an error is
        # readable. Keep a persistent copy of the traceback beside the server.
        error_log = os.path.join(BASE, "startup-error.log")
        with open(error_log, "a", encoding="utf-8") as log:
            log.write("\n" + "=" * 60 + "\n")
            log.write(time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
            traceback.print_exc(file=log)
        print()
        print("=" * 60)
        print(f"  Error log: {error_log}")
        print("  UNEXPECTED ERROR — please send this to whoever made the hub:")
        print("=" * 60)
        traceback.print_exc()
        print("=" * 60)
        input("\nPress Enter to close...")
