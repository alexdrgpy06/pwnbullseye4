#!/bin/bash -e
# Install Go, Bettercap, and pwngrid

export PATH=$PATH:/usr/local/go/bin

# Detect architecture
GOARCH="armv6l"
case "$(uname -m)" in
    armv6l|armv7l) GOARCH="armv6l" ;;
    aarch64)       GOARCH="arm64" ;;
    x86_64)        GOARCH="amd64" ;;
esac

GO_VERSION="1.22.5"
GO_FILE="go${GO_VERSION}.linux-${GOARCH}.tar.gz"

echo -e "\e[32m=== Installing Go ${GO_VERSION} (${GOARCH}) ===\e[0m"

pushd /tmp
if curl -fSL "https://go.dev/dl/${GO_FILE}" -o "${GO_FILE}"; then
    rm -rf /usr/local/go
    tar -C /usr/local -xzf "${GO_FILE}"
    echo -e "\e[32m=== Go installed ===\e[0m"
else
    echo -e "\e[31m=== Go download failed ===\e[0m"
    exit 1
fi
rm -f "${GO_FILE}"
popd

echo 'export PATH=$PATH:/usr/local/go/bin' >> /etc/profile
export PATH=$PATH:/usr/local/go/bin

echo -e "\e[32m=== Installing Bettercap ===\e[0m"

# Install bettercap from source
cd /tmp
git clone --depth 1 https://github.com/bettercap/bettercap.git
cd bettercap
go build -o /usr/local/bin/bettercap .
cd /tmp
rm -rf bettercap

echo -e "\e[32m=== Installing pwngrid ===\e[0m"

# Install pwngrid
cd /tmp
git clone --depth 1 https://github.com/jayofelony/pwngrid.git
cd pwngrid
go build -o /usr/local/bin/pwngrid cmd/pwngrid/*.go
cd /tmp
rm -rf pwngrid

# Create bettercap data directories
mkdir -p /usr/local/share/bettercap/caplets
mkdir -p /usr/local/share/bettercap/ui

# Download bettercap caplets
cd /tmp
git clone --depth 1 https://github.com/bettercap/caplets.git
cp -r caplets/* /usr/local/share/bettercap/caplets/ 2>/dev/null || true
rm -rf caplets

echo -e "\e[32m=== Bettercap + pwngrid installed ===\e[0m"
