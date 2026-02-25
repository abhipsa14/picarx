#!/usr/bin/env python3
"""
PiCar-X "Okay Robot" — Voice-Activated Control System
======================================================
Main system that runs on the Raspberry Pi, listening for the wake word
"okay robot" and then processing voice commands to control the PiCar-X.

Features:
  - Wake word detection ("okay robot") via Vosk offline STT
  - Voice commands for movement, camera, gestures, and modes
  - Background safety: obstacle avoidance + cliff detection
  - Optional LLM integration for natural conversation
  - Text-to-speech responses via Piper or Espeak
  - Sound effects (horn, engine start)
  - Autonomous modes: line tracking, obstacle avoidance, patrol
  - Runs as a systemd service on boot

Usage:
  sudo python3 okay_robot.py
"""

import sys
import os
import time
import signal
import threading
import logging
from logging.handlers import RotatingFileHandler

# ─── Fix os.getlogin() for systemd services (no TTY) ────────
# The picarx library calls os.getlogin() which fails under systemd.
# Monkey-patch it to return a valid username instead.
_original_getlogin = os.getlogin
def _safe_getlogin():
    try:
        return _original_getlogin()
    except OSError:
        import pwd
        return pwd.getpwuid(os.getuid()).pw_name
os.getlogin = _safe_getlogin

# ─── Configuration ───────────────────────────────────────────
from config import (
    ROBOT_NAME, WAKE_WORDS, WAKE_ENABLED,
    COMMAND_TIMEOUT_SECONDS,
    STT_LANGUAGE, STT_STREAM_MODE,
    TTS_ENGINE, TTS_MODEL,
    LLM_ENABLED, LLM_PROVIDER, LLM_MODEL, LLM_API_KEY,
    MOVE_SPEED, MOVE_DURATION, TURN_ANGLE,
    CAMERA_PAN_STEP, CAMERA_TILT_STEP,
    OBSTACLE_AVOIDANCE_ENABLED, SAFE_DISTANCE, DANGER_DISTANCE, TOO_CLOSE_DISTANCE,
    CLIFF_DETECTION_ENABLED, CLIFF_REFERENCE,
    LINE_TRACK_SPEED, LINE_TRACK_OFFSET,
    SOUND_DIR, MUSIC_DIR, HORN_SOUND, ENGINE_SOUND,
    LOG_FILE, PID_FILE, STARTUP_GREETING,
    KEYBOARD_ENABLED,
)
from actions import ACTIONS_DICT, execute_actions, reset_position
from keyboard_control import start_keyboard_thread

# ─── Logging Setup ───────────────────────────────────────────
logger = logging.getLogger("okay-robot")
logger.setLevel(logging.INFO)
_fmt = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

# Console handler
_ch = logging.StreamHandler(sys.stdout)
_ch.setFormatter(_fmt)
logger.addHandler(_ch)

# File handler (only if we can write to the log path)
try:
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    _fh = RotatingFileHandler(LOG_FILE, maxBytes=2_000_000, backupCount=3)
    _fh.setFormatter(_fmt)
    logger.addHandler(_fh)
except PermissionError:
    pass


# ═════════════════════════════════════════════════════════════
# GLOBAL STATE
# ═════════════════════════════════════════════════════════════
class RobotState:
    """Thread-safe shared state for the robot."""
    def __init__(self):
        self.lock = threading.Lock()
        self.running = True           # Master shutdown flag
        self.awake = False            # True after wake word detected
        self.listening = False        # True while processing commands
        self.autonomous_mode = None   # "line_track", "obstacle_avoid", "patrol", or None
        self.last_command_time = 0
        self.too_close = False        # Ultrasonic proximity alert

state = RobotState()


