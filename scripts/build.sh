#!/usr/bin/env bash
# Build SAKSHYA for a single-service deployment.
#
# Produces frontend/dist (served by FastAPI) and installs the backend
# dependencies. Run from the repository root.
set -euo pipefail

echo "==> Building frontend"
cd frontend
npm ci
npm run build
cd ..

echo "==> Installing backend dependencies"
cd backend
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cd ..

echo "==> Build complete"
echo "    frontend bundle: $(du -sh frontend/dist 2>/dev/null | cut -f1)"
