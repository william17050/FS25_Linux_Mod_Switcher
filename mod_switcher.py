#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Pango

import os
import shutil
import json
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

LIBRARY_DIR = Path.home() / "Documents/FS25ModLibrary"
LIBRARY_INDEX = LIBRARY_DIR / "library_index.json"
PROFILES_DIR = Path.home() / "Documents/FS25ModProfiles"
CONFIG_FILE = Path.home() / ".config/fs25-mod-switcher/config.json"

MODS_PATH = None  # set at startup from config or detection


# ── detection ─────────────────────────────────────────────────────────────────

def detect_mods_path():
    """Scan common Steam locations for the FS25 mods folder."""
    proton_suffix = Path("pfx/drive_c/users/steamuser/Documents/My Games/FarmingSimulator2025/mods")
    compatdata_roots = [
        Path.home() / ".steam/steam/steamapps/compatdata",
        Path.home() / ".var/app/com.valvesoftware.Steam/.steam/steam/steamapps/compatdata",
        Path.home() / ".local/share/Steam/steamapps/compatdata",
    ]
    for root in compatdata_roots:
        if not root.exists():
            continue
        for appid_dir in sorted(root.iterdir()):
            candidate = appid_dir / proton_suffix
            if candidate.exists() or candidate.is_symlink():
                return candidate

    # Native Linux install
    native = Path.home() / ".local/share/FarmingSimulator2025/mods"
    if native.exists() or native.is_symlink():
        return native

    return None


# ── config ────────────────────────────────────────────────────────────────────

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def save_config(config):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


# ── mod metadata ─────────────────────────────────────────────────────────────

