# PiCar-X "Okay Robot" — Voice-Activated System

A complete voice-activated control system for the SunFounder PiCar-X v2.0 robot car.
Say **"okay robot"** to wake it up, then speak commands to make it move, look around,
dance, track lines, avoid obstacles, and more — all hands-free.

## Features

- **Wake Word Detection** — "okay robot" (offline, via Vosk STT)
- **Voice Commands** — forward, backward, turn left/right, stop, look around, dance, spin, patrol
- **Expressive Gestures** — nod, shake head, wave, celebrate, act cute, think, depressed
- **Autonomous Modes** — line tracking, obstacle avoidance (voice-activated)
- **Safety Systems** — background ultrasonic obstacle detection + cliff detection
- **Sound Effects** — horn, engine start
- **Optional LLM** — connect to OpenAI, Gemini, DeepSeek, etc. for natural conversation
- **Auto-Start Service** — runs on boot via systemd

## Quick Start

### 1. Prerequisites

- Raspberry Pi (4 or 5) with Raspberry Pi OS
- Assembled PiCar-X v2.0
- USB microphone plugged in
- Speaker connected (via I2S amp on Robot HAT)
- Internet connection (for initial setup only)

### 2. Install

Copy this project folder to your Raspberry Pi, then run:

```bash
cd ~/picarx  # or wherever you placed the files
sudo bash setup.sh
```

The setup script will:
1. Update system packages
2. Install `robot-hat`, `vilib`, and `picar-x` modules
3. Enable the I2S audio amplifier
4. Install Vosk STT and dependencies
5. Deploy files to `/home/pi/`
6. Register and enable the systemd auto-start service
7. Prompt for reboot

### 3. Reboot

```bash
sudo reboot
```

After reboot, the system starts automatically. You'll hear: *"Hello! I am Robot. Say 'okay robot' to wake me up!"*

## Usage

### Voice Commands

| Command | Action |
|---------|--------|
| "okay robot" | Wake up the robot |
| "forward" / "go ahead" | Drive forward |
| "backward" / "reverse" | Drive backward |
| "turn left" / "turn right" | Turn and drive |
| "stop" / "halt" | Stop all movement |
| "look left" / "look right" | Pan camera |
| "look up" / "look down" | Tilt camera |
| "dance" | Fun dance routine |
| "spin" / "spin around" | Spin the car |
| "celebrate" / "party" | Victory flourish |
| "nod" / "say yes" | Nod gesture |
| "shake head" / "say no" | Shake head gesture |
| "wave" | Wave hands |
| "act cute" | Cute bouncy move |
| "think" | Thinking pose |
| "patrol" | Drive forward while scanning |
| "honk" / "horn" | Play horn sound |
| "status" | Report distance ahead |
| "help" | List available commands |
| "line tracking" | Enter line tracking mode |
| "obstacle avoidance" | Enter obstacle avoidance mode |
| "stop mode" | Exit autonomous mode |
| "sleep" / "goodbye" | Go back to waiting for wake word |

### Service Management

```bash
sudo systemctl start okay-robot      # Start the service
sudo systemctl stop okay-robot       # Stop the service
sudo systemctl restart okay-robot    # Restart
sudo systemctl status okay-robot     # Check status
journalctl -u okay-robot -f          # View live logs
```

### Manual Run (for testing)

```bash
cd /home/pi
sudo python3 okay_robot.py
```

## Configuration

Edit `/home/pi/config.py` to customize:

| Setting | Default | Description |
|---------|---------|-------------|
| `WAKE_WORDS` | `["okay robot", "ok robot"]` | Wake word phrases |
| `ROBOT_NAME` | `"Robot"` | Robot's name (used in speech) |
| `MOVE_SPEED` | `30` | Motor speed (0-100) |
| `COMMAND_TIMEOUT_SECONDS` | `30` | Seconds before going back to sleep |
| `LLM_ENABLED` | `False` | Enable AI conversation mode |
| `LLM_PROVIDER` | `"openai"` | LLM provider |
| `TTS_ENGINE` | `"piper"` | TTS engine (`piper` or `espeak`) |
| `OBSTACLE_AVOIDANCE_ENABLED` | `True` | Background obstacle safety |
| `CLIFF_DETECTION_ENABLED` | `True` | Background cliff safety |

### Enable AI Mode (Optional)

1. Edit `/home/pi/secret.py`:
   ```python
   LLM_API_KEY = "sk-your-openai-api-key-here"
   ```
2. Edit `config.py`:
   ```python
   LLM_ENABLED = True
   LLM_PROVIDER = "openai"  # or "gemini", "deepseek", etc.
   ```
3. Restart: `sudo systemctl restart okay-robot`

Now the robot uses an LLM to understand natural language and respond conversationally.

## Project Structure

```
picarx/
├── okay_robot.py         # Main system — wake word + command loop
├── actions.py            # All robot action functions
├── config.py             # Configuration (wake word, speeds, LLM, etc.)
├── setup.sh              # Automated install script
├── okay-robot.service    # systemd service unit file
└── README.md             # This file
```

## How It Works

1. **Boot** — systemd starts `okay_robot.py` automatically
2. **Wait** — Vosk STT listens continuously for "okay robot"
3. **Wake** — Robot greets you and enters command mode
4. **Listen** — Vosk transcribes your speech in real-time
5. **Process** — Commands are matched by keyword (or sent to LLM)
6. **Act** — Robot executes movement/gesture/mode
7. **Safety** — Background thread monitors ultrasonic + cliff sensors
8. **Sleep** — After 30s of silence (or "goodbye"), returns to step 2

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No response to wake word | Check USB microphone: `arecord -l` |
| No audio output | Run `sudo bash ~/robot-hat/i2samp.sh` again, reboot |
| Robot doesn't move | Check battery, motor connections |
| Service won't start | Check logs: `journalctl -u okay-robot -e` |
| Vosk model download fails | Ensure internet is connected on first run |
| LLM timeout | Check API key in `secret.py` and network |

## Based On

Built following the [SunFounder PiCar-X v2.0 Documentation](https://docs.sunfounder.com/projects/picar-x-v20/en/latest/), incorporating:
- Lesson 2: Basic Movement
- Lesson 4: Obstacle Avoidance
- Lesson 5: Cliff Detection
- Lesson 6: Line Tracking
- Lesson 13: Sound Effects
- Lesson 16: Voice Control with Vosk
- Lesson 21: AI Voice Assistant Car

## License

For personal/educational use. PiCar-X modules are (c) SunFounder.
