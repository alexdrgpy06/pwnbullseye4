#!/bin/bash
set -e

# The official pi-gen bullseye branch accidentally includes '^orphan_file'
# in the ROOT_FEATURES for mkfs.ext4. However, Debian Bullseye uses e2fsprogs 1.46.2,
# which predates the 'orphan_file' feature (added in 1.47.0).
# This causes the build to fail at the very end when creating the image.
# We patch export-image/prerun.sh to remove it.

PIGEN_DIR="${1:-pi-gen}"
PRERUN_SCRIPT="${PIGEN_DIR}/export-image/prerun.sh"

if [ -f "${PRERUN_SCRIPT}" ]; then
    echo "Patching export-image/prerun.sh to remove ^orphan_file..."
    sed -i 's/\^orphan_file//g' "${PRERUN_SCRIPT}"
    
    # Also clean up any trailing commas that might have been left if it was the last item,
    # or double commas if it was in the middle.
    sed -i 's/,,/,/g' "${PRERUN_SCRIPT}"
    sed -i 's/,$//g' "${PRERUN_SCRIPT}"
    sed -i 's/="^huge_file,"/="^huge_file"/g' "${PRERUN_SCRIPT}"
    
    echo "export-image/prerun.sh patched successfully"
else
    echo "WARNING: ${PRERUN_SCRIPT} not found!"
fi
