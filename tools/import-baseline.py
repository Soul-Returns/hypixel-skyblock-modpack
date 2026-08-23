#!/usr/bin/env python3
"""Import a configured instance into the pack as the shipped baseline.

Usage:
    tools/import-baseline.py ~/.local/share/PrismLauncher/instances/<name>/minecraft

Run this against an instance that was created FROM this pack. That matters: a
fresh pack instance's config directory contains configs for exactly the mods the
pack ships, so there is nothing to allowlist. Pointing it at an old instance
would drag in configs for mods that are not in the pack.

Before running it, in game:
    /defaultoptions saveAll
That writes config/defaultoptions/{options.txt,keybindings.txt,servers.dat},
which is what the pack ships instead of a bare options.txt.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK_CONFIG = ROOT / "pack" / "config"

# Never shipped. Mod-downloaded item/price repositories are hundreds of
# megabytes and are refetched on demand; the rest is machine- or account-local.
EXCLUDE_DIRS = {
    "skyhanni/repo", "skyhanni/backup", "skyhanni/logs",
    "skyblocker/item-repo",
    "notenoughupdates",
    "firmament/repo",
    "skyblockapi",
}
EXCLUDE_FILES = {
    "sodium-fingerprint.json",   # hardware fingerprint of the machine it ran on
}

# Values in the shipped options.txt that describe the maintainer's machine
# rather than a preference. Left in place, they break other people's game.
OPTION_OVERRIDES = {
    "soundDevice": '""',
    "resourcePacks": '["vanilla"]',
    "incompatibleResourcePacks": "[]",
    "lastServer": "",
}


def is_excluded(rel: Path) -> bool:
    posix = rel.as_posix()
    if rel.name in EXCLUDE_FILES:
        return True
    return any(posix == d or posix.startswith(d + "/") for d in EXCLUDE_DIRS)


def sanitize_options(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    changed, out = [], []
    for line in lines:
        key = line.split(":", 1)[0] if ":" in line else None
        if key in OPTION_OVERRIDES:
            out.append(f"{key}:{OPTION_OVERRIDES[key]}")
            changed.append(key)
        else:
            out.append(line)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("instance", type=Path,
                        help="the instance's minecraft/ directory")
    parser.add_argument("--only", choices=("defaults", "configs"),
                        help="import only the game defaults (options, keybinds, "
                             "server list) or only the mod configs; both by default")
    parser.add_argument("--no-refresh", action="store_true",
                        help="skip 'packwiz refresh' at the end")
    args = parser.parse_args()
    want_defaults = args.only in (None, "defaults")
    want_configs = args.only in (None, "configs")

    src_config = args.instance / "config"
    if not src_config.is_dir():
        return fail(f"{src_config} is not a directory - point me at an instance's minecraft/ dir")

    defaults = src_config / "defaultoptions"
    if want_defaults and not (defaults / "keybindings.txt").is_file():
        return fail(f"{defaults}/keybindings.txt is missing.\n"
                    "Run '/defaultoptions saveAll' in game first, otherwise the pack "
                    "would ship no keybind or option defaults at all.")

    # Replace rather than merge, per section: a leftover config for a mod that has
    # since been removed from the pack would otherwise be shipped forever.
    for section, wanted in (("defaultoptions", want_defaults), (None, want_configs)):
        if not wanted:
            continue
        if section:
            target = PACK_CONFIG / section
            if target.exists():
                shutil.rmtree(target)
        else:
            for child in (PACK_CONFIG.iterdir() if PACK_CONFIG.exists() else ()):
                if child.name == "defaultoptions":
                    continue
                shutil.rmtree(child) if child.is_dir() else child.unlink()
    PACK_CONFIG.mkdir(parents=True, exist_ok=True)

    copied = skipped = 0
    for path in sorted(src_config.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(src_config)
        in_defaults = rel.parts[0] == "defaultoptions"
        if not (want_defaults if in_defaults else want_configs):
            continue
        if is_excluded(rel):
            skipped += 1
            continue
        dest = PACK_CONFIG / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        copied += 1

    print(f"copied {copied} config files, skipped {skipped} excluded")

    options = PACK_CONFIG / "defaultoptions" / "options.txt"
    if want_defaults and options.is_file():
        changed = sanitize_options(options)
        print(f"sanitized machine-specific options: {', '.join(changed) or 'none'}")
    elif want_defaults:
        print("WARNING: no defaultoptions/options.txt - video defaults will not ship")

    # The pack must not carry these: Default Options owns them inside the
    # player's instance, and shipping them through packwiz would overwrite
    # everyone's live settings on every change.
    for stray in ("options.txt", "servers.dat"):
        leaked = ROOT / "pack" / stray
        if leaked.exists():
            leaked.unlink()
            print(f"removed pack/{stray} (belongs under config/defaultoptions/)")

    if args.no_refresh:
        print("\nskipped refresh - run 'packwiz refresh' in pack/ before committing")
        return 0

    print()
    return subprocess.call(["packwiz", "refresh"], cwd=ROOT / "pack")


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
