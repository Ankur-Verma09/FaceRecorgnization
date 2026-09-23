import subprocess
import sys
import shutil
from pathlib import Path

def build_app():
    print("=== Step 1: Building React Frontend Assets ===")
    frontend_dir = Path(__file__).parent / "frontend"
    npm_cmd = "npm run build"
    res = subprocess.run(f"cmd /c \"cd /d {frontend_dir} && {npm_cmd}\"", shell=True)
    if res.returncode != 0:
        print("Error: Frontend build failed.")
        sys.exit(1)

    print("\n=== Step 2: Running PyInstaller Build ===")
    pyinstaller_cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "app.spec"]
    res = subprocess.run(pyinstaller_cmd)
    if res.returncode != 0:
        print("Error: PyInstaller build failed. Ensure pyinstaller is installed ('pip install pyinstaller').")
        sys.exit(1)

    print("\n=== PyInstaller Build Completed Successfully! ===")
    print(f"Executable folder generated at: {Path(__file__).parent / 'dist' / 'OfflineFacePhotoOrganizer'}")

if __name__ == "__main__":
    build_app()
