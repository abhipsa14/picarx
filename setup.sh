#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# PiCar-X "Okay Robot" — Automated Setup & Install Script
# ═══════════════════════════════════════════════════════════════
# This script:
#   1. Updates the system
#   2. Installs robot-hat, vilib, picar-x modules
#   3. Enables I2S audio amplifier
#   4. Installs Vosk STT and Piper TTS dependencies
#   5. Copies the Okay Robot system to /home/pi/okay-robot
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

INSTALL_DIR="/home/pi/okay-robot"
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

# Copy project files
cp "$SCRIPT_DIR/okay_robot.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/config.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/actions.py" "$INSTALL_DIR/"

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

# Install systemd service
cp "$SCRIPT_DIR/okay-robot.service" /etc/systemd/system/okay-robot.service
systemctl daemon-reload
systemctl enable okay-robot.service

echo -e "${GREEN}[8/8] Okay Robot deployed to $INSTALL_DIR${NC}"

# ─── Done ─────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗"
echo "║              Installation Complete!                      ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║                                                          ║"
echo "║  Files installed to: /home/pi/okay-robot/               ║"
echo "║                                                          ║"
echo "║  Configuration: /home/pi/okay-robot/config.py           ║"
echo "║  API Keys:      /home/pi/okay-robot/secret.py           ║"
echo "║                                                          ║"
echo "║  Service commands:                                       ║"
echo "║    sudo systemctl start okay-robot    (start now)        ║"
echo "║    sudo systemctl stop okay-robot     (stop)             ║"
echo "║    sudo systemctl restart okay-robot  (restart)          ║"
echo "║    sudo systemctl status okay-robot   (check status)     ║"
echo "║    journalctl -u okay-robot -f        (view live logs)   ║"
echo "║                                                          ║"
echo "║  Manual run:                                             ║"
echo "║    cd /home/pi/okay-robot                                ║"
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
