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

# Copy our custom stage into pi-gen (Docker build doesn't support symlinks pointing outside the volume)
if [ -d "${STAGE_SRC}" ]; then
    cp -r "${STAGE_SRC}" "${PIGEN_DIR}/stage3"
    echo "Copied stage3 → ${PIGEN_DIR}/stage3"
else
    echo "ERROR: Stage source not found: ${STAGE_SRC}"
    exit 1
fi

echo "=== Stage setup complete ==="
echo "Active stages: stage0 stage1 stage2 stage3"
