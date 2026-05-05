#!/bin/bash
set -e

echo "Installing FS25 Linux Mod Switcher..."

# Install PyGObject if not already available
if ! python3 -c "import gi" 2>/dev/null; then
    echo "Installing PyGObject..."
    pip3 install pygobject
fi

# Verify GTK3 is accessible
if ! python3 -c "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk" 2>/dev/null; then
    echo "ERROR: GTK3 not found. Please install the GTK3 runtime for your distro."
    echo "  Fedora/Bazzite: sudo dnf install gtk3"
    echo "  Ubuntu/Debian:  sudo apt install python3-gi gir1.2-gtk-3.0"
    exit 1
fi

# Install the script
mkdir -p ~/.local/bin
cp mod_switcher.py ~/.local/bin/fs25-mod-switcher
chmod +x ~/.local/bin/fs25-mod-switcher

# Install desktop entry
mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/fs25-mod-switcher.desktop << EOF
[Desktop Entry]
Name=FS25 Mod Switcher
Comment=Switch mod profiles for Farming Simulator 25
Exec=python3 $HOME/.local/bin/fs25-mod-switcher
Icon=applications-games
Terminal=false
Type=Application
Categories=Game;Utility;
EOF

# Make sure ~/.local/bin is on PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo ""
    echo "NOTE: ~/.local/bin is not in your PATH."
    echo "Add this to your ~/.bashrc or ~/.zshrc:"
    echo '  export PATH="$HOME/.local/bin:$PATH"'
fi

echo ""
echo "Done! Search for 'FS25 Mod Switcher' in your app launcher."
echo "Or run: fs25-mod-switcher"
