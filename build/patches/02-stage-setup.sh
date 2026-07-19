#!/bin/bash
# Set up pi-gen stage structure for PwnBullseye4.
#
# - Copies the official jayofelony stage3 into pi-gen
# - Removes EXPORT_IMAGE from stage2 (we export at stage3)
# - Ensures stage4/5 are skipped

set -euo pipefail

PIGEN_DIR="${1:-.}"
STAGE_SRC="${2:-./pwnagotchi_src/stage3}"

echo "=== Setting up pi-gen stages ==="

# Remove EXPORT_IMAGE from stage2 so it doesn't produce an image
rm -f "${PIGEN_DIR}/stage2/EXPORT_IMAGE"
rm -f "${PIGEN_DIR}/stage2/EXPORT_NOOBS"
echo "Removed EXPORT_IMAGE from stage2"

# Skip stages 4, 5 (we stop at stage3)
for stage in stage4 stage5; do
    if [ -d "${PIGEN_DIR}/${stage}" ]; then
        touch "${PIGEN_DIR}/${stage}/SKIP"
        rm -f "${PIGEN_DIR}/${stage}/EXPORT_IMAGE"
        rm -f "${PIGEN_DIR}/${stage}/EXPORT_NOOBS"
        echo "Skipped ${stage}"
    fi
done

# Copy jayofelony's stage3 into pi-gen
if [ -d "${STAGE_SRC}" ]; then
    # Remove pi-gen default stage3 to prevent copying into stage3/stage3
    rm -rf "${PIGEN_DIR}/stage3"
    cp -a "${STAGE_SRC}" "${PIGEN_DIR}/stage3"
    echo "Copied stage3 → ${PIGEN_DIR}/stage3"
    
    # Fix bullseye package compatibility (downgrade or remove bookworm-specific packages)
    PKG_FILE="${PIGEN_DIR}/stage3/01-pwn-packages/00-packages-nr"
    if [ -f "$PKG_FILE" ]; then
        sed -i '/liblgpio-dev/d' "$PKG_FILE"
        sed -i '/libdtovl0/d' "$PKG_FILE"
        sed -i '/python3-luma/d' "$PKG_FILE"
        sed -i '/libcurl-ocaml-dev/d' "$PKG_FILE"
        sed -i '/libssl-ocaml-dev/d' "$PKG_FILE"
        sed -i 's/libtiff6/libtiff5/g' "$PKG_FILE"
        echo "" >> "$PKG_FILE"
        echo "python3-venv" >> "$PKG_FILE"
        echo "Patched ${PKG_FILE} for Bullseye compatibility"
    fi
    
    # Fix pip cache purge returning exit code 1 on Bullseye when cache is empty
    # and fix Debian's setuptools install_layout bug by upgrading pip and setuptools in the venv
    # and relax python_requires for Bullseye's Python 3.9
    CHROOT_SCRIPT="${PIGEN_DIR}/stage3/05-install-pwnagotchi/01-run-chroot.sh"
    if [ -f "$CHROOT_SCRIPT" ]; then
        python3 - "$CHROOT_SCRIPT" << 'PATCH_EOF'
import sys

path = sys.argv[1]
with open(path, 'r') as f:
    content = f.read()

# Normalize line endings (source file may have CRLF)
content = content.replace('\r\n', '\n')

# 1. Replace python3 -m venv with virtualenv (avoids locale.normalize bug in QEMU chroot)
content = content.replace(
    'python3 -m venv /opt/.pwn/ --system-site-packages',
    'virtualenv --system-site-packages /opt/.pwn/'
)

# 2. Upgrade pip/setuptools before install, make cache purge non-fatal
content = content.replace(
    'pip3 cache purge',
    'pip3 install --upgrade pip setuptools wheel\npip3 cache purge || true'
)

# 3. After git clone, patch pyproject.toml to allow Python 3.9
#    Also remove the original "cd pwnagotchi/" since we cd explicitly
old_block = "    git clone https://github.com/jayofelony/pwnagotchi.git\n    cd pwnagotchi/"
new_block = """    git clone https://github.com/jayofelony/pwnagotchi.git
    cd /opt/pwnagotchi
    sed -i 's/requires-python = ">=3.11"/requires-python = ">=3.9"/' pyproject.toml
    sed -i 's/Programming Language :: Python :: 3.11/Programming Language :: Python :: 3.9/' pyproject.toml"""

content = content.replace(old_block, new_block)

with open(path, 'w') as f:
    f.write(content)

print(f"Patched {path} for Bullseye Python 3.9 compatibility")
PATCH_EOF
    fi
    
    # Pin hcxtools to v6.2.4 (last version compatible with OpenSSL 1.1 on Bullseye)
    HCXTOOLS_SCRIPT="${PIGEN_DIR}/stage3/06-hcxtools/00-run-chroot.sh"
    if [ -f "$HCXTOOLS_SCRIPT" ]; then
        sed -i 's|git clone https://github.com/ZerBea/hcxtools.git hcxtools|git clone --depth 1 --branch 6.2.4 https://github.com/ZerBea/hcxtools.git hcxtools|' "$HCXTOOLS_SCRIPT"
        echo "Pinned hcxtools to v6.2.4 for OpenSSL 1.1 compatibility"
    fi
    
    # Fix /boot/firmware → /boot for Bullseye (Bookworm moved boot to /boot/firmware)
    PATCHES_SCRIPT="${PIGEN_DIR}/stage3/07-patches/00-run.sh"
    if [ -f "$PATCHES_SCRIPT" ]; then
        sed -i 's|/boot/firmware/|/boot/|g' "$PATCHES_SCRIPT"
        echo "Patched ${PATCHES_SCRIPT}: /boot/firmware → /boot"
    fi
else
    echo "ERROR: Stage source not found: ${STAGE_SRC}"
    exit 1
fi

echo "=== Stage setup complete ==="
echo "Active stages: stage0 stage1 stage2 stage3"
