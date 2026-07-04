#!/usr/bin/env bash
set -euo pipefail

url="${1:-}"
if [[ -z "$url" ]]; then
  echo "Usage: $0 '<facebook-url>'" >&2
  exit 2
fi

cookies_args=()
if [[ -n "${FACEBOOK_COOKIES_FILE:-}" && -f "$FACEBOOK_COOKIES_FILE" ]]; then
  cookies_args=(--cookies "$FACEBOOK_COOKIES_FILE")
fi

yt-dlp "${cookies_args[@]}" -F "$url"
yt-dlp "${cookies_args[@]}" -f "bv*+ba/best" "$url"
