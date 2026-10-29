#!/usr/bin/env bash
set -euo pipefail
PAX_WOLF=$(tools/fetch-wolf)
export PAX_WOLF
export PATH="$(dirname "$PAX_WOLF"):$PATH"
"$PAX_WOLF" --version | head -1
exec "$@"
