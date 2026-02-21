#!/usr/bin/env python3
"""
PiCar-X "Okay Robot" — Keyboard Control Module
================================================
Provides real-time keyboard control alongside voice commands.

Two input backends:
  1. **TTY mode** — raw terminal input via tty/termios (SSH, interactive shell)
  2. **evdev mode** — reads /dev/input directly (systemd service, no TTY needed)

The module auto-selects the best backend:
  - If a TTY is detected → uses TTY mode
  - If no TTY but evdev is available → uses evdev mode (reads physical keyboard)
  - If neither works → keyboard control is disabled (voice-only)

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
# ESCAPE SEQUENCE CONSTANTS (TTY mode)
# ─────────────────────────────────────────────────────────────
KEY_UP    = "\x1b[A"
KEY_DOWN  = "\x1b[B"
KEY_RIGHT = "\x1b[C"
KEY_LEFT  = "\x1b[D"
KEY_ESC   = "\x1b"
KEY_SPACE = " "

# ─────────────────────────────────────────────────────────────
# KEY → ACTION MAPPING (TTY mode — escape sequences & chars)
# ─────────────────────────────────────────────────────────────
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

# ─────────────────────────────────────────────────────────────
# EVDEV KEY CODE → ACTION MAPPING (systemd / no-TTY mode)
# ─────────────────────────────────────────────────────────────
# Linux input event key codes (see linux/input-event-codes.h)
EVDEV_KEY_MAP = {
    # Movement — arrow keys
    103: ("forward",       "↑  Forward"),        # KEY_UP
    108: ("backward",      "↓  Backward"),       # KEY_DOWN
    105: ("turn_left",     "←  Turn Left"),      # KEY_LEFT
    106: ("turn_right",    "→  Turn Right"),      # KEY_RIGHT
    57:  ("stop",          "⎵  Stop"),            # KEY_SPACE

    # Camera
    17:  ("look_up",       "W  Look Up"),         # KEY_W
    30:  ("look_left",     "A  Look Left"),       # KEY_A
    45:  ("look_down",     "X  Look Down"),       # KEY_X
    18:  ("look_right",    "E  Look Right"),      # KEY_E
    46:  ("look_center",   "C  Center Camera"),   # KEY_C

    # Gestures & Actions
    32:  ("dance",         "D  Dance"),           # KEY_D
    31:  ("shake_head",    "S  Shake Head"),      # KEY_S
    49:  ("nod",           "N  Nod"),             # KEY_N
    47:  ("wave_hands",    "V  Wave Hands"),      # KEY_V
    48:  ("celebrate",     "B  Celebrate"),       # KEY_B
    34:  ("act_cute",      "G  Act Cute"),        # KEY_G
    20:  ("think",         "T  Think"),           # KEY_T
    25:  ("patrol",        "P  Patrol"),          # KEY_P
    24:  ("spin_around",   "O  Spin Around"),     # KEY_O
    36:  ("twist_body",    "J  Twist Body"),      # KEY_J
    37:  ("depressed",     "K  Depressed"),       # KEY_K
    19:  ("reset",         "R  Reset Position"),  # KEY_R

    # Sound
    35:  ("horn",          "H  Horn / Honk"),     # KEY_H

    # Modes
    2:   ("mode_line",     "1  Line Tracking"),   # KEY_1
    3:   ("mode_obstacle", "2  Obstacle Avoid"),  # KEY_2
    11:  ("mode_cancel",   "0  Cancel Mode"),     # KEY_0

    # System
    16:  ("quit",          "Q  Quit"),            # KEY_Q
    1:   ("quit",          "Esc  Quit"),          # KEY_ESC
}


def print_help():
    """Print keyboard control help to console."""
    msg = """
