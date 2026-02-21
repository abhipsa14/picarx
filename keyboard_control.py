#!/usr/bin/env python3
"""
PiCar-X "Okay Robot" — Keyboard Control Module
================================================
Provides real-time keyboard control alongside voice commands.
Uses Linux terminal raw input (tty/termios) so it works over SSH
and also under systemd when a TTY is available.

Key Bindings:
  ───── Movement ─────
  ↑  (Up Arrow)        Forward
  ↓  (Down Arrow)      Backward
  ←  (Left Arrow)      Turn Left
  →  (Right Arrow)     Turn Right
  Space                Stop

  ───── Camera ─────
  w                    Look Up
  a                    Look Left (camera pan)
  x                    Look Down
  e                    Look Right (camera pan)
  c                    Center Camera

  ───── Gestures & Actions ─────
  d                    Dance
  s                    Shake Head
  n                    Nod
  v                    Wave Hands
  b                    Celebrate
  g                    Act Cute
  t                    Think
  p                    Patrol
  o                    Spin Around
  j                    Twist Body
  k                    Depressed / Sad
  r                    Reset Position

  ───── Modes ─────
  1                    Line Tracking Mode
  2                    Obstacle Avoidance Mode
  0                    Cancel Autonomous Mode

  ───── Sound ─────
  h                    Horn / Honk

  ───── System ─────
  q / Esc              Quit
  ?                    Show Help
"""

import sys
import os
import threading
import logging
import time

logger = logging.getLogger("okay-robot")

# ─────────────────────────────────────────────────────────────
# ESCAPE SEQUENCE CONSTANTS
# ─────────────────────────────────────────────────────────────
KEY_UP    = "\x1b[A"
KEY_DOWN  = "\x1b[B"
KEY_RIGHT = "\x1b[C"
KEY_LEFT  = "\x1b[D"
KEY_ESC   = "\x1b"
KEY_SPACE = " "

# ─────────────────────────────────────────────────────────────
# KEY → ACTION MAPPING
# ─────────────────────────────────────────────────────────────
# Each entry: key -> (action_name, display_label)
KEY_MAP = {
    # Movement
    KEY_UP:    ("forward",       "↑  Forward"),
    KEY_DOWN:  ("backward",      "↓  Backward"),
    KEY_LEFT:  ("turn_left",     "←  Turn Left"),
    KEY_RIGHT: ("turn_right",    "→  Turn Right"),
    KEY_SPACE: ("stop",          "⎵  Stop"),

    # Camera
    "w":       ("look_up",       "W  Look Up"),
    "a":       ("look_left",     "A  Look Left"),
    "x":       ("look_down",     "X  Look Down"),
    "e":       ("look_right",    "E  Look Right"),
    "c":       ("look_center",   "C  Center Camera"),

    # Gestures & Actions
    "d":       ("dance",         "D  Dance"),
    "s":       ("shake_head",    "S  Shake Head"),
    "n":       ("nod",           "N  Nod"),
    "v":       ("wave_hands",    "V  Wave Hands"),
    "b":       ("celebrate",     "B  Celebrate"),
    "g":       ("act_cute",      "G  Act Cute"),
    "t":       ("think",         "T  Think"),
    "p":       ("patrol",        "P  Patrol"),
    "o":       ("spin_around",   "O  Spin Around"),
    "j":       ("twist_body",    "J  Twist Body"),
    "k":       ("depressed",     "K  Depressed"),
    "r":       ("reset",         "R  Reset Position"),

    # Sound
    "h":       ("horn",          "H  Horn / Honk"),

    # Modes
    "1":       ("mode_line",     "1  Line Tracking Mode"),
    "2":       ("mode_obstacle", "2  Obstacle Avoidance Mode"),
    "0":       ("mode_cancel",   "0  Cancel Autonomous Mode"),

    # System
    "?":       ("help",          "?  Show Help"),
}


def print_help():
    """Print keyboard control help to console."""
    print("\n╔══════════════════════════════════════════════╗")
    print("║       KEYBOARD CONTROLS  (Okay Robot)       ║")
    print("╠══════════════════════════════════════════════╣")
    print("║  MOVEMENT                                   ║")
    print("║    ↑  Up Arrow ........ Forward              ║")
    print("║    ↓  Down Arrow ...... Backward             ║")
    print("║    ←  Left Arrow ...... Turn Left            ║")
    print("║    →  Right Arrow ..... Turn Right           ║")
    print("║    Space .............. Stop                 ║")
    print("║                                              ║")
    print("║  CAMERA                                      ║")
    print("║    W .................. Look Up               ║")
    print("║    A .................. Look Left             ║")
    print("║    X .................. Look Down             ║")
    print("║    E .................. Look Right            ║")
    print("║    C .................. Center Camera         ║")
    print("║                                              ║")
    print("║  GESTURES & ACTIONS                          ║")
    print("║    D .................. Dance                 ║")
    print("║    S .................. Shake Head            ║")
    print("║    N .................. Nod                   ║")
    print("║    V .................. Wave Hands            ║")
    print("║    B .................. Celebrate             ║")
    print("║    G .................. Act Cute              ║")
    print("║    T .................. Think                 ║")
    print("║    P .................. Patrol                ║")
    print("║    O .................. Spin Around           ║")
    print("║    J .................. Twist Body            ║")
    print("║    K .................. Depressed / Sad       ║")
    print("║    R .................. Reset Position        ║")
    print("║                                              ║")
    print("║  MODES                                       ║")
    print("║    1 .................. Line Tracking         ║")
    print("║    2 .................. Obstacle Avoidance    ║")
    print("║    0 .................. Cancel Mode           ║")
    print("║                                              ║")
    print("║  SOUND                                       ║")
    print("║    H .................. Horn / Honk           ║")
    print("║                                              ║")
    print("║  SYSTEM                                      ║")
    print("║    Q / Esc ............ Quit                  ║")
    print("║    ? .................. This Help             ║")
    print("╚══════════════════════════════════════════════╝\n")