# ═════════════════════════════════════════════════════════════
# HARDWARE INITIALIZATION
# ═════════════════════════════════════════════════════════════
def init_hardware():
    """Initialize PiCar-X hardware, STT, TTS, and optional LLM."""
    logger.info("Initializing PiCar-X hardware...")

    from picarx import Picarx
    car = Picarx()

    # Set cliff detection reference
    if CLIFF_DETECTION_ENABLED:
        car.set_cliff_reference(CLIFF_REFERENCE)

    logger.info("Initializing Vosk STT (language=%s)...", STT_LANGUAGE)
    from picarx.stt import Vosk
    stt = Vosk(language=STT_LANGUAGE)

    logger.info("Initializing TTS (engine=%s, model=%s)...", TTS_ENGINE, TTS_MODEL)
    tts = init_tts()

    # Optional LLM
    llm = None
    if LLM_ENABLED and LLM_API_KEY:
        llm = init_llm()

    # Music/Sound
    music = None
    try:
        from picarx.music import Music
        music = Music()
        music.music_set_volume(50)
        logger.info("Music/Sound system initialized.")
    except Exception as e:
        logger.warning("Music system not available: %s", e)

    return car, stt, tts, llm, music


def init_tts():
    """Initialize the text-to-speech engine."""
    if TTS_ENGINE == "piper":
        try:
            from picarx.tts import Piper
            tts = Piper(model=TTS_MODEL)
            logger.info("Piper TTS ready.")
            return tts
        except Exception as e:
            logger.warning("Piper TTS failed (%s), falling back to espeak.", e)

    # Fallback to espeak
    try:
        from picarx.tts import Espeak
        tts = Espeak()
        logger.info("Espeak TTS ready.")
        return tts
    except Exception as e:
        logger.warning("Espeak TTS also failed: %s", e)
        return None


def init_llm():
    """Initialize the LLM provider."""
    try:
        if LLM_PROVIDER == "openai":
            from picarx.llm import OpenAI as LLMClass
        elif LLM_PROVIDER == "gemini":
            from picarx.llm import Gemini as LLMClass
        elif LLM_PROVIDER == "deepseek":
            from picarx.llm import DeepSeek as LLMClass
        elif LLM_PROVIDER == "doubao":
            from picarx.llm import Doubao as LLMClass
        elif LLM_PROVIDER == "qwen":
            from picarx.llm import Qwen as LLMClass
        elif LLM_PROVIDER == "grok":
            from picarx.llm import Grok as LLMClass
        else:
            logger.warning("Unknown LLM provider: %s", LLM_PROVIDER)
            return None

        llm = LLMClass(api_key=LLM_API_KEY, model=LLM_MODEL)
        logger.info("LLM initialized: %s / %s", LLM_PROVIDER, LLM_MODEL)
        return llm
    except Exception as e:
        logger.warning("LLM initialization failed: %s", e)
        return None


# ═════════════════════════════════════════════════════════════
# TEXT-TO-SPEECH HELPER
# ═════════════════════════════════════════════════════════════
def say(tts, text):
    """Speak the given text."""
    if tts is None:
        logger.info("[SAY] %s", text)
        return
    try:
        logger.info("[SAY] %s", text)
        tts.say(text)
    except Exception as e:
        logger.error("TTS error: %s", e)


# ═════════════════════════════════════════════════════════════
# SOUND EFFECTS
# ═════════════════════════════════════════════════════════════
def play_sound(music, filename):
    """Play a sound effect asynchronously."""
    if music is None:
        return
    try:
        filepath = os.path.join(SOUND_DIR, filename)
        if os.path.exists(filepath):
            music.sound_play_threading(filepath)
        else:
            logger.warning("Sound file not found: %s", filepath)
    except Exception as e:
        logger.warning("Sound play error: %s", e)


