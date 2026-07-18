#!/bin/bash
# Set up pi-gen stage structure for PwnBullseye4.
#
# - Symlinks our custom stage-pwnagotchi into pi-gen
# - Removes EXPORT_IMAGE from stage2 (we export at stage-pwnagotchi)
# - Ensures stage3/4/5 are skipped

set -euo pipefail

PIGEN_DIR="${1:-.}"
STAGE_SRC="${2:-./build/stage-pwnagotchi}"

echo "=== Setting up pi-gen stages ==="

# Remove EXPORT_IMAGE from stage2 so it doesn't produce an image
rm -f "${PIGEN_DIR}/stage2/EXPORT_IMAGE"
rm -f "${PIGEN_DIR}/stage2/EXPORT_NOOBS"
echo "Removed EXPORT_IMAGE from stage2"

# Skip stages 3, 4, 5 (we replace with our custom stage)
for stage in stage3 stage4 stage5; do
    if [ -d "${PIGEN_DIR}/${stage}" ]; then
        touch "${PIGEN_DIR}/${stage}/SKIP"
        rm -f "${PIGEN_DIR}/${stage}/EXPORT_IMAGE"
        rm -f "${PIGEN_DIR}/${stage}/EXPORT_NOOBS"
        echo "Skipped ${stage}"
    fi
done

# Symlink our custom stage into pi-gen
if [ -d "${STAGE_SRC}" ]; then
    ln -sfn "$(realpath "${STAGE_SRC}")" "${PIGEN_DIR}/stage-pwnagotchi"
    echo "Linked stage-pwnagotchi → ${STAGE_SRC}"
else
    echo "ERROR: Stage source not found: ${STAGE_SRC}"
    exit 1
fi

echo "=== Stage setup complete ==="
echo "Active stages: stage0 stage1 stage2 stage-pwnagotchi"
