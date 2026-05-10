# FS25 Linux Mod Switcher

A GTK desktop app for managing and switching Farming Simulator 25 mod profiles on Linux. Built by a Linux FS25 player, for Linux FS25 players.

Most mod switchers work by keeping multiple full copies of your mods — one per profile. This app does it properly: **one copy of each mod, zero duplication**. Profiles are just lists of shortcuts (symlinks) pointing back to the single library. Switching is instant and costs no extra disk space.

---

## Features

- **Single mod library** — each mod zip stored once, no matter how many profiles use it
- **Named profiles** — create loadouts like "Elmcreek Casual", "Multiplayer Lite", "PV Rivers Full"
- **Instant switching** — switching profiles just repoints a single symlink, no file copying
- **Import Folder** — point at a downloaded mod pack folder and assign all of it to a profile in one click
- **Import Files** — add individual mod zips to the library
- **Smart mod list** — mods in your profile shown at the top, rest of library below; newly added mods appear at the bottom of the active section so you can see what you just changed
- **Clone profile** — duplicate an existing profile as a starting point, then add or remove mods from the copy
- **Mod metadata** — reads `modDesc.xml` inside each zip to extract title, author, version, and dependencies; map mods are marked with a 🗺 icon
- **Auto dependency detection** — ticking a mod automatically ticks its declared dependencies if they are in your library; warns about any that are missing
- **Dependency safety warning** — warns you if you try to remove a mod that another mod in the profile depends on
- **Auto-detection** — automatically finds your FS25 mods folder across all common Steam and Proton paths
- **Settings** — if auto-detection misses it, browse to your mods folder manually and save it
- **FS25 running guard** — warns you if the game is open before switching profiles

---

## Requirements

- Linux (developed and tested on Bazzite; works on any distro with GTK3)
- Python 3.8 or newer
- PyGObject (GTK3 Python bindings — installed automatically by the install script)
- Farming Simulator 25 via Steam + Proton, or the native Linux build

---

## Installation

**Step 1 — Clone the repository**

Open a terminal and run:

```bash
git clone https://github.com/william17050/FS25_Linux_Mod_Switcher.git
cd FS25_Linux_Mod_Switcher
```

**Step 2 — Run the install script**

```bash
chmod +x install.sh
./install.sh
```

This will:
- Install PyGObject (GTK3 bindings) if not already present
- Copy the app to `~/.local/bin/`
- Add **FS25 Mod Switcher** to your desktop app launcher

**Step 3 — Launch**

Search for **FS25 Mod Switcher** in your app launcher (press the Super/Windows key and start typing), or run from terminal:

```bash
fs25-mod-switcher
```

---

## First Launch

The first time you open the app it will:

1. **Scan automatically** for your FS25 mods folder across all common Steam/Proton install locations
2. **Confirm the path** — show you what it found and ask you to confirm, or let you browse to it manually if it wasn't found
3. **Migrate your existing mods** — if you have an existing mods folder, it moves everything into the library and creates a **Default** profile containing all of them. Your mods are safe and untouched.

After that you're ready to create profiles and start switching.

---

## How It Works

The core idea is simple. Instead of copying mods around, the app keeps one master copy of every mod in a library folder. Each profile is just a folder full of shortcuts (symlinks) pointing back to the library. The game's `mods` folder is itself a shortcut pointing at whichever profile is active.

```
~/Documents/FS25ModLibrary/          ← every mod lives here, once
    courseplay.zip
    seasons.zip
    FS25_PVRivers.zip
    bigTractor.zip

~/Documents/FS25ModProfiles/         ← profiles are folders of shortcuts
    Default/
        courseplay.zip  →  library/courseplay.zip
        seasons.zip     →  library/seasons.zip
    PV Rivers/
        courseplay.zip  →  library/courseplay.zip
        FS25_PVRivers.zip → library/FS25_PVRivers.zip
        seasons.zip     →  library/seasons.zip

~/.steam/.../FarmingSimulator2025/mods  →  FS25ModProfiles/Default  ← active profile
```

Switching profiles changes only the last line. The files never move.

---

## Step-by-Step Usage Guide

### Importing your first mods

If you already had a mods folder, your mods are already in the library after first launch. If you have additional mods to add:

- **Single mods:** Click **Import Files** in the top-right header → select one or more `.zip` files
- **A full mod pack folder:** Click **Import Folder** → browse to the folder → choose which profile to assign them all to (or create a new one on the spot)

### Creating a profile

1. Click **New Profile**
2. Give it a name (e.g. "PV Rivers")
3. A checklist of every mod in your library appears — tick the ones you want in this profile
4. Click OK — the profile is created with symlinks for each ticked mod

### Adding mods to an existing profile

1. Click the profile name on the left to select it
2. The right panel shows two sections: **In this profile** and **Not in profile**
3. Tick any mod in the **Not in profile** section to add it — it moves to the top section instantly
4. Untick a mod to remove it — it drops back into the bottom section alphabetically

### Switching profiles

1. Select the profile you want on the left
2. Click **Switch to Selected**
3. Close the app and launch FS25 — it will load the mods from the new profile

> **Note:** FS25 must be closed before switching. The app will warn you if it detects the game is running.

### Cloning a profile

Have a profile you want to use as a base for a new one? Select it and click **Clone**. Enter a name for the copy — it opens immediately with the same mods already ticked, ready to adjust. Great for creating a "Template" profile with your core mods and cloning it for each new map.

### Changing your mods folder path

Click **⚙ Settings** in the top-left to browse to a different mods folder. Useful if Steam is installed in a non-standard location or if you reinstall the game.

---

## Quick Reference

| What you want to do | How |
|---|---|
| Switch to a different profile | Select it on the left → **Switch to Selected** |
| Create a new profile | **New Profile** → name it → tick mods |
| Import a map mod pack folder | **Import Folder** → pick folder → assign to profile |
| Import individual mods | **Import Files** → select zip files |
| Add a mod to a profile | Select profile → tick the mod in the right panel |
| Remove a mod from a profile | Select profile → untick the mod in the right panel |
| Clone an existing profile | Select profile → **Clone** → enter new name |
| Change the FS25 mods folder | **⚙ Settings** |

---

## Troubleshooting

**The app couldn't find my FS25 mods folder**
Click **⚙ Settings** and browse to it manually. For Steam + Proton installs the path is usually:
```
~/.steam/steam/steamapps/compatdata/<APPID>/pfx/drive_c/users/steamuser/Documents/My Games/FarmingSimulator2025/mods
```
Where `<APPID>` is a number — look inside `~/.steam/steam/steamapps/compatdata/` for the right one.

**The game isn't loading the right mods**
Make sure you closed the app after switching and launched FS25 fresh. The game reads the mods folder on startup.

**Import Files button is greyed out / missing**
The buttons are in the header bar at the top right of the window. Try maximising the window if they're not visible.

**PyGObject install fails**
Try installing GTK3 development libraries first:
- Fedora / Bazzite: `sudo dnf install gcc gobject-introspection-devel cairo-gobject-devel pkg-config python3-devel gtk3`
- Ubuntu / Debian: `sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0`

---

## Contributing

Pull requests welcome. If you find a bug or have a feature idea, open an issue.

---

## License

MIT — do whatever you want with it.
