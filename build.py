#!/usr/bin/env python3.10
"""
Build script for Email Testing Server
Creates standalone executables for Windows and Linux using PyInstaller
"""

import os
import sys
import shutil
import platform
import subprocess
from pathlib import Path
from datetime import datetime
import stat

# Build configuration
APP_NAME = "email-testing-server"
VERSION = "1.0.0"
AUTHOR = "Ananthu Krishnan <dev.ananthu.krishnan@gmail.com>"
DESCRIPTION = "Local Email Testing Server - A desktop application for testing email functionality locally"
MAINTAINER = "Ananthu Krishnan"
PACKAGE_NAME = "email-testing-server"
SECTION = "net"
PRIORITY = "optional"
ARCHITECTURE = "amd64"
DEPENDS = "python3 (>= 3.10), python3-pip"

# Platform-specific settings
IS_WINDOWS = platform.system() == "Windows"
ICON_EXT = ".ico" if IS_WINDOWS else ".png"
ICON_NAME = f"assets/icon{ICON_EXT}"

# Python version check
REQUIRED_PYTHON = (3, 10)
if sys.version_info < REQUIRED_PYTHON:
    print(
        f"Error: Python {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]} or higher is required"
    )
    print(f"Current Python version: {sys.version_info[0]}.{sys.version_info[1]}")
    sys.exit(1)


def get_python_cmd():
    if IS_WINDOWS:
        for cmd in ["python3.10", "py -3.10", "python -3.10"]:
            try:
                subprocess.run(
                    cmd.split() + ["--version"], check=True, capture_output=True
                )
                return cmd.split()
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        raise RuntimeError(
            "Python 3.10 not found. Please install it and ensure it's in PATH"
        )
    else:
        python_cmd = "python3.10"
        try:
            subprocess.run([python_cmd, "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "Python 3.10 not found. Try: sudo apt install python3.10"
            )
        return [python_cmd]


def clean_build_dirs():
    for dir_name in ["build", "dist"]:
        if os.path.exists(dir_name):
            print(f"Cleaning {dir_name} directory...")
            shutil.rmtree(dir_name)


def setup_virtual_env():
    venv_dir = "env"
    if os.path.exists(venv_dir):
        shutil.rmtree(venv_dir)

    print("Creating virtual environment...")
    subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)

    if IS_WINDOWS:
        python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
        pip_exe = os.path.join(venv_dir, "Scripts", "pip.exe")
    else:
        python_exe = os.path.join(venv_dir, "bin", "python")
        pip_exe = os.path.join(venv_dir, "bin", "pip")

    subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    return python_exe, pip_exe


