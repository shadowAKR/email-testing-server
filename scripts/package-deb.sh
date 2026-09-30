#!/bin/sh
# Package the current native Linux build. Build on the target distro for ABI compatibility.
set -eu
umask 022
cd "$(dirname "$0")/.."
test -x build/bin/postroom || { echo 'Run make build first.' >&2; exit 1; }
arch=$(dpkg --print-architecture)
package_dir=$(mktemp -d)
chmod 755 "$package_dir"
trap 'rm -rf "$package_dir"' EXIT HUP INT TERM
install -Dm755 build/bin/postroom "$package_dir/usr/bin/postroom"
install -Dm644 assets/icon.png "$package_dir/usr/share/icons/hicolor/512x512/apps/postroom.png"
mkdir -p "$package_dir/DEBIAN" "$package_dir/usr/share/applications"
cat > "$package_dir/DEBIAN/control" <<CONTROL
Package: postroom
Version: 3.0.0
Architecture: $arch
Maintainer: Postroom
Section: devel
Priority: optional
Depends: libgtk-3-0 | libgtk-3-0t64, libwebkit2gtk-4.1-0
Description: Local SMTP capture and email inspection
 A Go and Wails desktop app for testing email without external delivery.
CONTROL
sed 's|Icon=.*|Icon=postroom|' postroom.desktop > "$package_dir/usr/share/applications/postroom.desktop"
dpkg-deb --root-owner-group --build "$package_dir" "build/bin/postroom_3.0.0_${arch}.deb"
