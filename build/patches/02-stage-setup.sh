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
        sed -i 's/libtiff6/libtiff5/g' "$PKG_FILE"
        echo "Patched ${PKG_FILE} for Bullseye compatibility"
    fi
else
    echo "ERROR: Stage source not found: ${STAGE_SRC}"
    exit 1
fi

echo "=== Stage setup complete ==="
echo "Active stages: stage0 stage1 stage2 stage3"
