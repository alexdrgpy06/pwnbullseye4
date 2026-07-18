#!/bin/bash -e
# Enable services and apply final tweaks inside the chroot

echo -e "\e[32m=== Enabling services ===\e[0m"

# Enable pwnagotchi services
systemctl enable pwnagotchi.service
systemctl enable bettercap.service
systemctl enable pwngrid-peer.service

# Enable SSH
systemctl enable ssh

# Set hostname
echo "pwnbullseye4" > /etc/hostname
sed -i 's/127.0.1.1.*/127.0.1.1\tpwnbullseye4/' /etc/hosts

# Configure swap (1GB for AI model)
echo "CONF_SWAPSIZE=1024" > /etc/dphys-swapfile

# Set CPU governor to performance (Pi Zero 2 W)
echo 'GOVERNOR="performance"' > /etc/default/cpufrequtils 2>/dev/null || true

# Create pwnagotchi user data directory
mkdir -p /root/handshakes
mkdir -p /root/peers

# Set permissions
chmod 755 /usr/bin/pwnagotchi 2>/dev/null || true
chmod 755 /usr/local/bin/bettercap 2>/dev/null || true
chmod 755 /usr/local/bin/pwngrid 2>/dev/null || true

echo -e "\e[32m=== Services enabled, system configured ===\e[0m"
