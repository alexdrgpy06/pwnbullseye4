#!/bin/bash

# This script injects an OS optimization stage into pi-gen

PIGEN_DIR="$1"
STAGE_DIR="${PIGEN_DIR}/stage3/07-os-optimizations"

mkdir -p "$STAGE_DIR"

# 1. Packages to install
cat << 'EOF' > "${STAGE_DIR}/00-packages"
cpufrequtils
EOF

# 2. Host-side script to append overclocking to config.txt (only if armv7)
cat << 'EOF' > "${STAGE_DIR}/00-run.sh"
#!/bin/bash -e

# Target arch is exported from build.yml via pi-gen/config
if [ "${TARGET_ARCH}" = "armv7" ]; then
    echo "Applying Pi Zero 2 W Overclock settings to config.txt"
    cat << 'CONFIG_EOF' >> "${ROOTFS_DIR}/boot/config.txt"

# Pwnbullseye4 Pi Zero 2 W Overclock Optimizations
arm_freq=1000
over_voltage=6
gpu_freq=400
CONFIG_EOF
fi
EOF

# 3. Chroot-side script
cat << 'EOF' > "${STAGE_DIR}/01-run-chroot.sh"
#!/bin/bash -e

echo "Applying OS optimizations..."

# Increase swap to 1024MB for AI
if grep -q "^CONF_SWAPSIZE=" /etc/dphys-swapfile; then
    sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=1024/' /etc/dphys-swapfile
else
    echo "CONF_SWAPSIZE=1024" >> /etc/dphys-swapfile
fi

# Set CPU Governor to performance
echo 'GOVERNOR="performance"' > /etc/default/cpufrequtils

# Fix Bluetooth coexistence for tethering
if [ ! -d "/etc/modprobe.d" ]; then
    mkdir -p /etc/modprobe.d
fi
echo "options brcmfmac roam_off=1" > /etc/modprobe.d/brcmfmac.conf
EOF

chmod +x "${STAGE_DIR}/00-run.sh"
chmod +x "${STAGE_DIR}/01-run-chroot.sh"

echo "OS optimizations stage injected."
