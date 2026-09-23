# ── KakaoTranslate Configuration ──────────────────────────────────────────
#
# Tip: put your personal values (CHAT_NAME, SELF_CHAT_TITLE, …) in a file
# called config_local.py next to this one. It overrides anything here and is
# ignored by git, so `git pull` never conflicts with your settings.

# Name of the KakaoTalk group chat to monitor — the exact title of its window.
# Open the chat as its own window (double-click it in KakaoTalk).
CHAT_NAME = ""

# How often to scan for new messages (seconds) — v1 and v2
POLL_INTERVAL = 5

# Title of your self-chat pop-out window.
# Open "My Chatroom" in KakaoTalk, pop it out, and copy the exact text from
# the window's title bar (usually your KakaoTalk display name on the English app).
SELF_CHAT_TITLE = ""

# Pixels from the bottom of the self-chat window to click the input box (v1, v2).
# Increase this if clicks land outside the input field.
INPUT_BOX_Y_OFFSET = 50

# ── Translation (all versions) ────────────────────────────────────────────
# "nllb"  – Meta NLLB-200: much better on casual Korean. One-time ~2.5 GB
#           download, uses ~2.5 GB RAM. Falls back to Argos if unavailable.
# "argos" – Argos Translate: small (~150 MB) and light, lower quality.
TRANSLATOR = "nllb"

# ── DMs (v2, v3) ──────────────────────────────────────────────────────────
# True: one DM per check containing every new message. False: one DM each.
BATCH_DMS = True
# Also translate messages you send yourself.
INCLUDE_OWN_MESSAGES = False

# ── v2 (screen OCR) ───────────────────────────────────────────────────────
# "auto" (Windows OCR if the Korean OCR language is installed, else easyocr),
# "windows", or "easyocr".
OCR_ENGINE = "auto"
# Height in pixels of the chat header (title + member count). None = detect
# automatically from the chat title. Only set this if detection fails.
HEADER_HEIGHT = None

# ── v3 (direct window access) ─────────────────────────────────────────────
POLL_INTERVAL_V3 = 3
# "auto" detects on the first DM whether window messages work (no focus
# change); otherwise it types into the window and restores focus afterwards.
# Force with "message" or "keyboard".
SEND_METHOD_V3 = "auto"
# Put back whatever was on the clipboard after each read.
RESTORE_CLIPBOARD = True

# ── Auto-start ────────────────────────────────────────────────────────────
# Which version run.bat / Task Scheduler starts: 1, 2 or 3.
AUTOSTART_VERSION = 1

# ──────────────────────────────────────────────────────────────────────────

try:
    from config_local import *  # noqa: F401,F403
except ImportError:
    pass
