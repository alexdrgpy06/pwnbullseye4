#!/bin/bash
# Patch pi-gen's on_chroot() to use plain chroot instead of capsh.
#
# WHY: capsh drops capabilities required for binfmt_misc to function,
# causing QEMU user-mode ARM emulation to fail with "Input/output error"
# when building on x86_64 hosts (GitHub Actions, Docker, WSL2).
#
# This was the #1 blocker in 60+ build attempts during Hermes #20.

set -euo pipefail

PIGEN_DIR="${1:-.}"
COMMON="${PIGEN_DIR}/scripts/common"

if [ ! -f "$COMMON" ]; then
    echo "ERROR: $COMMON not found"
    exit 1
fi

echo "=== Patching on_chroot() in scripts/common ==="

# Replace the on_chroot function with our fixed version
# The original uses: capsh $CAPSH_ARG -- -c "chroot ${ROOTFS_DIR} ..."
# Our fix uses: plain chroot with explicit environment variables

# First, check if already patched
if grep -q "# PATCHED: plain chroot for binfmt_misc" "$COMMON"; then
    echo "Already patched, skipping."
    exit 0
fi

# Create the patched on_chroot function
# We use python to do a reliable multi-line replacement
python3 << 'PYEOF'
import re
import sys

common_path = sys.argv[1] if len(sys.argv) > 1 else "scripts/common"

with open(common_path, 'r') as f:
    content = f.read()

# Pattern to match the entire on_chroot function
# It starts with "on_chroot()" and ends before "export -f on_chroot"
old_pattern = r'on_chroot\(\)\s*\{[^}]*\}\s*\nexport -f on_chroot'

new_function = '''on_chroot() {
\t# PATCHED: plain chroot for binfmt_misc compatibility (no capsh)
\tif ! mount | grep -q "$(realpath "${ROOTFS_DIR}"/proc)"; then
\t\tmount -t proc proc "${ROOTFS_DIR}/proc"
\tfi

\tif ! mount | grep -q "$(realpath "${ROOTFS_DIR}"/dev)"; then
\t\tmount --bind /dev "${ROOTFS_DIR}/dev"
\tfi

\tif ! mount | grep -q "$(realpath "${ROOTFS_DIR}"/dev/pts)"; then
\t\tmount --bind /dev/pts "${ROOTFS_DIR}/dev/pts"
\tfi

\tif ! mount | grep -q "$(realpath "${ROOTFS_DIR}"/sys)"; then
\t\tmount --bind /sys "${ROOTFS_DIR}/sys"
\tfi

\tDEBIAN_FRONTEND=noninteractive \\
\tDEBCONF_NONINTERACTIVE_SEEN=true \\
\tHOME=/root \\
\tPATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \\
\tLC_ALL=C \\
\tLANG=C \\
\tchroot "${ROOTFS_DIR}" "$@"
}
export -f on_chroot'''

new_content = re.sub(old_pattern, new_function, content, flags=re.DOTALL)

if new_content == content:
    print("WARNING: Pattern not matched, trying simpler replacement...")
    # Simpler approach: just replace the capsh line
    new_content = content.replace(
        'capsh $CAPSH_ARG -- -c "',
        'DEBIAN_FRONTEND=noninteractive DEBCONF_NONINTERACTIVE_SEEN=true HOME=/root PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin LC_ALL=C LANG=C chroot "${ROOTFS_DIR}" '
    )

with open(common_path, 'w') as f:
    f.write(new_content)

print("on_chroot() patched successfully")
PYEOF

echo "=== Patch applied ==="