# ═════════════════════════════════════════════════════════════
# SAFETY MONITOR — Background Thread
# ═════════════════════════════════════════════════════════════
def safety_monitor(car, tts, music):
    """
    Background thread that continuously monitors:
    - Ultrasonic distance (obstacle avoidance)
    - Grayscale sensors (cliff detection)
    """
    logger.info("Safety monitor started.")
    while state.running:
        try:
            # --- Obstacle Avoidance ---
            if OBSTACLE_AVOIDANCE_ENABLED:
                try:
                    distance = round(car.ultrasonic.read(), 2)
                    if distance > 0:  # Valid reading
                        if distance < TOO_CLOSE_DISTANCE:
                            with state.lock:
                                state.too_close = True
                            logger.warning("TOO CLOSE: %.1f cm — emergency backward!", distance)
                            car.set_dir_servo_angle(0)
                            car.backward(MOVE_SPEED)
                            time.sleep(0.5)
                            car.stop()
                        elif distance < DANGER_DISTANCE and state.autonomous_mode == "obstacle_avoid":
                            car.set_dir_servo_angle(30)
                            car.forward(MOVE_SPEED)
                            time.sleep(0.3)
                        else:
                            with state.lock:
                                state.too_close = False
                except Exception:
                    pass

            # --- Cliff Detection ---
            if CLIFF_DETECTION_ENABLED:
                try:
                    gm_val = car.get_grayscale_data()
                    if car.get_cliff_status(gm_val):
                        logger.warning("CLIFF detected! Backing up.")
                        car.stop()
                        car.set_dir_servo_angle(0)
                        car.backward(MOVE_SPEED)
                        time.sleep(0.6)
                        car.stop()
                except Exception:
                    pass

            time.sleep(0.1)

        except Exception as e:
            logger.error("Safety monitor error: %s", e)
            time.sleep(1)

    logger.info("Safety monitor stopped.")


# ═════════════════════════════════════════════════════════════
# AUTONOMOUS MODES
# ═════════════════════════════════════════════════════════════
def line_tracking_loop(car):
    """Line tracking using grayscale sensors."""
    logger.info("Line tracking mode active.")
    last_state = "stop"
    while state.running and state.autonomous_mode == "line_track":
        try:
            gm_val_list = car.get_grayscale_data()
            _state = car.get_line_status(gm_val_list)

            if _state == [0, 0, 0]:
                gm_state = "stop"
            elif _state[1] == 1:
                gm_state = "forward"
            elif _state[0] == 1:
                gm_state = "right"
            elif _state[2] == 1:
                gm_state = "left"
            else:
                gm_state = "stop"

            if gm_state != "stop":
                last_state = gm_state

            if gm_state == "forward":
                car.set_dir_servo_angle(0)
                car.forward(LINE_TRACK_SPEED)
            elif gm_state == "left":
                car.set_dir_servo_angle(LINE_TRACK_OFFSET)
                car.forward(LINE_TRACK_SPEED)
            elif gm_state == "right":
                car.set_dir_servo_angle(-LINE_TRACK_OFFSET)
                car.forward(LINE_TRACK_SPEED)
            else:
                # Out of line — try to recover
                if last_state == "left":
                    car.set_dir_servo_angle(-30)
                    car.backward(10)
                elif last_state == "right":
                    car.set_dir_servo_angle(30)
                    car.backward(10)

            time.sleep(0.01)
        except Exception as e:
            logger.error("Line tracking error: %s", e)
            time.sleep(0.1)

    car.stop()
    car.set_dir_servo_angle(0)
    logger.info("Line tracking mode stopped.")


def obstacle_avoid_loop(car):
    """Autonomous obstacle avoidance driving."""
    logger.info("Obstacle avoidance mode active.")
    while state.running and state.autonomous_mode == "obstacle_avoid":
        try:
            distance = round(car.ultrasonic.read(), 2)
            if distance < 0:
                time.sleep(0.1)
                continue

            if distance >= SAFE_DISTANCE:
                car.set_dir_servo_angle(0)
                car.forward(MOVE_SPEED)
            elif distance >= DANGER_DISTANCE:
                car.set_dir_servo_angle(30)
                car.forward(MOVE_SPEED)
                time.sleep(0.1)
            else:
                car.set_dir_servo_angle(-30)
                car.backward(MOVE_SPEED)
                time.sleep(0.5)

            time.sleep(0.05)
        except Exception as e:
            logger.error("Obstacle avoidance error: %s", e)
            time.sleep(0.1)

    car.stop()
    car.set_dir_servo_angle(0)
    logger.info("Obstacle avoidance mode stopped.")


