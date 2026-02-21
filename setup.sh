#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# PiCar-X "Okay Robot" — Automated Setup & Install Script
# ═══════════════════════════════════════════════════════════════
# This script:
#   1. Updates the system
#   2. Installs robot-hat, vilib, picar-x modules
#   3. Enables I2S audio amplifier
#   4. Installs Vosk STT and Piper TTS dependencies
#   5. Copies the Okay Robot system to /home/pi/
#   6. Installs and enables the systemd service
#
# Run with: sudo bash setup.sh
# ═══════════════════════════════════════════════════════════════

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

INSTALL_DIR="/home/pi"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   PiCar-X 'Okay Robot' — Setup & Installation Script   ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: Please run as root: sudo bash setup.sh${NC}"
    exit 1
fi

# ─── Step 1: System Update ───────────────────────────────────
echo -e "${YELLOW}[1/8] Updating system packages...${NC}"
apt update -y
apt upgrade -y
echo -e "${GREEN}[1/8] System updated.${NC}"

# ─── Step 2: Install System Dependencies ─────────────────────
echo -e "${YELLOW}[2/8] Installing system dependencies...${NC}"
apt install -y \
    git \
    python3-pip \
    python3-setuptools \
    python3-smbus \
    python3-pyaudio \
    portaudio19-dev \
    libatlas-base-dev \
    flac \
    alsa-utils \
    i2c-tools \
    espeak \
    libttspico-utils \
    ffmpeg
echo -e "${GREEN}[2/8] System dependencies installed.${NC}"

# ─── Step 3: Install robot-hat Module ─────────────────────────
echo -e "${YELLOW}[3/8] Installing robot-hat module...${NC}"
cd /home/pi
if [ -d "robot-hat" ]; then
    echo "  robot-hat directory exists, pulling latest..."
    cd robot-hat && git pull || true
else
    git clone -b 2.5.x https://github.com/sunfounder/robot-hat.git --depth 1
    cd robot-hat
fi
python3 install.py
echo -e "${GREEN}[3/8] robot-hat installed.${NC}"

# ─── Step 4: Install vilib Module ─────────────────────────────
echo -e "${YELLOW}[4/8] Installing vilib module...${NC}"
cd /home/pi
if [ -d "vilib" ]; then
    echo "  vilib directory exists, pulling latest..."
    cd vilib && git pull || true
else
    git clone https://github.com/sunfounder/vilib.git --depth 1
    cd vilib
fi
python3 install.py
echo -e "${GREEN}[4/8] vilib installed.${NC}"

# ─── Step 5: Install picar-x Module ──────────────────────────
echo -e "${YELLOW}[5/8] Installing picar-x module...${NC}"
cd /home/pi
if [ -d "picar-x" ]; then
    echo "  picar-x directory exists, pulling latest..."
    cd picar-x && git pull || true
else
    git clone -b 2.1.x https://github.com/sunfounder/picar-x.git --depth 1
    cd picar-x
fi
pip3 install . --break-system-packages 2>/dev/null || pip3 install .
echo -e "${GREEN}[5/8] picar-x installed.${NC}"

# ─── Step 6: Enable I2S Amplifier ────────────────────────────
echo -e "${YELLOW}[6/8] Enabling I2S audio amplifier...${NC}"
cd /home/pi/robot-hat
if [ -f "i2samp.sh" ]; then
    echo "  Running i2samp.sh (you may need to confirm with 'y')..."
    bash i2samp.sh <<< "y" || true
    echo -e "${GREEN}[6/8] I2S amplifier setup complete.${NC}"
else
    echo -e "${YELLOW}[6/8] i2samp.sh not found, skipping. You may need to run it manually.${NC}"
fi

# ─── Step 7: Install Python Dependencies ─────────────────────
echo -e "${YELLOW}[7/8] Installing Python dependencies (Vosk, etc.)...${NC}"
pip3 install --break-system-packages vosk 2>/dev/null || pip3 install vosk
pip3 install --break-system-packages sounddevice 2>/dev/null || pip3 install sounddevice
pip3 install --break-system-packages readchar 2>/dev/null || pip3 install readchar
echo -e "${GREEN}[7/8] Python dependencies installed.${NC}"

