#!/usr/bin/env python3
"""
PiCar-X "Okay Robot" — Robot Actions Library
=============================================
All physical actions the robot can perform, called by voice commands.
Each action is a standalone function that controls servos, motors, and LEDs.
"""

import time
import threading

# ─────────────────────────────────────────────────────────────
# Action Functions — each takes `car` (Picarx instance)
# ─────────────────────────────────────────────────────────────

def forward(car, speed=30, duration=1.0):
    """Drive forward."""
    car.set_dir_servo_angle(0)
    car.forward(speed)
    time.sleep(duration)
    car.stop()

def backward(car, speed=30, duration=1.0):
    """Drive backward."""
    car.set_dir_servo_angle(0)
    car.backward(speed)
    time.sleep(duration)
    car.stop()

def turn_left(car, speed=30, angle=25, duration=1.0):
    """Turn left and drive."""
    car.set_dir_servo_angle(-angle)
    car.forward(speed)
    time.sleep(duration)
    car.stop()
    car.set_dir_servo_angle(0)

def turn_right(car, speed=30, angle=25, duration=1.0):
    """Turn right and drive."""
    car.set_dir_servo_angle(angle)
    car.forward(speed)
    time.sleep(duration)
    car.stop()
    car.set_dir_servo_angle(0)

def stop(car):
    """Stop all movement."""
    car.stop()
    car.set_dir_servo_angle(0)

def look_left(car, angle=60):
    """Pan camera left."""
    car.set_cam_pan_angle(angle)
    time.sleep(0.5)

def look_right(car, angle=60):
    """Pan camera right."""
    car.set_cam_pan_angle(-angle)
    time.sleep(0.5)

def look_up(car, angle=30):
    """Tilt camera up."""
    car.set_cam_tilt_angle(angle)
    time.sleep(0.5)

def look_down(car, angle=30):
    """Tilt camera down."""
    car.set_cam_tilt_angle(-angle)
    time.sleep(0.5)

def look_center(car):
    """Center the camera."""
    car.set_cam_pan_angle(0)
    car.set_cam_tilt_angle(0)
    time.sleep(0.3)

def shake_head(car):
    """Shake head gesture — 'no'."""
    for angle in [30, -30, 20, -20, 10, -10, 0]:
        car.set_cam_pan_angle(angle)
        time.sleep(0.12)
    car.set_cam_pan_angle(0)

def nod(car):
    """Nod gesture — 'yes'."""
    for angle in [20, -10, 15, -5, 0]:
        car.set_cam_tilt_angle(angle)
        time.sleep(0.2)
    car.set_cam_tilt_angle(0)

def wave_hands(car):
    """Playful wave using steering servo as 'arms'."""
    car.set_cam_tilt_angle(15)
    for _ in range(2):
        car.set_dir_servo_angle(25)
        time.sleep(0.25)
        car.set_dir_servo_angle(-25)
        time.sleep(0.25)
    car.set_dir_servo_angle(0)
    car.set_cam_tilt_angle(0)

def resist(car):
    """Refuse/defensive motion."""
    car.set_cam_tilt_angle(10)
    for _ in range(3):
        car.set_dir_servo_angle(15)
        car.set_cam_pan_angle(15)
        time.sleep(0.15)
        car.set_dir_servo_angle(-15)
        car.set_cam_pan_angle(-15)
        time.sleep(0.15)
    car.stop()
    car.set_dir_servo_angle(0)
    car.set_cam_pan_angle(0)
    car.set_cam_tilt_angle(0)

def act_cute(car):
    """Bouncy 'cute' move with micro-shuffles."""
    car.set_cam_tilt_angle(-15)
    time.sleep(0.2)
    for _ in range(3):
        car.forward(15)
        time.sleep(0.1)
        car.stop()
        time.sleep(0.05)
        car.backward(15)
        time.sleep(0.1)
        car.stop()
        time.sleep(0.05)
    car.set_cam_tilt_angle(0)

def rub_hands(car):
    """Mimics rubbing hands together via steering oscillation."""
    for _ in range(5):
        car.set_dir_servo_angle(6)
        time.sleep(0.1)
        car.set_dir_servo_angle(-6)
        time.sleep(0.1)
    car.set_dir_servo_angle(0)

def think(car):
    """Thinking animation — smooth pan + tilt."""
    car.set_cam_pan_angle(-30)
    car.set_cam_tilt_angle(-10)
    car.set_dir_servo_angle(15)
    time.sleep(1.0)
    car.set_cam_pan_angle(-15)
    time.sleep(0.5)
    car.set_dir_servo_angle(0)
    car.set_cam_pan_angle(0)
    car.set_cam_tilt_angle(0)

