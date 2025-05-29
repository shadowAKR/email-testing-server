import os
import platform
import subprocess
import shutil
import sys


def build_package():
    # Get the current platform
    system = platform.system().lower()

    # Create necessary directories
    os.makedirs("dist", exist_ok=True)
    os.makedirs("assets", exist_ok=True)

    # Create a default icon if it doesn't exist
    if not os.path.exists("assets/icon.png"):
        create_default_icon()

    # Install required packages
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

    # Build command
    build_cmd = [
        "pyinstaller",
        "--name=EmailTestingServer",
        "--onefile",
        "--windowed",
        (
            "--add-data=assets:assets"
            if system == "windows"
            else "--add-data=assets:assets"
        ),
        "--icon=assets/icon.png",
        "main.py",
    ]

    # Run PyInstaller
    subprocess.run(build_cmd)

    # Create platform-specific package
    if system == "windows":
        # Create Windows installer using NSIS
        if not os.path.exists("installer.nsi"):
            create_nsis_script()
        subprocess.run(["makensis", "installer.nsi"])
    elif system == "linux":
        # Create Debian package
        create_debian_package()

    print(f"Build completed for {system}")


def create_default_icon():
    """Create a default icon if none exists"""
    try:
        from PIL import Image, ImageDraw

        # Create a 256x256 image with a blue background
        img = Image.new("RGB", (256, 256), color="#1a1a1a")
        draw = ImageDraw.Draw(img)

        # Draw a simple envelope shape
        draw.rectangle([(50, 50), (206, 206)], outline="#2196F3", width=8)
        draw.line([(50, 100), (206, 100)], fill="#2196F3", width=8)

        # Save the image
        img.save("assets/icon.png")
    except ImportError:
        print("Warning: PIL not installed, skipping icon creation")
        # Create an empty icon file
        with open("assets/icon.png", "wb") as f:
            f.write(b"")


def create_nsis_script():
    """Create NSIS script for Windows installer"""
    nsis_script = """
    !include "MUI2.nsh"
    
    Name "Email Testing Server"
    OutFile "dist/EmailTestingServer-Setup.exe"
    InstallDir "$PROGRAMFILES\\Email Testing Server"
    
    !insertmacro MUI_PAGE_WELCOME
    !insertmacro MUI_PAGE_DIRECTORY
    !insertmacro MUI_PAGE_INSTFILES
    !insertmacro MUI_PAGE_FINISH
    
    !insertmacro MUI_UNPAGE_CONFIRM
    !insertmacro MUI_UNPAGE_INSTFILES
    
    !insertmacro MUI_LANGUAGE "English"
    
    Section "Install"
        SetOutPath "$INSTDIR"
        File "dist\\EmailTestingServer.exe"
        CreateDirectory "$INSTDIR\\assets"
        CopyFiles "assets\\*.*" "$INSTDIR\\assets"
        
        CreateShortCut "$DESKTOP\\Email Testing Server.lnk" "$INSTDIR\\EmailTestingServer.exe"
        CreateShortCut "$STARTMENU\\Email Testing Server.lnk" "$INSTDIR\\EmailTestingServer.exe"
        
        WriteUninstaller "$INSTDIR\\uninstall.exe"
    SectionEnd
    
    Section "Uninstall"
        Delete "$INSTDIR\\EmailTestingServer.exe"
        Delete "$INSTDIR\\uninstall.exe"
        RMDir /r "$INSTDIR\\assets"
        RMDir "$INSTDIR"
        
        Delete "$DESKTOP\\Email Testing Server.lnk"
        Delete "$STARTMENU\\Email Testing Server.lnk"
    SectionEnd
    """

    with open("installer.nsi", "w") as f:
        f.write(nsis_script)


def create_debian_package():
    """Create Debian package for Ubuntu"""
    # Create DEBIAN directory
    os.makedirs("debian/DEBIAN", exist_ok=True)
    os.makedirs("debian/usr/bin", exist_ok=True)
    os.makedirs("debian/usr/share/applications", exist_ok=True)
    os.makedirs("debian/usr/share/email-testing-server/assets", exist_ok=True)

    # Create control file
    control_content = """Package: email-testing-server
Version: 1.0.0
Section: utils
Priority: optional
Architecture: amd64
Depends: python3
Maintainer: Your Name <your.email@example.com>
Description: Local Email Testing Server
 A desktop application for testing email functionality locally.
"""

    with open("debian/DEBIAN/control", "w") as f:
        f.write(control_content)

    # Create desktop entry
    desktop_entry = """[Desktop Entry]
Name=Email Testing Server
Comment=Local Email Testing Server
Exec=/usr/bin/email-testing-server
Icon=/usr/share/email-testing-server/assets/icon.png
Terminal=false
Type=Application
Categories=Utility;
"""

    with open("debian/usr/share/applications/email-testing-server.desktop", "w") as f:
        f.write(desktop_entry)

    # Copy executable and assets
    executable_path = "dist/EmailTestingServer"
    if not os.path.exists(executable_path):
        print(f"Error: Executable not found at {executable_path}")
        return

    shutil.copy(executable_path, "debian/usr/bin/email-testing-server")
    if os.path.exists("assets"):
        shutil.copytree(
            "assets", "debian/usr/share/email-testing-server/assets", dirs_exist_ok=True
        )

    # Set permissions
    os.chmod("debian/usr/bin/email-testing-server", 0o755)

    # Build package
    subprocess.run(
        ["dpkg-deb", "--build", "debian", "dist/email-testing-server_1.0.0_amd64.deb"]
    )

    # Cleanup
    shutil.rmtree("debian")


if __name__ == "__main__":
    build_package()
