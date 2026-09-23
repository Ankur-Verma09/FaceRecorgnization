import subprocess
import sys
import shutil
from pathlib import Path

def make_installer():
    print("=== Step 1: Building Base Application Executable Folder ===")
    build_script = Path(__file__).parent / "build_installer.py"
    res = subprocess.run([sys.executable, str(build_script)])
    if res.returncode != 0:
        print("Error building base application folder.")
        sys.exit(1)

    print("\n=== Step 2: Packaging Single 1-Click Windows Setup Executable ===")
    res = subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "setup_spec.spec"])
    if res.returncode != 0:
        print("Error compiling setup executable.")
        sys.exit(1)

    # Move output to installer_output directory
    dist_setup = Path(__file__).parent / "dist" / "Setup_OfflineFacePhotoOrganizer_v1.0.0.exe"
    out_dir = Path(__file__).parent / "installer_output"
    out_dir.mkdir(exist_ok=True)
    out_setup = out_dir / "Setup_OfflineFacePhotoOrganizer_v1.0.0.exe"

    if dist_setup.exists():
        shutil.move(str(dist_setup), str(out_setup))

    print("\n========================================================")
    print("=== Windows Setup Installer Built Successfully! ===")
    print(f"Installer File: {out_setup}")
    print("========================================================")
    print("This installer will:")
    print(" 1. Install app to C:\\Program Files\\Offline Face Photo Organizer")
    print(" 2. Create Start Menu & Desktop Shortcuts")
    print(" 3. Register in Windows Control Panel (Add/Remove Programs)")
    print(" 4. Include full Windows Control Panel Uninstaller")

if __name__ == "__main__":
    make_installer()