def _read_key():
    """
    Read a single keypress from stdin (Linux raw terminal mode).
    Returns the key as a string. Arrow keys return escape sequences.
    Returns None if reading fails (no TTY available).
    """
    import tty
    import termios

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        # If escape sequence, read more chars
        if ch == "\x1b":
            ch2 = sys.stdin.read(1)
            if ch2 == "[":
                ch3 = sys.stdin.read(1)
                return "\x1b[" + ch3
            return KEY_ESC  # Plain Escape
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def keyboard_listener(car, state, tts_func, play_sound_func, music,
                      start_line_tracking, start_obstacle_avoidance):
    """
    Background thread that reads keyboard input and dispatches actions.

    Args:
        car:                   Picarx instance
        state:                 RobotState shared state
        tts_func:              say(tts, text) callable — pass as lambda
        play_sound_func:       play_sound(music, file) callable
        music:                 Music instance
        start_line_tracking:   Callable to start line tracking mode
        start_obstacle_avoidance: Callable to start obstacle avoidance mode
    """
    from actions import ACTIONS_DICT, reset_position

    # Check if we have a real TTY
    if not _has_tty():
        logger.info("Keyboard control: No TTY detected (systemd service). "
                     "Keyboard input disabled. Use voice commands or SSH to "
                     "run interactively for keyboard control.")
        return

    logger.info("Keyboard control active. Press '?' for help.")
    print_help()

    while state.running:
        try:
            key = _read_key()
            if key is None:
                time.sleep(0.1)
                continue

            key_lower = key.lower() if len(key) == 1 else key

            # ─── Quit ───
            if key_lower in ("q", KEY_ESC):
                logger.info("Keyboard: Quit requested.")
                state.running = False
                os.kill(os.getpid(), __import__('signal').SIGTERM)
                break

            # ─── Help ───
            if key_lower == "?":
                print_help()
                continue

            # ─── Lookup in KEY_MAP ───
            if key_lower not in KEY_MAP and key not in KEY_MAP:
                continue

            action_name, label = KEY_MAP.get(key_lower) or KEY_MAP.get(key)
            logger.info("Keyboard: [%s] → %s", label, action_name)

            # ── Mode commands ──
            if action_name == "mode_line":
                with state.lock:
                    state.autonomous_mode = "line_track"
                start_line_tracking()
                print("[MODE] Line Tracking started. Press 0 to cancel.")
                continue

            if action_name == "mode_obstacle":
                with state.lock:
                    state.autonomous_mode = "obstacle_avoid"
                start_obstacle_avoidance()
                print("[MODE] Obstacle Avoidance started. Press 0 to cancel.")
                continue

            if action_name == "mode_cancel":
                with state.lock:
                    state.autonomous_mode = None
                car.stop()
                car.set_dir_servo_angle(0)
                print("[MODE] Autonomous mode cancelled.")
                continue

            # ── Horn ──
            if action_name == "horn":
                from config import HORN_SOUND
                play_sound_func(music, HORN_SOUND)
                print("[SOUND] Honk!")
                continue

            # ── Action from ACTIONS_DICT ──
            # Map underscore names to space-separated for dict lookup
            lookup_name = action_name.replace("_", " ")
            if lookup_name in ACTIONS_DICT:
                print(f"[ACTION] {label}")
                ACTIONS_DICT[lookup_name](car)
            elif action_name in ACTIONS_DICT:
                print(f"[ACTION] {label}")
                ACTIONS_DICT[action_name](car)
            else:
                print(f"[UNKNOWN] {action_name}")

        except Exception as e:
            # If terminal goes away (e.g. SSH disconnect), gracefully stop
            if "I/O" in str(e) or "Errno 5" in str(e) or "Input/output" in str(e):
                logger.info("Keyboard: Terminal disconnected. Keyboard input disabled.")
                break
            logger.error("Keyboard input error: %s", e)
            time.sleep(0.5)

    logger.info("Keyboard listener stopped.")


def _has_tty():
    """Check if stdin is a real terminal (TTY)."""
    try:
        return os.isatty(sys.stdin.fileno())
    except Exception:
        return False


def start_keyboard_thread(car, state, tts_func, play_sound_func, music,
                          start_line_tracking, start_obstacle_avoidance):
    """
    Start the keyboard listener in a daemon thread.
    Safe to call even when no TTY is available — it will simply log and return.
    """
    t = threading.Thread(
        target=keyboard_listener,
        args=(car, state, tts_func, play_sound_func, music,
              start_line_tracking, start_obstacle_avoidance),
        daemon=True,
        name="keyboard-control"
    )
    t.start()
    return t
