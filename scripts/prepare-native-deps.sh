#!/bin/sh
# Supply WebKitGTK development files without requiring sudo. Runtime libraries
# remain system-provided; this cache only contains headers, pkg-config metadata,
# and unversioned linker symlinks.
set -eu

cd "$(dirname "$0")/.."

if pkg-config --exists webkit2gtk-4.1; then
	exit 0
fi

root_dir=".native-deps/root"
pc_file="$root_dir/usr/lib/x86_64-linux-gnu/pkgconfig/webkit2gtk-4.1.pc"
if [ -f "$pc_file" ] && grep -q 'local build fallback v6' "$pc_file"; then
	exit 0
fi

command -v apt-get >/dev/null 2>&1 || {
	echo "WebKitGTK development files are missing. Install libwebkit2gtk-4.1-dev and libgtk-3-dev." >&2
	exit 1
}
command -v dpkg-deb >/dev/null 2>&1 || {
	echo "dpkg-deb is required to prepare local WebKitGTK development files." >&2
	exit 1
}

cache_dir="$(pwd)/.native-deps/archives"
rm -rf "$root_dir"
mkdir -p "$cache_dir/partial" "$root_dir"

# apt-get install --download-only still takes the system dpkg lock. Download
# the small development packages directly instead; their runtime libraries
# are already present on the build host.
(
	cd "$cache_dir"
	apt-get download \
		libwebkit2gtk-4.1-dev \
		libjavascriptcoregtk-4.1-dev \
		libgtk-3-dev \
		libsoup-3.0-dev \
		libatk1.0-dev \
		libpango1.0-dev
)

for package in "$cache_dir"/*.deb; do
	[ -e "$package" ] || continue
	dpkg-deb -x "$package" "$root_dir"
done

# The host has runtime libraries but not their unversioned development links.
# Fill in the few links used by Wails' WebKitGTK build flags.
lib_dir="$root_dir/usr/lib/x86_64-linux-gnu"
# The extracted dev package links to a runtime .so that intentionally is not
# copied into the cache. Point the relevant linker names at the host runtime.
for library in libwebkit2gtk-4.1.so libjavascriptcoregtk-4.1.so libgtk-3.so \
	libgdk-3.so libatk-1.0.so libsoup-3.0.so; do
	if [ -e "/usr/lib/x86_64-linux-gnu/${library%.so}.so.0" ]; then
		ln -sfn "/usr/lib/x86_64-linux-gnu/${library%.so}.so.0" "$lib_dir/$library"
	fi
done

# Avoid requiring every transitive .pc file: the extracted packages provide
# headers, while the explicit flags below match Wails' WebKitGTK link set.
project_root=$(pwd)
system_cflags='-I/usr/include/gio-unix-2.0 -I/usr/include/glib-2.0 -I/usr/lib/x86_64-linux-gnu/glib-2.0/include -I/usr/include/cairo -I/usr/include/gdk-pixbuf-2.0 -I/usr/include/pixman-1 -I/usr/include/fribidi -I/usr/include/harfbuzz -I/usr/include/freetype2 -I/usr/include/libpng16 -I/usr/include/libmount -I/usr/include/blkid -pthread'
cat > "$pc_file" <<PC
prefix=$project_root/$root_dir/usr
libdir=\${prefix}/lib/x86_64-linux-gnu
includedir=\${prefix}/include

Name: WebKitGTK local build fallback v6
Description: User-local WebKitGTK development metadata
Version: 4.1
Libs: -L\${libdir} -lwebkit2gtk-4.1 -lgtk-3 -lgdk-3 -lpangocairo-1.0 -lcairo-gobject -lgdk_pixbuf-2.0 -latk-1.0 -lpango-1.0 -lcairo -lharfbuzz -lsoup-3.0 -ljavascriptcoregtk-4.1 -lgobject-2.0 -lglib-2.0
Cflags: -I\${includedir}/webkitgtk-4.1 -I\${includedir}/gtk-3.0 -I\${includedir}/gdk-pixbuf-2.0 -I\${includedir}/pango-1.0 -I\${includedir}/cairo -I\${includedir}/libsoup-3.0 $system_cflags
PC

cat > "$lib_dir/pkgconfig/gtk+-3.0.pc" <<PC
prefix=$project_root/$root_dir/usr
includedir=\${prefix}/include

Name: GTK+ local build fallback
Description: User-local GTK development metadata
Version: 3.24
Libs: -L$lib_dir -lgtk-3 -lgdk-3 -latk-1.0 -lgdk_pixbuf-2.0 -lpangocairo-1.0 -lpango-1.0 -lcairo -lgobject-2.0 -lglib-2.0
Cflags: -I\${includedir}/gtk-3.0 -I\${includedir}/atk-1.0 -I\${includedir}/gdk-pixbuf-2.0 -I\${includedir}/pango-1.0 -I\${includedir}/cairo $system_cflags
PC

cat > "$lib_dir/pkgconfig/libsoup-3.0.pc" <<PC
prefix=$project_root/$root_dir/usr
includedir=\${prefix}/include

Name: libsoup local build fallback
Description: User-local libsoup development metadata
Version: 3.0
Libs: -L$lib_dir -lsoup-3.0 -lgio-2.0 -lgobject-2.0 -lglib-2.0
Cflags: -I\${includedir}/libsoup-3.0 $system_cflags
PC