# ═════════════════════════════════════════════════════════════
# COMMAND PROCESSING (Keyword-based)
# ═════════════════════════════════════════════════════════════

# LLM system prompt for AI-powered mode
LLM_SYSTEM_PROMPT = f"""You are {ROBOT_NAME}, a friendly PiCar-X robot car assistant.
You can perform physical actions. When you want to perform an action, put them on a
line starting with "ACTIONS:" followed by comma-separated action names.

Available actions:
forward, backward, turn_left, turn_right, stop, look_left, look_right, look_up,
look_down, look_center, shake_head, nod, wave_hands, resist, act_cute, rub_hands,
think, twist_body, celebrate, depressed, spin_around, dance, patrol, reset

Available modes (say these to enter autonomous mode):
line_track, obstacle_avoid

Keep responses short and fun. Use actions to express emotions.
Example response:
"Sure, turning left now! ACTIONS: turn_left"
"""


def process_command_keyword(text, car, tts, music):
    """
    Process voice command using keyword matching.
    Returns True if a command was handled, False otherwise.
    """
    text = text.lower().strip()
    if not text:
        return False

    logger.info("[HEARD] %s", text)

    # --- Sleep / Go back to waiting ---
    if any(w in text for w in ["sleep", "go to sleep", "goodbye", "bye"]):
        say(tts, f"Going to sleep. Say 'okay {ROBOT_NAME.lower()}' to wake me again.")
        reset_position(car)
        with state.lock:
            state.awake = False
            state.autonomous_mode = None
        return True

    # --- Stop autonomous mode ---
    if any(w in text for w in ["stop mode", "cancel mode", "exit mode", "normal mode"]):
        with state.lock:
            state.autonomous_mode = None
        car.stop()
        car.set_dir_servo_angle(0)
        say(tts, "Autonomous mode stopped. I'm listening for commands.")
        return True

    # --- Enter line tracking mode ---
    if any(w in text for w in ["line tracking", "track line", "follow line", "line track", "follow the line"]):
        say(tts, "Starting line tracking mode. Say stop to exit.")
        with state.lock:
            state.autonomous_mode = "line_track"
        t = threading.Thread(target=line_tracking_loop, args=(car,), daemon=True)
        t.start()
        return True

    # --- Enter obstacle avoidance mode ---
    if any(w in text for w in ["obstacle avoidance", "avoid obstacles", "obstacle mode", "avoid mode"]):
        say(tts, "Starting obstacle avoidance mode. Say stop to exit.")
        with state.lock:
            state.autonomous_mode = "obstacle_avoid"
        t = threading.Thread(target=obstacle_avoid_loop, args=(car,), daemon=True)
        t.start()
        return True

    # --- Sound effects ---
    if any(w in text for w in ["honk", "horn", "beep"]):
        play_sound(music, HORN_SOUND)
        say(tts, "Beep beep!")
        return True

    if any(w in text for w in ["start engine", "engine"]):
        play_sound(music, ENGINE_SOUND)
        say(tts, "Vroom vroom!")
        return True

    # --- Status / Help ---
    if any(w in text for w in ["status", "how are you", "what's up"]):
        try:
            dist = round(car.ultrasonic.read(), 2)
            say(tts, f"I'm doing great! Distance ahead is {dist} centimeters.")
        except Exception:
            say(tts, "I'm doing great and ready for commands!")
        return True

    if any(w in text for w in ["help", "what can you do", "commands"]):
        say(tts, "I can go forward, backward, turn left or right, look around, "
                 "dance, celebrate, patrol, track lines, avoid obstacles, and more! "
                 "Just tell me what to do.")
        return True

    # --- Stop (high priority) ---
    if text in ["stop", "halt", "freeze"]:
        with state.lock:
            state.autonomous_mode = None
        car.stop()
        car.set_dir_servo_angle(0)
        say(tts, "Stopped!")
        return True

    # --- Try action dictionary for single/compound commands ---
    # Check for exact matches first
    if text in ACTIONS_DICT:
        say(tts, f"Okay, {text}!")
        ACTIONS_DICT[text](car)
        return True

    # Check for keywords within the text
    for keyword in sorted(ACTIONS_DICT.keys(), key=len, reverse=True):
        if keyword in text:
            say(tts, f"Got it, {keyword}!")
            ACTIONS_DICT[keyword](car)
            return True

    return False