# ─── Step 8: Deploy Okay Robot System ────────────────────────
echo -e "${YELLOW}[8/8] Deploying Okay Robot system...${NC}"

# Create install directory
mkdir -p "$INSTALL_DIR"

# ── Helper: copy file or generate it inline if missing ──
copy_or_generate() {
    local filename="$1"
    local dest="$2"
    if [ -f "$SCRIPT_DIR/$filename" ]; then
        cp "$SCRIPT_DIR/$filename" "$dest"
        echo "  Copied $filename → $dest"
    else
        echo -e "${YELLOW}  $filename not found in repo — generating from template...${NC}"
        generate_file "$filename" "$dest"
    fi
}

generate_file() {
    local filename="$1"
    local dest="$2"
    case "$filename" in

    okay_robot.py)
        echo "  Downloading okay_robot.py from GitHub repo..."
        curl -fsSL "https://raw.githubusercontent.com/$(cd "$SCRIPT_DIR" && git remote get-url origin 2>/dev/null | sed 's|.*github.com[:/]||;s|\.git$||')/main/okay_robot.py" \
            -o "$dest/okay_robot.py" 2>/dev/null
        if [ $? -ne 0 ] || [ ! -s "$dest/okay_robot.py" ]; then
            echo -e "${RED}  Could not download okay_robot.py. Creating minimal placeholder.${NC}"
            cat > "$dest/okay_robot.py" << 'OKAYEOF'
#!/usr/bin/env python3
"""
PiCar-X "Okay Robot" — Voice-Activated Control System (placeholder).
This file was auto-generated because the source was not found during setup.
Please replace it with the full okay_robot.py from the project repository.
"""
import sys
print("ERROR: This is a placeholder okay_robot.py.", file=sys.stderr)
print("Please download the full version from the project repo.", file=sys.stderr)
sys.exit(1)
OKAYEOF
        fi
        ;;

    config.py)
        cat > "$dest/config.py" << 'CONFIGEOF'
#!/usr/bin/env python3
"""PiCar-X 'Okay Robot' — Configuration (auto-generated)."""

ROBOT_NAME = "Robot"
WAKE_WORDS = ["okay robot", "ok robot", "hey robot"]
WAKE_ENABLED = True
COMMAND_TIMEOUT_SECONDS = 30

STT_LANGUAGE = "en-us"
STT_STREAM_MODE = False

TTS_ENGINE = "piper"
TTS_MODEL = "en_US-ryan-low"

LLM_ENABLED = False
LLM_PROVIDER = "openai"
LLM_MODEL = "gpt-4o-mini"
LLM_API_KEY = ""
try:
    from secret import LLM_API_KEY as _KEY
    if not LLM_API_KEY:
        LLM_API_KEY = _KEY
except ImportError:
    pass

MOVE_SPEED = 30
MOVE_DURATION = 1.0
TURN_ANGLE = 25
CAMERA_PAN_STEP = 30
CAMERA_TILT_STEP = 20

OBSTACLE_AVOIDANCE_ENABLED = True
SAFE_DISTANCE = 40
DANGER_DISTANCE = 20
TOO_CLOSE_DISTANCE = 10

CLIFF_DETECTION_ENABLED = True
CLIFF_REFERENCE = [200, 200, 200]

LINE_TRACK_SPEED = 10
LINE_TRACK_OFFSET = 20

SOUND_DIR = "/home/pi/picar-x/sounds"
MUSIC_DIR = "/home/pi/picar-x/musics"
HORN_SOUND = "car-double-horn.wav"
ENGINE_SOUND = "car-start-engine.wav"

