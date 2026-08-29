#!/usr/bin/env bash
set -euo pipefail

if ! grep -qi "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
  echo "This setup script is intended for Raspberry Pi hardware."
  exit 2
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

sudo apt-get update
sudo apt-get install -y \
  python3 \
  python3-venv \
  python3-dev \
  python3-picamera2 \
  portaudio19-dev \
  libopenblas-dev \
  espeak-ng

if [[ ! -d .venv ]]; then
  python3 -m venv --system-site-packages .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --force-reinstall .

if [[ ! -f .env ]]; then
  pallattu-ai-assistant init --path .env
  echo
  echo "Created .env. Add OPENAI_API_KEY before starting the assistant."
fi

echo
echo "Raspberry Pi setup complete."
echo "Next run:"
echo "  source .venv/bin/activate"
echo "  pallattu-ai-assistant pi-check"
echo "  pallattu-ai-assistant run"
