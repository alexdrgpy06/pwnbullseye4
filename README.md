# PwnBullseye4

[![Build PwnBullseye4 Images](https://github.com/alexdrgpy06/pwnbullseye4/actions/workflows/build.yml/badge.svg)](https://github.com/alexdrgpy06/pwnbullseye4/actions/workflows/build.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Architecture](https://img.shields.io/badge/arch-armhf%20%7C%20armv7-orange)]()

32-bit Debian Bullseye pwnagotchi for **Raspberry Pi Zero W** and **Pi Zero 2 W**.

## Features

- **Async AI** — ONNX Runtime inference, non-blocking UI, heuristic fallback
- **Pi Zero 2 W** — lgpio from source, CPU governor, 1GB swap
- **Waveshare v4** — 2.13" e-Paper HAT v4 (250×122, SSD1680)
- **WPA-Sec** — automatic handshake upload
- **Bluetooth tethering** — Android/iOS out of the box
- **Reproducible** — pi-gen based, GitHub Actions CI
- **Pre-built images** — download from [Releases](https://github.com/alexdrgpy06/pwnbullseye4/releases)

## Quick Start

### Download

| Device | Image | Architecture |
|--------|-------|-------------|
| Pi Zero W | `pwnbullseye4-armhf-*.img.xz` | armhf (ARMv6) |
| Pi Zero 2 W | `pwnbullseye4-armv7-*.img.xz` | armv7 (ARMv7) |

Download from [Releases](https://github.com/alexdrgpy06/pwnbullseye4/releases).

### Flash

```bash
xzcat pwnbullseye4-armv7-*.img.xz | sudo dd of=/dev/sdX bs=4M status=progress
sudo sync
```

Or use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) → Custom image.

### First Boot

1. Insert SD card, connect Waveshare v4 display, power on
2. Wait ~60s for first boot
3. SSH: `ssh pi@pwnbullseye4.local` (password: `raspberry`)

## Configuration

Edit `/etc/pwnagotchi/config.toml`:

```toml
# WPA-Sec (get key at https://wpa-sec.stanev.org)
main.plugins.wpa-sec.enabled = true
main.plugins.wpa-sec.api_key = "YOUR_KEY"

# Display
ui.display.type = "waveshare_4"

# Bluetooth tethering
main.plugins.bt-tether.enabled = true
main.plugins.bt-tether.devices.my-phone.mac = "AA:BB:CC:DD:EE:FF"
```

## Building from Source

### GitHub Actions (recommended)

The CI pipeline builds both architectures automatically:

1. Fork this repo
2. Go to Actions → "Build PwnBullseye4 Images" → Run workflow
3. Download artifacts or wait for auto-release

### Local Build

Requires Linux (Ubuntu 22.04+) with Docker:

```bash
git clone https://github.com/alexdrgpy06/pwnbullseye4
cd pwnbullseye4

# Clone pi-gen
git clone --depth 1 --branch bullseye https://github.com/RPi-Distro/pi-gen.git

# Apply patches
bash build/patches/01-on-chroot-fix.sh pi-gen
bash build/patches/02-stage-setup.sh pi-gen "$(pwd)/build/stage-pwnagotchi"
cp build/config pi-gen/config

# Build
cd pi-gen
sudo ./build-docker.sh
```

Images output to `pi-gen/deploy/`.

## Architecture

```
pwnbullseye4/
├── .github/workflows/build.yml    # CI pipeline
├── ai/                            # ONNX Runtime AI agent
│   ├── agent.py                   # Async inference agent
│   ├── train.py                   # A2C training script
│   └── export_onnx.py             # Model export + quantization
├── build/
│   ├── config                     # Pi-gen build config
│   ├── patches/                   # Pi-gen patches
│   │   ├── 01-on-chroot-fix.sh    # Fix QEMU chroot
│   │   └── 02-stage-setup.sh      # Stage setup
│   └── stage-pwnagotchi/          # Custom pi-gen stage
│       ├── 00-packages/           # apt dependencies
│       ├── 01-bettercap/          # Go + bettercap + pwngrid
│       ├── 02-pwnagotchi/         # lgpio + pwnagotchi
│       └── 03-config/             # Config + systemd services
├── config/                        # Default configurations
│   ├── defaults.toml
│   └── wpa_sec.py
└── docs/                          # Documentation
```

## Credits

Built on the work of:
- [jayofelony/pwnagotchi](https://github.com/jayofelony/pwnagotchi) — noai branch
- [jayofelony/pwnagotchi-bullseye](https://github.com/jayofelony/pwnagotchi-bullseye) — v2.6.4
- [evilsocket/pwnagotchi](https://github.com/evilsocket/pwnagotchi) — original
- [RPi-Distro/pi-gen](https://github.com/RPi-Distro/pi-gen) — image builder

## License

MIT — see [LICENSE](LICENSE).

Upstream pwnagotchi code: GPL-3.0. Pi-gen: BSD-3-Clause.