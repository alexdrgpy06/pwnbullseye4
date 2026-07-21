# Implementation Plan

## Overview
Transition the PwnBullseye4 build pipeline to use Pwnagotchi v2.8.9 release and pre-install optimized ARMv6l PyTorch/Torchvision wheels for Python 3.9 compatibility on 32-bit Debian Bullseye.

## Types
The build pipeline now targets Python 3.9 runtime with ARMv6l architecture, requiring pre-installation of PyTorch and Torchvision wheels from the Sniffleupagus release.

## Files
Modifications include:
- Updated `.github/workflows/build.yml` to clone the `v2.8.9` tag of the pwnagotchi repository.
- Modified `build/patches/02-stage-setup.sh` to download and pre-install PyTorch/Torchvision wheels before package installation, with cleanup of wheel files.
- No new files created; existing patch scripts remain.
- Configuration updates in `pyproject.toml` to relax Python version constraints.

Detailed breakdown:
- New files: None
- Modified files: 
  - `.github/workflows/build.yml` (clone specific tag)
  - `build/patches/02-stage-setup.sh` (add wheel download and install steps)
  - Possibly `build/config` (if config changes needed)
- Deleted files: None
- Moved files: None

## Functions
No new or modified functions at the script level; the changes are focused on pipeline configuration and stage setup.

## Classes
No class modifications.

## Dependencies
- Added direct dependencies on `torch-2.1.0a0+gitunknown-cp39-cp39-linux_armv6l.whl` and `torchvision-0.16.0a0-cp39-cp39-linux_armv6l.whl` from Sniffleupagus release v1.0.0.
- Updated `pyproject.toml` to allow Python 3.9 runtime without stricter version checks.

## Testing
- Verify successful image build in GitHub Actions for both armhf and armv7 architectures.
- Confirm that PyTorch and Torchvision are correctly installed in the chroot environment.
- Run basic functionality tests for Pwnagotchi AI inference to ensure compatibility.

## Implementation Order
1. Update `.github/workflows/build.yml` to enforce `v2.8.9` branch checkout.
2. Modify `build/patches/02-stage-setup.sh` to include PyTorch/Torchvision wheel download, installation, and cleanup.
3. Ensure `pyproject.toml` Python version constraints are appropriately configured.
4. Execute build pipeline and validate image generation and PyTorch functionality.