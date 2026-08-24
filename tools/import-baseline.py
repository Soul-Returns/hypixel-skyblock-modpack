#!/usr/bin/env python3
"""Import a configured instance into the pack as the shipped baseline.

Usage:
    tools/import-baseline.py ~/.local/share/PrismLauncher/instances/<name>/minecraft

Point this at an instance created FROM this pack, configured the way players
should receive it. What gets shipped is deliberate, not "whatever is in the
config folder":

  * Game settings are split into first-launch-only options and per-key keybind
    defaults, because Default Options treats the two differently. See README.
  * Mod configs are shipped only if listed in SHIP_CONFIGS. Most mod config
    files are just the mod's own generated defaults, and shipping those adds
    files to every player's instance that say nothing.

Anything found but not shipped is printed, so nothing is dropped silently.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK_CONFIG = ROOT / "pack" / "config"
DEFAULTS_DIR = "defaultoptions"

# Mod configs worth shipping: ones where we deliberately changed something.
# Everything else is regenerated identically on any fresh install.
SHIP_CONFIGS = [
    "sodium-options.json",
    "sodium-extra-options.json",
]

# Machine-local files that must never ship even if allowlisted above.
EXCLUDE_FILES = {
    "sodium-fingerprint.json",   # hardware fingerprint of the machine it ran on
}

# Repo/cache directories: hundreds of MB, refetched on demand.
EXCLUDE_DIRS = {
    "skyhanni/repo", "skyhanni/backup", "skyhanni/logs",
    "skyblocker/item-repo",
    "notenoughupdates",
    "firmament/repo",
    "skyblockapi",
}

# Option lines dropped from the shipped options.txt. Minecraft recreates each of
# these at its own default on first launch, which is the point: these are
# settings we refuse to decide on someone else's behalf.
DROP_OPTIONS = {
    "fullscreen": "forcing fullscreen on a first launch is hostile",
    "exclusiveFullscreen": "follows fullscreen",
    "renderDistance": "pending bobby setup",
    "simulationDistance": "pending bobby setup",
}

# Values forced regardless of what the source instance had.
OPTION_OVERRIDES = {
    "soundDevice": '""',                 # names a specific audio device
    "resourcePacks": "[]",
    "incompatibleResourcePacks": "[]",
    "lastServer": "",
    "damageTiltStrength": "0.0",          # accessibility: no screen tilt on damage
    "sharePresence": '"none"',            # vanilla 26.2 friend presence: Hidden
}


def read_options(path):
    """options.txt as an ordered list of (key, value) plus raw non-kv lines."""
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition(":")
        entries.append((key, value) if sep else (None, line))
    return entries


def write_options(entries, path):
    out = []
    dropped, overridden = [], []
    for key, value in entries:
        if key is None:
            out.append(value)
            continue
        if key.startswith("key_"):
            continue                      # keybinds live in keybindings.txt
        if key in DROP_OPTIONS:
            dropped.append(key)
            continue
        if key in OPTION_OVERRIDES and value != OPTION_OVERRIDES[key]:
            overridden.append((key, value, OPTION_OVERRIDES[key]))
            value = OPTION_OVERRIDES[key]
        out.append(f"{key}:{value}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return dropped, overridden


def write_keybindings(entries, path):
    """Derive keybindings.txt from options.txt.

    '/defaultoptions saveAll' writes this file, but it needs a world to run in.
    options.txt already holds every binding, and the only difference in format
    is a trailing modifier field, so deriving it needs no game session.
    """
    lines = []
    for key, value in entries:
        if key and key.startswith("key_"):
            lines.append(f"{key}:{value}:")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


def excluded(rel):
    posix = rel.as_posix()
    if rel.name in EXCLUDE_FILES:
        return True
    return any(posix == d or posix.startswith(d + "/") for d in EXCLUDE_DIRS)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("instance", type=Path, help="the instance's minecraft/ directory")
    parser.add_argument("--no-refresh", action="store_true",
                        help="skip 'packwiz refresh' at the end")
    args = parser.parse_args()

    mc = args.instance
    src_config = mc / "config"
    if not src_config.is_dir():
        return fail(f"{src_config} is not a directory - point me at an instance's minecraft/ dir")
    if not (mc / "options.txt").is_file():
        return fail(f"{mc}/options.txt is missing - launch the instance once first")

    if PACK_CONFIG.exists():
        shutil.rmtree(PACK_CONFIG)
    defaults = PACK_CONFIG / DEFAULTS_DIR
    defaults.mkdir(parents=True)

    entries = read_options(mc / "options.txt")
    dropped, overridden = write_options(entries, defaults / "options.txt")
    bindings = write_keybindings(entries, defaults / "keybindings.txt")

    settings = sum(1 for k, _ in entries if k and not k.startswith("key_"))
    print(f"options.txt      {settings - len(dropped)} settings")
    print(f"keybindings.txt  {bindings} bindings")
    for key in dropped:
        print(f"  dropped {key:<22} {DROP_OPTIONS[key]}")
    for key, was, now in overridden:
        print(f"  forced  {key:<22} {was} -> {now}")

    servers = mc / "servers.dat"
    if servers.is_file():
        shutil.copy2(servers, defaults / "servers.dat")
        print(f"servers.dat      copied ({servers.stat().st_size} bytes)")
    else:
        print("servers.dat      MISSING - players get an empty server list")

    print("\nmod configs")
    shipped = set()
    for name in SHIP_CONFIGS:
        src = src_config / name
        if not src.is_file():
            print(f"  MISSING  {name}")
            continue
        if excluded(Path(name)):
            print(f"  excluded {name}")
            continue
        dest = PACK_CONFIG / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        shipped.add(name)
        print(f"  shipped  {name}")

    # Report, never silently drop: an unshipped config may be an oversight.
    others = sorted(
        p.relative_to(src_config).as_posix()
        for p in src_config.rglob("*")
        if p.is_file()
        and p.relative_to(src_config).parts[0] != DEFAULTS_DIR
        and p.relative_to(src_config).as_posix() not in shipped
        and not excluded(p.relative_to(src_config))
    )
    if others:
        print(f"\nnot shipped ({len(others)}) - mod defaults, regenerated on any install")
        for name in others:
            print(f"  {name}")
        print("  add to SHIP_CONFIGS in this script if one of these was tuned")

    if args.no_refresh:
        print("\nskipped refresh - run 'packwiz refresh' in pack/ before committing")
        return 0
    print()
    return subprocess.call(["packwiz", "refresh"], cwd=ROOT / "pack")


def fail(message):
    print(f"error: {message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
