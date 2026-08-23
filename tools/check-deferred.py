#!/usr/bin/env python3
"""Report which deferred Skyblock mods have a build for the pack's MC version.

Reads the target Minecraft version out of pack/pack.toml so it stays correct
across version bumps, then asks Modrinth once per slug.
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = "Soul-Returns/hypixel-skyblock-modpack check-deferred"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req) as fh:
        return json.load(fh)


def pack_mc_version():
    text = (ROOT / "pack" / "pack.toml").read_text()
    match = re.search(r'^minecraft\s*=\s*"([^"]+)"', text, re.M)
    if not match:
        sys.exit("could not read minecraft version from pack/pack.toml")
    return match.group(1)


def slugs():
    lines = (ROOT / "tools" / "deferred.txt").read_text().splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]


def main():
    mc = pack_mc_version()
    query = urllib.parse.urlencode({
        "game_versions": json.dumps([mc]),
        "loaders": json.dumps(["fabric"]),
    })
    ready, waiting = [], []
    for slug in slugs():
        try:
            versions = get(f"https://api.modrinth.com/v2/project/{slug}/version?{query}")
        except urllib.error.HTTPError as exc:
            waiting.append((slug, f"HTTP {exc.code}"))
            continue
        if versions:
            newest = versions[0]
            ready.append((slug, newest["version_number"], newest["version_type"]))
        else:
            project = get(f"https://api.modrinth.com/v2/project/{slug}")
            newest_mc = project["game_versions"][-1] if project["game_versions"] else "?"
            waiting.append((slug, f"newest MC {newest_mc}"))
        time.sleep(0.12)

    print(f"pack targets Minecraft {mc}\n")
    print(f"READY ({len(ready)})")
    for slug, version, kind in sorted(ready):
        note = "" if kind == "release" else f"  <{kind}>"
        print(f"  {slug:<26} {version}{note}")
    print(f"\nNO {mc} BUILD YET ({len(waiting)})")
    for slug, why in sorted(waiting):
        print(f"  {slug:<26} {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