def install_dependencies(python_exe, pip_exe):
    print("Installing dependencies in virtual environment...")
    deps = [
        "flet==0.28.3",  # Updated to exact version from requirements.txt
        "flet-cli==0.28.3",
        "flet-desktop==0.28.3",
        # "flet-desktop-light==0.28.3",
        "flet-web==0.28.3",
        "aiosmtpd==1.4.6",
        "html2text==2025.4.15",
        "PyQt6==6.9.0",
        "PyQt6-Qt6==6.9.0",
        "PyQt6_sip==13.10.2",
        "Pillow==10.2.0",
        "python-dotenv==1.1.0",
        "requests==2.31.0",
        "dnspython==2.7.0",
        "pyinstaller==6.3.0",
        "pyinstaller-hooks-contrib==2025.4",
        "cryptography==42.0.5",
        "websockets==15.0.1",
        "fastapi==0.115.12",
        "uvicorn==0.34.2",
        "starlette==0.46.2",
        "pydantic==2.11.5",
        "pydantic_core==2.33.2",
        "typing_extensions==4.13.2",
        "anyio==4.9.0",
        "click==8.2.1",
        "h11==0.16.0",
        "httpx==0.28.1",
        "idna==3.10",
        "sniffio==1.3.1",
        "watchfiles==1.0.5",
        "watchdog==4.0.2",
        "rich==14.0.0",
        "pygments==2.19.1",
        "markdown-it-py==3.0.0",
        "mdurl==0.1.2",
        "packaging==25.0",
        "platformdirs==4.2.0",
        "toml==0.10.2",
        "tomlkit==0.12.4",
        "pyproject_hooks==1.0.0",
        "build==1.0.3",
        "installer==0.7.0",
        "wheel==0.42.0",
        "setuptools==69.2.0",
    ]
    for dep in deps:
        try:
            print(f"Installing {dep}...")
            subprocess.run([pip_exe, "install", dep], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error installing {dep}: {e}")
            raise


def create_version_file():
    if not IS_WINDOWS:
        return None
    version_info = f"""
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({VERSION.replace('.', ', ')}, 0),
    prodvers=({VERSION.replace('.', ', ')}, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'{AUTHOR.split("<")[0].strip()}'),
        StringStruct(u'FileDescription', u'{DESCRIPTION}'),
        StringStruct(u'FileVersion', u'{VERSION}'),
        StringStruct(u'InternalName', u'{APP_NAME}'),
        StringStruct(u'LegalCopyright', u'Copyright (c) {datetime.now().year} {AUTHOR}'),
        StringStruct(u'OriginalFilename', u'{APP_NAME}.exe'),
        StringStruct(u'ProductName', u'{APP_NAME}'),
        StringStruct(u'ProductVersion', u'{VERSION}')])
    ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
    version_file = "version_info.txt"
    with open(version_file, "w") as f:
        f.write(version_info)
    return version_file


def create_default_icon():
    try:
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (256, 256), color="#1a1a1a")
        draw = ImageDraw.Draw(img)
        draw.rectangle(((50, 50), (206, 206)), outline="#2196F3", width=8)
        draw.line([(50, 100), (206, 100)], fill="#2196F3", width=8)
        os.makedirs("assets", exist_ok=True)
        img.save(ICON_NAME)
    except ImportError:
        print("PIL not installed, skipping icon generation")
        os.makedirs("assets", exist_ok=True)
        with open(ICON_NAME, "wb") as f:
            f.write(b"")


def build_executable():
    clean_build_dirs()
    python_exe, pip_exe = setup_virtual_env()
    install_dependencies(python_exe, pip_exe)

    # Ensure icons exist
    if not os.path.exists(ICON_NAME):
        raise RuntimeError(f"Icon file {ICON_NAME} not found in assets directory")

    # Copy icons to build directory for PyInstaller
    build_assets_dir = os.path.join("build", "assets")
    os.makedirs(build_assets_dir, exist_ok=True)
    shutil.copy2(ICON_NAME, os.path.join(build_assets_dir, os.path.basename(ICON_NAME)))
    # Also copy the other icon format for cross-platform support
    other_icon = "assets/icon.png" if IS_WINDOWS else "assets/icon.ico"
    shutil.copy2(
        other_icon, os.path.join(build_assets_dir, os.path.basename(other_icon))
    )

    version_file = create_version_file() if IS_WINDOWS else None

    # Collect all required Flet components
    flet_components = [
        "flet",
        "flet_core",
        "flet_runtime",
        "flet_web",
        "flet_desktop",
        "flet_desktop_light",
        "flet_cli",
        "flet_utils",
        "flet_async",
        "flet_async_websocket",
        "flet_async_websocket_connection",
        "flet_async_websocket_connection_state",
    ]

    pyinstaller_cmd = [
        python_exe,
        "-m",
        "PyInstaller",
        "main.py",
        "--name",
        APP_NAME,
        "--onefile",
        "--windowed",
        "--clean",
        "--noconfirm",
        "--icon",
        ICON_NAME,
        "--add-data",
        f"assets{os.pathsep}assets",  # Add entire assets directory
        "--add-data",
        f"build/assets{os.pathsep}assets",  # Add build assets directory
        "--collect-all",
        "aiosmtpd",
        "--collect-all",
        "Pillow",
        "--collect-all",
        "requests",
        "--collect-all",
        "html2text",
        "--collect-all",
        "cryptography",
        "--collect-all",
        "websockets",
        "--collect-all",
        "fastapi",
        "--collect-all",
        "uvicorn",
        "--collect-all",
        "starlette",
        "--collect-all",
        "pydantic",
        "--collect-all",
        "anyio",
        "--collect-all",
        "httpx",
        "--collect-all",
        "watchfiles",
        "--collect-all",
        "rich",
        "--collect-all",
        "markdown_it",
        "--collect-all",
        "PyQt6",
    ]

    # Add all Flet components
    for component in flet_components:
        pyinstaller_cmd.extend(["--collect-all", component])

    # Add hidden imports
    hidden_imports = [
        "email_server",
        "logger_config",
        "flet",
        "flet_core",
        "flet_runtime",
        "flet_web",
        "flet_desktop",
        "flet_desktop_light",
        "flet_cli",
        "flet_utils",
        "flet_async",
        "flet_async_websocket",
        "flet_async_websocket_connection",
        "flet_async_websocket_connection_state",
        "aiosmtpd",
        "aiosmtpd.controller",
        "aiosmtpd.handlers",
        "PIL",
        "PIL._tkinter_finder",
        "PyQt6",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.sip",
        "requests",
        "html2text",
        "cryptography",
        "websockets",
        "fastapi",
        "fastapi.applications",
        "fastapi.routing",
        "fastapi.middleware",
        "starlette",
        "starlette.applications",
        "starlette.routing",
        "starlette.middleware",
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.lifespan",
        "uvicorn.protocols",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "pydantic",
        "pydantic_core",
        "pydantic.json",
        "pydantic.types",
        "pydantic.validators",
        "pydantic.errors",
        "pydantic.fields",
        "pydantic.main",
        "pydantic.networks",
        "pydantic.schema",
        "pydantic.utils",
        "pydantic.version",
        "anyio",
        "anyio.abc",
        "anyio.streams",
        "anyio.streams.memory",
        "anyio.streams.stapled",
        "anyio.streams.text",
        "anyio.streams.tls",
        "anyio.to_thread",
        "anyio.from_thread",
        "anyio.lowlevel",
        "anyio.path",
        "anyio._backends",
        "anyio._backends._asyncio",
        "anyio._backends._trio",
        "httpx",
        "httpx._client",
        "httpx._config",
        "httpx._content",
        "httpx._exceptions",
        "httpx._models",
        "httpx._status_codes",
        "httpx._transports",
        "httpx._types",
        "httpx._utils",
        "httpx._version",
        "watchfiles",
        "watchfiles.filters",
        "watchfiles.main",
        "watchfiles.run",
        "watchfiles.watcher",
        "watchfiles.watcher._fsevents",
        "watchfiles.watcher._inotify",
        "watchfiles.watcher._kqueue",
        "watchfiles.watcher._polling",
        "watchfiles.watcher._windows",
        "rich",
        "rich.console",
        "rich.highlighter",
        "rich.logging",
        "rich.markdown",
        "rich.panel",
        "rich.pretty",
        "rich.progress",
        "rich.prompt",
        "rich.rule",
        "rich.style",
        "rich.syntax",
        "rich.table",
        "rich.text",
        "rich.theme",
        "rich.traceback",
        "markdown_it",
        "markdown_it.parser_block",
        "markdown_it.parser_core",
        "markdown_it.parser_inline",
        "markdown_it.renderer",
        "markdown_it.rules_block",
        "markdown_it.rules_core",
        "markdown_it.rules_inline",
        "markdown_it.utils",
        "typing_extensions",
        "email",
        "email.message",
        "email.parser",
        "email.policy",
        "email.utils",
        "email.header",
        "email.charset",
        "email.encoders",
        "email.generator",
        "email.iterators",
        "email.mime",
        "email.mime.text",
        "email.mime.multipart",
        "email.mime.nonmultipart",
        "email.mime.base",
        "email.mime.application",
        "email.mime.audio",
        "email.mime.image",
        "email.mime.message",
        "datetime",
        "json",
        "logging",
        "socket",
        "threading",
        "time",
        "html",
        "html.parser",
        "html.entities",
        "urllib",
        "urllib.parse",
        "urllib.request",
        "urllib.error",
        "urllib.response",
        "pathlib",
        "os",
        "sys",
        "asyncio",
        "asyncio.base_events",
        "asyncio.base_subprocess",
        "asyncio.constants",
        "asyncio.coroutines",
        "asyncio.events",
        "asyncio.exceptions",
        "asyncio.format_helpers",
        "asyncio.futures",
        "asyncio.locks",
        "asyncio.log",
        "asyncio.proactor_events",
        "asyncio.protocols",
        "asyncio.queues",
        "asyncio.runners",
        "asyncio.selector_events",
        "asyncio.streams",
        "asyncio.subprocess",
        "asyncio.tasks",
        "asyncio.transports",
        "asyncio.unix_events",
        "asyncio.windows_events",
        "asyncio.windows_utils",
    ]

    for imp in hidden_imports:
        pyinstaller_cmd.extend(["--hidden-import", imp])

    if version_file:
        pyinstaller_cmd.extend(["--version-file", version_file])

    # Add additional data files
    pyinstaller_cmd.extend(
        [
            "--add-data",
            f"email_server.py{os.pathsep}.",
            "--add-data",
            f"logger_config.py{os.pathsep}.",
            "--add-data",
            f"version.py{os.pathsep}.",
        ]
    )

    print("Building executable...")
    print("Running command:", " ".join(pyinstaller_cmd))
    subprocess.run(pyinstaller_cmd, check=True)

    if version_file and os.path.exists(version_file):
        os.remove(version_file)

    print(f"\nBuild completed successfully!")
    print(
        f"Executable location: {os.path.join('dist', APP_NAME + ('.exe' if IS_WINDOWS else ''))}"
    )


def create_deb_package():
    """Create a Debian package (.deb) for the application."""
    print("\nCreating Debian package...")

    try:
        # Ensure icons exist
        if not os.path.exists(ICON_NAME):
            raise RuntimeError(f"Icon file {ICON_NAME} not found in assets directory")

        # Create package directory structure
        package_dir = f"{PACKAGE_NAME}_{VERSION}_{ARCHITECTURE}"
        if os.path.exists(package_dir):
            shutil.rmtree(package_dir)

        # Create DEBIAN directory
        debian_dir = os.path.join(package_dir, "DEBIAN")
        os.makedirs(debian_dir, exist_ok=True)

        # Create control file
        control_content = f"""Package: {PACKAGE_NAME}
Version: {VERSION}
Section: {SECTION}
Priority: {PRIORITY}
Architecture: {ARCHITECTURE}
Depends: {DEPENDS}
Maintainer: {MAINTAINER} <{AUTHOR.split('<')[1].strip('>')}>
Description: {DESCRIPTION}
 This is a desktop application for testing email functionality locally.
 It provides a local SMTP server and a user interface to monitor emails.
"""

        with open(os.path.join(debian_dir, "control"), "w") as f:
            f.write(control_content)

        # Create postinst script with proper icon cache update
        postinst_content = """#!/bin/bash
set -e
# Update desktop database
update-desktop-database || true
# Update icon cache for all icon sizes
for size in 16 24 32 48 64 128 256; do
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor/${size}x${size} || true
done
# Update icon cache for hicolor
gtk-update-icon-cache -f -t /usr/share/icons/hicolor || true
"""

        with open(os.path.join(debian_dir, "postinst"), "w") as f:
            f.write(postinst_content)
        os.chmod(
            os.path.join(debian_dir, "postinst"),
            stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH,
        )

        # Create prerm script
        prerm_content = """#!/bin/bash
set -e
# Update desktop database
update-desktop-database || true
# Update icon cache for all icon sizes
for size in 16 24 32 48 64 128 256; do
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor/${size}x${size} || true
done
# Update icon cache for hicolor
gtk-update-icon-cache -f -t /usr/share/icons/hicolor || true
"""

        with open(os.path.join(debian_dir, "prerm"), "w") as f:
            f.write(prerm_content)
        os.chmod(
            os.path.join(debian_dir, "prerm"),
            stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH,
        )

        # Create desktop entry with proper icon path
        desktop_dir = os.path.join(package_dir, "usr", "share", "applications")
        os.makedirs(desktop_dir, exist_ok=True)

        desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Email Testing Server
Comment={DESCRIPTION}
Exec=/usr/bin/{APP_NAME}
Icon={APP_NAME}
Terminal=false
Categories=Network;Email;
StartupWMClass={APP_NAME}
StartupNotify=true
"""

        with open(os.path.join(desktop_dir, f"{PACKAGE_NAME}.desktop"), "w") as f:
            f.write(desktop_content)

        # Create icon directories and copy icon to all standard sizes
        icon_sizes = [16, 24, 32, 48, 64, 128, 256]
        for size in icon_sizes:
            icon_dir = os.path.join(
                package_dir,
                "usr",
                "share",
                "icons",
                "hicolor",
                f"{size}x{size}",
                "apps",
            )
            os.makedirs(icon_dir, exist_ok=True)
            shutil.copy2(ICON_NAME, os.path.join(icon_dir, f"{APP_NAME}.png"))

        # Create binary directory and copy executable
        bin_dir = os.path.join(package_dir, "usr", "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy2(os.path.join("dist", APP_NAME), os.path.join(bin_dir, APP_NAME))
        os.chmod(
            os.path.join(bin_dir, APP_NAME),
            stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH,
        )

        # Build the package
        deb_file = f"{PACKAGE_NAME}_{VERSION}_{ARCHITECTURE}.deb"
        if os.path.exists(deb_file):
            os.remove(deb_file)

        print(f"Building {deb_file}...")
        subprocess.run(["dpkg-deb", "--build", package_dir], check=True)

        # Clean up
        shutil.rmtree(package_dir)

        print(f"\nDebian package created successfully: {deb_file}")
        return deb_file

    except Exception as e:
        print(f"Error creating Debian package: {e}")
        raise


def build_all():
    """Build both executable and Debian package."""
    try:
        # First build the executable
        build_executable()

        # Then create the Debian package
        if not IS_WINDOWS:  # Only create .deb on Linux
            create_deb_package()

    except Exception as e:
        print(f"Build failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    build_all()
