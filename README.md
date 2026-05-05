# FS25 Linux Mod Switcher

A GTK desktop app for managing and switching Farming Simulator 25 mod profiles on Linux.

Instead of keeping multiple copies of the same mods, this app maintains a single **mod library** and uses symlinks to build profiles. Switching profiles is instant and uses zero extra disk space.

---

## Features

- **Single mod library** — each mod zip stored once, no duplicates
- **Named profiles** — create loadouts like "Elmcreek Casual", "Multiplayer", "PV Rivers"
- **Instant switching** — profiles are symlinks, no file copying
- **Import Folder** — import a whole mod pack folder and assign it to a profile in one step
- **Import Files** — add individual mods to the library
- **Smart mod list** — mods in a profile shown at top, library mods below; newly added mods pin to bottom so you can see what you just changed
- **Auto-detection** — finds your FS25 mods folder automatically across all common Steam/Proton paths
- **Configurable path** — Settings button to change the mods folder at any time
- **FS25 running detection** — warns you if the game is open before switching

---

## Requirements

- Linux (tested on Bazzite, works on any distro with GTK3)
- Python 3.8+
- PyGObject (GTK3 bindings)
- Farming Simulator 25 via Steam + Proton (or native Linux install)

---

## Installation

**1. Clone the repo**
```bash
git clone https://github.com/william17050/FS25_Linux_Mod_Switcher.git
cd FS25_Linux_Mod_Switcher
```

**2. Run the install script**
```bash
chmod +x install.sh
./install.sh
```

This installs PyGObject if needed, copies the app to `~/.local/bin`, and adds it to your app launcher.

**3. Launch**

Search for **FS25 Mod Switcher** in your app launcher, or run:
```bash
fs25-mod-switcher
```

---

## First Run

On first launch the app will:
1. Automatically scan for your FS25 mods folder across all common Steam/Proton locations
2. Show you the detected path to confirm (or let you browse to it manually)
3. Migrate your existing mods folder into the library and create a **Default** profile — your mods are untouched

---

## How It Works

```
~/Documents/FS25ModLibrary/       ← all mod zips live here (one copy each)
    courseplay.zip
    seasons.zip
    FS25_PVRivers.zip
    ...

~/Documents/FS25ModProfiles/      ← profiles are folders of symlinks
    Default/
        courseplay.zip  →  ../../FS25ModLibrary/courseplay.zip
        seasons.zip     →  ../../FS25ModLibrary/seasons.zip
    PV Rivers/
        courseplay.zip  →  ../../FS25ModLibrary/courseplay.zip
        FS25_PVRivers.zip → ../../FS25ModLibrary/FS25_PVRivers.zip

~/.steam/.../FarmingSimulator2025/mods  →  ~/Documents/FS25ModProfiles/Default
```

The game's `mods` folder is a symlink pointing at whichever profile is active. Switching profiles just repoints that symlink.

---

## Usage

| Action | How |
|--------|-----|
| Switch profile | Select profile on the left → click **Switch to Selected** |
| New profile | Click **New Profile** → name it → tick mods from library |
| Import a mod pack folder | Click **Import Folder** → pick folder → assign to profile |
| Import individual mods | Click **Import Files** → select zip files |
| Add/remove a mod from profile | Tick/untick in the right panel |
| Change mods folder path | Click **⚙ Settings** |

---

## License

MIT
