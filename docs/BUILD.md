# PwnBullseye4 Build Documentation

## Overview
This document describes how to build the PwnBullseye4 image for Raspberry Pi Zero W (armhf) and Pi Zero 2 W (armv7).

## Prerequisites

### Build Host Requirements
- Linux (Ubuntu 22.04+, Debian 12+, or WSL2)
- Docker (for pi-gen containerized build)
- Or native build tools: `debootstrap`, `qemu-user-static`, `binfmt-support`

### For Native Build (without Docker)
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y \
    debootstrap qemu-user-static binfmt-support \
    kpartx dosfstools parted \
    python3 python3-venv git curl wget \
    xz-utils zip unzip

# Enable binfmt for ARM emulation
sudo update-binfmts --enable qemu-arm
```

## Quick Start (Docker)

```bash
cd /h/pwnbullseye4/build/pi-gen

# Build armhf (Pi Zero W)
./build-docker.sh -c ../configs/config-armhf

# Build armv7 (Pi Zero 2 W) 
./build-docker.sh -c ../configs/config-armv7
```

## Quick Start (Native)

```bash
cd /h/pwnbullseye4/build/pi-gen

# Build armhf (Pi Zero W)
./build.sh -c ../configs/config-armhf

# Build armv7 (Pi Zero 2 W)
./build.sh -c ../configs/config-armv7
```

## Build Stages

### Stage 0: Base System (pi-gen default)
- Raspberry Pi OS Bullseye Lite (32-bit)
- Basic system configuration

### Stage 1: Core Packages (`stage1/00-packages`)
- Kernel, firmware, bootloader
- Networking tools (wpasupplicant, bluez, iptables)
- Development tools (git, cmake, build-essential, python3-dev)
- Display libraries (python3-spidev, python3-rpi.gpio, i2c-tools, spi-tools)
- Firmware packages

### Stage 2: Python & Dependencies (`stage2/00-packages`, `stage2/01-run.sh`)
- Python packages via pip: numpy, scipy, torch, stable-baselines3, onnxruntime, etc.
- **lgpio from source** (required for Pi Zero 2 W GPIO)
- Bettercap v2.29.1 (pinned)
- hcxtools from source
- nexmon firmware for Pi Zero 2 W

### Stage 3: Pwnagotchi Installation (`stage3/`)
- `00-pre-pwn`: Pre-install setup
- `01-pwn-packages`: Additional packages
- `02-libpcap`: libpcap from source
- `03-bettercap-pwngrid`: Bettercap pwngrid integration
- `04-nexmon`: Nexmon firmware
- `05-install-pwnagotchi`: Main pwnagotchi install
  - Creates `/etc/pwnagotchi` directories
  - Installs pwnagotchi from local source (noai branch)
  - Sets up virtual environment with system-site-packages
- `06-hcxtools`: hcxtools utilities
- `07-patches`: System patches
- `08-pwnstore`: PwnStore integration

## Configuration Files

### `/h/pwnbullseye4/config/defaults.toml`
Optimized defaults for PwnBullseye4:
- AI enabled with ONNX Runtime backend
- Async inference with heuristic fallback
- Waveshare v4 display as default
- WPA-Sec plugin enabled
- Bluetooth tethering configured
- Web UI on port 8080

### `/h/pwnbullseye4/config/config.toml.example`
User configuration template

## Output Images

Images are saved to `pi-gen/deploy/`:
- `pwnbullseye4-armhf-<date>.img.xz` - Pi Zero W
- `pwnbullseye4-armv7-<date>.img.xz` - Pi Zero 2 W

## Flashing Image

```bash
# Using Raspberry Pi Imager (recommended)
# Select "Custom" image and choose the .img.xz file

