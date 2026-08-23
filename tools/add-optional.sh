#!/usr/bin/env bash
# Adds the "matter of taste" mods as packwiz optional mods.
#
# An optional mod is downloaded only if the player ticks it in the installer
# dialog, which appears on first install and whenever a NEW optional mod shows
# up - not on every launch. This is the alternative to friends installing these
# by hand, which is where duplicate-mod-id crashes come from.
#
# Run from the repo root. Idempotent-ish: re-running re-adds at the newest
# version compatible with pack.toml.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../pack"

# slug|default|description
ENTRIES=(
  "bobby|true|Render distance beyond the server limit. Costs disk space for its chunk cache."
  "rei|true|Recipe and item viewer. Skyblock mods hook into it for item lists."
  "inventoryhudplus|false|Shows your inventory, armor and potion effects on the HUD."
  "vmp-fabric|false|Networking and chunk-loading optimization. The 26.2 build is still alpha."
)

for entry in "${ENTRIES[@]}"; do
  IFS='|' read -r slug default description <<<"$entry"
  echo "==> $slug"
  packwiz mr add "$slug" -y

  toml="mods/${slug}.pw.toml"
  [[ -f "$toml" ]] || { echo "ERROR: expected $toml after add" >&2; exit 1; }

  # packwiz writes no [option] table, so append one. Guard against a second run
  # stacking duplicate tables onto the same file.
  if grep -q '^\[option\]' "$toml"; then
    echo "    [option] already present, left alone"
    continue
  fi
  cat >> "$toml" <<TOML

[option]
optional = true
default = $default
description = "$description"
TOML
done

packwiz refresh
echo
echo "Done. Optional mods:"
grep -l '^\[option\]' mods/*.pw.toml