╔══════════════════════════════════════════════╗
║       KEYBOARD CONTROLS  (Okay Robot)       ║
╠══════════════════════════════════════════════╣
║  MOVEMENT                                   ║
║    ↑  Up Arrow ........ Forward              ║
║    ↓  Down Arrow ...... Backward             ║
║    ←  Left Arrow ...... Turn Left            ║
║    →  Right Arrow ..... Turn Right           ║
║    Space .............. Stop                 ║
║                                              ║
║  CAMERA                                      ║
║    W .................. Look Up               ║
║    A .................. Look Left             ║
║    X .................. Look Down             ║
║    E .................. Look Right            ║
║    C .................. Center Camera         ║
║                                              ║
║  GESTURES & ACTIONS                          ║
║    D .................. Dance                 ║
║    S .................. Shake Head            ║
║    N .................. Nod                   ║
║    V .................. Wave Hands            ║
║    B .................. Celebrate             ║
║    G .................. Act Cute              ║
║    T .................. Think                 ║
║    P .................. Patrol                ║
║    O .................. Spin Around           ║
║    J .................. Twist Body            ║
║    K .................. Depressed / Sad       ║
║    R .................. Reset Position        ║
║                                              ║
║  MODES                                       ║
║    1 .................. Line Tracking         ║
║    2 .................. Obstacle Avoidance    ║
║    0 .................. Cancel Mode           ║
║                                              ║
║  SOUND                                       ║
║    H .................. Horn / Honk           ║
║                                              ║
║  SYSTEM                                      ║
║    Q / Esc ............ Quit                  ║
║    ? .................. This Help             ║
╚══════════════════════════════════════════════╝
"""
    logger.info(msg)
    print(msg)


# ═════════════════════════════════════════════════════════════
# BACKEND 1: TTY MODE (terminal / SSH)
# ═════════════════════════════════════════════════════════════

def _read_key():
    """
    Read a single keypress from stdin (Linux raw terminal mode).
    Returns the key as a string. Arrow keys return escape sequences.
    """
    import tty
    import termios

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            ch2 = sys.stdin.read(1)
            if ch2 == "[":
                ch3 = sys.stdin.read(1)
                return "\x1b[" + ch3
            return KEY_ESC
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _tty_listener(car, state, dispatch_action):
    """TTY-based keyboard listener (interactive terminal / SSH)."""
    logger.info("Keyboard control active (TTY mode). Press '?' for help.")
    print_help()

    while state.running:
        try:
            key = _read_key()
            if key is None:
                time.sleep(0.1)
                continue

            key_lower = key.lower() if len(key) == 1 else key

            # Quit
            if key_lower in ("q", KEY_ESC):
                logger.info("Keyboard: Quit requested.")
                state.running = False
                os.kill(os.getpid(), __import__('signal').SIGTERM)
                break

            # Help
            if key_lower == "?":
                print_help()
                continue

            # Lookup
            entry = KEY_MAP.get(key_lower) or KEY_MAP.get(key)
            if not entry:
                continue

            action_name, label = entry
            dispatch_action(action_name, label)

        except Exception as e:
            if "I/O" in str(e) or "Errno 5" in str(e) or "Input/output" in str(e):
                logger.info("Keyboard: Terminal disconnected. TTY mode disabled.")
                break
            logger.error("Keyboard (TTY) error: %s", e)
            time.sleep(0.5)

    logger.info("TTY keyboard listener stopped.")


# ═════════════════════════════════════════════════════════════
# BACKEND 2: EVDEV MODE (systemd service / no TTY)
# ═════════════════════════════════════════════════════════════

def _find_keyboard_device():
    """
    Find a keyboard input device in /dev/input/ using evdev.
    Returns the device path or None.
    """
    try:
        import evdev
    except ImportError:
        return None

    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for device in devices:
        capabilities = device.capabilities(verbose=True)
        # Look for devices that have EV_KEY with typical keyboard keys
        for cap_type, events in capabilities.items():
            if cap_type[0] == "EV_KEY":
                # Check for common keyboard keys (KEY_A=30, KEY_SPACE=57, KEY_UP=103)
                event_codes = [e[0][1] if isinstance(e[0], tuple) else e[0] for e in events]
                if 30 in event_codes and 57 in event_codes:
                    logger.info("Keyboard device found: %s (%s)", device.path, device.name)
                    return device.path
    return None


def _evdev_listener(car, state, dispatch_action):
    """
    evdev-based keyboard listener — reads directly from /dev/input/.
    Works under systemd without any TTY. Requires root and the `evdev` package.
    """
    try:
        import evdev
    except ImportError:
        logger.warning("Keyboard (evdev): python3-evdev not installed. "
                       "Install with: sudo pip3 install evdev")
        return

    dev_path = _find_keyboard_device()
    if not dev_path:
        logger.info("Keyboard (evdev): No keyboard device found in /dev/input/. "
                     "Plug in a USB keyboard to use keyboard control.")
        # Keep checking periodically for a keyboard to be plugged in
        _evdev_hotplug_loop(state, dispatch_action)
        return

    logger.info("Keyboard control active (evdev mode: %s).", dev_path)

    try:
        import evdev
        device = evdev.InputDevice(dev_path)
        # Don't grab exclusively — let other processes also read
        logger.info("Listening for keyboard events on %s (%s)...", device.path, device.name)

        for event in device.read_loop():
            if not state.running:
                break

            # Only handle key-down events (value=1), skip repeats (value=2)
            if event.type != evdev.ecodes.EV_KEY or event.value != 1:
                continue

            entry = EVDEV_KEY_MAP.get(event.code)
            if not entry:
                continue

            action_name, label = entry

            # Quit
            if action_name == "quit":
                logger.info("Keyboard (evdev): Quit requested.")
                state.running = False
                os.kill(os.getpid(), __import__('signal').SIGTERM)
                break

            dispatch_action(action_name, label)

    except OSError as e:
        logger.warning("Keyboard (evdev) device error: %s. Device may have been unplugged.", e)
        # Try hotplug loop to wait for reconnection
        if state.running:
            _evdev_hotplug_loop(state, dispatch_action)
    except Exception as e:
        logger.error("Keyboard (evdev) error: %s", e)

    logger.info("evdev keyboard listener stopped.")


def _evdev_hotplug_loop(state, dispatch_action):
    """
    Periodically check for a keyboard device to appear (USB hotplug).
    When found, start the evdev listener for it.
    """
    logger.info("Keyboard (evdev): Waiting for USB keyboard to be plugged in...")
    while state.running:
        time.sleep(5)
        dev_path = _find_keyboard_device()
        if dev_path:
            logger.info("Keyboard (evdev): Device detected! Starting listener.")
            # Import here to avoid top-level import issues
            import evdev
            try:
                device = evdev.InputDevice(dev_path)
                for event in device.read_loop():
                    if not state.running:
                        return

                    if event.type != evdev.ecodes.EV_KEY or event.value != 1:
                        continue

                    entry = EVDEV_KEY_MAP.get(event.code)
                    if not entry:
                        continue

                    action_name, label = entry
                    if action_name == "quit":
                        logger.info("Keyboard (evdev): Quit requested.")
                        state.running = False
                        os.kill(os.getpid(), __import__('signal').SIGTERM)
                        return

                    dispatch_action(action_name, label)

            except OSError:
                logger.warning("Keyboard (evdev): Device disconnected. Waiting for reconnect...")
                continue
            except Exception as e:
                logger.error("Keyboard (evdev) hotplug error: %s", e)
                continue


# ═════════════════════════════════════════════════════════════
# COMMON DISPATCH LOGIC
# ═════════════════════════════════════════════════════════════

def _make_dispatcher(car, state, play_sound_func, music,
                     start_line_tracking, start_obstacle_avoidance):
    """
    Create a dispatch_action(action_name, label) function that executes
    the robot action. Shared between TTY and evdev backends.
    """
    from actions import ACTIONS_DICT

    def dispatch_action(action_name, label):
        logger.info("Keyboard: [%s] → %s", label, action_name)

        # Mode commands
        if action_name == "mode_line":
            with state.lock:
                state.autonomous_mode = "line_track"
            start_line_tracking()
            logger.info("[MODE] Line Tracking started. Press 0 to cancel.")
            return

        if action_name == "mode_obstacle":
            with state.lock:
                state.autonomous_mode = "obstacle_avoid"
            start_obstacle_avoidance()
            logger.info("[MODE] Obstacle Avoidance started. Press 0 to cancel.")
            return

        if action_name == "mode_cancel":
            with state.lock:
                state.autonomous_mode = None
            car.stop()
            car.set_dir_servo_angle(0)
            logger.info("[MODE] Autonomous mode cancelled.")
            return

        # Horn
        if action_name == "horn":
            from config import HORN_SOUND
            play_sound_func(music, HORN_SOUND)
            logger.info("[SOUND] Honk!")
            return

        # Action from ACTIONS_DICT
        lookup_name = action_name.replace("_", " ")
        if lookup_name in ACTIONS_DICT:
            logger.info("[ACTION] %s", label)
            ACTIONS_DICT[lookup_name](car)
        elif action_name in ACTIONS_DICT:
            logger.info("[ACTION] %s", label)
            ACTIONS_DICT[action_name](car)
        else:
            logger.warning("[UNKNOWN] %s", action_name)

    return dispatch_action


# ═════════════════════════════════════════════════════════════
# PUBLIC API
# ═════════════════════════════════════════════════════════════

def _has_tty():
    """Check if stdin is a real terminal (TTY)."""
    try:
        return os.isatty(sys.stdin.fileno())
    except Exception:
        return False


def _has_evdev():
    """Check if evdev is available."""
    try:
        import evdev
        return True
    except ImportError:
        return False


def keyboard_listener(car, state, tts_func, play_sound_func, music,
                      start_line_tracking, start_obstacle_avoidance):
    """
    Main keyboard listener — auto-selects TTY or evdev backend.
    """
    dispatch = _make_dispatcher(car, state, play_sound_func, music,
                                start_line_tracking, start_obstacle_avoidance)

    if _has_tty():
        _tty_listener(car, state, dispatch)
    elif _has_evdev():
        logger.info("No TTY detected — using evdev for keyboard input (systemd mode).")
        _evdev_listener(car, state, dispatch)
    else:
        logger.info("Keyboard control: No TTY and evdev not installed. "
                     "Keyboard input disabled. To enable under systemd, "
                     "install evdev: sudo pip3 install evdev")


def start_keyboard_thread(car, state, tts_func, play_sound_func, music,
                          start_line_tracking, start_obstacle_avoidance):
    """
    Start the keyboard listener in a daemon thread.
    Auto-selects TTY or evdev backend. Safe to call in any environment.
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
