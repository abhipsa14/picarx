#!/usr/bin/env python3
"""
PiCar-X "Okay Robot" Voice-Activated System - Configuration
============================================================
Edit this file to customize wake word, LLM, TTS/STT, and behavior.
"""

# ─────────────────────────────────────────────────────────────
# WAKE WORD SETTINGS
# ─────────────────────────────────────────────────────────────
ROBOT_NAME = "Robot"
WAKE_WORDS = ["okay robot", "ok robot", "hey robot"]
WAKE_ENABLED = True

# After this many seconds of silence in command mode, go back to sleep
COMMAND_TIMEOUT_SECONDS = 30

# ─────────────────────────────────────────────────────────────
# SPEECH-TO-TEXT (STT) — Vosk (Offline)
# ─────────────────────────────────────────────────────────────
STT_LANGUAGE = "en-us"          # Vosk language code
STT_STREAM_MODE = False         # True = streaming partial results

# ─────────────────────────────────────────────────────────────
# TEXT-TO-SPEECH (TTS) — Piper (Offline)
# ─────────────────────────────────────────────────────────────
TTS_ENGINE = "piper"            # "piper" or "espeak"
TTS_MODEL = "en_US-ryan-low"   # Piper voice model

# ─────────────────────────────────────────────────────────────
# LLM (Large Language Model) — Optional AI responses
# ─────────────────────────────────────────────────────────────
# Set LLM_ENABLED = True and provide API key to get AI-powered
# conversational responses instead of simple keyword matching.
LLM_ENABLED = False
LLM_PROVIDER = "openai"        # "openai", "gemini", "deepseek", "doubao", "qwen", "grok"
LLM_MODEL = "gpt-4o-mini"
LLM_API_KEY = ""               # Put your API key here or in secret.py

# Try to load API key from secret.py if not set above
try:
    from secret import LLM_API_KEY as _KEY
    if not LLM_API_KEY:
        LLM_API_KEY = _KEY
except ImportError:
    pass

# ─────────────────────────────────────────────────────────────
# MOVEMENT SETTINGS
# ─────────────────────────────────────────────────────────────
MOVE_SPEED = 30                 # Default motor speed (0-100)
MOVE_DURATION = 1.0             # How long each move command lasts (seconds)
TURN_ANGLE = 25                 # Steering angle for turns (degrees)
CAMERA_PAN_STEP = 30            # Camera pan step (degrees)
CAMERA_TILT_STEP = 20           # Camera tilt step (degrees)

# ─────────────────────────────────────────────────────────────
# OBSTACLE AVOIDANCE (runs as background safety check)
# ─────────────────────────────────────────────────────────────
OBSTACLE_AVOIDANCE_ENABLED = True
SAFE_DISTANCE = 40              # cm — no action needed
DANGER_DISTANCE = 20            # cm — turn away
TOO_CLOSE_DISTANCE = 10         # cm — emergency backward

# ─────────────────────────────────────────────────────────────
# CLIFF DETECTION (runs as background safety check)
# ─────────────────────────────────────────────────────────────
CLIFF_DETECTION_ENABLED = True
CLIFF_REFERENCE = [200, 200, 200]   # Grayscale threshold for cliff

# ─────────────────────────────────────────────────────────────
# LINE TRACKING MODE
# ─────────────────────────────────────────────────────────────
LINE_TRACK_SPEED = 10           # Slower speed for line tracking
LINE_TRACK_OFFSET = 20          # Steering angle offset for tracking

# ─────────────────────────────────────────────────────────────
# SOUND FILES (relative to picar-x install directory)
# ─────────────────────────────────────────────────────────────
SOUND_DIR = "/home/pi/picar-x/sounds"
MUSIC_DIR = "/home/pi/picar-x/musics"
HORN_SOUND = "car-double-horn.wav"
ENGINE_SOUND = "car-start-engine.wav"

# ─────────────────────────────────────────────────────────────
# KEYBOARD CONTROL
# ─────────────────────────────────────────────────────────────
KEYBOARD_ENABLED = True         # Enable keyboard input (auto-disables if no TTY)

# ─────────────────────────────────────────────────────────────
# SYSTEM / SERVICE
# ─────────────────────────────────────────────────────────────
LOG_FILE = "/var/log/okay-robot.log"
PID_FILE = "/var/run/okay-robot.pid"
STARTUP_GREETING = f"Hello! I am {ROBOT_NAME}. Say 'okay robot' to wake me up!"
