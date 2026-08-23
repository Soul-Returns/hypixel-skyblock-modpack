#!/usr/bin/env bash
# Builds the Prism Launcher instance zip that friends import once.
#
# The zip contains no mods and no configs - only the launcher settings and the
# packwiz bootstrap. Everything else is pulled from the pack URL on first
# launch, which is also what makes every later launch an update.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="${1:-$HERE/../dist/Hypixel-Skyblock.zip}"

BOOTSTRAP_VERSION="v0.0.3"
BOOTSTRAP_SHA256="a8fbb24dc604278e97f4688e82d3d91a318b98efc08d5dbfcbcbcab6443d116c"
BOOTSTRAP_URL="https://github.com/packwiz/packwiz-installer-bootstrap/releases/download/${BOOTSTRAP_VERSION}/packwiz-installer-bootstrap.jar"

CACHE="$HERE/.cache/packwiz-installer-bootstrap-${BOOTSTRAP_VERSION}.jar"
mkdir -p "$(dirname "$CACHE")"

if [[ ! -f "$CACHE" ]]; then
  echo "==> downloading packwiz-installer-bootstrap $BOOTSTRAP_VERSION"
  curl -fsSL -o "$CACHE.tmp" "$BOOTSTRAP_URL"
  mv "$CACHE.tmp" "$CACHE"
fi

# Pinned hash: this jar runs on every friend's machine before Minecraft does.
echo "$BOOTSTRAP_SHA256  $CACHE" | sha256sum -c - >/dev/null || {
  echo "ERROR: bootstrap jar hash mismatch - refusing to build" >&2
  rm -f "$CACHE"
  exit 1
}

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

# Prism reads both "minecraft" and ".minecraft"; this matches what Prism
# itself writes on Linux.
mkdir -p "$STAGE/minecraft"
cp "$HERE/instance/instance.cfg" "$HERE/instance/mmc-pack.json" "$STAGE/"
cp "$CACHE" "$STAGE/minecraft/packwiz-installer-bootstrap.jar"

mkdir -p "$(dirname "$OUT")"
rm -f "$OUT"
( cd "$STAGE" && zip -qr "$OUT" . )

echo "==> $OUT"
unzip -l "$OUT"