def process_command_llm(text, car, tts, llm, music):
    """
    Process voice command using LLM for natural language understanding.
    The LLM generates a response and optionally includes ACTIONS: line.
    """
    if not llm:
        return process_command_keyword(text, car, tts, music)

    text = text.lower().strip()
    if not text:
        return False

    logger.info("[HEARD-LLM] %s", text)

    # Still handle sleep/stop locally
    if any(w in text for w in ["sleep", "go to sleep", "goodbye", "bye"]):
        say(tts, f"Going to sleep. Say 'okay {ROBOT_NAME.lower()}' to wake me again.")
        reset_position(car)
        with state.lock:
            state.awake = False
            state.autonomous_mode = None
        return True

    if text in ["stop", "halt", "freeze"]:
        with state.lock:
            state.autonomous_mode = None
        car.stop()
        car.set_dir_servo_angle(0)
        say(tts, "Stopped!")
        return True

    # Check for too-close ultrasonic override
    with state.lock:
        is_too_close = state.too_close

    if is_too_close:
        try:
            dist = round(car.ultrasonic.read(), 2)
        except Exception:
            dist = 0
        text = f"<<<Ultrasonic sense too close: {dist}cm>>> " + text

    # Query LLM
    try:
        logger.info("[LLM] Sending to %s...", LLM_PROVIDER)
        response = llm.chat(text, system=LLM_SYSTEM_PROMPT)
        logger.info("[LLM RESPONSE] %s", response)
    except Exception as e:
        logger.error("LLM error: %s", e)
        say(tts, "Sorry, I couldn't reach my brain right now.")
        # Fall back to keyword matching
        return process_command_keyword(text, car, tts, music)

    # Parse response — split speech from actions
    speech_parts = []
    action_names = []
    for line in response.split("\n"):
        line = line.strip()
        if line.upper().startswith("ACTIONS:"):
            action_str = line[len("ACTIONS:"):].strip()
            action_names = [a.strip().lower().replace(" ", "_") for a in action_str.split(",")]
            # Convert underscores back to spaces for action lookup
            action_names = [a.replace("_", " ") for a in action_names]
        else:
            if line:
                speech_parts.append(line)

    # Speak the response
    speech_text = " ".join(speech_parts)
    if speech_text:
        say(tts, speech_text)

    # Execute actions
    if action_names:
        execute_actions(car, action_names)

    return True


