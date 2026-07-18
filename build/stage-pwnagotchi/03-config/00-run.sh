#!/bin/bash -e
# Copy configuration files into the rootfs

echo -e "\e[32m=== Installing PwnBullseye4 configuration ===\e[0m"

# Create pwnagotchi directories
install -v -d "${ROOTFS_DIR}/etc/pwnagotchi"
install -v -d "${ROOTFS_DIR}/etc/pwnagotchi/log"
install -v -d "${ROOTFS_DIR}/etc/pwnagotchi/conf.d/"
install -v -d "${ROOTFS_DIR}/etc/pwnagotchi/custom-plugins/"
install -v -d "${ROOTFS_DIR}/etc/pwnagotchi/handshakes/"
install -v -d "${ROOTFS_DIR}/etc/pwnagotchi/backups/"
install -v -d "${ROOTFS_DIR}/etc/pwnagotchi/sessions/"
install -v -d "${ROOTFS_DIR}/usr/local/share/pwnagotchi/custom-plugins/"

# Copy config files from our files/ directory
install -v -m 644 files/defaults.toml \
    "${ROOTFS_DIR}/etc/pwnagotchi/default.toml"

install -v -m 644 files/config.toml.example \
    "${ROOTFS_DIR}/etc/pwnagotchi/config.toml"

# Install WPA-Sec plugin
install -v -m 644 files/wpa_sec.py \
    "${ROOTFS_DIR}/usr/local/share/pwnagotchi/custom-plugins/wpa-sec.py"

# Create systemd service for pwnagotchi
cat > "${ROOTFS_DIR}/etc/systemd/system/pwnagotchi.service" << 'SYSTEMD'
[Unit]
Description=pwnagotchi
After=network.target
Wants=network.target

[Service]
Type=simple
ExecStart=/usr/bin/pwnagotchi
Restart=always
RestartSec=10
User=root
WorkingDirectory=/root

[Install]
WantedBy=multi-user.target
SYSTEMD

# Create systemd service for bettercap
cat > "${ROOTFS_DIR}/etc/systemd/system/bettercap.service" << 'SYSTEMD'
[Unit]
Description=bettercap
After=network.target
Before=pwnagotchi.service

[Service]
Type=simple
ExecStart=/usr/local/bin/bettercap -no-colors -caplet pwnagotchi-auto -iface wlan0mon
Restart=always
RestartSec=5
User=root
Environment=HOME=/root

[Install]
WantedBy=multi-user.target
SYSTEMD

# Create pwngrid-peer service
cat > "${ROOTFS_DIR}/etc/systemd/system/pwngrid-peer.service" << 'SYSTEMD'
[Unit]
Description=pwngrid-peer
After=network.target bettercap.service
Wants=bettercap.service

[Service]
Type=simple
ExecStart=/usr/local/bin/pwngrid -peer -iface wlan0mon -wait
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
SYSTEMD

echo -e "\e[32m=== Configuration installed ===\e[0m"