# Or using dd (Linux/macOS)
xzcat pwnbullseye4-armv7-*.img.xz | sudo dd of=/dev/sdX bs=4M status=progress
sudo sync
```

## First Boot

1. Insert SD card into Pi
2. Connect Waveshare v4 e-Paper HAT
3. Power on
4. Wait 60-90 seconds for first boot setup
5. SSH: `ssh pi@pwnbullseye4.local` (password: `raspberry`)
6. Check status: `sudo systemctl status pwnagotchi`

## Configuration

### WPA-Sec Setup
1. Create account at https://wpa-sec.stanev.org
2. Get API key
3. Edit `/etc/pwnagotchi/config.toml`:
```toml
main.plugins.wpa-sec.enabled = true
main.plugins.wpa-sec.api_key = "YOUR_API_KEY"
```

### Bluetooth Tethering (Android)
```toml
main.plugins.bt-tether.enabled = true
main.plugins.bt-tether.devices.my-phone.enabled = true
main.plugins.bt-tether.devices.my-phone.mac = "AA:BB:CC:DD:EE:FF"
main.plugins.bt-tether.devices.my-phone.ip = "192.168.44.44"
```

### Display Configuration
```toml
ui.display.type = "waveshare_4"
ui.display.rotation = 0
ui.display.invert = true
```

## AI Model

The AI model is pre-trained and exported to ONNX format:
- Location: `/root/brain.onnx`
- Format: ONNX (opset 11)
- Inference: ONNX Runtime CPU
- Fallback: Heuristic random policy

To train your own model:
```bash
cd /h/pwnbullseye4/ai
python3 train.py --timesteps 100000 --output models/brain.zip
python3 export_onnx.py models/brain.zip /root/brain.onnx
```

## Troubleshooting

### Display not working
- Check wiring (SPI pins)
- Verify `ui.display.type = "waveshare_4"` in config
- Check `dmesg | grep spi` for SPI errors
- Try `ui.display.invert = false` if colors inverted

### AI not loading
- Check `/var/log/pwnagotchi.log` for AI errors
- Verify `/root/brain.onnx` exists
- Check ONNX Runtime installed: `pip3 list | grep onnx`
- Fallback policy activates automatically

### Bluetooth not working
- Ensure `bluez` and `bluez-tools` installed
- Check `bluetoothctl` for pairing
- Verify `bt-tether` plugin config

### Build fails
- Ensure qemu-user-static registered: `docker run --rm --privileged multiarch/qemu-user-static --reset -p yes`
- Clean build: `./build-docker.sh -c config-armv7 -C`
- Check disk space (need ~20GB)

## Customizing Build

### Add/Remove Packages
Edit stage package files:
- `build/stages/stage1/00-packages`
- `build/stages/stage2/00-packages`

### Modify Pwnagotchi Source
Edit files in `build/stages/stage3/05-install-pwnagotchi/src/pwnagotchi/`

### Change Default Config
Edit `build/stages/stage3/05-install-pwnagotchi/01-run-chroot.sh` to copy custom configs

## Pi Zero 2 W Specific Fixes

The build includes these critical fixes for Pi Zero 2 W:

1. **lgpio from source** - Required for GPIO access on BCM2711
2. **nexmon firmware** - Proper WiFi firmware for BCM43430
3. **CPU governor performance** - Set in boot config
4. **Swap 1GB** - For AI model memory
5. **Overclock settings** in config.txt:
   ```
   arm_freq=1000
   over_voltage=6
   gpu_freq=400
   ```
6. **QEMU CPU emulation** for armv6 during chroot install

## Security Notes

- Default SSH password: `raspberry` (CHANGE ON FIRST BOOT)
- Web UI default credentials: `changeme` / `changeme`
- Disable SSH password auth after setting up keys
- Firewall: Only ports 22, 8080, 8081 (bettercap) exposed

## License

Based on:
- jayofelony/pwnagotchi-bullseye (v2.6.4) - GPL-3.0
- jayofelony/pwnagotchi (noai branch) - GPL-3.0
- evilsocket/pwnagotchi (v1.5.5) - GPL-3.0
- RPi-Distro/pi-gen - BSD-3-Clause

PwnBullseye4 modifications - MIT License