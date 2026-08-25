#!/usr/bin/env bash
# Build SAKSHYA for a single-service deployment.
#
# Produces frontend/dist (served by FastAPI) and installs the backend
# dependencies. Run from the repository root:
#
#     bash scripts/build.sh
#
# Invoked via `bash` rather than executed directly, so the build never depends
# on the executable bit surviving a commit made from Windows.
set -euo pipefail

cd "$(dirname "$0")/.."

# Fail loudly and specifically. A missing toolchain otherwise surfaces as an
# opaque "command not found" partway through a build log.
for tool in node npm python; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: '$tool' is not available on this build machine." >&2
        echo "       SAKSHYA builds a React frontend and a Python API in one" >&2
        echo "       service, so the builder needs Node 18+ and Python 3.11+." >&2
        echo "       If your host's Python image has no Node, either enable it" >&2
        echo "       or build the frontend separately and commit frontend/dist." >&2
        exit 1
    fi
done

echo "==> Node $(node --version) / npm $(npm --version) / $(python --version 2>&1)"

echo "==> Building frontend"
cd frontend
npm ci
npm run build
cd ..

if [ ! -f frontend/dist/index.html ]; then
    echo "ERROR: frontend build produced no frontend/dist/index.html" >&2
    exit 1
fi

echo "==> Installing backend dependencies"
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt

echo "==> Build complete"
echo "    frontend/dist: $(du -sh frontend/dist 2>/dev/null | cut -f1)"
