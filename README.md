# Hypixel Skyblock Modpack

A preconfigured, self-updating Hypixel Skyblock modpack for
[Prism Launcher](https://prismlauncher.org/). Install once, then it updates
itself on every launch — no re-importing, no re-doing keybinds.

> **Status: mods only.** The 30 mods install and update correctly. Game
> options, keybinds and mod configs are not shipped yet — that baseline is
> being built and will land via `tools/import-baseline.py`.

- **Minecraft** 26.2, **Fabric Loader** 0.19.3 (needs Java 25, Prism downloads it)
- Update URL: `https://soul-returns.github.io/hypixel-skyblock-modpack/pack.toml`

## For players

1. Install [Prism Launcher](https://prismlauncher.org/) and log in.
2. Download `Hypixel-Skyblock.zip` from
   [Releases](https://github.com/Soul-Returns/hypixel-skyblock-modpack/releases).
3. In Prism: **Add Instance → Import from zip →** pick the file.
4. Launch. The first start downloads the mods and settings, so it takes a minute.

Once the baseline lands, keybinds, video settings and the server list come
preconfigured — and they stay yours to change. Nothing you set in the game's own
options menu is ever overwritten by an update.

### What updates do to your instance

| Your change | What happens on update |
|---|---|
| You installed your own mods | **Untouched.** The updater only manages files it installed itself. |
| You edited a config the pack ships | Kept — until the pack changes that same file, which overwrites it. |
| You edited a config the pack does not ship | **Untouched.** |
| A mod is removed from the pack | Deleted, because the updater installed it. |
| You rebound a key | **Kept forever.** Keybinds are shipped as *defaults*, so anything you rebind wins permanently. |
| You changed a video/gameplay setting | **Kept.** Those defaults apply on your first launch only and are never reapplied. |

Two things to know if you add your own mods:

- **Do not hand-install a Skyblock mod that might land in the pack later**
  (SkyHanni, Skyblocker, Firmament…). You would end up with two copies and
  Minecraft refuses to start on a duplicate mod id. Ask instead — that is what
  the optional-mod list is for.
- **Remove your own mods before a Minecraft version bump.** The pack's mods get
  updated, yours do not, and an old jar crashes the game.

Never remove the pre-launch command in **Edit Instance → Settings → Custom
commands**. That command *is* the updater.

## For me (maintaining it)

```bash
cd pack
packwiz update --all        # or: packwiz update skyhanni
packwiz refresh             # rewrite index.toml hashes  <- do not skip
cd .. && git commit -am "Update mods" && git push
```

Pushing to `main` publishes `pack/` to GitHub Pages, and every player picks it
up on their next launch. CI fails the build if `index.toml` is stale, so a
forgotten `packwiz refresh` cannot ship broken hashes.

Adding a mod:

```bash
cd pack && packwiz mr add <modrinth-slug> && packwiz refresh
```

Shipping a mod config change is just editing the file under `pack/config/` and
running `packwiz refresh`. That overwrites the file for everyone, including
players who tuned it — which is the point for things like duplicate-feature
defaults.

### Game options and keybinds

Vanilla settings are **not** shipped as `options.txt`, because that file is a
single blob: changing view bobbing in it would also reset everyone's hotbar
keys. They go through [Default Options](https://modrinth.com/mod/default-options)
instead, which splits the problem in two:

| File | Granularity | Can you push a change later? |
|---|---|---|
| `config/defaultoptions/keybindings.txt` | **per key** | **Yes.** Reapplied every launch as each key's *default*. A key the player rebound keeps their binding; a key they never touched follows yours, including keys you add later. |
| `config/defaultoptions/options.txt` | whole file | **No.** Copied only when the player has no `options.txt` at all, i.e. genuinely once. |
| `config/defaultoptions/servers.dat` | whole file | No, same rule. |

So keybind defaults are live and safe to edit; video and gameplay defaults are
a one-shot at install time. If you must change a video setting for people who
already installed, you have to tell them — there is no mechanism for it, and
that is the deliberate cost of never clobbering their settings.

Never add `options.txt` or `servers.dat` to the pack root. Default Options owns
those paths in the player's instance, and shipping them through packwiz would
reintroduce exactly the clobbering this avoids.

#### Importing a baseline

Configure a real instance and import it, rather than editing these files by
hand. Point the script at an instance created **from this pack** — its config
directory then holds configs for exactly the mods the pack ships, so there is
nothing to filter.

```bash
# in game, after setting up options and keybinds:
#   /defaultoptions saveAll
tools/import-baseline.py ~/.local/share/PrismLauncher/instances/<name>/minecraft --only defaults

# later, once mods are configured:
tools/import-baseline.py ~/.local/share/PrismLauncher/instances/<name>/minecraft --only configs
```

`--only` keeps the two stages independent, so importing mod configs cannot
disturb the game defaults. The script replaces rather than merges each section —
otherwise a config for a mod dropped from the pack would ship forever. It also
excludes mod repo caches (hundreds of MB, refetched on demand) and
`sodium-fingerprint.json`, and rewrites the machine-specific `soundDevice` and
resource pack list out of the shipped options.

### Layout

```
pack/                  the modpack itself; this directory is what Pages serves
  pack.toml            MC + loader versions, pack version
  index.toml           generated by `packwiz refresh` — never edit by hand
  mods/*.pw.toml       one file per mod: download URL, hash, update source
  config/              shipped mod configs (not populated yet)
  config/defaultoptions/
    options.txt        video and gameplay defaults, applied on first launch only
    keybindings.txt    keybind defaults, reapplied per key every launch
    servers.dat        server list, preadded on first launch
installer/
  instance/            Prism instance template (no mods, just settings + updater)
  build-instance.sh    builds dist/Hypixel-Skyblock.zip
tools/
  deferred.txt         Skyblock mods deliberately not in the pack yet
  check-deferred.py    which of them have a build for pack.toml's MC version
  add-optional.sh      adds the taste-dependent mods as optional mods
  import-baseline.py   imports a configured instance's settings into the pack
```

### Rebuilding the player zip

Only needed when the update URL, memory defaults, Minecraft/loader version or a
pinned installer jar changes — not for mod updates.

The zip ships `packwiz-installer.jar` pinned and launches the bootstrap with
`--bootstrap-no-update`. That is deliberate: left to update itself, the
bootstrap calls `api.github.com` on **every launch**, which allows 60
unauthenticated requests per hour per IP. Once it 403s, the bootstrap fails to
load the installer at all and the game does not start — so a few players behind
one NAT would break each other's launches. Both jars are hash-checked at build
time. Bumping them is a manual version bump in `build-instance.sh`.

```bash
./installer/build-instance.sh
```

Then attach `dist/Hypixel-Skyblock.zip` to a GitHub release.

### Optional mods

`tools/add-optional.sh` marks a mod optional: players get a checkbox for it on
first install, and again whenever a new optional mod appears. Use this instead
of arguing about taste — it keeps people inside the pack rather than
hand-installing mods and hitting duplicate-id crashes.

### Deferred Skyblock mods

The pack currently ships **no** Skyblock mods. SoulMod is next in line and
needs a tagged release in `Soul-Returns/SoulModRework` first, since packwiz
references a download URL. Everything else is listed in `tools/deferred.txt`:

```bash
python3 tools/check-deferred.py
```

Adding them is not just a `packwiz mr add`. SkyHanni, Skyblocker and Firmament
overlap heavily and enable duplicate features by default; resolving that in
`pack/config/` is the actual work, and is the reason this pack exists.