# ═════════════════════════════════════════════════════════════
# MAIN LOOP
# ═════════════════════════════════════════════════════════════
def main():
    """Main entry point for the Okay Robot system."""
    logger.info("=" * 60)
    logger.info("  PiCar-X 'Okay Robot' Voice-Activated System")
    logger.info("  Wake word: %s", WAKE_WORDS)
    logger.info("  LLM: %s (enabled=%s)", LLM_PROVIDER if LLM_ENABLED else "none", LLM_ENABLED)
    logger.info("=" * 60)

    # Write PID file
    try:
        os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass

    # Initialize hardware
    car, stt, tts, llm, music = init_hardware()

    # Signal handler for graceful shutdown
    def shutdown(signum=None, frame=None):
        logger.info("Shutdown signal received.")
        state.running = False
        state.autonomous_mode = None
        try:
            car.stop()
            car.set_dir_servo_angle(0)
            car.set_cam_pan_angle(0)
            car.set_cam_tilt_angle(0)
        except Exception:
            pass
        try:
            os.remove(PID_FILE)
        except Exception:
            pass

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    # Start safety monitor
    safety_thread = threading.Thread(target=safety_monitor, args=(car, tts, music), daemon=True)
    safety_thread.start()

    # Play startup sound and greeting
    play_sound(music, ENGINE_SOUND)
    time.sleep(1)
    say(tts, STARTUP_GREETING)
    logger.info("System ready. Waiting for wake word...")

    # ─── Start keyboard control thread ───
    if KEYBOARD_ENABLED:
        def _start_line_tracking():
            t = threading.Thread(target=line_tracking_loop, args=(car,), daemon=True)
            t.start()

        def _start_obstacle_avoidance():
            t = threading.Thread(target=obstacle_avoid_loop, args=(car,), daemon=True)
            t.start()

        start_keyboard_thread(
            car=car,
            state=state,
            tts_func=lambda text: say(tts, text),
            play_sound_func=play_sound,
            music=music,
            start_line_tracking=_start_line_tracking,
            start_obstacle_avoidance=_start_obstacle_avoidance,
        )

    # Choose command processor
    process_command = process_command_llm if (LLM_ENABLED and llm) else process_command_keyword

    # ─── Main Loop ───
    try:
        while state.running:
            # ─── Phase 1: Wait for wake word ───
            if WAKE_ENABLED and not state.awake:
                logger.info("Listening for wake word: %s", WAKE_WORDS)
                try:
                    stt.wait_until_heard(WAKE_WORDS)
                except Exception as e:
                    logger.error("Wake word detection error: %s", e)
                    time.sleep(1)
                    continue

                if not state.running:
                    break

                with state.lock:
                    state.awake = True
                    state.last_command_time = time.time()

                logger.info("Wake word detected!")
                say(tts, f"Hi there! I'm {ROBOT_NAME}. What would you like me to do?")
                nod_thread = threading.Thread(target=lambda: __import__('actions').nod(car), daemon=True)
                nod_thread.start()

            # ─── Phase 2: Command loop ───
            with state.lock:
                state.listening = True

            while state.running and state.awake:
                # Check timeout
                elapsed = time.time() - state.last_command_time
                if elapsed > COMMAND_TIMEOUT_SECONDS:
                    logger.info("Command timeout — going back to sleep.")
                    say(tts, f"I haven't heard anything for a while. Going to sleep. "
                             f"Say 'okay {ROBOT_NAME.lower()}' to wake me again.")
                    with state.lock:
                        state.awake = False
                        state.autonomous_mode = None
                    reset_position(car)
                    break

                # Listen for a command
                try:
                    result = stt.listen(stream=STT_STREAM_MODE)
                    if isinstance(result, dict):
                        text = result.get("text", "").strip()
                    else:
                        text = str(result).strip()
                except Exception as e:
                    logger.error("STT listen error: %s", e)
                    time.sleep(0.5)
                    continue

                if not text:
                    continue

                # Update last command time
                with state.lock:
                    state.last_command_time = time.time()

                # Check if wake word is in the text (re-trigger greeting)
                is_wake = any(w in text.lower() for w in WAKE_WORDS)
                if is_wake:
                    say(tts, f"Yes, I'm here! What's up?")
                    continue

                # Process the command
                handled = process_command(text, car, tts, music) if not LLM_ENABLED else process_command(text, car, tts, llm, music)

                if not handled:
                    say(tts, "I didn't understand that. Try saying a command like forward, turn left, or dance.")

            with state.lock:
                state.listening = False

    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    finally:
        shutdown()
        logger.info("Okay Robot system shut down. Goodbye!")


if __name__ == "__main__":
    main()
