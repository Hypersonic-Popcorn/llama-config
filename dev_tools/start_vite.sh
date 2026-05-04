#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../frontend"
npx vite --host 0.0.0.0
