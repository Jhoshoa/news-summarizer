#!/usr/bin/env bash
# Adds a 2GB swapfile if one doesn't already exist. Run once on a fresh
# EC2 instance before the first `docker compose build` -- a 1GiB
# t2.micro/t3.micro will OOM building the frontend (npm ci + vite build)
# without this.
set -euo pipefail

SWAPFILE=/swapfile
SIZE_MB=2048

if swapon --show | grep -q "$SWAPFILE"; then
  echo "Swap already active on $SWAPFILE, nothing to do."
  exit 0
fi

sudo fallocate -l "${SIZE_MB}M" "$SWAPFILE"
sudo chmod 600 "$SWAPFILE"
sudo mkswap "$SWAPFILE"
sudo swapon "$SWAPFILE"

if ! grep -q "^$SWAPFILE " /etc/fstab; then
  echo "$SWAPFILE none swap sw 0 0" | sudo tee -a /etc/fstab
fi

echo "Swap enabled:"
free -h