def twist_body(car):
    """Body twist — alternating forward/backward with pan/steer."""
    for _ in range(3):
        car.forward(15)
        time.sleep(0.15)
        car.stop()
        car.set_cam_pan_angle(20)
        car.set_dir_servo_angle(-15)
        time.sleep(0.15)
        car.backward(15)
        time.sleep(0.15)
        car.stop()
        car.set_cam_pan_angle(-20)
        car.set_dir_servo_angle(15)
        time.sleep(0.15)
    car.stop()
    car.set_dir_servo_angle(0)
    car.set_cam_pan_angle(0)

def celebrate(car):
    """Festive celebration flourish."""
    car.set_cam_tilt_angle(20)
    for _ in range(2):
        car.set_cam_pan_angle(-30)
        car.set_dir_servo_angle(-20)
        time.sleep(0.2)
        car.set_cam_pan_angle(30)
        car.set_dir_servo_angle(20)
        time.sleep(0.2)
    car.set_cam_pan_angle(0)
    car.set_cam_tilt_angle(0)
    car.set_dir_servo_angle(0)

def depressed(car):
    """Sad posture sequence."""
    for angle in [-10, -20, -15, -25, -10]:
        car.set_cam_tilt_angle(angle)
        time.sleep(0.4)
    time.sleep(1.0)
    car.set_cam_tilt_angle(0)

def spin_around(car, speed=30):
    """Spin the car around (360-ish)."""
    car.set_dir_servo_angle(35)
    car.forward(speed)
    time.sleep(2.5)
    car.stop()
    car.set_dir_servo_angle(0)

def dance(car):
    """A fun dance routine combining moves."""
    for _ in range(2):
        car.set_dir_servo_angle(25)
        car.forward(20)
        time.sleep(0.3)
        car.set_dir_servo_angle(-25)
        time.sleep(0.3)
    car.stop()
    car.set_dir_servo_angle(0)
    wave_hands(car)
    celebrate(car)

def patrol(car, speed=25, duration=5.0):
    """Patrol mode — drive forward with head scanning."""
    car.forward(speed)
    end_time = time.time() + duration
    angle = 0
    direction = 1
    while time.time() < end_time:
        car.set_cam_pan_angle(angle)
        angle += 5 * direction
        if angle > 45 or angle < -45:
            direction *= -1
        time.sleep(0.1)
    car.stop()
    car.set_cam_pan_angle(0)

def reset_position(car):
    """Reset all servos to center and stop motors."""
    car.stop()
    car.set_dir_servo_angle(0)
    car.set_cam_pan_angle(0)
    car.set_cam_tilt_angle(0)


# ─────────────────────────────────────────────────────────────
# Action lookup dictionary — maps keywords to functions
# ─────────────────────────────────────────────────────────────
ACTIONS_DICT = {
    "forward":       forward,
    "go forward":    forward,
    "move forward":  forward,
    "go ahead":      forward,
    "backward":      backward,
    "go backward":   backward,
    "move backward": backward,
    "go back":       backward,
    "reverse":       backward,
    "back up":       backward,
    "turn left":     turn_left,
    "go left":       turn_left,
    "left":          turn_left,
    "turn right":    turn_right,
    "go right":      turn_right,
    "right":         turn_right,
    "stop":          stop,
    "halt":          stop,
    "freeze":        stop,
    "look left":     look_left,
    "look right":    look_right,
    "look up":       look_up,
    "look down":     look_down,
    "look center":   look_center,
    "center":        look_center,
    "shake head":    shake_head,
    "say no":        shake_head,
    "nod":           nod,
    "say yes":       nod,
    "wave":          wave_hands,
    "wave hands":    wave_hands,
    "resist":        resist,
    "refuse":        resist,
    "act cute":      act_cute,
    "cute":          act_cute,
    "rub hands":     rub_hands,
    "think":         think,
    "thinking":      think,
    "twist":         twist_body,
    "twist body":    twist_body,
    "celebrate":     celebrate,
    "party":         celebrate,
    "happy":         celebrate,
    "depressed":     depressed,
    "sad":           depressed,
    "spin":          spin_around,
    "spin around":   spin_around,
    "dance":         dance,
    "patrol":        patrol,
    "reset":         reset_position,
}


def execute_actions(car, action_names):
    """
    Execute a list of action names sequentially.
    action_names: list of strings matching keys in ACTIONS_DICT
    """
    for name in action_names:
        name = name.strip().lower()
        if name in ACTIONS_DICT:
            try:
                ACTIONS_DICT[name](car)
            except Exception as e:
                print(f"[ACTION ERROR] {name}: {e}")
        else:
            print(f"[ACTION] Unknown action: {name}")
