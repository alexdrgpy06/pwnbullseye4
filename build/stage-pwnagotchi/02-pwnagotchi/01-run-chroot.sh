#!/bin/bash -e
# Install lgpio from source and pwnagotchi

echo -e "\e[32m=== Installing lgpio from source ===\e[0m"

cd /opt
if wget -q http://abyz.me.uk/lg/lg.zip; then
    unzip -q lg.zip
    cd lg
    make
    make install
    cd /opt
    rm -rf lg.zip lg/
    echo -e "\e[32m=== lgpio installed ===\e[0m"
else
    echo -e "\e[33m=== lgpio download failed, skipping (non-fatal) ===\e[0m"
fi

echo -e "\e[32m=== Installing pwnagotchi ===\e[0m"

cd /opt
if [ ! -d pwnagotchi ]; then
    git clone --depth 1 https://github.com/jayofelony/pwnagotchi.git
fi
cd pwnagotchi

# Handle armv6 QEMU CPU emulation
if [ "$(uname -m)" = "armv6l" ]; then
    export QEMU_CPU=arm1176
fi

# Create Python virtual environment
echo -e "\e[32m=== Setting up Python venv ===\e[0m"
python3 -m venv /opt/.pwn/ --system-site-packages

# Install pwnagotchi in venv
source /opt/.pwn/bin/activate
pip3 cache purge 2>/dev/null || true
pip3 install --no-cache-dir . || {
    echo -e "\e[33m=== pip install failed, trying with --break-system-packages ===\e[0m"
    pip3 install --no-cache-dir --break-system-packages .
}
deactivate

# Create symlink
ln -sf /opt/.pwn/bin/pwnagotchi /usr/bin/pwnagotchi

# Cleanup
rm -rf /opt/pwnagotchi

echo -e "\e[32m=== pwnagotchi installed ===\e[0m"
