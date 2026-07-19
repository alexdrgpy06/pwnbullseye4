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

# 1. Upgrade pip/setuptools before install, make cache purge non-fatal
content = content.replace(
    'pip3 cache purge',
    'pip3 install --upgrade pip setuptools wheel\npip3 cache purge || true'
)

# 2. After git clone, patch pyproject.toml to allow Python 3.9
old_clone = 'git clone https://github.com/jayofelony/pwnagotchi.git'
new_clone = old_clone + """
    cd /opt/pwnagotchi
    sed -i 's/requires-python = ">=3.11"/requires-python = ">=3.9"/' pyproject.toml
    sed -i 's/Programming Language :: Python :: 3.11/Programming Language :: Python :: 3.9/' pyproject.toml"""

content = content.replace(old_clone, new_clone)

with open(path, 'w') as f:
    f.write(content)

print(f"Patched {path} for Bullseye Python 3.9 compatibility")
PATCH_EOF
    fi
else
    echo "ERROR: Stage source not found: ${STAGE_SRC}"
    exit 1
fi

echo "=== Stage setup complete ==="
echo "Active stages: stage0 stage1 stage2 stage3"