LOG_FILE = "/var/log/okay-robot.log"
PID_FILE = "/var/run/okay-robot.pid"
STARTUP_GREETING = f"Hello! I am {ROBOT_NAME}. Say 'okay robot' to wake me up!"
CONFIGEOF
        echo "  Generated config.py"
        ;;

    actions.py)
        echo "  Downloading actions.py from GitHub repo..."
        curl -fsSL "https://raw.githubusercontent.com/$(cd "$SCRIPT_DIR" && git remote get-url origin 2>/dev/null | sed 's|.*github.com[:/]||;s|\.git$||')/main/actions.py" \
            -o "$dest/actions.py" 2>/dev/null
        if [ $? -ne 0 ] || [ ! -s "$dest/actions.py" ]; then
            echo -e "${RED}  Could not download actions.py. Creating minimal placeholder.${NC}"
            cat > "$dest/actions.py" << 'ACTIONSEOF'
#!/usr/bin/env python3
"""PiCar-X actions library (auto-generated minimal version)."""
import time

def forward(car, speed=30, duration=1.0):
    car.set_dir_servo_angle(0); car.forward(speed); time.sleep(duration); car.stop()
def backward(car, speed=30, duration=1.0):
    car.set_dir_servo_angle(0); car.backward(speed); time.sleep(duration); car.stop()
def turn_left(car, speed=30, angle=25, duration=1.0):
    car.set_dir_servo_angle(-angle); car.forward(speed); time.sleep(duration); car.stop(); car.set_dir_servo_angle(0)
def turn_right(car, speed=30, angle=25, duration=1.0):
    car.set_dir_servo_angle(angle); car.forward(speed); time.sleep(duration); car.stop(); car.set_dir_servo_angle(0)
def stop(car):
    car.stop(); car.set_dir_servo_angle(0)
def look_left(car, angle=60):
    car.set_camera_servo1_angle(angle); time.sleep(0.5)
def look_right(car, angle=60):
    car.set_camera_servo1_angle(-angle); time.sleep(0.5)
def look_up(car, angle=30):
    car.set_camera_servo2_angle(angle); time.sleep(0.5)
def look_down(car, angle=30):
    car.set_camera_servo2_angle(-angle); time.sleep(0.5)
def look_center(car):
    car.set_camera_servo1_angle(0); car.set_camera_servo2_angle(0); time.sleep(0.3)
def nod(car):
    for a in [20,-10,15,-5,0]: car.set_camera_servo2_angle(a); time.sleep(0.2)
def shake_head(car):
    for a in [30,-30,20,-20,10,-10,0]: car.set_camera_servo1_angle(a); time.sleep(0.12)
def celebrate(car):
    car.set_camera_servo2_angle(20)
    for _ in range(2):
        car.set_camera_servo1_angle(-30); car.set_dir_servo_angle(-20); time.sleep(0.2)
        car.set_camera_servo1_angle(30); car.set_dir_servo_angle(20); time.sleep(0.2)
    car.set_camera_servo1_angle(0); car.set_camera_servo2_angle(0); car.set_dir_servo_angle(0)
def dance(car):
    for _ in range(2):
        car.set_dir_servo_angle(25); car.forward(20); time.sleep(0.3)
        car.set_dir_servo_angle(-25); time.sleep(0.3)
    car.stop(); car.set_dir_servo_angle(0); celebrate(car)
def reset_position(car):
    car.stop(); car.set_dir_servo_angle(0); car.set_camera_servo1_angle(0); car.set_camera_servo2_angle(0)

ACTIONS_DICT = {
    "forward": forward, "go forward": forward, "move forward": forward,
    "backward": backward, "go backward": backward, "reverse": backward,
    "turn left": turn_left, "left": turn_left,
    "turn right": turn_right, "right": turn_right,
    "stop": stop, "halt": stop,
    "look left": look_left, "look right": look_right,
    "look up": look_up, "look down": look_down,
    "look center": look_center, "center": look_center,
    "nod": nod, "say yes": nod,
    "shake head": shake_head, "say no": shake_head,
    "celebrate": celebrate, "party": celebrate,
    "dance": dance, "reset": reset_position,
}

def execute_actions(car, action_names):
    for name in action_names:
        name = name.strip().lower()
        if name in ACTIONS_DICT:
            try: ACTIONS_DICT[name](car)
            except Exception as e: print(f"[ACTION ERROR] {name}: {e}")
        else: print(f"[ACTION] Unknown action: {name}")