def read_mod_metadata(zip_path):
    """Peek inside a mod zip and parse modDesc.xml. Returns dict or None."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            with z.open('modDesc.xml') as f:
                root = ET.parse(f).getroot()

            title_el = root.find('.//title/en')
            title = (title_el.text or '').strip() if title_el is not None else ''

            author_el = root.find('author')
            author = (author_el.text or '').strip() if author_el is not None else ''

            version_el = root.find('version')
            version = (version_el.text or '').strip() if version_el is not None else ''

            is_map = root.find('.//maps/map') is not None

            deps = [d.text.strip() for d in root.findall('.//dependencies/dependency')
                    if d.text and d.text.strip()]

            return {'title': title, 'author': author, 'version': version,
                    'isMap': is_map, 'dependencies': deps}
    except Exception:
        return None


def load_library_index():
    if LIBRARY_INDEX.exists():
        with open(LIBRARY_INDEX) as f:
            return json.load(f)
    return {}


def save_library_index(index):
    with open(LIBRARY_INDEX, 'w') as f:
        json.dump(index, f, indent=2)


def scan_library_for_metadata():
    """Scan any library mods not yet in the index and add their metadata."""
    index = load_library_index()
    changed = False
    for mod_file in LIBRARY_DIR.iterdir():
        if mod_file.suffix.lower() != '.zip':
            continue
        if mod_file.name not in index:
            meta = read_mod_metadata(mod_file)
            index[mod_file.name] = meta or {}
            changed = True
    if changed:
        save_library_index(index)
    return index


def index_mod(mod_name):
    """Read and store metadata for a single newly imported mod."""
    index = load_library_index()
    if mod_name not in index:
        meta = read_mod_metadata(LIBRARY_DIR / mod_name)
        index[mod_name] = meta or {}
        save_library_index(index)


def resolve_dependencies(mod_name, index):
    """Return list of zip filenames that are dependencies of mod_name and exist in library."""
    meta = index.get(mod_name, {})
    deps = meta.get('dependencies', [])
    library_mods = set(get_library_mods())
    found = []
    missing = []
    for dep in deps:
        zip_name = dep if dep.endswith('.zip') else dep + '.zip'
        if zip_name in library_mods:
            found.append(zip_name)
        else:
            missing.append(dep)
    return found, missing


# ── data helpers ──────────────────────────────────────────────────────────────

def get_profiles():
    return sorted(p.name for p in PROFILES_DIR.iterdir() if p.is_dir())


def get_active_profile():
    if MODS_PATH and MODS_PATH.is_symlink():
        target = Path(os.readlink(str(MODS_PATH)))
        if target.parent == PROFILES_DIR:
            return target.name
    return None


def get_library_mods():
    return sorted(f.name for f in LIBRARY_DIR.iterdir() if f.is_file())


def get_profile_mods(profile_name):
    folder = PROFILES_DIR / profile_name
    return {f.name for f in folder.iterdir() if f.is_symlink()}


def is_fs25_running():
    try:
        return subprocess.run(["pgrep", "-f", "FarmingSimulator25"], capture_output=True).returncode == 0
    except Exception:
        return False


def migrate_to_library(source_dir):
    moved = []
    for f in list(source_dir.iterdir()):
        if f.is_file() and not f.is_symlink():
            dest = LIBRARY_DIR / f.name
            if not dest.exists():
                shutil.move(str(f), str(dest))
            else:
                f.unlink()
            moved.append(f.name)
    return moved


def create_profile_symlinks(profile_name, mod_names):
    folder = PROFILES_DIR / profile_name
    folder.mkdir(parents=True, exist_ok=True)
    for name in mod_names:
        link = folder / name
        if not link.exists():
            link.symlink_to(LIBRARY_DIR / name)


def set_active_profile(profile_name, config):
    target = PROFILES_DIR / profile_name
    if MODS_PATH.is_symlink():
        MODS_PATH.unlink()
    MODS_PATH.symlink_to(target)
    config["active_profile"] = profile_name
    save_config(config)


def first_run_setup():
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    if MODS_PATH.exists() and not MODS_PATH.is_symlink():
        moved = migrate_to_library(MODS_PATH)
        MODS_PATH.rmdir()
        create_profile_symlinks("Default", moved)
        config = load_config()
        set_active_profile("Default", config)

    elif MODS_PATH.is_symlink():
        target = MODS_PATH.resolve()
        if target.exists() and any(f.is_file() and not f.is_symlink() for f in target.iterdir()):
            moved = migrate_to_library(target)
            create_profile_symlinks(target.name, moved)

    elif not MODS_PATH.exists():
        (PROFILES_DIR / "Default").mkdir(exist_ok=True)
        config = load_config()
        set_active_profile("Default", config)


# ── setup dialog ──────────────────────────────────────────────────────────────

class SetupDialog(Gtk.Dialog):
    """Shown on first run or when the user opens Settings."""

    def __init__(self, parent, current_path=None):
        super().__init__(title="FS25 Mods Folder", parent=parent, modal=True)
        self.set_default_size(520, -1)
        self.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                         "Save", Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)

        detected = detect_mods_path()
        self._path = current_path or detected

        box = self.get_content_area()
        box.set_spacing(10)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)

        if detected and not current_path:
            status = Gtk.Label(use_markup=True, halign=Gtk.Align.START)
            status.set_markup("<b>FS25 mods folder detected automatically.</b>")
            box.pack_start(status, False, False, 0)
        elif not detected and not current_path:
            status = Gtk.Label(use_markup=True, halign=Gtk.Align.START)
            status.set_markup("<span foreground='orange'>Could not detect FS25 automatically.\nBrowse to your mods folder manually.</span>")
            box.pack_start(status, False, False, 0)

        box.pack_start(Gtk.Label(label="FS25 mods folder:", halign=Gtk.Align.START), False, False, 0)

        path_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.pack_start(path_row, False, False, 0)

        self._path_label = Gtk.Label(halign=Gtk.Align.START)
        self._path_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        self._path_label.set_hexpand(True)
        self._update_path_label()
        path_row.pack_start(self._path_label, True, True, 0)

        browse_btn = Gtk.Button(label="Browse…")
        browse_btn.connect("clicked", self._on_browse)
        path_row.pack_start(browse_btn, False, False, 0)

        box.show_all()

    def _update_path_label(self):
        if self._path:
            self._path_label.set_markup(f"<tt>{self._path}</tt>")
        else:
            self._path_label.set_markup("<i>No folder selected</i>")

    def _on_browse(self, _btn):
        chooser = Gtk.FileChooserDialog(
            title="Select FS25 Mods Folder",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        chooser.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                            "Select", Gtk.ResponseType.OK)
        if self._path:
            try:
                chooser.set_current_folder(str(self._path.parent))
            except Exception:
                pass
        response = chooser.run()
        if response == Gtk.ResponseType.OK:
            self._path = Path(chooser.get_filename())
            self._update_path_label()
        chooser.destroy()

    def get_path(self):
        return self._path


# ── profile dialogs ───────────────────────────────────────────────────────────

class NewProfileDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title="New Profile", parent=parent, modal=True)
        self.set_default_size(420, 540)
        self.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                         Gtk.STOCK_OK, Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)

        box = self.get_content_area()
        box.set_spacing(0)

        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        name_box.set_margin_top(12)
        name_box.set_margin_start(12)
        name_box.set_margin_end(12)
        name_box.set_margin_bottom(6)
        box.pack_start(name_box, False, False, 0)

        name_box.pack_start(Gtk.Label(label="Name:"), False, False, 0)
        self._name_entry = Gtk.Entry()
        self._name_entry.set_activates_default(True)
        self._name_entry.set_hexpand(True)
        name_box.pack_start(self._name_entry, True, True, 0)

        box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)

        mod_label = Gtk.Label(label="Select mods for this profile:")
        mod_label.set_halign(Gtk.Align.START)
        mod_label.set_margin_start(12)
        mod_label.set_margin_top(8)
        box.pack_start(mod_label, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_margin_start(8)
        scrolled.set_margin_end(8)
        scrolled.set_margin_bottom(8)
        box.pack_start(scrolled, True, True, 0)

        list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        scrolled.add(list_box)

        self._checks = {}
        mods = get_library_mods()
        if not mods:
            list_box.pack_start(
                Gtk.Label(label="No mods in library yet.\nUse Import Mods to add some first."),
                True, True, 12)
        else:
            for name in mods:
                cb = Gtk.CheckButton(label=name)
                self._checks[name] = cb
                list_box.pack_start(cb, False, False, 0)

        box.show_all()

    def get_name(self):
        return self._name_entry.get_text().strip()

    def get_selected(self):
        return {name for name, cb in self._checks.items() if cb.get_active()}


# ── main window ───────────────────────────────────────────────────────────────

class ModSwitcherWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="FS25 Mod Switcher")
        self.set_default_size(860, 600)
        self.config = load_config()
        self._toggled_mods = []
        self._build_ui()
        self._refresh_profiles()

    def _build_ui(self):
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title("FS25 Mod Switcher")
        self.set_titlebar(header)

        settings_btn = Gtk.Button(label="⚙ Settings")
        settings_btn.connect("clicked", self._on_settings)
        header.pack_start(settings_btn)

        import_btn = Gtk.Button(label="Import Files")
        import_btn.connect("clicked", self._on_import)
        header.pack_end(import_btn)

        import_folder_btn = Gtk.Button(label="Import Folder")
        import_folder_btn.connect("clicked", self._on_import_folder)
        header.pack_end(import_folder_btn)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(root)

        self.active_label = Gtk.Label()
        self.active_label.set_margin_top(10)
        self.active_label.set_margin_bottom(10)
        root.pack_start(self.active_label, False, False, 0)

        root.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(220)
        root.pack_start(paned, True, True, 0)

        # Left — profiles
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        paned.add1(left)

        profile_label = Gtk.Label(label="Profiles")
        profile_label.get_style_context().add_class("dim-label")
        profile_label.set_margin_top(8)
        profile_label.set_margin_bottom(4)
        left.pack_start(profile_label, False, False, 0)

        scrolled_left = Gtk.ScrolledWindow()
        scrolled_left.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_left.set_vexpand(True)
        left.pack_start(scrolled_left, True, True, 0)

        self.profile_list = Gtk.ListBox()
        self.profile_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.profile_list.connect("row-selected", self._on_profile_selected)
        scrolled_left.add(self.profile_list)

        # Right — mod checklist
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        paned.add2(right)

        self.mod_panel_label = Gtk.Label(label="Mods")
        self.mod_panel_label.get_style_context().add_class("dim-label")
        self.mod_panel_label.set_margin_top(8)
        self.mod_panel_label.set_margin_bottom(4)
        right.pack_start(self.mod_panel_label, False, False, 0)

        scrolled_right = Gtk.ScrolledWindow()
        scrolled_right.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
        scrolled_right.set_overlay_scrolling(False)
        scrolled_right.set_vexpand(True)
        right.pack_start(scrolled_right, True, True, 0)

        self.mod_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        scrolled_right.add(self.mod_list_box)

        root.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)

        # Bottom buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_margin_top(10)
        btn_box.set_margin_bottom(10)
        btn_box.set_margin_start(12)
        btn_box.set_margin_end(12)
        root.pack_start(btn_box, False, False, 0)

        self.switch_btn = Gtk.Button(label="Switch to Selected")
        self.switch_btn.get_style_context().add_class("suggested-action")
        self.switch_btn.connect("clicked", self._on_switch)
        btn_box.pack_start(self.switch_btn, True, True, 0)

        new_btn = Gtk.Button(label="New Profile")
        new_btn.connect("clicked", self._on_new_profile)
        btn_box.pack_start(new_btn, False, False, 0)

        clone_btn = Gtk.Button(label="Clone")
        clone_btn.connect("clicked", self._on_clone)
        btn_box.pack_start(clone_btn, False, False, 0)

        rename_btn = Gtk.Button(label="Rename")
        rename_btn.connect("clicked", self._on_rename)
        btn_box.pack_start(rename_btn, False, False, 0)

        delete_btn = Gtk.Button(label="Delete")
        delete_btn.get_style_context().add_class("destructive-action")
        delete_btn.connect("clicked", self._on_delete)
        btn_box.pack_start(delete_btn, False, False, 0)

    # ── refresh ────────────────────────────────────────────────────────────────

    def _refresh_profiles(self):
        for child in self.profile_list.get_children():
            self.profile_list.remove(child)

        active = get_active_profile()
        if active:
            self.active_label.set_markup(f"<b>Active:  {active}</b>")
        else:
            self.active_label.set_markup("<b>No active profile</b>")

        for name in get_profiles():
            row = Gtk.ListBoxRow()
            row.profile_name = name

            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            hbox.set_margin_top(8)
            hbox.set_margin_bottom(8)
            hbox.set_margin_start(10)
            hbox.set_margin_end(10)

            label = Gtk.Label(label=name)
            label.set_halign(Gtk.Align.START)
            hbox.pack_start(label, True, True, 0)

            if name == active:
                dot = Gtk.Label(label="●")
                dot.get_style_context().add_class("dim-label")
                hbox.pack_end(dot, False, False, 0)

            row.add(hbox)
            self.profile_list.add(row)

        self.profile_list.show_all()
        self._refresh_mod_panel(None)

    def _refresh_mod_panel(self, profile_name):
        for child in self.mod_list_box.get_children():
            self.mod_list_box.remove(child)

        if profile_name is None:
            self.mod_panel_label.set_text("Mods")
            self.mod_list_box.show_all()
            return

        profile_mods = get_profile_mods(profile_name)
        library_mods = get_library_mods()

        self.mod_panel_label.set_markup(
            f"Mods in <b>{profile_name}</b>  "
            f"<span foreground='gray'>({len(profile_mods)} of {len(library_mods)})</span>"
        )

        if not library_mods:
            lbl = Gtk.Label(label="Library is empty. Import some mods first.")
            lbl.set_margin_top(16)
            self.mod_list_box.pack_start(lbl, False, False, 0)
        else:
            toggled_set = set(self._toggled_mods)

            in_profile = (
                [m for m in library_mods if m in profile_mods and m not in toggled_set] +
                [m for m in self._toggled_mods if m in profile_mods]
            )
            not_in_profile = [m for m in library_mods if m not in profile_mods]

            if in_profile:
                self._add_section_header(f"In this profile ({len(in_profile)})")
                for mod_name in in_profile:
                    self._add_mod_row(mod_name, True, profile_name)

            if in_profile and not_in_profile:
                sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
                sep.set_margin_top(4)
                sep.set_margin_bottom(4)
                self.mod_list_box.pack_start(sep, False, False, 0)

            if not_in_profile:
                self._add_section_header(f"Not in profile ({len(not_in_profile)})")
                for mod_name in not_in_profile:
                    self._add_mod_row(mod_name, False, profile_name)

        self.mod_list_box.show_all()

    def _add_section_header(self, text):
        lbl = Gtk.Label(label=text)
        lbl.set_halign(Gtk.Align.START)
        lbl.set_margin_start(8)
        lbl.set_margin_top(6)
        lbl.set_margin_bottom(2)
        lbl.get_style_context().add_class("dim-label")
        self.mod_list_box.pack_start(lbl, False, False, 0)

    def _add_mod_row(self, mod_name, active, profile_name):
        index = load_library_index()
        meta = index.get(mod_name, {})
        is_map = meta.get('isMap', False)
        deps = meta.get('dependencies', [])
        title = meta.get('title', '')

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row.set_margin_start(8)
        row.set_margin_top(3)
        row.set_margin_bottom(3)

        prefix = '🗺 ' if is_map else ''
        label = f"{prefix}{mod_name}"
        cb = Gtk.CheckButton(label=label)
        cb.set_active(active)
        cb.connect("toggled", self._on_mod_toggled, profile_name, mod_name)
        row.pack_start(cb, True, True, 0)

        if title:
            title_lbl = Gtk.Label(label=title)
            title_lbl.get_style_context().add_class("dim-label")
            title_lbl.set_ellipsize(Pango.EllipsizeMode.END)
            title_lbl.set_max_width_chars(30)
            row.pack_start(title_lbl, False, False, 0)

        if deps:
            dep_lbl = Gtk.Label(label=f"  {len(deps)} deps")
            dep_lbl.get_style_context().add_class("dim-label")
            row.pack_start(dep_lbl, False, False, 0)

        self.mod_list_box.pack_start(row, False, False, 0)

    # ── handlers ───────────────────────────────────────────────────────────────

    def _on_settings(self, _btn):
        global MODS_PATH
        dialog = SetupDialog(self, current_path=MODS_PATH)
        response = dialog.run()
        new_path = dialog.get_path()
        dialog.destroy()

        if response != Gtk.ResponseType.OK or not new_path:
            return

        MODS_PATH = new_path
        self.config["mods_path"] = str(new_path)
        save_config(self.config)
        first_run_setup()
        self._refresh_profiles()

    def _on_profile_selected(self, listbox, row):
        self._toggled_mods = []
        self._refresh_mod_panel(row.profile_name if row else None)

    def _on_mod_toggled(self, cb, profile_name, mod_name):
        link = PROFILES_DIR / profile_name / mod_name
        if cb.get_active():
            if not link.exists():
                link.symlink_to(LIBRARY_DIR / mod_name)
            if mod_name not in self._toggled_mods:
                self._toggled_mods.append(mod_name)

            # Auto-add dependencies
            index = load_library_index()
            found_deps, missing_deps = resolve_dependencies(mod_name, index)
            profile_mods = get_profile_mods(profile_name)
            auto_added = []
            for dep in found_deps:
                if dep not in profile_mods:
                    dep_link = PROFILES_DIR / profile_name / dep
                    if not dep_link.exists():
                        dep_link.symlink_to(LIBRARY_DIR / dep)
                    if dep not in self._toggled_mods:
                        self._toggled_mods.append(dep)
                    auto_added.append(dep)

            if auto_added or missing_deps:
                msg_parts = []
                if auto_added:
                    msg_parts.append(f"Auto-added {len(auto_added)} required mod{'s' if len(auto_added) != 1 else ''}:\n" +
                                     '\n'.join(f"  • {d}" for d in auto_added))
                if missing_deps:
                    msg_parts.append(f"Missing from library ({len(missing_deps)}):\n" +
                                     '\n'.join(f"  • {d}" for d in missing_deps))
                self._msg("Dependencies", '\n\n'.join(msg_parts),
                          Gtk.MessageType.WARNING if missing_deps else Gtk.MessageType.INFO)
        else:
            # Check if any other mod in this profile declares this as a dependency
            index = load_library_index()
            profile_mods = get_profile_mods(profile_name)
            mod_stem = mod_name[:-4] if mod_name.endswith('.zip') else mod_name
            needed_by = [
                m for m in profile_mods
                if mod_stem in index.get(m, {}).get('dependencies', [])
                and m != mod_name
            ]

            if needed_by:
                dialog = Gtk.MessageDialog(
                    parent=self, modal=True,
                    message_type=Gtk.MessageType.WARNING,
                    buttons=Gtk.ButtonsType.YES_NO,
                    text=f'"{mod_name}" is required by:'
                )
                dialog.format_secondary_text(
                    '\n'.join(f'  • {m}' for m in needed_by) +
                    '\n\nRemove it anyway?'
                )
                response = dialog.run()
                dialog.destroy()

                if response != Gtk.ResponseType.YES:
                    # Revert the checkbox without triggering another toggle
                    cb.handler_block_by_func(self._on_mod_toggled)
                    cb.set_active(True)
                    cb.handler_unblock_by_func(self._on_mod_toggled)
                    return

            if link.is_symlink():
                link.unlink()
            if mod_name in self._toggled_mods:
                self._toggled_mods.remove(mod_name)

        row = self.profile_list.get_selected_row()
        if row:
            self._refresh_mod_panel(row.profile_name)

    def _on_switch(self, _btn):
        row = self.profile_list.get_selected_row()
        if not row:
            self._msg("Select a profile", "Click a profile on the left first.")
            return
        selected = row.profile_name
        if selected == get_active_profile():
            self._msg("Already active", f'"{selected}" is already the active profile.')
            return
        if is_fs25_running():
            self._msg("FS25 is running",
                      "Close Farming Simulator 25 before switching profiles.",
                      Gtk.MessageType.WARNING)
            return
        set_active_profile(selected, self.config)
        self._refresh_profiles()

    def _on_new_profile(self, _btn):
        dialog = NewProfileDialog(self)
        response = dialog.run()
        name = dialog.get_name()
        selected_mods = dialog.get_selected()
        dialog.destroy()

        if response != Gtk.ResponseType.OK or not name:
            return
        if (PROFILES_DIR / name).exists():
            self._msg("Already exists", f'A profile named "{name}" already exists.')
            return

        create_profile_symlinks(name, selected_mods)
        self._refresh_profiles()

        for row in self.profile_list.get_children():
            if row.profile_name == name:
                self.profile_list.select_row(row)
                break

    def _on_clone(self, _btn):
        row = self.profile_list.get_selected_row()
        if not row:
            self._msg("Select a profile", "Click a profile to clone first.")
            return
        source = row.profile_name

        dialog = Gtk.Dialog(title="Clone Profile", parent=self, modal=True)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_OK, Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_default_size(320, -1)
        box = dialog.get_content_area()
        box.set_spacing(8)
        box.set_margin_top(14)
        box.set_margin_bottom(14)
        box.set_margin_start(14)
        box.set_margin_end(14)
        box.pack_start(Gtk.Label(label=f'Clone "{source}" as:', halign=Gtk.Align.START), False, False, 0)
        entry = Gtk.Entry()
        entry.set_text(f"{source} (copy)")
        entry.select_region(0, -1)
        entry.set_activates_default(True)
        box.pack_start(entry, False, False, 0)
        box.show_all()

        response = dialog.run()
        new_name = entry.get_text().strip()
        dialog.destroy()

        if response != Gtk.ResponseType.OK or not new_name:
            return
        if (PROFILES_DIR / new_name).exists():
            self._msg("Already exists", f'A profile named "{new_name}" already exists.')
            return

        # Copy all symlinks from source to new profile
        new_dir = PROFILES_DIR / new_name
        new_dir.mkdir()
        for link in (PROFILES_DIR / source).iterdir():
            if link.is_symlink():
                (new_dir / link.name).symlink_to(LIBRARY_DIR / link.name)

        self._refresh_profiles()

        # Select the new profile immediately
        for row in self.profile_list.get_children():
            if row.profile_name == new_name:
                self.profile_list.select_row(row)
                break

    def _on_rename(self, _btn):
        row = self.profile_list.get_selected_row()
        if not row:
            self._msg("Select a profile", "Click a profile on the left first.")
            return
        selected = row.profile_name

        dialog = Gtk.Dialog(title="Rename Profile", parent=self, modal=True)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_OK, Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_default_size(320, -1)
        box = dialog.get_content_area()
        box.set_spacing(8)
        box.set_margin_top(14)
        box.set_margin_bottom(14)
        box.set_margin_start(14)
        box.set_margin_end(14)
        box.pack_start(Gtk.Label(label=f'Rename "{selected}" to:', halign=Gtk.Align.START), False, False, 0)
        entry = Gtk.Entry()
        entry.set_text(selected)
        entry.select_region(0, -1)
        entry.set_activates_default(True)
        box.pack_start(entry, False, False, 0)
        box.show_all()

        response = dialog.run()
        new_name = entry.get_text().strip()
        dialog.destroy()

        if response != Gtk.ResponseType.OK or not new_name or new_name == selected:
            return
        if (PROFILES_DIR / new_name).exists():
            self._msg("Already exists", f'A profile named "{new_name}" already exists.')
            return

        old_path = PROFILES_DIR / selected
        new_path = PROFILES_DIR / new_name
        old_path.rename(new_path)

        if selected == get_active_profile():
            if MODS_PATH.is_symlink():
                MODS_PATH.unlink()
            MODS_PATH.symlink_to(new_path)
            self.config["active_profile"] = new_name
            save_config(self.config)

        self._refresh_profiles()

    def _on_delete(self, _btn):
        row = self.profile_list.get_selected_row()
        if not row:
            self._msg("Select a profile", "Click a profile on the left first.")
            return
        selected = row.profile_name
        if selected == get_active_profile():
            self._msg("Cannot delete active profile",
                      "Switch to another profile first.",
                      Gtk.MessageType.WARNING)
            return

        dialog = Gtk.MessageDialog(
            parent=self, modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f'Delete profile "{selected}"?'
        )
        dialog.format_secondary_text(
            "The profile and its symlinks will be removed.\n"
            "Your mod files in the library are NOT deleted."
        )
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.YES:
            shutil.rmtree(str(PROFILES_DIR / selected))
            self._refresh_profiles()

    def _on_import(self, _btn):
        dialog = Gtk.FileChooserDialog(
            title="Import Mods to Library", parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           "Import", Gtk.ResponseType.OK)
        dialog.set_select_multiple(True)
        f = Gtk.FileFilter()
        f.set_name("Mod files (*.zip)")
        f.add_pattern("*.zip")
        dialog.add_filter(f)

        response = dialog.run()
        files = dialog.get_filenames()
        dialog.destroy()

        if response != Gtk.ResponseType.OK:
            return

        imported, skipped = self._import_files_to_library([Path(p) for p in files])
        msg = f"Imported {imported} mod{'s' if imported != 1 else ''}."
        if skipped:
            msg += f"\n{skipped} already in library and skipped."
        self._msg("Import complete", msg)

        row = self.profile_list.get_selected_row()
        if row:
            self._refresh_mod_panel(row.profile_name)

    def _on_import_folder(self, _btn):
        chooser = Gtk.FileChooserDialog(
            title="Select Mod Folder", parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        chooser.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                            "Select", Gtk.ResponseType.OK)
        response = chooser.run()
        folder = Path(chooser.get_filename()) if response == Gtk.ResponseType.OK else None
        chooser.destroy()

        if folder is None:
            return

        zips = sorted(folder.glob("*.zip"))
        if not zips:
            self._msg("No mods found", f'No .zip files found in\n"{folder}"')
            return

        dialog = Gtk.Dialog(title="Import from Folder", parent=self, modal=True)
        dialog.set_default_size(380, -1)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           "Import", Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)

        box = dialog.get_content_area()
        box.set_spacing(10)
        box.set_margin_top(14)
        box.set_margin_bottom(14)
        box.set_margin_start(14)
        box.set_margin_end(14)

        box.pack_start(Gtk.Label(
            label=f'Found <b>{len(zips)}</b> mods in\n"{folder.name}"',
            use_markup=True, halign=Gtk.Align.START
        ), False, False, 0)
        box.pack_start(Gtk.Label(label="Add all to profile:", halign=Gtk.Align.START), False, False, 0)

        NEW_PROFILE_SENTINEL = "── New profile... ──"
        combo = Gtk.ComboBoxText()
        for name in get_profiles():
            combo.append_text(name)
        combo.append_text(NEW_PROFILE_SENTINEL)
        combo.set_active(0)
        box.pack_start(combo, False, False, 0)

        name_entry = Gtk.Entry()
        name_entry.set_placeholder_text("New profile name")
        name_entry.set_no_show_all(True)
        name_entry.set_activates_default(True)
        box.pack_start(name_entry, False, False, 0)

        combo.connect("changed", lambda _: name_entry.set_visible(
            combo.get_active_text() == NEW_PROFILE_SENTINEL))
        box.show_all()

        response = dialog.run()
        chosen = combo.get_active_text()
        new_name = name_entry.get_text().strip()
        dialog.destroy()

        if response != Gtk.ResponseType.OK:
            return

        if chosen == NEW_PROFILE_SENTINEL:
            if not new_name:
                self._msg("No name given", "Enter a name for the new profile.")
                return
            if (PROFILES_DIR / new_name).exists():
                self._msg("Already exists", f'A profile named "{new_name}" already exists.')
                return
            profile_name = new_name
            (PROFILES_DIR / profile_name).mkdir(parents=True)
        else:
            profile_name = chosen

        imported, skipped = self._import_files_to_library(zips)
        for z in zips:
            create_profile_symlinks(profile_name, [z.name])

        self._refresh_profiles()
        for row in self.profile_list.get_children():
            if row.profile_name == profile_name:
                self.profile_list.select_row(row)
                break

        msg = f"Imported {imported} mod{'s' if imported != 1 else ''} into library"
        if skipped:
            msg += f" ({skipped} already existed)"
        msg += f'\nand linked all to profile "{profile_name}".'
        self._msg("Import complete", msg)

    def _import_files_to_library(self, paths):
        imported = skipped = 0
        for src in paths:
            dest = LIBRARY_DIR / src.name
            if dest.exists():
                skipped += 1
            else:
                shutil.copy2(str(src), str(dest))
                index_mod(src.name)
                imported += 1
        return imported, skipped

    def _msg(self, title, body, msg_type=Gtk.MessageType.INFO):
        dialog = Gtk.MessageDialog(
            parent=self, modal=True,
            message_type=msg_type,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )
        dialog.format_secondary_text(body)
        dialog.run()
        dialog.destroy()


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    global MODS_PATH

    config = load_config()

    # Resolve mods path: saved config → auto-detect → ask user
    if "mods_path" in config:
        MODS_PATH = Path(config["mods_path"])
    else:
        MODS_PATH = detect_mods_path()

    # Show setup dialog if path is missing or doesn't exist
    if not MODS_PATH or (not MODS_PATH.exists() and not MODS_PATH.is_symlink()):
        # Need a throwaway window as parent for the dialog
        dummy = Gtk.Window()
        dialog = SetupDialog(dummy, current_path=MODS_PATH)
        response = dialog.run()
        chosen = dialog.get_path()
        dialog.destroy()
        dummy.destroy()

        if response != Gtk.ResponseType.OK or not chosen:
            return  # user cancelled, exit

        MODS_PATH = chosen
        config["mods_path"] = str(chosen)
        save_config(config)

    first_run_setup()
    scan_library_for_metadata()

    win = ModSwitcherWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
