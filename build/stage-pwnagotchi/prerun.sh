#!/bin/bash -e
# stage-pwnagotchi prerun: copy previous stage rootfs
if [ "${CLEAN}" = "1" ]; then
	rm -rf "${ROOTFS_DIR}"
fi

copy_previous
