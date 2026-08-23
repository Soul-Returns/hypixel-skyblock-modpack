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

# packwiz-installer is shipped rather than self-updated. Left to update itself,
# the bootstrap calls api.github.com on EVERY launch; that endpoint allows 60
# unauthenticated requests per hour per IP, and once it 403s the bootstrap fails
# to load the installer at all and the game does not start. Several players
# behind one NAT would break each other's launches.
INSTALLER_VERSION="v0.5.14"
INSTALLER_SHA256="c9f646908d340d84773948a9a7d98bc1dae250d35e1016dc6e2b8459760b5598"
INSTALLER_URL="https://github.com/packwiz/packwiz-installer/releases/download/${INSTALLER_VERSION}/packwiz-installer.jar"

fetch_pinned() {
  local name="$1" version="$2" url="$3" want="$4"
  local cache="$HERE/.cache/${name}-${version}.jar"
  mkdir -p "$(dirname "$cache")"

  if [[ ! -f "$cache" ]]; then
    echo "==> downloading $name $version" >&2
    curl -fsSL -o "$cache.tmp" "$url"
    mv "$cache.tmp" "$cache"
  fi

  # These jars run on every player's machine before Minecraft does.
  if ! echo "$want  $cache" | sha256sum -c - >/dev/null 2>&1; then
    echo "ERROR: $name hash mismatch - refusing to build" >&2
    rm -f "$cache"
    exit 1
  fi
  echo "$cache"
}

BOOTSTRAP_JAR="$(fetch_pinned packwiz-installer-bootstrap "$BOOTSTRAP_VERSION" "$BOOTSTRAP_URL" "$BOOTSTRAP_SHA256")"
INSTALLER_JAR="$(fetch_pinned packwiz-installer "$INSTALLER_VERSION" "$INSTALLER_URL" "$INSTALLER_SHA256")"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

# Prism reads both "minecraft" and ".minecraft"; this matches what Prism
# itself writes on Linux.
mkdir -p "$STAGE/minecraft"
cp "$HERE/instance/instance.cfg" "$HERE/instance/mmc-pack.json" "$STAGE/"
cp "$BOOTSTRAP_JAR" "$STAGE/minecraft/packwiz-installer-bootstrap.jar"
cp "$INSTALLER_JAR" "$STAGE/minecraft/packwiz-installer.jar"

mkdir -p "$(dirname "$OUT")"
rm -f "$OUT"
( cd "$STAGE" && zip -qr "$OUT" . )

echo "==> $OUT"
unzip -l "$OUT"
