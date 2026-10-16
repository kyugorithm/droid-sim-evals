#!/usr/bin/env bash
# Reinstall ephemeral container OS libraries; Python/PVC persistence is separate.
set -euo pipefail
sudo -n apt-get update -qq
sudo -n apt-get install -y --no-install-recommends libegl1 libgl1 libvulkan1 libxt6 libglu1-mesa