ACTIONSEOF
        fi
        ;;

    okay-robot.service)
        cat > "$dest" << 'SERVICEEOF'
[Unit]
Description=PiCar-X "Okay Robot" Voice-Activated Control System
Documentation=https://docs.sunfounder.com/projects/picar-x-v20/en/latest/
After=network.target sound.target
Wants=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/home/pi
ExecStartPre=/bin/sleep 10
ExecStart=/usr/bin/python3 /home/pi/okay_robot.py
ExecStop=/bin/kill -SIGTERM $MAINPID
Restart=on-failure
RestartSec=10
StandardOutput=journal+console
StandardError=journal+console
Environment=PYTHONUNBUFFERED=1
Environment=HOME=/root
Environment=DISPLAY=:0
SupplementaryGroups=i2c gpio audio video input
WatchdogSec=120
TimeoutStartSec=60
TimeoutStopSec=15

[Install]
WantedBy=multi-user.target
SERVICEEOF
        echo "  Generated okay-robot.service"
        ;;

    *)
        echo -e "${RED}  No template available for $filename — skipping.${NC}"
        ;;
    esac
}

# ── Deploy project files ──
copy_or_generate "okay_robot.py" "$INSTALL_DIR"
copy_or_generate "config.py" "$INSTALL_DIR"
copy_or_generate "actions.py" "$INSTALL_DIR"

# Create secret.py template if it doesn't exist
if [ ! -f "$INSTALL_DIR/secret.py" ]; then
    cat > "$INSTALL_DIR/secret.py" << 'SECRETEOF'
#!/usr/bin/env python3
"""
Secret configuration — API keys for LLM providers.
Edit this file to add your API key.
"""
LLM_API_KEY = ""  # Put your OpenAI/Gemini/DeepSeek/etc. API key here
SECRETEOF
    echo "  Created secret.py template at $INSTALL_DIR/secret.py"
fi

# Set permissions
chown -R pi:pi "$INSTALL_DIR" 2>/dev/null || true
chmod +x "$INSTALL_DIR/okay_robot.py"

# Install systemd service — copy or generate
if [ -f "$SCRIPT_DIR/okay-robot.service" ]; then
    cp "$SCRIPT_DIR/okay-robot.service" /etc/systemd/system/okay-robot.service
    echo "  Copied okay-robot.service → /etc/systemd/system/"
else
    echo -e "${YELLOW}  okay-robot.service not found in repo — generating...${NC}"
    generate_file "okay-robot.service" "/etc/systemd/system/okay-robot.service"
fi
systemctl daemon-reload
systemctl enable okay-robot.service

echo -e "${GREEN}[8/8] Okay Robot deployed to $INSTALL_DIR${NC}"

# ─── Done ─────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗"
echo "║              Installation Complete!                      ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║                                                          ║"
echo "║  Files installed to: /home/pi/                           ║"
echo "║                                                          ║"
echo "║  Configuration: /home/pi/config.py                      ║"
echo "║  API Keys:      /home/pi/secret.py                      ║"
echo "║                                                          ║"
echo "║  Service commands:                                       ║"
echo "║    sudo systemctl start okay-robot    (start now)        ║"
echo "║    sudo systemctl stop okay-robot     (stop)             ║"
echo "║    sudo systemctl restart okay-robot  (restart)          ║"
echo "║    sudo systemctl status okay-robot   (check status)     ║"
echo "║    journalctl -u okay-robot -f        (view live logs)   ║"
echo "║                                                          ║"
echo "║  Manual run:                                             ║"
echo "║    cd /home/pi                                            ║"
echo "║    sudo python3 okay_robot.py                            ║"
echo "║                                                          ║"
echo "║  Wake word: 'okay robot'                                 ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "${YELLOW}NOTE: A reboot is recommended to complete I2S audio setup.${NC}"
echo -e "${YELLOW}      Run: sudo reboot${NC}"
echo ""
read -p "Reboot now? (y/N): " REBOOT_CHOICE
if [[ "$REBOOT_CHOICE" =~ ^[Yy]$ ]]; then
    echo "Rebooting..."
    reboot
fi
